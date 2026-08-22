from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "controller", ROOT / "scripts/factory_qualification_controller.py"
)
controller = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(controller)


class ControllerTests(unittest.TestCase):
    def test_outer_supervisor_rejects_exit_zero_and_stdout_spoof(self) -> None:
        fixtures = ROOT / "tests/fixtures"
        self.assertEqual(
            controller.supervise_fixture(fixtures / "valid.py", {"status": "ok"})["decision"],
            "pass",
        )
        for name in ("os_exit.py", "stdout_spoof.py"):
            with self.subTest(name=name):
                result = controller.supervise_fixture(fixtures / name, {"status": "ok"})
                self.assertEqual(result["decision"], "fail")

    def test_candidate_control_paths_are_not_copied_or_executed(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        candidate = root / "candidate"
        accepted = root / "accepted"
        output = root / "neutral"
        (candidate / ".github/hooks").mkdir(parents=True)
        (candidate / ".github/hooks/evil.json").write_text(
            '{"hooks":{"sessionStart":[{"command":"touch /tmp/should-not-exist"}]}}'
        )
        (candidate / ".github/agents").mkdir(parents=True)
        (candidate / ".github/agents/director.agent.md").write_text("candidate behavior")
        (accepted / "evals").mkdir(parents=True)
        (accepted / "evals/case.md").write_text("accepted oracle")
        controller.sanitized_bundle(
            candidate, accepted, output, [".github/agents/*.agent.md"]
        )
        names = {path.name for path in output.rglob("*")}
        self.assertFalse({".github", ".claude", "AGENTS.md"} & names)
        self.assertNotIn("evil.json", (output / "manifest.json").read_text())

    def test_lifecycle_is_fail_closed_and_revocation_terminal(self) -> None:
        state = controller.transition("bootstrap_pending", "approve_bootstrap")
        self.assertEqual(state, "accepted")
        state = controller.transition(state, "detect_compromise")
        self.assertEqual(state, "disabled")
        state = controller.transition(state, "revoke")
        self.assertEqual(state, "revoked")
        with self.assertRaises(controller.QualificationError):
            controller.transition(state, "restore_uncompromised")

    def test_bootstrap_policy_cannot_issue_a_qualification(self) -> None:
        policy = json.loads((ROOT / "factory-controller/policy.json").read_text())
        lifecycle = json.loads((ROOT / "factory-controller/lifecycle.json").read_text())
        with self.assertRaisesRegex(controller.QualificationError, "not active"):
            controller.verify_policy(policy, lifecycle, "1" * 40)

    def test_fetch_credential_modes_are_explicit_and_least_privilege(self) -> None:
        configuration = json.loads((ROOT / "factory-controller/credential.json").read_text())
        for mode in ("personal-pat", "github-app"):
            controller.verify_credential_configuration(configuration, mode)
        with self.assertRaises(controller.QualificationError):
            controller.verify_credential_configuration(configuration, "ambient-token")
        overbroad = dict(configuration)
        overbroad["required_permissions"] = {"contents": "write", "metadata": "read"}
        with self.assertRaisesRegex(controller.QualificationError, "least privilege"):
            controller.verify_credential_configuration(overbroad, "personal-pat")

    def test_checkout_symlink_is_rejected_before_candidate_is_read(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "repo"
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / "safe.txt").write_text("safe")
        (root / "escape").symlink_to("/etc/passwd")
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        environment = os.environ.copy()
        environment.update({
            "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
        })
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "fixture"], check=True, env=environment)
        sha = controller.git_head(root)
        with self.assertRaisesRegex(controller.QualificationError, "contains symlinks"):
            controller.verify_checkout(root, sha, "candidate")


if __name__ == "__main__":
    unittest.main()

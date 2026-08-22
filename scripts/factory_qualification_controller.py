#!/usr/bin/env python3
"""Accepted Factory qualification controller.

Candidate repositories are untrusted data.  This module is always executed from
the accepted clockgrove/.github revision, never from a Factory checkout.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
RESULT_PREFIX = "FACTORY_TRUSTED_RESULT:"
TRANSITIONS = {
    ("bootstrap_pending", "approve_bootstrap"): "accepted",
    ("accepted", "qualify_upgrade"): "upgrade_qualified",
    ("upgrade_qualified", "activate_upgrade"): "accepted",
    ("accepted", "detect_compromise"): "disabled",
    ("upgrade_qualified", "detect_compromise"): "disabled",
    ("disabled", "restore_uncompromised"): "accepted",
    ("disabled", "restart_bootstrap"): "bootstrap_pending",
    ("accepted", "revoke"): "revoked",
    ("upgrade_qualified", "revoke"): "revoked",
    ("disabled", "revoke"): "revoked",
}


class QualificationError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise QualificationError(f"{path} must contain a JSON object")
    return value


def require_sha(value: str, name: str) -> None:
    if not SHA.fullmatch(value):
        raise QualificationError(f"{name} must be a full lowercase commit SHA")


def git_head(root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def verify_checkout(root: Path, expected: str, name: str) -> None:
    require_sha(expected, name)
    if git_head(root) != expected:
        raise QualificationError(f"{name} checkout does not match declared SHA")
    remotes = subprocess.run(
        ["git", "-C", str(root), "remote"], check=True, capture_output=True, text=True
    ).stdout.strip()
    if remotes:
        raise QualificationError(f"{name} checkout retains a network remote")
    config = (root / ".git/config").read_text(errors="replace")
    if "http.extraheader" in config.lower() or "authorization" in config.lower():
        raise QualificationError(f"{name} checkout retains credential configuration")
    symlinks = [path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_symlink()]
    if symlinks:
        raise QualificationError(f"{name} checkout contains symlinks: {', '.join(symlinks[:5])}")


def verify_policy(policy: dict, lifecycle: dict, workflow_sha: str) -> None:
    require_sha(workflow_sha, "controller")
    require_sha(policy.get("accepted_factory_sha", ""), "accepted Factory")
    if policy.get("candidate_repository") != "clockgrove/factory":
        raise QualificationError("controller policy targets an unexpected repository")
    if policy.get("workflow_path") != ".github/workflows/factory-accepted-qualification.yml":
        raise QualificationError("controller policy names an unexpected workflow")
    if lifecycle.get("state") not in {"accepted", "upgrade_qualified"}:
        raise QualificationError("controller lifecycle is not active")
    accepted = lifecycle.get("accepted_controller_sha")
    require_sha(accepted or "", "accepted controller")
    if accepted in lifecycle.get("revoked_controller_shas", []):
        raise QualificationError("accepted trust-root SHA is revoked")
    if workflow_sha in lifecycle.get("revoked_controller_shas", []):
        raise QualificationError("controller SHA is revoked")


def verify_credential_configuration(configuration: dict, mode: str) -> None:
    if mode not in configuration.get("supported_modes", {}):
        raise QualificationError("credential mode is not supported by accepted policy")
    if configuration.get("target_repository") != "clockgrove/factory":
        raise QualificationError("fetch credential targets an unexpected repository")
    if configuration.get("required_permissions") != {"contents": "read", "metadata": "read"}:
        raise QualificationError("fetch credential permissions are not least privilege")


def transition(state: str, event: str) -> str:
    try:
        return TRANSITIONS[(state, event)]
    except KeyError as exc:
        raise QualificationError(f"invalid lifecycle transition: {state} + {event}") from exc


def files_matching(root: Path, patterns: list[str]) -> list[Path]:
    matches: set[Path] = set()
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink() or ".git" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        if any(fnmatch.fnmatchcase(relative, pattern) for pattern in patterns):
            matches.add(path)
    return sorted(matches)


def sanitized_bundle(candidate: Path, accepted: Path, output: Path, patterns: list[str]) -> dict:
    if output.exists():
        shutil.rmtree(output)
    (output / "candidate-data").mkdir(parents=True)
    (output / "accepted-oracle").mkdir(parents=True)
    manifest: list[dict[str, str]] = []
    for number, source in enumerate(files_matching(candidate, patterns), start=1):
        data = source.read_bytes()
        target = output / "candidate-data" / f"input-{number:04d}.txt"
        target.write_bytes(data)
        manifest.append(
            {
                "source": source.relative_to(candidate).as_posix(),
                "file": target.relative_to(output).as_posix(),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    if not manifest:
        raise QualificationError("declared candidate input set is empty")
    for number, source in enumerate(sorted((accepted / "evals").glob("*.md")), start=1):
        target = output / "accepted-oracle" / f"case-{number:04d}.md"
        target.write_bytes(source.read_bytes())
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    # These names are intentionally absent so Copilot cannot discover candidate controls.
    forbidden = {".github", ".claude", "AGENTS.md", "CLAUDE.md", "GEMINI.md"}
    if any(path.name in forbidden for path in output.rglob("*")):
        raise QualificationError("sanitized input contains a configuration discovery path")
    return {"count": len(manifest), "manifest_sha256": hashlib.sha256((output / "manifest.json").read_bytes()).hexdigest()}


def run_accepted_validator(accepted: Path, candidate: Path, neutral: Path) -> None:
    del neutral  # The accepted gate performs data reads only and needs no working tree.
    required = (
        "plugin.json", "AGENTS.md", "README.md", "evals/manifest.json",
        "scripts/validate_factory.py", "scripts/qualification_controller.py",
        ".github/workflows/qualification-request.yml",
        ".github/workflows/validate-factory.yml",
        ".github/agents/clockgrove-director.agent.md",
    )
    missing = [name for name in required if not (candidate / name).is_file()]
    if missing:
        raise QualificationError(f"candidate is missing accepted package files: {', '.join(missing)}")
    plugin = load_json(candidate / "plugin.json")
    if plugin.get("name") != "clockgrove-factory":
        raise QualificationError("candidate plugin identity changed")
    for path in candidate.rglob("*.py"):
        if path.is_symlink() or ".git" in path.parts:
            continue
        try:
            compile(path.read_text(), str(path), "exec")
        except SyntaxError as exc:
            raise QualificationError(f"candidate Python is invalid: {path}") from exc
    request = (candidate / ".github/workflows/qualification-request.yml").read_text()
    for marker in (
        "clockgrove/.github", ".github/workflows/factory-accepted-qualification.yml",
        "persist-credentials: false", "0000000000000000000000000000000000000000",
    ):
        if marker not in request:
            raise QualificationError(f"candidate request boundary lacks {marker}")
    if "secrets." in request or "pull_request_target:" in request:
        raise QualificationError("candidate request crosses the secretless boundary")
    helper = (candidate / "scripts/qualification_controller.py").read_text()
    for forbidden in ("subprocess", "FACTORY_QUALIFICATION_COPILOT_TOKEN", "FACTORY_CANDIDATE_READ_TOKEN"):
        if forbidden in helper:
            raise QualificationError(f"candidate request helper contains forbidden {forbidden}")
    moving_action = re.compile(r"(?m)^\s*(?:uses:\s+[^#\n]+|[A-Za-z0-9_-]+:)@v\d+")
    for workflow in (candidate / ".github/workflows").glob("*.yml"):
        if moving_action.search(workflow.read_text()):
            raise QualificationError(f"candidate workflow has a moving action pin: {workflow.name}")


def supervise_fixture(executable: Path, expected: dict) -> dict:
    """Run untrusted fixture as a child; only this outer process issues PASS."""
    completed = subprocess.run(
        [sys.executable, "-I", str(executable)],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        env={"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"},
        check=False,
        timeout=10,
        close_fds=True,
    )
    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError:
        response = None
    passed = completed.returncode == 0 and response == expected and not completed.stderr
    return {
        "decision": "pass" if passed else "fail",
        "child_returncode": completed.returncode,
        "response_digest": hashlib.sha256(completed.stdout.encode()).hexdigest(),
    }


def deterministic(args: argparse.Namespace) -> None:
    policy = load_json(args.policy)
    lifecycle = load_json(args.lifecycle)
    credential = load_json(args.credential)
    verify_policy(policy, lifecycle, args.controller_sha)
    verify_credential_configuration(credential, args.credential_mode)
    require_sha(args.candidate_sha, "candidate")
    verify_checkout(args.accepted_root, policy["accepted_factory_sha"], "accepted Factory")
    verify_checkout(args.candidate_root, args.candidate_sha, "candidate")
    if args.candidate_sha in lifecycle.get("revoked_candidate_shas", []):
        raise QualificationError("candidate SHA is revoked")
    neutral = Path(tempfile.mkdtemp(prefix="factory-accepted-gate-"))
    try:
        run_accepted_validator(args.accepted_root, args.candidate_root, neutral)
        bundle = sanitized_bundle(
            args.candidate_root,
            args.accepted_root,
            args.bundle,
            policy["declared_candidate_inputs"],
        )
    finally:
        shutil.rmtree(neutral, ignore_errors=True)
    record = {
        "schema_version": 1,
        "decision": "pass",
        "controller_repository": "clockgrove/.github",
        "controller_sha": args.controller_sha,
        "candidate_repository": policy["candidate_repository"],
        "candidate_sha": args.candidate_sha,
        "accepted_factory_sha": policy["accepted_factory_sha"],
        "credential_mode": args.credential_mode,
        "input_manifest_sha256": "sha256:" + bundle["manifest_sha256"],
        "input_count": bundle["count"],
    }
    args.output.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")


def fixture(args: argparse.Namespace) -> None:
    result = supervise_fixture(args.executable, json.loads(args.expected))
    print(RESULT_PREFIX + json.dumps(result, sort_keys=True, separators=(",", ":")))
    if result["decision"] != args.expect_decision:
        raise QualificationError("outer supervisor decision differed from expectation")


def lifecycle(args: argparse.Namespace) -> None:
    record = load_json(args.input)
    next_state = transition(record["state"], args.event)
    record["state"] = next_state
    if args.controller_sha:
        require_sha(args.controller_sha, "controller")
    if args.event in {"approve_bootstrap", "activate_upgrade", "restore_uncompromised"}:
        if not args.controller_sha:
            raise QualificationError("transition requires an immutable controller SHA")
        record["accepted_controller_sha"] = args.controller_sha
    if args.event == "revoke":
        if not args.controller_sha:
            raise QualificationError("revocation requires a controller SHA")
        values = set(record.get("revoked_controller_shas", []))
        values.add(args.controller_sha)
        record["revoked_controller_shas"] = sorted(values)
    args.output.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")


def release_record(args: argparse.Namespace) -> None:
    deterministic_record = load_json(args.deterministic)
    for name, value in (
        ("controller", args.controller_sha),
        ("candidate", args.candidate_sha),
    ):
        require_sha(value, name)
    expected = {
        "decision": "pass",
        "controller_repository": "clockgrove/.github",
        "controller_sha": args.controller_sha,
        "candidate_repository": "clockgrove/factory",
        "candidate_sha": args.candidate_sha,
    }
    for key, value in expected.items():
        if deterministic_record.get(key) != value:
            raise QualificationError(f"deterministic record has wrong {key}")
    evidence = []
    for path in sorted(args.evidence):
        body = path.read_text()
        if "FACTORY_QUALIFICATION: PASS" not in body:
            raise QualificationError(f"semantic evidence did not pass: {path.name}")
        evidence.append(
            {
                "name": path.name,
                "sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    if not evidence:
        raise QualificationError("semantic evidence is required")
    request = load_json(args.request)
    for key in ("controller_repository", "controller_sha", "candidate_repository", "candidate_sha"):
        if request.get(key) != expected[key]:
            raise QualificationError(f"qualification request has wrong {key}")
    record = {
        **expected,
        "schema_version": 1,
        "accepted_factory_sha": deterministic_record["accepted_factory_sha"],
        "credential_mode": deterministic_record["credential_mode"],
        "input_manifest_sha256": deterministic_record["input_manifest_sha256"],
        "request_sha256": "sha256:" + hashlib.sha256(args.request.read_bytes()).hexdigest(),
        "workflow_ref": f"clockgrove/.github/.github/workflows/factory-accepted-qualification.yml@{args.controller_sha}",
        "run_id": args.run_id,
        "run_attempt": args.run_attempt,
        "semantic_evidence": evidence,
    }
    args.output.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    commands = result.add_subparsers(dest="command", required=True)
    gate = commands.add_parser("deterministic")
    gate.add_argument("--policy", type=Path, required=True)
    gate.add_argument("--lifecycle", type=Path, required=True)
    gate.add_argument("--credential", type=Path, required=True)
    gate.add_argument("--credential-mode", required=True)
    gate.add_argument("--accepted-root", type=Path, required=True)
    gate.add_argument("--candidate-root", type=Path, required=True)
    gate.add_argument("--controller-sha", required=True)
    gate.add_argument("--candidate-sha", required=True)
    gate.add_argument("--bundle", type=Path, required=True)
    gate.add_argument("--output", type=Path, required=True)
    gate.set_defaults(handler=deterministic)
    sandbox = commands.add_parser("fixture")
    sandbox.add_argument("--executable", type=Path, required=True)
    sandbox.add_argument("--expected", required=True)
    sandbox.add_argument("--expect-decision", choices=("pass", "fail"), required=True)
    sandbox.set_defaults(handler=fixture)
    state = commands.add_parser("lifecycle")
    state.add_argument("--input", type=Path, required=True)
    state.add_argument("--event", required=True)
    state.add_argument("--controller-sha")
    state.add_argument("--output", type=Path, required=True)
    state.set_defaults(handler=lifecycle)
    record = commands.add_parser("record")
    record.add_argument("--deterministic", type=Path, required=True)
    record.add_argument("--request", type=Path, required=True)
    record.add_argument("--evidence", type=Path, action="append", default=[])
    record.add_argument("--controller-sha", required=True)
    record.add_argument("--candidate-sha", required=True)
    record.add_argument("--run-id", required=True)
    record.add_argument("--run-attempt", required=True)
    record.add_argument("--output", type=Path, required=True)
    record.set_defaults(handler=release_record)
    return result


def main() -> None:
    args = parser().parse_args()
    try:
        args.handler(args)
    except (QualificationError, OSError, ValueError, subprocess.SubprocessError) as exc:
        raise SystemExit(f"qualification failed: {exc}") from exc


if __name__ == "__main__":
    main()

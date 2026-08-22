# Factory accepted qualification controller

This public organization-policy repository is the trust root for Factory release
qualification. Factory candidates cannot change this workflow, its accepted
policy, its lifecycle ledger, or its secrets.

## Boundary

`.github/workflows/factory-accepted-qualification.yml` runs only by explicit
dispatch at an exact accepted commit and uses the protected `factory-release`
environment. A read-only fine-grained credential fetches the private Factory
candidate and previously accepted Factory oracle at exact full SHAs. The
credential is scoped to that one step, both remotes and credential configuration
are removed, and candidate content is never executed by the controller.

The accepted deterministic validator reads the candidate as data under isolated
Python. Semantic evaluation receives only a manifest-bound copy of declared
behavior files, renamed below a neutral non-repository directory. Candidate
hooks, MCP configuration, plugins, settings, instructions, workflows, scripts,
and tests are not copied. Copilot runs from that neutral directory with a clean
`COPILOT_HOME`, all hooks disabled, custom instructions disabled, built-in MCP
disabled, no plugins, read as its only tool, all tool URLs denied, remote export
disabled, and automatic update disabled. Its only network use is the pinned
Copilot client's inference channel; candidate-controlled executable surfaces
have no network path because they are never run.

The sandbox integration suite proves that the outer trusted supervisor accepts a
valid structured child response but rejects `os._exit(0)` and fake PASS output.
It also mounts an adversarial candidate hook and proves it remains inert. A
child exit code or stdout line is never itself release evidence.

## Required GitHub configuration

Create the `factory-release` environment in `clockgrove/.github`. Restrict its
deployment branch/tag policy to the protected controller ref and add required
reviewers if the current GitHub plan exposes that control. Add only:

- `FACTORY_QUALIFICATION_COPILOT_TOKEN`: a dedicated token with Copilot Requests
  read access and no repository write permissions.

Set the repository variable `FACTORY_FETCH_CREDENTIAL_MODE` to one of the two
accepted modes in `factory-controller/credential.json`:

- `personal-pat` (the current, non-Enterprise path): add
  `FACTORY_CANDIDATE_READ_TOKEN`, a fine-grained personal access token restricted
  to `clockgrove/factory` with Contents read and Metadata read only. The controller
  checks access to that exact repository and rejects visible classic write/admin
  scopes. Fine-grained PAT permission metadata is not introspectable at runtime,
  so bootstrap evidence must include a screenshot/export of its repository and
  permission selection. No Enterprise-only environment feature is required.
- `github-app`: create a Clockgrove-owned GitHub App installed only on `factory`,
  grant Contents read and Metadata read, set `FACTORY_QUALIFICATION_APP_ID`, and
  add `FACTORY_QUALIFICATION_APP_PRIVATE_KEY`. The pinned token action mints a
  repository-restricted installation token for each run; no long-lived fetch PAT
  is then needed.

Unsupported or unset modes fail closed. The qualification record names the mode,
never the credential. Migration is a reviewed configuration change: install and
test the App, add its ID/key, change the mode variable to `github-app`, run a
qualification, verify its attestation, then revoke the PAT. Rollback reverses the
mode only while the least-privilege PAT remains valid.

Factory itself receives neither secret. Protect `main` in this public repository
with required pull-request review and passing controller validation checks.

## Bootstrap and promotion

The checked-in lifecycle begins at `bootstrap_pending`, so the workflow cannot
issue a qualification record. Two organization owners outside the Factory
candidate-writer set must review the exact bootstrap commit, validate repository
access and secret-name evidence, run the adversarial CI, and record approval in a
GitHub Release. A second reviewed activation change applies `approve_bootstrap`,
records the reviewed trust-root SHA, and changes the ledger to `accepted`.
Factory pins the exact activation commit (which contains that ledger change) in
its secretless request workflow. This two-commit sequence avoids the impossible
and unsafe requirement for a Git commit to contain its own SHA.

Controller upgrades are qualified under the currently accepted controller.
After `qualify_upgrade`, owners merge the new immutable commit and apply
`activate_upgrade`; Factory updates its pin only in a separate reviewed PR. Old
records and commits are never rewritten.

## Disable, recover, and revoke

On suspected compromise, disable the workflow/environment and revoke both tokens
before investigation. Apply `detect_compromise`, rotate credentials, and either
restore the last uncompromised SHA or return to bootstrap. Revocation is an
explicit human change to the lifecycle ledger and a GitHub Release that names the
controller SHA, affected candidate SHAs and run IDs, reason, scope, and replacement.
The `revoked` state is terminal, and revoked SHAs are rejected before evaluation.

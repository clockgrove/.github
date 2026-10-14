# Contributing to Clockgrove

Read the target repository's README, AGENTS.md and contributor guidance before making a change. Search existing issues before opening a new one.

Set the native GitHub issue type explicitly:

- `Bug` for a standalone defect.
- `Feature` for a requested capability or Factory Objective.
- `Task` for a Work Item, maintenance, investigation or qualification. A corrective Work Item remains `Task`.

Use labels for independent information such as area, priority, phase or Factory role. Do not add redundant `bug`, `enhancement`, `feature` or `task` classification labels. Preserve required role labels such as `factory:objective` and `factory:work-item`.

Issue forms must set their top-level `type`. When creating an issue through a CLI or API, supply the type explicitly and verify the returned issue's type and labels. Do not assume a title or label assigned the type, and do not leave issues untyped when an appropriate native type is available.

An issue's type or Project placement does not authorize execution, spending or deployment. Follow the target repository's existing approval and delivery rules. Keep credentials, private source and raw agent transcripts out of public issues.

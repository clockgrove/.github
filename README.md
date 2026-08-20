# Clockgrove organization configuration

This repository contains organization-level GitHub configuration and the public Clockgrove organization profile.

## Copilot capability marketplace

`.github/plugin/marketplace.json` publishes the Clockgrove capability packages used by project repositories:

- `clockgrove-factory` — Director and engineering-management capabilities from `clockgrove/factory`;
- `clockgrove-skills` — reusable Clockgrove product/engineering skills from `clockgrove/skills`.

Target repositories enable the packages declaratively through `.github/copilot/settings.json`. The marketplace is distribution/configuration only; product authority remains in the target repository, Factory behavior remains in `clockgrove/factory`, and shared skill behavior remains in `clockgrove/skills`.

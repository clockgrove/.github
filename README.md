# Clockgrove organization configuration

This repository contains organization-level GitHub configuration and the public Clockgrove organization profile.

## Copilot capability marketplace

`.github/plugin/marketplace.json` publishes the Clockgrove capability packages used by project repositories:

- `clockgrove-factory` — Director and engineering-management capabilities from `clockgrove/factory`;
- `clockgrove-skills` — reusable Clockgrove product/engineering skills from `clockgrove/skills`.

Target repositories enable the packages declaratively through `.github/copilot/settings.json`. The marketplace is distribution/configuration only; product authority remains in the target repository, Factory behavior remains in `clockgrove/factory`, and shared skill behavior remains in `clockgrove/skills`.

## Release discipline

Versioned capability entries are pinned to full immutable commit SHAs, never moving `main` refs. `scripts/validate-marketplace.py` and the corresponding GitHub Actions check enforce the release inventory and pin format before changes are merged.

Consumer repositories may additionally pin the marketplace repository itself to a reviewed commit SHA so their complete capability resolution is reproducible.

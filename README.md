# Clockgrove organization configuration

This repository contains organization-level GitHub configuration and the public Clockgrove organization profile.

## Copilot capability marketplace

`.github/plugin/marketplace.json` publishes the Clockgrove capability packages used by project repositories:

- `clockgrove-factory` — Director and engineering-management capabilities from `clockgrove/factory`;
- `clockgrove-skills` — reusable Clockgrove product/engineering skills from `clockgrove/skills`.

The source repositories contain GitHub Copilot-compatible root `plugin.json` manifests. This repository is the shared marketplace catalog; Factory and Skills do not need to duplicate it.

Register and install the packages with GitHub Copilot CLI:

```bash
copilot plugin marketplace add clockgrove/.github
copilot plugin install clockgrove-factory@clockgrove
copilot plugin install clockgrove-skills@clockgrove
```

A plugin can also be installed directly from its repository without registering the marketplace:

```bash
copilot plugin install clockgrove/factory
copilot plugin install clockgrove/skills
```

Target repositories can enable the marketplace and packages declaratively through `.github/copilot/settings.json`. The marketplace is distribution/configuration only; product authority remains in the target repository, Factory behavior remains in `clockgrove/factory`, and shared skill behavior remains in `clockgrove/skills`.

## Release discipline

Versioned capability entries use the GitHub Copilot source object's `sha` field with a full immutable commit SHA, as recommended for reproducible installs. They never use a moving branch or tag. `scripts/validate-marketplace.py` and the corresponding GitHub Actions check enforce the release inventory and pin format before changes are merged.

Consumer repositories may additionally pin the marketplace repository itself to a reviewed commit SHA so their complete capability resolution is reproducible.

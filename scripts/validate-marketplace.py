#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT/'.github/plugin/marketplace.json'
data = json.loads(path.read_text())
errors: list[str] = []

def err(msg: str): errors.append(msg)

if data.get('name') != 'clockgrove': err('marketplace name mismatch')
if data.get('metadata', {}).get('version') != '1.0.0': err('marketplace release version must be 1.0.0')
plugins = data.get('plugins')
if not isinstance(plugins, list): err('plugins must be a list'); plugins = []
expected = {'clockgrove-factory': 'clockgrove/factory', 'clockgrove-skills': 'clockgrove/skills'}
seen = set()
for plugin in plugins:
    name = plugin.get('name')
    seen.add(name)
    if name not in expected:
        err(f'unexpected plugin {name}')
        continue
    if plugin.get('version') != '1.0.0': err(f'{name}: expected version 1.0.0')
    source = plugin.get('source', {})
    if source.get('source') != 'github': err(f'{name}: source must be github')
    if source.get('repo') != expected[name]: err(f'{name}: wrong repo')
    ref = source.get('ref')
    if not isinstance(ref, str) or not re.fullmatch(r'[0-9a-f]{40}', ref):
        err(f'{name}: source ref must be a full 40-character commit SHA')
    if 'sha' in source: err(f'{name}: obsolete source sha field is not GitHub Copilot compatible; use ref')
    unexpected = set(source) - {'source', 'repo', 'ref'}
    if unexpected: err(f'{name}: unexpected source fields: {sorted(unexpected)}')
if seen != set(expected): err(f'plugin inventory mismatch: {seen}')

if errors:
    print('Marketplace validation FAILED')
    for e in errors: print(f'- {e}')
    sys.exit(1)
print('Marketplace validation passed')
for plugin in plugins: print(f'- {plugin["name"]} {plugin["version"]} @ {plugin["source"]["ref"]}')

#!/usr/bin/env python3
"""
Pre-commit hook analyzer: checks staged files for new cross-tab imports or duplicate IDs.
Runs the Agent-2A analyzer in diff mode (heuristic: analyzes staged files and their imports).
Exits non-zero to block commit if violations found.
"""
import sys, subprocess, json, os, tempfile

# Get staged files
res = subprocess.run(['git','diff','--cached','--name-only'], capture_output=True, text=True)
files = [l for l in res.stdout.splitlines() if l.strip().endswith('.py')]
if not files:
    print('No staged python files; skipping Agent-2A precommit checks')
    sys.exit(0)

print('Agent-2A precommit: staged python files:', files)

# Run the analyzer (full run but we will inspect only staged files results)
analyzer = 'tools/analysis/agent2a_analysis.py'
if not os.path.exists(analyzer):
    print('Analyzer not found; skip')
    sys.exit(0)

# Run analyzer to produce JSON
subprocess.run(['python3', analyzer], check=True)
report = 'reports/agent2a/architecture_report.json'
if not os.path.exists(report):
    print('Analyzer did not produce report; failing')
    sys.exit(2)

with open(report) as f:
    data = json.load(f)

ids_by_file = data.get('ids_by_file', {})
# Build inverse map for quick staged checks
id_usage = {}
for f, ids in ids_by_file.items():
    for i in ids:
        id_usage.setdefault(i, []).append(f)

# Check duplicates among staged files
violations = False
for f in files:
    # check ids in this file
    ids = ids_by_file.get(f, [])
    for i in ids:
        users = id_usage.get(i, [])
        # if used in other files outside this file, flag
        other = [u for u in users if u!=f]
        if other:
            print(f"Precommit ERROR: ID '{i}' in staged file {f} is used in other files: {other}")
            violations = True

# Check cross-tab imports: simple heuristic using imports_by_file
imports_by_file = data.get('imports_by_file', {})
module_by_path = data.get('module_by_path', {})

for f in files:
    imports = imports_by_file.get(f, [])
    for imp in imports:
        # if import resolves to a different tab under financial_dashboard.tabs
        if imp.startswith('financial_dashboard.tabs'):
            # allow for same-file imports; flag cross-tab
            print(f"Precommit WARNING: Staged file {f} imports tab module {imp}; ensure this is intentional")
            # don't block on warning

if violations:
    print('Agent-2A precommit: violations found; aborting commit')
    sys.exit(4)
print('Agent-2A precommit: checks passed')
sys.exit(0)

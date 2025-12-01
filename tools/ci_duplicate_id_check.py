#!/usr/bin/env python3
"""
Interpret the analyzer JSON output and fail CI on duplicate IDs across tabs
or cross-tab imports found.
Usage: python tools/ci_duplicate_id_check.py path/to/architecture_report.json
"""
import sys, json

if len(sys.argv) < 2:
    print("Usage: ci_duplicate_id_check.py <architecture_report.json>")
    sys.exit(2)

path = sys.argv[1]
with open(path) as f:
    data = json.load(f)

ids_by_file = data.get('ids_by_file', {})
major_tabs = data.get('major_tabs', {})

# Build ID usage map
id_usage = {}
for f, ids in ids_by_file.items():
    for i in ids:
        id_usage.setdefault(i, []).append(f)

# Find duplicate IDs used in files belonging to different major tabs
duplicates = {i:files for i,files in id_usage.items() if len(files)>1}

# Cross-tab imports from architecture JSON (resolved_graph keys)
resolved_graph = data.get('resolved_graph', {})
# We treat any resolved_graph entries as potential cross imports; the analyzer
# already records which modules import which; for CI we will be conservative
cross_tab_warnings = []
for src, targets in resolved_graph.items():
    for t in targets:
        # naive heuristic: if both source and target are under financial_dashboard.tabs but different subfolders
        if 'financial_dashboard.tabs' in src and 'financial_dashboard.tabs' in t and src.split('.')[-1]!=t.split('.')[-1]:
            cross_tab_warnings.append((src,t))

err = False
if duplicates:
    print("ERROR: Found duplicate component IDs used in multiple files:")
    for i,files in duplicates.items():
        print(f" - ID '{i}' used in {len(files)} files: {files}")
    err = True

if cross_tab_warnings:
    print("ERROR: Potential cross-tab imports detected:")
    for s,t in cross_tab_warnings[:50]:
        print(f" - {s} -> {t}")
    err = True

if err:
    sys.exit(4)
print("ci_duplicate_id_check: OK")
sys.exit(0)

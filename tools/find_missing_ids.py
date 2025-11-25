#!/usr/bin/env python3
"""
Scan repository for Dash component IDs referenced in callbacks (Output/Input/State)
and compare against IDs declared in layout files and `layout_placeholders.py`.

Outputs a prioritized list of missing IDs with file locations and counts.
"""
import re
import json
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent

py_files = list(repo_root.rglob('*.py'))
html_files = list(repo_root.rglob('*.html'))
js_files = list(repo_root.rglob('*.js'))

# regexes
re_output = re.compile(r"Output\(\s*['\"]([^'\"]+)['\"]")
re_input = re.compile(r"Input\(\s*['\"]([^'\"]+)['\"]")
re_state = re.compile(r"State\(\s*['\"]([^'\"]+)['\"]")
re_id_attr = re.compile(r"id\s*=\s*['\"]([^'\"]+)['\"]")
re_dcc_store = re.compile(r"dcc\.Store\(\s*id\s*=\s*['\"]([^'\"]+)['\"]")

referenced = {}  # id -> {count, files, types}
declared = {}    # id -> {count, files}

def add_ref(id_, file, kind):
    d = referenced.setdefault(id_, {'count':0,'files':set(),'kinds':{}})
    d['count'] += 1
    d['files'].add(str(file))
    d['kinds'].setdefault(kind,0)
    d['kinds'][kind] += 1

def add_decl(id_, file):
    d = declared.setdefault(id_, {'count':0,'files':set()})
    d['count'] += 1
    d['files'].add(str(file))

# scan python files for Output/Input/State and dcc.Store
for p in py_files:
    try:
        txt = p.read_text(errors='ignore')
    except Exception:
        continue
    for m in re_output.finditer(txt):
        add_ref(m.group(1), p, 'Output')
    for m in re_input.finditer(txt):
        add_ref(m.group(1), p, 'Input')
    for m in re_state.finditer(txt):
        add_ref(m.group(1), p, 'State')
    for m in re_dcc_store.finditer(txt):
        add_decl(m.group(1), p)
    # also look for html.Div(id='...') usage
    for m in re_id_attr.finditer(txt):
        # heuristics: if file is layout or contains 'layout' in path, treat as declaration
        if 'layout' in p.name or '/tabs/' in str(p):
            add_decl(m.group(1), p)

# scan layout_placeholders specifically for declarations
lp = repo_root / 'financial_dashboard' / 'layout_placeholders.py'
if lp.exists():
    txt = lp.read_text(errors='ignore')
    for m in re_id_attr.finditer(txt):
        add_decl(m.group(1), lp)

# scan HTML files for id attributes
for p in html_files:
    try:
        txt = p.read_text(errors='ignore')
    except Exception:
        continue
    for m in re_id_attr.finditer(txt):
        add_decl(m.group(1), p)

# Now compute missing IDs
missing = []
for id_, info in referenced.items():
    if id_ not in declared:
        missing.append((id_, info))

# Sort by reference count desc
missing.sort(key=lambda x: x[1]['count'], reverse=True)

report = {
    'total_referenced_ids': len(referenced),
    'total_declared_ids': len(declared),
    'total_missing': len(missing),
    'missing': []
}

for id_, info in missing[:200]:
    report['missing'].append({
        'id': id_,
        'refs': info['count'],
        'kinds': info['kinds'],
        'files': sorted(list(info['files']))[:10]
    })

# write report
out = repo_root / 'reports' / 'missing_ids_report.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2))
print(f"Wrote report to: {out}")
print(json.dumps({'total_referenced': len(referenced),'total_declared': len(declared),'total_missing': len(missing)}, indent=2))

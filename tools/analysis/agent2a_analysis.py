"""
Agent-2A structural analysis script
Walks repository Python files, builds import graph, finds circular imports,
extracts Dash component IDs, dcc.Store IDs, module-level globals, and
produces several markdown reports for architecture, tab isolation, and
future-proof blueprint.

Run: python tools/analysis/agent2a_analysis.py
"""
import os
import ast
import re
import json
from collections import defaultdict, deque

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT_DIR = os.path.join(ROOT, 'reports', 'agent2a')
os.makedirs(OUT_DIR, exist_ok=True)

PY_EXTS = ('.py',)
EXCLUDE_DIRS = {'.venv_local', '.venv', '__pycache__', 'node_modules', '.git'}

file_index = []
module_by_path = {}
imports_by_file = defaultdict(list)
imported_by = defaultdict(set)
module_globals = defaultdict(list)
ids_by_file = defaultdict(set)
stores_by_file = defaultdict(set)

def is_excluded(path):
    parts = path.split(os.sep)
    return any(p in EXCLUDE_DIRS for p in parts)

# regex to find id= or id = or id= { for dict IDs; and dcc.Store id
ID_RE = re.compile(r"id\s*=\s*(?:\{[^}]*\}|\'([^\']+)\'|\"([^\"]+)\")")
# simple match for dcc.Store(id="...") or Store(id='...')
STORE_RE = re.compile(r"Store\s*\(\s*id\s*=\s*['\"]([^'\"]+)['\"]")
# pattern for dict-style pattern-matching ids: {"type": "rl-select-brief", "index": ...}
DICT_ID_RE = re.compile(r"\{\s*['\"]type['\"]\s*:\s*['\"]([^'\"]+)['\"]")

# Only scan core directories to reduce memory and avoid large unrelated files
scan_dirs = [
    os.path.join(ROOT, 'financial_dashboard'),
    os.path.join(ROOT, 'tools'),
    os.path.join(ROOT, 'tests')
]

for base in scan_dirs:
    if not os.path.isdir(base):
        continue
    for dirpath, dirnames, filenames in os.walk(base):
        if is_excluded(dirpath):
            continue
        for fn in filenames:
            if fn.endswith(PY_EXTS):
                path = os.path.join(dirpath, fn)
                rel = os.path.relpath(path, ROOT)
                file_index.append(rel)

# Parse files for imports, ids, globals
for rel in file_index:
    path = os.path.join(ROOT, rel)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            src = f.read()
    except Exception:
        continue
    # detect string IDs with regex
    for m in STORE_RE.finditer(src):
        stores_by_file[rel].add(m.group(1))
    for m in ID_RE.finditer(src):
        g1 = m.group(1)
        g2 = m.group(2)
        val = g1 or g2
        if val:
            ids_by_file[rel].add(val)
    for m in DICT_ID_RE.finditer(src):
        ids_by_file[rel].add(m.group(1))
    # AST parse for imports and module-level names
    try:
        tree = ast.parse(src, filename=rel)
    except Exception:
        continue
    # compute module name from path
    modname = rel.replace(os.sep, '.')
    if modname.endswith('.py'):
        modname = modname[:-3]
    module_by_path[rel] = modname
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports_by_file[rel].append(n.name)
                imported_by[n.name].add(rel)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module
            if mod:
                imports_by_file[rel].append(mod)
                imported_by[mod].add(rel)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            # collect module-level names considered 'globals'
            targets = []
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        targets.append(t.id)
            else:
                t = node.target
                if isinstance(t, ast.Name):
                    targets.append(t.id)
            # simplistic heuristic: uppercase or leading underscore often globals/config
            for name in targets:
                if name.isupper() or name.startswith('_'):
                    module_globals[rel].append(name)

# Build import graph (module name nodes)
graph = defaultdict(set)
for rel, mods in imports_by_file.items():
    src_mod = module_by_path.get(rel, rel)
    for m in mods:
        graph[src_mod].add(m)

# Detect cycles using DFS on graph of modules present in module_by_path
# We will only consider imports that resolve to files inside repo
modname_to_rel = {v: k for k, v in module_by_path.items()}

def resolve_mod(m):
    # exact match
    if m in modname_to_rel:
        return m
    # try prefix match for submodule imports
    for k in modname_to_rel:
        if k.endswith(m) or k.startswith(m + '.'):
            return k
    return None

resolved_graph = defaultdict(set)
for src, targets in graph.items():
    for t in targets:
        r = resolve_mod(t)
        if r:
            resolved_graph[src].add(r)

# Find cycles
visited = set()
stack = []
cycles = []

def dfs(node, path):
    if node in path:
        idx = path.index(node)
        cycles.append(path[idx:] + [node])
        return
    path.append(node)
    for neigh in resolved_graph.get(node, []):
        dfs(neigh, path.copy())

for node in resolved_graph:
    dfs(node, [])

# Gather tab modules under financial_dashboard/tabs
tabs_dir = os.path.join(ROOT, 'financial_dashboard', 'tabs')
tab_files = []
if os.path.isdir(tabs_dir):
    for dp, dns, fns in os.walk(tabs_dir):
        if is_excluded(dp):
            continue
        for fn in fns:
            if fn.endswith('.py'):
                rel = os.path.relpath(os.path.join(dp, fn), ROOT)
                tab_files.append(rel)

# For each major tab specified by the user, attempt to match files and gather IDs and stores and cross-imports
major_tabs = {
    'market_trends': [],
    'volatility_lab': [],
    'options_lab': [],
    'strategy_lab': [],
    'portfolio': [],
    'market_forecast': [],
    'research_lab': [],
    'attribution_lab': []
}

for rel in tab_files:
    name = os.path.basename(rel).lower()
    for key in list(major_tabs.keys()):
        if key in name or key.replace('_','') in name:
            major_tabs[key].append(rel)

# Produce reports
arch = {
    'root': ROOT,
    'total_py_files': len(file_index),
}

# Write architecture report
with open(os.path.join(OUT_DIR, 'architecture_report.json'), 'w') as f:
    json.dump({
        'file_index': file_index,
        'module_by_path': module_by_path,
        'imports_by_file': dict(imports_by_file),
        'module_globals': dict(module_globals),
        'ids_by_file': {k: list(v) for k, v in ids_by_file.items()},
        'stores_by_file': {k: list(v) for k, v in stores_by_file.items()},
        'resolved_graph': {k: list(v) for k, v in resolved_graph.items()},
        'cycles': cycles,
        'major_tabs': major_tabs
    }, f, indent=2)

# Build human-friendly architecture markdown
lines = []
lines.append('# System Architecture Report\n')
lines.append('Repository root: ' + ROOT + '\n')
lines.append(f'Total Python files scanned: {len(file_index)}\n')
lines.append('## Top-level folders (sample)\n')
for item in os.listdir(ROOT):
    lines.append('- ' + item)
lines.append('\n')
lines.append('## Detected cycles (import circulars)\n')
if cycles:
    for c in cycles:
        lines.append('- Cycle: ' + ' -> '.join(c))
else:
    lines.append('- No cycles detected among resolvable internal modules')

# Cross-tab imports
lines.append('\n## Cross-tab imports (tab file imports modules outside its folder)\n')
for tab, files in major_tabs.items():
    lines.append(f'### Tab: {tab} (files: {len(files)})')
    cross = set()
    for rel in files:
        for imp in imports_by_file.get(rel, []):
            r = resolve_mod(imp)
            if r and not r.startswith('financial_dashboard.tabs.' + tab):
                cross.add(imp)
    if cross:
        for c in sorted(cross):
            lines.append(f'- {c}')
    else:
        lines.append('- No obvious cross-tab imports detected')
lines.append('\n')

# IDs collisions: find IDs used in more than one file
id_usage = defaultdict(list)
for f, ids in ids_by_file.items():
    for i in ids:
        id_usage[i].append(f)

lines.append('## Shared component IDs (potential leaks)\n')
shared_ids = {i:files for i, files in id_usage.items() if len(files) > 1}
if shared_ids:
    for i, files in shared_ids.items():
        lines.append(f'- ID `{i}` used in {len(files)} files:')
        for f in files:
            lines.append('  - ' + f)
else:
    lines.append('- No duplicated simple string IDs found')

# Stores used
lines.append('\n## dcc.Store keys by file\n')
for f, stores in stores_by_file.items():
    if stores:
        lines.append(f'- {f}: {sorted(list(stores))}')

# Globals per file
lines.append('\n## Module-level globals (heuristic)\n')
for f, globs in module_globals.items():
    if globs:
        lines.append(f'- {f}: {globs}')

with open(os.path.join(OUT_DIR, 'architecture_report.md'), 'w') as f:
    f.write('\n'.join(lines))

# Tab isolation report
tab_lines = []
tab_lines.append('# Tab Isolation Report\n')
for tab, files in major_tabs.items():
    tab_lines.append(f'## {tab}\n')
    if not files:
        tab_lines.append('- No files matched this tab (search by filename)\n')
        continue
    tab_lines.append('- Files:')
    for rel in files:
        tab_lines.append('  - ' + rel)
    # gather IDs and stores
    ids = set()
    stores = set()
    globals_ = set()
    imports_ = set()
    for rel in files:
        ids.update(ids_by_file.get(rel, set()))
        stores.update(stores_by_file.get(rel, set()))
        for g in module_globals.get(rel, []):
            globals_.add(g)
        for imp in imports_by_file.get(rel, []):
            imports_.add(imp)
    tab_lines.append(f'- Component IDs: {sorted(list(ids))}')
    tab_lines.append(f'- Stores: {sorted(list(stores))}')
    tab_lines.append(f'- Module-level globals: {sorted(list(globals_))}')
    # cross imports into other tabs
    crossmods = [imp for imp in imports_ if resolve_mod(imp) and resolve_mod(imp) not in [module_by_path.get(r) for r in files]]
    tab_lines.append(f'- External imports count: {len(crossmods)}')
    if crossmods:
        for cm in sorted(crossmods):
            tab_lines.append('  - ' + cm)
    tab_lines.append('\n')

with open(os.path.join(OUT_DIR, 'tab_isolation_report.md'), 'w') as f:
    f.write('\n'.join(tab_lines))

# Blueprint and safety plan (high-level templates)
with open(os.path.join(OUT_DIR, 'structural_blueprint.md'), 'w') as f:
    f.write('# Structural Isolation Blueprint\n\n')
    f.write('Proposal:\n')
    f.write('- Per-tab package under `financial_dashboard/tabs/<tab_name>/` with:\n')
    f.write('  - `layout.py` (creates layout only)\n')
    f.write('  - `callbacks.py` (register_callbacks(app) only)\n')
    f.write('  - `components.py` (UI helper components)\n')
    f.write('  - `data.py` (tab-local data loaders)\n')
    f.write('- No cross-imports between tabs: use dependency injection via a `services` module.\n')
    f.write('- Namespacing IDs: prefix all IDs with tab shortnames (e.g., `mt-`, `rl-`).\n')
    f.write('- Central tab registry: a single `callbacks.register_all_callbacks` drives per-tab `register_callbacks` and tracks registered tabs to prevent duplicates.\n')

with open(os.path.join(OUT_DIR, 'safety_plan.md'), 'w') as f:
    f.write('# System Safety Plan\n\n')
    f.write('Measures to prevent callback duplication and cross-tab leakage:\n')
    f.write('- Enforce `register_callbacks(app)` signature per tab.\n')
    f.write('- Static pre-merge hook: run analyzer to fail on duplicated IDs or cross-tab imports.\n')
    f.write('- CI job: run `python -m tools.analysis.agent2a_analysis` and block on non-zero exit if leaks found.\n')
    f.write('- Lint rules: ruff + custom flake plugin to prohibit imports from `financial_dashboard.tabs.*` across tabs.\n')
    f.write('- Runtime guard: app._registered_tabs set on app instance (already present) plus check to prevent re-registration.\n')

# Completion marker
with open(os.path.join(OUT_DIR, 'COMPLETION_MARKER.txt'), 'w') as f:
    f.write('AGENT-2A analysis complete. Reports generated in reports/agent2a/')

print('Analysis complete. Reports written to:', OUT_DIR)

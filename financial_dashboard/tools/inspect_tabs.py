"""
Inspector: attempt to import each module in `tabs/` and report whether it exposes `layout` and `register_callbacks`.
Run: python3 tools/inspect_tabs.py
"""
import importlib.util
import os
import sys
import traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TABS_DIR = os.path.join(ROOT, 'tabs')

sys.path.insert(0, ROOT)

results = []
for fn in sorted(os.listdir(TABS_DIR)):
    if not fn.endswith('.py') or fn.startswith('__'):
        continue
    name = os.path.splitext(fn)[0]
    path = os.path.join(TABS_DIR, fn)
    info = {'module': name, 'path': path, 'imported': False, 'has_layout': False, 'layout_callable': False, 'has_register_callbacks': False, 'error': None}
    try:
        spec = importlib.util.spec_from_file_location(f'Dash.tabs.{name}', path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        info['imported'] = True
        if hasattr(mod, 'layout'):
            info['has_layout'] = True
            info['layout_callable'] = callable(getattr(mod, 'layout'))
            # Try to call layout with common signature if callable
            try:
                _ = mod.layout() if info['layout_callable'] else None
            except TypeError:
                # maybe requires is_tab arg
                try:
                    _ = mod.layout(is_tab=True)
                except Exception as e:
                    info['error'] = f'layout call failed: {e}'
            except Exception as e:
                info['error'] = f'layout call raised: {e}'
        if hasattr(mod, 'register_callbacks'):
            info['has_register_callbacks'] = True
    except Exception as e:
        info['error'] = traceback.format_exc().splitlines()[-1]
    results.append(info)

print("Tab import summary:\n")
for r in results:
    print(f"- {r['module']}: imported={r['imported']} layout={r['has_layout']} callable={r['layout_callable']} register_callbacks={r['has_register_callbacks']} error={r['error']}")

# Save report to file
out = os.path.join(ROOT, 'tools', 'inspect_tabs_report.txt')
with open(out, 'w') as f:
    for r in results:
        f.write(f"{r['module']}: imported={r['imported']} layout={r['has_layout']} callable={r['layout_callable']} register_callbacks={r['has_register_callbacks']} error={r['error']}\n")

print('\nReport written to', out)

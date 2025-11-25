import importlib, pkgutil, traceback, sys, os

sys.path.insert(0, os.getcwd())
bad = {}

# The prompt suggested 'dash/tabs', but the workspace has 'financial_dashboard/tabs'
# I will check 'financial_dashboard/tabs'
search_path = 'financial_dashboard/tabs'

if not os.path.exists(search_path):
    print(f"Path {search_path} does not exist")
    sys.exit(0)

for finder, name, ispkg in pkgutil.iter_modules([search_path]):
    try:
        mod = importlib.import_module("financial_dashboard.tabs." + name)
        # Check for create_layout or layout attribute
        if not (hasattr(mod, "create_layout") or hasattr(mod, "layout")):
             bad[name] = "Missing create_layout or layout"
    except Exception as e:
        bad[name] = traceback.format_exc()

print(len(bad))
for k, v in bad.items():
    print("MODULE:", k)
    print(v)

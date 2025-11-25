import json
import logging
import os
import sys

sys.path.insert(0, os.getcwd())

# Silence noisy logs so output stays valid JSON
logging.basicConfig(level=logging.ERROR)

out = {}
try:
    from financial_dashboard.app import create_app
    app = create_app()
    callback_map = getattr(app, "callback_map", {})
    out["callback_map_len"] = len(callback_map)
    out["callback_map_keys"] = list(callback_map.keys())[:500]
except Exception as exc:
    out["app_import_err"] = str(exc)

print(json.dumps(out, indent=2))

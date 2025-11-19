import sys
import json
import importlib
import os
sys.path.insert(0, r'C:\Aarav\fin_env')
out = {}
# shared job registry
try:
    import _shared as SH
    out['jobs'] = {k: v.get('status') for k, v in SH.JOBS.items()}
    out['results_present'] = bool(SH.RESULTS_CACHE.get('results'))
    out['results_keys'] = list(SH.RESULTS_CACHE.get('results').keys()) if SH.RESULTS_CACHE.get('results') else None
except Exception as e:
    out['shared_error'] = str(e)

# debug log
dbg_path = r'C:\Aarav\fin_env\forecast_debug.log'
if os.path.exists(dbg_path):
    try:
        out['debug_log'] = open(dbg_path, 'r', encoding='utf-8').read()
    except Exception as e:
        out['debug_log_error'] = str(e)
else:
    out['debug_log'] = None

# inspect modules
try:
    mf = importlib.import_module('Gradio.market_forecast')
    out['forecast_file'] = getattr(mf, '__file__', None)
    out['forecast_has_run_forecast_for_ticker'] = hasattr(mf, 'run_forecast_for_ticker')
    out['forecast_exports'] = [n for n in dir(mf) if not n.startswith('_')]
except Exception as e:
    out['forecast_import_error'] = str(e)

try:
    mt = importlib.import_module('Gradio.market_trends')
    out['trends_file'] = getattr(mt, '__file__', None)
    out['trends_has_run_full_analysis'] = hasattr(mt, 'run_full_analysis')
    out['trends_exports_sample'] = [n for n in dir(mt) if not n.startswith('_')][:60]
except Exception as e:
    out['trends_import_error'] = str(e)

print(json.dumps(out, indent=2, default=str))

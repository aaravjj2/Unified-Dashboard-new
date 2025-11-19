from importlib.machinery import SourceFileLoader
import os
proj_root = os.path.abspath(os.path.dirname(__file__))
SH = SourceFileLoader('Dash._shared', os.path.join(proj_root, '_shared.py')).load_module()
import json
print('JOBS keys:', list(SH.JOBS.keys()))
print('RESULTS_CACHE loaded_at:', SH.RESULTS_CACHE.get('loaded_at'))
print('RESULTS_CACHE keys:', list(SH.RESULTS_CACHE.get('results').keys()) if SH.RESULTS_CACHE.get('results') else None)
print('RESULTS_CACHE sample:', json.dumps(SH.RESULTS_CACHE.get('results') and (SH.RESULTS_CACHE.get('results').get('detailed') or SH.RESULTS_CACHE.get('results').get('tidy') or SH.RESULTS_CACHE.get('results').get('brief_json') or {}), indent=2, default=str))

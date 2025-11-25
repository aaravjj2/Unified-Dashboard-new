import time
print('Starting smoke tests')
import importlib.util
import os
base = os.path.dirname(__file__)
sh_path = os.path.join(base, '_shared.py')
spec = importlib.util.spec_from_file_location('Dash._shared', sh_path)
SH = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SH)
print('Loaded SH from', sh_path)

# 1) schedule a quick background job that writes RESULTS_CACHE

def quick_job():
    time.sleep(1)
    SH.RESULTS_CACHE['results'] = {'ok': True, 'detailed': [{'ticker': 'SMOKE', 'forecast': 'simulated'}]}
    return SH.RESULTS_CACHE['results']

print('Starting quick background job')
job_id = SH.start_background_job(quick_job, args=(), job_name='smoke_quick')
print('Job queued:', job_id)

# poll until done
for i in range(20):
    j = SH.JOBS.get(job_id)
    if j is None:
        print('Job disappeared')
        break
    status = j.get('status')
    print('Status:', status)
    if status in ('done', 'error'):
        break
    time.sleep(0.5)

print('Final job status:', SH.JOBS.get(job_id))
print('RESULTS_CACHE:', SH.RESULTS_CACHE.get('results'))

# 2) call dashboard header callback directly if available
try:
    import importlib.util
    md_path = os.path.join(base, 'market_dashboard.py')
    spec = importlib.util.spec_from_file_location('market_dashboard', md_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print('Imported market_dashboard OK')
    fn = getattr(mod, '_run_trends_from_dashboard', None)
    if fn is None:
        print('dashboard callback not found')
    else:
        print('Calling dashboard callback...')
        out = fn(1)
        print('Callback returned:', out)
except Exception as e:
    print('Failed to import or call dashboard callback:', e)
    import traceback; traceback.print_exc()

print('Smoke tests complete')

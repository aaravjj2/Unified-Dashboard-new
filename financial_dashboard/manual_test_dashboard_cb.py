from importlib.machinery import SourceFileLoader
import time
import re
import os
proj_root = os.path.abspath(os.path.dirname(__file__))
SH = SourceFileLoader('Dash._shared', os.path.join(proj_root, '_shared.py')).load_module()
md = SourceFileLoader('market_dashboard', os.path.join(proj_root, 'market_dashboard.py')).load_module()
print('Calling dashboard callback to enqueue trends job...')
res = md._run_trends_from_dashboard(1)
print('Callback returned:', res)
m = re.search(r'job_[0-9]+', res or '')
if not m:
    print('No job id found; RESULTS_CACHE now:', SH.RESULTS_CACHE)
    raise SystemExit(0)
job_id = m.group(0)
print('Watching job id:', job_id)
for i in range(120):
    job = SH.JOBS.get(job_id)
    print(i, job and job.get('status'))
    if job and job.get('status') in ('done','error'):
        break
    time.sleep(0.5)
print('\nFinal job record:')
print(SH.JOBS.get(job_id))
print('\nRESULTS_CACHE:')
print(SH.RESULTS_CACHE)

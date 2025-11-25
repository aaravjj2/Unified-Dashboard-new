from importlib.machinery import SourceFileLoader
import time
import re

# Load shared and dashboard by path
SH = SourceFileLoader('Dash._shared', r'C:\Aarav\fin_env\Dash\_shared.py').load_module()
import os
proj_root = os.path.abspath(os.path.dirname(__file__))
md = SourceFileLoader('market_dashboard', os.path.join(proj_root, 'market_dashboard.py')).load_module()

print('Calling dashboard callback to enqueue trends job...')
res = md._run_trends_from_dashboard(1)
print('Callback returned:', res)

m = re.search(r'job_[0-9]+', res or '')
if not m:
    print('No job id found in callback return; exiting')
    raise SystemExit(2)
job_id = m.group(0)
print('Watching job id:', job_id)

# poll JOBS until done or timeout
for i in range(60):
    job = SH.JOBS.get(job_id)
    print(i, job and job.get('status'))
    if job and job.get('status')=='done':
        break
    time.sleep(0.5)

job = SH.JOBS.get(job_id)
print('\nFinal job record:')
print(job)
print('\nRESULTS_CACHE:')
print(SH.RESULTS_CACHE)

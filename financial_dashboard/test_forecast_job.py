from importlib.machinery import SourceFileLoader
import time

from importlib.machinery import SourceFileLoader
import os
proj_root = os.path.abspath(os.path.dirname(__file__))
SH = SourceFileLoader('Dash._shared', os.path.join(proj_root, '_shared.py')).load_module()
# Use the mt_mod from SH
print('mt_mod present:', getattr(SH, 'mt_mod', None) is not None)
print('Has run_forecast:', getattr(getattr(SH, 'mt_mod', None), 'run_forecast', None) is not None)

# enqueue a job via start_background_job
def target(tickers, horizon):
    if SH.mt_mod is not None and hasattr(SH.mt_mod, 'run_forecast'):
        return SH.mt_mod.run_forecast(tickers, horizon=horizon)
    # fallback simulated
    import time
    time.sleep(1)
    return {'ok': True, 'detailed': [{'ticker': t, 'forecast':'simulated', 'horizon': horizon} for t in tickers]}

job_id = SH.start_background_job(target, args=(['AAPL','MSFT'], 7), job_name='manual_test_forecast')
print('Queued job:', job_id)

# poll
for i in range(60):
    job = SH.JOBS.get(job_id)
    print(i, job and job.get('status'))
    if job and job.get('status') in ('done','error'):
        break
    time.sleep(0.5)

print('\nJOB record:')
print(SH.JOBS.get(job_id))
print('\nRESULTS_CACHE:')
print(SH.RESULTS_CACHE)

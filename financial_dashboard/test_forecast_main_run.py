from importlib.machinery import SourceFileLoader
import time
import os
proj_root = os.path.abspath(os.path.dirname(__file__))
SH = SourceFileLoader('Dash._shared', os.path.join(proj_root, '_shared.py')).load_module()
forecast_tab = SourceFileLoader('market_forecast', os.path.join(proj_root, 'tabs', 'market_forecast.py')).load_module()

# Build a small wrapper that reuses the job_target logic defined inside the tab
# We call the same logic inline, but via a background job to mimic UI behavior.

def wrapper():
    # pick some tickers
    tickers=['AAPL','MSFT']
    horizon=7
    # reuse tab's job_target by copying its code path: call mt.main() if available
    mt = getattr(SH, 'mt_mod', None)
    if mt is None:
        return {'ok': False, 'error': 'no mt_mod'}
    if hasattr(mt, 'run_forecast'):
        return mt.run_forecast(tickers, horizon=horizon)
    if hasattr(mt, 'main'):
        import sys
        prev = sys.argv
        sys.argv = [prev[0]] + ['--tickers'] + tickers + ['--period','1y','--interval','1d']
        try:
            mt.main()
        finally:
            sys.argv = prev
        if hasattr(SH, 'load_cached_results_from_outputs'):
            loaded = SH.load_cached_results_from_outputs()
            return {'ok': True, 'detailed': loaded.get('detailed') if loaded.get('detailed') else loaded.get('tidy') if loaded.get('tidy') else [{'notes': 'no detailed output'}]}
    return {'ok': False, 'error': 'no entrypoint'}

jid = SH.start_background_job(wrapper, job_name='test_forecast_main')
print('queued', jid)
for i in range(300):
    job = SH.JOBS.get(jid)
    print(i, job and job.get('status'))
    if job and job.get('status') in ('done','error'):
        break
    time.sleep(0.5)
print('final job record:', SH.JOBS.get(jid))
print('RESULTS_CACHE:', SH.RESULTS_CACHE)

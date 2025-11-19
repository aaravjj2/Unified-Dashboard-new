"""Simulate the dashboard 'Run Trends Analysis' action by queuing the same job
used by the Trends tab. This lets us test the dashboard-side orchestration
without a browser.
"""
import time
import os
import importlib.util
# load shared
proj_root = os.path.abspath(os.path.dirname(__file__))
spec = importlib.util.spec_from_file_location('Dash._shared', os.path.join(proj_root, '_shared.py'))
SH = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SH)
mt = getattr(SH, 'mt_mod', None)
print('SH loaded. mt_mod present?', mt is not None)
if mt is None:
    raise SystemExit('No mt_mod available')
# pick default tickers (same as dashboard default)
DEFAULT_TICKERS = ['NVDA','AAPL','MSFT','GOOGL','META','AMZN','TSLA','INTC','AMD','AVGO','NTCL','SPY','QQQ','XLK','LZMH']
period = '1y'
# Re-create job_target from the Trends tab (safe-call style)
def job_target(tickers, period, no_options, no_news, use_cache_only):
    try:
        mt = SH.mt_mod
        # Prefer run_full_analysis
        if mt is not None and hasattr(mt, 'run_full_analysis'):
            return mt.run_full_analysis(tickers, period=period, interval='1d', options_topn=3, no_options=no_options, no_news=no_news, use_cache_only=use_cache_only)
        # else, try CLI main()
        if mt is not None and hasattr(mt, 'main'):
            import sys
            prev_argv = sys.argv
            sys.argv = [prev_argv[0]] + ['--tickers'] + tickers + ['--period', period or '1y', '--interval', '1d']
            try:
                mt.main()
            finally:
                sys.argv = prev_argv
            loaded = SH.load_cached_results_from_outputs() if hasattr(SH, 'load_cached_results_from_outputs') else None
            if loaded:
                return {'ok': True, 'detailed': loaded.get('detailed') or loaded.get('tidy') or [], 'tidy': loaded.get('tidy') or loaded.get('detailed') or [], 'brief_json': loaded.get('brief_json'), 'brief_text': loaded.get('brief_text')}
        # fallback
        rows = []
        for t in tickers:
            rows.append({'ticker': t, 'composite_score': None, 'notes': 'no mt_mod'})
        return {'ok': True, 'detailed': rows, 'tidy': rows, 'prices': {}}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'trace': getattr(e, '__traceback__', str(e))}

print('Queuing job for tickers:', DEFAULT_TICKERS)
job_id = SH.start_background_job(job_target, args=(DEFAULT_TICKERS, period, False, False, False), job_name='simulate_dashboard_run')
print('Job queued:', job_id)
# Poll
while True:
    job = SH.JOBS.get(job_id)
    if not job:
        print('Job missing from registry')
        break
    status = job.get('status')
    print('Status:', status)
    if status in ('done', 'error'):
        print('Result:', job.get('result'))
        break
    time.sleep(2)
# List outputs in outputs/ for inspection
out_root = getattr(SH, 'OUT_ROOT', os.path.join(os.path.dirname(__file__), '..', 'outputs'))
print('\nOutputs under', out_root)
for root,dirs,files in os.walk(out_root):
    for f in files:
        print('-', os.path.join(root,f))
print('\nDone')

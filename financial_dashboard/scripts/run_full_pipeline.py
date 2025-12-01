"""Run the full orchestrator pipeline with production-like settings.

Usage: python Dash/scripts/run_full_pipeline.py
"""
import os
import glob
import json
import sys

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.pipeline.orchestrator import run_monthly_pipeline

data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
files = sorted(glob.glob(os.path.join(data_dir, 'features_*.csv')) + glob.glob(os.path.join(data_dir, 'features_*.parquet')))
if not files:
    print('No features files found in Dash/data. Aborting full run.')
    raise SystemExit(1)

latest = files[-1]
print('Using features file', latest)
out_dir = os.path.join(os.path.dirname(__file__), '..', 'models', 'full_run')
meta = run_monthly_pipeline(latest, features=['ret_3m','ret_6m','vol30','rsi14'], target='ret_1m', out_dir=out_dir, embeddings_kwargs={'epochs':20,'overwrite':True})
print(json.dumps(meta, indent=2))

"""Run a small smoke orchestrator pipeline (short epochs) and print meta JSON.

Usage: python3 scripts/run_smoke_pipeline.py
"""
import os
import glob
import json
import sys

# Ensure repo root is on sys.path for direct script execution
# workspace root is two levels up from Dash/scripts (workspace root = /mnt/c/Aarav/fin_env)
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.pipeline.orchestrator import run_monthly_pipeline

data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
files = sorted(glob.glob(os.path.join(data_dir, 'features_*.csv')) + glob.glob(os.path.join(data_dir, 'features_*.parquet')))
if not files:
    print('No features files found in Dash/data. Aborting smoke run.')
    raise SystemExit(1)

latest = files[-1]
print('Using features file', latest)
out_dir = os.path.join(os.path.dirname(__file__), '..', 'models', 'preview')
meta = run_monthly_pipeline(latest, features=['ret_3m','ret_6m','vol30','rsi14'], target='ret_1m', out_dir=out_dir, embeddings_kwargs={'epochs':3,'overwrite':True})
print(json.dumps(meta, indent=2))

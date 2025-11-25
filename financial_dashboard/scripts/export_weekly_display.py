#!/usr/bin/env python3
"""Export enriched weekly picks to a CSV for review.

This script adjusts sys.path so modules like `_shared` resolve (the codebase
uses top-level imports), imports the weekly_picks tab enrichment, and writes
the resulting DataFrame to `outputs/weekly_display_<timestamp>.csv`.

Run under Doppler (to inject secrets) and the project venv:
  source /mnt/c/Aarav/fin_env/.venv_local/bin/activate
  doppler run --project dash --config dev -- python3 financial_dashboard/scripts/export_weekly_display.py
"""
import sys
import os
import datetime

# Ensure the financial_dashboard directory is on sys.path so imports like
# `import _shared` used by the tabs package resolve to financial_dashboard/_shared.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from tabs import weekly_picks
except Exception as e:
    print('Failed importing weekly_picks:', e)
    raise

df, err, summary = weekly_picks._load_and_enrich_picks()
if err:
    print('Error enriching picks:', err)
    sys.exit(1)

out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'outputs'))
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, f'weekly_display_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
df.to_csv(out_path, index=False)
print('Wrote display CSV:', out_path)
print(df.head().to_string())

"""Run the Monthly Picks loader standalone

Usage: python scripts/run_monthly.py

This will import the monthly_picks module and print the CSV path and a small
preview (head) so you can confirm the data outside the Dash UI.
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tabs import monthly_picks

p = monthly_picks._find_latest_picks()
print('Found picks CSV:', p)
if p and os.path.exists(p):
    df, p2 = monthly_picks._load_picks_df(p)
    if df is not None:
        print('Rows:', len(df))
        print(df.head().to_string())
    else:
        print('Failed to load picks:', p2)
else:
    print('No picks CSV found')

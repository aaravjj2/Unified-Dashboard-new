#!/usr/bin/env python3
"""Debug GROQ recommendation"""

from financial_dashboard.tabs.options_lab.ml_recommendations import get_groq_recommendation
from financial_dashboard.utils.load_keys_env import load_keys_env

load_keys_env()

rec = get_groq_recommendation(
    ticker="AAPL",
    spot_price=150.0,
    options_data={'test': 'data'}
)

print(f"Length: {len(rec) if rec else 0}")
print(f"Type: {type(rec)}")
print(f"Content:\n{rec}")

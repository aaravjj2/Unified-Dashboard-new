#!/usr/bin/env python3
"""Test if register_callbacks can be called"""
import sys
print("TEST: Starting...", flush=True)

from financial_dashboard.app import create_app

print("TEST: Created app", flush=True)
app = create_app()

print("TEST: Loading market_trends module", flush=True)
from financial_dashboard.tabs import market_trends

print("TEST: About to call register_callbacks", flush=True)
sys.stdout.flush()
sys.stderr.flush()

market_trends.register_callbacks(app)

print("TEST: register_callbacks completed!", flush=True)

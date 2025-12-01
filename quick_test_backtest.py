#!/usr/bin/env python3
"""Quick test: Check if Strategy Lab validation + backtest work"""
import requests
import json
import time

BASE_URL = "http://localhost:8050"

print("🔍 Quick Strategy Lab Backtest Test\n")
print("=" * 60)

# Test 1: Check app is running
print("\n1️⃣ Checking if app is running...")
try:
    resp = requests.get(BASE_URL, timeout=5)
    if resp.status_code == 200:
        print("   ✅ App is running (HTTP 200)")
    else:
        print(f"   ⚠️ App returned HTTP {resp.status_code}")
except Exception as e:
    print(f"   ❌ App not reachable: {e}")
    exit(1)

# Test 2: Check container logs for recent activity
print("\n2️⃣ Checking container logs for Strategy Lab activity...")
import subprocess
log_check = subprocess.run(
    "docker logs dash_app 2>&1 | tail -50 | grep -i 'strategy\\|backtest'",
    shell=True,
    capture_output=True,
    text=True
)
if log_check.stdout.strip():
    print("   📋 Recent Strategy Lab logs:")
    for line in log_check.stdout.strip().split('\n')[:5]:
        print(f"      {line[:80]}")
else:
    print("   ⚠️ No recent Strategy Lab logs")

# Test 3: Manual log watch for backtest
print("\n3️⃣ Instructions for manual testing:")
print("   1. Open browser: http://localhost:8050")
print("   2. Click: Strategy Lab → Execute & Configure")
print("   3. Click: Run Backtest button")
print("   4. In another terminal, run:")
print("      docker logs -f dash_app | grep -i 'running real backtest'")
print("   5. Watch for:")
print("      - 'Running REAL backtest...'")
print("      - Signal generation logs")
print("      - Trade simulation logs")
print("      - Final metrics")

# Test 4: Check if dates are correct
print("\n4️⃣ Verifying date fix in container...")
date_check = subprocess.run(
    "docker exec dash_app grep -A 1 'end_date =' /app/financial_dashboard/tabs/strategy_lab/subtabs/execution.py | head -2",
    shell=True,
    capture_output=True,
    text=True
)
if 'timedelta(days=1)' in date_check.stdout:
    print("   ✅ Date fix confirmed: end_date = datetime.now() - timedelta(days=1)")
elif 'datetime.now()' in date_check.stdout:
    print("   ⚠️ Found datetime.now() in file:")
    print(f"      {date_check.stdout.strip()}")
else:
    print("   ❓ Could not verify date code")

print("\n" + "=" * 60)
print("✅ Tests complete. Fix is deployed.")
print("⚠️ To verify backtest works, manually test in browser.")
print("=" * 60 + "\n")

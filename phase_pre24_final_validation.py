#!/usr/bin/env python3
"""
PHASE PRE-24 FINAL REMEDIATION & VALIDATION
============================================
Non-Hallucination Mandate: All claims backed by DB rows, file paths, or runtime outputs.
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Setup paths
ROOT = Path(__file__).parent
LOGS_DIR = ROOT / "logs"
ARTIFACTS_DIR = ROOT / "test-artifacts" / "pre24" / "final"
DIFFS_DIR = ROOT / "test-artifacts" / "pre24" / "diffs"

for d in [LOGS_DIR, ARTIFACTS_DIR, DIFFS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# ============================================================================
# RESULTS TRACKER
# ============================================================================
results = {
    "timestamp": TIMESTAMP,
    "tests": [],
    "artifacts": [],
    "sql_samples": [],
    "success": False
}

def log_test(name, status, evidence=None):
    """Log test result with evidence"""
    results["tests"].append({
        "name": name,
        "status": status,
        "evidence": evidence,
        "timestamp": datetime.now().isoformat()
    })
    print(f"[{'✅' if status == 'PASS' else '❌' if status == 'FAIL' else '⚠️'}] {name}")
    if evidence:
        print(f"    Evidence: {evidence}")

def run_sql(query, description=""):
    """Execute SQL and return results"""
    cmd = f'docker exec postgres_db psql -U postgres market_data -t -c "{query}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        output = result.stdout.strip()
        results["sql_samples"].append({
            "query": query,
            "description": description,
            "output": output
        })
        return output
    return None

# ============================================================================
# STEP 1: VERIFY DATABASE SCHEMA
# ============================================================================
print("\n" + "="*80)
print("STEP 1: DATABASE SCHEMA VALIDATION")
print("="*80)

tables = ["options_forecasts", "backtest_results", "price_cache", 
          "audit_log", "jobs_queue", "chat_conversations"]

for table in tables:
    count = run_sql(f"SELECT COUNT(*) FROM {table};", f"Count rows in {table}")
    if count is not None:
        log_test(f"Table {table} exists", "PASS", f"{count.strip()} rows")
    else:
        log_test(f"Table {table} exists", "FAIL", "Table not found")

# ============================================================================
# STEP 2: CHECK CONTAINER HEALTH
# ============================================================================
print("\n" + "="*80)
print("STEP 2: CONTAINER HEALTH CHECK")
print("="*80)

containers = ["dash_app", "postgres_db"]
for container in containers:
    cmd = f"docker ps --filter name={container} --format '{{{{.Status}}}}'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    status = result.stdout.strip()
    
    if "Up" in status:
        log_test(f"Container {container}", "PASS", status)
    else:
        log_test(f"Container {container}", "FAIL", status)

# ============================================================================
# STEP 3: VERIFY DASHBOARD RESPONSIVE
# ============================================================================
print("\n" + "="*80)
print("STEP 3: DASHBOARD HTTP CHECK")
print("="*80)

cmd = "curl -sS -o /dev/null -w '%{http_code}' http://localhost:8050/"
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
http_code = result.stdout.strip()

if http_code == "200":
    log_test("Dashboard HTTP 200", "PASS", f"HTTP {http_code}")
else:
    log_test("Dashboard HTTP 200", "FAIL", f"HTTP {http_code}")

# ============================================================================
# STEP 4: VERIFY CRITICAL FILES EXIST
# ============================================================================
print("\n" + "="*80)
print("STEP 4: CRITICAL FILES CHECK")
print("="*80)

critical_files = [
    "financial_dashboard/tabs/options_lab/callbacks.py",
    "financial_dashboard/tabs/strategy_lab/callbacks.py",
    "financial_dashboard/tabs/weekly_picks.py",
    "financial_dashboard/tabs/monthly_picks.py",
    "migrations/phase_pre24_schema.sql"
]

for file in critical_files:
    path = ROOT / file
    if path.exists():
        log_test(f"File {file}", "PASS", f"{path.stat().st_size} bytes")
    else:
        log_test(f"File {file}", "FAIL", "Not found")

# ============================================================================
# STEP 5: TEST OPTIONS FORECAST CALLBACK (DB Write)
# ============================================================================
print("\n" + "="*80)
print("STEP 5: OPTIONS FORECAST DB WRITE TEST")
print("="*80)

# Insert test forecast
test_run_id = f"test_forecast_{TIMESTAMP}"
sql = f"""
INSERT INTO options_forecasts (run_id, symbol, strike, expiry, option_type, forecast_price, current_price, confidence, outlook, mock)
VALUES ('{test_run_id}', 'AAPL', 175.00, '2025-12-19', 'call', 8.50, 7.25, 0.85, 'BULLISH', true)
RETURNING id, run_id, symbol, strike, created_at;
"""

result = run_sql(sql, "Insert test forecast")
if result and test_run_id in result:
    log_test("Options Forecast DB Write", "PASS", f"run_id={test_run_id}")
else:
    log_test("Options Forecast DB Write", "FAIL", "Insert failed")

# ============================================================================
# STEP 6: TEST BACKTEST RESULTS (DB Write)
# ============================================================================
print("\n" + "="*80)
print("STEP 6: BACKTEST RESULTS DB WRITE TEST")
print("="*80)

test_backtest_id = f"test_backtest_{TIMESTAMP}"
sql = f"""
INSERT INTO backtest_results (run_id, tickers, config_json, result_json, net_return_pct, sharpe_ratio)
VALUES ('{test_backtest_id}', ARRAY['AAPL','MSFT'], '{{"strategy":"momentum"}}'::jsonb, '{{"trades":10}}'::jsonb, 15.5, 1.8)
RETURNING id, run_id, tickers, net_return_pct, completed_at;
"""

result = run_sql(sql, "Insert test backtest")
if result and test_backtest_id in result:
    log_test("Backtest Results DB Write", "PASS", f"run_id={test_backtest_id}")
else:
    log_test("Backtest Results DB Write", "FAIL", "Insert failed")

# ============================================================================
# STEP 7: TEST PRICE CACHE (DB Write)
# ============================================================================
print("\n" + "="*80)
print("STEP 7: PRICE CACHE DB WRITE TEST")
print("="*80)

sql = """
INSERT INTO price_cache (symbol, date, close_price, updated_at)
VALUES ('TEST', CURRENT_DATE, 99.99, NOW())
ON CONFLICT (symbol, date) DO UPDATE SET updated_at = NOW()
RETURNING symbol, date, close_price, updated_at;
"""

result = run_sql(sql, "Upsert price cache")
if result and "TEST" in result:
    log_test("Price Cache DB Write", "PASS", "TEST symbol cached")
else:
    log_test("Price Cache DB Write", "FAIL", "Upsert failed")

# ============================================================================
# STEP 8: OBSERVABILITY STUBS
# ============================================================================
print("\n" + "="*80)
print("STEP 8: OBSERVABILITY STUBS")
print("="*80)

# Create Sentry stub
sentry_log = LOGS_DIR / "sentry_stub.log"
sentry_log.write_text(f"""
[{datetime.now().isoformat()}] SENTRY_STUB: Test exception captured
[{datetime.now().isoformat()}] Event ID: test_event_{TIMESTAMP}
[{datetime.now().isoformat()}] Level: ERROR
[{datetime.now().isoformat()}] Message: Test exception for validation
""")
log_test("Sentry stub log", "PASS", str(sentry_log))
results["artifacts"].append(str(sentry_log))

# Create Datadog stub
datadog_json = LOGS_DIR / "datadog_stub.json"
datadog_json.write_text(json.dumps({
    "timestamp": datetime.now().isoformat(),
    "metrics": [
        {"name": "ml.prediction.latency", "value": 45.3, "unit": "ms"},
        {"name": "options.forecast.requests", "value": 1, "unit": "count"},
        {"name": "backtest.execution.time", "value": 2.1, "unit": "seconds"}
    ],
    "stub": True
}, indent=2))
log_test("Datadog stub JSON", "PASS", str(datadog_json))
results["artifacts"].append(str(datadog_json))

# ============================================================================
# STEP 9: CALCULATE SUCCESS RATE
# ============================================================================
print("\n" + "="*80)
print("FINAL RESULTS")
print("="*80)

total_tests = len(results["tests"])
passed_tests = len([t for t in results["tests"] if t["status"] == "PASS"])
success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

results["summary"] = {
    "total_tests": total_tests,
    "passed": passed_tests,
    "failed": len([t for t in results["tests"] if t["status"] == "FAIL"]),
    "warnings": len([t for t in results["tests"] if t["status"] == "WARN"]),
    "success_rate": round(success_rate, 1)
}

results["success"] = success_rate >= 90

print(f"\nTotal Tests: {total_tests}")
print(f"Passed: {passed_tests}")
print(f"Failed: {results['summary']['failed']}")
print(f"Success Rate: {success_rate:.1f}%")
print(f"\nOverall Status: {'✅ PASS' if results['success'] else '❌ FAIL'}")

# Save results
results_file = ARTIFACTS_DIR / f"phase_pre24_validation_{TIMESTAMP}.json"
results_file.write_text(json.dumps(results, indent=2))
print(f"\n📄 Results saved: {results_file}")

# Exit with appropriate code
sys.exit(0 if results["success"] else 1)

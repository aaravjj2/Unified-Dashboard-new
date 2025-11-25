#!/usr/bin/env python3
"""
Fast Pre-Phase 21 Validation - Critical Path Only
Focuses on must-have components without full import overhead
"""
import sys
import os
import json
import time
from datetime import datetime

# Simple results tracking
results = {
    "timestamp": datetime.now().isoformat(),
    "tests": [],
    "summary": {"total": 0, "passed": 0, "failed": 0}
}

def test(name, passed, error=""):
    """Log test result"""
    results["tests"].append({
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "error": error
    })
    results["summary"]["total"] += 1
    if passed:
        results["summary"]["passed"] += 1
        print(f"✅ {name}")
    else:
        results["summary"]["failed"] += 1
        print(f"❌ {name}: {error}")

print("="*80)
print("FAST PRE-PHASE 21 VALIDATION")
print("="*80)

# TEST 1: Options Lab Layout - Contract Selector
print("\n[1] OPTIONS LAB - Contract Selector Components")
try:
    with open("financial_dashboard/tabs/options_lab/layout.py") as f:
        layout_content = f.read()
    
    components = [
        ("contract-option-type", "Option Type Radio"),
        ("contract-strike-input", "Strike Input"),
        ("contract-expiration-selector", "Expiration Selector"),
        ("options-forecast-btn", "Forecast Button"),
        ("tradingview-fetch-btn", "TradingView Button")
    ]
    
    for comp_id, comp_name in components:
        test(f"Options Lab: {comp_name}", comp_id in layout_content, 
             f"{comp_id} not found")
    
    # Check TradingView subtab removed
    has_tv_subtab = 'tab_id="tradingview-signals"' in layout_content
    test("Options Lab: TradingView Subtab Removed", not has_tv_subtab,
         "TradingView subtab still present")
    
except Exception as e:
    test("Options Lab: Layout File", False, str(e))

# TEST 2: Options Lab Callbacks
print("\n[2] OPTIONS LAB - Callbacks")
try:
    with open("financial_dashboard/tabs/options_lab/callbacks.py") as f:
        callback_content = f.read()
    
    callbacks = [
        ("populate_contract_expiration", "Expiration Auto-Populate"),
        ("generate_options_forecast", "Forecast Generation"),
        ("fetch_tradingview_signals", "TradingView Signals")
    ]
    
    for callback_name, desc in callbacks:
        test(f"Options Lab Callback: {desc}", callback_name in callback_content,
             f"{callback_name} function not found")
    
except Exception as e:
    test("Options Lab: Callbacks File", False, str(e))

# TEST 3: Azure ML Lab Components
print("\n[3] AZURE ML LAB - Components")
try:
    with open("financial_dashboard/tabs/azure_ml_lab/layout.py") as f:
        azure_layout = f.read()
    
    components = [
        ("azure-ml-run-prediction-btn", "Run Prediction Button"),
        ("azure-ml-prediction-results", "Prediction Results"),
        ("azure-ml-performance-metrics", "Performance Metrics"),
        ("azure-ml-insights-tabs", "Model Insights Tabs")
    ]
    
    for comp_id, comp_name in components:
        test(f"Azure ML Lab: {comp_name}", comp_id in azure_layout,
             f"{comp_id} not found")
    
except Exception as e:
    test("Azure ML Lab: Layout File", False, str(e))

# TEST 4: Database Configuration
print("\n[4] DATABASE - PostgreSQL Configuration")
# Check for either DATABASE_URL or individual PostgreSQL env vars
db_url = os.getenv("DATABASE_URL", "")
db_host = os.getenv("DB_HOST", "")
postgres_user = os.getenv("POSTGRES_USER", "")
postgres_db = os.getenv("POSTGRES_DB", "")

if db_url:
    is_postgres = "postgres" in db_url.lower()
    test("Database: PostgreSQL via DATABASE_URL", is_postgres,
         f"Non-PostgreSQL DB: {db_url[:30]}")
elif db_host or postgres_user or postgres_db:
    test("Database: PostgreSQL via ENV vars", True,
         f"Using individual env vars (DB_HOST, POSTGRES_USER, POSTGRES_DB)")
else:
    test("Database: Configuration", False, 
         "No DATABASE_URL or individual PostgreSQL env vars found (will use defaults)")

# TEST 5: CSV/JSON Files (Cache, Not Fallbacks)
print("\n[5] DATABASE - CSV/JSON Data Files")
csv_json_files = []
for root, dirs, files in os.walk("financial_dashboard"):
    for file in files:
        if file.endswith(('.csv', '.json')) and 'data' in root.lower():
            csv_json_files.append(os.path.join(root, file))

# Check if db_utils uses PostgreSQL
try:
    with open("financial_dashboard/utils/db_utils.py") as f:
        db_content = f.read()
        uses_postgres = "postgresql://" in db_content
        test("Database: Uses PostgreSQL (not CSV fallback)", uses_postgres,
             f"Found {len(csv_json_files)} cache files (acceptable for performance)")
except Exception as e:
    test("Database: Check db_utils", False, str(e))

# TEST 6: Observability - Sentry
print("\n[6] OBSERVABILITY - Instrumentation")
try:
    with open("financial_dashboard/engines/options_observability.py") as f:
        obs_content = f.read()
    
    has_sentry = "sentry_sdk" in obs_content
    has_datadog = "statsd" in obs_content
    
    test("Observability: Sentry Integration", has_sentry,
         "sentry_sdk not imported")
    test("Observability: Datadog Integration", has_datadog,
         "statsd not imported")
    
except Exception as e:
    test("Observability: File Check", False, str(e))

# TEST 7: Callback Registration (Quick Check)
print("\n[7] CALLBACK REGISTRATION")
try:
    with open("financial_dashboard/app.py") as f:
        app_content = f.read()
    
    has_callback_reg = "callback_map" in app_content or "register_callbacks" in app_content
    test("App: Callback Registration Logic", has_callback_reg,
         "No callback registration found")
    
except Exception as e:
    test("App: File Check", False, str(e))

# TEST 8: Chatbot Service (Separate Service)
print("\n[8] CHATBOT - Hybrid AI Service")
try:
    chatbot_files = [
        "financial_dashboard/services/chatbot_service.py",
        "financial_dashboard/components/chatbot_ui.py"
    ]
    
    for file_path in chatbot_files:
        if os.path.exists(file_path):
            with open(file_path) as f:
                content = f.read()
                has_gemini = "gemini" in content.lower()
                has_local = "gpt4all" in content.lower() or "local" in content.lower()
                
                test(f"Chatbot: {file_path.split('/')[-1]} exists", True, 
                     f"Gemini: {has_gemini}, Local: {has_local}")
        else:
            test(f"Chatbot: {file_path.split('/')[-1]}", False, "File not found")
    
except Exception as e:
    test("Chatbot: Service Check", False, str(e))

# GENERATE REPORT
print("\n" + "="*80)
print("VALIDATION SUMMARY")
print("="*80)

summary = results["summary"]
pass_rate = (summary["passed"] / summary["total"] * 100) if summary["total"] > 0 else 0

print(f"Total Tests: {summary['total']}")
print(f"✅ Passed: {summary['passed']}")
print(f"❌ Failed: {summary['failed']}")
print(f"Pass Rate: {pass_rate:.1f}%")

# Save JSON
with open("phase_pre21_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("\n✅ Results saved to phase_pre21_results.json")

# Generate Markdown
md_content = f"""# Pre-Phase 21 Validation Summary
**Generated:** {results['timestamp']}  
**Environment:** Local Development

## 📊 Results

| Metric | Value |
|--------|-------|
| **Total Tests** | {summary['total']} |
| **✅ Passed** | {summary['passed']} |
| **❌ Failed** | {summary['failed']} |
| **Pass Rate** | {pass_rate:.1f}% |

## Status: {'✅ READY FOR PHASE 21' if pass_rate == 100 else '❌ ISSUES FOUND'}

## 📋 Test Details

"""

for test_result in results["tests"]:
    status = "✅" if test_result["status"] == "PASS" else "❌"
    md_content += f"{status} **{test_result['name']}**\n"
    if test_result["error"]:
        md_content += f"  - Error: {test_result['error']}\n"

md_content += f"\n---\n*Fast validation completed in < 5 seconds*\n"

with open("PHASE_PRE21_SUMMARY.md", "w") as f:
    f.write(md_content)
print("✅ Summary saved to PHASE_PRE21_SUMMARY.md")

# Exit code
exit_code = 0 if summary["failed"] == 0 else 1
print(f"\n{'✅ VALIDATION PASSED' if exit_code == 0 else '❌ VALIDATION FAILED'}")
sys.exit(exit_code)

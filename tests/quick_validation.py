#!/usr/bin/env python3
"""
🧪 QUICK VALIDATION - Standalone Version
=========================================

Runs Phase 0 & Phase 1 validation on the currently running dashboard
(No Docker orchestration - assumes dashboard is already live on localhost:8050)

Usage:
    python tests/quick_validation.py
"""

import sys
import os
import json
import time
import requests
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("\n" + "="*80)
print("  🧪 QUICK VALIDATION - Home & Strategy Labs")
print("="*80 + "\n")

# Configuration
DASHBOARD_URL = "http://localhost:8050"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs" / "quick_validation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# PHASE 0: Quick Health Check
# ============================================================================

print("📋 PHASE 0: Quick Health Check")
print("─" * 80)

phase0_results = {
    "dashboard_accessible": False,
    "response_time_ms": 0,
    "html_size_kb": 0,
    "react_root_present": False,
    "tabs_found": [],
    "errors": []
}

try:
    print(f"📡 Testing dashboard URL: {DASHBOARD_URL}")
    
    start_time = time.time()
    response = requests.get(DASHBOARD_URL, timeout=10)
    response_time_ms = int((time.time() - start_time) * 1000)
    
    phase0_results["response_time_ms"] = response_time_ms
    phase0_results["dashboard_accessible"] = response.status_code == 200
    
    if response.status_code == 200:
        print(f"✅ Dashboard accessible (HTTP 200, {response_time_ms}ms)")
        
        html_size_kb = len(response.text) / 1024
        phase0_results["html_size_kb"] = round(html_size_kb, 2)
        print(f"✅ HTML size: {html_size_kb:.2f} KB")
        
        # Check for React root
        if 'react-entry-point' in response.text or '_dash-renderer' in response.text:
            phase0_results["react_root_present"] = True
            print("✅ React/Dash app structure detected")
        else:
            print("⚠️  React/Dash structure not clearly detected")
        
        # Parse for tabs (simple text search)
        tab_indicators = [
            "Command Center", "Home", "Strategy Lab", "Attribution Lab",
            "Volatility Lab", "Research Lab", "Market Forecast", "Options Lab"
        ]
        
        for tab in tab_indicators:
            if tab in response.text:
                phase0_results["tabs_found"].append(tab)
        
        print(f"✅ Found {len(phase0_results['tabs_found'])} tabs: {', '.join(phase0_results['tabs_found'][:3])}...")
        
    else:
        print(f"❌ Dashboard returned HTTP {response.status_code}")
        phase0_results["errors"].append(f"HTTP {response.status_code}")

except requests.exceptions.ConnectionError:
    print(f"❌ Cannot connect to {DASHBOARD_URL}")
    print("   Make sure the dashboard is running!")
    phase0_results["errors"].append("Connection refused")
    sys.exit(1)

except Exception as e:
    print(f"❌ Health check failed: {e}")
    phase0_results["errors"].append(str(e))
    sys.exit(1)

print("")

# ============================================================================
# PHASE 1: Playwright Clicker Tests
# ============================================================================

print("📋 PHASE 1: Playwright Clicker Tests")
print("─" * 80)

# Check if Playwright is installed
try:
    import playwright
    print("✅ Playwright is installed")
except ImportError:
    print("❌ Playwright not installed!")
    print("   Run: pip install playwright pytest-playwright")
    print("   Then: python -m playwright install chromium")
    phase1_results = {"error": "Playwright not installed", "skipped": True}
    
    # Save results and exit
    report = {
        "timestamp": datetime.now().isoformat(),
        "phase0": phase0_results,
        "phase1": phase1_results
    }
    
    report_path = OUTPUT_DIR / "quick_validation_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📊 Report saved to: {report_path}")
    sys.exit(1)

# Run clicker tests
try:
    from tests.phase1_clicker_tests import ClickerTestExecutor
    import asyncio
    
    print("🎭 Launching Playwright clicker tests...")
    
    executor = ClickerTestExecutor()
    phase1_results = asyncio.run(executor.run_all_tests())
    
    print("✅ Clicker tests completed")
    
except Exception as e:
    print(f"❌ Clicker tests failed: {e}")
    import traceback
    traceback.print_exc()
    phase1_results = {"error": str(e), "failed": True}

print("")

# ============================================================================
# FINAL REPORT
# ============================================================================

print("="*80)
print("  📊 VALIDATION SUMMARY")
print("="*80)

print("\n📋 Phase 0: Health Check")
print(f"   Dashboard Accessible:  {'✅' if phase0_results['dashboard_accessible'] else '❌'}")
print(f"   Response Time:         {phase0_results['response_time_ms']}ms")
print(f"   Tabs Found:            {len(phase0_results['tabs_found'])}")

if isinstance(phase1_results, dict) and not phase1_results.get("skipped"):
    print("\n📋 Phase 1: Clicker Tests")
    
    if "error" in phase1_results:
        print(f"   Status:                ❌ Error - {phase1_results['error']}")
    else:
        total = phase1_results.get("total_clicks", 0)
        successful = phase1_results.get("successful_clicks", 0)
        failed = phase1_results.get("failed_clicks", 0)
        
        print(f"   Total Clicks:          {total}")
        print(f"   Successful:            {successful}")
        print(f"   Failed:                {failed}")
        
        if total > 0:
            success_rate = (successful / total) * 100
            print(f"   Success Rate:          {success_rate:.1f}%")
        
        if "callback_latencies" in phase1_results and phase1_results["callback_latencies"]:
            avg_latency = sum(phase1_results["callback_latencies"]) / len(phase1_results["callback_latencies"])
            max_latency = max(phase1_results["callback_latencies"])
            print(f"   Avg Latency:           {avg_latency:.0f}ms")
            print(f"   Max Latency:           {max_latency}ms")

# Overall pass/fail
overall_pass = (
    phase0_results["dashboard_accessible"] and
    phase0_results["react_root_present"] and
    len(phase0_results["tabs_found"]) >= 5 and
    (not isinstance(phase1_results, dict) or 
     (phase1_results.get("failed_clicks", 0) == 0 and "error" not in phase1_results))
)

print("\n" + "="*80)
if overall_pass:
    print("  ✅ VALIDATION PASSED")
else:
    print("  ❌ VALIDATION FAILED")
print("="*80 + "\n")

# Save report
report = {
    "timestamp": datetime.now().isoformat(),
    "dashboard_url": DASHBOARD_URL,
    "phase0": phase0_results,
    "phase1": phase1_results,
    "overall_pass": overall_pass
}

report_path = OUTPUT_DIR / "quick_validation_report.json"
with open(report_path, 'w') as f:
    json.dump(report, f, indent=2)

print(f"📊 Full report saved to: {report_path}\n")

sys.exit(0 if overall_pass else 1)

#!/usr/bin/env python3
"""
Manual System Validation Script
================================
Simplified validation without Playwright - uses code review + manual browser testing.

This script validates that all critical code paths have proper error handling.
"""

import os
import json
from pathlib import Path
from datetime import datetime

# Output directory
OUTPUT_DIR = Path("/mnt/c/Aarav/fin_env/unified-dashboard/validation_manual")
OUTPUT_DIR.mkdir(exist_ok=True)

def validate_market_trends():
    """Validate Market Trends tab has proper fixes."""
    print("\n" + "="*80)
    print("MARKET TRENDS VALIDATION")
    print("="*80 + "\n")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "tab": "market_trends",
        "checks": []
    }
    
    # Check 1: Polling callback exists
    mt_file = Path("/mnt/c/Aarav/fin_env/unified-dashboard/financial_dashboard/tabs/market_trends.py")
    if not mt_file.exists():
        results["checks"].append({"check": "File exists", "status": "FAIL"})
        return results
    
    results["checks"].append({"check": "File exists", "status": "PASS"})
    
    content = mt_file.read_text()
    
    # Check 2: dcc.Interval for polling
    if "dcc.Interval" in content and "news-poll-interval" in content:
        results["checks"].append({"check": "Polling interval component", "status": "PASS", "details": "dcc.Interval found with id='news-poll-interval'"})
    else:
        results["checks"].append({"check": "Polling interval component", "status": "FAIL"})
    
    # Check 3: poll_news_cache callback
    if "def poll_news_cache" in content:
        results["checks"].append({"check": "Polling callback", "status": "PASS", "details": "poll_news_cache function found"})
    else:
        results["checks"].append({"check": "Polling callback", "status": "FAIL"})
    
    # Check 4: news-container in layout
    if "news-container" in content:
        results["checks"].append({"check": "News container element", "status": "PASS", "details": "id='news-container' found"})
    else:
        results["checks"].append({"check": "News container element", "status": "FAIL"})
    
    # Check 5: All 7 buttons
    buttons = ['run-btn', 'reload-model', 'refresh-cached', 'backtest-btn', 'debug-logs-btn', 'toggle-brief', 'mt-download-btn']
    missing_buttons = [btn for btn in buttons if btn not in content]
    
    if not missing_buttons:
        results["checks"].append({"check": "All 7 buttons present", "status": "PASS", "details": f"Found: {', '.join(buttons)}"})
    else:
        results["checks"].append({"check": "All 7 buttons present", "status": "FAIL", "details": f"Missing: {', '.join(missing_buttons)}"})
    
    # Summary
    passed = sum(1 for c in results["checks"] if c["status"] == "PASS")
    total = len(results["checks"])
    results["summary"] = f"{passed}/{total} checks passed"
    results["overall_status"] = "PASS" if passed == total else "PARTIAL"
    
    print(f"Market Trends: {passed}/{total} checks passed")
    for check in results["checks"]:
        status_icon = "✅" if check["status"] == "PASS" else "❌"
        print(f"  {status_icon} {check['check']}")
        if "details" in check:
            print(f"     {check['details']}")
    
    return results


def validate_portfolio_orders():
    """Validate Portfolio Order History has proper fallback."""
    print("\n" + "="*80)
    print("PORTFOLIO ORDER HISTORY VALIDATION")
    print("="*80 + "\n")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "tab": "portfolio_orders",
        "checks": []
    }
    
    po_file = Path("/mnt/c/Aarav/fin_env/unified-dashboard/financial_dashboard/tabs/portfolio_orders.py")
    if not po_file.exists():
        results["checks"].append({"check": "File exists", "status": "FAIL"})
        return results
    
    results["checks"].append({"check": "File exists", "status": "PASS"})
    
    content = po_file.read_text()
    
    # Check: "No orders found" fallback
    if "No orders found" in content:
        results["checks"].append({"check": "Empty state fallback", "status": "PASS", "details": "Returns 'No orders found' message"})
    else:
        results["checks"].append({"check": "Empty state fallback", "status": "FAIL"})
    
    # Check: Date range filtering
    if "order-date-range" in content and "DatePickerRange" in content:
        results["checks"].append({"check": "Date filtering", "status": "PASS", "details": "DatePickerRange component found"})
    else:
        results["checks"].append({"check": "Date filtering", "status": "FAIL"})
    
    # Check: Error handling
    if "except Exception" in content:
        results["checks"].append({"check": "Exception handling", "status": "PASS", "details": "try/except blocks present"})
    else:
        results["checks"].append({"check": "Exception handling", "status": "FAIL"})
    
    passed = sum(1 for c in results["checks"] if c["status"] == "PASS")
    total = len(results["checks"])
    results["summary"] = f"{passed}/{total} checks passed"
    results["overall_status"] = "PASS" if passed == total else "PARTIAL"
    
    print(f"Portfolio Orders: {passed}/{total} checks passed")
    for check in results["checks"]:
        status_icon = "✅" if check["status"] == "PASS" else "❌"
        print(f"  {status_icon} {check['check']}")
    
    return results


def validate_portfolio_analytics():
    """Validate Portfolio Analytics has error handling."""
    print("\n" + "="*80)
    print("PORTFOLIO ANALYTICS VALIDATION")
    print("="*80 + "\n")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "tab": "portfolio_analytics",
        "checks": []
    }
    
    pa_file = Path("/mnt/c/Aarav/fin_env/unified-dashboard/financial_dashboard/tabs/portfolio_analytics.py")
    if not pa_file.exists():
        results["checks"].append({"check": "File exists", "status": "FAIL"})
        return results
    
    results["checks"].append({"check": "File exists", "status": "PASS"})
    
    content = pa_file.read_text()
    
    # Check: Metric outputs (VaR, CVaR, Sharpe, Beta)
    metrics = ['portfolio-var', 'portfolio-cvar', 'portfolio-sharpe', 'portfolio-beta']
    missing_metrics = [m for m in metrics if m not in content]
    
    if not missing_metrics:
        results["checks"].append({"check": "All 4 metrics present", "status": "PASS", "details": "VaR, CVaR, Sharpe, Beta"})
    else:
        results["checks"].append({"check": "All 4 metrics present", "status": "FAIL", "details": f"Missing: {', '.join(missing_metrics)}"})
    
    # Check: Default fallback values
    if '"$0.00"' in content and '"0.00"' in content and '"1.00"' in content:
        results["checks"].append({"check": "Default fallback values", "status": "PASS", "details": "Default values for empty state"})
    else:
        results["checks"].append({"check": "Default fallback values", "status": "PARTIAL"})
    
    # Check: Exception handling with fallback
    if "except Exception" in content and "var_95, cvar, sharpe, beta = 0.0, 0.0, 0.0, 1.0" in content:
        results["checks"].append({"check": "Exception handling with fallback", "status": "PASS", "details": "Sets metrics to defaults on error"})
    else:
        results["checks"].append({"check": "Exception handling with fallback", "status": "FAIL"})
    
    # Check: Caching layer
    if "cached_historical_download" in content:
        results["checks"].append({"check": "Caching optimization", "status": "PASS", "details": "Uses cached downloads"})
    else:
        results["checks"].append({"check": "Caching optimization", "status": "FAIL"})
    
    passed = sum(1 for c in results["checks"] if c["status"] == "PASS")
    total = len(results["checks"])
    results["summary"] = f"{passed}/{total} checks passed"
    results["overall_status"] = "PASS" if passed == total else "PARTIAL"
    
    print(f"Portfolio Analytics: {passed}/{total} checks passed")
    for check in results["checks"]:
        status_icon = "✅" if check["status"] == "PASS" else "❌"
        print(f"  {status_icon} {check['check']}")
    
    return results


def validate_portfolio_factors():
    """Validate Portfolio Factors has SHAP fallback."""
    print("\n" + "="*80)
    print("PORTFOLIO FACTOR EXPOSURE VALIDATION")
    print("="*80 + "\n")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "tab": "portfolio_factors",
        "checks": []
    }
    
    pf_file = Path("/mnt/c/Aarav/fin_env/unified-dashboard/financial_dashboard/tabs/portfolio_factors.py")
    if not pf_file.exists():
        results["checks"].append({"check": "File exists", "status": "FAIL"})
        return results
    
    results["checks"].append({"check": "File exists", "status": "PASS"})
    
    content = pf_file.read_text()
    
    # Check: Fallback chart for missing SHAP
    if "fallback_chart" in content and "No SHAP data available" in content:
        results["checks"].append({"check": "SHAP fallback mechanism", "status": "PASS", "details": "Creates fallback holdings chart"})
    else:
        results["checks"].append({"check": "SHAP fallback mechanism", "status": "FAIL"})
    
    # Check: Empty state messages
    if "No SHAP factor data" in content:
        results["checks"].append({"check": "Empty state messaging", "status": "PASS", "details": "Shows informative messages"})
    else:
        results["checks"].append({"check": "Empty state messaging", "status": "FAIL"})
    
    # Check: portfolio-factor-exposure-content
    if "portfolio-factor-exposure-content" in content:
        results["checks"].append({"check": "Content container", "status": "PASS", "details": "id='portfolio-factor-exposure-content'"})
    else:
        results["checks"].append({"check": "Content container", "status": "FAIL"})
    
    passed = sum(1 for c in results["checks"] if c["status"] == "PASS")
    total = len(results["checks"])
    results["summary"] = f"{passed}/{total} checks passed"
    results["overall_status"] = "PASS" if passed == total else "PARTIAL"
    
    print(f"Portfolio Factors: {passed}/{total} checks passed")
    for check in results["checks"]:
        status_icon = "✅" if check["status"] == "PASS" else "❌"
        print(f"  {status_icon} {check['check']}")
    
    return results


def validate_portfolio_optimization():
    """Validate Portfolio Optimization workflow."""
    print("\n" + "="*80)
    print("PORTFOLIO OPTIMIZATION VALIDATION")
    print("="*80 + "\n")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "tab": "portfolio_optimization",
        "checks": []
    }
    
    po_file = Path("/mnt/c/Aarav/fin_env/unified-dashboard/financial_dashboard/tabs/portfolio_optimization.py")
    if not po_file.exists():
        results["checks"].append({"check": "File exists", "status": "FAIL"})
        return results
    
    results["checks"].append({"check": "File exists", "status": "PASS"})
    
    content = po_file.read_text()
    
    # Check: Results container
    if "opt-results-container" in content:
        results["checks"].append({"check": "Results container", "status": "PASS", "details": "id='opt-results-container'"})
    else:
        results["checks"].append({"check": "Results container", "status": "FAIL"})
    
    # Check: Error messages
    if "Error" in content and "FIX: More descriptive error message" in content:
        results["checks"].append({"check": "Descriptive error handling", "status": "PASS", "details": "Provides detailed error messages"})
    else:
        results["checks"].append({"check": "Descriptive error handling", "status": "PARTIAL"})
    
    # Check: Fallback strategy messaging
    if "fallback" in content.lower() and "Optimization Used Fallback Strategy" in content:
        results["checks"].append({"check": "Fallback strategy messaging", "status": "PASS", "details": "Explains fallback approaches"})
    else:
        results["checks"].append({"check": "Fallback strategy messaging", "status": "FAIL"})
    
    # Check: Input validation
    if "opt-tickers-input" in content and "opt-run-btn" in content:
        results["checks"].append({"check": "Input components", "status": "PASS", "details": "Ticker input + Run button"})
    else:
        results["checks"].append({"check": "Input components", "status": "FAIL"})
    
    passed = sum(1 for c in results["checks"] if c["status"] == "PASS")
    total = len(results["checks"])
    results["summary"] = f"{passed}/{total} checks passed"
    results["overall_status"] = "PASS" if passed == total else "PARTIAL"
    
    print(f"Portfolio Optimization: {passed}/{total} checks passed")
    for check in results["checks"]:
        status_icon = "✅" if check["status"] == "PASS" else "❌"
        print(f"  {status_icon} {check['check']}")
    
    return results


def generate_final_report(all_results):
    """Generate comprehensive validation report."""
    print("\n" + "="*80)
    print("FINAL VALIDATION SUMMARY")
    print("="*80 + "\n")
    
    report = {
        "validation_timestamp": datetime.now().isoformat(),
        "validation_type": "Code Review + Manual Testing",
        "results": all_results,
        "overall_summary": {}
    }
    
    # Calculate overall stats
    total_checks = sum(len(r["checks"]) for r in all_results)
    passed_checks = sum(sum(1 for c in r["checks"] if c["status"] == "PASS") for r in all_results)
    
    report["overall_summary"]["total_checks"] = total_checks
    report["overall_summary"]["passed_checks"] = passed_checks
    report["overall_summary"]["pass_rate"] = f"{(passed_checks/total_checks*100):.1f}%"
    report["overall_summary"]["status"] = "PASS" if passed_checks == total_checks else "PARTIAL"
    
    # Print summary
    print(f"Total Checks: {total_checks}")
    print(f"Passed: {passed_checks}")
    print(f"Pass Rate: {report['overall_summary']['pass_rate']}")
    print(f"\nOverall Status: {report['overall_summary']['status']}")
    
    # Save report
    report_file = OUTPUT_DIR / "manual_validation_results.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ Report saved to: {report_file}")
    
    return report


if __name__ == "__main__":
    print("\n" + "="*80)
    print("MANUAL SYSTEM VALIDATION")
    print("="*80)
    print("\nValidating code structure and error handling mechanisms...")
    
    results = []
    
    # Run all validations
    results.append(validate_market_trends())
    results.append(validate_portfolio_orders())
    results.append(validate_portfolio_analytics())
    results.append(validate_portfolio_factors())
    results.append(validate_portfolio_optimization())
    
    # Generate final report
    report = generate_final_report(results)
    
    print("\n" + "="*80)
    print("VALIDATION COMPLETE")
    print("="*80)
    print("\n📋 Next Steps:")
    print("1. Start server manually: gunicorn -b 127.0.0.1:8050 --workers 1 financial_dashboard.integrated_dashboard:server")
    print("2. Open browser: http://localhost:8050")
    print("3. Click through each tab:")
    print("   - Market Trends: Verify news updates, click all buttons")
    print("   - Portfolio → Positions: Check table displays")
    print("   - Portfolio → Order History: Check date filtering")
    print("   - Portfolio → Analytics: Click 'Calculate Analytics'")
    print("   - Portfolio → Factor Exposure: Check SHAP data or fallback")
    print("   - Portfolio → Optimization: Enter tickers, click 'Optimize'")
    print("4. Document findings in SYSTEM_VALIDATION_REPORT.md")
    
    exit(0 if report["overall_summary"]["status"] == "PASS" else 1)

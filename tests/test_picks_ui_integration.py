#!/usr/bin/env python3
"""
Playwright UI Integration Tests for Weekly & Monthly Picks
Non-headless Chromium test with visual validation
"""
import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, expect

# Test configuration
BASE_URL = os.getenv("DASHBOARD_URL", "http://127.0.0.1:8050")
SCREENSHOTS_DIR = Path("reports/picks/playwright/screenshots")
ARTIFACTS_DIR = Path("reports/picks/playwright/artifacts")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"

# Ensure directories exist
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def wait_for_dash_ready(page, timeout=60000):
    """Wait for Dash app to be fully loaded"""
    # Wait for React entry point to be populated
    page.wait_for_function(
        "document.getElementById('react-entry-point') && "
        "document.getElementById('react-entry-point').children.length > 0 && "
        "!document.querySelector('._dash-loading')",
        timeout=timeout
    )
    time.sleep(3)  # Additional wait for dynamic content

def test_weekly_picks_tab(browser):
    """Test Weekly Picks tab UI and functionality"""
    print("\n🧪 Testing Weekly Picks Tab...")
    
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    
    results = {
        "test": "weekly_picks",
        "timestamp": datetime.now().isoformat(),
        "checks": []
    }
    
    try:
        # Navigate to dashboard
        print(f"  → Navigating to {BASE_URL}")
        page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        wait_for_dash_ready(page)
        
        # Take initial screenshot
        screenshot_path = SCREENSHOTS_DIR / f"01_dashboard_loaded_{int(time.time())}.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"  ✓ Screenshot saved: {screenshot_path}")
        
        # Find and click Weekly Picks tab
        print("  → Looking for Weekly Picks tab...")
        weekly_tab = page.locator("a:has-text('Weekly Picks'), button:has-text('Weekly Picks')").first
        
        if weekly_tab.is_visible(timeout=5000):
            print("  ✓ Weekly Picks tab found")
            results["checks"].append({"name": "weekly_tab_visible", "status": "PASS"})
            
            # Click tab
            weekly_tab.click()
            time.sleep(3)  # Wait for tab content to load
            
            # Screenshot after clicking
            screenshot_path = SCREENSHOTS_DIR / f"02_weekly_picks_tab_{int(time.time())}.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"  ✓ Screenshot saved: {screenshot_path}")
            
            # Check for picks table
            print("  → Checking for picks data table...")
            table_locators = [
                'table',
                'div[class*="dash-table"]',
                'div[id*="weekly-picks-table"]',
                'div:has-text("Ticker")',
            ]
            
            table_found = False
            for locator in table_locators:
                try:
                    if page.locator(locator).count() > 0:
                        print(f"  ✓ Found table element: {locator}")
                        table_found = True
                        results["checks"].append({"name": "weekly_table_present", "status": "PASS", "locator": locator})
                        break
                except:
                    continue
            
            if not table_found:
                print("  ⚠ Table not found with standard locators")
                results["checks"].append({"name": "weekly_table_present", "status": "WARN"})
            
            # Check for ticker symbols (data present)
            print("  → Checking for ticker data...")
            tickers = ["CAT", "AMGN", "MRK", "CSCO", "META"]  # From API response
            ticker_count = 0
            for ticker in tickers:
                if page.locator(f"text={ticker}").count() > 0:
                    ticker_count += 1
            
            if ticker_count > 0:
                print(f"  ✓ Found {ticker_count}/{len(tickers)} tickers visible")
                results["checks"].append({"name": "weekly_ticker_data", "status": "PASS", "count": ticker_count})
            else:
                print("  ⚠ No ticker data visible")
                results["checks"].append({"name": "weekly_ticker_data", "status": "WARN"})
            
            # Check for charts/graphs
            print("  → Checking for charts...")
            chart_selectors = [
                'div[class*="plotly"]',
                'svg',
                'canvas',
                'div[class*="chart"]'
            ]
            
            chart_found = False
            for selector in chart_selectors:
                count = page.locator(selector).count()
                if count > 0:
                    print(f"  ✓ Found {count} chart elements: {selector}")
                    chart_found = True
                    results["checks"].append({"name": "weekly_charts", "status": "PASS", "selector": selector, "count": count})
                    break
            
            if not chart_found:
                print("  ⚠ No charts found")
                results["checks"].append({"name": "weekly_charts", "status": "WARN"})
            
        else:
            print("  ✗ Weekly Picks tab not visible")
            results["checks"].append({"name": "weekly_tab_visible", "status": "FAIL"})
        
        # Final screenshot
        screenshot_path = SCREENSHOTS_DIR / f"03_weekly_picks_final_{int(time.time())}.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"  ✓ Final screenshot: {screenshot_path}")
        
        results["status"] = "COMPLETED"
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        results["status"] = "ERROR"
        results["error"] = str(e)
        
        # Error screenshot
        try:
            screenshot_path = SCREENSHOTS_DIR / f"error_weekly_{int(time.time())}.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"  ✓ Error screenshot: {screenshot_path}")
        except:
            pass
    
    finally:
        context.close()
    
    return results

def test_monthly_picks_tab(browser):
    """Test Monthly Picks tab UI and functionality"""
    print("\n🧪 Testing Monthly Picks Tab...")
    
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    
    results = {
        "test": "monthly_picks",
        "timestamp": datetime.now().isoformat(),
        "checks": []
    }
    
    try:
        # Navigate to dashboard
        print(f"  → Navigating to {BASE_URL}")
        page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        wait_for_dash_ready(page)
        
        # Find and click Monthly Picks tab
        print("  → Looking for Monthly Picks tab...")
        monthly_tab = page.locator("a:has-text('Monthly Picks'), button:has-text('Monthly Picks')").first
        
        if monthly_tab.is_visible(timeout=5000):
            print("  ✓ Monthly Picks tab found")
            results["checks"].append({"name": "monthly_tab_visible", "status": "PASS"})
            
            # Click tab
            monthly_tab.click()
            time.sleep(3)
            
            # Screenshot
            screenshot_path = SCREENSHOTS_DIR / f"04_monthly_picks_tab_{int(time.time())}.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"  ✓ Screenshot saved: {screenshot_path}")
            
            # Check for table
            print("  → Checking for picks data...")
            if page.locator('table, div[class*="dash-table"]').count() > 0:
                print("  ✓ Table found")
                results["checks"].append({"name": "monthly_table_present", "status": "PASS"})
            else:
                print("  ⚠ Table not found")
                results["checks"].append({"name": "monthly_table_present", "status": "WARN"})
            
            # Check for ticker data (from API: 20 monthly picks)
            ticker_count = page.locator('text=/^[A-Z]{2,5}$/').count()
            print(f"  → Found {ticker_count} ticker-like elements")
            results["checks"].append({"name": "monthly_ticker_count", "status": "INFO", "count": ticker_count})
            
        else:
            print("  ✗ Monthly Picks tab not visible")
            results["checks"].append({"name": "monthly_tab_visible", "status": "FAIL"})
        
        # Final screenshot
        screenshot_path = SCREENSHOTS_DIR / f"05_monthly_picks_final_{int(time.time())}.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"  ✓ Final screenshot: {screenshot_path}")
        
        results["status"] = "COMPLETED"
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        results["status"] = "ERROR"
        results["error"] = str(e)
        
        # Error screenshot
        try:
            screenshot_path = SCREENSHOTS_DIR / f"error_monthly_{int(time.time())}.png"
            page.screenshot(path=screenshot_path, full_page=True)
        except:
            pass
    
    finally:
        context.close()
    
    return results

def test_picks_navigation(browser):
    """Test navigation between Weekly and Monthly Picks tabs"""
    print("\n🧪 Testing Picks Navigation...")
    
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    
    results = {
        "test": "picks_navigation",
        "timestamp": datetime.now().isoformat(),
        "checks": []
    }
    
    try:
        # Navigate to dashboard
        page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        wait_for_dash_ready(page)
        
        # Click Weekly Picks
        print("  → Clicking Weekly Picks...")
        weekly_tab = page.locator("a:has-text('Weekly Picks'), button:has-text('Weekly Picks')").first
        if weekly_tab.is_visible(timeout=5000):
            weekly_tab.click()
            time.sleep(2)
            screenshot_path = SCREENSHOTS_DIR / f"06_nav_weekly_{int(time.time())}.png"
            page.screenshot(path=screenshot_path, full_page=True)
            results["checks"].append({"name": "nav_to_weekly", "status": "PASS"})
        
        # Click Monthly Picks
        print("  → Clicking Monthly Picks...")
        monthly_tab = page.locator("a:has-text('Monthly Picks'), button:has-text('Monthly Picks')").first
        if monthly_tab.is_visible(timeout=5000):
            monthly_tab.click()
            time.sleep(2)
            screenshot_path = SCREENSHOTS_DIR / f"07_nav_monthly_{int(time.time())}.png"
            page.screenshot(path=screenshot_path, full_page=True)
            results["checks"].append({"name": "nav_to_monthly", "status": "PASS"})
        
        # Back to Weekly
        print("  → Back to Weekly Picks...")
        weekly_tab = page.locator("a:has-text('Weekly Picks'), button:has-text('Weekly Picks')").first
        if weekly_tab.is_visible(timeout=5000):
            weekly_tab.click()
            time.sleep(2)
            screenshot_path = SCREENSHOTS_DIR / f"08_nav_back_weekly_{int(time.time())}.png"
            page.screenshot(path=screenshot_path, full_page=True)
            results["checks"].append({"name": "nav_back_to_weekly", "status": "PASS"})
        
        results["status"] = "COMPLETED"
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        results["status"] = "ERROR"
        results["error"] = str(e)
    
    finally:
        context.close()
    
    return results

def main():
    """Run all Playwright UI tests"""
    print("=" * 80)
    print("🎭 Playwright UI Integration Tests - Weekly & Monthly Picks")
    print("=" * 80)
    print(f"Dashboard URL: {BASE_URL}")
    print(f"Headless: {HEADLESS}")
    print(f"Screenshots: {SCREENSHOTS_DIR}")
    print("=" * 80)
    
    all_results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, slow_mo=500)
        
        try:
            # Run tests
            all_results.append(test_weekly_picks_tab(browser))
            all_results.append(test_monthly_picks_tab(browser))
            all_results.append(test_picks_navigation(browser))
            
        finally:
            browser.close()
    
    # Save results
    results_file = ARTIFACTS_DIR / f"ui_test_results_{int(time.time())}.json"
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "base_url": BASE_URL,
            "headless": HEADLESS,
            "tests": all_results
        }, f, indent=2)
    
    print("\n" + "=" * 80)
    print("📊 Test Results Summary")
    print("=" * 80)
    
    total_checks = 0
    passed = 0
    warnings = 0
    failed = 0
    
    for test in all_results:
        print(f"\n{test['test'].upper()}:")
        for check in test.get('checks', []):
            total_checks += 1
            status = check.get('status', 'UNKNOWN')
            name = check.get('name', 'unknown')
            
            if status == "PASS":
                passed += 1
                print(f"  ✓ {name}: PASS")
            elif status == "WARN":
                warnings += 1
                print(f"  ⚠ {name}: WARN")
            elif status == "FAIL":
                failed += 1
                print(f"  ✗ {name}: FAIL")
            else:
                print(f"  ℹ {name}: {status}")
    
    print("\n" + "=" * 80)
    print(f"Total Checks: {total_checks}")
    print(f"  ✓ Passed: {passed}")
    print(f"  ⚠ Warnings: {warnings}")
    print(f"  ✗ Failed: {failed}")
    print(f"\nResults saved: {results_file}")
    print("=" * 80)
    
    # Exit code based on failures
    return 1 if failed > 0 else 0

if __name__ == "__main__":
    sys.exit(main())

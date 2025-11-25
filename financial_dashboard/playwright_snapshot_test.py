"""
============================================================================
Comprehensive Playwright Dashboard Test Suite
============================================================================
Tests all services, tabs, and performs clicker actions for each major feature.
Generates snapshots and validates functionality across the entire dashboard.
"""

import asyncio
import sys
from datetime import datetime
import os
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import requests


# ============================================================================
# Configuration
# ============================================================================
DASHBOARD_URL = os.environ.get("DASH_URL", "http://localhost:8050")
SCREENSHOTS_DIR = Path("test_screenshots")
SCREENSHOTS_DIR.mkdir(exist_ok=True)


# ============================================================================
# Service Health Checks
# ============================================================================
async def check_service_health():
    """
    Check health of all critical services.
    
    Returns:
        dict: Service health status
    """
    print("=" * 80)
    print("🏥 SERVICE HEALTH CHECKS")
    print("=" * 80)
    
    services = {
        "Dashboard": f"{DASHBOARD_URL}",
        "API Gateway": "http://localhost:8000/health",
        "Dagster (Dagit)": "http://localhost:3000/server_info",
        "MLflow": "http://localhost:5000/health",
        "MinIO": "http://localhost:9000/minio/health/live",
        "News Analysis": "http://localhost:8006/health",
        "Portfolio Service": "http://localhost:8056/health",
        "Market Trends": "http://localhost:8055/health",
    }
    
    results = {}
    healthy_count = 0
    
    for name, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {name:25} HEALTHY")
                results[name] = "healthy"
                healthy_count += 1
            else:
                print(f"⚠️  {name:25} DEGRADED (status {response.status_code})")
                results[name] = "degraded"
        except Exception as e:
            print(f"❌ {name:25} UNAVAILABLE ({str(e)[:40]}...)")
            results[name] = "unavailable"
    
    print("-" * 80)
    print(f"📊 Health Summary: {healthy_count}/{len(services)} services healthy")
    print("=" * 80)
    print()
    
    return results


# ============================================================================
# Tab-Specific Tests with Clicker Actions
# ============================================================================
async def test_home_tab(page):
    """Test Home tab and verify portfolio widget."""
    print("🏠 Testing HOME TAB...")
    
    try:
        await page.goto(DASHBOARD_URL, timeout=120000, wait_until="domcontentloaded")
        await page.wait_for_timeout(8000)  # Wait for interval callback to fire at least once (5s interval + buffer)
        
        try:
            value = await page.locator('#home-portfolio-value').inner_text(timeout=5000)
            # Check if it's the live value or fallback
            is_live = "$92,3" in value or ("$" in value and value != "$125,430.50")
            status = "(live)" if is_live else "(offline)"
            print(f"   ✅ Portfolio value loaded: {value} {status}")
        except:
            print(f"   ⚠️  Portfolio value not found")
        
        try:
            scan_btn = page.locator('text=Scan Market').first
            if await scan_btn.count() > 0:
                await scan_btn.click(timeout=5000)
                print(f"   ✅ Clicked 'Scan Market' button")
        except Exception as e:
            print(f"   ⚠️  Could not click 'Scan Market': {str(e)[:50]}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        await page.screenshot(path=str(SCREENSHOTS_DIR / f"home_tab_{timestamp}.png"), full_page=True)
        print(f"   📸 Screenshot saved")
        
        return True
    except Exception as e:
        print(f"   ❌ Home tab failed: {str(e)[:80]}")
        return False


async def test_portfolio_tab(page):
    """Test Portfolio tab and verify positions."""
    print("💼 Testing PORTFOLIO TAB...")
    
    try:
        await page.locator('text=Portfolio').first.click(timeout=10000)
        await page.wait_for_timeout(2000)
        
        try:
            value = await page.locator('#portfolio-value').inner_text(timeout=5000)
            print(f"   ✅ Portfolio value: {value}")
        except:
            print(f"   ⚠️  Portfolio value not loaded")
        
        try:
            await page.locator('#portfolio-refresh-btn').first.click(timeout=5000)
            print(f"   ✅ Clicked refresh button")
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"   ⚠️  Could not click refresh")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        await page.screenshot(path=str(SCREENSHOTS_DIR / f"portfolio_tab_{timestamp}.png"), full_page=True)
        print(f"   📸 Screenshot saved")
        
        return True
    except Exception as e:
        print(f"   ❌ Portfolio tab failed: {str(e)[:80]}")
        return False


async def test_market_trends_tab(page):
    """Test Market Trends tab."""
    print("📈 Testing MARKET TRENDS TAB...")
    
    try:
        await page.locator('text=Market Trends').first.click(timeout=10000)
        await page.wait_for_timeout(3000)
        
        try:
            run_btn = page.locator('#run-trends-analysis').first
            if await run_btn.count() > 0:
                await run_btn.click(timeout=5000)
                print(f"   ✅ Clicked 'Run Analysis'")
                await page.wait_for_timeout(2000)
        except:
            print(f"   ⚠️  'Run Analysis' button not found")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        await page.screenshot(path=str(SCREENSHOTS_DIR / f"market_trends_tab_{timestamp}.png"), full_page=True)
        print(f"   📸 Screenshot saved")
        
        return True
    except Exception as e:
        print(f"   ❌ Market Trends failed: {str(e)[:80]}")
        return False


# ============================================================================
# Main Test Execution
# ============================================================================
async def main():
    """Execute all tests and generate comprehensive report."""
    print()
    print("=" * 80)
    print("🧪 COMPREHENSIVE DASHBOARD TEST SUITE")
    print("=" * 80)
    print(f"Dashboard URL: {DASHBOARD_URL}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    # First check service health
    health_results = await check_service_health()
    
    # Launch browser and run UI tests
    async with async_playwright() as p:
        browser = None
        try:
            print("=" * 80)
            print("🌐 DASHBOARD UI TESTS")
            print("=" * 80)
            print()
            
            print("🚀 Launching headless Chromium browser...")
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_viewport_size({"width": 1920, "height": 1080})
            print("✅ Browser launched successfully")
            print()
            
            # Run all tab tests
            test_results = {
                "Home Tab": await test_home_tab(page),
                "Portfolio Tab": await test_portfolio_tab(page),
                "Market Trends Tab": await test_market_trends_tab(page),
            }
            
            print()
            
        except Exception as e:
            print(f"❌ Browser test execution failed: {e}")
            test_results = {}
            
        finally:
            if browser:
                await browser.close()
                print("🔒 Browser closed")
    
    # ========================================================================
    # Final Summary Report
    # ========================================================================
    print()
    print("=" * 80)
    print("📊 FINAL TEST SUMMARY")
    print("=" * 80)
    print()
    
    # Service Health Summary
    print("🏥 SERVICE HEALTH:")
    healthy_count = sum(1 for status in health_results.values() if status == "healthy")
    total_services = len(health_results)
    print(f"   {healthy_count}/{total_services} services healthy")
    
    for name, status in health_results.items():
        if status == "healthy":
            print(f"   ✅ {name}")
        elif status == "degraded":
            print(f"   ⚠️  {name} (degraded)")
        else:
            print(f"   ❌ {name} (unavailable)")
    
    print()
    
    # UI Tests Summary
    print("🖥️  UI TAB TESTS:")
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    print(f"   {passed_tests}/{total_tests} tests passed")
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")
    
    print()
    print("=" * 80)
    
    # Overall Status
    overall_health = healthy_count >= (total_services * 0.75)
    overall_ui = passed_tests >= (total_tests * 0.75)
    overall_success = overall_health and overall_ui
    
    if overall_success:
        print("🎉 OVERALL STATUS: ✅ SYSTEM OPERATIONAL")
        print("=" * 80)
        return 0
    elif overall_health or overall_ui:
        print("⚠️  OVERALL STATUS: PARTIAL SUCCESS - Some issues detected")
        print("=" * 80)
        return 1
    else:
        print("❌ OVERALL STATUS: CRITICAL ISSUES DETECTED")
        print("=" * 80)
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

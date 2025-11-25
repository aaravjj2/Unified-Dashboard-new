#!/usr/bin/env python3
"""
Phase 7C: Comprehensive Market Forecast Tab Testing

Tests:
1. Portfolio data loading
2. Market Forecast tab rendering
3. Forecast generation
4. SHAP data integration
5. UI elements and interactions
"""

import sys
import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from datetime import datetime
from pathlib import Path

# Test configuration
BASE_URL = "http://localhost:8050"
TIMEOUT = 30
TEST_RESULTS = []

def setup_driver():
    """Setup headless Chrome driver"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"❌ Failed to setup Chrome driver: {e}")
        return None

def print_header(title):
    print("\n" + "="*80)
    print(f"{title}")
    print("="*80)

def print_result(test_name, passed, message=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if message:
        print(f"   {message}")
    
    TEST_RESULTS.append({
        "test": test_name,
        "passed": passed,
        "message": message
    })

def test_dashboard_health():
    """Test 1: Dashboard health check"""
    print_header("TEST 1: DASHBOARD HEALTH CHECK")
    
    try:
        response = requests.get(BASE_URL, timeout=TIMEOUT)
        if response.status_code == 200:
            print_result("Dashboard accessible", True, f"Status: {response.status_code}")
            return True
        else:
            print_result("Dashboard accessible", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_result("Dashboard accessible", False, str(e))
        return False

def test_market_forecast_tab(driver):
    """Test 2: Market Forecast tab loads"""
    print_header("TEST 2: MARKET FORECAST TAB LOADING")
    
    if not driver:
        print_result("Market Forecast tab", False, "No driver available")
        return False
    
    try:
        driver.get(BASE_URL)
        time.sleep(3)
        
        # Look for Market Forecast tab
        tabs = driver.find_elements(By.CSS_SELECTOR, "[role='tab']")
        market_forecast_found = False
        for tab in tabs:
            if "Market Forecast" in tab.text:
                market_forecast_found = True
                print_result("Market Forecast tab exists", True, "Tab found in navigation")
                
                # Click the tab
                tab.click()
                time.sleep(2)
                
                # Check if content loaded
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "mf-ticker-selector"))
                    )
                    print_result("Market Forecast content loaded", True, "Ticker selector found")
                    return True
                except:
                    print_result("Market Forecast content loaded", False, "Ticker selector not found")
                    return False
        
        if not market_forecast_found:
            print_result("Market Forecast tab exists", False, "Tab not found in navigation")
            return False
            
    except Exception as e:
        print_result("Market Forecast tab", False, str(e))
        return False

def test_forecast_generation(driver):
    """Test 3: Forecast generation works"""
    print_header("TEST 3: FORECAST GENERATION")
    
    if not driver:
        print_result("Forecast generation", False, "No driver available")
        return False
    
    try:
        # Click generate button
        generate_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "mf-generate-btn"))
        )
        generate_btn.click()
        print_result("Generate button clicked", True, "Button is clickable")
        
        # Wait for results (summary cards should appear)
        time.sleep(5)
        
        # Check if summary cards appeared
        try:
            summary = driver.find_element(By.ID, "mf-summary-cards")
            if summary.text:
                print_result("Summary cards generated", True, "Cards contain data")
            else:
                print_result("Summary cards generated", False, "Cards are empty")
                return False
        except:
            print_result("Summary cards generated", False, "Cards not found")
            return False
        
        # Check if charts rendered
        try:
            returns_chart = driver.find_element(By.ID, "mf-returns-chart")
            volatility_chart = driver.find_element(By.ID, "mf-volatility-chart")
            print_result("Charts rendered", True, "Both charts found")
        except:
            print_result("Charts rendered", False, "Charts not found")
            return False
        
        # Check if details table populated
        try:
            details = driver.find_element(By.ID, "mf-details-table")
            if details.text:
                print_result("Details table populated", True, "Table contains data")
                return True
            else:
                print_result("Details table populated", False, "Table is empty")
                return False
        except:
            print_result("Details table populated", False, "Table not found")
            return False
            
    except Exception as e:
        print_result("Forecast generation", False, str(e))
        return False

def test_data_integrity():
    """Test 4: Data integrity check"""
    print_header("TEST 4: DATA INTEGRITY CHECK")
    
    import subprocess
    
    # Check portfolio data
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "dash_app", "cat", "/app/cache/portfolio_data.json"],
        capture_output=True,
        text=True
    )
    
    try:
        portfolio = json.loads(result.stdout)
        num_positions = len(portfolio.get("positions", []))
        print_result("Portfolio data valid", num_positions >= 40, f"{num_positions} positions")
    except:
        print_result("Portfolio data valid", False, "Failed to parse portfolio data")
        return False
    
    # Check market brief
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "dash_app", "cat", "/app/cache/market_brief.json"],
        capture_output=True,
        text=True
    )
    
    try:
        market = json.loads(result.stdout)
        num_tickers = market.get("num_tickers", 0)
        print_result("Market brief valid", num_tickers >= 40, f"{num_tickers} tickers")
    except:
        print_result("Market brief valid", False, "Failed to parse market brief")
        return False
    
    # Check SHAP data
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "dash_app", "cat", "/app/explain/picks_explain_20251024.json"],
        capture_output=True,
        text=True
    )
    
    try:
        shap = json.loads(result.stdout)
        if 'explanations' in shap:
            explanations = shap['explanations']
        else:
            explanations = shap
        num_tickers = len(explanations)
        print_result("SHAP data valid", num_tickers >= 40, f"{num_tickers} tickers")
        return True
    except:
        print_result("SHAP data valid", False, "Failed to parse SHAP data")
        return False

def generate_report():
    """Generate test report"""
    print_header("TEST SUMMARY")
    
    total_tests = len(TEST_RESULTS)
    passed_tests = sum(1 for r in TEST_RESULTS if r["passed"])
    failed_tests = total_tests - passed_tests
    
    print(f"\n📊 Results: {passed_tests}/{total_tests} tests passed\n")
    
    for result in TEST_RESULTS:
        status = "✅" if result["passed"] else "❌"
        print(f"{status} {result['test']}")
        if result["message"]:
            print(f"   {result['message']}")
    
    print(f"\n{'='*80}")
    if failed_tests == 0:
        print("🎉 ALL TESTS PASSED")
        print("✅ Market Forecast tab fully functional")
    else:
        print(f"⚠️  {failed_tests} TEST(S) FAILED")
        print("❌ Review failures before proceeding")
    print(f"{'='*80}\n")
    
    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "total": total_tests,
        "passed": passed_tests,
        "failed": failed_tests,
        "results": TEST_RESULTS
    }
    
    report_path = "/tmp/phase7c_test_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"📝 Report saved: {report_path}\n")
    
    return failed_tests == 0

if __name__ == "__main__":
    print("\n" + "="*80)
    print("PHASE 7C: MARKET FORECAST TAB TESTING")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Target: {BASE_URL}")
    print("="*80)
    
    # Test 1: Dashboard health
    test_dashboard_health()
    
    # Test 4: Data integrity (can run without browser)
    test_data_integrity()
    
    # Test 2-3: Browser tests
    driver = setup_driver()
    if driver:
        try:
            test_market_forecast_tab(driver)
            test_forecast_generation(driver)
        finally:
            driver.quit()
    else:
        print_result("Browser tests", False, "Could not setup Chrome driver - skipping UI tests")
    
    # Generate report
    success = generate_report()
    sys.exit(0 if success else 1)

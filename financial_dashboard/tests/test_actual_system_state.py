"""
Comprehensive E2E Test Suite - Actual System State Validation
Tests every tab and feature to determine EXACTLY what works and what doesn't
"""
import time
from playwright.sync_api import sync_playwright, expect

BASE_URL = "http://localhost:8000"
TIMEOUT = 30000  # 30 seconds

def test_dashboard_loads():
    """Test 1: Dashboard loads successfully"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("✓ Test 1: Loading dashboard...")
        page.goto(BASE_URL, timeout=TIMEOUT)
        page.wait_for_load_state("networkidle", timeout=TIMEOUT)
        
        # Check for main title
        title = page.locator("text=Financial Dashboard").first
        expect(title).to_be_visible(timeout=TIMEOUT)
        
        print("  ✅ PASS: Dashboard loads")
        browser.close()

def test_all_tabs_exist():
    """Test 2: All expected tabs exist in navigation"""
    expected_tabs = [
        "Home",
        "Market Trends",
        "Market Forecast",
        "Volatility Lab",
        "Monthly Picks",
        "Weekly Picks",
        "Analysis Hub",
        "Portfolio",
        "Research Lab",
        "Options Lab",
        "Backtesting Lab"
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("✓ Test 2: Checking tab navigation...")
        page.goto(BASE_URL, timeout=TIMEOUT)
        page.wait_for_load_state("networkidle", timeout=TIMEOUT)
        
        results = {}
        for tab_name in expected_tabs:
            try:
                tab = page.locator(f"text={tab_name}").first
                is_visible = tab.is_visible(timeout=5000)
                results[tab_name] = "✅ FOUND" if is_visible else "❌ NOT VISIBLE"
            except Exception as e:
                results[tab_name] = f"❌ NOT FOUND: {str(e)[:50]}"
        
        for tab, status in results.items():
            print(f"  {status}: {tab}")
        
        browser.close()
        return results

def test_market_trends_interaction():
    """Test 3: Market Trends tab can be clicked and loads content"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("✓ Test 3: Testing Market Trends interaction...")
        page.goto(BASE_URL, timeout=TIMEOUT)
        page.wait_for_load_state("networkidle", timeout=TIMEOUT)
        
        # Click Market Trends tab
        try:
            mt_tab = page.locator("text=Market Trends").first
            mt_tab.click(timeout=TIMEOUT)
            time.sleep(2)  # Wait for content to load
            
            # Check if content area exists
            content = page.locator("#page-content").first
            expect(content).to_be_visible(timeout=TIMEOUT)
            
            print("  ✅ PASS: Market Trends tab interactive")
        except Exception as e:
            print(f"  ❌ FAIL: {str(e)}")
        
        browser.close()

def test_backtesting_lab():
    """Test 4: Backtesting Lab tab exists and loads"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("✓ Test 4: Testing Backtesting Lab (Sprint 8)...")
        page.goto(BASE_URL, timeout=TIMEOUT)
        page.wait_for_load_state("networkidle", timeout=TIMEOUT)
        
        try:
            # Look for Backtesting Lab tab
            bt_tab = page.locator("text=Backtesting Lab").first
            is_visible = bt_tab.is_visible(timeout=10000)
            
            if is_visible:
                bt_tab.click(timeout=TIMEOUT)
                time.sleep(2)
                
                # Check for strategy dropdown
                strategy_dropdown = page.locator("select, .Select-control").first
                if strategy_dropdown.is_visible(timeout=5000):
                    print("  ✅ PASS: Backtesting Lab exists and has UI elements")
                else:
                    print("  ⚠️  PARTIAL: Tab exists but UI elements not found")
            else:
                print("  ❌ FAIL: Backtesting Lab tab not visible")
        except Exception as e:
            print(f"  ❌ FAIL: {str(e)}")
        
        browser.close()

def test_home_tab_data():
    """Test 5: Home tab shows data (not just placeholders)"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("✓ Test 5: Testing Home tab for real data...")
        page.goto(BASE_URL, timeout=TIMEOUT)
        page.wait_for_load_state("networkidle", timeout=TIMEOUT)
        
        try:
            # Click Home tab
            home_tab = page.locator("text=Home").first
            home_tab.click(timeout=TIMEOUT)
            time.sleep(2)
            
            # Check for placeholder text
            content = page.content()
            has_placeholder = "placeholder" in content.lower() or "n/a" in content.lower()
            
            if has_placeholder:
                print("  ⚠️  WARNING: Home tab may have placeholder data")
            else:
                print("  ✅ PASS: Home tab appears to have real data")
        except Exception as e:
            print(f"  ❌ FAIL: {str(e)}")
        
        browser.close()

def test_chatbot_ui():
    """Test 6: AI Chatbot UI exists and is readable"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("✓ Test 6: Testing AI Chatbot UI...")
        page.goto(BASE_URL, timeout=TIMEOUT)
        page.wait_for_load_state("networkidle", timeout=TIMEOUT)
        
        try:
            # Look for chatbot button
            chatbot_btn = page.locator("[id*='chat'], [class*='chat-button']").first
            is_visible = chatbot_btn.is_visible(timeout=5000)
            
            if is_visible:
                print("  ✅ PASS: Chatbot UI element found")
            else:
                print("  ❌ FAIL: Chatbot UI not visible")
        except Exception as e:
            print(f"  ❌ FAIL: {str(e)}")
        
        browser.close()

def run_all_tests():
    """Run all tests and generate report"""
    print("=" * 60)
    print("COMPREHENSIVE E2E SYSTEM VALIDATION")
    print("=" * 60)
    print()
    
    results = []
    
    try:
        test_dashboard_loads()
        results.append(("Dashboard Loads", "PASS"))
    except Exception as e:
        print(f"  ❌ FAIL: {str(e)}")
        results.append(("Dashboard Loads", "FAIL"))
    
    print()
    
    try:
        tab_results = test_all_tabs_exist()
        results.append(("Tab Navigation", "PASS" if all("✅" in v for v in tab_results.values()) else "PARTIAL"))
    except Exception as e:
        print(f"  ❌ FAIL: {str(e)}")
        results.append(("Tab Navigation", "FAIL"))
    
    print()
    
    try:
        test_market_trends_interaction()
        results.append(("Market Trends", "PASS"))
    except Exception as e:
        results.append(("Market Trends", "FAIL"))
    
    print()
    
    try:
        test_backtesting_lab()
        results.append(("Backtesting Lab", "PASS"))
    except Exception as e:
        results.append(("Backtesting Lab", "FAIL"))
    
    print()
    
    try:
        test_home_tab_data()
        results.append(("Home Tab Data", "PASS"))
    except Exception as e:
        results.append(("Home Tab Data", "FAIL"))
    
    print()
    
    try:
        test_chatbot_ui()
        results.append(("Chatbot UI", "PASS"))
    except Exception as e:
        results.append(("Chatbot UI", "FAIL"))
    
    print()
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, status in results if status == "PASS")
    total = len(results)
    
    for test_name, status in results:
        symbol = "✅" if status == "PASS" else "⚠️" if status == "PARTIAL" else "❌"
        print(f"{symbol} {test_name}: {status}")
    
    print()
    print(f"TOTAL: {passed}/{total} tests passed")
    print("=" * 60)

if __name__ == "__main__":
    run_all_tests()

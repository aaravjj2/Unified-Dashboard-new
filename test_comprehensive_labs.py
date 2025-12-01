"""
Comprehensive test for Strategy Lab, Research Lab, Volatility Lab, Chatbot, and Stock Picks
"""
import sys
import time
from playwright.sync_api import sync_playwright, expect

BASE_URL = "http://localhost:8051"

def test_all_components():
    """Test all dashboard components"""
    results = {
        'strategy_lab': {'status': 'not_tested', 'details': []},
        'research_lab': {'status': 'not_tested', 'details': []},
        'volatility_lab': {'status': 'not_tested', 'details': []},
        'stock_picks': {'status': 'not_tested', 'details': []},
        'chatbot': {'status': 'not_tested', 'details': []}
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        # Console error tracking
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        
        try:
            print("=" * 60)
            print("COMPREHENSIVE DASHBOARD TEST")
            print("=" * 60)
            
            # Load dashboard
            print("\n1. Loading dashboard...")
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            print("   ✅ Dashboard loaded")
            
            # ============================================================
            # TEST STOCK PICKS
            # ============================================================
            print("\n2. Testing Stock Picks...")
            try:
                # Click Stock Picks tab
                picks_tab = page.locator("a.nav-link:has-text('Stock Picks'), button:has-text('Stock Picks')")
                if picks_tab.count() > 0:
                    picks_tab.first.click()
                    time.sleep(2)
                    
                    # Check for weekly picks table
                    table = page.locator("#weekly-table, .dash-table-container, table")
                    if table.count() > 0:
                        results['stock_picks']['details'].append("Weekly picks table found")
                        
                        # Check for ticker data
                        nvda = page.locator("text=NVDA")
                        aapl = page.locator("text=AAPL")
                        if nvda.count() > 0 and aapl.count() > 0:
                            results['stock_picks']['details'].append("Ticker data (NVDA, AAPL) visible")
                            results['stock_picks']['status'] = 'passed'
                        else:
                            results['stock_picks']['details'].append("Ticker data not visible")
                            results['stock_picks']['status'] = 'partial'
                    else:
                        results['stock_picks']['details'].append("Table not found")
                        results['stock_picks']['status'] = 'failed'
                else:
                    results['stock_picks']['details'].append("Stock Picks tab not found")
                    results['stock_picks']['status'] = 'failed'
                    
            except Exception as e:
                results['stock_picks']['status'] = 'error'
                results['stock_picks']['details'].append(f"Error: {str(e)}")
            
            print(f"   Status: {results['stock_picks']['status']}")
            for d in results['stock_picks']['details']:
                print(f"   - {d}")
            
            # ============================================================
            # TEST STRATEGY LAB
            # ============================================================
            print("\n3. Testing Strategy Lab...")
            try:
                # Click Strategy Lab tab
                sl_tab = page.locator("a.nav-link:has-text('Strategy Lab'), button:has-text('Strategy Lab')")
                if sl_tab.count() > 0:
                    sl_tab.first.click()
                    time.sleep(2)
                    
                    # Check for subtabs
                    setup_tab = page.locator("text=Setup, button:has-text('Setup')")
                    backtest_tab = page.locator("text=Backtest")
                    
                    if setup_tab.count() > 0:
                        results['strategy_lab']['details'].append("Setup subtab found")
                    if backtest_tab.count() > 0:
                        results['strategy_lab']['details'].append("Backtest subtab found")
                    
                    # Check for strategy type dropdown
                    strategy_dropdown = page.locator("#sl-strategy-type")
                    if strategy_dropdown.count() > 0:
                        results['strategy_lab']['details'].append("Strategy type dropdown found")
                    
                    # Check for ticker input
                    ticker_input = page.locator("#sl-tickers-input")
                    if ticker_input.count() > 0:
                        results['strategy_lab']['details'].append("Ticker input found")
                    
                    if len(results['strategy_lab']['details']) >= 2:
                        results['strategy_lab']['status'] = 'passed'
                    else:
                        results['strategy_lab']['status'] = 'partial'
                else:
                    results['strategy_lab']['details'].append("Strategy Lab tab not found")
                    results['strategy_lab']['status'] = 'failed'
                    
            except Exception as e:
                results['strategy_lab']['status'] = 'error'
                results['strategy_lab']['details'].append(f"Error: {str(e)}")
            
            print(f"   Status: {results['strategy_lab']['status']}")
            for d in results['strategy_lab']['details']:
                print(f"   - {d}")
            
            # ============================================================
            # TEST RESEARCH LAB
            # ============================================================
            print("\n4. Testing Research Lab...")
            try:
                # Click Research Lab tab
                rl_tab = page.locator("a.nav-link:has-text('Research Lab'), button:has-text('Research Lab')")
                if rl_tab.count() > 0:
                    rl_tab.first.click()
                    time.sleep(2)
                    
                    # Check for subtabs
                    scan_tab = page.locator("text=Market Scan")
                    factor_tab = page.locator("text=Factor Analysis")
                    
                    if scan_tab.count() > 0:
                        results['research_lab']['details'].append("Market Scan subtab found")
                    if factor_tab.count() > 0:
                        results['research_lab']['details'].append("Factor Analysis subtab found")
                    
                    # Check for ticker input in Market Scan
                    ticker_input = page.locator("#rl-scan-ticker, input[placeholder*='ticker'], #market-scan-tickers")
                    if ticker_input.count() > 0:
                        results['research_lab']['details'].append("Ticker input found")
                    
                    if len(results['research_lab']['details']) >= 2:
                        results['research_lab']['status'] = 'passed'
                    else:
                        results['research_lab']['status'] = 'partial'
                else:
                    results['research_lab']['details'].append("Research Lab tab not found")
                    results['research_lab']['status'] = 'failed'
                    
            except Exception as e:
                results['research_lab']['status'] = 'error'
                results['research_lab']['details'].append(f"Error: {str(e)}")
            
            print(f"   Status: {results['research_lab']['status']}")
            for d in results['research_lab']['details']:
                print(f"   - {d}")
            
            # ============================================================
            # TEST VOLATILITY LAB
            # ============================================================
            print("\n5. Testing Volatility Lab...")
            try:
                # Click Volatility Lab tab
                vl_tab = page.locator("a.nav-link:has-text('Volatility Lab'), button:has-text('Volatility Lab')")
                if vl_tab.count() > 0:
                    vl_tab.first.click()
                    time.sleep(2)
                    
                    # Check for IV Surface elements
                    ticker_input = page.locator("#vl-calc-ticker")
                    compute_btn = page.locator("#vl-calc-run-btn, button:has-text('Compute')")
                    heatmap = page.locator("#vl-heatmap")
                    
                    if ticker_input.count() > 0:
                        results['volatility_lab']['details'].append("Ticker input found")
                    if compute_btn.count() > 0:
                        results['volatility_lab']['details'].append("Compute button found")
                    if heatmap.count() > 0:
                        results['volatility_lab']['details'].append("Heatmap container found")
                    
                    # Check for subtabs
                    signals_tab = page.locator("text=Signals")
                    backtest_tab = page.locator("text=Backtest")
                    
                    if signals_tab.count() > 0:
                        results['volatility_lab']['details'].append("Signals subtab found")
                    if backtest_tab.count() > 0:
                        results['volatility_lab']['details'].append("Backtest subtab found")
                    
                    if len(results['volatility_lab']['details']) >= 3:
                        results['volatility_lab']['status'] = 'passed'
                    else:
                        results['volatility_lab']['status'] = 'partial'
                else:
                    results['volatility_lab']['details'].append("Volatility Lab tab not found")
                    results['volatility_lab']['status'] = 'failed'
                    
            except Exception as e:
                results['volatility_lab']['status'] = 'error'
                results['volatility_lab']['details'].append(f"Error: {str(e)}")
            
            print(f"   Status: {results['volatility_lab']['status']}")
            for d in results['volatility_lab']['details']:
                print(f"   - {d}")
            
            # ============================================================
            # TEST CHATBOT
            # ============================================================
            print("\n6. Testing AI Chatbot...")
            try:
                # Look for chatbot FAB (floating action button)
                chatbot_fab = page.locator("#chatbot-fab, .chatbot-fab, button:has-text('Chat'), [class*='chat']")
                chatbot_container = page.locator("#chatbot-container, .chatbot-container, [id*='chatbot']")
                
                if chatbot_fab.count() > 0:
                    results['chatbot']['details'].append("Chatbot FAB button found")
                    
                    # Try to click it
                    try:
                        chatbot_fab.first.click()
                        time.sleep(1)
                        
                        # Check if chat panel opened
                        chat_input = page.locator("#chatbot-input, textarea[id*='chat'], input[id*='chat']")
                        if chat_input.count() > 0:
                            results['chatbot']['details'].append("Chat input field found")
                            
                            # Try sending a message
                            chat_input.first.fill("Hello, what can you help me with?")
                            
                            send_btn = page.locator("#chatbot-send, button:has-text('Send'), button[type='submit']")
                            if send_btn.count() > 0:
                                results['chatbot']['details'].append("Send button found")
                                results['chatbot']['status'] = 'passed'
                            else:
                                results['chatbot']['status'] = 'partial'
                        else:
                            results['chatbot']['details'].append("Chat input not found after clicking FAB")
                            results['chatbot']['status'] = 'partial'
                    except Exception as e:
                        results['chatbot']['details'].append(f"Could not interact with chatbot: {str(e)}")
                        results['chatbot']['status'] = 'partial'
                        
                elif chatbot_container.count() > 0:
                    results['chatbot']['details'].append("Chatbot container found")
                    results['chatbot']['status'] = 'partial'
                else:
                    results['chatbot']['details'].append("Chatbot UI elements not found")
                    results['chatbot']['status'] = 'failed'
                    
            except Exception as e:
                results['chatbot']['status'] = 'error'
                results['chatbot']['details'].append(f"Error: {str(e)}")
            
            print(f"   Status: {results['chatbot']['status']}")
            for d in results['chatbot']['details']:
                print(f"   - {d}")
            
            # Take screenshot
            page.screenshot(path="/home/aarav/Unified-Dashboard/test_comprehensive.png", full_page=True)
            print("\n   📸 Screenshot saved to test_comprehensive.png")
            
            # Console errors summary
            if console_errors:
                print(f"\n⚠️ Console errors detected: {len(console_errors)}")
                for err in console_errors[:5]:
                    print(f"   - {err[:100]}...")
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for component, result in results.items():
        status_icon = "✅" if result['status'] == 'passed' else ("⚠️" if result['status'] == 'partial' else "❌")
        print(f"{status_icon} {component}: {result['status']}")
        if result['status'] not in ['passed']:
            all_passed = False
    
    print("\n" + "=" * 60)
    
    return all_passed

if __name__ == "__main__":
    success = test_all_components()
    sys.exit(0 if success else 1)

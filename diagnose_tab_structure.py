#!/usr/bin/env python3
"""
Diagnostic test to verify tab structure and identify issues
"""

from playwright.sync_api import sync_playwright
import time
import json

def diagnose_tabs():
    """Check all tabs for structural issues"""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        print("="*80)
        print("TAB STRUCTURE DIAGNOSTIC")
        print("="*80)
        
        page.goto('http://localhost:8051', timeout=60000)
        time.sleep(8)
        
        tabs_to_check = [
            'Market Trends',
            'Market Forecast',
            'Strategy Lab',
            'Volatility Lab',
            'Research Lab',
        ]
        
        for tab_name in tabs_to_check:
            print(f"\n{'='*80}")
            print(f"CHECKING: {tab_name}")
            print('='*80)
            
            try:
                # Find and click tab
                tab_selectors = [
                    f'text="{tab_name}"',
                    f'button:has-text("{tab_name}")',
                    f'a:has-text("{tab_name}")',
                ]
                
                clicked = False
                for selector in tab_selectors:
                    try:
                        elem = page.locator(selector).first
                        if elem.count() > 0:
                            elem.click()
                            clicked = True
                            print(f"✅ Clicked tab using: {selector}")
                            break
                    except:
                        continue
                
                if not clicked:
                    print(f"❌ Could not click {tab_name}")
                    continue
                
                time.sleep(3)
                
                # Get page content for analysis
                content = page.content()
                
                # Check for specific issues
                if tab_name == "Research Lab":
                    has_subtabs = page.locator('[id*="research"][id*="tab"], .nav-tabs').count() > 0
                    has_content = page.locator('#research-lab-content, #research-notes, #market-scan').count() > 0
                    print(f"   Has subtabs: {has_subtabs}")
                    print(f"   Has content div: {has_content}")
                    
                    # List visible subtabs
                    subtabs = page.locator('.nav-tabs .nav-link').all()
                    print(f"   Visible subtabs: {len(subtabs)}")
                    for i, st in enumerate(subtabs[:10]):
                        try:
                            text = st.inner_text()
                            print(f"      - {text}")
                        except:
                            pass
                
                elif tab_name == "Market Trends":
                    has_table = page.locator('table, #market-trends-sentinel-table').count() > 0
                    has_cached_data = 'cached' in content.lower() or 'last updated' in content.lower()
                    has_buttons = page.locator('#reload-model, #toggle-brief, #mt-download-btn').count()
                    
                    print(f"   Has table: {has_table}")
                    print(f"   Has cached data text: {has_cached_data}")
                    print(f"   Buttons found: {has_buttons}/3")
                    
                    # Check for empty state
                    empty_indicators = ['no data', 'no results', 'run analysis', 'get started']
                    has_empty_state = any(ind in content.lower() for ind in empty_indicators)
                    print(f"   Shows empty state: {has_empty_state}")
                
                elif tab_name == "Strategy Lab":
                    has_backtest_btn = page.locator('#backtest-btn, button:has-text("Run Backtest")').count() > 0
                    has_ticker_input = page.locator('#sl-ticker-input, #tickers-input').count() > 0
                    has_results_area = page.locator('#backtest-results, #sl-results').count() > 0
                    
                    print(f"   Has backtest button: {has_backtest_btn}")
                    print(f"   Has ticker input: {has_ticker_input}")
                    print(f"   Has results area: {has_results_area}")
                
                elif tab_name == "Volatility Lab":
                    has_subtabs = page.locator('[id*="vol"][id*="tab"], .nav-tabs').count() > 0
                    has_heatmap = page.locator('#vl-heatmap, [id*="heatmap"]').count() > 0
                    
                    print(f"   Has subtabs: {has_subtabs}")
                    print(f"   Has heatmap: {has_heatmap}")
                    
                    # Check structure type
                    if has_subtabs:
                        print(f"   ✅ Using modular structure")
                    else:
                        print(f"   ⚠️  Using older single-page structure")
                
                elif tab_name == "Market Forecast":
                    has_forecast_btn = page.locator('#run-forecast, button:has-text("Run Forecast")').count() > 0
                    has_ticker_input = page.locator('#mf-ticker, #mf-ticker-input').count() > 0
                    has_results = page.locator('#mf-results, #forecast-results').count() > 0
                    
                    print(f"   Has forecast button: {has_forecast_btn}")
                    print(f"   Has ticker input: {has_ticker_input}")
                    print(f"   Has results area: {has_results}")
                
                # Take screenshot
                filename = f"/home/aarav/unified-dashboard/test_screenshots/diagnostic_{tab_name.replace(' ', '_').lower()}.png"
                page.screenshot(path=filename, full_page=True)
                print(f"   📸 Screenshot: {filename}")
                
            except Exception as e:
                print(f"❌ Error checking {tab_name}: {e}")
        
        print("\n" + "="*80)
        print("Browser will stay open for 15 seconds for manual inspection...")
        time.sleep(15)
        
        browser.close()
        
        print("\n✅ DIAGNOSTIC COMPLETE")

if __name__ == '__main__':
    diagnose_tabs()

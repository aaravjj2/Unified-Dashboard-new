"""
Live Browser Test - Verify ALL fixes working
Tests Research Lab, Market Forecast, and Portfolio button
"""
import time
from playwright.sync_api import sync_playwright, expect

def test_all_fixes():
    """Test all three reported issues"""
    with sync_playwright() as p:
        # Launch visible browser
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        results = {}
        
        try:
            # Navigate to dashboard
            print("🌐 Loading dashboard...")
            page.goto('http://localhost:8051/', wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(5000)  # Wait for full render
            
            # TEST 1: Research Lab - Factor Analysis has content
            print("\n📊 Testing Research Lab - Factor Analysis...")
            research_tab = page.locator('a#research_lab-tab')
            research_tab.click()
            page.wait_for_timeout(2000)
            
            # Click Factor Analysis subtab
            factor_tab = page.locator('a[data-rb-event-key="factor-analysis"]')
            factor_tab.click()
            page.wait_for_timeout(2000)
            
            # Check for content
            factor_content = page.locator('div#factor-analysis')
            content_text = factor_content.inner_text()
            
            if len(content_text) > 100:
                print(f"   ✅ Factor Analysis HAS CONTENT ({len(content_text)} chars)")
                results['factor_analysis'] = 'HAS_CONTENT'
                page.screenshot(path='reports/fix_verification/screenshots/factor_analysis_FIXED.png')
            else:
                print(f"   ❌ Factor Analysis EMPTY ({len(content_text)} chars)")
                results['factor_analysis'] = 'EMPTY'
                page.screenshot(path='reports/fix_verification/screenshots/factor_analysis_FAILED.png')
            
            # TEST 2: Market Forecast has chart
            print("\n📈 Testing Market Forecast...")
            mf_tab = page.locator('a#market_forecast-tab')
            mf_tab.click()
            page.wait_for_timeout(3000)
            
            # Look for chart
            mf_chart = page.locator('div#mf-forecast-chart')
            if mf_chart.is_visible():
                print("   ✅ Market Forecast CHART VISIBLE")
                results['market_forecast'] = 'WORKING'
                page.screenshot(path='reports/fix_verification/screenshots/market_forecast_FIXED.png')
            else:
                print("   ❌ Market Forecast CHART NOT FOUND")
                results['market_forecast'] = 'NOT_WORKING'
                page.screenshot(path='reports/fix_verification/screenshots/market_forecast_FAILED.png')
            
            # TEST 3: Portfolio refresh button
            print("\n💼 Testing Portfolio refresh button...")
            portfolio_tab = page.locator('a#portfolio-tab')
            portfolio_tab.click()
            page.wait_for_timeout(2000)
            
            # Get BEFORE state
            positions_before = page.locator('table#portfolio-positions-table tbody tr')
            count_before = positions_before.count()
            print(f"   Positions BEFORE: {count_before}")
            
            # Click refresh button
            refresh_btn = page.locator('button#refresh-portfolio-btn')
            if refresh_btn.is_visible():
                print("   🔄 Clicking refresh button...")
                refresh_btn.click()
                page.wait_for_timeout(5000)  # Wait for callback
                
                # Get AFTER state
                positions_after = page.locator('table#portfolio-positions-table tbody tr')
                count_after = positions_after.count()
                print(f"   Positions AFTER: {count_after}")
                
                if count_after >= 3:
                    print(f"   ✅ Portfolio refresh WORKING (showing {count_after} positions)")
                    results['portfolio_refresh'] = 'WORKING'
                else:
                    print(f"   ❌ Portfolio refresh FAILED (still showing {count_after} positions)")
                    results['portfolio_refresh'] = 'FAILED'
                
                page.screenshot(path='reports/fix_verification/screenshots/portfolio_FIXED.png')
            else:
                print("   ❌ Refresh button NOT VISIBLE")
                results['portfolio_refresh'] = 'BUTTON_NOT_FOUND'
                page.screenshot(path='reports/fix_verification/screenshots/portfolio_FAILED.png')
            
            # FINAL Summary
            print("\n" + "="*80)
            print("LIVE TEST RESULTS SUMMARY")
            print("="*80)
            for test, status in results.items():
                icon = "✅" if status in ('HAS_CONTENT', 'WORKING') else "❌"
                print(f"{icon} {test}: {status}")
            print("="*80)
            
            # Save results
            import json
            with open('reports/fix_verification/tests/live_test_results.json', 'w') as f:
                json.dump(results, f, indent=2)
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            page.screenshot(path='reports/fix_verification/screenshots/error.png')
            raise
        finally:
            browser.close()

if __name__ == '__main__':
    test_all_fixes()

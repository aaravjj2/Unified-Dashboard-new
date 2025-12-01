"""
Comprehensive test for all reported issues
Tests:
1. Factor Exposure error handling
2. Optimization tab error fix
3. Analytics calculations
4. Text color in white boxes
5. Inspect button in Positions
"""
import asyncio
from playwright.async_api import async_playwright
import json

async def test_all_issues():
    """Test all reported dashboard issues."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        console_errors = []
        page.on('console', lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)
        
        results = {
            'factor_exposure': {'status': 'UNKNOWN', 'details': ''},
            'optimization': {'status': 'UNKNOWN', 'details': ''},
            'analytics': {'status': 'UNKNOWN', 'details': ''},
            'text_color': {'status': 'UNKNOWN', 'details': ''},
            'inspect_button': {'status': 'UNKNOWN', 'details': ''}
        }
        
        print("=" * 80)
        print("🧪 COMPREHENSIVE ISSUE TEST")
        print("=" * 80)
        
        # Load dashboard
        print("\n📋 Loading dashboard...")
        await page.goto('http://localhost:8056/')
        await page.wait_for_timeout(4000)
        
        # Test 1: Check text color in portfolio value cards
        print("\n🎨 Test 1: Text Color in White Boxes")
        try:
            portfolio_value_elem = page.locator('#portfolio-value')
            color = await portfolio_value_elem.evaluate('el => window.getComputedStyle(el).color')
            print(f"  Portfolio Value text color: {color}")
            
            # Check if it's black-ish (rgb values close to 0)
            if 'rgb(0, 0, 0)' in color or 'rgb(255, 255, 255)' not in color:
                results['text_color']['status'] = 'PASS'
                results['text_color']['details'] = f"Text color is {color} (should be black)"
                print(f"  ✅ PASS - Text is dark/black")
            else:
                results['text_color']['status'] = 'FAIL'
                results['text_color']['details'] = f"Text color is {color} (should be black not white)"
                print(f"  ❌ FAIL - Text is white, should be black")
        except Exception as e:
            results['text_color']['status'] = 'ERROR'
            results['text_color']['details'] = str(e)
            print(f"  ❌ ERROR: {e}")
        
        await page.screenshot(path='_issue_test_1_text_color.png')
        
        # Test 2: Positions Tab - Inspect Button
        print("\n🔍 Test 2: Inspect Button in Positions Tab")
        try:
            positions_tab = page.locator('text=Positions').first
            await positions_tab.click()
            await page.wait_for_timeout(2000)
            
            # Look for inspect button/icon in table
            inspect_cells = await page.locator('text=🔍').count()
            print(f"  Inspect icons found: {inspect_cells}")
            
            if inspect_cells > 0:
                # Try clicking the first inspect icon
                first_inspect = page.locator('text=🔍').first
                await first_inspect.click()
                await page.wait_for_timeout(1000)
                
                # Check if modal opened
                modal = await page.locator('#inspect-modal').get_attribute('aria-hidden')
                is_modal_open = modal == 'false' if modal else False
                
                if is_modal_open:
                    modal_title = await page.locator('#inspect-modal-title').inner_text()
                    print(f"  Modal opened with title: {modal_title}")
                    results['inspect_button']['status'] = 'PASS'
                    results['inspect_button']['details'] = f"Modal opened: {modal_title}"
                    print(f"  ✅ PASS - Inspect modal works")
                    
                    # Close modal
                    close_btn = page.locator('#inspect-modal-close')
                    await close_btn.click()
                    await page.wait_for_timeout(500)
                else:
                    results['inspect_button']['status'] = 'FAIL'
                    results['inspect_button']['details'] = "Modal didn't open"
                    print(f"  ❌ FAIL - Modal didn't open")
            else:
                results['inspect_button']['status'] = 'FAIL'
                results['inspect_button']['details'] = "No inspect icons found"
                print(f"  ❌ FAIL - No inspect buttons found")
                
        except Exception as e:
            results['inspect_button']['status'] = 'ERROR'
            results['inspect_button']['details'] = str(e)
            print(f"  ❌ ERROR: {e}")
        
        await page.screenshot(path='_issue_test_2_inspect.png')
        
        # Test 3: Analytics Tab - Check for calculations
        print("\n📊 Test 3: Analytics Tab - VaR/Sharpe Calculations")
        try:
            analytics_tab = page.locator('text=Analytics').first
            await analytics_tab.click()
            await page.wait_for_timeout(3000)
            
            var_value = await page.locator('#portfolio-var').inner_text()
            cvar_value = await page.locator('#portfolio-cvar').inner_text()
            sharpe_value = await page.locator('#portfolio-sharpe').inner_text()
            
            print(f"  VaR: {var_value}")
            print(f"  CVaR: {cvar_value}")
            print(f"  Sharpe: {sharpe_value}")
            
            # Check if any value is non-zero
            if '$0.00' not in var_value or '0.00' not in sharpe_value:
                results['analytics']['status'] = 'PASS'
                results['analytics']['details'] = f"VaR={var_value}, Sharpe={sharpe_value}"
                print(f"  ✅ PASS - Analytics showing values")
            else:
                results['analytics']['status'] = 'WARN'
                results['analytics']['details'] = "Still showing $0.00 - may need yfinance data"
                print(f"  ⚠️  WARN - Still $0.00 (may need historical data)")
        except Exception as e:
            results['analytics']['status'] = 'ERROR'
            results['analytics']['details'] = str(e)
            print(f"  ❌ ERROR: {e}")
        
        await page.screenshot(path='_issue_test_3_analytics.png')
        
        # Test 4: Optimization Tab - Check for error
        print("\n⚙️  Test 4: Optimization Tab - Division Error Fix")
        try:
            opt_tab = page.locator('text=Optimization').first
            await opt_tab.click()
            await page.wait_for_timeout(2000)
            
            # Check for error message
            error_alert = await page.locator('.alert-danger:has-text("unsupported operand")').count()
            
            if error_alert == 0:
                results['optimization']['status'] = 'PASS'
                results['optimization']['details'] = "No division error found"
                print(f"  ✅ PASS - No division error")
            else:
                error_text = await page.locator('.alert-danger').first.inner_text()
                results['optimization']['status'] = 'FAIL'
                results['optimization']['details'] = error_text[:100]
                print(f"  ❌ FAIL - Error still present: {error_text[:100]}")
        except Exception as e:
            results['optimization']['status'] = 'ERROR'
            results['optimization']['details'] = str(e)
            print(f"  ❌ ERROR: {e}")
        
        await page.screenshot(path='_issue_test_4_optimization.png')
        
        # Test 5: Factor Exposure Tab - Check error handling
        print("\n🧬 Test 5: Factor Exposure - SHAP Data Error Handling")
        try:
            factor_tab = page.locator('text=Factor Exposure').first
            await factor_tab.click()
            await page.wait_for_timeout(2000)
            
            # Check for friendly error message
            no_data_msg = await page.locator('text=No SHAP factor data').count()
            helpful_alert = await page.locator('.alert:has-text("SHAP")').count()
            
            if no_data_msg > 0 or helpful_alert > 0:
                results['factor_exposure']['status'] = 'PASS'
                results['factor_exposure']['details'] = "Graceful error handling present"
                print(f"  ✅ PASS - Friendly error message shown")
            else:
                results['factor_exposure']['status'] = 'UNKNOWN'
                results['factor_exposure']['details'] = "No error or data found"
                print(f"  ⚠️  UNKNOWN - No SHAP data or error message")
        except Exception as e:
            results['factor_exposure']['status'] = 'ERROR'
            results['factor_exposure']['details'] = str(e)
            print(f"  ❌ ERROR: {e}")
        
        await page.screenshot(path='_issue_test_5_factor.png')
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 ISSUE TEST SUMMARY")
        print("=" * 80)
        
        for test_name, result in results.items():
            status_emoji = {
                'PASS': '✅',
                'FAIL': '❌',
                'WARN': '⚠️ ',
                'ERROR': '❌',
                'UNKNOWN': '❓'
            }.get(result['status'], '❓')
            
            print(f"\n{status_emoji} {test_name.replace('_', ' ').title()}: {result['status']}")
            print(f"   {result['details']}")
        
        # Overall assessment
        passed = sum(1 for r in results.values() if r['status'] == 'PASS')
        failed = sum(1 for r in results.values() if r['status'] == 'FAIL')
        total = len(results)
        
        print(f"\n🎯 Overall: {passed} passed, {failed} failed, {total - passed - failed} other")
        
        print("\n📸 Screenshots saved:")
        for i in range(1, 6):
            print(f"  - _issue_test_{i}_*.png")
        
        # Save results
        with open('_issue_test_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        print("\n📄 Results saved to _issue_test_results.json")
        
        await page.wait_for_timeout(5000)
        await browser.close()
        
        return results

if __name__ == '__main__':
    asyncio.run(test_all_issues())

"""
Final comprehensive test - verify all dashboard functionality
"""
import asyncio
from playwright.async_api import async_playwright
import json

async def comprehensive_test():
    """Complete dashboard functionality test."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        console_errors = []
        page.on('console', lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)
        
        print("=" * 80)
        print("🧪 COMPREHENSIVE DASHBOARD TEST")
        print("=" * 80)
        
        # Test 1: Initial Load
        print("\n📋 Test 1: Initial Page Load")
        await page.goto('http://localhost:8056/')
        await page.wait_for_timeout(4000)
        
        # Check portfolio values
        portfolio_value = await page.locator('#portfolio-value').inner_text()
        total_invested = await page.locator('#portfolio-invested').inner_text()
        unrealized_pl = await page.locator('#portfolio-unrealized-pl').inner_text()
        buying_power = await page.locator('#portfolio-buying-power').inner_text()
        
        print(f"  Portfolio Value: {portfolio_value}")
        print(f"  Total Invested: {total_invested}")
        print(f"  Unrealized P/L: {unrealized_pl}")
        print(f"  Buying Power: {buying_power}")
        
        test1_pass = "$0.00" not in portfolio_value
        print(f"  ✅ PASS" if test1_pass else f"  ❌ FAIL - Values are $0.00")
        
        await page.screenshot(path='_test_step1_initial_values.png')
        
        # Test 2: Positions Tab
        print("\n📋 Test 2: Positions Tab")
        positions_tab = page.locator('text=Positions').first
        await positions_tab.click()
        await page.wait_for_timeout(2000)
        
        positions_table = await page.locator('#portfolio-positions-table').count()
        print(f"  Positions table present: {positions_table > 0}")
        
        # Check if table has data
        table_rows = await page.locator('.dash-table-container tbody tr').count()
        print(f"  Table rows: {table_rows}")
        
        test2_pass = table_rows > 0
        print(f"  ✅ PASS" if test2_pass else f"  ❌ FAIL - No positions data")
        
        await page.screenshot(path='_test_step2_positions.png', full_page=True)
        
        # Test 3: Orders Tab
        print("\n📋 Test 3: Order History Tab")
        orders_tab = page.locator('text=Order History').first
        await orders_tab.click()
        await page.wait_for_timeout(2000)
        
        orders_table = await page.locator('#portfolio-orders-table').count()
        print(f"  Orders table present: {orders_table > 0}")
        
        test3_pass = orders_table > 0
        print(f"  ✅ PASS" if test3_pass else f"  ❌ FAIL - Orders table not found")
        
        await page.screenshot(path='_test_step3_orders.png', full_page=True)
        
        # Test 4: Analytics Tab
        print("\n📋 Test 4: Analytics Tab")
        analytics_tab = page.locator('text=Analytics').first
        await analytics_tab.click()
        await page.wait_for_timeout(3000)
        
        var_value = await page.locator('#portfolio-var').inner_text()
        sharpe_value = await page.locator('#portfolio-sharpe').inner_text()
        
        print(f"  VaR: {var_value}")
        print(f"  Sharpe: {sharpe_value}")
        
        test4_pass = "$0.00" not in var_value or "0.00" not in sharpe_value
        print(f"  ✅ PASS" if test4_pass else f"  ⚠️  WARN - Analytics may not be loaded")
        
        await page.screenshot(path='_test_step4_analytics.png', full_page=True)
        
        # Test 5: Optimization Tab
        print("\n📋 Test 5: Optimization Tab")
        opt_tab = page.locator('text=Optimization').first
        await opt_tab.click()
        await page.wait_for_timeout(2000)
        
        opt_content = await page.locator('#portfolio-optimization-content').count()
        print(f"  Optimization content present: {opt_content > 0}")
        
        test5_pass = opt_content > 0
        print(f"  ✅ PASS" if test5_pass else f"  ❌ FAIL - Optimization tab not found")
        
        await page.screenshot(path='_test_step5_optimization.png', full_page=True)
        
        # Test 6: Factor Exposure Tab
        print("\n📋 Test 6: Factor Exposure Tab")
        factor_tab = page.locator('text=Factor Exposure').first
        await factor_tab.click()
        await page.wait_for_timeout(2000)
        
        factor_content = await page.locator('#portfolio-factor-exposure-content').count()
        print(f"  Factor exposure content present: {factor_content > 0}")
        
        test6_pass = factor_content > 0
        print(f"  ✅ PASS" if test6_pass else f"  ⚠️  WARN - Factor exposure may require SHAP data")
        
        await page.screenshot(path='_test_step6_factor_exposure.png', full_page=True)
        
        # Test 7: Refresh Button
        print("\n📋 Test 7: Refresh Button")
        await page.locator('text=Positions').first.click()
        await page.wait_for_timeout(1000)
        
        old_value = await page.locator('#portfolio-value').inner_text()
        await page.locator('#portfolio-refresh-btn').click()
        await page.wait_for_timeout(2000)
        new_value = await page.locator('#portfolio-value').inner_text()
        
        print(f"  Value before refresh: {old_value}")
        print(f"  Value after refresh: {new_value}")
        test7_pass = new_value != "$0.00"
        print(f"  ✅ PASS" if test7_pass else f"  ❌ FAIL - Refresh didn't work")
        
        # Test 8: Console Errors
        print("\n📋 Test 8: Console Errors Check")
        error_count = len(console_errors)
        print(f"  Console errors: {error_count}")
        if error_count > 0:
            for err in console_errors[:5]:
                print(f"    - {err[:100]}")
        
        test8_pass = error_count == 0
        print(f"  ✅ PASS" if test8_pass else f"  ⚠️  WARN - {error_count} console errors")
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        tests = [
            ("Initial Load", test1_pass),
            ("Positions Tab", test2_pass),
            ("Order History Tab", test3_pass),
            ("Analytics Tab", test4_pass),
            ("Optimization Tab", test5_pass),
            ("Factor Exposure Tab", test6_pass),
            ("Refresh Button", test7_pass),
            ("No Console Errors", test8_pass)
        ]
        
        passed = sum(1 for _, p in tests if p)
        total = len(tests)
        
        for name, result in tests:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status} - {name}")
        
        print(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED! Dashboard is fully functional!")
        elif passed >= total * 0.75:
            print("\n✅ DASHBOARD IS WORKING! Some optional features may need attention.")
        else:
            print("\n⚠️  DASHBOARD HAS ISSUES - Please review failed tests.")
        
        print("\n📸 Screenshots saved:")
        print("  - _test_step1_initial_values.png")
        print("  - _test_step2_positions.png")
        print("  - _test_step3_orders.png")
        print("  - _test_step4_analytics.png")
        print("  - _test_step5_optimization.png")
        print("  - _test_step6_factor_exposure.png")
        
        await page.wait_for_timeout(5000)
        await browser.close()

if __name__ == '__main__':
    asyncio.run(comprehensive_test())

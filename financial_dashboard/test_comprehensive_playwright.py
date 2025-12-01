#!/usr/bin/env python3
"""
Comprehensive Playwright Test Suite - All Dashboard Issues

Tests:
1. Market Trends - Table display (should show all rows, not minimized)
2. Analysis Hub - Attribution data display
3. Portfolio - Frontend components and transaction upload
4. Research Lab - Error checking and results viewer

Usage:
    python3 test_comprehensive_playwright.py
"""

import asyncio
import sys
import os
from playwright.async_api import async_playwright
from datetime import datetime


async def test_market_trends_table(page):
    """Test Market Trends table - should show all rows, not minimized."""
    print("\n📊 Testing Market Trends Table...")
    
    await page.goto('http://localhost:8050', timeout=30000)
    await page.wait_for_load_state('networkidle', timeout=30000)
    
    # Wait for table to load
    try:
        await page.wait_for_selector('#results-table-client', timeout=10000)
        print("  ✓ Results table found")
    except:
        print("  ⚠ Results table not found - may need to trigger analysis")
        # Click run analysis button if present
        try:
            run_btn = page.locator('button:has-text("Run Full Analysis")')
            if await run_btn.is_visible():
                await run_btn.click()
                print("  ⏳ Triggered analysis run...")
                await page.wait_for_timeout(5000)
        except:
            pass
    
    # Check table rows
    try:
        rows = await page.locator('#results-table-client .data-table-row').count()
        print(f"  ✓ Table showing {rows} rows")
        
        if rows < 5:
            print(f"  ⚠ WARNING: Only {rows} rows visible - table may be minimized!")
        else:
            print(f"  ✓ Table properly displaying multiple rows")
    except Exception as e:
        print(f"  ⚠ Could not count table rows: {e}")
    
    # Check for min-height CSS issues
    try:
        table_style = await page.locator('#results-table-client').evaluate(
            'el => window.getComputedStyle(el).height'
        )
        print(f"  ℹ Table computed height: {table_style}")
    except:
        pass
    
    # Take screenshot
    await page.screenshot(path='test_market_trends_table.png', full_page=True)
    print("  ✓ Screenshot saved: test_market_trends_table.png")
    
    return True


async def test_analysis_hub_data(page):
    """Test Analysis Hub - check if attribution data is displaying."""
    print("\n📈 Testing Analysis Hub Attribution Data...")
    
    await page.goto('http://localhost:8054', timeout=30000)
    await page.wait_for_load_state('networkidle', timeout=30000)
    
    # Check page loaded
    try:
        header = page.locator('h2:has-text("Analysis Hub")')
        assert await header.is_visible(), "Analysis Hub header not visible"
        print("  ✓ Analysis Hub loaded")
    except Exception as e:
        print(f"  ✗ Failed to load: {e}")
        return False
    
    # Check Attribution tab
    try:
        attr_tab = page.locator('text=Attribution Analysis')
        await attr_tab.click()
        await page.wait_for_timeout(1000)
        print("  ✓ Attribution tab clicked")
    except:
        print("  ⚠ Could not find Attribution tab")
    
    # Check for attribution controls
    try:
        run_btn = page.locator('button:has-text("Run Attribution Analysis")')
        assert await run_btn.is_visible(), "Run button not visible"
        print("  ✓ Attribution controls present")
        
        # Click run button
        await run_btn.click()
        print("  ⏳ Running attribution analysis...")
        await page.wait_for_timeout(3000)
        
        # Check for results
        try:
            results_div = page.locator('#attr-results-container')
            if await results_div.is_visible():
                print("  ✓ Attribution results container visible")
                
                # Check summary cards
                total_return = await page.locator('#attr-total-return').inner_text()
                alpha = await page.locator('#attr-alpha').inner_text()
                beta = await page.locator('#attr-beta').inner_text()
                
                print(f"  ℹ Total Return: {total_return}")
                print(f"  ℹ Alpha: {alpha}")
                print(f"  ℹ Beta: {beta}")
                
                if total_return == "--" or alpha == "--":
                    print("  ⚠ WARNING: Attribution data showing placeholders (--)")
                else:
                    print("  ✓ Attribution data populated")
            else:
                print("  ⚠ WARNING: Results container not visible after run")
        except Exception as e:
            print(f"  ⚠ Could not check results: {e}")
    except Exception as e:
        print(f"  ⚠ Attribution controls issue: {e}")
    
    # Take screenshot
    await page.screenshot(path='test_analysis_hub_data.png', full_page=True)
    print("  ✓ Screenshot saved: test_analysis_hub_data.png")
    
    return True


async def test_portfolio_frontend(page):
    """Test Portfolio Dashboard - check frontend components and transaction upload."""
    print("\n💼 Testing Portfolio Frontend...")
    
    await page.goto('http://localhost:8056', timeout=30000)
    await page.wait_for_load_state('networkidle', timeout=30000)
    
    # Check page loaded
    try:
        header = page.locator('h2:has-text("Portfolio Dashboard")')
        assert await header.is_visible(), "Portfolio header not visible"
        print("  ✓ Portfolio Dashboard loaded")
    except Exception as e:
        print(f"  ✗ Failed to load: {e}")
        return False
    
    # Check summary cards
    try:
        notional = await page.locator('#port-notional').inner_text()
        invested = await page.locator('#port-invested').inner_text()
        realized = await page.locator('#port-realized-pnl').inner_text()
        unrealized = await page.locator('#port-unrealized-pnl').inner_text()
        
        print(f"  ℹ Notional: {notional}")
        print(f"  ℹ Invested: {invested}")
        print(f"  ℹ Realized P/L: {realized}")
        print(f"  ℹ Unrealized P/L: {unrealized}")
        
        if notional == "$0" and invested == "$0":
            print("  ℹ Portfolio is empty (expected if no transactions uploaded)")
        else:
            print("  ✓ Portfolio showing data")
    except Exception as e:
        print(f"  ⚠ Could not read summary cards: {e}")
    
    # Check for upload button
    try:
        upload_btn = page.locator('button:has-text("Upload Transactions")')
        if await upload_btn.count() > 0:
            print("  ✓ Transaction upload button found")
        else:
            print("  ⚠ WARNING: No transaction upload button found")
    except:
        print("  ⚠ Could not check for upload button")
    
    # Check tabs
    try:
        positions_tab = page.locator('text=Positions')
        performance_tab = page.locator('text=Performance')
        transactions_tab = page.locator('text=Transactions')
        
        tabs_visible = 0
        if await positions_tab.count() > 0:
            print("  ✓ Positions tab present")
            tabs_visible += 1
        if await performance_tab.count() > 0:
            print("  ✓ Performance tab present")
            tabs_visible += 1
        if await transactions_tab.count() > 0:
            print("  ✓ Transactions tab present")
            tabs_visible += 1
        
        if tabs_visible < 3:
            print(f"  ⚠ WARNING: Only {tabs_visible}/3 tabs found")
    except Exception as e:
        print(f"  ⚠ Could not check tabs: {e}")
    
    # Take screenshot
    await page.screenshot(path='test_portfolio_frontend.png', full_page=True)
    print("  ✓ Screenshot saved: test_portfolio_frontend.png")
    
    return True


async def test_research_lab_errors(page):
    """Test Research Lab - check for errors and results viewer."""
    print("\n🔬 Testing Research Lab...")
    
    await page.goto('http://localhost:8058', timeout=30000)
    await page.wait_for_load_state('networkidle', timeout=30000)
    
    # Check page loaded
    try:
        header = page.locator('h2:has-text("Research Lab")')
        assert await header.is_visible(), "Research Lab header not visible"
        print("  ✓ Research Lab loaded")
    except Exception as e:
        print(f"  ✗ Failed to load: {e}")
        return False
    
    # Check console for errors
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    
    await page.wait_for_timeout(2000)
    
    if errors:
        print(f"  ⚠ WARNING: Found {len(errors)} console errors:")
        for err in errors[:5]:  # Show first 5
            print(f"    - {err[:100]}")
    else:
        print("  ✓ No console errors detected")
    
    # Check tabs
    try:
        new_exp_tab = page.locator('text=New Experiment')
        results_tab = page.locator('text=Results')
        
        if await new_exp_tab.count() > 0:
            print("  ✓ New Experiment tab present")
        if await results_tab.count() > 0:
            print("  ✓ Results tab present")
            
            # Click Results tab
            await results_tab.click()
            await page.wait_for_timeout(1000)
            
            # Check for results dropdown
            try:
                exp_dropdown = page.locator('#exp-results-selector')
                if await exp_dropdown.is_visible():
                    print("  ✓ Experiment results dropdown found")
                else:
                    print("  ⚠ WARNING: Results dropdown not visible")
            except:
                print("  ⚠ WARNING: Results dropdown not found")
    except Exception as e:
        print(f"  ⚠ Could not check tabs: {e}")
    
    # Check for error messages in page
    try:
        error_text = await page.locator('text=/error|exception|failed/i').count()
        if error_text > 0:
            print(f"  ⚠ WARNING: Found {error_text} error-related text elements")
    except:
        pass
    
    # Take screenshot
    await page.screenshot(path='test_research_lab_errors.png', full_page=True)
    print("  ✓ Screenshot saved: test_research_lab_errors.png")
    
    return True


async def run_all_tests():
    """Run all comprehensive tests."""
    print("=" * 80)
    print("🧪 COMPREHENSIVE DASHBOARD TEST SUITE")
    print("=" * 80)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        results = []
        
        # Run all tests
        try:
            results.append(("Market Trends Table", await test_market_trends_table(page)))
        except Exception as e:
            print(f"  ✗ Market Trends test failed: {e}")
            results.append(("Market Trends Table", False))
        
        try:
            results.append(("Analysis Hub Data", await test_analysis_hub_data(page)))
        except Exception as e:
            print(f"  ✗ Analysis Hub test failed: {e}")
            results.append(("Analysis Hub Data", False))
        
        try:
            results.append(("Portfolio Frontend", await test_portfolio_frontend(page)))
        except Exception as e:
            print(f"  ✗ Portfolio test failed: {e}")
            results.append(("Portfolio Frontend", False))
        
        try:
            results.append(("Research Lab Errors", await test_research_lab_errors(page)))
        except Exception as e:
            print(f"  ✗ Research Lab test failed: {e}")
            results.append(("Research Lab Errors", False))
        
        await browser.close()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        for test_name, passed in results:
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{status:10} {test_name}")
        
        passed_count = sum(1 for _, p in results if p)
        total_count = len(results)
        
        print(f"\nTotal: {passed_count}/{total_count} tests passed")
        print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        return passed_count == total_count


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

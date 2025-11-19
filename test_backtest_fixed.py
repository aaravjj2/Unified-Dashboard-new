#!/usr/bin/env python3
"""Test Script: Verify Strategy Lab Backtest Fix - Zero Returns Issue"""
import asyncio
import time
from playwright.async_api import async_playwright

async def test_backtest_with_fixed_dates():
    print("🧪 Testing Strategy Lab Backtest with Fixed Date Range\n")
    print("=" * 70)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            # 1. Load Dashboard
            print("1️⃣ Loading dashboard at http://localhost:8050...")
            await page.goto('http://localhost:8050', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            print("   ✅ Dashboard loaded\n")
            
            # 2. Navigate to Strategy Lab
            print("2️⃣ Navigating to Strategy Lab...")
            strategy_lab_tab = page.locator('a:has-text("Strategy Lab")')
            if await strategy_lab_tab.count() > 0:
                await strategy_lab_tab.click()
                await asyncio.sleep(2)
                print("   ✅ Strategy Lab tab opened\n")
            else:
                print("   ❌ Strategy Lab tab not found!")
                return False
            
            # 3. Go to Execute & Configure subtab
            print("3️⃣ Opening Execute & Configure subtab...")
            execute_tab = page.locator('a:has-text("Execute & Configure")')
            if await execute_tab.count() > 0:
                await execute_tab.click()
                await asyncio.sleep(2)
                print("   ✅ Execute & Configure tab opened\n")
            else:
                print("   ❌ Execute & Configure tab not found!")
                return False
            
            # 4. Check default dates
            print("4️⃣ Checking default date values...")
            start_date = await page.locator('#sl-execute-start-date').input_value()
            end_date = await page.locator('#sl-execute-end-date').input_value()
            print(f"   📅 Start Date: {start_date}")
            print(f"   📅 End Date: {end_date}")
            
            # Verify end date is NOT today (should be yesterday)
            from datetime import datetime, timedelta
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            if end_date == yesterday:
                print(f"   ✅ End date is yesterday ({yesterday}) - FIX CONFIRMED\n")
            else:
                print(f"   ⚠️ End date is {end_date}, expected {yesterday}\n")
            
            # 5. Run Backtest
            print("5️⃣ Running backtest...")
            run_button = page.locator('#sl-execute-run-btn')
            if await run_button.count() > 0:
                await run_button.click()
                print("   ✅ Run button clicked\n")
            else:
                print("   ❌ Run button not found!")
                return False
            
            # 6. Wait for backtest to complete (give it 90 seconds max)
            print("6️⃣ Waiting for backtest to complete (up to 90s)...")
            await asyncio.sleep(5)  # Initial wait for processing to start
            
            # Check for loading indicator or results
            max_wait = 90
            waited = 5
            while waited < max_wait:
                # Check if Results tab has data
                results_content = await page.locator('#sl-results-metrics').inner_text()
                if results_content and '--' not in results_content[:50]:
                    print(f"   ✅ Backtest completed in ~{waited}s\n")
                    break
                
                await asyncio.sleep(5)
                waited += 5
                if waited % 15 == 0:
                    print(f"   ⏳ Still waiting... ({waited}s elapsed)")
            
            # 7. Check Results Tab
            print("7️⃣ Checking Results tab for metrics...")
            results_tab = page.locator('a:has-text("Results")')
            if await results_tab.count() > 0:
                await results_tab.click()
                await asyncio.sleep(2)
                
                # Get metrics
                metrics_text = await page.locator('#sl-results-metrics').inner_text()
                print("   📊 Results Tab Content:")
                print("   " + "-" * 60)
                for line in metrics_text.split('\n')[:10]:  # First 10 lines
                    print(f"   {line}")
                print("   " + "-" * 60)
                
                # Check if we got real data (not all zeros/dashes)
                if 'CAGR' in metrics_text and '--' not in metrics_text[:100]:
                    print("   ✅ Results tab shows real metrics!\n")
                    return True
                elif '--' in metrics_text:
                    print("   ❌ Results tab still shows dashes (no data)\n")
                    return False
                else:
                    print("   ⚠️ Unexpected results format\n")
                    return False
            else:
                print("   ❌ Results tab not found!\n")
                return False
                
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await browser.close()

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print(" Strategy Lab Backtest Fix Verification Test")
    print("=" * 70 + "\n")
    
    start_time = time.time()
    result = asyncio.run(test_backtest_with_fixed_dates())
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 70)
    if result:
        print(f"✅ TEST PASSED - Backtest returned real data! ({elapsed:.1f}s)")
    else:
        print(f"❌ TEST FAILED - Backtest still returning zeros ({elapsed:.1f}s)")
    print("=" * 70 + "\n")

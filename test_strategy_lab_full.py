#!/usr/bin/env python3
"""
Comprehensive Strategy Lab Test with Screenshots
Tests: Execute & Configure, Results, Benchmark, Risk & Factors tabs
"""
import asyncio
import os
from playwright.async_api import async_playwright
from datetime import datetime

async def test_strategy_lab_full():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    screenshot_dir = f"/app/test-artifacts/strategy_lab_{timestamp}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            print("=" * 80)
            print("STRATEGY LAB COMPREHENSIVE TEST")
            print("=" * 80)
            
            # Create screenshot directory
            os.makedirs(screenshot_dir, exist_ok=True)
            
            # Step 1: Load Dashboard
            print("\n1️⃣ Loading dashboard...")
            await page.goto('http://localhost:8050', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            await page.screenshot(path=f"{screenshot_dir}/01_home.png")
            print("   ✅ Dashboard loaded")
            
            # Step 2: Go to Strategy Lab
            print("\n2️⃣ Opening Strategy Lab...")
            await page.click('a:has-text("Strategy Lab")')
            await asyncio.sleep(2)
            await page.screenshot(path=f"{screenshot_dir}/02_strategy_lab_initial.png")
            print("   ✅ Strategy Lab opened")
            
            # Step 3: Go to Execute & Configure
            print("\n3️⃣ Opening Execute & Configure tab...")
            await page.click('a:has-text("Execute & Configure")')
            await asyncio.sleep(2)
            await page.screenshot(path=f"{screenshot_dir}/03_execute_before.png")
            print("   ✅ Execute & Configure tab opened")
            
            # Step 4: Run Backtest
            print("\n4️⃣ Running backtest...")
            await page.click('#sl-run-backtest-btn')
            print("   ⏳ Waiting 45s for backtest to complete...")
            await asyncio.sleep(45)
            await page.screenshot(path=f"{screenshot_dir}/04_execute_after_backtest.png")
            
            # Get backtest results text
            try:
                results_text = await page.locator('.alert-success, .alert-warning').inner_text()
                print("\n   📊 Backtest Results:")
                for line in results_text.split('\n')[:15]:
                    if line.strip():
                        print(f"      {line}")
            except Exception as e:
                print(f"   ⚠️ Could not extract results text: {e}")
            
            print("   ✅ Backtest executed")
            
            # Step 5: Check Results Tab
            print("\n5️⃣ Checking Results tab...")
            await page.click('a:has-text("Results"):not(:has-text("Execute"))')
            await asyncio.sleep(2)
            await page.screenshot(path=f"{screenshot_dir}/05_results_tab.png")
            
            # Get metrics
            try:
                cagr = await page.locator('#sl-metric-cagr').inner_text()
                sharpe = await page.locator('#sl-metric-sharpe').inner_text()
                maxdd = await page.locator('#sl-metric-maxdd').inner_text()
                winrate = await page.locator('#sl-metric-winrate').inner_text()
                print(f"   📈 Metrics: CAGR={cagr}, Sharpe={sharpe}, MaxDD={maxdd}, WinRate={winrate}")
                
                if cagr == "--":
                    print("   ❌ ISSUE: Results tab showing '--' (not synced)")
                else:
                    print("   ✅ Results tab shows data")
            except Exception as e:
                print(f"   ⚠️ Could not extract metrics: {e}")
            
            # Step 6: Check Benchmark Tab
            print("\n6️⃣ Checking Benchmark tab...")
            await page.click('a:has-text("Benchmark")')
            await asyncio.sleep(2)
            await page.screenshot(path=f"{screenshot_dir}/06_benchmark_tab.png")
            
            # Check for chart
            try:
                has_chart = await page.locator('.js-plotly-plot').count() > 0
                if has_chart:
                    print("   ✅ Benchmark chart rendered")
                else:
                    print("   ❌ ISSUE: No chart found in Benchmark tab")
            except:
                print("   ⚠️ Could not check for chart")
            
            # Step 7: Check Risk & Factors Tab
            print("\n7️⃣ Checking Risk & Factors tab...")
            await page.click('a:has-text("Risk & Factors")')
            await asyncio.sleep(2)
            await page.screenshot(path=f"{screenshot_dir}/07_risk_factors_tab.png")
            
            # Check for content
            try:
                risk_content = await page.locator('#sl-risk-content').inner_text()
                if "Run backtest" in risk_content or risk_content.strip() == "":
                    print("   ❌ ISSUE: Risk & Factors tab empty")
                else:
                    print("   ✅ Risk & Factors tab shows data")
            except:
                print("   ⚠️ Could not check risk content")
            
            # Step 8: Check Weekly Picks
            print("\n8️⃣ Checking Weekly Picks...")
            await page.click('a:has-text("Weekly Picks")')
            await asyncio.sleep(2)
            await page.screenshot(path=f"{screenshot_dir}/08_weekly_picks.png")
            
            # Check price columns
            try:
                table = await page.locator('table').first.inner_html()
                if 'Current Price' in table:
                    print("   ✅ Weekly Picks table has Current Price column")
                    # TODO: Check if prices are correct
                else:
                    print("   ⚠️ Weekly Picks table structure unclear")
            except:
                print("   ⚠️ Could not check Weekly Picks table")
            
            # Step 9: Check Monthly Picks
            print("\n9️⃣ Checking Monthly Picks...")
            await page.click('a:has-text("Monthly Picks")')
            await asyncio.sleep(2)
            await page.screenshot(path=f"{screenshot_dir}/09_monthly_picks.png")
            
            print("\n" + "=" * 80)
            print(f"✅ TEST COMPLETE - Screenshots saved to: {screenshot_dir}")
            print("=" * 80)
            
            # Copy screenshots to host
            print("\n📤 Copying screenshots to host...")
            return screenshot_dir
            
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path=f"{screenshot_dir}/ERROR.png")
            return None
        finally:
            await browser.close()

if __name__ == '__main__':
    result_dir = asyncio.run(test_strategy_lab_full())
    if result_dir:
        print(f"\n🎯 To copy screenshots to host:")
        print(f"   docker cp dash_app:{result_dir} ./test-artifacts/")

#!/usr/bin/env python3
"""
Test Weekly and Monthly Picks Price Data
Investigates: Current Price and Week/Month Start Price accuracy
"""
import asyncio
import os
from playwright.async_api import async_playwright
from datetime import datetime
import json

async def test_picks_prices():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    screenshot_dir = f"/app/test-artifacts/picks_prices_{timestamp}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            print("=" * 80)
            print("WEEKLY & MONTHLY PICKS PRICE INVESTIGATION")
            print("=" * 80)
            
            os.makedirs(screenshot_dir, exist_ok=True)
            
            # Load Dashboard
            print("\n1️⃣ Loading dashboard...")
            await page.goto('http://localhost:8050', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            print("   ✅ Dashboard loaded")
            
            # Test Weekly Picks
            print("\n2️⃣ Testing Weekly Picks...")
            await page.click('a:has-text("Weekly Picks")')
            await asyncio.sleep(3)
            await page.screenshot(path=f"{screenshot_dir}/weekly_picks.png")
            
            # Extract table data
            try:
                # Look for the table
                table_rows = await page.locator('table tbody tr').all()
                print(f"   📊 Found {len(table_rows)} rows in Weekly Picks table")
                
                # Extract first 3 rows of data
                for i, row in enumerate(table_rows[:3]):
                    cells = await row.locator('td').all()
                    if len(cells) >= 6:
                        rank = await cells[0].inner_text()
                        ticker = await cells[1].inner_text()
                        current_price = await cells[2].inner_text()
                        daily_change = await cells[3].inner_text()
                        week_start = await cells[4].inner_text()
                        profit_loss = await cells[5].inner_text()
                        
                        print(f"\n   Row {i+1}:")
                        print(f"      Ticker: {ticker}")
                        print(f"      Current Price: {current_price}")
                        print(f"      Daily Change: {daily_change}")
                        print(f"      Week Start: {week_start}")
                        print(f"      Profit/Loss: {profit_loss}")
                        
                        # Check for issues
                        if current_price == "N/A" or current_price == "$0.00":
                            print(f"      ❌ ISSUE: Current Price is {current_price}")
                        if week_start == "N/A" or week_start == "$0.00":
                            print(f"      ❌ ISSUE: Week Start is {week_start}")
                
            except Exception as e:
                print(f"   ⚠️ Could not extract Weekly Picks data: {e}")
            
            # Test Monthly Picks
            print("\n3️⃣ Testing Monthly Picks...")
            await page.click('a:has-text("Monthly Picks")')
            await asyncio.sleep(3)
            await page.screenshot(path=f"{screenshot_dir}/monthly_picks.png")
            
            # Extract table data
            try:
                table_rows = await page.locator('table tbody tr').all()
                print(f"   📊 Found {len(table_rows)} rows in Monthly Picks table")
                
                # Extract first 3 rows of data
                for i, row in enumerate(table_rows[:3]):
                    cells = await row.locator('td').all()
                    if len(cells) >= 6:
                        rank = await cells[0].inner_text()
                        ticker = await cells[1].inner_text()
                        current_price = await cells[2].inner_text()
                        daily_change = await cells[3].inner_text()
                        month_start = await cells[4].inner_text()
                        profit_loss = await cells[5].inner_text()
                        
                        print(f"\n   Row {i+1}:")
                        print(f"      Ticker: {ticker}")
                        print(f"      Current Price: {current_price}")
                        print(f"      Daily Change: {daily_change}")
                        print(f"      Month Start: {month_start}")
                        print(f"      Profit/Loss: {profit_loss}")
                        
                        # Check for issues
                        if current_price == "N/A" or current_price == "$0.00":
                            print(f"      ❌ ISSUE: Current Price is {current_price}")
                        if month_start == "N/A" or month_start == "$0.00":
                            print(f"      ❌ ISSUE: Month Start is {month_start}")
                
            except Exception as e:
                print(f"   ⚠️ Could not extract Monthly Picks data: {e}")
            
            # Check logs for price fetching
            print("\n4️⃣ Checking logs for price fetching issues...")
            print("   (Check container logs with: docker logs dash_app | grep -i 'price\\|fetch\\|weekly\\|monthly')")
            
            print("\n" + "=" * 80)
            print(f"✅ TEST COMPLETE - Screenshots saved to: {screenshot_dir}")
            print("=" * 80)
            
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
    result_dir = asyncio.run(test_picks_prices())
    if result_dir:
        print(f"\n🎯 To copy screenshots:")
        print(f"   docker cp dash_app:{result_dir} ./test-artifacts/")

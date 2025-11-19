#!/usr/bin/env python3
"""
End-to-End Market Trends Validation
Tests the complete flow: Run Analysis → Fetch Prices → Render Table → Verify Zero N/A
"""
import asyncio
from playwright.async_api import async_playwright
import time

async def test_market_trends_complete_flow():
    """
    Complete E2E test:
    1. Navigate to Market Trends tab
    2. Click "Run Full Analysis" button
    3. Wait for job completion
    4. Verify table has NO "Data Unavailable" values
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("="*80)
        print("MARKET TRENDS E2E VALIDATION")
        print("="*80)
        
        # Step 1: Navigate to Market Trends
        print("\n📍 Step 1: Navigating to Market Trends tab...")
        await page.goto("http://localhost:8050/", wait_until="domcontentloaded")
        await page.wait_for_selector('a:has-text("Market Trends")', timeout=15000)
        
        # Click Market Trends tab
        await page.locator('a:has-text("Market Trends")').click()
        await page.wait_for_timeout(2000)
        print("✅ Market Trends tab loaded")
        
        # Step 2: Check if table already exists
        print("\n📊 Step 2: Checking for existing table...")
        table = page.locator('table.market-trends-html-table')
        table_exists = await table.count() > 0
        
        if table_exists:
            print("⚠️  Table already exists - checking data quality...")
            page_content = await page.content()
            unavailable_count = page_content.count("Data Unavailable")
            
            if unavailable_count > 0:
                print(f"❌ Found {unavailable_count} 'Data Unavailable' values - need to re-run analysis")
                table_exists = False  # Force re-run
            else:
                print(f"✅ Table looks good! Zero 'Data Unavailable' values")
                await browser.close()
                return True
        
        # Step 3: Trigger "Run Full Analysis"
        if not table_exists or unavailable_count > 0:
            print("\n🚀 Step 3: Triggering 'Run Full Analysis'...")
            
            # Click the button
            run_btn = page.locator('#run-btn')
            if await run_btn.count() == 0:
                print("❌ Run button not found!")
                await browser.close()
                return False
            
            await run_btn.click()
            print("✅ Clicked 'Run Full Analysis' - waiting for job completion...")
            
            # Wait for loading indicator to appear and disappear
            try:
                # Wait for loading spinner
                loading = page.locator('._dash-loading')
                if await loading.count() > 0:
                    print("   Waiting for Dash loading indicator...")
                    await loading.wait_for(state='hidden', timeout=90000)
                    print("   ✓ Loading complete")
            except:
                print("   No loading indicator detected - continuing...")
            
            # Wait for table to appear (up to 60 seconds)
            print("\n⏰ Step 4: Waiting for table to render...")
            try:
                await page.wait_for_selector('table.market-trends-html-table', timeout=60000)
                print("✅ Table rendered!")
            except Exception as e:
                print(f"❌ Table did not appear within 60s: {e}")
                await page.screenshot(path="market_trends_timeout.png")
                await browser.close()
                return False
        
        # Step 5: Validate data quality
        print("\n✅ Step 5: Validating table data quality...")
        await page.wait_for_timeout(2000)  # Let table fully populate
        
        # Get page content and count "Data Unavailable"
        page_content = await page.content()
        unavailable_count = page_content.count("Data Unavailable")
        na_count = page_content.count(">N/A<")
        
        # Count table rows
        rows = page.locator('table.market-trends-html-table tbody tr')
        row_count = await rows.count()
        
        print(f"\n📊 Final Results:")
        print(f"   - Table rows: {row_count}")
        print(f"   - 'Data Unavailable' occurrences: {unavailable_count}")
        print(f"   - 'N/A' occurrences: {na_count}")
        
        # Take screenshot
        await page.screenshot(path="market_trends_final_validation.png", full_page=True)
        print(f"   - Screenshot saved: market_trends_final_validation.png")
        
        # Final verdict
        print("\n" + "="*80)
        if unavailable_count == 0 and na_count == 0 and row_count > 0:
            print("✅ SUCCESS: Market Trends table is fully operational!")
            print(f"   - {row_count} tickers rendered")
            print("   - Zero missing/N/A values")
            print("   - All price data populated")
            await browser.close()
            return True
        else:
            print("❌ FAILURE: Data quality issues detected")
            if row_count == 0:
                print("   - No table rows found")
            if unavailable_count > 0:
                print(f"   - {unavailable_count} 'Data Unavailable' values")
            if na_count > 0:
                print(f"   - {na_count} 'N/A' values")
            await browser.close()
            return False

if __name__ == "__main__":
    success = asyncio.run(test_market_trends_complete_flow())
    print("\n" + "="*80)
    if success:
        print("🎉 MISSION COMPLETE: Market Trends tab verified operational")
        print("="*80)
        exit(0)
    else:
        print("❌ MISSION FAILED: Market Trends tab has issues")
        print("="*80)
        print("\nNext steps:")
        print("1. Check server logs for errors")
        print("2. Verify price cache files exist: ls -la outputs/prices_*.json")
        print("3. Restart Dash server to reload price cache")
        exit(1)

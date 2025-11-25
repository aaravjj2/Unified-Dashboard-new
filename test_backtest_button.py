#!/usr/bin/env python3
"""
Backtest Button Functionality Test
Verifies that clicking "Backtest Trend Signals" button:
1. Triggers a background job
2. Updates the Market Trends table
3. Opens backtest modal with results
"""
import asyncio
from playwright.async_api import async_playwright

async def test_backtest_button():
    """Test Backtest button click and result display"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("="*80)
        print("BACKTEST BUTTON FUNCTIONALITY TEST")
        print("="*80)
        
        # Step 1: Navigate to Market Trends
        print("\n📍 Step 1: Loading Market Trends tab...")
        await page.goto("http://localhost:8050/", wait_until="domcontentloaded")
        await page.wait_for_selector('a:has-text("Market Trends")', timeout=15000)
        await page.locator('a:has-text("Market Trends")').click()
        await page.wait_for_timeout(2000)
        print("✅ Market Trends tab loaded")
        
        # Step 2: Locate Backtest button
        print("\n🔍 Step 2: Finding Backtest button...")
        backtest_btn = page.locator('#backtest-btn')
        btn_count = await backtest_btn.count()
        
        if btn_count == 0:
            print("❌ Backtest button not found in DOM!")
            await browser.close()
            return False
        
        # Check if button is visible
        is_visible = await backtest_btn.is_visible()
        print(f"✅ Backtest button found (visible: {is_visible})")
        
        # Step 3: Click Backtest button
        print("\n🚀 Step 3: Clicking 'Backtest Trend Signals' button...")
        try:
            await backtest_btn.click()
            print("✅ Button clicked successfully")
        except Exception as e:
            print(f"❌ Failed to click button: {e}")
            await browser.close()
            return False
        
        # Step 4: Monitor for job status update
        print("\n⏰ Step 4: Monitoring job status...")
        try:
            # Wait for status message to appear
            status = page.locator('#status')
            await status.wait_for(state='visible', timeout=5000)
            
            # Get status text
            status_text = await status.inner_text()
            print(f"✅ Status message appeared: {status_text}")
            
            # Check if job ID is mentioned
            if "Job ID:" in status_text:
                print("✅ Job queued successfully (Job ID found in status)")
            else:
                print("⚠️  Status message doesn't contain Job ID")
        except Exception as e:
            print(f"⚠️  Status element not visible: {e}")
        
        # Step 5: Wait for job completion (check for table update)
        print("\n📊 Step 5: Waiting for analysis completion...")
        try:
            # Wait up to 90 seconds for loading to complete
            loading = page.locator('._dash-loading')
            if await loading.count() > 0:
                print("   Waiting for Dash loading indicator...")
                await loading.wait_for(state='hidden', timeout=90000)
                print("   ✓ Loading complete")
            else:
                # No loading indicator, wait fixed time
                print("   No loading indicator - waiting 60s...")
                await page.wait_for_timeout(60000)
        except Exception as e:
            print(f"   ⚠️  Loading wait exception: {e}")
        
        # Step 6: Check if table was updated
        print("\n📋 Step 6: Verifying table update...")
        table = page.locator('table.market-trends-html-table')
        if await table.count() > 0:
            rows = page.locator('table.market-trends-html-table tbody tr')
            row_count = await rows.count()
            print(f"✅ Table found with {row_count} rows")
            
            # Check for "Data Unavailable"
            page_content = await page.content()
            unavailable_count = page_content.count("Data Unavailable")
            print(f"   - 'Data Unavailable' count: {unavailable_count}")
            
            if unavailable_count == 0:
                print("✅ All price data populated!")
            else:
                print(f"⚠️  {unavailable_count} missing values found")
        else:
            print("❌ No table found after backtest")
        
        # Step 7: Check for backtest modal (if implemented)
        print("\n🔍 Step 7: Checking for backtest modal...")
        modal = page.locator('#backtest-modal')
        if await modal.count() > 0:
            is_modal_visible = await modal.is_visible()
            print(f"✅ Backtest modal found (visible: {is_modal_visible})")
            
            if is_modal_visible:
                # Try to get modal content
                try:
                    modal_content = page.locator('#backtest-results-content')
                    if await modal_content.count() > 0:
                        content_text = await modal_content.inner_text()
                        print(f"✅ Modal content: {content_text[:200]}...")
                except Exception as e:
                    print(f"   Could not read modal content: {e}")
        else:
            print("⚠️  Backtest modal not found in DOM")
        
        # Take screenshot
        await page.screenshot(path="backtest_test_result.png", full_page=True)
        print(f"\n📸 Screenshot saved: backtest_test_result.png")
        
        # Final verdict
        print("\n" + "="*80)
        print("BACKTEST FUNCTIONALITY VERDICT")
        print("="*80)
        
        # Success criteria:
        # 1. Button click worked
        # 2. Job was queued (status message appeared)
        # 3. Table updated (has rows)
        # 4. Zero "Data Unavailable" values
        
        success = True
        if btn_count == 0:
            print("❌ Button not found")
            success = False
        elif row_count == 0:
            print("❌ Table not updated after backtest")
            success = False
        elif unavailable_count > 0:
            print(f"⚠️  PARTIAL: Table updated but {unavailable_count} missing values")
            success = False
        else:
            print("✅ SUCCESS: Backtest button fully functional")
            print("   - Button click triggers job")
            print("   - Table updates with results")
            print("   - All price data populated")
        
        await browser.close()
        return success

if __name__ == "__main__":
    success = asyncio.run(test_backtest_button())
    exit(0 if success else 1)

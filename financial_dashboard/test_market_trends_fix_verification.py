"""
Quick test to verify Market Trends "Refresh cached display" button now works
"""
import asyncio
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_refresh_button():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            logger.info("Loading Market Trends dashboard...")
            await page.goto('http://localhost:8050', wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000)
            
            logger.info("✅ Page loaded")
            
            # Check initial state
            logger.info("\n1. Checking initial results-area state...")
            results_area = page.locator('#results-area')
            initial_content = await results_area.inner_html()
            logger.info(f"Initial results-area content length: {len(initial_content)}")
            
            if len(initial_content) > 100:
                logger.info("✅ results-area already has content!")
            else:
                logger.info("⚠️ results-area is empty initially")
            
            # Click "Refresh cached display" button
            logger.info("\n2. Clicking 'Refresh cached display' button...")
            refresh_button = page.locator('button:has-text("Refresh cached display")')
            await refresh_button.click()
            logger.info("✅ Button clicked")
            
            # Wait for update
            logger.info("\n3. Waiting for table to appear...")
            await page.wait_for_timeout(3000)
            
            # Check if table appeared
            table_container = page.locator('[data-testid="trends-results-table-container"]')
            table_count = await table_container.count()
            
            if table_count > 0:
                logger.info("✅ TABLE FOUND! Fix is working!")
                
                # Count rows
                rows = await page.locator('[data-testid="trends-results-table-container"] tr').count()
                logger.info(f"✅ Table has {rows} rows")
                
                # Check for DataTable
                datatable = page.locator('.dash-table')
                if await datatable.count() > 0:
                    logger.info("✅ Dash DataTable component found")
                else:
                    logger.warning("⚠️ Dash DataTable class not found")
            else:
                logger.error("❌ Table container still not found after refresh")
                
                # Check results-area again
                final_content = await results_area.inner_html()
                logger.info(f"Final results-area content length: {len(final_content)}")
                
                if len(final_content) > len(initial_content):
                    logger.info("Content increased, but no testid container found")
                    logger.info(f"Content preview: {final_content[:500]}")
            
            # Check brief
            logger.info("\n4. Checking brief text...")
            brief_wrapper = page.locator('#compact-brief-wrapper')
            if await brief_wrapper.count() > 0:
                brief_text = await brief_wrapper.inner_text()
                if "No brief available" in brief_text:
                    logger.warning("⚠️ Brief still shows 'No brief available'")
                else:
                    logger.info(f"✅ Brief text found: {brief_text[:100]}...")
            
            # Check status message
            status_div = page.locator('#status')
            if await status_div.count() > 0:
                status_text = await status_div.inner_text()
                logger.info(f"Status message: {status_text}")
            
            # Take screenshot
            await page.screenshot(path='/tmp/market_trends_after_fix.png')
            logger.info("\n📸 Screenshot saved: /tmp/market_trends_after_fix.png")
            
            logger.info("\n" + "="*60)
            if table_count > 0:
                logger.info("✅ SUCCESS! Market Trends table is now displaying!")
            else:
                logger.error("❌ FAILED! Table still not showing")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await page.wait_for_timeout(3000)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_refresh_button())

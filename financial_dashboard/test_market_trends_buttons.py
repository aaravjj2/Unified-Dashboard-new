"""
Test Market Trends dashboard buttons using Playwright
Tests: Run Full Analysis, Refresh cached display, Reload Model buttons
"""
import asyncio
from playwright.async_api import async_playwright
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_market_trends():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Set to True for headless
        page = await browser.new_page()
        
        # Capture console messages
        console_messages = []
        page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))
        
        try:
            logger.info("Navigating to Market Trends dashboard...")
            await page.goto('http://localhost:8050', wait_until='networkidle', timeout=30000)
            logger.info("✅ Page loaded")
            
            # Wait for main content
            await page.wait_for_selector('h3:has-text("Market Trends")', timeout=10000)
            logger.info("✅ Market Trends title found")
            
            # Take initial screenshot
            await page.screenshot(path='/tmp/market_trends_initial.png')
            logger.info("📸 Initial screenshot saved")
            
            # Test 1: Check if cached data loads on page load
            logger.info("\n=== Checking for initial cached data ===")
            await page.wait_for_timeout(3000)
            
            # Look for table container
            table_container = page.locator('[data-testid="trends-results-table"]')
            if await table_container.count() > 0:
                logger.info("✅ Results table container found")
                # Check if table has rows
                rows = await page.locator('[data-testid="trends-results-table"] tr').count()
                logger.info(f"Table has {rows} rows")
            else:
                logger.warning("⚠️ No results table container found")
            
            # Check for brief text
            brief_div = page.locator('#mt-brief-text')
            if await brief_div.count() > 0:
                brief_text = await brief_div.inner_text()
                if brief_text and brief_text.strip() and "No brief available" not in brief_text:
                    logger.info(f"✅ Brief text found: {brief_text[:100]}...")
                else:
                    logger.warning(f"⚠️ Brief text empty or shows 'No brief available': {brief_text}")
            else:
                logger.warning("⚠️ Brief text div not found")
            
            # Test 2: Click "Refresh cached display" button
            logger.info("\n=== Testing REFRESH CACHED DISPLAY button ===")
            refresh_button = page.locator('button:has-text("Refresh cached display")')
            if await refresh_button.count() > 0:
                await refresh_button.click()
                logger.info("✅ Refresh cached display button clicked")
                await page.wait_for_timeout(3000)
                
                # Check if table updates
                if await table_container.count() > 0:
                    rows = await page.locator('[data-testid="trends-results-table"] tr').count()
                    logger.info(f"After refresh: Table has {rows} rows")
                else:
                    logger.warning("⚠️ Table still not visible after refresh")
                
                # Check brief again
                if await brief_div.count() > 0:
                    brief_text = await brief_div.inner_text()
                    if brief_text and brief_text.strip() and "No brief available" not in brief_text:
                        logger.info(f"✅ Brief text after refresh: {brief_text[:100]}...")
                    else:
                        logger.warning(f"⚠️ Brief still empty: {brief_text}")
                
                await page.screenshot(path='/tmp/market_trends_after_refresh.png')
                logger.info("📸 Screenshot after refresh saved")
            else:
                logger.error("❌ Refresh cached display button not found")
            
            # Test 3: Check "Reload Model" button
            logger.info("\n=== Testing RELOAD MODEL button ===")
            reload_button = page.locator('button:has-text("Reload Model")')
            if await reload_button.count() > 0:
                await reload_button.click()
                logger.info("✅ Reload Model button clicked")
                await page.wait_for_timeout(2000)
                
                # Check for model status message
                model_status = page.locator('#mt-model-status')
                if await model_status.count() > 0:
                    status_text = await model_status.inner_text()
                    logger.info(f"Model status: {status_text}")
                else:
                    logger.warning("⚠️ Model status div not found")
            else:
                logger.error("❌ Reload Model button not found")
            
            # Test 4: Run Full Analysis (if we want to test it)
            logger.info("\n=== Testing RUN FULL ANALYSIS button ===")
            
            # Check if ticker input exists
            ticker_input = page.locator('textarea[id="mt-tickers-input"]')
            if await ticker_input.count() > 0:
                current_value = await ticker_input.input_value()
                logger.info(f"Current tickers: {current_value}")
                
                # Optionally fill in test tickers (commented out to avoid running long job)
                # await ticker_input.fill("AAPL,MSFT,GOOGL")
                # logger.info("✅ Entered test tickers: AAPL,MSFT,GOOGL")
            else:
                logger.error("❌ Ticker input not found")
            
            run_button = page.locator('button:has-text("Run Full Analysis")')
            if await run_button.count() > 0:
                logger.info("✅ Run Full Analysis button found (not clicking to avoid long job)")
                # await run_button.click()  # Uncomment to actually run
            else:
                logger.error("❌ Run Full Analysis button not found")
            
            # Test 5: Check job status section
            logger.info("\n=== Checking JOB STATUS section ===")
            status_div = page.locator('#mt-job-status')
            if await status_div.count() > 0:
                status_text = await status_div.inner_text()
                logger.info(f"Job status: {status_text}")
            else:
                logger.warning("⚠️ Job status div not found")
            
            # Final screenshot
            await page.screenshot(path='/tmp/market_trends_final.png')
            logger.info("📸 Final screenshot saved")
            
            # Print console messages
            if console_messages:
                logger.info("\n=== Browser Console Messages (last 30) ===")
                for msg in console_messages[-30:]:
                    logger.info(msg)
            
            logger.info("\n=== TEST SUMMARY ===")
            logger.info("Market Trends button tests completed. Check logs and screenshots.")
            logger.info("Screenshots saved:")
            logger.info("  - /tmp/market_trends_initial.png")
            logger.info("  - /tmp/market_trends_after_refresh.png")
            logger.info("  - /tmp/market_trends_final.png")
            
        except Exception as e:
            logger.error(f"❌ Error during test: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path='/tmp/market_trends_error.png')
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_market_trends())

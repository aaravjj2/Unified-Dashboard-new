"""
Test Market Forecast dashboard buttons using Playwright
Tests: Run Forecast, Ping, Download, Backtest buttons
"""
import asyncio
from playwright.async_api import async_playwright
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_market_forecast():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Set to True for headless
        page = await browser.new_page()
        
        # Capture console messages
        console_messages = []
        page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))
        
        try:
            logger.info("Navigating to Market Forecast dashboard...")
            await page.goto('http://localhost:8051', wait_until='networkidle', timeout=30000)
            logger.info("✅ Page loaded")
            
            # Wait for main content
            await page.wait_for_selector('h3:has-text("Market Forecast")', timeout=10000)
            logger.info("✅ Market Forecast title found")
            
            # Test 1: Ping button
            logger.info("\n=== Testing PING button ===")
            ping_button = page.locator('button:has-text("Ping")')
            if await ping_button.count() > 0:
                await ping_button.click()
                logger.info("✅ Ping button clicked")
                await page.wait_for_timeout(2000)
                
                # Check for ping output
                ping_output = page.locator('#mf-ping-output')
                if await ping_output.count() > 0:
                    text = await ping_output.inner_text()
                    logger.info(f"✅ Ping output: {text}")
                else:
                    logger.warning("⚠️ No ping output found")
            else:
                logger.error("❌ Ping button not found")
            
            # Test 2: Run Forecast button
            logger.info("\n=== Testing RUN FORECAST button ===")
            
            # Fill in tickers
            ticker_input = page.locator('input[id="mf-tickers"]')
            if await ticker_input.count() > 0:
                await ticker_input.fill("AAPL,MSFT")
                logger.info("✅ Entered tickers: AAPL,MSFT")
            else:
                logger.error("❌ Ticker input not found")
            
            # Fill in horizon
            horizon_input = page.locator('input[id="mf-horizon"]')
            if await horizon_input.count() > 0:
                await horizon_input.fill("30")
                logger.info("✅ Entered horizon: 30 days")
            else:
                logger.error("❌ Horizon input not found")
            
            # Click Run Forecast
            run_button = page.locator('button:has-text("Run Forecast")')
            if await run_button.count() > 0:
                await run_button.click()
                logger.info("✅ Run Forecast button clicked")
                
                # Wait for job status
                await page.wait_for_timeout(3000)
                
                # Check for job status message
                status_div = page.locator('#mf-status')
                if await status_div.count() > 0:
                    status_text = await status_div.inner_text()
                    logger.info(f"✅ Job status: {status_text}")
                else:
                    logger.warning("⚠️ No job status found")
                
                # Wait longer to see if job completes
                logger.info("Waiting 10 seconds for job to process...")
                await page.wait_for_timeout(10000)
                
                # Check status again
                if await status_div.count() > 0:
                    status_text = await status_div.inner_text()
                    logger.info(f"Job status after wait: {status_text}")
                
            else:
                logger.error("❌ Run Forecast button not found")
            
            # Test 3: Download CSV button
            logger.info("\n=== Testing DOWNLOAD CSV button ===")
            download_button = page.locator('button:has-text("Download CSV (latest)")')
            if await download_button.count() > 0:
                logger.info("✅ Download CSV button found")
                # Note: Actually clicking might trigger download, so we just verify it exists
            else:
                logger.error("❌ Download CSV button not found")
            
            # Test 4: Backtest buttons
            logger.info("\n=== Testing BACKTEST buttons ===")
            
            backtest_run = page.locator('button:has-text("Run Backtest")')
            if await backtest_run.count() > 0:
                logger.info("✅ Run Backtest button found")
            else:
                logger.error("❌ Run Backtest button not found")
            
            backtest_refresh = page.locator('button:has-text("Refresh Backtest outputs")')
            if await backtest_refresh.count() > 0:
                logger.info("✅ Refresh Backtest button found")
            else:
                logger.error("❌ Refresh Backtest button not found")
            
            # Take screenshot
            screenshot_path = '/tmp/market_forecast_test.png'
            await page.screenshot(path=screenshot_path)
            logger.info(f"\n📸 Screenshot saved: {screenshot_path}")
            
            # Print console messages
            if console_messages:
                logger.info("\n=== Browser Console Messages ===")
                for msg in console_messages[-20:]:  # Last 20 messages
                    logger.info(msg)
            
            logger.info("\n=== TEST SUMMARY ===")
            logger.info("All button tests completed. Check logs above for results.")
            
        except Exception as e:
            logger.error(f"❌ Error during test: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_market_forecast())

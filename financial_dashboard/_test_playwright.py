import asyncio
from playwright.async_api import async_playwright, expect
import time
import os
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_test(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Capture and log any browser console errors
        error_messages = []
        page.on("console", lambda msg: error_messages.append(msg.text) if msg.type == "error" else None)

        try:
            logger.info(f"Navigating to {url}...")
            await page.goto(url, wait_until='networkidle', timeout=60000)
            logger.info("Page loaded.")

            # 1. Verify main layout components are present
            logger.info("Verifying main layout...")
            await expect(page.locator("h2:has-text('Unified Market Dashboard')")).to_be_visible()
            await expect(page.locator("#tabs")).to_be_visible()
            # The tab content is now inside a wrapper
            await expect(page.locator("#tab-content")).to_be_visible()
            logger.info("Main layout verified.")

            # 2. Check Market Trends tab is loaded by default and click it
            logger.info("Verifying default tab (Market Trends)...")
            await expect(page.locator("h3:has-text('Market Trends')")).to_be_visible(timeout=20000)
            
            # Click the tab to ensure it's active
            trends_tab_selector = "div[role='tablist'] >> text=Market Trends"
            await page.locator(trends_tab_selector).click()
            logger.info("Market Trends tab is active.")

            # 3. Check for initial cached results using data-testid
            logger.info("Checking for initial cached results table...")
            results_table_selector = '[data-testid="trends-results-table"]'
            try:
                # Use a robust wait for the table to appear and have at least one row
                await expect(page.locator(f"{results_table_selector} tr")).to_have_count(1, timeout=15000)
                logger.info("Initial results table is present and has rows.")
            except Exception:
                logger.warning("No initial table rows found; this is acceptable if cache is empty.")

            # 4. Test the "Run Full Analysis" button
            logger.info("Testing 'Run Full Analysis' button...")
            await page.locator("#run-btn").click()

            # 5. Wait for the analysis to complete by watching the status element
            logger.info("Waiting for analysis to complete in the UI (up to 30s)...")
            status_locator = page.locator("#status")
            await expect(status_locator).to_contain_text(re.compile(r"completed|finished", re.IGNORECASE), timeout=30000)
            logger.info("Analysis completed in UI.")

            # 6. Verify the results table is populated with new data
            logger.info("Verifying results table is updated...")
            # The table should now be visible and contain multiple rows
            await expect(page.locator(f"{results_table_selector} tr").nth(5)).to_be_visible(timeout=10000)
            logger.info("Results table updated after analysis.")

            # 7. Final check for console errors
            if error_messages:
                errors = "\n".join(error_messages)
                raise AssertionError(f"Browser console errors detected during test:\n{errors}")

            logger.info("\nPlaywright test completed successfully!")

        except Exception as e:
            logger.exception(f"\nAn error occurred during the Playwright test: {e}")
            await page.screenshot(path='playwright_error_screenshot.png')
            logger.error("Screenshot saved to 'playwright_error_screenshot.png'")
            # Re-raise the exception to ensure the test fails in CI/CD environments
            raise
        finally:
            await browser.close()

async def main():
    port = os.environ.get("DASH_PORT", "8050")
    app_url = f"http://127.0.0.1:{port}"
    await run_test(app_url)

if __name__ == "__main__":
    asyncio.run(main())

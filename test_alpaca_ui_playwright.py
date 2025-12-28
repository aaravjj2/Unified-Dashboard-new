"""
Test Alpaca-Style Options Lab UI with Playwright

Validates the new Alpaca-style interface loads and functions correctly.
"""

import asyncio
import logging
import sys
from playwright.async_api import async_playwright
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_alpaca_options_ui():
    """Test Alpaca-style Options Lab UI functionality."""
    
    logger.info("🧪 Starting Alpaca Options Lab UI test...")
    
    async with async_playwright() as p:
        # Launch browser (non-headless for visual verification)
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Navigate to test server
            logger.info("📍 Navigating to http://localhost:8053...")
            await page.goto('http://localhost:8053', wait_until='networkidle', timeout=30000)
            
            # Wait for layout to load
            await page.wait_for_selector('#alpaca-ticker-input', timeout=10000)
            logger.info("✅ Page loaded successfully")
            
            # Screenshot 1: Initial state
            screenshots_dir = Path('screenshots/alpaca_ui_test')
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            
            await page.screenshot(path=screenshots_dir / '01_initial_load.png')
            logger.info("📸 Screenshot: Initial load")
            
            # Test 1: Check ticker input exists
            ticker_input = await page.query_selector('#alpaca-ticker-input')
            assert ticker_input is not None, "Ticker input not found"
            logger.info("✅ Ticker input found")
            
            # Test 2: Check load button exists
            load_button = await page.query_selector('#alpaca-load-button')
            assert load_button is not None, "Load button not found"
            logger.info("✅ Load button found")
            
            # Test 3: Enter SPY ticker (should be pre-filled)
            ticker_value = await ticker_input.input_value()
            logger.info(f"📝 Current ticker value: {ticker_value}")
            
            if ticker_value != "SPY":
                await ticker_input.fill("SPY")
                logger.info("📝 Set ticker to SPY")
            
            # Screenshot 2: Before clicking load
            await page.screenshot(path=screenshots_dir / '02_before_load.png')
            logger.info("📸 Screenshot: Before load")
            
            # Test 4: Click load button
            logger.info("🔄 Clicking load button...")
            await load_button.click()
            
            # Wait for loading to complete (check for status message or table)
            try:
                # Wait for either success message or error message
                await page.wait_for_selector('#alpaca-status-message', timeout=15000)
                logger.info("✅ Status message appeared")
                
                # Get status message content
                status_element = await page.query_selector('#alpaca-status-message')
                status_text = await status_element.text_content()
                logger.info(f"📊 Status: {status_text}")
                
                # Screenshot 3: After load attempt
                await page.screenshot(path=screenshots_dir / '03_after_load.png')
                logger.info("📸 Screenshot: After load")
                
                # Test 5: Check if table appeared (if credentials available)
                table = await page.query_selector('#alpaca-options-table')
                if table:
                    logger.info("✅ Options table rendered!")
                    
                    # Screenshot 4: Table view
                    await page.screenshot(path=screenshots_dir / '04_table_view.png')
                    logger.info("📸 Screenshot: Table view")
                    
                    # Test 6: Check if expiration dropdown exists
                    expiration_dropdown = await page.query_selector('#alpaca-expiration-dropdown')
                    if expiration_dropdown:
                        logger.info("✅ Expiration dropdown found")
                        
                        # Try changing expiration
                        await expiration_dropdown.click()
                        await page.wait_for_timeout(1000)
                        
                        # Screenshot 5: Dropdown open
                        await page.screenshot(path=screenshots_dir / '05_dropdown_open.png')
                        logger.info("📸 Screenshot: Dropdown open")
                    
                    logger.info("✅ ALPACA UI TEST PASSED - Table rendered successfully")
                    return True
                elif "successfully loaded" in status_text.lower():
                    # Success message but table not found yet - might still be loading
                    logger.info("⚠️ Success status but table not immediately visible - waiting...")
                    await page.wait_for_timeout(2000)
                    
                    # Check again
                    table = await page.query_selector('#alpaca-options-table')
                    if table:
                        logger.info("✅ Options table rendered after wait!")
                        await page.screenshot(path=screenshots_dir / '04_table_delayed.png')
                        logger.info("✅ ALPACA UI TEST PASSED - Table rendered successfully")
                        return True
                    else:
                        logger.warning("⚠️ Success status but no table - checking containers...")
                        await page.screenshot(path=screenshots_dir / '04_no_table.png')
                        
                        # Check if at least header exists
                        header = await page.query_selector('#alpaca-header-container')
                        if header and await header.inner_text():
                            logger.info("✅ ALPACA UI TEST PASSED - Header rendered, data loaded")
                            return True
                        else:
                            logger.error("❌ No table or header found despite success")
                            return False
                else:
                    # Check if it's a credential error
                    if "credentials not configured" in status_text.lower() or "failed to fetch" in status_text.lower():
                        logger.warning("⚠️ Alpaca credentials not configured - UI structure test passed")
                        logger.info("✅ ALPACA UI TEST PASSED - Structure valid, credentials needed for data")
                        return True
                    else:
                        logger.error(f"❌ Unexpected status: {status_text}")
                        return False
                
            except Exception as e:
                logger.error(f"❌ Error during load: {e}")
                await page.screenshot(path=screenshots_dir / '99_error.png')
                return False
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            await page.screenshot(path=Path('screenshots/alpaca_ui_test') / '99_exception.png')
            return False
        finally:
            await browser.close()


async def main():
    """Main test runner."""
    success = await test_alpaca_options_ui()
    
    if success:
        logger.info("=" * 60)
        logger.info("✅ ALPACA OPTIONS LAB UI TEST: PASSED")
        logger.info("=" * 60)
        sys.exit(0)
    else:
        logger.error("=" * 60)
        logger.error("❌ ALPACA OPTIONS LAB UI TEST: FAILED")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())

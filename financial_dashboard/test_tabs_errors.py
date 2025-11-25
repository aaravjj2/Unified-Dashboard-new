#!/usr/bin/env python3
"""
Playwright test to click tabs and capture any errors
"""
import sys
import asyncio
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_tabs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Capture console messages
        console_messages = []
        def handle_console(msg):
            console_messages.append(f"[{msg.type}] {msg.text}")
            if msg.type in ['error', 'warning']:
                logger.error(f"Console {msg.type}: {msg.text}")
        
        page.on("console", handle_console)
        
        # Capture page errors
        page_errors = []
        def handle_error(error):
            page_errors.append(str(error))
            logger.error(f"Page error: {error}")
        
        page.on("pageerror", handle_error)
        
        try:
            logger.info("Loading main page...")
            await page.goto('http://localhost:8000/', wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(2000)
            
            logger.info("Page loaded successfully")
            
            # Try to click each tab - using button/tab selectors
            tabs_to_test = [
                ('Analysis Hub', '[role="tab"]:has-text("Analysis Hub")'),
                ('Portfolio', '[role="tab"]:has-text("Portfolio")'),
                ('Research Lab', '[role="tab"]:has-text("Research Lab")')
            ]
            
            for tab_name, selector in tabs_to_test:
                try:
                    logger.info(f"\n{'='*50}")
                    logger.info(f"Testing tab: {tab_name}")
                    logger.info(f"{'='*50}")
                    
                    # Clear previous messages
                    console_messages.clear()
                    page_errors.clear()
                    
                    # Try to find and click the tab
                    tab_element = await page.query_selector(selector)
                    if tab_element:
                        logger.info(f"Found {tab_name} tab, clicking...")
                        await tab_element.click()
                        await page.wait_for_timeout(3000)
                        
                        # Check for error messages in the page
                        error_text = await page.text_content('body')
                        if 'internal server error' in error_text.lower():
                            logger.error(f"✗ {tab_name}: Shows 'Internal Server Error'")
                            
                            # Try to get more details
                            error_content = await page.query_selector('.dash-error')
                            if error_content:
                                error_details = await error_content.text_content()
                                logger.error(f"Error details: {error_details}")
                        else:
                            logger.info(f"✓ {tab_name}: No internal server error visible")
                        
                        # Show console errors
                        if page_errors:
                            logger.error(f"Page errors for {tab_name}:")
                            for err in page_errors:
                                logger.error(f"  - {err}")
                        
                        # Show console messages
                        error_console = [msg for msg in console_messages if '[error]' in msg.lower()]
                        if error_console:
                            logger.error(f"Console errors for {tab_name}:")
                            for msg in error_console:
                                logger.error(f"  - {msg}")
                    else:
                        logger.warning(f"Could not find {tab_name} tab with selector: {selector}")
                    
                except Exception as e:
                    logger.error(f"Error testing {tab_name}: {e}")
            
            # Save final screenshot
            await page.screenshot(path='/mnt/c/Aarav/fin_env/Dash/test_tabs_errors.png', full_page=True)
            logger.info("\nScreenshot saved: test_tabs_errors.png")
            
        except Exception as e:
            logger.error(f"Error during test: {e}")
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(test_tabs())

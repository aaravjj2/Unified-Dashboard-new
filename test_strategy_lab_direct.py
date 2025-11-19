#!/usr/bin/env python3
"""
Strategy Lab Direct Test
Tests Strategy Lab buttons after callback fixes.
"""

import asyncio
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_strategy_lab():
    """Test Strategy Lab buttons directly."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Non-headless to see what happens
        page = await browser.new_page()
        
        # Capture console errors
        console_errors = []
        page.on("console", lambda msg: 
            console_errors.append(f"[{msg.type}] {msg.text()}") if msg.type in ["error", "warning"] else None)
        
        try:
            logger.info("Loading dashboard...")
            await page.goto("http://localhost:8050", timeout=30000)
            await page.wait_for_timeout(3000)
            
            logger.info("Clicking Strategy Lab tab...")
            # Find and click Strategy Lab - it's the 4th tab
            await page.click("ul.nav a.nav-link:has-text('Strategy Lab')", timeout=10000)
            await page.wait_for_timeout(2000)
            
            logger.info("Strategy Lab loaded. Checking for console errors...")
            await page.wait_for_timeout(2000)
            
            if console_errors:
                logger.error(f"❌ Found {len(console_errors)} console errors:")
                for err in console_errors:
                    logger.error(f"   {err}")
            else:
                logger.info("✅ No console errors on Strategy Lab load!")
            
            # Test Setup tab - Validate button
            logger.info("\nTesting Setup tab - Validate Strategy button...")
            validate_btn = await page.query_selector("button#sl-validate-btn")
            if validate_btn:
                logger.info("✅ Validate button found!")
                await validate_btn.click()
                await page.wait_for_timeout(2000)
                
                # Check for validation result
                validation_result = await page.query_selector("#sl-validation-result")
                if validation_result:
                    text = await validation_result.inner_text()
                    logger.info(f"✅ Validation result displayed: {text[:100]}")
                else:
                    logger.error("❌ Validation result element not found")
            else:
                logger.error("❌ Validate button not found!")
            
            # Test Backtest tab
            logger.info("\nTesting Backtest tab...")
            await page.click("button#backtest-tab", timeout=5000)
            await page.wait_for_timeout(1000)
            
            # Check for date pickers
            start_date = await page.query_selector("#sl-start-date")
            end_date = await page.query_selector("#sl-end-date")
            
            if start_date and end_date:
                logger.info("✅ Date pickers found (sl-start-date, sl-end-date)")
            else:
                logger.error(f"❌ Date pickers missing - start:{start_date is not None}, end:{end_date is not None}")
            
            # Test Execute tab
            logger.info("\nTesting Execute tab...")
            await page.click("button#execute-tab", timeout=5000)
            await page.wait_for_timeout(1000)
            
            run_backtest_btn = await page.query_selector("button#sl-run-backtest-btn")
            if run_backtest_btn:
                logger.info("✅ Run Backtest button found!")
            else:
                logger.error("❌ Run Backtest button not found!")
            
            # Test Results tab
            logger.info("\nTesting Results tab...")
            await page.click("button#results-tab", timeout=5000)
            await page.wait_for_timeout(1000)
            
            # Check for metric components
            metrics = ["sl-metric-cagr", "sl-metric-sharpe", "sl-metric-maxdd", "sl-metric-winrate"]
            for metric_id in metrics:
                elem = await page.query_selector(f"#{metric_id}")
                if elem:
                    logger.info(f"✅ {metric_id} found")
                else:
                    logger.error(f"❌ {metric_id} NOT FOUND")
            
            # Test Benchmark tab
            logger.info("\nTesting Benchmark tab...")
            await page.click("button#benchmark-tab", timeout=5000)
            await page.wait_for_timeout(1000)
            
            # Check for new charts
            charts = ["sl-vs-benchmark", "sl-factor-attribution", "sl-exposure-breakdown"]
            for chart_id in charts:
                elem = await page.query_selector(f"#{chart_id}")
                if elem:
                    logger.info(f"✅ {chart_id} found")
                else:
                    logger.error(f"❌ {chart_id} NOT FOUND")
            
            logger.info("\n" + "="*80)
            logger.info("FINAL CONSOLE ERRORS:")
            logger.info("="*80)
            if console_errors:
                for err in console_errors:
                    logger.info(err)
            else:
                logger.info("✅ NO CONSOLE ERRORS!")
            
            # Keep browser open for 10 seconds for visual inspection
            logger.info("\nKeeping browser open for 10 seconds for visual inspection...")
            await page.wait_for_timeout(10000)
            
        except Exception as e:
            logger.error(f"❌ Test failed: {str(e)}")
            raise
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_strategy_lab())

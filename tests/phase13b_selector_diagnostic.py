#!/usr/bin/env python3
"""Phase 13B - Quick Selector Diagnostic"""

import asyncio
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

async def test_selectors():
    """Test each tab selector quickly"""
    async with async_playwright() as p:
        logger.info("🚀 Launching Chromium...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        
        logger.info("📍 Navigating to http://localhost:8050...")
        await page.goto("http://localhost:8050", wait_until="networkidle", timeout=30000)
        
        logger.info("⏳ Waiting for dashboard tabs...")
        await page.wait_for_selector("#dashboard-tabs", state="visible", timeout=15000)
        
        # Test each tab selector
        tabs_to_test = {
            "home_lab": "#tab-home_lab",
            "market_forecast": "#tab-market_forecast",
            "portfolio": "#tab-portfolio",
            "azure_ml_lab": "#tab-azure_ml_lab",
            "options_lab": "#tab-options_lab",
            "strategy_lab": "#tab-strategy_lab",
            "weekly_picks": "#tab-weekly_picks",
            "monthly_picks": "#tab-monthly_picks",
            "market_trends": "#tab-market_trends"
        }
        
        results = []
        for tab_id, selector in tabs_to_test.items():
            try:
                # Check if selector exists
                count = await page.locator(selector).count()
                if count > 0:
                    logger.info(f"  ✅ {tab_id}: Found {count} element(s) with {selector}")
                    results.append((tab_id, "FOUND", selector))
                else:
                    logger.warning(f"  ❌ {tab_id}: No elements found for {selector}")
                    results.append((tab_id, "MISSING", selector))
            except Exception as e:
                logger.error(f"  ❌ {tab_id}: Error - {e}")
                results.append((tab_id, "ERROR", str(e)))
        
        logger.info("\n" + "="*60)
        logger.info("📊 SELECTOR DIAGNOSTIC SUMMARY")
        logger.info("="*60)
        for tab_id, status, detail in results:
            logger.info(f"{status:8s} | {tab_id:20s} | {detail}")
        
        await browser.close()
        logger.info("\n✅ Diagnostic complete!")

if __name__ == "__main__":
    asyncio.run(test_selectors())

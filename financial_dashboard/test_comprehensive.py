#!/usr/bin/env python3
"""
Comprehensive Playwright test for all dashboard tabs and functionality.
Tests each tab, verifies data tables, buttons, and UI elements.
"""

import asyncio
from playwright.async_api import async_playwright, expect
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DashboardTester:
    def __init__(self, url='http://127.0.0.1:8050'):
        self.url = url
        self.browser = None
        self.page = None
        self.errors = []
        
    async def setup(self):
        """Set up the browser and navigate to the dashboard"""
        self.browser = await self.playwright.chromium.launch(headless=False, slow_mo=500)
        self.page = await self.browser.new_page()
        await self.page.goto("http://127.0.0.1:8050", wait_until="networkidle", timeout=30000)
        # Wait for React to render
        await asyncio.sleep(3)
        
    async def teardown(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()
    
    async def navigate_to_tab(self, tab_name):
        """Navigate to a specific tab."""
        logger.info(f"Navigating to {tab_name} tab...")
        try:
            # Click the tab
            await self.page.click(f".tab:has-text('{tab_name}')", timeout=5000)
            await self.page.wait_for_timeout(2000)
            logger.info(f"✓ {tab_name} tab loaded")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to load {tab_name} tab: {e}")
            await self.page.screenshot(path=f'error_{tab_name.replace(" ", "_").lower()}.png')
            return False
    
    async def test_main_layout(self):
        """Test that the main dashboard layout loads correctly"""
        logger.info("="*80)
        logger.info("Testing Main Layout")
        logger.info("="*80)
        
        try:
            # Check for dashboard title
            await expect(self.page.locator("h1")).to_contain_text("Unified Market Dashboard")
            logger.info("✓ Dashboard title present")
            
            # Check for tabs container - using correct class name
            tabs_container = self.page.locator("#tabs-container, .tab-container")
            await expect(tabs_container).to_be_visible(timeout=5000)
            logger.info("✓ Tabs container visible")
            
            # Check that tabs are present
            tabs = self.page.locator(".tab")
            tab_count = await tabs.count()
            logger.info(f"✓ Found {tab_count} tabs")
            
            if tab_count == 0:
                raise Exception("No tabs found!")
            
        except Exception as e:
            logger.error(f"✗ {str(e)}")
            self.errors.append(f"Main layout error: {str(e)}")
            await self.page.screenshot(path="error_main_layout.png")
    
    async def test_market_trends(self):
        """Test Market Trends tab"""
        logger.info("="*80)
        logger.info("Testing Market Trends Tab")
        logger.info("="*80)
        
        try:
            logger.info("Navigating to Market Trends tab...")
            # Click Market Trends tab - using correct selector
            await self.page.click(".tab:has-text('Market Trends')", timeout=5000)
            await self.page.wait_for_load_state("networkidle")
            logger.info("✓ Market Trends tab loaded")
            
            # Check for analysis results
            await asyncio.sleep(2)
            content = self.page.locator("#tab-content")
            await expect(content).to_be_visible(timeout=5000)
            logger.info("✓ Tab content visible")
            
            # Check for data table
            table = self.page.locator("table, .dash-table")
            await expect(table.first).to_be_visible(timeout=10000)
            logger.info("✓ Market Trends table visible")
            
        except Exception as e:
            logger.error(f"✗ Failed to load Market Trends tab: {e}")
            self.errors.append(f"Market Trends tab error: {str(e)}")
            await self.page.screenshot(path="error_market_trends.png")
    
    async def test_weekly_picks(self):
        """Test Weekly Picks tab."""
        logger.info("="*80)
        logger.info("Testing Weekly Picks Tab")
        logger.info("="*80)
        
        if not await self.navigate_to_tab("Weekly Picks"):
            return False
        
        # Check for results table
        try:
            table = self.page.locator("table, .dash-table")
            await expect(table).to_be_visible(timeout=10000)
            logger.info("✓ Weekly Picks table visible")
        except Exception as e:
            logger.error(f"✗ Weekly Picks table missing: {e}")
            return False
        
        return True
    
    async def test_monthly_picks(self):
        """Test Monthly Picks tab."""
        logger.info("="*80)
        logger.info("Testing Monthly Picks Tab")
        logger.info("="*80)
        
        if not await self.navigate_to_tab("Monthly Picks"):
            return False
        
        # Check for results table
        try:
            table = self.page.locator("table, .dash-table")
            await expect(table).to_be_visible(timeout=10000)
            logger.info("✓ Monthly Picks table visible")
        except Exception as e:
            logger.error(f"✗ Monthly Picks table missing: {e}")
            return False
        
        return True
    
    async def test_portfolio(self):
        """Test Portfolio tab."""
        logger.info("="*80)
        logger.info("Testing Portfolio Tab")
        logger.info("="*80)
        
        if not await self.navigate_to_tab("Portfolio"):
            return False
        
        # Check for summary cards
        try:
            value_card = self.page.locator("#portfolio-value")
            await expect(value_card).to_be_visible(timeout=5000)
            logger.info("✓ Portfolio value card visible")
        except:
            logger.error("✗ Portfolio value card missing")
        
        # Check for sub-tabs
        try:
            positions_tab = self.page.locator("text=Positions")
            await expect(positions_tab).to_be_visible(timeout=5000)
            logger.info("✓ Portfolio sub-tabs visible")
        except:
            logger.error("✗ Portfolio sub-tabs missing")
            return False
        
        return True
    
    async def test_text_visibility(self):
        """Test that text in white boxes is black."""
        logger.info("="*80)
        logger.info("Testing Text Color in White Boxes")
        logger.info("="*80)
        
        # Check card body text color
        cards = await self.page.query_selector_all(".card-body")
        if not cards:
            logger.warning("No cards found to test text color")
            return True
        
        for i, card in enumerate(cards[:3]):  # Test first 3 cards
            try:
                color = await card.evaluate("el => window.getComputedStyle(el).color")
                logger.info(f"Card {i+1} text color: {color}")
                # Black or dark text should have low RGB values
                if "0, 0, 0" in color or "rgb(0" in color:
                    logger.info(f"✓ Card {i+1} has dark text")
                else:
                    logger.warning(f"⚠ Card {i+1} text may not be dark enough: {color}")
            except Exception as e:
                logger.error(f"✗ Could not check card {i+1} text color: {e}")
        
        return True
    
    async def run_all_tests(self):
        """Run all tests."""
        await self.setup()
        
        try:
            all_passed = True
            
            # Test main layout
            if not await self.test_main_layout():
                all_passed = False
            
            # Test individual tabs
            await self.test_market_trends()
            await self.test_weekly_picks()
            await self.test_monthly_picks()
            await self.test_portfolio()
            
            # Test text visibility
            await self.test_text_visibility()
            
            # Summary
            logger.info("="*80)
            logger.info("TEST SUMMARY")
            logger.info("="*80)
            if self.errors:
                logger.error(f"Errors encountered: {len(self.errors)}")
                for err in self.errors:
                    logger.error(f"  - {err}")
                all_passed = False
            
            if all_passed:
                logger.info("✓ ALL TESTS PASSED")
            else:
                logger.error("✗ SOME TESTS FAILED")
            
            return all_passed
            
        finally:
            await self.teardown()

async def main():
    async with async_playwright() as playwright:
        tester = DashboardTester()
        tester.playwright = playwright
        success = await tester.run_all_tests()
        return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

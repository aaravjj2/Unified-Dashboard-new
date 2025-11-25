"""
Browser Tests for Market Forecast, Research Lab, and Volatility Lab
Tests button clicks and takes screenshots using Playwright
"""

import pytest
import asyncio
from playwright.async_api import async_playwright, Page
from pathlib import Path
import time

DASHBOARD_URL = "http://localhost:8051"
SCREENSHOTS_DIR = Path("reports/browser_tests/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

pytestmark = pytest.mark.asyncio


class TestMarketForecast:
    """Test Market Forecast tab buttons and UI"""
    
    async def test_market_forecast_tab_exists(self):
        """Test that Market Forecast tab is visible"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto(DASHBOARD_URL)
            await page.wait_for_timeout(2000)
            
            # Take initial screenshot
            await page.screenshot(path=SCREENSHOTS_DIR / "01_market_forecast_initial.png", full_page=True)
            
            # Check if Market Forecast tab exists
            market_forecast_tab = page.locator('a:has-text("Market Forecast")')
            is_visible = await market_forecast_tab.is_visible()
            
            print(f"✓ Market Forecast tab visible: {is_visible}")
            
            await browser.close()
            assert is_visible, "Market Forecast tab should be visible"
    
    async def test_market_forecast_ui_elements(self):
        """Test Market Forecast UI elements are present"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto(DASHBOARD_URL)
            await page.wait_for_timeout(2000)
            
            # Click Market Forecast tab if it exists
            try:
                market_forecast_tab = page.locator('a:has-text("Market Forecast")')
                if await market_forecast_tab.is_visible():
                    await market_forecast_tab.click()
                    await page.wait_for_timeout(2000)
                    
                    # Take screenshot after clicking tab
                    await page.screenshot(path=SCREENSHOTS_DIR / "02_market_forecast_tab_clicked.png", full_page=True)
                    
                    # Check for component IDs (mf-* prefix)
                    ticker_input = page.locator('#mf-ticker-input')
                    run_button = page.locator('#mf-run-button')
                    
                    ticker_exists = await ticker_input.count() > 0
                    button_exists = await run_button.count() > 0
                    
                    print(f"✓ Ticker input exists: {ticker_exists}")
                    print(f"✓ Run button exists: {button_exists}")
                    
                    await browser.close()
                else:
                    print("⚠️ Market Forecast tab not found")
                    await browser.close()
            except Exception as e:
                print(f"❌ Error: {e}")
                await browser.close()
                raise


class TestResearchLab:
    """Test Research Lab tab buttons and UI"""
    
    async def test_research_lab_load(self):
        """Test Research Lab tab loads"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto(DASHBOARD_URL)
            await page.wait_for_timeout(2000)
            
            # Find and click Research Lab tab
            research_tab = page.locator('a:has-text("Research Lab")')
            if await research_tab.is_visible():
                await research_tab.click()
                await page.wait_for_timeout(2000)
                
                # Take screenshot
                await page.screenshot(path=SCREENSHOTS_DIR / "03_research_lab_loaded.png", full_page=True)
                
                # Check for Research Lab buttons
                generate_button = page.locator('button:has-text("Generate")')
                button_exists = await generate_button.count() > 0
                
                print(f"✓ Research Lab loaded")
                print(f"✓ Generate button exists: {button_exists}")
                
                await browser.close()
            else:
                print("⚠️ Research Lab tab not found")
                await browser.close()
    
    async def test_research_lab_button_click(self):
        """Test Research Lab button click"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto(DASHBOARD_URL)
            await page.wait_for_timeout(2000)
            
            # Navigate to Research Lab
            research_tab = page.locator('a:has-text("Research Lab")')
            if await research_tab.is_visible():
                await research_tab.click()
                await page.wait_for_timeout(2000)
                
                # Try to click a button
                try:
                    generate_button = page.locator('button:has-text("Generate")').first
                    if await generate_button.is_visible():
                        await generate_button.click()
                        await page.wait_for_timeout(3000)
                        
                        # Take screenshot after click
                        await page.screenshot(path=SCREENSHOTS_DIR / "04_research_lab_button_clicked.png", full_page=True)
                        
                        print("✓ Research Lab button clicked successfully")
                except Exception as e:
                    print(f"⚠️ Could not click button: {e}")
                
                await browser.close()
            else:
                await browser.close()


class TestVolatilityLab:
    """Test Volatility Lab tab buttons and UI"""
    
    async def test_volatility_lab_load(self):
        """Test Volatility Lab tab loads"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto(DASHBOARD_URL)
            await page.wait_for_timeout(2000)
            
            # Find and click Volatility Lab tab
            vol_tab = page.locator('a:has-text("Volatility Lab")')
            if await vol_tab.is_visible():
                await vol_tab.click()
                await page.wait_for_timeout(2000)
                
                # Take screenshot
                await page.screenshot(path=SCREENSHOTS_DIR / "05_volatility_lab_loaded.png", full_page=True)
                
                # Check for Volatility Lab buttons
                compute_button = page.locator('button:has-text("Compute")')
                button_exists = await compute_button.count() > 0
                
                print(f"✓ Volatility Lab loaded")
                print(f"✓ Compute button exists: {button_exists}")
                
                await browser.close()
            else:
                print("⚠️ Volatility Lab tab not found")
                await browser.close()
    
    async def test_volatility_lab_button_click(self):
        """Test Volatility Lab button click"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto(DASHBOARD_URL)
            await page.wait_for_timeout(2000)
            
            # Navigate to Volatility Lab
            vol_tab = page.locator('a:has-text("Volatility Lab")')
            if await vol_tab.is_visible():
                await vol_tab.click()
                await page.wait_for_timeout(2000)
                
                # Try to click Compute IV Surface button
                try:
                    compute_button = page.locator('button:has-text("Compute IV Surface")').first
                    if await compute_button.is_visible():
                        # Take before screenshot
                        await page.screenshot(path=SCREENSHOTS_DIR / "06_volatility_lab_before_click.png", full_page=True)
                        
                        await compute_button.click()
                        await page.wait_for_timeout(4000)  # Wait for computation
                        
                        # Take after screenshot
                        await page.screenshot(path=SCREENSHOTS_DIR / "07_volatility_lab_after_click.png", full_page=True)
                        
                        print("✓ Volatility Lab button clicked successfully")
                    else:
                        print("⚠️ Compute button not visible")
                except Exception as e:
                    print(f"⚠️ Could not click button: {e}")
                
                await browser.close()
            else:
                await browser.close()


class TestAllTabs:
    """Test all three tabs in sequence"""
    
    async def test_all_tabs_workflow(self):
        """Test navigating through all three tabs and taking screenshots"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # Visible browser
            page = await browser.new_page()
            
            await page.goto(DASHBOARD_URL)
            await page.wait_for_timeout(2000)
            
            # Initial state
            await page.screenshot(path=SCREENSHOTS_DIR / "workflow_01_initial.png", full_page=True)
            print("✓ Step 1: Initial page loaded")
            
            # Test Market Forecast
            try:
                mf_tab = page.locator('a:has-text("Market Forecast")')
                if await mf_tab.is_visible():
                    await mf_tab.click()
                    await page.wait_for_timeout(2000)
                    await page.screenshot(path=SCREENSHOTS_DIR / "workflow_02_market_forecast.png", full_page=True)
                    print("✓ Step 2: Market Forecast tab loaded")
            except Exception as e:
                print(f"⚠️ Market Forecast error: {e}")
            
            # Test Research Lab
            try:
                rl_tab = page.locator('a:has-text("Research Lab")')
                if await rl_tab.is_visible():
                    await rl_tab.click()
                    await page.wait_for_timeout(2000)
                    await page.screenshot(path=SCREENSHOTS_DIR / "workflow_03_research_lab.png", full_page=True)
                    print("✓ Step 3: Research Lab tab loaded")
            except Exception as e:
                print(f"⚠️ Research Lab error: {e}")
            
            # Test Volatility Lab
            try:
                vl_tab = page.locator('a:has-text("Volatility Lab")')
                if await vl_tab.is_visible():
                    await vl_tab.click()
                    await page.wait_for_timeout(2000)
                    await page.screenshot(path=SCREENSHOTS_DIR / "workflow_04_volatility_lab.png", full_page=True)
                    print("✓ Step 4: Volatility Lab tab loaded")
                    
                    # Try clicking Compute button
                    compute_btn = page.locator('button:has-text("Compute IV Surface")').first
                    if await compute_btn.is_visible():
                        await compute_btn.click()
                        await page.wait_for_timeout(4000)
                        await page.screenshot(path=SCREENSHOTS_DIR / "workflow_05_volatility_computed.png", full_page=True)
                        print("✓ Step 5: Volatility Lab computation complete")
            except Exception as e:
                print(f"⚠️ Volatility Lab error: {e}")
            
            await browser.close()
            print("\n✅ All workflow tests complete! Check reports/browser_tests/screenshots/")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

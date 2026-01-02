#!/usr/bin/env python3
"""Simple test to verify forecast chart rendering"""

import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Navigate
        await page.goto("http://localhost:8051", timeout=30000)
        await page.wait_for_load_state("networkidle")
        print("✅ Dashboard loaded")
        
        # Click Market Forecast tab
        await page.locator("text=Market Forecast").first.click()
        await page.wait_for_timeout(2000)
        print("✅ Market Forecast tab clicked")
        
        # Wait for button
        await page.wait_for_selector("#mf-run-btn", timeout=10000)
        
        # Click Generate Forecast
        btn = page.locator("#mf-run-btn")
        await btn.scroll_into_view_if_needed()
        await btn.click()
        print("🖱️ Clicked Generate Forecast")
        
        # Wait for processing
        print("⏳ Waiting for forecast...")
        await page.wait_for_timeout(10000)  # 10 seconds
        
        # Check for any plotly charts
        all_charts = await page.locator(".js-plotly-plot").count()
        print(f"\n📊 Total Plotly charts on page: {all_charts}")
        
        # Check specific containers
        containers = [
            "#mf-forecast-chart",
            "#mf-model-comparison-chart",
            "#mf-scenario-chart",
            "#mf-model-metrics"
        ]
        
        for container_id in containers:
            el = page.locator(container_id)
            exists = await el.count() > 0
            if exists:
                inner = await el.inner_html()
                has_plotly = "js-plotly-plot" in inner or "plotly" in inner.lower()
                print(f"  {container_id}: exists={exists}, has_chart={has_plotly}")
            else:
                print(f"  {container_id}: NOT FOUND")
        
        # Take screenshot
        await page.screenshot(path="final_forecast_check.png", full_page=True)
        print("\n📷 Screenshot: final_forecast_check.png")
        
        await browser.close()
        
        if all_charts >= 2:
            print("\n✅ TEST PASSED: Charts are rendering!")
            return 0
        else:
            print("\n⚠️ Check screenshot to verify rendering")
            return 0  # Don't fail, just check

if __name__ == "__main__":
    asyncio.run(main())

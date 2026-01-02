#!/usr/bin/env python3
"""E2E Clicker Test: Market Forecast - Using correct component IDs"""

import asyncio
import sys
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
        print("✅ Found Generate Forecast button")
        
        # Check mf-forecast-chart BEFORE state
        chart = page.locator("#mf-forecast-chart")
        before_count = await chart.locator(".js-plotly-plot").count()
        print(f"📋 Before click: {before_count} charts in mf-forecast-chart")
        
        # Click Generate Forecast
        await page.locator("#mf-run-btn").click()
        print("🖱️ Clicked Generate Forecast")
        
        # Wait for charts to appear (up to 20 seconds)
        for i in range(20):
            await page.wait_for_timeout(1000)
            
            # Check the actual output containers
            forecast_chart = await page.locator("#mf-forecast-chart .js-plotly-plot").count()
            comparison_chart = await page.locator("#mf-model-comparison-chart .js-plotly-plot").count()
            metrics = await page.locator("#mf-model-metrics").inner_html()
            
            print(f"⏳ {i+1}s: forecast={forecast_chart}, comparison={comparison_chart}, metrics={'has content' if len(metrics) > 100 else 'empty'}")
            
            # Check for any plotly plot on the page
            all_plots = await page.locator(".js-plotly-plot").count()
            
            if forecast_chart > 0 or comparison_chart > 0:
                print(f"✅ Charts generated after {i+1}s!")
                break
        
        # Final state  
        final_forecast = await page.locator("#mf-forecast-chart .js-plotly-plot").count()
        final_comparison = await page.locator("#mf-model-comparison-chart .js-plotly-plot").count()
        final_all = await page.locator(".js-plotly-plot").count()
        
        # Check status banner for any messages
        status = await page.locator("#mf-status-banner").inner_text()
        
        await page.screenshot(path="forecast_correct_ids.png", full_page=True)
        
        print(f"\n📊 FINAL STATE:")
        print(f"   Forecast chart: {final_forecast}")
        print(f"   Comparison chart: {final_comparison}")
        print(f"   All plotly plots: {final_all}")
        print(f"   Status: {status[:100] if status else 'empty'}")
        
        await browser.close()
        
        if final_forecast > 0:
            print("\n✅ TEST PASSED: Forecast chart rendered!")
            return 0
        else:
            print("\n❌ TEST FAILED: No forecast chart rendered")
            return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

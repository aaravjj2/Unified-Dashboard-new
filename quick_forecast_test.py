#!/usr/bin/env python3
"""Quick Forecast Test - Check if Generate Forecast works"""

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
        
        # Check BEFORE state
        output = page.locator("#mf-forecast-output")
        before_text = await output.inner_text() if await output.count() > 0 else ""
        print(f"📋 Before: {before_text[:80]}...")
        
        # Click Generate Forecast
        await page.locator("#mf-run-btn").click()
        print("🖱️ Clicked Generate Forecast")
        
        # Wait for graphs to appear (up to 30 seconds)
        success = False
        for i in range(30):
            await page.wait_for_timeout(1000)
            graphs = await page.locator("#mf-forecast-output .js-plotly-plot").count()
            if graphs > 0:
                print(f"✅ {graphs} forecast graphs generated after {i+1}s!")
                success = True
                break
            if i % 5 == 0:
                print(f"⏳ Waiting... {i}s")
        
        # Final check
        after_text = await output.inner_text() if await output.count() > 0 else ""
        final_graphs = await page.locator("#mf-forecast-output .js-plotly-plot").count()
        
        await page.screenshot(path="forecast_result.png", full_page=True)
        
        if final_graphs > 0:
            print(f"\n✅ TEST PASSED: {final_graphs} graphs generated!")
            print(f"📷 Screenshot: forecast_result.png")
            await browser.close()
            return 0
        else:
            print(f"\n❌ TEST FAILED: No graphs")
            print(f"Content: {after_text[:200]}")
            await browser.close()
            return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

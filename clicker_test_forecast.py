#!/usr/bin/env python3
"""E2E Clicker Test: Market Forecast - Generate Forecast button"""

import asyncio
from playwright.async_api import async_playwright, expect

async def main():
    print("🧪 E2E CLICKER TEST: Market Forecast Tab")
    print("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Navigate
        print("\n[1] Navigating to dashboard...")
        await page.goto("http://localhost:8051", timeout=30000)
        await page.wait_for_load_state("networkidle")
        print("✅ Dashboard loaded")
        
        # Click Market Forecast tab
        print("\n[2] Clicking Market Forecast tab...")
        tab = page.locator("text=Market Forecast").first
        await tab.click()
        await page.wait_for_timeout(2000)
        print("✅ Market Forecast tab clicked")
        
        # Wait for the tab to load 
        print("\n[3] Waiting for tab content to load...")
        await page.wait_for_selector("#mf-run-btn", timeout=10000)
        print("✅ Found Generate Forecast button")
        
        # Check what models are selected
        print("\n[4] Checking selected models...")
        checkboxes = page.locator("#mf-models-checklist input:checked")
        count = await checkboxes.count()
        print(f"   Selected models: {count}")
        
        # Check the forecast output BEFORE clicking
        print("\n[5] Checking BEFORE state...")
        output_area = page.locator("#mf-forecast-output")
        before_content = await output_area.inner_text() if await output_area.count() > 0 else "NOT FOUND"
        print(f"   Content: {before_content[:100]}...")
        
        # Now click the Generate Forecast button
        print("\n[6] Clicking 'Generate Forecast' button...")
        btn = page.locator("#mf-run-btn")
        await btn.scroll_into_view_if_needed()
        await btn.click()
        print("✅ Button clicked!")
        
        # Wait for the forecast to generate (this can take 5-10 seconds)
        print("\n[7] Waiting for forecast generation (up to 30s)...")
        
        # Try to detect loading state
        for i in range(30):
            await page.wait_for_timeout(1000)
            
            # Check if content has changed
            after_content = await output_area.inner_text() if await output_area.count() > 0 else "NOT FOUND"
            
            # Check for graphs appearing
            graphs = page.locator("#mf-forecast-output .js-plotly-plot")
            graph_count = await graphs.count()
            
            print(f"   {i+1}s: Graphs={graph_count}, Content changed={before_content != after_content}")
            
            # If we have graphs, we're done!
            if graph_count > 0:
                print("✅ Forecast graphs generated!")
                break
        
        # Final state
        print("\n[8] FINAL STATE:")
        final_content = await output_area.inner_text() if await output_area.count() > 0 else "NOT FOUND"
        final_graphs = await page.locator("#mf-forecast-output .js-plotly-plot").count()
        
        print(f"   Output graphs: {final_graphs}")
        print(f"   Content preview: {final_content[:200]}...")
        
        # Check for any loading spinner or error message
        spinner = await page.locator(".fa-spinner, .loading").count()
        error_msg = page.locator("#mf-forecast-output :text('error')")
        error_count = await error_msg.count()
        
        print(f"   Loading spinners: {spinner}")
        print(f"   Error messages: {error_count}")
        
        # Take screenshot
        await page.screenshot(path="forecast_test_result.png", full_page=True)
        print("\n📷 Screenshot saved: forecast_test_result.png")
        
        # Summary
        print("\n" + "=" * 60)
        if final_graphs > 0:
            print("✅ TEST PASSED: Forecast generated successfully!")
        else:
            print("❌ TEST FAILED: No forecast graphs generated!")
            print(f"   Final content: {final_content}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

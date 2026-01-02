#!/usr/bin/env python3
"""
Quick test for Market Forecast Tab components
"""

import asyncio
from playwright.async_api import async_playwright

async def test_market_forecast():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Navigate to dashboard
            print("📍 Navigating to dashboard...")
            await page.goto("http://localhost:8051", timeout=30000)
            await asyncio.sleep(3)
            
            # Click Market Forecast tab
            print("📍 Clicking Market Forecast tab...")
            await page.click("text=Market Forecast")
            await asyncio.sleep(3)
            
            # Take screenshot for debugging
            await page.screenshot(path="/tmp/mf_test.png")
            print("📸 Screenshot saved to /tmp/mf_test.png")
            
            # Check components
            print("\n📋 COMPONENT CHECK:")
            
            # Preset dropdown
            preset = await page.query_selector("#mf-preset-select")
            print(f"  Preset Dropdown (#mf-preset-select): {'✅ Found' if preset else '❌ Not Found'}")
            
            # Auto-tune toggle  
            autotune = await page.query_selector("#mf-autotune-toggle")
            print(f"  Auto-Tune Toggle: {'✅ Found' if autotune else '⚠️ Not Found'}")
            
            # Train All button
            train_all = await page.query_selector("#mf-train-all-btn")
            print(f"  Train All Button: {'✅ Found' if train_all else '❌ Not Found'}")
            
            # Run button
            run_btn = await page.query_selector("#mf-run-btn")
            print(f"  Run Button: {'✅ Found' if run_btn else '❌ Not Found'}")
            
            # Leaderboard section
            leaderboard = await page.query_selector("#mf-leaderboard-collapse")
            print(f"  Leaderboard Section: {'✅ Found' if leaderboard else '⚠️ Not Found'}")
            
            # Progress modal
            progress = await page.query_selector("#mf-progress-modal")
            print(f"  Progress Modal: {'✅ Found' if progress else '⚠️ Not Found'}")
            
            # Status display
            status = await page.query_selector("#mf-status")
            print(f"  Status Display: {'✅ Found' if status else '❌ Not Found'}")
            
            # Test Train All if found
            if train_all:
                print("\n🚀 Testing Train All button...")
                await page.click("#mf-train-all-btn")
                await asyncio.sleep(10)
                
                status_el = await page.query_selector("#mf-status")
                if status_el:
                    status_text = await status_el.inner_text()
                    print(f"  📊 Status after training: {status_text}")
                
                # Check for forecast graph
                graph = await page.query_selector("#mf-forecast-graph")
                if graph:
                    print("  📈 Forecast graph generated!")
                    
                await page.screenshot(path="/tmp/mf_after_train.png")
                print("📸 Post-training screenshot saved to /tmp/mf_after_train.png")
            
            print("\n✅ Test complete!")
            
        except Exception as e:
            print(f"❌ Test error: {e}")
            await page.screenshot(path="/tmp/mf_error.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_market_forecast())

#!/usr/bin/env python3
"""
End-to-End Test for Market Forecast Tab
Tests all the new features: presets, leaderboard, Train All button
"""

import asyncio
from playwright.async_api import async_playwright
import json

async def test_market_forecast():
    results = {
        "preset_dropdown": False,
        "preset_options": [],
        "autotune_toggle": False,
        "train_all_button": False,
        "leaderboard_section": False,
        "run_forecast": False,
        "models_trained": 0,
        "forecast_status": "",
        "leaderboard_populated": False,
        "errors": []
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Navigate to dashboard
            print("📍 Navigating to dashboard...")
            await page.goto("http://localhost:8051", wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)
            
            # Click Market Forecast tab
            print("📍 Clicking Market Forecast tab...")
            tabs = await page.query_selector_all(".nav-link")
            for tab in tabs:
                text = await tab.inner_text()
                if "Market Forecast" in text:
                    await tab.click()
                    break
            await asyncio.sleep(2)
            
            # Check for preset dropdown (dbc.Select)
            print("📍 Checking preset dropdown...")
            preset_select = await page.query_selector("#mf-preset-select")
            if preset_select:
                results["preset_dropdown"] = True
                # Get options
                options = await page.query_selector_all("#mf-preset-select option")
                for opt in options:
                    text = await opt.inner_text()
                    results["preset_options"].append(text.strip())
                print(f"  ✅ Preset dropdown found with options: {results['preset_options']}")
            else:
                print("  ❌ Preset dropdown not found")
                results["errors"].append("Preset dropdown #mf-preset-select not found")
            
            # Check for Auto-Tune toggle
            print("📍 Checking Auto-Tune toggle...")
            autotune = await page.query_selector("#mf-autotune-toggle")
            if autotune:
                results["autotune_toggle"] = True
                print("  ✅ Auto-Tune toggle found")
            else:
                print("  ⚠️  Auto-Tune toggle not found")
            
            # Check for Train All button
            print("📍 Checking Train All button...")
            train_all = await page.query_selector("#mf-train-all-btn")
            if train_all:
                results["train_all_button"] = True
                print("  ✅ Train All button found")
            else:
                print("  ❌ Train All button not found")
                results["errors"].append("Train All button not found")
            
            # Check for leaderboard section
            print("📍 Checking Leaderboard section...")
            leaderboard = await page.query_selector("#mf-leaderboard-collapse")
            if leaderboard:
                results["leaderboard_section"] = True
                print("  ✅ Leaderboard section found")
            else:
                print("  ⚠️  Leaderboard section not found")
            
            # Test running forecast with Train All
            print("\n📍 Testing Train All forecast...")
            if results["train_all_button"]:
                # Select a preset first
                if results["preset_dropdown"]:
                    await page.select_option("#mf-preset-select", "fast")
                    await asyncio.sleep(0.5)
                    print("  📝 Selected 'fast' preset")
                
                # Click Train All
                await page.click("#mf-train-all-btn")
                print("  🚀 Clicked Train All button")
                
                # Wait for forecast to complete
                await asyncio.sleep(15)  # Give time for models to train
                
                # Check status
                status_el = await page.query_selector("#mf-status")
                if status_el:
                    status_text = await status_el.inner_text()
                    results["forecast_status"] = status_text
                    print(f"  📊 Status: {status_text}")
                    
                    if "model" in status_text.lower():
                        results["run_forecast"] = True
                        # Extract model count
                        import re
                        match = re.search(r"(\d+)\s*model", status_text)
                        if match:
                            results["models_trained"] = int(match.group(1))
                
                # Check if leaderboard populated
                leaderboard_table = await page.query_selector("#mf-leaderboard-table table")
                if leaderboard_table:
                    rows = await page.query_selector_all("#mf-leaderboard-table table tbody tr")
                    if len(rows) > 0:
                        results["leaderboard_populated"] = True
                        print(f"  🏆 Leaderboard has {len(rows)} entries")
                
            # Print summary
            print("\n" + "="*60)
            print("📋 TEST RESULTS SUMMARY")
            print("="*60)
            print(f"✅ Preset Dropdown: {'PASS' if results['preset_dropdown'] else 'FAIL'}")
            if results['preset_options']:
                print(f"   Options: {', '.join(results['preset_options'])}")
            print(f"✅ Auto-Tune Toggle: {'PASS' if results['autotune_toggle'] else 'NOT FOUND'}")
            print(f"✅ Train All Button: {'PASS' if results['train_all_button'] else 'FAIL'}")
            print(f"✅ Leaderboard Section: {'PASS' if results['leaderboard_section'] else 'NOT FOUND'}")
            print(f"✅ Forecast Execution: {'PASS' if results['run_forecast'] else 'FAIL'}")
            print(f"   Models Trained: {results['models_trained']}")
            print(f"   Status: {results['forecast_status']}")
            print(f"✅ Leaderboard Data: {'PASS' if results['leaderboard_populated'] else 'NOT POPULATED'}")
            
            if results["errors"]:
                print("\n❌ ERRORS:")
                for err in results["errors"]:
                    print(f"   - {err}")
            
        except Exception as e:
            print(f"❌ Test error: {e}")
            results["errors"].append(str(e))
        finally:
            await browser.close()
    
    return results

if __name__ == "__main__":
    asyncio.run(test_market_forecast())

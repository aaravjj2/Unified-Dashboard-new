"""
Phase 8: Full Headed Playwright Smoke Test
Agent-1B - Comprehensive validation across all major tabs
"""
import asyncio
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright

# Tab configurations to test
TABS_TO_TEST = [
    {'id': 'home_lab', 'name': 'Command Center', 'selectors': ['#tab-home_lab']},
    {'id': 'market_trends', 'name': 'Market Trends', 'selectors': ['#tab-market_trends']},
    {'id': 'market_forecast', 'name': 'Market Forecast', 'selectors': ['#tab-market_forecast']},
    {'id': 'volatility_lab', 'name': 'Volatility Lab', 'selectors': ['#tab-volatility_lab']},
    {'id': 'portfolio', 'name': 'Portfolio', 'selectors': ['#tab-portfolio']},
]

async def test_full_smoke():
    """Run headed smoke test across all major tabs"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "test": "full_smoke_phase8",
        "tabs_tested": [],
        "overall_verdict": "PASS",
        "artifacts": []
    }
    
    base_url = "http://localhost:8050"
    screenshot_dir = "reports/agent1b/screenshots/smoke"
    os.makedirs(screenshot_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_har_path="reports/agent1b/playwright/full_smoke.har"
        )
        page = await context.new_page()
        
        all_console_logs = []
        page.on("console", lambda msg: all_console_logs.append({
            "type": msg.type,
            "text": msg.text
        }))
        
        try:
            # Navigate
            print("🚀 Starting Full Smoke Test")
            print(f"🌐 Navigating to {base_url}")
            await page.goto(base_url, wait_until="networkidle", timeout=30000)
            await page.screenshot(path=f"{screenshot_dir}/00_initial_load.png")
            results["artifacts"].append(f"{screenshot_dir}/00_initial_load.png")
            
            # Test each tab
            for idx, tab_config in enumerate(TABS_TO_TEST, 1):
                tab_result = {
                    "tab_id": tab_config['id'],
                    "tab_name": tab_config['name'],
                    "verdict": "PENDING"
                }
                
                try:
                    print(f"\n📑 [{idx}/{len(TABS_TO_TEST)}] Testing {tab_config['name']}...")
                    
                    # Click tab
                    clicked = False
                    for selector in tab_config['selectors']:
                        try:
                            await page.click(selector, timeout=5000)
                            clicked = True
                            print(f"  ✅ Opened tab using: {selector}")
                            break
                        except:
                            continue
                    
                    if not clicked:
                        tab_result["verdict"] = "FAIL - Could not click tab"
                        results["overall_verdict"] = "FAIL"
                        results["tabs_tested"].append(tab_result)
                        continue
                    
                    # Wait for content to load
                    await page.wait_for_timeout(2000)
                    
                    # Take screenshot
                    screenshot_path = f"{screenshot_dir}/{idx:02d}_{tab_config['id']}.png"
                    await page.screenshot(path=screenshot_path)
                    results["artifacts"].append(screenshot_path)
                    
                    # Check for any visible content
                    has_content = await page.query_selector('h1, h2, h3, h4, h5, table, canvas, .plotly')
                    if has_content:
                        tab_result["verdict"] = "PASS - Content loaded"
                        print(f"  ✅ Content verified")
                    else:
                        tab_result["verdict"] = "FAIL - No visible content"
                        results["overall_verdict"] = "FAIL"
                        print(f"  ❌ No content detected")
                    
                except Exception as e:
                    tab_result["verdict"] = f"FAIL - {str(e)}"
                    results["overall_verdict"] = "FAIL"
                    print(f"  ❌ Error: {e}")
                
                results["tabs_tested"].append(tab_result)
            
            # Final screenshot
            await page.screenshot(path=f"{screenshot_dir}/99_final.png")
            results["artifacts"].append(f"{screenshot_dir}/99_final.png")
            
            # Save console logs
            with open("reports/agent1b/playwright/full_smoke_console.json", "w") as f:
                json.dump(all_console_logs, f, indent=2)
            results["artifacts"].append("reports/agent1b/playwright/full_smoke_console.json")
            
        except Exception as e:
            print(f"❌ Critical Error: {e}")
            results["overall_verdict"] = f"FAIL - {str(e)}"
            await page.screenshot(path=f"{screenshot_dir}/error.png")
            results["artifacts"].append(f"{screenshot_dir}/error.png")
        
        finally:
            await context.close()
            await browser.close()
    
    # Save results
    with open("reports/agent1b/playwright/full_smoke_result.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "="*70)
    print("FULL SMOKE TEST SUMMARY")
    print("="*70)
    print(f"Overall Verdict: {results['overall_verdict']}")
    print(f"Tabs Tested: {len(results['tabs_tested'])}/{len(TABS_TO_TEST)}")
    print("-"*70)
    for tab_result in results["tabs_tested"]:
        status = "✅" if "PASS" in tab_result["verdict"] else "❌"
        print(f"{status} {tab_result['tab_name']}: {tab_result['verdict']}")
    print("="*70)
    print(f"Screenshots: {len([a for a in results['artifacts'] if '.png' in a])}")
    print(f"HAR file: reports/agent1b/playwright/full_smoke.har")
    print(f"Console logs: reports/agent1b/playwright/full_smoke_console.json")
    print("="*70)
    
    return results

if __name__ == "__main__":
    asyncio.run(test_full_smoke())

"""
Phase 7: Command Center (Home Lab) Headed Validation
Agent-1B - Verify Command Center tab loads and displays dashboard overview
"""
import asyncio
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright

async def test_command_center():
    """Test Command Center (home_lab) tab with headed browser"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "test": "command_center_phase7",
        "verdicts": {},
        "artifacts": []
    }
    
    base_url = "http://localhost:8050"
    screenshot_dir = "reports/agent1b/screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_har_path="reports/agent1b/playwright/command_center.har"
        )
        page = await context.new_page()
        
        console_logs = []
        page.on("console", lambda msg: console_logs.append({
            "type": msg.type,
            "text": msg.text
        }))
        
        try:
            # Navigate
            print(f"🌐 Navigating to {base_url}")
            await page.goto(base_url, wait_until="networkidle", timeout=30000)
            results["verdicts"]["page_load"] = "PASS"
            
            # Click Command Center tab
            print("🏠 Opening Command Center tab")
            tab_selectors = [
                '#tab-home_lab',
                'button#tab-home_lab',
                'button.nav-link:has-text("Command")',
                'button.nav-link:has-text("Home")',
            ]
            
            clicked = False
            for selector in tab_selectors:
                try:
                    await page.click(selector, timeout=5000)
                    clicked = True
                    print(f"✅ Clicked tab using: {selector}")
                    break
                except:
                    continue
            
            if not clicked:
                raise Exception("Could not find Command Center tab")
            
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f"{screenshot_dir}/cc_01_opened.png")
            results["artifacts"].append(f"{screenshot_dir}/cc_01_opened.png")
            results["verdicts"]["tab_switch"] = "PASS"
            
            # Check for dashboard elements
            dashboard_found = await page.query_selector('[class*="dashboard"], h2, h3, h4')
            results["verdicts"]["dashboard_content"] = "PASS" if dashboard_found else "FAIL - not found"
            
            # Check for metrics/cards
            cards_found = await page.query_selector('[class*="card"], [class*="metric"]')
            results["verdicts"]["metrics_cards"] = "PASS" if cards_found else "FAIL - not found"
            
            # Check for any interactive elements
            interactive_found = await page.query_selector('button, input, select, .dash-dropdown')
            results["verdicts"]["interactive_elements"] = "PASS" if interactive_found else "FAIL - not found"
            
            # Final screenshot
            await page.screenshot(path=f"{screenshot_dir}/cc_02_final.png")
            results["artifacts"].append(f"{screenshot_dir}/cc_02_final.png")
            
            # Save DOM
            dom_content = await page.content()
            with open("reports/agent1b/dom/command_center.html", "w") as f:
                f.write(dom_content)
            results["artifacts"].append("reports/agent1b/dom/command_center.html")
            
            # Save console logs
            with open("reports/agent1b/playwright/command_center_console.json", "w") as f:
                json.dump(console_logs, f, indent=2)
            results["artifacts"].append("reports/agent1b/playwright/command_center_console.json")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results["verdicts"]["overall"] = f"FAIL - {str(e)}"
            await page.screenshot(path=f"{screenshot_dir}/cc_error.png")
            results["artifacts"].append(f"{screenshot_dir}/cc_error.png")
        
        finally:
            await context.close()
            await browser.close()
    
    # Save results
    with open("reports/agent1b/playwright/command_center_result.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("COMMAND CENTER TEST SUMMARY")
    print("="*60)
    for key, verdict in results["verdicts"].items():
        status = "✅" if "PASS" in verdict else "❌"
        print(f"{status} {key}: {verdict}")
    print("="*60)
    
    return results

if __name__ == "__main__":
    asyncio.run(test_command_center())

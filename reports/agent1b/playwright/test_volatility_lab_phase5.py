"""
Phase 5: Volatility Lab Headed Validation
Agent-1B - Verify Volatility Lab tab structure and functionality
"""
import asyncio
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright

async def test_volatility_lab():
    """Test Volatility Lab tab with headed browser"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "test": "volatility_lab_phase5",
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
            record_har_path="reports/agent1b/playwright/volatility_lab.har"
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
            
            # Click Volatility Lab tab
            print("📉 Opening Volatility Lab tab")
            tab_selectors = [
                '#tab-volatility_lab',
                'button#tab-volatility_lab',
                'button.nav-link:has-text("Volatility")',
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
                raise Exception("Could not find Volatility Lab tab")
            
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f"{screenshot_dir}/vol_01_opened.png")
            results["artifacts"].append(f"{screenshot_dir}/vol_01_opened.png")
            results["verdicts"]["tab_switch"] = "PASS"
            
            # Check for controls/inputs (common volatility lab elements)
            ticker_input = await page.query_selector('#vol-ticker-input, #vl-ticker-input, input[placeholder*="ticker"]')
            if ticker_input:
                results["verdicts"]["ticker_input"] = "PASS"
                print("✅ Ticker input found")
            else:
                results["verdicts"]["ticker_input"] = "FAIL - not found"
            
            # Check for compute/run button
            run_btn_selectors = ['#vol-compute-btn', '#vl-run-btn', '#vol-run-btn', 'button:has-text("Compute")', 'button:has-text("Calculate")']
            run_btn_found = False
            for selector in run_btn_selectors:
                btn = await page.query_selector(selector)
                if btn:
                    run_btn_found = True
                    print(f"✅ Run button found: {selector}")
                    break
            
            results["verdicts"]["run_button"] = "PASS" if run_btn_found else "FAIL - not found"
            
            # Check for results/chart area
            chart_selectors = ['#vol-chart', '#vl-chart', '#volatility-chart', '[id*="vol"][id*="chart"]']
            chart_found = False
            for selector in chart_selectors:
                chart = await page.query_selector(selector)
                if chart:
                    chart_found = True
                    print(f"✅ Chart found: {selector}")
                    break
            
            results["verdicts"]["chart_area"] = "PASS" if chart_found else "FAIL - not found"
            
            # Check for any data table
            table = await page.query_selector('table, [id*="vol"][id*="table"], .dash-table')
            if table:
                results["verdicts"]["data_table"] = "PASS"
                print("✅ Data table found")
            else:
                results["verdicts"]["data_table"] = "FAIL - not found"
            
            # Final screenshot
            await page.screenshot(path=f"{screenshot_dir}/vol_02_final.png")
            results["artifacts"].append(f"{screenshot_dir}/vol_02_final.png")
            
            # Save DOM
            dom_content = await page.content()
            with open("reports/agent1b/dom/volatility_lab.html", "w") as f:
                f.write(dom_content)
            results["artifacts"].append("reports/agent1b/dom/volatility_lab.html")
            
            # Save console logs
            with open("reports/agent1b/playwright/volatility_lab_console.json", "w") as f:
                json.dump(console_logs, f, indent=2)
            results["artifacts"].append("reports/agent1b/playwright/volatility_lab_console.json")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results["verdicts"]["overall"] = f"FAIL - {str(e)}"
            await page.screenshot(path=f"{screenshot_dir}/vol_error.png")
            results["artifacts"].append(f"{screenshot_dir}/vol_error.png")
        
        finally:
            await context.close()
            await browser.close()
    
    # Save results
    with open("reports/agent1b/playwright/volatility_lab_result.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("VOLATILITY LAB TEST SUMMARY")
    print("="*60)
    for key, verdict in results["verdicts"].items():
        status = "✅" if "PASS" in verdict else "❌"
        print(f"{status} {key}: {verdict}")
    print("="*60)
    
    return results

if __name__ == "__main__":
    asyncio.run(test_volatility_lab())

"""
Phase 6: Portfolio Headed Validation
Agent-1B - Verify Portfolio tab loads and displays key elements
"""
import asyncio
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright

async def test_portfolio():
    """Test Portfolio tab with headed browser"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "test": "portfolio_phase6",
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
            record_har_path="reports/agent1b/playwright/portfolio.har"
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
            
            # Click Portfolio tab
            print("💼 Opening Portfolio tab")
            tab_selectors = [
                '#tab-portfolio',
                'button#tab-portfolio',
                'button.nav-link:has-text("Portfolio")',
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
                raise Exception("Could not find Portfolio tab")
            
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f"{screenshot_dir}/portfolio_01_opened.png")
            results["artifacts"].append(f"{screenshot_dir}/portfolio_01_opened.png")
            results["verdicts"]["tab_switch"] = "PASS"
            
            # Check for positions/holdings section
            positions_found = False
            positions_selectors = ['#pa-positions', '#portfolio-positions', '[id*="position"]', 'h4:has-text("Positions")', 'h5:has-text("Holdings")']
            for selector in positions_selectors:
                elem = await page.query_selector(selector)
                if elem:
                    positions_found = True
                    print(f"✅ Positions section found: {selector}")
                    break
            
            results["verdicts"]["positions_section"] = "PASS" if positions_found else "FAIL - not found"
            
            # Check for summary metrics
            metrics_found = await page.query_selector('[class*="metric"], [class*="summary"], h4, h5')
            results["verdicts"]["metrics_display"] = "PASS" if metrics_found else "FAIL - not found"
            
            # Check for any table or chart
            table_or_chart = await page.query_selector('table, .dash-table, [id*="chart"], [id*="graph"]')
            results["verdicts"]["data_display"] = "PASS" if table_or_chart else "FAIL - not found"
            
            # Final screenshot
            await page.screenshot(path=f"{screenshot_dir}/portfolio_02_final.png")
            results["artifacts"].append(f"{screenshot_dir}/portfolio_02_final.png")
            
            # Save DOM
            dom_content = await page.content()
            with open("reports/agent1b/dom/portfolio.html", "w") as f:
                f.write(dom_content)
            results["artifacts"].append("reports/agent1b/dom/portfolio.html")
            
            # Save console logs
            with open("reports/agent1b/playwright/portfolio_console.json", "w") as f:
                json.dump(console_logs, f, indent=2)
            results["artifacts"].append("reports/agent1b/playwright/portfolio_console.json")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results["verdicts"]["overall"] = f"FAIL - {str(e)}"
            await page.screenshot(path=f"{screenshot_dir}/portfolio_error.png")
            results["artifacts"].append(f"{screenshot_dir}/portfolio_error.png")
        
        finally:
            await context.close()
            await browser.close()
    
    # Save results
    with open("reports/agent1b/playwright/portfolio_result.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("PORTFOLIO TEST SUMMARY")
    print("="*60)
    for key, verdict in results["verdicts"].items():
        status = "✅" if "PASS" in verdict else "❌"
        print(f"{status} {key}: {verdict}")
    print("="*60)
    
    return results

if __name__ == "__main__":
    asyncio.run(test_portfolio())

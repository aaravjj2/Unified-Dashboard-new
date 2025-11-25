"""
Phase 3: Market Trends Headed Validation
Agent-1B - Headed Chromium test for Market Trends tab
"""
import asyncio
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright

async def test_market_trends():
    """Test Market Trends tab with headed browser"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "test": "market_trends_phase3",
        "verdicts": {},
        "artifacts": []
    }
    
    base_url = "http://localhost:8050"
    screenshot_dir = "reports/agent1b/screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)
    
    async with async_playwright() as p:
        # Launch headed Chromium
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_har_path="reports/agent1b/playwright/market_trends.har"
        )
        page = await context.new_page()
        
        # Enable console logging
        console_logs = []
        page.on("console", lambda msg: console_logs.append({
            "type": msg.type,
            "text": msg.text
        }))
        
        try:
            # Navigate to dashboard
            print(f"🌐 Navigating to {base_url}")
            await page.goto(base_url, wait_until="networkidle", timeout=30000)
            await page.screenshot(path=f"{screenshot_dir}/mt_01_home.png")
            results["artifacts"].append(f"{screenshot_dir}/mt_01_home.png")
            results["verdicts"]["page_load"] = "PASS"
            
            # Click Market Trends tab (using dbc.Tab structure: tab-{tab_key})
            print("📊 Opening Market Trends tab")
            # Try multiple selectors to find the Market Trends tab link
            tab_selectors = [
                '#tab-market_trends',  # Direct ID
                'button#tab-market_trends',  # Bootstrap tab button
                'a.nav-link[href*="market"]',  # Nav link with "market" in href
                'button.nav-link:has-text("Market Trends")',  # Button with text
            ]
            
            clicked = False
            for selector in tab_selectors:
                try:
                    await page.click(selector, timeout=5000)
                    clicked = True
                    print(f"✅ Clicked tab using selector: {selector}")
                    break
                except:
                    continue
            
            if not clicked:
                # Fallback: list all tabs for debugging
                tabs_html = await page.locator('[id^="tab-"]').all()
                print(f"⚠️ Available tabs: {len(tabs_html)} found")
                raise Exception("Could not find Market Trends tab with any selector")
            
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f"{screenshot_dir}/mt_02_tab_opened.png")
            results["artifacts"].append(f"{screenshot_dir}/mt_02_tab_opened.png")
            results["verdicts"]["tab_switch"] = "PASS"
            
            # Check if Run Analysis button exists
            run_btn = await page.query_selector('#run-btn')
            if run_btn:
                print("✅ Run Analysis button found")
                results["verdicts"]["run_btn_exists"] = "PASS"
                
                # Click Run Analysis
                print("🔄 Clicking Run Analysis...")
                await page.click('#run-btn')
                await page.wait_for_timeout(3000)
                await page.screenshot(path=f"{screenshot_dir}/mt_03_after_run.png")
                results["artifacts"].append(f"{screenshot_dir}/mt_03_after_run.png")
                results["verdicts"]["run_analysis_click"] = "PASS"
            else:
                print("❌ Run Analysis button NOT found")
                results["verdicts"]["run_btn_exists"] = "FAIL - button not in DOM"
            
            # Check for news container
            news_container = await page.query_selector('#news-container')
            if news_container:
                news_visible = await news_container.is_visible()
                results["verdicts"]["news_container"] = "PASS" if news_visible else "FAIL - not visible"
                print(f"📰 News container: {'visible' if news_visible else 'hidden'}")
            else:
                results["verdicts"]["news_container"] = "FAIL - not in DOM"
            
            # Check for results area
            results_area = await page.query_selector('#results-area')
            if results_area:
                results["verdicts"]["results_area"] = "PASS"
                print("📈 Results area found")
            else:
                results["verdicts"]["results_area"] = "FAIL - not in DOM"
            
            # Save final screenshot
            await page.screenshot(path=f"{screenshot_dir}/mt_04_final.png")
            results["artifacts"].append(f"{screenshot_dir}/mt_04_final.png")
            
            # Save DOM snapshot
            dom_content = await page.content()
            with open("reports/agent1b/dom/market_trends.html", "w") as f:
                f.write(dom_content)
            results["artifacts"].append("reports/agent1b/dom/market_trends.html")
            
            # Save console logs
            with open("reports/agent1b/playwright/market_trends_console.json", "w") as f:
                json.dump(console_logs, f, indent=2)
            results["artifacts"].append("reports/agent1b/playwright/market_trends_console.json")
            
        except Exception as e:
            print(f"❌ Error during test: {e}")
            results["verdicts"]["overall"] = f"FAIL - {str(e)}"
            await page.screenshot(path=f"{screenshot_dir}/mt_error.png")
            results["artifacts"].append(f"{screenshot_dir}/mt_error.png")
        
        finally:
            await context.close()
            await browser.close()
    
    # Save test results
    with open("reports/agent1b/playwright/market_trends_result.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("MARKET TRENDS TEST SUMMARY")
    print("="*60)
    for key, verdict in results["verdicts"].items():
        status = "✅" if "PASS" in verdict else "❌"
        print(f"{status} {key}: {verdict}")
    print("="*60)
    
    return results

if __name__ == "__main__":
    asyncio.run(test_market_trends())

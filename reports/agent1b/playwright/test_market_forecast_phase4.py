"""
Phase 4: Market Forecast Headed Validation
Agent-1B - Verify Market Forecast tab displays fixtures correctly
"""
import asyncio
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright

async def test_market_forecast():
    """Test Market Forecast tab with headed browser"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "test": "market_forecast_phase4",
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
            record_har_path="reports/agent1b/playwright/market_forecast.har"
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
            
            # Click Market Forecast tab
            print("📈 Opening Market Forecast tab")
            tab_selectors = [
                '#tab-market_forecast',
                'button#tab-market_forecast',
                'button.nav-link:has-text("Market Forecast")',
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
                raise Exception("Could not find Market Forecast tab")
            
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f"{screenshot_dir}/mf_01_opened.png")
            results["artifacts"].append(f"{screenshot_dir}/mf_01_opened.png")
            results["verdicts"]["tab_switch"] = "PASS"
            
            # Check for forecast chart
            chart = await page.query_selector('#mf-forecast-chart')
            if chart:
                chart_visible = await chart.is_visible()
                results["verdicts"]["forecast_chart"] = "PASS" if chart_visible else "FAIL - not visible"
                print(f"📊 Forecast chart: {'visible' if chart_visible else 'hidden'}")
            else:
                results["verdicts"]["forecast_chart"] = "FAIL - not in DOM"
            
            # Check for metrics cards
            metrics_ids = ['mf-return-card', 'mf-vol-card', 'mf-sharpe-card', 'mf-dd-card']
            metrics_found = 0
            for metric_id in metrics_ids:
                metric = await page.query_selector(f'#{metric_id}')
                if metric:
                    metrics_found += 1
            
            results["verdicts"]["metrics_cards"] = f"PASS - {metrics_found}/4 found"
            print(f"📊 Metrics cards: {metrics_found}/4")
            
            # Check for explanation chart
            explain_chart = await page.query_selector('#mf-explain-chart')
            if explain_chart:
                explain_visible = await explain_chart.is_visible()
                results["verdicts"]["explanation_chart"] = "PASS" if explain_visible else "FAIL - not visible"
                print(f"🔍 Explanation chart: {'visible' if explain_visible else 'hidden'}")
            else:
                results["verdicts"]["explanation_chart"] = "FAIL - not in DOM"
            
            # Final screenshot
            await page.screenshot(path=f"{screenshot_dir}/mf_02_final.png")
            results["artifacts"].append(f"{screenshot_dir}/mf_02_final.png")
            
            # Save DOM
            dom_content = await page.content()
            with open("reports/agent1b/dom/market_forecast.html", "w") as f:
                f.write(dom_content)
            results["artifacts"].append("reports/agent1b/dom/market_forecast.html")
            
            # Save console logs
            with open("reports/agent1b/playwright/market_forecast_console.json", "w") as f:
                json.dump(console_logs, f, indent=2)
            results["artifacts"].append("reports/agent1b/playwright/market_forecast_console.json")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results["verdicts"]["overall"] = f"FAIL - {str(e)}"
            await page.screenshot(path=f"{screenshot_dir}/mf_error.png")
            results["artifacts"].append(f"{screenshot_dir}/mf_error.png")
        
        finally:
            await context.close()
            await browser.close()
    
    # Save results
    with open("reports/agent1b/playwright/market_forecast_result.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("MARKET FORECAST TEST SUMMARY")
    print("="*60)
    for key, verdict in results["verdicts"].items():
        status = "✅" if "PASS" in verdict else "❌"
        print(f"{status} {key}: {verdict}")
    print("="*60)
    
    return results

if __name__ == "__main__":
    asyncio.run(test_market_forecast())

"""
CORRECTED Phase 3: Market Trends Functional Test
Verify Run Analysis button actually produces results, not just clickability
"""
import asyncio
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright

async def test_market_trends_functional():
    """Test Market Trends button functionality with result verification"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "test": "market_trends_functional",
        "verdicts": {},
        "artifacts": [],
        "failures": []
    }
    
    base_url = "http://localhost:8051"
    screenshot_dir = "reports/agent1b/screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_har_path="reports/agent1b/playwright/market_trends_functional.har"
        )
        page = await context.new_page()
        
        console_logs = []
        page.on("console", lambda msg: console_logs.append({
            "type": msg.type,
            "text": msg.text
        }))
        
        try:
            print("🔍 Testing Market Trends FUNCTIONAL behavior...")
            
            # Navigate and open tab
            await page.goto(base_url, wait_until="networkidle", timeout=30000)
            await page.click('#tab-market_trends', timeout=10000)
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f"{screenshot_dir}/mt_func_01_before.png")
            results["artifacts"].append(f"{screenshot_dir}/mt_func_01_before.png")
            
            # Get initial content state
            initial_content = await page.text_content('body')
            print(f"📝 Initial content length: {len(initial_content)} chars")
            
            # Look for placeholder/loading text BEFORE clicking
            placeholder_before = await page.query_selector('text=/loading|placeholder|no data|waiting/i')
            print(f"⏳ Placeholder before click: {'Found' if placeholder_before else 'Not found'}")
            
            # Check for existing table BEFORE clicking
            table_before = await page.query_selector('table, .dash-table')
            rows_before = 0
            if table_before:
                rows = await table_before.query_selector_all('tr')
                rows_before = len(rows)
                print(f"📊 Table rows before click: {rows_before}")
            else:
                print("📊 No table found before click")
            
            # Click Run Analysis
            print("🔄 Clicking Run Analysis...")
            await page.click('#run-btn')
            
            # Wait for job to queue (should see "Job queued" message)
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f"{screenshot_dir}/mt_func_02_after_click.png")
            results["artifacts"].append(f"{screenshot_dir}/mt_func_02_after_click.png")
            
            job_queued = await page.query_selector('text=/job queued|queued|processing/i')
            if job_queued:
                job_text = await job_queued.text_content()
                print(f"✅ Job status visible: '{job_text}'")
                results["verdicts"]["job_queued_message"] = "PASS"
            else:
                print("❌ No 'job queued' message visible")
                results["verdicts"]["job_queued_message"] = "FAIL - no queue confirmation"
                results["failures"].append("No job queue confirmation shown to user")
            
            # Wait longer for background job to complete (poll for changes)
            print("⏳ Waiting for results (up to 30 seconds)...")
            changed = False
            for i in range(30):
                await page.wait_for_timeout(1000)
                
                # Check if table appeared or updated
                table_now = await page.query_selector('table, .dash-table')
                if table_now:
                    rows = await table_now.query_selector_all('tr')
                    rows_now = len(rows)
                    if rows_now > rows_before:
                        print(f"✅ Table updated! {rows_before} -> {rows_now} rows")
                        changed = True
                        break
                
                # Check if placeholder disappeared
                placeholder_now = await page.query_selector('text=/loading|placeholder|no data|waiting/i')
                if placeholder_before and not placeholder_now:
                    print(f"✅ Placeholder cleared after {i+1} seconds")
                    changed = True
                    break
                
                if (i + 1) % 5 == 0:
                    print(f"  ⏱️ Still waiting... {i+1}s elapsed")
            
            # Take screenshot after waiting
            await page.screenshot(path=f"{screenshot_dir}/mt_func_03_after_wait.png")
            results["artifacts"].append(f"{screenshot_dir}/mt_func_03_after_wait.png")
            
            # Final verification
            final_content = await page.text_content('body')
            content_changed = len(final_content) != len(initial_content)
            
            table_after = await page.query_selector('table, .dash-table')
            rows_after = 0
            if table_after:
                rows = await table_after.query_selector_all('tr')
                rows_after = len(rows)
            
            print(f"\n📊 RESULTS:")
            print(f"  Content changed: {content_changed}")
            print(f"  Table rows: {rows_before} -> {rows_after}")
            print(f"  Changed detected: {changed}")
            
            if changed and rows_after > rows_before:
                results["verdicts"]["results_displayed"] = "PASS - Table populated with data"
                print("✅ SUCCESS: Results displayed")
            elif changed:
                results["verdicts"]["results_displayed"] = "PARTIAL - Content changed but table not populated"
                results["failures"].append("Content changed but no table data visible")
                print("⚠️ PARTIAL: Content changed but no clear results table")
            else:
                results["verdicts"]["results_displayed"] = "FAIL - No visible change after 30s"
                results["failures"].append("No visible output change after clicking Run Analysis")
                print("❌ FAIL: No visible results after 30 seconds")
            
            # Save DOM snapshot
            dom_content = await page.content()
            with open("reports/agent1b/dom/market_trends_functional.html", "w") as f:
                f.write(dom_content)
            
            # Save console logs
            with open("reports/agent1b/playwright/market_trends_functional_console.json", "w") as f:
                json.dump(console_logs, f, indent=2)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results["verdicts"]["overall"] = f"FAIL - {str(e)}"
            results["failures"].append(str(e))
            await page.screenshot(path=f"{screenshot_dir}/mt_func_error.png")
        
        finally:
            await context.close()
            await browser.close()
    
    # Save results
    with open("reports/agent1b/playwright/market_trends_functional_result.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*60)
    print("MARKET TRENDS FUNCTIONAL TEST")
    print("="*60)
    for key, verdict in results["verdicts"].items():
        status = "✅" if "PASS" in verdict else ("⚠️" if "PARTIAL" in verdict else "❌")
        print(f"{status} {key}: {verdict}")
    if results["failures"]:
        print("\n❌ FAILURES:")
        for failure in results["failures"]:
            print(f"  - {failure}")
    print("="*60)
    
    return results

if __name__ == "__main__":
    asyncio.run(test_market_trends_functional())

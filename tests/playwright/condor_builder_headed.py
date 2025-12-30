"""
Playwright Headful Audit - Iron Condor Strategy Builder
Phase 3: Strategy Implementation

Tests:
1. Navigate to Strategy Builder tab
2. Input ticker value
3. Select expiry dropdown
4. Adjust width slider
5. Enter contracts
6. Click calculate button
7. Verify payoff chart renders
8. Logic Check: Verify widening slider increases Max Loss
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, expect

# Setup paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports" / "phase3_strat"
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"
DOM_DIR = REPORTS_DIR / "dom"
LOGS_DIR = REPORTS_DIR / "logs"

# Create directories
for dir_path in [SCREENSHOTS_DIR, DOM_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Test configuration
BASE_URL = "http://localhost:8051"
TIMEOUT = 30000  # 30 seconds

class PlaywrightAudit:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "base_url": BASE_URL,
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0
            }
        }
        self.har_path = REPORTS_DIR / "playwright" / "full_audit.har"
        self.har_path.parent.mkdir(parents=True, exist_ok=True)
    
    def log_test(self, test_name, status, details="", error=None):
        """Log a test result"""
        result = {
            "name": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        if error:
            result["error"] = str(error)
        
        self.results["tests"].append(result)
        self.results["summary"]["total"] += 1
        self.results["summary"][status.lower()] += 1
        
        status_icon = "✅" if status == "PASSED" else "❌" if status == "FAILED" else "⏭️"
        print(f"{status_icon} {test_name}: {status}")
        if details:
            print(f"   {details}")
        if error:
            print(f"   Error: {error}")
    
    async def capture_element_state(self, page, element_id, action_name):
        """Capture screenshot and DOM for an element"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Screenshot
            screenshot_path = SCREENSHOTS_DIR / f"{element_id}_{action_name}_{timestamp}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            
            # DOM snapshot
            dom_content = await page.content()
            dom_path = DOM_DIR / f"{element_id}_{action_name}_{timestamp}.html"
            with open(dom_path, 'w', encoding='utf-8') as f:
                f.write(dom_content)
            
            # Console logs
            return True
        except Exception as e:
            print(f"   ⚠️ Failed to capture state for {element_id}: {e}")
            return False
    
    async def run_audit(self):
        """Run the complete Playwright audit"""
        print("=" * 80)
        print("🎭 PLAYWRIGHT HEADFUL AUDIT - STRATEGY BUILDER")
        print("=" * 80)
        
        async with async_playwright() as p:
            # Launch browser in HEADFUL mode
            print("\n🌐 Launching Chromium (headful mode)...")
            browser = await p.chromium.launch(
                headless=False,
                slow_mo=500  # Slow down for visibility
            )
            
            # Create context with HAR recording
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                record_har_path=str(self.har_path)
            )
            
            page = await context.new_page()
            
            # Console log capture
            console_logs = []
            page.on("console", lambda msg: console_logs.append({
                "type": msg.type,
                "text": msg.text,
                "timestamp": datetime.now().isoformat()
            }))
            
            try:
                # TEST 1: Navigate to dashboard
                print("\n📍 TEST 1: Navigate to dashboard...")
                await page.goto(BASE_URL, timeout=TIMEOUT, wait_until="networkidle")
                await asyncio.sleep(2)
                self.log_test("Navigate to Dashboard", "PASSED", f"Loaded {BASE_URL}")
                
                # TEST 2: Find and click Strategy Builder tab
                print("\n📍 TEST 2: Navigate to Strategy Builder tab...")
                await self.capture_element_state(page, "dashboard", "pre_tab_click")
                
                try:
                    # Try multiple selectors for the tab
                    tab_clicked = False
                    tab_selectors = [
                        "text=🦅 Strategy Builder",
                        "text=Strategy Builder",
                        "[tab-id='strategy_builder']",
                        "#tab-strategy_builder"
                    ]
                    
                    for selector in tab_selectors:
                        try:
                            await page.click(selector, timeout=5000)
                            tab_clicked = True
                            print(f"   ✓ Clicked tab using selector: {selector}")
                            break
                        except:
                            continue
                    
                    if tab_clicked:
                        await asyncio.sleep(2)
                        await self.capture_element_state(page, "dashboard", "post_tab_click")
                        self.log_test("Navigate to Strategy Builder Tab", "PASSED", "Tab clicked successfully")
                    else:
                        self.log_test("Navigate to Strategy Builder Tab", "FAILED", "Could not find tab")
                        raise Exception("Tab not found")
                
                except Exception as e:
                    self.log_test("Navigate to Strategy Builder Tab", "FAILED", error=e)
                    raise
                
                # TEST 3: Input ticker
                print("\n📍 TEST 3: Test ticker input...")
                await self.capture_element_state(page, "input-ticker", "pre_input")
                
                try:
                    await page.wait_for_selector("#input-ticker", timeout=TIMEOUT)
                    await page.fill("#input-ticker", "SPY")
                    await asyncio.sleep(1)
                    await self.capture_element_state(page, "input-ticker", "post_input")
                    
                    # Verify value
                    value = await page.input_value("#input-ticker")
                    assert value == "SPY", f"Expected 'SPY', got '{value}'"
                    self.log_test("Input Ticker", "PASSED", "Ticker set to SPY")
                except Exception as e:
                    self.log_test("Input Ticker", "FAILED", error=e)
                
                # TEST 4: Select expiry dropdown
                print("\n📍 TEST 4: Test expiry dropdown...")
                await self.capture_element_state(page, "dropdown-expiry", "pre_select")
                
                try:
                    await page.wait_for_selector("#dropdown-expiry", timeout=TIMEOUT)
                    # Click the dropdown
                    await page.click("#dropdown-expiry")
                    await asyncio.sleep(1)
                    # Select first option
                    await page.click("#dropdown-expiry .Select-option:first-child", timeout=5000)
                    await asyncio.sleep(1)
                    await self.capture_element_state(page, "dropdown-expiry", "post_select")
                    self.log_test("Select Expiry", "PASSED", "Expiry selected")
                except Exception as e:
                    self.log_test("Select Expiry", "FAILED", error=e)
                
                # TEST 5: Adjust width slider - CRITICAL TEST
                print("\n📍 TEST 5: Test width slider (CRITICAL LOGIC CHECK)...")
                await self.capture_element_state(page, "slider-width", "pre_adjust")
                
                try:
                    # Get initial Max Loss value
                    await page.wait_for_selector("#display-max-loss", timeout=TIMEOUT)
                    initial_max_loss_text = await page.text_content("#display-max-loss")
                    initial_max_loss = float(initial_max_loss_text.replace("$", "").replace(",", ""))
                    print(f"   Initial Max Loss: ${initial_max_loss:.2f}")
                    
                    # Move slider to increase width
                    slider = await page.query_selector("#slider-width input")
                    if slider:
                        # Get current value
                        current_value = await slider.get_attribute("value")
                        print(f"   Current slider value: {current_value}")
                        
                        # Set to higher value
                        await slider.fill("30")
                        await asyncio.sleep(2)
                        
                        # Trigger calculate
                        await page.click("#btn-calculate-strategy")
                        await asyncio.sleep(2)
                        
                        await self.capture_element_state(page, "slider-width", "post_adjust")
                        
                        # Get new Max Loss value
                        new_max_loss_text = await page.text_content("#display-max-loss")
                        new_max_loss = float(new_max_loss_text.replace("$", "").replace(",", ""))
                        print(f"   New Max Loss: ${new_max_loss:.2f}")
                        
                        # LOGIC CHECK: Max Loss should increase with width
                        if new_max_loss > initial_max_loss:
                            self.log_test("Width Slider Logic", "PASSED", 
                                        f"Max Loss increased from ${initial_max_loss:.2f} to ${new_max_loss:.2f}")
                        else:
                            self.log_test("Width Slider Logic", "FAILED", 
                                        f"Max Loss did not increase: ${initial_max_loss:.2f} -> ${new_max_loss:.2f}")
                    else:
                        raise Exception("Slider not found")
                        
                except Exception as e:
                    self.log_test("Width Slider Logic", "FAILED", error=e)
                
                # TEST 6: Enter contracts
                print("\n📍 TEST 6: Test contracts input...")
                await self.capture_element_state(page, "input-contracts", "pre_input")
                
                try:
                    await page.wait_for_selector("#input-contracts", timeout=TIMEOUT)
                    await page.fill("#input-contracts", "5")
                    await asyncio.sleep(1)
                    await self.capture_element_state(page, "input-contracts", "post_input")
                    
                    value = await page.input_value("#input-contracts")
                    assert value == "5", f"Expected '5', got '{value}'"
                    self.log_test("Input Contracts", "PASSED", "Contracts set to 5")
                except Exception as e:
                    self.log_test("Input Contracts", "FAILED", error=e)
                
                # TEST 7: Verify payoff graph
                print("\n📍 TEST 7: Verify payoff graph renders...")
                await self.capture_element_state(page, "graph-payoff", "pre_check")
                
                try:
                    await page.wait_for_selector("#graph-payoff", timeout=TIMEOUT)
                    # Check if graph has plotly content
                    graph_html = await page.inner_html("#graph-payoff")
                    has_plot = "plotly" in graph_html.lower() or "svg" in graph_html.lower()
                    
                    if has_plot:
                        await self.capture_element_state(page, "graph-payoff", "post_render")
                        self.log_test("Payoff Graph Render", "PASSED", "Graph rendered successfully")
                    else:
                        self.log_test("Payoff Graph Render", "FAILED", "Graph container empty")
                except Exception as e:
                    self.log_test("Payoff Graph Render", "FAILED", error=e)
                
                # Save console logs
                console_log_path = LOGS_DIR / "console_logs.json"
                with open(console_log_path, 'w') as f:
                    json.dump(console_logs, f, indent=2)
                
                # Check for console errors
                errors = [log for log in console_logs if log["type"] == "error"]
                if errors:
                    print(f"\n⚠️ Found {len(errors)} console errors")
                    self.log_test("Console Errors Check", "FAILED", 
                                f"Found {len(errors)} console errors")
                else:
                    print("\n✅ No console errors found")
                    self.log_test("Console Errors Check", "PASSED", "No console errors")
                
            except Exception as e:
                print(f"\n❌ Fatal error during audit: {e}")
                self.log_test("Fatal Error", "FAILED", error=e)
            
            finally:
                # Keep browser open for 5 seconds
                print("\n⏳ Keeping browser open for review (5 seconds)...")
                await asyncio.sleep(5)
                
                # Close
                await context.close()
                await browser.close()
        
        # Save results
        result_path = REPORTS_DIR / "playwright" / "full_audit_result.json"
        with open(result_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print("\n" + "=" * 80)
        print("📊 AUDIT SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {self.results['summary']['total']}")
        print(f"✅ Passed: {self.results['summary']['passed']}")
        print(f"❌ Failed: {self.results['summary']['failed']}")
        print(f"⏭️ Skipped: {self.results['summary']['skipped']}")
        print(f"\n📄 Results saved to: {result_path}")
        print(f"📸 Screenshots: {SCREENSHOTS_DIR}")
        print(f"🌐 HAR file: {self.har_path}")
        
        # Determine acceptance
        acceptance = (
            self.results['summary']['passed'] == self.results['summary']['total'] and
            self.results['summary']['skipped'] == 0
        )
        
        if acceptance:
            print("\n✅ ✅ ✅ ACCEPTANCE: ALL TESTS PASSED ✅ ✅ ✅")
            return 0
        else:
            print("\n❌ ❌ ❌ ACCEPTANCE: TESTS FAILED ❌ ❌ ❌")
            return 1

async def main():
    audit = PlaywrightAudit()
    exit_code = await audit.run_audit()
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())

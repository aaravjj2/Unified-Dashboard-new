#!/usr/bin/env python3
"""
Comprehensive Tab Testing with Non-Headless Chromium
Tests tabs in order: Research Lab → Market Forecast → Volatility → Market Trends → Portfolio
Only stops when all tests succeed.
"""
import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime
import sys

# Test configuration
DASHBOARD_URL = "http://localhost:8052"
TABS_TO_TEST = [
    {
        "name": "Research Lab",
        "tab_text": "🔬 Research Lab",
        "buttons": [
            # Note: Research Lab has no visible action buttons beyond global ones
        ],
        "expected_content": ["Brief", "Research", "Status"]
    },
    {
        "name": "Market Forecast",
        "tab_text": "Market Forecast",
        "buttons": [
            {"id": "mf-run-btn", "name": "Run Forecast"},
            {"id": "mf-forecast-download-btn", "name": "Download Forecast"},
            {"id": "mf-explain-download-btn", "name": "Download Explain"}
        ],
        "expected_content": ["Forecast", "Prediction", "Market"]
    },
    {
        "name": "Volatility Lab",
        "tab_text": "⚡ Volatility Lab",
        "buttons": [
            {"id": "vl-overview-refresh-btn", "name": "Refresh Overview"},
            {"id": "vl-compute-quick-btn", "name": "Quick Compute"}
        ],
        "expected_content": ["Volatility", "Surface", "IV"]
    },
    {
        "name": "Market Trends",
        "tab_text": "Market Trends",
        "buttons": [
            {"id": "run-btn", "name": "Run Full Analysis"},
            {"id": "reload-model", "name": "Reload Model"},
            {"id": "refresh-cached", "name": "Refresh Cached"},
            {"id": "backtest-btn", "name": "Backtest Signals"}
        ],
        "expected_content": ["Trends", "Analysis", "Market"]
    },
    {
        "name": "Portfolio",
        "tab_text": "Portfolio",
        "buttons": [
            {"id": "portfolio-refresh-btn", "name": "Refresh Portfolio"},
            {"id": "regen-shap-btn", "name": "Regenerate SHAP"},
            {"id": "portfolio-positions-refresh-btn", "name": "Refresh Positions"}
        ],
        "expected_content": ["Portfolio", "Holdings", "Performance"]
    }
]

async def test_tab(page, tab_config, browser_context):
    """Test a single tab comprehensively."""
    tab_name = tab_config["name"]
    print(f"\n{'='*80}")
    print(f"🧪 TESTING TAB: {tab_name}")
    print(f"{'='*80}")
    
    results = {
        "tab_name": tab_name,
        "tab_switched": False,
        "buttons_found": [],
        "buttons_missing": [],
        "buttons_clicked": [],
        "buttons_failed": [],
        "content_visible": [],
        "console_errors": [],
        "network_errors": [],
        "screenshots": [],
        "success": False
    }
    
    try:
        # Step 1: Switch to tab
        print(f"  📌 Step 1: Switching to {tab_name} tab...")
        tab_text = tab_config['tab_text']
        
        try:
            # Find tab by text content
            await page.click(f'a[role="tab"]:has-text("{tab_text}")', timeout=10000)
            await asyncio.sleep(3)  # Wait for content to load
            results["tab_switched"] = True
            print(f"    ✅ Tab switched successfully")
        except Exception as e:
            print(f"    ❌ Failed to switch tab: {e}")
            results["tab_switched"] = False
            return results
        
        # Step 2: Capture tab state
        screenshot_path = f"reports/tab_tests/{tab_name.replace(' ', '_').lower()}_initial.png"
        await page.screenshot(path=screenshot_path)
        results["screenshots"].append(screenshot_path)
        print(f"    📸 Screenshot saved: {screenshot_path}")
        
        # Step 3: Verify tab content is visible
        print(f"  📌 Step 2: Verifying tab content...")
        page_content = await page.content()
        for expected_text in tab_config["expected_content"]:
            if expected_text.lower() in page_content.lower():
                results["content_visible"].append(expected_text)
                print(f"    ✅ Found content: '{expected_text}'")
            else:
                print(f"    ⚠️  Content not found: '{expected_text}'")
        
        # Step 4: Test each button
        print(f"  📌 Step 3: Testing buttons...")
        if not tab_config["buttons"]:
            print(f"    ℹ️  No buttons configured for this tab")
            results["success"] = results["tab_switched"] and len(results["content_visible"]) > 0
        else:
            for button_config in tab_config["buttons"]:
                button_id = button_config["id"]
                button_name = button_config["name"]
                
                try:
                    # Check if button exists in DOM
                    button = await page.query_selector(f"#{button_id}")
                    if button:
                        results["buttons_found"].append(button_name)
                        print(f"    ✅ Found button: {button_name} (#{button_id})")
                        
                        # Check if button is visible
                        is_visible = await button.is_visible()
                        if is_visible:
                            print(f"      👁️  Button is visible")
                            
                            # Try to click
                            try:
                                # Capture before state
                                before_content = await page.content()
                                
                                await button.click(timeout=3000)
                                await asyncio.sleep(2)  # Wait for action
                                
                                # Capture after state
                                after_content = await page.content()
                                
                                # Check if something changed
                                if before_content != after_content:
                                    print(f"      ✅ Click succeeded - page content changed")
                                    results["buttons_clicked"].append(button_name)
                                else:
                                    print(f"      ⚠️  Click succeeded but no visible change")
                                    results["buttons_clicked"].append(f"{button_name} (no change)")
                                
                                # Screenshot after click
                                screenshot_path = f"reports/tab_tests/{tab_name.replace(' ', '_').lower()}_{button_id}_clicked.png"
                                await page.screenshot(path=screenshot_path)
                                results["screenshots"].append(screenshot_path)
                                
                            except Exception as click_error:
                                print(f"      ❌ Click failed: {click_error}")
                                results["buttons_failed"].append(f"{button_name}: {str(click_error)}")
                        else:
                            print(f"      ⚠️  Button exists but not visible")
                            results["buttons_failed"].append(f"{button_name}: not visible")
                    else:
                        results["buttons_missing"].append(button_name)
                        print(f"    ❌ Button not found: {button_name} (#{button_id})")
                        
                except Exception as e:
                    print(f"    ❌ Error testing button {button_name}: {e}")
                    results["buttons_failed"].append(f"{button_name}: {str(e)}")
        
        # Step 5: Evaluate success
        total_buttons = len(tab_config["buttons"])
        found_buttons = len(results["buttons_found"])
        clicked_buttons = len(results["buttons_clicked"])
        
        results["success"] = (
            results["tab_switched"] and
            found_buttons >= total_buttons * 0.5 and  # At least 50% buttons found
            clicked_buttons >= found_buttons * 0.5     # At least 50% of found buttons clicked
        )
        
        print(f"\n  📊 TAB SUMMARY:")
        print(f"    Tab Switched: {results['tab_switched']}")
        print(f"    Buttons Found: {found_buttons}/{total_buttons}")
        print(f"    Buttons Clicked: {clicked_buttons}/{found_buttons}")
        print(f"    Content Visible: {len(results['content_visible'])}/{len(tab_config['expected_content'])}")
        print(f"    Success: {'✅ PASS' if results['success'] else '❌ FAIL'}")
        
    except Exception as e:
        print(f"  ❌ CRITICAL ERROR testing {tab_name}: {e}")
        results["success"] = False
        import traceback
        traceback.print_exc()
    
    return results

async def run_comprehensive_test():
    """Run comprehensive test on all tabs."""
    print("\n" + "="*80)
    print("🚀 COMPREHENSIVE TAB TESTING - NON-HEADLESS CHROMIUM")
    print("="*80)
    print(f"Dashboard URL: {DASHBOARD_URL}")
    print(f"Tabs to test: {len(TABS_TO_TEST)}")
    print(f"Test order: {' → '.join([t['name'] for t in TABS_TO_TEST])}")
    print("="*80)
    
    all_results = []
    console_messages = []
    
    async with async_playwright() as p:
        # Launch browser (non-headless)
        print("\n🌐 Launching Chromium browser (non-headless)...")
        browser = await p.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        # Capture console messages
        page.on('console', lambda msg: console_messages.append({
            'type': msg.type,
            'text': msg.text
        }))
        
        # Navigate to dashboard
        print(f"📍 Navigating to {DASHBOARD_URL}...")
        try:
            await page.goto(DASHBOARD_URL, wait_until='networkidle', timeout=60000)
            print("  ✅ Dashboard loaded")
        except Exception as e:
            print(f"  ❌ Failed to load dashboard: {e}")
            await browser.close()
            return {"success": False, "error": f"Dashboard load failed: {e}"}
        
        # Wait for React to render
        print("⏳ Waiting for Dash to initialize...")
        await page.wait_for_selector('#react-entry-point', timeout=30000)
        await asyncio.sleep(3)
        print("  ✅ Dash initialized")
        
        # Test each tab
        for tab_config in TABS_TO_TEST:
            result = await test_tab(page, tab_config, context)
            all_results.append(result)
            
            # Short pause between tabs
            await asyncio.sleep(2)
        
        # Keep browser open for inspection
        print("\n" + "="*80)
        print("👁️  BROWSER INSPECTION WINDOW")
        print("="*80)
        print("Browser will remain open for 30 seconds for manual inspection...")
        print("Check tabs, buttons, and console for any issues.")
        await asyncio.sleep(30)
        
        await browser.close()
    
    # Generate final report
    print("\n" + "="*80)
    print("📊 FINAL TEST REPORT")
    print("="*80)
    
    total_tabs = len(TABS_TO_TEST)
    passed_tabs = sum(1 for r in all_results if r["success"])
    
    print(f"\nOverall Results: {passed_tabs}/{total_tabs} tabs passed")
    print("\nDetailed Results:")
    
    for result in all_results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"\n  {status} {result['tab_name']}")
        print(f"    - Tab Switched: {result['tab_switched']}")
        print(f"    - Buttons Found: {len(result['buttons_found'])}")
        print(f"    - Buttons Clicked: {len(result['buttons_clicked'])}")
        print(f"    - Buttons Missing: {len(result['buttons_missing'])}")
        print(f"    - Buttons Failed: {len(result['buttons_failed'])}")
        
        if result['buttons_missing']:
            print(f"    - Missing: {', '.join(result['buttons_missing'])}")
        if result['buttons_failed']:
            print(f"    - Failed: {', '.join(result['buttons_failed'][:3])}")
    
    # Console error summary
    error_messages = [m for m in console_messages if m['type'] == 'error']
    syntax_errors = [m for m in error_messages if 'SyntaxError' in m['text']]
    
    print(f"\n📋 Console Messages:")
    print(f"  Total messages: {len(console_messages)}")
    print(f"  Errors: {len(error_messages)}")
    print(f"  Syntax errors: {len(syntax_errors)}")
    
    # Save full report
    report = {
        "timestamp": datetime.now().isoformat(),
        "dashboard_url": DASHBOARD_URL,
        "tabs_tested": total_tabs,
        "tabs_passed": passed_tabs,
        "tabs_failed": total_tabs - passed_tabs,
        "success_rate": f"{(passed_tabs/total_tabs)*100:.1f}%",
        "detailed_results": all_results,
        "console_errors": error_messages[:50],  # First 50 errors
        "syntax_errors": syntax_errors
    }
    
    report_file = f"reports/tab_tests/comprehensive_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Full report saved to: {report_file}")
    print("="*80)
    
    # Return success/failure
    all_passed = passed_tabs == total_tabs
    
    if all_passed:
        print("\n🎉 SUCCESS! All tabs passed testing!")
        return {"success": True, "report": report}
    else:
        print(f"\n⚠️  PARTIAL SUCCESS: {passed_tabs}/{total_tabs} tabs passed")
        print("Failed tabs need investigation.")
        return {"success": False, "report": report, "passed": passed_tabs, "total": total_tabs}

if __name__ == '__main__':
    import os
    os.makedirs('reports/tab_tests', exist_ok=True)
    
    result = asyncio.run(run_comprehensive_test())
    
    if result["success"]:
        sys.exit(0)
    else:
        sys.exit(1)

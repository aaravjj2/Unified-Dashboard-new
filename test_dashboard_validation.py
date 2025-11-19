#!/usr/bin/env python3
"""
Pre-Phase 24 Dashboard Validation
Comprehensive check of dashboard functionality vs placeholder content
"""
import asyncio
import json
import time
from playwright.async_api import async_playwright
from pathlib import Path

async def validate_dashboard():
    """Run comprehensive dashboard validation"""
    
    results = {
        "timestamp": time.time(),
        "dashboard_url": "http://localhost:8051",
        "tabs_checked": [],
        "issues_found": [],
        "placeholder_content": [],
        "broken_functionality": [],
        "console_errors": []
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Capture console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append({
            "type": msg.type,
            "text": msg.text,
            "location": msg.location
        }))
        
        try:
            # Load dashboard
            print("🔍 Loading dashboard...")
            await page.goto("http://localhost:8051", wait_until="networkidle", timeout=30000)
            await page.screenshot(path="reports/pre_phase24_validation/screenshots/dashboard_load.png")
            
            # Check for React errors
            react_errors = [err for err in console_errors if "react" in err["text"].lower() or "minified" in err["text"].lower()]
            if react_errors:
                results["console_errors"] = react_errors
                print(f"❌ Found {len(react_errors)} React errors")
            
            # Get all visible tabs
            tabs = await page.locator('[role="tab"]').all()
            print(f"📋 Found {len(tabs)} tabs")
            
            for i, tab in enumerate(tabs):
                tab_text = await tab.inner_text()
                print(f"🔍 Checking tab: {tab_text}")
                
                try:
                    await tab.click()
                    await page.wait_for_timeout(2000)  # Wait for content to load
                    
                    # Take screenshot
                    screenshot_path = f"reports/pre_phase24_validation/screenshots/tab_{i}_{tab_text.replace(' ', '_').lower()}.png"
                    await page.screenshot(path=screenshot_path)
                    
                    # Check for placeholder content
                    page_content = await page.content()
                    placeholder_indicators = [
                        "placeholder", "mock", "sample", "test data", "lorem ipsum",
                        "$0.00", "$100,000", "N/A", "Coming Soon", "Under Development"
                    ]
                    
                    found_placeholders = []
                    for indicator in placeholder_indicators:
                        if indicator.lower() in page_content.lower():
                            found_placeholders.append(indicator)
                    
                    # Check for broken functionality
                    buttons = await page.locator('button:visible').all()
                    broken_buttons = []
                    
                    for button in buttons[:5]:  # Check first 5 buttons
                        button_text = await button.inner_text()
                        if button_text and len(button_text.strip()) > 0:
                            try:
                                await button.click()
                                await page.wait_for_timeout(1000)
                                # Check if anything happened (network requests, DOM changes)
                                # This is a simplified check
                            except Exception as e:
                                broken_buttons.append(f"{button_text}: {str(e)}")
                    
                    tab_result = {
                        "name": tab_text,
                        "screenshot": screenshot_path,
                        "placeholders_found": found_placeholders,
                        "broken_buttons": broken_buttons,
                        "console_errors_count": len([e for e in console_errors if e not in results["console_errors"]])
                    }
                    
                    results["tabs_checked"].append(tab_result)
                    
                    if found_placeholders:
                        results["placeholder_content"].extend([f"{tab_text}: {p}" for p in found_placeholders])
                    
                    if broken_buttons:
                        results["broken_functionality"].extend([f"{tab_text}: {b}" for b in broken_buttons])
                        
                except Exception as e:
                    print(f"❌ Error checking tab {tab_text}: {e}")
                    results["issues_found"].append(f"Tab {tab_text}: {str(e)}")
            
            # Check specific financial data endpoints
            print("🔍 Checking API endpoints...")
            api_checks = [
                "/api/weekly_picks",
                "/api/monthly_picks", 
                "/api/portfolio_summary"
            ]
            
            for endpoint in api_checks:
                try:
                    response = await page.request.get(f"http://localhost:8051{endpoint}")
                    if response.status == 200:
                        data = await response.json()
                        if "error" in data or "mock" in str(data).lower():
                            results["issues_found"].append(f"API {endpoint}: Returns error or mock data")
                    else:
                        results["issues_found"].append(f"API {endpoint}: HTTP {response.status}")
                except Exception as e:
                    results["issues_found"].append(f"API {endpoint}: {str(e)}")
            
        except Exception as e:
            print(f"❌ Critical error: {e}")
            results["critical_error"] = str(e)
        
        finally:
            await browser.close()
    
    # Save results
    with open("reports/pre_phase24_validation/validation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Generate summary
    total_issues = len(results["issues_found"]) + len(results["placeholder_content"]) + len(results["broken_functionality"])
    
    summary = f"""DASHBOARD VALIDATION SUMMARY
=============================
Timestamp: {time.ctime(results['timestamp'])}
Tabs Checked: {len(results['tabs_checked'])}
Total Issues Found: {total_issues}

PLACEHOLDER CONTENT ({len(results['placeholder_content'])}):
{chr(10).join(f"- {item}" for item in results['placeholder_content'][:10])}

BROKEN FUNCTIONALITY ({len(results['broken_functionality'])}):
{chr(10).join(f"- {item}" for item in results['broken_functionality'][:10])}

GENERAL ISSUES ({len(results['issues_found'])}):
{chr(10).join(f"- {item}" for item in results['issues_found'][:10])}

CONSOLE ERRORS: {len(results['console_errors'])}

STATUS: {'NEEDS_MAJOR_FIXES' if total_issues > 5 else 'MINOR_ISSUES' if total_issues > 0 else 'HEALTHY'}
"""
    
    with open("reports/pre_phase24_validation/VALIDATION_SUMMARY.txt", "w") as f:
        f.write(summary)
    
    print(summary)
    return results

if __name__ == "__main__":
    asyncio.run(validate_dashboard())
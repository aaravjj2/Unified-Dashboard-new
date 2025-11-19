#!/usr/bin/env python3
"""
Comprehensive Button & Callback Testing Suite
Tests all interactive buttons across ALL dashboard tabs.

User-reported issues:
1. Strategy Lab - nothing works
2. Azure ML Lab - only scaffold/placeholder  
3. "Run full diagnostic" button broken
4. Options Lab - no new functionality visible
"""

import asyncio
import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
DASHBOARD_URL = "http://localhost:8050"
TAB_SELECTOR = "ul.nav a.nav-link"
TIMEOUT = 10000  # 10 seconds

# Tab-to-button mapping with expected behaviors
TAB_TESTS = {
    "Home": {
        "buttons": [
            {
                "name": "Run Full Diagnostic",
                "selector": "button:has-text('Run Full Diagnostic')",
                "expected_output_selector": "#diagnostic-output",
                "description": "Should run system-wide health check"
            },
            {
                "name": "Fetch Latest News",
                "selector": "button:has-text('Fetch Latest News')",
                "expected_output_selector": "#news-container",
                "description": "Should populate news feed"
            }
        ]
    },
    "Strategy Lab": {
        "buttons": [
            {
                "name": "Validate Strategy (Setup tab)",
                "subtab_selector": "button#setup-tab",
                "selector": "button#sl-validate-btn",
                "expected_output_selector": "#sl-validation-result",
                "description": "Should validate strategy configuration"
            },
            {
                "name": "Run Backtest (Execute tab)",
                "subtab_selector": "button#execute-tab",
                "selector": "button#sl-run-backtest-btn",
                "expected_output_selector": "#sl-backtest-progress",
                "description": "Should execute backtest simulation"
            },
            {
                "name": "Reset to Defaults (Backtest tab)",
                "subtab_selector": "button#backtest-tab",
                "selector": "button#sl-reset-btn",
                "expected_output_selector": "#sl-initial-capital",
                "description": "Should reset backtest parameters"
            }
        ]
    },
    "Azure ML Lab": {
        "buttons": [
            {
                "name": "Train Model",
                "selector": "button:has-text('Train Model'), button:has-text('Start Training')",
                "expected_output_selector": "#training-output, #ml-output",
                "description": "Should start ML model training"
            },
            {
                "name": "Run Prediction",
                "selector": "button:has-text('Predict'), button:has-text('Run Prediction')",
                "expected_output_selector": "#prediction-output, #ml-results",
                "description": "Should generate predictions"
            }
        ]
    },
    "Options Lab": {
        "buttons": [
            {
                "name": "Calculate Greeks",
                "selector": "button:has-text('Calculate'), button#calculate-greeks-btn",
                "expected_output_selector": "#greeks-output",
                "description": "Should calculate option Greeks"
            },
            {
                "name": "Fetch Options Chain",
                "selector": "button:has-text('Fetch Options'), button:has-text('Get Chain')",
                "expected_output_selector": "#options-chain-table",
                "description": "Should load options chain data"
            }
        ]
    },
    "Portfolio": {
        "buttons": [
            {
                "name": "Update Portfolio",
                "selector": "button:has-text('Update Portfolio'), button:has-text('Refresh')",
                "expected_output_selector": "#portfolio-metrics",
                "description": "Should refresh portfolio data"
            }
        ]
    },
    "Market Forecast": {
        "buttons": [
            {
                "name": "Generate Forecast",
                "selector": "button:has-text('Forecast'), button:has-text('Predict')",
                "expected_output_selector": "#forecast-chart",
                "description": "Should generate market forecast"
            }
        ]
    },
    "Market Trends": {
        "buttons": [
            {
                "name": "Refresh Trends",
                "selector": "button:has-text('Refresh'), button:has-text('Update')",
                "expected_output_selector": "#trends-table",
                "description": "Should update market trends"
            }
        ]
    }
}

async def check_console_errors(page):
    """Capture console errors from the page."""
    errors = []
    page.on("console", lambda msg: 
        errors.append(msg.text()) if msg.type == "error" else None)
    return errors

async def test_button(page, tab_name, button_config):
    """Test a single button and return results."""
    result = {
        "tab": tab_name,
        "button": button_config["name"],
        "description": button_config["description"],
        "status": "UNKNOWN",
        "error": None,
        "output_visible": False,
        "console_errors": []
    }
    
    try:
        # Navigate to subtab if specified
        if "subtab_selector" in button_config:
            logger.info(f"  Navigating to subtab: {button_config['subtab_selector']}")
            await page.click(button_config["subtab_selector"], timeout=5000)
            await page.wait_for_timeout(1000)
        
        # Check if button exists
        button_selector = button_config["selector"]
        button = await page.query_selector(button_selector)
        
        if not button:
            result["status"] = "NOT_FOUND"
            result["error"] = f"Button not found: {button_selector}"
            logger.warning(f"  ❌ {result['button']}: NOT FOUND")
            return result
        
        # Capture console errors before clicking
        console_errors = []
        page.on("console", lambda msg: 
            console_errors.append(msg.text()) if msg.type == "error" else None)
        
        # Click the button
        logger.info(f"  🖱️  Clicking: {button_config['name']}")
        await button.click()
        await page.wait_for_timeout(3000)  # Wait for callback to execute
        
        # Check for expected output
        output_selector = button_config.get("expected_output_selector", "")
        if output_selector:
            output_elem = await page.query_selector(output_selector)
            result["output_visible"] = output_elem is not None
            
            if output_elem:
                # Check if output has meaningful content
                output_text = await output_elem.inner_text()
                result["output_content"] = output_text[:200] if output_text else "(empty)"
        
        # Capture any console errors
        await page.wait_for_timeout(1000)
        result["console_errors"] = console_errors
        
        # Determine status
        if console_errors:
            result["status"] = "ERROR"
            result["error"] = f"Console errors: {'; '.join(console_errors[:3])}"
            logger.error(f"  ❌ {result['button']}: ERRORS - {result['error']}")
        elif result["output_visible"]:
            result["status"] = "SUCCESS"
            logger.info(f"  ✅ {result['button']}: SUCCESS (output visible)")
        else:
            result["status"] = "NO_OUTPUT"
            result["error"] = f"No output found at: {output_selector}"
            logger.warning(f"  ⚠️  {result['button']}: NO OUTPUT")
        
    except PlaywrightTimeout as e:
        result["status"] = "TIMEOUT"
        result["error"] = f"Timeout: {str(e)}"
        logger.error(f"  ❌ {result['button']}: TIMEOUT - {str(e)}")
    except Exception as e:
        result["status"] = "EXCEPTION"
        result["error"] = str(e)
        logger.error(f"  ❌ {result['button']}: EXCEPTION - {str(e)}")
    
    return result

async def test_tab_buttons(page, tab_name, tab_index):
    """Test all buttons in a specific tab."""
    logger.info(f"\n{'='*80}")
    logger.info(f"Testing Tab: {tab_name} (index {tab_index})")
    logger.info(f"{'='*80}")
    
    try:
        # Click the tab
        await page.click(f"{TAB_SELECTOR}:nth-child({tab_index + 1})", timeout=TIMEOUT)
        await page.wait_for_timeout(2000)  # Wait for tab content to load
        
        # Get button tests for this tab
        tab_config = TAB_TESTS.get(tab_name, {})
        buttons = tab_config.get("buttons", [])
        
        if not buttons:
            logger.warning(f"  ⚠️  No button tests defined for {tab_name}")
            return []
        
        # Test each button
        results = []
        for button_config in buttons:
            result = await test_button(page, tab_name, button_config)
            results.append(result)
        
        return results
        
    except Exception as e:
        logger.error(f"  ❌ Error testing {tab_name}: {str(e)}")
        return [{
            "tab": tab_name,
            "button": "Tab Click",
            "status": "ERROR",
            "error": str(e)
        }]

async def run_comprehensive_test():
    """Run comprehensive button tests across all tabs."""
    logger.info("🚀 Starting Comprehensive Button & Callback Test Suite")
    logger.info(f"Dashboard URL: {DASHBOARD_URL}")
    
    all_results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Navigate to dashboard
            logger.info(f"\n📡 Loading dashboard: {DASHBOARD_URL}")
            await page.goto(DASHBOARD_URL, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)  # Let React hydrate
            
            # Get all tab names
            tabs = await page.query_selector_all(TAB_SELECTOR)
            tab_names = []
            for tab in tabs:
                name = await tab.inner_text()
                tab_names.append(name.strip())
            
            logger.info(f"Found {len(tab_names)} tabs: {', '.join(tab_names)}")
            
            # Test each tab that has defined button tests
            for tab_index, tab_name in enumerate(tab_names):
                if tab_name in TAB_TESTS:
                    results = await test_tab_buttons(page, tab_name, tab_index)
                    all_results.extend(results)
                else:
                    logger.info(f"\n⏭️  Skipping {tab_name} (no button tests defined)")
            
        except Exception as e:
            logger.error(f"❌ Fatal error during testing: {str(e)}")
            all_results.append({
                "tab": "Global",
                "button": "Test Suite",
                "status": "FATAL_ERROR",
                "error": str(e)
            })
        finally:
            await browser.close()
    
    return all_results

def generate_report(results):
    """Generate comprehensive test report."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Calculate statistics
    total = len(results)
    success = len([r for r in results if r["status"] == "SUCCESS"])
    errors = len([r for r in results if r["status"] == "ERROR"])
    not_found = len([r for r in results if r["status"] == "NOT_FOUND"])
    no_output = len([r for r in results if r["status"] == "NO_OUTPUT"])
    
    # Generate report
    report = f"""
{'='*100}
COMPREHENSIVE BUTTON & CALLBACK TEST REPORT
{'='*100}
Timestamp: {timestamp}
Dashboard URL: {DASHBOARD_URL}

📊 TEST SUMMARY:
   Total Tests:     {total}
   ✅ Success:      {success} ({success/total*100:.1f}%)
   ❌ Errors:       {errors} ({errors/total*100:.1f}%)
   🔍 Not Found:    {not_found} ({not_found/total*100:.1f}%)
   ⚠️  No Output:   {no_output} ({no_output/total*100:.1f}%)

{'='*100}
DETAILED RESULTS:
{'='*100}
"""
    
    # Group results by tab
    tabs = {}
    for result in results:
        tab = result["tab"]
        if tab not in tabs:
            tabs[tab] = []
        tabs[tab].append(result)
    
    for tab_name, tab_results in sorted(tabs.items()):
        report += f"\n{'▼'*100}\n"
        report += f"TAB: {tab_name}\n"
        report += f"{'▼'*100}\n"
        
        for result in tab_results:
            status_icon = {
                "SUCCESS": "✅",
                "ERROR": "❌",
                "NOT_FOUND": "🔍",
                "NO_OUTPUT": "⚠️",
                "TIMEOUT": "⏱️",
                "EXCEPTION": "💥"
            }.get(result["status"], "❓")
            
            report += f"\n{status_icon} {result['button']}\n"
            report += f"   Status: {result['status']}\n"
            report += f"   Description: {result['description']}\n"
            
            if result.get("error"):
                report += f"   Error: {result['error']}\n"
            
            if result.get("output_visible"):
                report += f"   Output: Visible\n"
                if result.get("output_content"):
                    report += f"   Content Preview: {result['output_content']}\n"
            
            if result.get("console_errors"):
                report += f"   Console Errors ({len(result['console_errors'])}):\n"
                for err in result['console_errors'][:5]:
                    report += f"      • {err}\n"
    
    report += f"\n{'='*100}\n"
    report += "END OF REPORT\n"
    report += f"{'='*100}\n"
    
    return report

async def main():
    """Main test execution."""
    try:
        results = await run_comprehensive_test()
        report = generate_report(results)
        
        # Print to console
        print(report)
        
        # Save to file
        report_file = f"button_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        logger.info(f"\n✅ Report saved to: {report_file}")
        
        # Save JSON results
        json_file = f"button_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"✅ JSON results saved to: {json_file}")
        
    except Exception as e:
        logger.error(f"❌ Test suite failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Playwright E2E Tests for Options Forecast & Azure ML Prediction
Also investigates TradingView failure in Options Lab

Tests:
1. Options Forecast - Click forecast button and verify results
2. Azure ML Prediction - Click prediction button and verify output
3. TradingView in Options Lab - Debug why it fails

Usage:
    python tests/test_options_azureml_playwright.py
"""

import asyncio
import sys
import os
from pathlib import Path
from playwright.async_api import async_playwright
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

DASHBOARD_URL = os.getenv('DASHBOARD_URL', 'http://localhost:8050')
TIMEOUT = 60000  # 60 seconds
SCREENSHOT_DIR = 'outputs/playwright_tests'
Path(SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)


async def test_options_forecast(page):
    """Test Options Forecast feature with Chromium."""
    print("\n" + "="*70)
    print("🔮 TESTING: Options Forecast")
    print("="*70)
    
    try:
        # Navigate to dashboard
        print("📍 Navigating to dashboard...")
        await page.goto(DASHBOARD_URL, timeout=TIMEOUT)
        await page.wait_for_load_state('networkidle', timeout=TIMEOUT)
        print("  ✅ Dashboard loaded")
        
        # Take initial screenshot
        await page.screenshot(path=f'{SCREENSHOT_DIR}/01_options_forecast_home.png', full_page=True)
        
        # Navigate to Options Lab
        print("📍 Clicking Options Lab tab...")
        options_tab = page.locator('text=💹 Options Lab').first
        await options_tab.wait_for(state='visible', timeout=TIMEOUT)
        await options_tab.click()
        await page.wait_for_timeout(2000)
        print("  ✅ Options Lab opened")
        
        await page.screenshot(path=f'{SCREENSHOT_DIR}/02_options_lab_loaded.png', full_page=True)
        
        # Load mock data first
        print("📊 Loading mock data for AAPL...")
        ticker_input = page.locator('#options-ticker-input')
        await ticker_input.wait_for(state='visible', timeout=TIMEOUT)
        await ticker_input.clear()
        await ticker_input.fill('AAPL')
        
        mock_btn = page.locator('#options-mock-btn')
        await mock_btn.click()
        await page.wait_for_timeout(3000)
        print("  ✅ Mock data loaded")
        
        await page.screenshot(path=f'{SCREENSHOT_DIR}/03_mock_data_loaded.png', full_page=True)
        
        # Find and click Options Forecast tab/button
        print("🔮 Looking for Options Forecast feature...")
        
        # Try multiple possible selectors for forecast (prioritize explicit id)
        forecast_selectors = [
            '#options-forecast-btn',
            'button:has-text("Forecast")',
            'text=Options Forecast',
            'text=Forecast',
            'button:has-text("Run Forecast")',
            'button:has-text("Generate Forecast")'
        ]
        
        forecast_found = False
        for selector in forecast_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=2000):
                    print(f"  ✅ Found forecast element: {selector}")
                    await element.click()
                    # Give the app a bit more time to process the forecast callback
                    await page.wait_for_timeout(7000)
                    forecast_found = True
                    break
            except:
                continue
        
        if not forecast_found:
            print("  ⚠️ WARNING: Options Forecast button not found")
            print("  Checking available tabs/buttons...")
            
            # List all visible buttons
            all_buttons = await page.locator('button').all()
            button_texts = []
            for btn in all_buttons:
                try:
                    if await btn.is_visible():
                        text = await btn.inner_text()
                        if text:
                            button_texts.append(text)
                except:
                    pass
            
            print(f"  Available buttons: {', '.join(button_texts[:20])}")
            
            # Take screenshot showing what's available
            await page.screenshot(path=f'{SCREENSHOT_DIR}/04_forecast_not_found.png', full_page=True)
            return False
        
        print("  ✅ Forecast button clicked")
        await page.screenshot(path=f'{SCREENSHOT_DIR}/04_forecast_clicked.png', full_page=True)
        
        # Check for forecast results
        print("🔍 Checking for forecast results...")
        result_selectors = [
            '#options-forecast-results',
            '#options-forecast-chart',
            '#options-forecast-output',
            'text=Forecast Results',
            'text=Predicted Price'
        ]
        
        results_found = False
        for selector in result_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=5000):
                    content = await element.inner_text()
                    print(f"  ✅ Found results: {selector}")
                    print(f"  📊 Content preview: {content[:200]}...")
                    results_found = True
                    break
            except:
                continue
        
        if not results_found:
            print("  ⚠️ WARNING: Forecast results not visible")
        
        await page.screenshot(path=f'{SCREENSHOT_DIR}/05_forecast_results.png', full_page=True)
        
        print(f"\n✅ Options Forecast test completed")
        print(f"📸 Screenshots saved to: {SCREENSHOT_DIR}/")
        return forecast_found and results_found
        
    except Exception as e:
        print(f"\n❌ Options Forecast test failed: {str(e)}")
        await page.screenshot(path=f'{SCREENSHOT_DIR}/error_options_forecast.png', full_page=True)
        return False


async def test_azure_ml_prediction(page):
    """Test Azure ML Prediction feature with Chromium."""
    print("\n" + "="*70)
    print("🤖 TESTING: Azure ML Prediction")
    print("="*70)
    
    try:
        # Navigate to dashboard
        print("📍 Navigating to dashboard...")
        await page.goto(DASHBOARD_URL, timeout=TIMEOUT)
        await page.wait_for_load_state('networkidle', timeout=TIMEOUT)
        print("  ✅ Dashboard loaded")
        
        # Navigate to Azure ML Lab
        print("📍 Clicking Azure ML Lab tab...")
        
        # Try multiple selectors
        ml_selectors = [
            'text=🧠 Azure ML Lab',
            'text=Azure ML Lab',
            'text=Azure ML',
            'a:has-text("Azure ML")'
        ]
        
        ml_found = False
        for selector in ml_selectors:
            try:
                ml_tab = page.locator(selector).first
                if await ml_tab.is_visible(timeout=5000):
                    await ml_tab.click()
                    await page.wait_for_timeout(2000)
                    ml_found = True
                    print("  ✅ Azure ML Lab opened")
                    break
            except:
                continue
        
        if not ml_found:
            print("  ⚠️ WARNING: Azure ML Lab tab not found")
            # List available tabs
            all_tabs = await page.locator('a.nav-link').all()
            tab_texts = []
            for tab in all_tabs:
                try:
                    text = await tab.inner_text()
                    if text:
                        tab_texts.append(text)
                except:
                    pass
            print(f"  Available tabs: {', '.join(tab_texts)}")
            await page.screenshot(path=f'{SCREENSHOT_DIR}/11_ml_tab_not_found.png', full_page=True)
            return False
        
        await page.screenshot(path=f'{SCREENSHOT_DIR}/12_azure_ml_loaded.png', full_page=True)
        
        # Look for prediction button
        print("🤖 Looking for ML Prediction button...")
        
        prediction_selectors = [
            '#azure-ml-run-prediction-btn',  # Correct ID from layout.py
            '#azure-ml-predict-btn',
            '#azure-ml-run-btn',
            'button:has-text("Run Prediction")',
            'button:has-text("Predict")',
            'button:has-text("Generate Prediction")',
            'button:has-text("Run")'
        ]
        
        predict_found = False
        for selector in prediction_selectors:
            try:
                predict_btn = page.locator(selector).first
                if await predict_btn.is_visible(timeout=2000):
                    print(f"  ✅ Found prediction button: {selector}")
                    await predict_btn.click()
                    await page.wait_for_timeout(5000)  # ML predictions may take longer
                    predict_found = True
                    break
            except:
                continue
        
        if not predict_found:
            print("  ⚠️ WARNING: ML Prediction button not found")
            # List all visible buttons
            all_buttons = await page.locator('button').all()
            button_texts = []
            for btn in all_buttons:
                try:
                    if await btn.is_visible():
                        text = await btn.inner_text()
                        if text:
                            button_texts.append(text)
                except:
                    pass
            print(f"  Available buttons: {', '.join(button_texts[:20])}")
            await page.screenshot(path=f'{SCREENSHOT_DIR}/13_predict_not_found.png', full_page=True)
            return False
        
        print("  ✅ Prediction button clicked")
        await page.screenshot(path=f'{SCREENSHOT_DIR}/13_prediction_clicked.png', full_page=True)
        
        # Check for prediction results
        print("🔍 Checking for ML prediction results...")
        
        result_selectors = [
            '#azure-ml-prediction-results',
            '#azure-ml-results',
            '#azure-ml-output',
            'text=Prediction Results',
            'text=ML Prediction Complete',
            'text=Predicted',
            '.alert-success'
        ]
        
        results_found = False
        result_content = ""
        for selector in result_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=5000):
                    content = await element.inner_text()
                    print(f"  ✅ Found results: {selector}")
                    print(f"  📊 Content preview: {content[:300]}...")
                    result_content = content
                    results_found = True
                    
                    # Check output length (Phase 18B requirement: ≥150 chars)
                    if len(content) >= 150:
                        print(f"  ✅ Output length: {len(content)} chars (meets ≥150 requirement)")
                    else:
                        print(f"  ⚠️ Output length: {len(content)} chars (below 150 requirement)")
                    
                    break
            except:
                continue
        
        if not results_found:
            print("  ⚠️ WARNING: ML prediction results not visible")
        
        await page.screenshot(path=f'{SCREENSHOT_DIR}/14_prediction_results.png', full_page=True)
        
        print(f"\n✅ Azure ML Prediction test completed")
        print(f"📸 Screenshots saved to: {SCREENSHOT_DIR}/")
        return predict_found and results_found
        
    except Exception as e:
        print(f"\n❌ Azure ML Prediction test failed: {str(e)}")
        await page.screenshot(path=f'{SCREENSHOT_DIR}/error_azure_ml.png', full_page=True)
        return False


async def test_tradingview_options_lab(page):
    """Investigate TradingView failure in Options Lab."""
    print("\n" + "="*70)
    print("📈 TESTING: TradingView in Options Lab (Debug)")
    print("="*70)
    
    try:
        # Navigate to dashboard
        print("📍 Navigating to dashboard...")
        await page.goto(DASHBOARD_URL, timeout=TIMEOUT)
        await page.wait_for_load_state('networkidle', timeout=TIMEOUT)
        
        # Navigate to Options Lab
        print("📍 Opening Options Lab...")
        options_tab = page.locator('text=💹 Options Lab').first
        await options_tab.wait_for(state='visible', timeout=TIMEOUT)
        await options_tab.click()
        await page.wait_for_timeout(2000)
        
        await page.screenshot(path=f'{SCREENSHOT_DIR}/21_options_lab_for_tv.png', full_page=True)
        
        # Look for TradingView widget/iframe/element
        print("🔍 Searching for TradingView components...")
        
        tv_selectors = [
            'iframe[src*="tradingview"]',
            'iframe[src*="trading"]',
            '#tradingview-widget',
            '#tradingview_chart',
            '.tradingview-widget-container',
            'text=TradingView',
            'text=Trading View'
        ]
        
        tv_found = False
        for selector in tv_selectors:
            try:
                element = page.locator(selector).first
                count = await page.locator(selector).count()
                print(f"  🔍 Checking: {selector} (found: {count})")
                
                if count > 0:
                    tv_found = True
                    is_visible = await element.is_visible(timeout=2000)
                    print(f"  ✅ Found TradingView element: {selector} (visible: {is_visible})")
                    
                    # Check if it's an iframe
                    if 'iframe' in selector:
                        src = await element.get_attribute('src')
                        print(f"  📋 Iframe src: {src}")
                    
                    # Check element properties
                    try:
                        bounding_box = await element.bounding_box()
                        if bounding_box:
                            print(f"  📏 Dimensions: {bounding_box}")
                        else:
                            print(f"  ⚠️ Element has no bounding box (may be hidden)")
                    except:
                        pass
                    
            except Exception as e:
                print(f"  ❌ Error checking {selector}: {str(e)}")
        
        if not tv_found:
            print("  ⚠️ WARNING: No TradingView components found")
            print("\n  Possible reasons:")
            print("    1. TradingView not implemented in Options Lab")
            print("    2. TradingView widget failed to load")
            print("    3. Widget is in a different tab/section")
            print("    4. Widget requires specific actions to appear")
        
        # Check console for TradingView errors
        print("\n🔍 Checking browser console for errors...")
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: console_logs.append(f"[ERROR] {err}"))
        
        await page.wait_for_timeout(3000)
        
        if console_logs:
            print(f"  📋 Console logs ({len(console_logs)} messages):")
            for log in console_logs[:10]:  # Show first 10
                if 'tradingview' in log.lower() or 'trading' in log.lower():
                    print(f"    {log}")
        
        # Check network requests
        print("\n🔍 Checking network requests for TradingView...")
        network_requests = []
        page.on("request", lambda req: network_requests.append(req.url))
        
        await page.wait_for_timeout(2000)
        
        tv_requests = [url for url in network_requests if 'tradingview' in url.lower()]
        if tv_requests:
            print(f"  ✅ Found {len(tv_requests)} TradingView network requests:")
            for url in tv_requests[:5]:
                print(f"    {url}")
        else:
            print("  ⚠️ No TradingView network requests detected")
        
        await page.screenshot(path=f'{SCREENSHOT_DIR}/22_tradingview_debug.png', full_page=True)
        
        # Check if there's a specific tab/section for charts
        print("\n🔍 Looking for chart tabs/sections...")
        chart_selectors = [
            'text=Charts',
            'text=Chart',
            'text=Visualization',
            'text=Price Chart',
            'button:has-text("Chart")'
        ]
        
        for selector in chart_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=1000):
                    print(f"  ✅ Found chart section: {selector}")
                    await element.click()
                    await page.wait_for_timeout(2000)
                    await page.screenshot(path=f'{SCREENSHOT_DIR}/23_chart_section.png', full_page=True)
                    break
            except:
                continue
        
        print(f"\n📸 Screenshots saved to: {SCREENSHOT_DIR}/")
        return tv_found
        
    except Exception as e:
        print(f"\n❌ TradingView investigation failed: {str(e)}")
        await page.screenshot(path=f'{SCREENSHOT_DIR}/error_tradingview.png', full_page=True)
        return False


async def main():
    """Run all Playwright tests."""
    print("\n" + "="*70)
    print("🎭 PLAYWRIGHT E2E TEST SUITE")
    print("Options Forecast | Azure ML Prediction | TradingView Debug")
    print("="*70)
    print(f"\n📍 Dashboard URL: {DASHBOARD_URL}")
    print(f"📸 Screenshot Directory: {SCREENSHOT_DIR}")
    print(f"⏱️ Timeout: {TIMEOUT}ms")
    
    results = {
        'options_forecast': False,
        'azure_ml_prediction': False,
        'tradingview_debug': False
    }
    
    async with async_playwright() as p:
        print("\n🚀 Launching Chromium browser...")
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        
        page = await context.new_page()
        
        # Set up console/error monitoring
        page.on("console", lambda msg: print(f"  🖥️ Browser [{msg.type}]: {msg.text[:100]}"))
        page.on("pageerror", lambda err: print(f"  ❌ Browser Error: {str(err)[:100]}"))
        
        try:
            # Test 1: Options Forecast
            results['options_forecast'] = await test_options_forecast(page)
            
            # Test 2: Azure ML Prediction
            results['azure_ml_prediction'] = await test_azure_ml_prediction(page)
            
            # Test 3: TradingView Debug
            results['tradingview_debug'] = await test_tradingview_options_lab(page)
            
        finally:
            await browser.close()
    
    # Print summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name.replace('_', ' ').title()}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\n🎯 Results: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print(f"📸 All screenshots saved to: {SCREENSHOT_DIR}/")
    
    return all(results.values())


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

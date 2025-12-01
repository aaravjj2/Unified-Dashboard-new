#!/usr/bin/env python3
"""
Market Forecast Browser Test (Non-Headless)
Tests the Market Forecast tab in Chromium with visible browser
"""

import time
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

DASHBOARD_URL = "http://localhost:8051"
SCREENSHOT_DIR = Path("reports/test_screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def take_screenshot(page, name: str):
    """Take a screenshot with timestamp"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filepath = SCREENSHOT_DIR / f"{name}_{timestamp}.png"
    page.screenshot(path=str(filepath), full_page=True)
    print(f"  📸 Screenshot saved: {filepath}")
    return filepath


def test_market_forecast_tab(page):
    """Test Market Forecast tab functionality"""
    print("\n" + "="*60)
    print("🧪 MARKET FORECAST TAB TEST")
    print("="*60)
    
    # Navigate to dashboard
    print("\n1. Navigating to dashboard...")
    page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=30000)
    time.sleep(2)
    take_screenshot(page, "01_dashboard_loaded")
    
    # Find and click Market Forecast tab
    print("\n2. Looking for Market Forecast tab...")
    
    # Try multiple selectors
    tab_selectors = [
        'div[class*="tab"][id*="market-forecast"]',
        'div.tab-container >> text=Market Forecast',
        'button:has-text("Market Forecast")',
        'div:has-text("Market Forecast"):visible',
        '[data-tab="market-forecast"]'
    ]
    
    tab_found = False
    for selector in tab_selectors:
        try:
            tab = page.locator(selector).first
            if tab.is_visible(timeout=2000):
                print(f"   Found tab with selector: {selector}")
                tab.click()
                tab_found = True
                break
        except:
            continue
    
    if not tab_found:
        # Try finding by scanning all visible tabs
        print("   Scanning visible tabs...")
        tabs = page.locator('div.tab, button.tab, [role="tab"]').all()
        for tab in tabs:
            try:
                text = tab.inner_text()
                if "forecast" in text.lower() or "market" in text.lower():
                    print(f"   Found tab: '{text}'")
                    tab.click()
                    tab_found = True
                    break
            except:
                continue
    
    time.sleep(2)
    take_screenshot(page, "02_market_forecast_tab")
    
    # Check for AI Forecast components
    print("\n3. Checking for AI Forecast components...")
    
    components_to_check = [
        ("AI Forecast section", 'div:has-text("AI Forecast")'),
        ("Sentiment gauge", '#ai-sentiment-gauge, [id*="sentiment"]'),
        ("Forecast chart", '[id*="forecast-chart"], .js-plotly-plot'),
        ("Confidence score", 'div:has-text("Confidence")'),
        ("Model info", 'div:has-text("Model"), div:has-text("LSTM")'),
    ]
    
    for name, selector in components_to_check:
        try:
            element = page.locator(selector).first
            if element.is_visible(timeout=3000):
                print(f"   ✅ {name}: FOUND")
            else:
                print(f"   ⚠️  {name}: Not visible")
        except:
            print(f"   ❌ {name}: Not found")
    
    # Check for sentiment score display
    print("\n4. Looking for sentiment data...")
    page_content = page.content()
    sentiment_indicators = ["sentiment", "bullish", "bearish", "neutral", "confidence"]
    for indicator in sentiment_indicators:
        if indicator.lower() in page_content.lower():
            print(f"   ✅ Found '{indicator}' in page content")
    
    take_screenshot(page, "03_ai_components")
    
    # Test subtabs if present
    print("\n5. Testing subtabs...")
    subtab_selectors = [
        'div.subtab, button.subtab',
        '[id*="subtab"]',
        'div.tab-content >> button'
    ]
    
    for selector in subtab_selectors:
        try:
            subtabs = page.locator(selector).all()
            if subtabs:
                print(f"   Found {len(subtabs)} subtabs")
                for idx, subtab in enumerate(subtabs[:5]):  # Limit to first 5
                    try:
                        text = subtab.inner_text()
                        print(f"   - Subtab {idx+1}: '{text.strip()}'")
                        subtab.click()
                        time.sleep(1)
                        take_screenshot(page, f"04_subtab_{idx+1}")
                    except:
                        continue
                break
        except:
            continue
    
    # Test symbol selector if present
    print("\n6. Testing symbol selector...")
    symbol_selectors = [
        '#symbol-selector',
        '[id*="ticker"]',
        'input[placeholder*="symbol" i]',
        '.symbol-dropdown'
    ]
    
    for selector in symbol_selectors:
        try:
            dropdown = page.locator(selector).first
            if dropdown.is_visible(timeout=2000):
                print(f"   Found symbol selector: {selector}")
                dropdown.click()
                time.sleep(1)
                take_screenshot(page, "05_symbol_dropdown")
                break
        except:
            continue
    
    # Check for any errors in console
    print("\n7. Checking browser console for errors...")
    # Console messages are captured separately if needed
    
    take_screenshot(page, "06_final_state")
    
    print("\n" + "="*60)
    print("✅ Market Forecast Tab Test Complete!")
    print("="*60)
    return True


def test_ai_sentiment_display(page):
    """Test AI sentiment display functionality"""
    print("\n" + "="*60)
    print("🧪 AI SENTIMENT DISPLAY TEST")
    print("="*60)
    
    # Navigate to Market Forecast
    page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=30000)
    time.sleep(2)
    
    # Look for sentiment-related elements
    print("\n1. Looking for sentiment elements...")
    
    sentiment_selectors = [
        '#ai-sentiment-score',
        '[id*="sentiment"]',
        'div:has-text("Sentiment")',
        '.sentiment-gauge',
        '.sentiment-indicator'
    ]
    
    for selector in sentiment_selectors:
        try:
            elements = page.locator(selector).all()
            for elem in elements:
                if elem.is_visible():
                    text = elem.inner_text()
                    if text.strip():
                        print(f"   ✅ {selector}: '{text[:50]}...'")
        except:
            continue
    
    # Look for forecast data
    print("\n2. Looking for forecast data...")
    forecast_patterns = ["forecast", "prediction", "target", "confidence", "trend"]
    page_text = page.inner_text("body")
    
    for pattern in forecast_patterns:
        if pattern.lower() in page_text.lower():
            # Find context around the pattern
            idx = page_text.lower().find(pattern.lower())
            context = page_text[max(0, idx-20):idx+50].replace('\n', ' ')
            print(f"   Found '{pattern}': ...{context}...")
    
    take_screenshot(page, "07_sentiment_display")
    return True


def main():
    print("\n" + "="*70)
    print("🚀 MARKET FORECAST BROWSER TEST - NON-HEADLESS MODE")
    print("="*70)
    print(f"\nDashboard URL: {DASHBOARD_URL}")
    print(f"Screenshots will be saved to: {SCREENSHOT_DIR}")
    
    with sync_playwright() as p:
        # Launch Chromium in non-headless mode
        print("\n📺 Launching Chromium browser (visible mode)...")
        browser = p.chromium.launch(
            headless=False,
            slow_mo=500,  # Slow down actions for visibility
            args=['--window-size=1920,1080']
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Enable console logging
        page = context.new_page()
        
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        
        try:
            # Run tests
            test_market_forecast_tab(page)
            test_ai_sentiment_display(page)
            
            # Report console errors
            if console_errors:
                print("\n" + "="*60)
                print("⚠️  CONSOLE ERRORS DETECTED:")
                print("="*60)
                for error in console_errors[:10]:  # Limit to first 10
                    print(f"   - {error[:100]}...")
            
            print("\n" + "="*70)
            print("✅ ALL BROWSER TESTS COMPLETED!")
            print("="*70)
            print(f"\nScreenshots saved to: {SCREENSHOT_DIR}")
            
            # Keep browser open for a moment to see final state
            print("\nBrowser will close in 5 seconds...")
            time.sleep(5)
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            take_screenshot(page, "error_state")
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()

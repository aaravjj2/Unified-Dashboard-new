#!/usr/bin/env python3
"""
Comprehensive Browser Test for Market Forecast and AI Chatbot
Tests both features with non-headless Chromium
"""

import time
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

DASHBOARD_URL = "http://localhost:8050"
SCREENSHOT_DIR = Path("reports/test_screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def take_screenshot(page, name: str):
    """Take a screenshot with timestamp"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filepath = SCREENSHOT_DIR / f"{name}_{timestamp}.png"
    page.screenshot(path=str(filepath), full_page=False)
    print(f"  📸 Screenshot: {filepath}")
    return filepath


def test_market_forecast(page):
    """Test enhanced Market Forecast with AI sentiment"""
    print("\n" + "="*60)
    print("🧪 TEST 1: MARKET FORECAST TAB")
    print("="*60)
    
    # Navigate to dashboard
    print("\n1. Navigating to dashboard...")
    page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=30000)
    time.sleep(2)
    
    # Find and click Market Forecast tab
    print("\n2. Opening Market Forecast tab...")
    try:
        # Try multiple selectors
        tab = page.locator('div:has-text("Market Forecast")').first
        if tab.is_visible(timeout=3000):
            tab.click()
            time.sleep(2)
            print("   ✅ Market Forecast tab opened")
    except:
        print("   ⚠️ Could not find Market Forecast tab by text")
    
    take_screenshot(page, "01_market_forecast")
    
    # Look for AI/Sentiment components
    print("\n3. Checking for AI forecast components...")
    
    components = [
        ("Ticker selector", '#mf-ticker-selector, [id*="ticker"]'),
        ("Forecast button", '#mf-generate-btn, button:has-text("Generate"), button:has-text("Forecast")'),
        ("Chart area", '.js-plotly-plot, [id*="chart"]'),
        ("Sentiment indicator", '[id*="sentiment"], div:has-text("Sentiment")'),
    ]
    
    found_count = 0
    for name, selector in components:
        try:
            elem = page.locator(selector).first
            if elem.is_visible(timeout=2000):
                print(f"   ✅ {name}: Found")
                found_count += 1
            else:
                print(f"   ⚠️ {name}: Not visible")
        except:
            print(f"   ❌ {name}: Not found")
    
    # Try to generate a forecast
    print("\n4. Testing forecast generation...")
    try:
        # Try to find and interact with ticker input
        ticker_input = page.locator('#mf-ticker-input, input[placeholder*="ticker" i]').first
        if ticker_input.is_visible(timeout=2000):
            ticker_input.fill("AAPL")
            print("   ✅ Entered ticker: AAPL")
            time.sleep(1)
            
            # Click generate button
            gen_btn = page.locator('#mf-generate-btn, button:has-text("Generate")').first
            if gen_btn.is_visible(timeout=2000):
                gen_btn.click()
                print("   ✅ Clicked generate button")
                time.sleep(5)  # Wait for forecast
                
    except Exception as e:
        print(f"   ⚠️ Forecast generation: {e}")
    
    take_screenshot(page, "02_forecast_generated")
    
    # Check page content for sentiment/forecast data
    print("\n5. Checking page content...")
    content = page.content().lower()
    indicators = ['sentiment', 'forecast', 'prediction', 'confidence', 'bullish', 'bearish']
    for ind in indicators:
        if ind in content:
            print(f"   ✅ Found '{ind}' in page content")
    
    print(f"\n   Components found: {found_count}/4")
    return found_count >= 2


def test_chatbot(page):
    """Test AI Chatbot functionality"""
    print("\n" + "="*60)
    print("🧪 TEST 2: AI CHATBOT")
    print("="*60)
    
    # Navigate to dashboard
    print("\n1. Ensuring dashboard is loaded...")
    page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=30000)
    time.sleep(2)
    
    # Find and click chatbot toggle
    print("\n2. Opening chatbot...")
    try:
        toggle_btn = page.locator('#chatbot-toggle-btn, #chatbot-fab, button:has-text("Chat")').first
        if toggle_btn.is_visible(timeout=3000):
            toggle_btn.click()
            time.sleep(1)
            print("   ✅ Chatbot toggle clicked")
        else:
            # Try JavaScript click
            page.evaluate("document.getElementById('chatbot-toggle-btn')?.click()")
            time.sleep(1)
            print("   ✅ Chatbot opened via JS")
    except Exception as e:
        print(f"   ⚠️ Could not open chatbot: {e}")
    
    take_screenshot(page, "03_chatbot_open")
    
    # Check if chatbot window is visible
    print("\n3. Checking chatbot window...")
    try:
        chatbot_window = page.locator('#chatbot-container, #chatbot-window').first
        if chatbot_window.is_visible(timeout=2000):
            print("   ✅ Chatbot window is visible")
            
            # Check for input field
            chat_input = page.locator('#chatbot-input, textarea[id*="chat"], input[id*="chat"]').first
            if chat_input.is_visible(timeout=2000):
                print("   ✅ Chat input field found")
                
                # Try sending a message
                print("\n4. Sending test message...")
                chat_input.fill("What is the current market sentiment?")
                time.sleep(0.5)
                
                # Find and click send button
                send_btn = page.locator('#chatbot-send-btn, button:has-text("Send")').first
                if send_btn.is_visible(timeout=2000):
                    send_btn.click()
                    print("   ✅ Message sent")
                    time.sleep(3)  # Wait for response
                    
                    take_screenshot(page, "04_chatbot_response")
                    
                    # Check for response
                    messages = page.locator('#chatbot-messages, .chat-message').first
                    if messages.is_visible():
                        msg_text = messages.inner_text()
                        if len(msg_text) > 50:
                            print(f"   ✅ Response received: {len(msg_text)} chars")
                            print(f"   Preview: {msg_text[:100]}...")
                            return True
                        
        else:
            print("   ⚠️ Chatbot window not visible")
            
    except Exception as e:
        print(f"   ⚠️ Chatbot test error: {e}")
    
    return False


def test_sentiment_sources():
    """Test sentiment data sources (non-browser)"""
    print("\n" + "="*60)
    print("🧪 TEST 3: SENTIMENT SOURCES")
    print("="*60)
    
    results = {}
    
    # Test Finnhub
    print("\n1. Testing Finnhub sentiment...")
    try:
        from services.cc.ingest_finnhub import get_market_sentiment
        result = get_market_sentiment()
        if result.get('error') is None:
            print(f"   ✅ Finnhub: {result['score']:.3f}")
            results['finnhub'] = True
        else:
            print(f"   ⚠️ Finnhub: {result.get('error')}")
            results['finnhub'] = False
    except Exception as e:
        print(f"   ❌ Finnhub: {e}")
        results['finnhub'] = False
    
    # Test Alpaca
    print("\n2. Testing Alpaca sentiment...")
    try:
        from services.cc.alpaca_market import get_market_sentiment
        result = get_market_sentiment()
        if result.get('error') is None:
            print(f"   ✅ Alpaca: {result['score']:.3f}")
            results['alpaca'] = True
        else:
            print(f"   ⚠️ Alpaca: {result.get('error')}")
            results['alpaca'] = False
    except Exception as e:
        print(f"   ❌ Alpaca: {e}")
        results['alpaca'] = False
    
    # Test FinBERT
    print("\n3. Testing FinBERT sentiment...")
    try:
        from financial_dashboard.models.finbert_sentiment import FinBERTSentimentAnalyzer
        analyzer = FinBERTSentimentAnalyzer()
        result = analyzer.get_ticker_sentiment("AAPL")
        print(f"   ✅ FinBERT: {result['sentiment_mean']:.3f} ({result['signal']})")
        print(f"   Headlines analyzed: {result['sentiment_count']}")
        results['finbert'] = True
    except Exception as e:
        print(f"   ❌ FinBERT: {e}")
        results['finbert'] = False
    
    passed = sum(1 for v in results.values() if v)
    print(f"\n   Sentiment sources: {passed}/3 working")
    return passed >= 2


def main():
    print("\n" + "="*70)
    print("🚀 COMPREHENSIVE MARKET FORECAST & CHATBOT TEST")
    print("="*70)
    print(f"\nDashboard URL: {DASHBOARD_URL}")
    print(f"Screenshots: {SCREENSHOT_DIR}")
    
    results = {}
    
    # Test sentiment sources first (non-browser)
    results['sentiment'] = test_sentiment_sources()
    
    # Browser tests
    with sync_playwright() as p:
        print("\n📺 Launching Chromium (visible mode)...")
        browser = p.chromium.launch(
            headless=False,
            slow_mo=300,
            args=['--window-size=1600,900']
        )
        
        context = browser.new_context(viewport={'width': 1600, 'height': 900})
        page = context.new_page()
        
        # Capture console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        
        try:
            results['forecast'] = test_market_forecast(page)
            results['chatbot'] = test_chatbot(page)
            
        except Exception as e:
            print(f"\n❌ Test error: {e}")
            take_screenshot(page, "error")
        finally:
            # Report console errors
            if console_errors:
                print("\n" + "="*60)
                print("⚠️ CONSOLE ERRORS:")
                print("="*60)
                for err in console_errors[:5]:
                    print(f"   - {err[:100]}")
            
            print("\nClosing browser in 3 seconds...")
            time.sleep(3)
            browser.close()
    
    # Summary
    print("\n" + "="*70)
    print("📋 TEST SUMMARY")
    print("="*70)
    
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test}: {status}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    if passed == total:
        print(f"\n🎉 ALL {total} TESTS PASSED!")
    else:
        print(f"\n⚠️ {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

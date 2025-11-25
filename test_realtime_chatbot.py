"""
Test chatbot with real-time NVDA price after yfinance integration
"""
import asyncio
from playwright.async_api import async_playwright

async def test_realtime_chatbot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1200})
        
        # Clear all cache and cookies
        await context.clear_cookies()
        
        page = await context.new_page()
        
        print("=" * 80)
        print("TESTING CHATBOT WITH REAL-TIME DATA")
        print("=" * 80)
        
        # Load dashboard with cache bypass
        print("\n[1/5] Loading dashboard (cache bypass)...")
        await page.goto('http://localhost:8051?t=' + str(asyncio.get_event_loop().time()), timeout=15000, wait_until='networkidle')
        await page.wait_for_timeout(5000)
        
        # Open chatbot
        print("\n[2/5] Opening chatbot...")
        await page.click('#chatbot-toggle-btn', timeout=5000)
        await page.wait_for_selector('#chatbot-window', state='visible', timeout=5000)
        await page.wait_for_timeout(2000)
        
        # Test NVDA price
        print("\n[3/5] Asking for NVDA current price...")
        await page.fill('#chatbot-input', 'What is the current price of NVDA stock?')
        await page.click('#chatbot-send-btn')
        await page.wait_for_timeout(15000)  # Wait for LLM + yfinance
        
        # Capture response
        await page.screenshot(path='/home/aarav/unified-dashboard/REALTIME_chatbot_nvda.png')
        
        # Get response text
        chatbot_text = await page.evaluate("() => document.querySelector('#chatbot-messages').innerText")
        print(f"\nChatbot response:")
        print(chatbot_text)
        
        # Check for indicators of real-time data
        has_old_price = "$5.64" in chatbot_text or "August 2021" in chatbot_text
        has_recent_data = "2024" in chatbot_text or "2025" in chatbot_text or "$" in chatbot_text
        
        print(f"\n✓ Has old price ($5.64 or Aug 2021): {has_old_price} (should be False)")
        print(f"✓ Has recent data (2024/2025 or $): {has_recent_data} (should be True)")
        
        # Test another stock
        print("\n[4/5] Asking for AAPL price...")
        await page.fill('#chatbot-input', 'What is AAPL trading at right now?')
        await page.click('#chatbot-send-btn')
        await page.wait_for_timeout(15000)
        
        await page.screenshot(path='/home/aarav/unified-dashboard/REALTIME_chatbot_aapl.png')
        
        # Final screenshot
        print("\n[5/5] Capturing final state...")
        await page.screenshot(path='/home/aarav/unified-dashboard/REALTIME_final.png', full_page=True)
        
        await browser.close()
        
        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)
        print(f"Real-time data working: {not has_old_price and has_recent_data}")

if __name__ == '__main__':
    asyncio.run(test_realtime_chatbot())

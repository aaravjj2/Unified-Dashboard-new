"""
Test chatbot UI and functionality with proper waits
"""
import asyncio
from playwright.async_api import async_playwright

async def test_chatbot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("=" * 70)
        print("CHATBOT UI TEST")
        print("=" * 70)
        
        # Load dashboard
        print("\n[1/5] Loading dashboard...")
        await page.goto('http://localhost:8051', timeout=15000)
        await page.wait_for_selector('text=Financial Dashboard', timeout=10000)
        await page.wait_for_timeout(3000)
        print("✓ Dashboard loaded")
        
        # Open chatbot
        print("\n[2/5] Opening chatbot...")
        await page.evaluate("document.getElementById('chatbot-toggle-btn').click()")
        await page.wait_for_selector('#chatbot-window', state='visible', timeout=5000)
        await page.wait_for_timeout(2000)  # Extra wait for animations
        print("✓ Chatbot opened")
        
        # Check if input field is visible
        print("\n[3/5] Checking input field...")
        input_visible = await page.is_visible('#chatbot-input')
        print(f"✓ Input field visible: {input_visible}")
        
        if not input_visible:
            # Try to find what's wrong
            chatbot_html = await page.locator('#chatbot-window').inner_html()
            print(f"Chatbot HTML length: {len(chatbot_html)} chars")
            
            # Check if input exists in DOM
            input_exists = await page.locator('#chatbot-input').count()
            print(f"Input field exists in DOM: {input_exists > 0}")
        
        # Take screenshot before sending message
        await page.screenshot(path='/home/aarav/unified-dashboard/chatbot_before_message.png', full_page=True)
        print("✓ Screenshot saved: chatbot_before_message.png")
        
        # Send a test message
        print("\n[4/5] Sending test message...")
        test_message = "What is the price of AAPL?"
        
        # Try to fill input
        try:
            await page.fill('#chatbot-input', test_message)
            await page.click('#chatbot-send-btn')
            print(f"✓ Sent message: '{test_message}'")
            
            # Wait for response (LLM takes time)
            print("⏳ Waiting for LLM response (up to 15 seconds)...")
            await page.wait_for_timeout(15000)
            
            # Count messages
            messages = await page.locator('#chatbot-messages .card').count()
            print(f"✓ Total message bubbles: {messages}")
            
        except Exception as e:
            print(f"✗ Error sending message: {e}")
        
        # Take final screenshot
        print("\n[5/5] Capturing final state...")
        chatbot_window = page.locator('#chatbot-window')
        await chatbot_window.screenshot(path='/home/aarav/unified-dashboard/chatbot_after_message.png')
        await page.screenshot(path='/home/aarav/unified-dashboard/chatbot_full_page.png', full_page=True)
        print("✓ Screenshots saved")
        
        await browser.close()
        
        print("\n" + "=" * 70)
        print("TEST COMPLETE")
        print("=" * 70)
        print("\nScreenshots:")
        print("  - chatbot_before_message.png")
        print("  - chatbot_after_message.png")
        print("  - chatbot_full_page.png")

if __name__ == '__main__':
    asyncio.run(test_chatbot())

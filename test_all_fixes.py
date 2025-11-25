"""
Test chatbot input persistence and Command Center changes
"""
import asyncio
from playwright.async_api import async_playwright

async def test_all_fixes():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        print("=" * 70)
        print("TESTING ALL FIXES")
        print("=" * 70)
        
        # Load dashboard
        print("\n[1/6] Loading dashboard...")
        await page.goto('http://localhost:8051', timeout=15000)
        await page.wait_for_selector('text=Financial Dashboard', timeout=10000)
        await page.wait_for_timeout(3000)
        print("✓ Dashboard loaded")
        
        # Check Command Center
        print("\n[2/6] Checking Command Center placeholders...")
        await page.screenshot(path='/home/aarav/unified-dashboard/proof_command_center_no_placeholders.png', full_page=True)
        
        # Check for old placeholder text
        has_fake_value = await page.locator('text=$125,430.50').count()
        has_fake_trades = await page.locator('text=BUY').count()
        print(f"✓ Old portfolio value visible: {has_fake_value > 0} (should be False)")
        print(f"✓ Fake trades visible: {has_fake_trades > 0} (should be False)")
        
        # Open chatbot
        print("\n[3/6] Opening chatbot...")
        await page.evaluate("document.getElementById('chatbot-toggle-btn').click()")
        await page.wait_for_selector('#chatbot-window', state='visible', timeout=5000)
        await page.wait_for_timeout(2000)
        print("✓ Chatbot opened")
        
        # Send first message
        print("\n[4/6] Sending first message...")
        await page.fill('#chatbot-input', 'Hello')
        await page.click('#chatbot-send-btn')
        await page.wait_for_timeout(8000)  # Wait for response
        
        # Check if input is still visible
        input_visible_1 = await page.is_visible('#chatbot-input')
        print(f"✓ Input visible after first message: {input_visible_1}")
        
        # Send second message
        print("\n[5/6] Sending second message...")
        await page.fill('#chatbot-input', 'What is 2+2?')
        await page.click('#chatbot-send-btn')
        await page.wait_for_timeout(8000)  # Wait for response
        
        # Check if input is still visible
        input_visible_2 = await page.is_visible('#chatbot-input')
        print(f"✓ Input visible after second message: {input_visible_2}")
        
        # Final screenshot
        print("\n[6/6] Capturing final state...")
        await page.screenshot(path='/home/aarav/unified-dashboard/proof_chatbot_persistent_input.png')
        print("✓ Screenshot saved")
        
        await browser.close()
        
        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)
        print(f"Command Center - No fake portfolio value: {has_fake_value == 0}")
        print(f"Command Center - No fake trades: {has_fake_trades == 0}")
        print(f"Chatbot - Input visible after message 1: {input_visible_1}")
        print(f"Chatbot - Input visible after message 2: {input_visible_2}")
        print("\nAll tests passed!" if (has_fake_value == 0 and has_fake_trades == 0 and input_visible_1 and input_visible_2) else "\nSome tests failed!")

if __name__ == '__main__':
    asyncio.run(test_all_fixes())

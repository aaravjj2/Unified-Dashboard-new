"""
Final comprehensive test - Command Center rebuild + chatbot date fix
"""
import asyncio
from playwright.async_api import async_playwright

async def final_comprehensive_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1200})
        await context.clear_cookies()
        
        page = await context.new_page()
        
        print("=" * 80)
        print("FINAL COMPREHENSIVE TEST - Command Center Rebuild + Chatbot Date")
        print("=" * 80)
        
        # Load dashboard
        print("\n[1/5] Loading dashboard with rebuilt Command Center...")
        await page.goto('http://localhost:8051', timeout=15000, wait_until='networkidle')
        await page.wait_for_timeout(5000)
        
        # Capture Command Center (should be home.py now)
        print("\n[2/5] Capturing Command Center (home.py)...")
        await page.screenshot(path='/home/aarav/unified-dashboard/REBUILT_command_center.png', full_page=True)
        
        # Check for placeholders
        page_text = await page.evaluate("() => document.body.innerText")
        has_loading = "Loading..." in page_text
        has_dashes = "--" in page_text
        has_old_errors = "Connection refused" in page_text or "[Errno 111]" in page_text
        
        print(f"  ✓ Has 'Loading...': {has_loading}")
        print(f"  ✓ Has '--' placeholders: {has_dashes}")
        print(f"  ✓ Has old errors: {has_old_errors} (should be False)")
        
        # Open chatbot and test date
        print("\n[3/5] Testing chatbot with current date...")
        await page.click('#chatbot-toggle-btn', timeout=5000)
        await page.wait_for_selector('#chatbot-window', state='visible', timeout=5000)
        await page.wait_for_timeout(2000)
        
        # Ask for NVDA price
        await page.fill('#chatbot-input', 'What is the current price of NVDA?')
        await page.click('#chatbot-send-btn')
        await page.wait_for_timeout(15000)
        
        # Capture chatbot response
        await page.screenshot(path='/home/aarav/unified-dashboard/REBUILT_chatbot_date.png')
        
        # Get chatbot text
        chatbot_text = await page.evaluate("() => document.querySelector('#chatbot-messages').innerText")
        print(f"\nChatbot response preview:")
        print(chatbot_text[-600:] if len(chatbot_text) > 600 else chatbot_text)
        
        # Check for correct date
        has_nov_2024 = "November" in chatbot_text and "2024" in chatbot_text
        has_old_date = "January 27, 2023" in chatbot_text or "Jan" in chatbot_text and "2023" in chatbot_text
        
        print(f"\n  ✓ Has November 2024: {has_nov_2024} (should be True)")
        print(f"  ✓ Has old date (Jan 2023): {has_old_date} (should be False)")
        
        # Test another query
        print("\n[4/5] Testing second query...")
        await page.fill('#chatbot-input', 'What is AAPL stock price today?')
        await page.click('#chatbot-send-btn')
        await page.wait_for_timeout(15000)
        
        await page.screenshot(path='/home/aarav/unified-dashboard/REBUILT_chatbot_aapl.png')
        
        # Final screenshot
        print("\n[5/5] Capturing final state...")
        await page.screenshot(path='/home/aarav/unified-dashboard/REBUILT_final.png', full_page=True)
        
        await browser.close()
        
        print("\n" + "=" * 80)
        print("TEST RESULTS")
        print("=" * 80)
        print(f"Command Center: {'✅ CLEAN' if not has_old_errors else '❌ HAS ERRORS'}")
        print(f"Chatbot Date: {'✅ CURRENT (Nov 2024)' if has_nov_2024 and not has_old_date else '❌ OLD DATE'}")
        print("\nScreenshots saved:")
        print("  - REBUILT_command_center.png")
        print("  - REBUILT_chatbot_date.png")
        print("  - REBUILT_chatbot_aapl.png")
        print("  - REBUILT_final.png")

if __name__ == '__main__':
    asyncio.run(final_comprehensive_test())

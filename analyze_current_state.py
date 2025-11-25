"""
Capture current Command Center state and test chatbot with NVDA price query
"""
import asyncio
from playwright.async_api import async_playwright

async def analyze_current_state():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1200})
        
        print("=" * 80)
        print("ANALYZING CURRENT STATE")
        print("=" * 80)
        
        # Load dashboard
        print("\n[1/4] Loading dashboard...")
        await page.goto('http://localhost:8051', timeout=15000, wait_until='networkidle')
        await page.wait_for_timeout(5000)
        
        # Capture Command Center
        print("\n[2/4] Capturing Command Center current state...")
        await page.screenshot(path='/home/aarav/unified-dashboard/CURRENT_command_center.png', full_page=True)
        
        # Get all text
        page_text = await page.evaluate("() => document.body.innerText")
        print(f"\nCommand Center contains:")
        print(f"  - 'Connection refused': {'Connection refused' in page_text}")
        print(f"  - '[Errno 111]': {'[Errno 111]' in page_text}")
        print(f"  - 'Error:': {'Error:' in page_text}")
        print(f"  - 'unavailable': {'unavailable' in page_text.lower()}")
        
        # Open chatbot and test NVDA price
        print("\n[3/4] Testing chatbot with NVDA price query...")
        try:
            await page.click('#chatbot-toggle-btn', timeout=5000)
            await page.wait_for_selector('#chatbot-window', state='visible', timeout=5000)
            await page.wait_for_timeout(2000)
            
            # Ask for NVDA price
            await page.fill('#chatbot-input', 'What is the current price of NVDA?')
            await page.click('#chatbot-send-btn')
            await page.wait_for_timeout(12000)
            
            # Capture chatbot response
            await page.screenshot(path='/home/aarav/unified-dashboard/CURRENT_chatbot_nvda.png')
            
            # Get chatbot response text
            chatbot_text = await page.evaluate("() => document.querySelector('#chatbot-messages').innerText")
            print(f"\nChatbot response preview:")
            print(chatbot_text[-500:] if len(chatbot_text) > 500 else chatbot_text)
            
        except Exception as e:
            print(f"  Error testing chatbot: {e}")
        
        # Final screenshot
        print("\n[4/4] Capturing final state...")
        await page.screenshot(path='/home/aarav/unified-dashboard/CURRENT_full_state.png', full_page=True)
        
        await browser.close()
        
        print("\n" + "=" * 80)
        print("SCREENSHOTS SAVED")
        print("=" * 80)
        print("  - CURRENT_command_center.png")
        print("  - CURRENT_chatbot_nvda.png")
        print("  - CURRENT_full_state.png")

if __name__ == '__main__':
    asyncio.run(analyze_current_state())

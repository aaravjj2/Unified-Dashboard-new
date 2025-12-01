"""
Capture comprehensive proof screenshots of chatbot working
"""
import asyncio
from playwright.async_api import async_playwright

async def capture_chatbot_proof():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        print("=" * 70)
        print("CHATBOT PROOF CAPTURE")
        print("=" * 70)
        
        # Load dashboard
        print("\n[1/6] Loading dashboard...")
        await page.goto('http://localhost:8051', timeout=15000)
        await page.wait_for_selector('text=Financial Dashboard', timeout=10000)
        await page.wait_for_timeout(3000)
        print("✓ Dashboard loaded")
        
        # Open chatbot
        print("\n[2/6] Opening chatbot...")
        await page.evaluate("document.getElementById('chatbot-toggle-btn').click()")
        await page.wait_for_selector('#chatbot-window', state='visible', timeout=5000)
        await page.wait_for_timeout(2000)
        print("✓ Chatbot opened")
        
        # Screenshot 1: Chatbot open with welcome message
        await page.screenshot(path='/home/aarav/unified-dashboard/proof_chatbot_1_open.png')
        print("✓ Screenshot 1: Chatbot open")
        
        # Send first message
        print("\n[3/6] Sending first message...")
        await page.fill('#chatbot-input', 'Hello, what can you help me with?')
        await page.click('#chatbot-send-btn')
        await page.wait_for_timeout(8000)  # Wait for LLM
        
        # Screenshot 2: First interaction
        await page.screenshot(path='/home/aarav/unified-dashboard/proof_chatbot_2_first_msg.png')
        print("✓ Screenshot 2: First message response")
        
        # Send stock query
        print("\n[4/6] Sending stock query...")
        await page.fill('#chatbot-input', 'What is AAPL stock?')
        await page.click('#chatbot-send-btn')
        await page.wait_for_timeout(8000)  # Wait for LLM
        
        # Screenshot 3: Stock query
        await page.screenshot(path='/home/aarav/unified-dashboard/proof_chatbot_3_stock_query.png')
        print("✓ Screenshot 3: Stock query response")
        
        # Send math query
        print("\n[5/6] Sending math query...")
        await page.fill('#chatbot-input', 'Calculate 25 * 4')
        await page.click('#chatbot-send-btn')
        await page.wait_for_timeout(8000)  # Wait for LLM
        
        # Screenshot 4: Math query
        await page.screenshot(path='/home/aarav/unified-dashboard/proof_chatbot_4_math.png')
        print("✓ Screenshot 4: Math query response")
        
        # Final full page screenshot
        print("\n[6/6] Final full page screenshot...")
        await page.screenshot(path='/home/aarav/unified-dashboard/proof_chatbot_5_full.png', full_page=True)
        print("✓ Screenshot 5: Full page")
        
        await browser.close()
        
        print("\n" + "=" * 70)
        print("PROOF CAPTURE COMPLETE")
        print("=" * 70)
        print("\nScreenshots saved:")
        print("  - proof_chatbot_1_open.png")
        print("  - proof_chatbot_2_first_msg.png")
        print("  - proof_chatbot_3_stock_query.png")
        print("  - proof_chatbot_4_math.png")
        print("  - proof_chatbot_5_full.png")

if __name__ == '__main__':
    asyncio.run(capture_chatbot_proof())

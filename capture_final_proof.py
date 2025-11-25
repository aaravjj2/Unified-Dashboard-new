"""
Capture proof of chatbot input field and Command Center changes
"""
import asyncio
from playwright.async_api import async_playwright

async def capture_final_proof():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        print("=" * 70)
        print("FINAL PROOF CAPTURE - Chatbot Input & Command Center")
        print("=" * 70)
        
        # Load dashboard
        print("\n[1/5] Loading dashboard...")
        await page.goto('http://localhost:8051', timeout=15000)
        await page.wait_for_selector('text=Financial Dashboard', timeout=10000)
        await page.wait_for_timeout(3000)
        print("✓ Dashboard loaded")
        
        # Capture Command Center (Home tab)
        print("\n[2/5] Capturing Command Center...")
        await page.screenshot(path='/home/aarav/unified-dashboard/proof_command_center_final.png', full_page=True)
        print("✓ Command Center screenshot saved")
        
        # Open chatbot
        print("\n[3/5] Opening chatbot...")
        await page.evaluate("document.getElementById('chatbot-toggle-btn').click()")
        await page.wait_for_selector('#chatbot-window', state='visible', timeout=5000)
        await page.wait_for_timeout(2000)
        print("✓ Chatbot opened")
        
        # Check if input is visible
        input_visible = await page.is_visible('#chatbot-input')
        print(f"✓ Input field visible: {input_visible}")
        
        # Capture chatbot with input field
        print("\n[4/5] Capturing chatbot with input field...")
        await page.screenshot(path='/home/aarav/unified-dashboard/proof_chatbot_input_visible.png')
        print("✓ Chatbot screenshot saved")
        
        # Try to type in input
        if input_visible:
            print("\n[5/5] Testing input field...")
            await page.fill('#chatbot-input', 'Test message')
            await page.screenshot(path='/home/aarav/unified-dashboard/proof_chatbot_with_text.png')
            print("✓ Input field is functional!")
        
        await browser.close()
        
        print("\n" + "=" * 70)
        print("PROOF CAPTURE COMPLETE")
        print("=" * 70)
        print("\nScreenshots:")
        print("  - proof_command_center_final.png")
        print("  - proof_chatbot_input_visible.png")
        print("  - proof_chatbot_with_text.png")

if __name__ == '__main__':
    asyncio.run(capture_final_proof())

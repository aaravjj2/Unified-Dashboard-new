"""
Test Chatbot with LLM and capture screenshot
"""
import asyncio
from playwright.async_api import async_playwright

async def test_chatbot_llm():
    async with async_playwright() as p:
        # Launch headless
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("🌐 Loading dashboard...")
        await page.goto('http://localhost:8051')
        await page.wait_for_selector('text=Financial Dashboard', timeout=10000)
        
        # Wait for JS fixes
        await page.wait_for_timeout(3000)
        
        # Open Chatbot
        print("💬 Opening Chatbot...")
        # The FAB might be hidden or z-indexed, let's force click it
        await page.evaluate("document.getElementById('chatbot-toggle-btn').click()")
        await page.wait_for_selector('#chatbot-window', state='visible')
        
        # Send Message
        print("📤 Sending message: 'What is the capital of France?'")
        await page.fill('#chatbot-input', 'What is the capital of France?')
        await page.click('#chatbot-send-btn')
        
        # Wait for response (LLM might take a few seconds)
        print("⏳ Waiting for LLM response...")
        # Wait for a bubble that is NOT from the user
        await page.wait_for_selector('#chatbot-messages .card-body > div:last-child', timeout=15000)
        await page.wait_for_timeout(5000) # Extra wait for text to render
        
        # Take screenshot of the chatbot window
        print("📸 Taking screenshot...")
        chatbot_window = page.locator('#chatbot-window')
        await chatbot_window.screenshot(path='/home/aarav/unified-dashboard/chatbot_llm_proof.png')
        
        # Also full page
        await page.screenshot(path='/home/aarav/unified-dashboard/dashboard_full_proof.png')
        
        print("✅ Screenshots saved to:")
        print("  - /home/aarav/unified-dashboard/chatbot_llm_proof.png")
        print("  - /home/aarav/unified-dashboard/dashboard_full_proof.png")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_chatbot_llm())

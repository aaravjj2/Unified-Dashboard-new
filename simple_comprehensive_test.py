"""
Simplified comprehensive test - screenshot analysis + chatbot financial testing
"""
import asyncio
from playwright.async_api import async_playwright

async def simple_comprehensive_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1200})
        
        print("=" * 80)
        print("COMPREHENSIVE TEST - Screenshots + Chatbot Financial Questions")
        print("=" * 80)
        
        # Load dashboard
        print("\n[1/8] Loading dashboard...")
        await page.goto('http://localhost:8051', timeout=15000, wait_until='networkidle')
        await page.wait_for_timeout(5000)
        print("✓ Dashboard loaded")
        
        # Capture initial state
        print("\n[2/8] Capturing Command Center (Home tab)...")
        await page.screenshot(path='/home/aarav/unified-dashboard/analysis_home_tab.png', full_page=True)
        
        # Get page text content for analysis
        page_text = await page.evaluate("() => document.body.innerText")
        print(f"✓ Page contains '$125,430.50': {'$125,430.50' in page_text}")
        print(f"✓ Page contains 'Loading...': {'Loading...' in page_text}")
        print(f"✓ Page contains 'Service Offline': {'Service Offline' in page_text}")
        
        # Open chatbot
        print("\n[3/8] Opening chatbot...")
        try:
            await page.click('#chatbot-toggle-btn', timeout=5000)
            await page.wait_for_selector('#chatbot-window', state='visible', timeout=5000)
            await page.wait_for_timeout(2000)
            print("✓ Chatbot opened")
        except Exception as e:
            print(f"✗ Failed to open chatbot: {e}")
            await page.screenshot(path='/home/aarav/unified-dashboard/error_chatbot_not_found.png')
            await browser.close()
            return
        
        # Financial Question 1: Portfolio
        print("\n[4/8] Q1: Portfolio value...")
        await page.fill('#chatbot-input', 'What is my current portfolio value and positions?')
        await page.click('#chatbot-send-btn')
        await page.wait_for_timeout(12000)
        await page.screenshot(path='/home/aarav/unified-dashboard/chatbot_financial_q1.png')
        
        # Financial Question 2: Stock Price
        print("\n[5/8] Q2: Stock price...")
        await page.fill('#chatbot-input', 'What is the current price of AAPL and TSLA?')
        await page.click('#chatbot-send-btn')
        await page.wait_for_timeout(12000)
        await page.screenshot(path='/home/aarav/unified-dashboard/chatbot_financial_q2.png')
        
        # Financial Question 3: News
        print("\n[6/8] Q3: Latest news...")
        await page.fill('#chatbot-input', 'What is the latest news about NVDA?')
        await page.click('#chatbot-send-btn')
        await page.wait_for_timeout(12000)
        await page.screenshot(path='/home/aarav/unified-dashboard/chatbot_financial_q3.png')
        
        # Financial Question 4: Market Analysis
        print("\n[7/8] Q4: Market analysis...")
        await page.fill('#chatbot-input', 'Analyze the tech sector performance today')
        await page.click('#chatbot-send-btn')
        await page.wait_for_timeout(12000)
        await page.screenshot(path='/home/aarav/unified-dashboard/chatbot_financial_q4.png')
        
        # Final screenshot
        print("\n[8/8] Final comprehensive screenshot...")
        await page.screenshot(path='/home/aarav/unified-dashboard/final_analysis.png', full_page=True)
        
        await browser.close()
        
        print("\n" + "=" * 80)
        print("TEST COMPLETE - Screenshots saved for analysis")
        print("=" * 80)
        print("\nScreenshots:")
        print("  1. analysis_home_tab.png - Command Center initial state")
        print("  2. chatbot_financial_q1.png - Portfolio question")
        print("  3. chatbot_financial_q2.png - Stock prices")
        print("  4. chatbot_financial_q3.png - News query")
        print("  5. chatbot_financial_q4.png - Market analysis")
        print("  6. final_analysis.png - Complete final state")

if __name__ == '__main__':
    asyncio.run(simple_comprehensive_test())

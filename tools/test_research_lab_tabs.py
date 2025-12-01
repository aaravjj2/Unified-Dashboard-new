#!/usr/bin/env python3
"""
Test Research Lab tabs callback firing
"""
import asyncio
from playwright.async_api import async_playwright
import sys

async def test_research_lab_tabs():
    """Test if Research Lab subtabs callback fires"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        console_messages = []
        page.on('console', lambda msg: console_messages.append(f"{msg.type}: {msg.text}"))
        
        print("🌐 Loading dashboard...")
        await page.goto('http://localhost:8090', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(2)
        
        print("📋 Clicking Research Lab tab...")
        await page.get_by_text('Research Lab', exact=False).first.click()
        await asyncio.sleep(2)
        
        # Check initial state
        content_div = page.locator('#research-lab-content')
        initial_html = await content_div.inner_html()
        print(f"\n📊 Initial research-lab-content HTML length: {len(initial_html)} chars")
        print(f"Initial content preview: {initial_html[:200]}")
        
        # Try clicking subtabs
        subtabs = ['Market Scan', 'Factor Analysis', 'Correlation Explorer', 'Strategy Backtest', 'Research Notes']
        
        for subtab in subtabs:
            print(f"\n🔍 Testing subtab: {subtab}")
            try:
                # Click subtab
                await page.get_by_text(subtab, exact=False).click()
                await asyncio.sleep(1)
                
                # Check content
                new_html = await content_div.inner_html()
                print(f"  Content length after click: {len(new_html)} chars")
                
                if len(new_html) > 50:
                    print(f"  ✅ Content loaded: {new_html[:100]}")
                else:
                    print(f"  ❌ Content still empty or minimal")
                    
            except Exception as e:
                print(f"  ❌ Error clicking {subtab}: {e}")
        
        # Check console errors
        print(f"\n📊 Total console messages: {len(console_messages)}")
        errors = [msg for msg in console_messages if 'error' in msg.lower()]
        print(f"📊 Console errors: {len(errors)}")
        
        if errors:
            print("\n🔴 Recent console errors:")
            for err in errors[-10:]:
                print(f"  {err}")
        
        print("\n👁️ Browser staying open for 30 seconds...")
        await asyncio.sleep(30)
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_research_lab_tabs())

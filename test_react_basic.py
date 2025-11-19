#!/usr/bin/env python3
"""
Test basic React functionality
"""
import asyncio
from playwright.async_api import async_playwright

async def test_react():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("🔍 Testing React functionality...")
        
        # Navigate to dashboard
        await page.goto("http://localhost:8051", wait_until="networkidle", timeout=30000)
        
        # Wait for React to load
        await page.wait_for_timeout(10000)
        
        # Check if React loaded
        react_loaded = await page.evaluate("() => window.React !== undefined")
        print(f"📋 React loaded: {react_loaded}")
        
        # Check if Dash renderer loaded
        dash_loaded = await page.evaluate("() => window.dash_renderer !== undefined")
        print(f"📋 Dash renderer loaded: {dash_loaded}")
        
        # Check current page content
        content = await page.content()
        
        if "_dash-loading" in content:
            print("❌ Page stuck in loading state")
        else:
            print("✅ Page loaded successfully")
        
        # Check for any JavaScript errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        
        await page.wait_for_timeout(2000)
        
        if console_errors:
            print(f"❌ JavaScript errors found: {len(console_errors)}")
            for error in console_errors[:5]:
                print(f"  - {error}")
        else:
            print("✅ No JavaScript errors")
        
        # Try to manually trigger React render
        try:
            result = await page.evaluate("""
                () => {
                    if (window.dash_renderer && window.dash_renderer.render) {
                        window.dash_renderer.render();
                        return 'render_called';
                    }
                    return 'no_renderer';
                }
            """)
            print(f"📋 Manual render result: {result}")
        except Exception as e:
            print(f"❌ Manual render failed: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_react())
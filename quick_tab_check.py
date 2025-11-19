#!/usr/bin/env python3
"""
Quick tab visibility check
"""
import asyncio
from playwright.async_api import async_playwright

async def check_tabs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("🔍 Loading dashboard...")
        await page.goto("http://localhost:8051", wait_until="networkidle", timeout=30000)
        
        # Wait a bit for everything to load
        await page.wait_for_timeout(5000)
        
        # Take screenshot
        await page.screenshot(path="dashboard_current_state.png", full_page=True)
        
        # Check for tabs
        tabs = await page.locator('[role="tab"]').all()
        print(f"📋 Found {len(tabs)} tabs with role='tab'")
        
        # Check for dbc.Tab elements
        dbc_tabs = await page.locator('.nav-link').all()
        print(f"📋 Found {len(dbc_tabs)} elements with class 'nav-link'")
        
        # Check for any tab-like elements
        tab_elements = await page.locator('a[href*="tab"], button[role="tab"], .tab, .nav-item').all()
        print(f"📋 Found {len(tab_elements)} tab-like elements")
        
        # Get page content to check for tab names
        content = await page.content()
        tab_names = ['Command Center', 'Research Lab', 'Strategy Lab', 'Options Lab', 'Weekly Picks', 'Monthly Picks']
        
        for name in tab_names:
            if name in content:
                print(f"✅ Found '{name}' in page content")
            else:
                print(f"❌ Missing '{name}' from page content")
        
        # Check console logs
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))
        
        await page.wait_for_timeout(2000)
        
        print(f"\n📋 Console logs ({len(console_logs)} total):")
        for log in console_logs[-10:]:  # Show last 10
            print(f"  {log}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_tabs())
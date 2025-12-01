#!/usr/bin/env python3
"""Quick Playwright diagnostic"""

import asyncio
from playwright.async_api import async_playwright

async def test_playwright():
    print("1. Initializing Playwright...")
    async with async_playwright() as p:
        print("2. Launching Chromium...")
        browser = await p.chromium.launch(headless=True)
        print("3. Creating page...")
        page = await browser.new_page()
        print("4. Navigating to dashboard...")
        await page.goto("http://localhost:8051", timeout=30000)
        print("5. Getting title...")
        title = await page.title()
        print(f"✅ Dashboard title: {title}")
        await browser.close()
        print("✅ Playwright test complete!")

if __name__ == "__main__":
    asyncio.run(test_playwright())

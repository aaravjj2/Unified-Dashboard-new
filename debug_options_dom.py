#!/usr/bin/env python3
"""
Debug Options Lab DOM structure
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto("http://localhost:8051")
        await page.wait_for_timeout(5000)
        
        # Click Options Lab
        await page.click("text=Options Lab")
        await page.wait_for_timeout(3000)
        
        # Get page HTML
        html = await page.content()
        
        # Find all elements with 'options' in their ID
        options_elements = await page.evaluate('''() => {
            const elements = document.querySelectorAll('[id*="options"], [id*="ol-"]');
            return Array.from(elements).map(el => ({
                tag: el.tagName,
                id: el.id,
                class: el.className,
                text: el.innerText?.substring(0, 50)
            })).slice(0, 30);
        }''')
        
        print("Elements with 'options' or 'ol-' in ID:")
        for el in options_elements:
            print(f"  {el['tag']}: #{el['id']} - {el.get('text', '')[:30]}")
        
        # Find tabs
        tabs = await page.evaluate('''() => {
            const tabs = document.querySelectorAll('.nav-tabs .nav-link, [role="tab"]');
            return Array.from(tabs).map(el => ({
                tag: el.tagName,
                id: el.id,
                text: el.innerText,
                parent: el.parentElement?.id || el.parentElement?.className
            })).slice(0, 20);
        }''')
        
        print("\nTabs found:")
        for tab in tabs:
            print(f"  {tab['text'][:30]} - parent: {tab.get('parent', 'N/A')[:30]}")
        
        await browser.close()


asyncio.run(main())

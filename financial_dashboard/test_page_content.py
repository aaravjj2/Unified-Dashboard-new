#!/usr/bin/env python3
"""
Check what's actually rendering on the page
"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto('http://localhost:8000/', wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)
        
        # Get all visible text
        body_text = await page.text_content('body')
        print("BODY TEXT:")
        print("=" * 80)
        print(body_text[:2000])
        print("=" * 80)
        
        # Get HTML structure
        html = await page.content()
        with open('/mnt/c/Aarav/fin_env/Dash/test_page_structure.html', 'w') as f:
            f.write(html)
        print("\nFull HTML saved to: test_page_structure.html")
        
        # Check for any error divs
        errors = await page.query_selector_all('.dash-error, .error, [class*="error"]')
        print(f"\nFound {len(errors)} error elements")
        
        # Check what divs exist
        all_divs = await page.query_selector_all('div[id]')
        print(f"\nFound {len(all_divs)} divs with IDs:")
        for div in all_divs[:20]:
            div_id = await div.get_attribute('id')
            print(f"  - {div_id}")
        
        await browser.close()

asyncio.run(main())

#!/usr/bin/env python3
"""Quick console error count check"""
import asyncio
from playwright.async_api import async_playwright

async def check_errors():
    errors = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        page.on('console', lambda msg: errors.append(msg) if msg.type == 'error' else None)
        
        print("Loading dashboard...")
        await page.goto('http://localhost:8051', wait_until='networkidle', timeout=60000)
        
        print("Waiting 15 seconds...")
        await asyncio.sleep(15)
        
        print(f"\n{'='*80}")
        print(f"✨ ERROR COUNT: {len(errors)}")
        print(f"{'='*80}\n")
        
        if len(errors) > 0:
            print("Sample errors:")
            for i, err in enumerate(errors[:5], 1):
                print(f"{i}. {err.text[:150]}")
        else:
            print("🎉 NO CONSOLE ERRORS! Dashboard is clean!")
        
        print("\nBrowser will stay open for 20 seconds for inspection...")
        await asyncio.sleep(20)
        await browser.close()
    
    return len(errors)

if __name__ == '__main__':
    count = asyncio.run(check_errors())
    print(f"\nFinal count: {count} errors")

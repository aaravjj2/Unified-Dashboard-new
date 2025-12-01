#!/usr/bin/env python3
"""Quick console error capture from live dashboard."""
import asyncio
from playwright.async_api import async_playwright
import json


async def capture_console_errors():
    """Capture console errors from dashboard."""
    console_errors = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Capture console messages
        def handle_console(msg):
            if msg.type in ['error', 'warning']:
                console_errors.append({
                    'type': msg.type,
                    'text': msg.text,
                    'location': msg.location
                })
        
        page.on('console', handle_console)
        
        # Load dashboard
        await page.goto('http://localhost:8050', wait_until='networkidle', timeout=60000)
        await asyncio.sleep(5)
        
        await browser.close()
    
    # Filter for duplicate callback errors
    duplicate_errors = [e for e in console_errors if 'duplicate' in e['text'].lower()]
    
    print(f"Total console errors/warnings: {len(console_errors)}")
    print(f"Duplicate callback warnings: {len(duplicate_errors)}")
    
    if duplicate_errors:
        print("\nSample duplicate warnings:")
        for err in duplicate_errors[:5]:
            print(f"  [{err['type']}] {err['text'][:150]}")
    
    # Save to file
    with open('reports/duplicates_fix/diagnostics/runtime_console_errors.json', 'w') as f:
        json.dump({
            'total_errors': len(console_errors),
            'duplicate_warnings': len(duplicate_errors),
            'all_errors': console_errors,
            'duplicate_errors': duplicate_errors
        }, f, indent=2)
    
    print(f"\n✅ Saved to: reports/duplicates_fix/diagnostics/runtime_console_errors.json")


if __name__ == '__main__':
    asyncio.run(capture_console_errors())

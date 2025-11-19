#!/usr/bin/env python3
"""
Simple console error checker - just load Strategy Lab and capture console.
"""

import asyncio
from playwright.async_api import async_playwright
import json

async def check_console():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Capture all console messages
        console_msgs = []
        def handle_console(msg):
            console_msgs.append({
                "type": msg.type,
                "text": msg.text,
                "location": msg.location
            })
        
        page.on("console", handle_console)
        
        try:
            print("Loading dashboard...")
            await page.goto("http://localhost:8050", timeout=30000)
            await page.wait_for_timeout(3000)
            
            print("Clicking Strategy Lab...")
            await page.click("ul.nav a.nav-link:has-text('Strategy Lab')", timeout=10000)
            await page.wait_for_timeout(5000)  # Wait for all callbacks to register
            
            # Filter errors
            errors = [m for m in console_msgs if m["type"] == "error"]
            warnings = [m for m in console_msgs if m["type"] == "warning"]
            
            print(f"\n{'='*80}")
            print(f"CONSOLE ANALYSIS:")
            print(f"{'='*80}")
            print(f"Total messages: {len(console_msgs)}")
            print(f"Errors: {len(errors)}")
            print(f"Warnings: {len(warnings)}")
            
            if errors:
                print(f"\n❌ ERRORS FOUND:")
                for err in errors:
                    print(f"   • {err['text']}")
            else:
                print(f"\n✅ NO ERRORS - Strategy Lab callbacks fixed!")
            
            if warnings:
                print(f"\n⚠️  WARNINGS:")
                for warn in warnings[:10]:  # Limit to 10
                    print(f"   • {warn['text']}")
            
            # Save full log
            with open("strategy_lab_console.json", "w") as f:
                json.dump(console_msgs, f, indent=2)
            print(f"\nFull console log saved to: strategy_lab_console.json")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(check_console())

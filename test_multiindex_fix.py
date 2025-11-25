#!/usr/bin/env python3
"""Test MultiIndex data access fix for Strategy Lab backtest"""
import asyncio
import time
from playwright.async_api import async_playwright

async def test_backtest():
    print("🧪 Testing Strategy Lab Backtest - MultiIndex Fix\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            # Load dashboard
            print("1. Loading dashboard...")
            await page.goto('http://localhost:8050', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            # Go to Strategy Lab
            print("2. Opening Strategy Lab...")
            await page.click('a:has-text("Strategy Lab")')
            await asyncio.sleep(2)
            
            # Go to Execute tab
            print("3. Opening Execute & Configure tab...")
            await page.click('a:has-text("Execute & Configure")')
            await asyncio.sleep(2)
            
            # Trigger backtest
            print("4. Running backtest...")
            await page.click('#sl-execute-run-btn')
            print("   ⏳ Waiting 60s for backtest to complete...")
            await asyncio.sleep(60)
            
            print("\n✅ Test complete - Check logs with:")
            print("   docker logs dash_app 2>&1 | grep -A 30 'Running REAL backtest' | tail -40")
            
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(test_backtest())

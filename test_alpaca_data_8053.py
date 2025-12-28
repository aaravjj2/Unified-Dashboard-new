#!/usr/bin/env python3
"""
Full Alpaca Options Lab Data Loading Test - Port 8053
Tests actual data loading and table population
"""

import asyncio
import sys
from datetime import datetime
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8053"

async def test_data_loading():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        
        print("="*70)
        print("ALPACA OPTIONS DATA LOADING TEST")
        print("="*70)
        
        # Load page
        print("\n📍 Loading Alpaca UI...")
        await page.goto(BASE_URL, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(2000)
        
        # Screenshot initial state
        await page.screenshot(path='screenshots/alpaca_data_01_initial.png')
        print("   📸 Initial state captured")
        
        # Get current ticker value
        ticker_input = await page.query_selector('#alpaca-ticker-input')
        if ticker_input:
            value = await ticker_input.input_value()
            print(f"   Ticker value: {value}")
        
        # Check status message
        status = await page.query_selector('#alpaca-status-message')
        if status:
            status_text = await status.inner_text()
            print(f"   Status: {status_text[:100] if status_text else 'Empty'}")
        
        # Click load button
        load_btn = await page.query_selector('#alpaca-load-button')
        if load_btn:
            print("\n📍 Clicking Load Chain button...")
            await load_btn.click()
            
            # Wait for data to load (longer timeout for API calls)
            print("   Waiting for API response...")
            await page.wait_for_timeout(8000)
            
            # Screenshot after load
            await page.screenshot(path='screenshots/alpaca_data_02_after_load.png')
            print("   📸 After load state captured")
            
            # Check status message again
            status = await page.query_selector('#alpaca-status-message')
            if status:
                status_text = await status.inner_text()
                print(f"\n   📊 Status after load: {status_text}")
            
            # Check table container
            table = await page.query_selector('#alpaca-table-container')
            if table:
                html = await table.inner_html()
                print(f"   📊 Table container size: {len(html)} chars")
                
                # Check for actual table rows
                rows = await table.query_selector_all('tr')
                print(f"   📊 Table rows: {len(rows)}")
                
                if len(rows) > 0:
                    # Get first row content
                    first_row = await rows[0].inner_text() if rows else None
                    print(f"   📊 First row: {first_row[:100] if first_row else 'None'}...")
            
            # Check if header was updated
            header = await page.query_selector('#alpaca-header-container')
            if header:
                header_html = await header.inner_html()
                print(f"   📊 Header container: {len(header_html)} chars")
            
            # Check if expiration selector appeared
            exp_container = await page.query_selector('#alpaca-expiration-container')
            if exp_container:
                exp_html = await exp_container.inner_html()
                print(f"   📊 Expiration container: {len(exp_html)} chars")
                
                # Look for actual expiration selector
                exp_selector = await exp_container.query_selector('#alpaca-expiration-selector')
                if exp_selector:
                    print("   ✅ Expiration selector (alpaca-expiration-selector) found!")
                else:
                    print("   ⚠️ No expiration selector inside container")
        
        # Final screenshot
        await page.screenshot(path='screenshots/alpaca_data_03_final.png', full_page=True)
        print("   📸 Final state captured")
        
        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Console Errors: {len(errors)}")
        if errors:
            for err in errors[:5]:
                print(f"   ❌ {err[:100]}")
        
        await browser.close()
        
        return len(errors) == 0

if __name__ == "__main__":
    success = asyncio.run(test_data_loading())
    sys.exit(0 if success else 1)

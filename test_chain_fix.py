#!/usr/bin/env python3
"""Test that Chain & Greeks panel now receives data."""

from playwright.sync_api import sync_playwright
import time

def test_chain_viewer_fix():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        print("1️⃣ Loading dashboard...")
        page.goto('http://localhost:8053', wait_until='networkidle', timeout=30000)
        page.wait_for_timeout(2000)
        
        print("2️⃣ Clicking Strategy tab...")
        strategy_tab = page.locator('text=📊 Strategy Lab').first
        if strategy_tab.is_visible():
            strategy_tab.click()
            page.wait_for_timeout(1000)
            print("   ✅ Strategy tab clicked")
        
        print("3️⃣ Clicking Chain & Greeks subtab...")
        chain_subtab = page.locator('text=📈 Chain & Greeks').first
        if chain_subtab.is_visible():
            chain_subtab.click()
            page.wait_for_timeout(1000)
            print("   ✅ Chain subtab clicked")
        
        # Check initial state
        chain_container = page.locator('#chain-viewer-table-container')
        initial_content = chain_container.text_content() if chain_container.is_visible() else ""
        print(f"\n4️⃣ Initial chain viewer state:")
        print(f"   Content: {initial_content[:100]}...")
        
        print("\n5️⃣ Clicking Load Chain button...")
        load_btn = page.locator('#alpaca-load-button')
        if load_btn.is_visible():
            load_btn.click()
            print("   ✅ Load button clicked")
        
        # Wait for data to load
        print("\n6️⃣ Waiting for data to load...")
        page.wait_for_timeout(5000)
        
        # Check status message
        status = page.locator('#alpaca-status-message')
        status_text = status.text_content() if status.is_visible() else ""
        print(f"   Status: {status_text}")
        
        # Check chain viewer content AFTER load
        chain_container = page.locator('#chain-viewer-table-container')
        final_content = chain_container.text_content() if chain_container.is_visible() else ""
        print(f"\n7️⃣ Final chain viewer state:")
        print(f"   Content length: {len(final_content)} chars")
        print(f"   First 200 chars: {final_content[:200]}...")
        
        # Check if content changed
        content_changed = initial_content != final_content
        has_table_data = len(final_content) > 100 and "Click 'Load Chain'" not in final_content
        
        # Check stats
        calls_oi = page.locator('#chain-calls-oi').text_content()
        puts_oi = page.locator('#chain-puts-oi').text_content()
        pc_ratio = page.locator('#chain-pc-ratio').text_content()
        
        print(f"\n8️⃣ Stats:")
        print(f"   Calls OI: {calls_oi}")
        print(f"   Puts OI: {puts_oi}")
        print(f"   P/C Ratio: {pc_ratio}")
        
        # Take screenshot
        page.screenshot(path='chain_viewer_fix_proof.png', full_page=True)
        print(f"\n📸 Screenshot saved: chain_viewer_fix_proof.png")
        
        # Results
        print("\n" + "="*50)
        print("RESULTS:")
        print("="*50)
        
        if content_changed and has_table_data:
            print("✅ CHAIN VIEWER FIX WORKING!")
            print("   - Content changed after loading")
            print("   - Table data is present")
        else:
            print("❌ CHAIN VIEWER STILL NOT WORKING")
            print(f"   - Content changed: {content_changed}")
            print(f"   - Has table data: {has_table_data}")
        
        if calls_oi != "--" and puts_oi != "--":
            print("✅ Stats are populated!")
        else:
            print("❌ Stats not populated")
        
        browser.close()

if __name__ == "__main__":
    test_chain_viewer_fix()

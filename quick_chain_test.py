#!/usr/bin/env python3
"""Quick test for chain viewer fix."""

import sys
sys.stdout = open('/dev/null', 'w')
sys.stderr = open('/dev/null', 'w')

from playwright.sync_api import sync_playwright
import json

def test():
    results = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        page.goto('http://localhost:8053', wait_until='networkidle', timeout=30000)
        page.wait_for_timeout(2000)
        
        # Click Strategy tab
        strategy_tab = page.locator('text=📊 Strategy Lab').first
        if strategy_tab.is_visible():
            strategy_tab.click()
            page.wait_for_timeout(1000)
        
        # Click Chain & Greeks subtab
        chain_subtab = page.locator('text=📈 Chain & Greeks').first
        if chain_subtab.is_visible():
            chain_subtab.click()
            page.wait_for_timeout(1000)
        
        # Get initial content
        chain_container = page.locator('#chain-viewer-table-container')
        initial = chain_container.text_content() if chain_container.is_visible() else ""
        results['initial_content'] = initial[:100] if initial else "NOT FOUND"
        
        # Click Load
        load_btn = page.locator('#alpaca-load-button')
        if load_btn.is_visible():
            load_btn.click()
        
        page.wait_for_timeout(6000)
        
        # Get final content
        final = chain_container.text_content() if chain_container.is_visible() else ""
        results['final_content_len'] = len(final)
        results['has_table_data'] = len(final) > 100 and "Click 'Load Chain'" not in final
        results['content_changed'] = initial != final
        
        # Get stats
        results['calls_oi'] = page.locator('#chain-calls-oi').text_content()
        results['puts_oi'] = page.locator('#chain-puts-oi').text_content()
        results['pc_ratio'] = page.locator('#chain-pc-ratio').text_content()
        
        # Get status
        status = page.locator('#alpaca-status-message')
        results['status'] = status.text_content() if status.is_visible() else ""
        
        # Screenshot
        page.screenshot(path='chain_fix_proof.png', full_page=True)
        
        browser.close()
    
    return results

if __name__ == "__main__":
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    
    results = test()
    
    print("="*60)
    print("CHAIN VIEWER FIX TEST RESULTS")
    print("="*60)
    print(f"Initial content: {results.get('initial_content', 'N/A')}")
    print(f"Final content length: {results.get('final_content_len', 0)} chars")
    print(f"Content changed: {results.get('content_changed', False)}")
    print(f"Has table data: {results.get('has_table_data', False)}")
    print(f"Status: {results.get('status', 'N/A')}")
    print(f"Calls OI: {results.get('calls_oi', 'N/A')}")
    print(f"Puts OI: {results.get('puts_oi', 'N/A')}")
    print(f"P/C Ratio: {results.get('pc_ratio', 'N/A')}")
    print("="*60)
    
    if results.get('has_table_data') and results.get('calls_oi', '--') != '--':
        print("✅ CHAIN VIEWER FIX WORKING!")
    else:
        print("❌ CHAIN VIEWER STILL BROKEN")
    
    print("\n📸 Screenshot: chain_fix_proof.png")

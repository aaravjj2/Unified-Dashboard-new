#!/usr/bin/env python3
"""Debug script to find actual element IDs."""

from playwright.sync_api import sync_playwright
import time

def find_elements():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:8053/", timeout=30000)
        time.sleep(4)
        
        print("\n" + "="*60)
        print("ELEMENT ID DISCOVERY")
        print("="*60)
        
        # Get all elements with IDs
        elements_with_ids = page.eval_on_selector_all(
            "[id]",
            "elements => elements.map(el => ({id: el.id, tag: el.tagName, text: el.textContent?.slice(0, 50)}))"
        )
        
        print(f"\nFound {len(elements_with_ids)} elements with IDs:\n")
        
        # Group by pattern
        ai_elements = [e for e in elements_with_ids if 'ai' in e['id'].lower()]
        chart_elements = [e for e in elements_with_ids if 'chart' in e['id'].lower() or 'gex' in e['id'].lower() or 'vol' in e['id'].lower()]
        table_elements = [e for e in elements_with_ids if 'table' in e['id'].lower() or 'flow' in e['id'].lower()]
        position_elements = [e for e in elements_with_ids if 'position' in e['id'].lower()]
        status_elements = [e for e in elements_with_ids if 'status' in e['id'].lower() or 'system' in e['id'].lower()]
        
        print("🤖 AI-related elements:")
        for e in ai_elements[:15]:
            print(f"   #{e['id']}: {e['tag']}")
        
        print("\n📊 Chart-related elements:")
        for e in chart_elements[:15]:
            print(f"   #{e['id']}: {e['tag']}")
        
        print("\n📋 Table/Flow-related elements:")
        for e in table_elements[:15]:
            print(f"   #{e['id']}: {e['tag']}")
        
        print("\n💼 Position-related elements:")
        for e in position_elements[:15]:
            print(f"   #{e['id']}: {e['tag']}")
        
        print("\n🔧 Status/System elements:")
        for e in status_elements[:15]:
            print(f"   #{e['id']}: {e['tag']}")
        
        # Click on Strategy tab and check again
        print("\n--- After clicking Strategy tab ---")
        strategy_tab = page.locator("//div[contains(@class, 'tab') and contains(text(), 'Strategy')]").first
        if strategy_tab.count() > 0:
            strategy_tab.click()
            time.sleep(2)
            
            ai_elements_after = page.eval_on_selector_all(
                "[id*='ai-'], [id*='regime'], [id*='signals'], [id*='predictions']",
                "elements => elements.map(el => ({id: el.id, tag: el.tagName}))"
            )
            print("\n🤖 AI elements on Strategy tab:")
            for e in ai_elements_after:
                print(f"   #{e['id']}: {e['tag']}")
        
        # Click on Scanner tab
        print("\n--- After clicking Scanner tab ---")
        scanner_tab = page.locator("//div[contains(@class, 'tab') and contains(text(), 'Scanner')]").first
        if scanner_tab.count() > 0:
            scanner_tab.click()
            time.sleep(2)
            
            scanner_elements = page.eval_on_selector_all(
                "[id*='gex'], [id*='vol'], [id*='flow'], [id*='chart'], [id*='surface']",
                "elements => elements.map(el => ({id: el.id, tag: el.tagName}))"
            )
            print("\n📊 Scanner elements:")
            for e in scanner_elements:
                print(f"   #{e['id']}: {e['tag']}")
        
        browser.close()
        print("="*60)

if __name__ == "__main__":
    find_elements()

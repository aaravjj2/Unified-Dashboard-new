#!/usr/bin/env python3
"""Test that clicking tabs actually switches the visible content."""

from playwright.sync_api import sync_playwright
import time

URL = 'http://127.0.0.1:8000'

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # NOT headless so we can see
        page = browser.new_page()
        page.goto(URL, timeout=60000)
        time.sleep(4)  # Let it load
        
        # Check what's initially visible
        print("="*70)
        print("INITIAL STATE (should show Market Trends):")
        visible_text = page.evaluate("""
            () => {
                // Find the active tab pane
                const active = document.querySelector('.tab-pane.active');
                if (active) {
                    return active.innerText.substring(0, 200);
                }
                return 'NO ACTIVE TAB FOUND';
            }
        """)
        print(visible_text[:200])
        
        # Now click Monthly Picks tab
        print("\n" + "="*70)
        print("Clicking 'Monthly Picks' tab...")
        try:
            # Try multiple ways to click
            page.click("text='Monthly Picks'")
        except Exception as e:
            print(f"ERROR clicking: {e}")
            return
        time.sleep(2)
        
        visible_text = page.evaluate("""
            () => {
                const active = document.querySelector('.tab-pane.active');
                if (active) {
                    return active.innerText.substring(0, 200);
                }
                return 'NO ACTIVE TAB FOUND';
            }
        """)
        print("AFTER clicking Monthly Picks:")
        print(visible_text[:200])
        
        # Now click Weekly Picks tab
        print("\n" + "="*70)
        print("Clicking 'Weekly Picks' tab...")
        weekly_tab = page.get_by_text("Weekly Picks", exact=True)
        weekly_tab.click()
        time.sleep(2)
        
        visible_text = page.evaluate("""
            () => {
                const active = document.querySelector('.tab-pane.active');
                if (active) {
                    return active.innerText.substring(0, 200);
                }
                return 'NO ACTIVE TAB FOUND';
            }
        """)
        print("AFTER clicking Weekly Picks:")
        print(visible_text[:200])
        
        # Now click Analysis Hub
        print("\n" + "="*70)
        print("Clicking 'Analysis Hub' tab...")
        analysis_tab = page.get_by_text("Analysis Hub", exact=True)
        analysis_tab.click()
        time.sleep(2)
        
        visible_text = page.evaluate("""
            () => {
                const active = document.querySelector('.tab-pane.active');
                if (active) {
                    return active.innerText.substring(0, 200);
                }
                return 'NO ACTIVE TAB FOUND';
            }
        """)
        print("AFTER clicking Analysis Hub:")
        print(visible_text[:200])
        
        print("\n" + "="*70)
        print("Test complete!")
        browser.close()

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Simple manual check: Navigate to Weekly/Monthly Picks tabs and check logs
"""

import time
import subprocess
from playwright.sync_api import sync_playwright
from datetime import datetime

def test_navigate_picks():
    """Just navigate to picks tabs to trigger the code"""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    screenshot_dir = f'/app/test-artifacts/picks_nav_{timestamp}'
    subprocess.run(['mkdir', '-p', screenshot_dir], check=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Visible browser
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            print("Loading dashboard...")
            page.goto('http://localhost:8050', wait_until='networkidle', timeout=30000)
            time.sleep(3)
            page.screenshot(path=f'{screenshot_dir}/01_home.png')
            
            # Try to find any link with "Picks" in the text
            print("\nLooking for Picks tabs...")
            picks_links = page.locator('a').all()
            print(f"Found {len(picks_links)} links total")
            
            for i, link in enumerate(picks_links[:30]):  # Check first 30 links
                text = link.inner_text()
                if text and ('picks' in text.lower() or 'weekly' in text.lower() or 'monthly' in text.lower()):
                    print(f"  Link {i}: '{text}'")
            
            # Try clicking "Weekly Picks" if found
            weekly_link = page.locator('a:has-text("Weekly Picks")')
            if weekly_link.count() > 0:
                print("\n✅ Found Weekly Picks link, clicking...")
                weekly_link.click()
                time.sleep(5)  # Wait for fetch
                page.screenshot(path=f'{screenshot_dir}/02_weekly_picks.png')
            else:
                print("\n❌ Weekly Picks link not found")
            
            # Try clicking "Monthly Picks" if found
            monthly_link = page.locator('a:has-text("Monthly Picks")')
            if monthly_link.count() > 0:
                print("\n✅ Found Monthly Picks link, clicking...")
                monthly_link.click()
                time.sleep(5)  # Wait for fetch
                page.screenshot(path=f'{screenshot_dir}/03_monthly_picks.png')
            else:
                print("\n❌ Monthly Picks link not found")
            
            print(f"\n✅ Screenshots saved to {screenshot_dir}")
            
            # Keep browser open for 30 seconds to allow manual inspection
            print("\n⏳ Keeping browser open for 30 seconds (check logs)...")
            time.sleep(30)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            page.screenshot(path=f'{screenshot_dir}/error.png')
        finally:
            browser.close()

if __name__ == '__main__':
    test_navigate_picks()

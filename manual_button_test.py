#!/usr/bin/env python3
"""
Manual Button Test - Volatility Lab
===================================
Open browser, click buttons manually, and capture screenshots.
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from datetime import datetime

# Configuration
DASHBOARD_URL = "http://localhost:8051"
SCREENSHOT_DIR = Path("reports/button_fixed_test")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print(f"🔍 Manual Button Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Screenshots will be saved to: {SCREENSHOT_DIR}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=500,
            args=['--start-maximized']
        )
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: print(f"[BROWSER] {msg.type}: {msg.text}"))
        
        # Navigate to dashboard
        print("\n📍 Step 1: Loading Dashboard...")
        page.goto(DASHBOARD_URL, wait_until='networkidle', timeout=30000)
        time.sleep(3)
        page.screenshot(path=str(SCREENSHOT_DIR / '01_dashboard_home.png'))
        print("✅ Dashboard loaded")
        
        # Navigate to Volatility Lab
        print("\n📍 Step 2: Navigating to Volatility Lab...")
        vol_tab = page.locator('a:has-text("Volatility Lab")')
        if vol_tab.count() > 0:
            vol_tab.first.click()
            time.sleep(3)
            page.screenshot(path=str(SCREENSHOT_DIR / '02_vol_lab.png'))
            print("✅ Volatility Lab opened")
        else:
            print("❌ Volatility Lab tab not found!")
            return
        
        # Switch to IV Surface tab
        print("\n📍 Step 3: Switching to IV Surface tab...")
        iv_surface_tab = page.locator('a.nav-link:has-text("📈 IV Surface")')
        if iv_surface_tab.count() > 0:
            iv_surface_tab.click()
            time.sleep(2)
            page.screenshot(path=str(SCREENSHOT_DIR / '03_iv_surface_tab.png'))
            print("✅ IV Surface tab active")
        else:
            print("❌ IV Surface tab not found!")
        
        # Find and click Run button
        print("\n📍 Step 4: Clicking Run button...")
        run_btn = page.locator('[id="vl-calc-run-btn"]')
        if run_btn.count() > 0:
            print(f"   Button found: {run_btn.count()} instance(s)")
            print(f"   Visible: {run_btn.is_visible()}")
            print(f"   Enabled: {run_btn.is_enabled()}")
            
            # Take before screenshot
            page.screenshot(path=str(SCREENSHOT_DIR / '04_before_run_click.png'))
            
            # Click button
            print("   Clicking button...")
            run_btn.click()
            
            # Wait and capture after
            print("   Waiting 5 seconds for response...")
            time.sleep(5)
            page.screenshot(path=str(SCREENSHOT_DIR / '05_after_run_click.png'))
            print("✅ Run button clicked - screenshots captured")
            
            # Check if heatmap changed
            heatmap = page.locator('[id="vl-heatmap"]')
            if heatmap.count() > 0:
                print(f"   Heatmap found: visible={heatmap.is_visible()}")
            else:
                print("   ❌ Heatmap not found!")
        else:
            print("❌ Run button not found!")
        
        # Wait for manual inspection
        print("\n📍 Step 5: Manual Inspection Window (30 seconds)...")
        print("   You can now interact with the dashboard manually.")
        print("   Browser will close automatically in 30 seconds.")
        time.sleep(30)
        
        # Cleanup
        context.close()
        browser.close()
        
        print(f"\n✅ Test complete. Screenshots saved to: {SCREENSHOT_DIR}")

if __name__ == '__main__':
    main()

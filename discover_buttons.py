#!/usr/bin/env python3
"""
Options Lab Button Discovery - Find all actual buttons in each subtab
"""

import os
import time
from playwright.sync_api import sync_playwright

DASHBOARD_URL = "http://127.0.0.1:8051"
SCREENSHOT_DIR = "/tmp/options_lab_buttons"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

SUBTABS = [
    ("options-chain-tab", "Chain Viewer"),
    ("options-greeks-tab", "Greeks Calculator"), 
    ("options-vol-tab", "IV Surface"),
    ("options-flow-tab", "Flow Scanner"),
    ("options-iv-tab", "IV Analysis"),
    ("options-strategy-tab", "Strategy Builder"),
    ("options-manual-tab", "Manual Trade"),
    ("options-portfolio-tab", "Portfolio Greeks"),
    ("options-screener-tab", "Screener"),
    ("options-ai-tab", "AI Recommendations"),
    ("options-earnings-tab", "Earnings Calendar"),
    ("options-backtest-tab", "Backtester"),
]

def discover_buttons():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        print("=" * 70)
        print("OPTIONS LAB BUTTON DISCOVERY")
        print("=" * 70)
        
        # Load dashboard
        page.goto(DASHBOARD_URL, timeout=30000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        # Navigate to Options Lab
        page.locator("#tab-options_lab").click()
        time.sleep(2)
        
        # Load mock data first
        page.locator("#options-mock-btn").click()
        time.sleep(3)
        print("✓ Mock data loaded\n")
        
        all_buttons = {}
        
        # Inspect each subtab
        for tab_id, tab_name in SUBTABS:
            print(f"\n{'='*50}")
            print(f"SUBTAB: {tab_name} (#{tab_id})")
            print("="*50)
            
            try:
                tab = page.locator(f"#{tab_id}")
                if tab.count() > 0:
                    tab.click()
                    time.sleep(1.5)
                    
                    # Find all buttons in the active tab pane
                    buttons = page.locator("button:visible").all()
                    button_info = []
                    
                    for btn in buttons:
                        try:
                            btn_id = btn.get_attribute("id") or "no-id"
                            btn_text = btn.inner_text().strip()[:50]
                            btn_class = btn.get_attribute("class") or ""
                            
                            # Skip navigation buttons
                            if "nav" in btn_class.lower() or btn_id.startswith("tab-"):
                                continue
                                
                            button_info.append({
                                "id": btn_id,
                                "text": btn_text,
                                "clickable": btn.is_visible() and btn.is_enabled()
                            })
                            print(f"  BUTTON: #{btn_id} - '{btn_text}' - clickable={btn.is_enabled()}")
                        except:
                            pass
                    
                    all_buttons[tab_name] = button_info
                    
                    # Take screenshot
                    page.screenshot(path=f"{SCREENSHOT_DIR}/{tab_id}.png")
                    
                else:
                    print(f"  ✗ Tab not found!")
                    
            except Exception as e:
                print(f"  ✗ Error: {e}")
        
        print("\n\n" + "=" * 70)
        print("SUMMARY: Buttons per subtab")
        print("=" * 70)
        
        for tab_name, buttons in all_buttons.items():
            print(f"\n{tab_name}:")
            actionable = [b for b in buttons if b['id'] != 'no-id' and 'options-' in b['id'] or 'ol-' in b['id'] or 'chain-' in b['id'] or 'sim-' in b['id']]
            for b in actionable:
                print(f"  - #{b['id']}: {b['text']}")
        
        time.sleep(3)
        browser.close()
        
        return all_buttons

if __name__ == "__main__":
    discover_buttons()

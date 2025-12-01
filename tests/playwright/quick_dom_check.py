#!/usr/bin/env python3
"""Quick DOM check for Research Lab elements."""
import os
import sys
import time
from playwright.sync_api import sync_playwright

def main():
    """Quick check of Research Lab DOM elements."""
    base_url = os.getenv("DASHBOARD_URL", "http://localhost:8050")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # headless for quick check
        context = browser.new_context()
        page = context.new_page()
        
        print(f"Navigating to {base_url}")
        page.goto(base_url, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=30000)
        
        # Look for Research Lab tab
        print("\n--- Looking for Research Lab tab ---")
        research_tab = page.locator("text=Research Lab").first
        if research_tab.is_visible(timeout=5000):
            print("✅ Research Lab tab found, clicking...")
            research_tab.click()
            time.sleep(3)  # Wait for tab to load
            page.wait_for_load_state("networkidle", timeout=10000)
        else:
            print("❌ Research Lab tab not found!")
            # Look for any tabs
            tabs = page.locator(".nav-link, [role='tab']").all()
            print(f"Found {len(tabs)} tab-like elements")
        
        # Now look for rl- prefixed elements
        print("\n--- Checking for rl- prefixed elements ---")
        rl_elements = page.locator("[id^='rl-']").all()
        print(f"Found {len(rl_elements)} elements with rl- prefix")
        
        for elem in rl_elements[:20]:  # First 20
            elem_id = elem.get_attribute("id")
            is_visible = elem.is_visible()
            tag_name = elem.evaluate("e => e.tagName")
            print(f"  - {elem_id}: {tag_name}, visible={is_visible}")
        
        # Check for specific buttons
        print("\n--- Checking specific buttons ---")
        buttons_to_check = [
            "rl-scan-run-btn",
            "rl-factor-run-btn", 
            "rl-screen-run-btn",
            "rl-rag-send-btn",
        ]
        
        for btn_id in buttons_to_check:
            btn = page.locator(f"#{btn_id}")
            count = btn.count()
            if count > 0:
                is_visible = btn.first.is_visible()
                print(f"  - {btn_id}: count={count}, visible={is_visible}")
            else:
                print(f"  - {btn_id}: NOT FOUND")
        
        # Take a screenshot
        screenshots_dir = "/home/aarav/unified-dashboard/reports/research_lab/playwright"
        os.makedirs(screenshots_dir, exist_ok=True)
        page.screenshot(path=f"{screenshots_dir}/dom_check.png", full_page=True)
        print(f"\n✅ Screenshot saved to {screenshots_dir}/dom_check.png")
        
        # Get HTML snippet
        html = page.content()
        with open(f"{screenshots_dir}/dom_check.html", "w") as f:
            f.write(html)
        print(f"✅ HTML saved to {screenshots_dir}/dom_check.html")
        
        browser.close()

if __name__ == "__main__":
    main()

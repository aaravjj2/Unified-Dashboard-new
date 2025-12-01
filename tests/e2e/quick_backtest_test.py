#!/usr/bin/env python3
"""Quick headed test for Run Backtest button."""
from playwright.sync_api import sync_playwright
import time

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page()
        
        # Add request logging
        def log_request(request):
            if "_dash" in request.url:
                print(f"📡 REQ: {request.method} {request.url[:80]}")
        
        def log_response(response):
            if "_dash" in response.url:
                status = "✅" if response.status == 200 else "❌"
                print(f"{status} RESP: {response.status} {response.url[:80]}")
        
        page.on("request", log_request)
        page.on("response", log_response)
        
        print("🔗 Navigating to dashboard...")
        page.goto("http://127.0.0.1:8051/", wait_until="networkidle", timeout=60000)
        time.sleep(2)
        
        print("📍 Clicking Strategy Lab tab...")
        page.click('a[href="/strategy-lab"]')
        page.wait_for_url("**/strategy-lab**", timeout=10000)
        time.sleep(2)
        
        print("📍 Clicking Execute & Configure subtab...")
        page.click('text=Execute & Configure')
        time.sleep(2)
        
        # Get button state before click
        btn = page.locator("#sl-run-backtest-btn")
        print(f"🔘 Button visible: {btn.is_visible()}")
        print(f"🔘 Button enabled: {btn.is_enabled()}")
        print(f"🔘 Button text: {btn.text_content()}")
        
        # Check current store value
        store = page.locator("#sl-backtest-results")
        print(f"📦 Store exists: {store.count() > 0}")
        
        print("\n🚀 CLICKING RUN BACKTEST...")
        btn.click()
        
        # Wait and observe
        print("⏳ Waiting for callback response...")
        time.sleep(10)
        
        # Check status div
        status = page.locator("#sl-execution-status")
        if status.count() > 0:
            print(f"📊 Execution Status: {status.inner_text()[:200]}")
        
        # Check progress
        progress = page.locator('[id*="progress"]').first
        if progress.count() > 0:
            print(f"📊 Progress: {progress.inner_text()[:100]}")
        
        print("\n🔍 Checking Results subtab...")
        page.click('text=Results')
        time.sleep(2)
        
        # Check for results content
        results_area = page.locator('#strategy-lab-results-content, [id*="results"]').first
        if results_area.count() > 0:
            print(f"📊 Results visible: {results_area.is_visible()}")
            print(f"📊 Results text: {results_area.inner_text()[:300]}")
        
        print("\n⏸️ Keeping browser open for 30 seconds for inspection...")
        time.sleep(30)
        
        browser.close()

if __name__ == "__main__":
    test()

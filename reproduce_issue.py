
import time
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        # Connect to the existing browser session
        browser = p.chromium.connect_over_cdp("http://172.28.80.1:9222")
        context = browser.contexts[0]
        page = context.pages[0]

        print(f"Connected to page: {page.title()}")

        # 1. Verify TradingView Widget on Home Page
        print("\n--- Verifying TradingView Widget ---")
        page.goto("http://localhost:8051/")
        page.wait_for_load_state("networkidle")
        
        tv_iframe = page.locator("#tradingview_widget")
        if tv_iframe.count() > 0:
            print("TradingView iframe found.")
            box = tv_iframe.bounding_box()
            print(f"Iframe Bounding Box: {box}")
            if box['height'] > 0 and box['width'] > 0:
                print("Iframe has non-zero dimensions.")
                # Take screenshot of the iframe area
                page.screenshot(path="/home/aarav/.gemini/antigravity/brain/99986055-5ae0-45f1-b535-2d36203e17c6/debug_tradingview.png", clip=box)
                print("Screenshot saved to debug_tradingview.png")
            else:
                print("FAIL: Iframe has zero dimensions!")
        else:
            print("FAIL: TradingView iframe NOT found in DOM.")

        # 2. Verify Volatility Lab IV Surface
        print("\n--- Verifying Volatility Lab IV Surface ---")
        # Navigate to Vol Lab
        # We need to find the tab button. Based on layout, it's in a dbc.Tabs with id "volatility-lab-tabs"
        # The tab id is "tab-iv-surface"
        
        # First ensure we are on the Vol Lab page/tab
        # The dashboard seems to be single page with tabs? 
        # Wait, index.py handles routing. 
        # Let's check if there is a main nav to switch to Vol Lab if we are on Home.
        # Assuming we are on Home, we need to click the Volatility Lab nav link if it exists, 
        # OR if it's a tab within the dashboard.
        # Looking at previous context, it seems to be a tab-based app or separate pages.
        # Let's try navigating directly if possible, or finding the link.
        # The user said "Volatility Lab" is a tab.
        
        # Let's look for a link with text "Volatility Lab"
        vol_lab_link = page.locator("a:has-text('Volatility Lab')")
        if vol_lab_link.count() > 0:
            # Check for blocking modal
            modal = page.locator(".modal.show")
            if modal.count() > 0:
                print("WARNING: Found blocking modal!")
                print(f"Modal Text: {modal.inner_text()}")
                page.screenshot(path="/home/aarav/.gemini/antigravity/brain/99986055-5ae0-45f1-b535-2d36203e17c6/debug_modal.png")
                
                # Try to close it
                close_btn = modal.locator("button.btn-close, button:has-text('Close')")
                if close_btn.count() > 0:
                    print("Closing modal...")
                    close_btn.click()
                    page.wait_for_timeout(1000)
                else:
                    print("Could not find close button on modal.")
            
            vol_lab_link.click()
            print("Clicked 'Volatility Lab' navigation link.")
        else:
            print("Could not find 'Volatility Lab' link, assuming we might be there or need to check tabs.")
        
        page.wait_for_timeout(2000)

        # Now switch to "IV Surface" tab within Vol Lab
        print("Attempting to find IV Surface tab...")
        # Use the specific DBC attribute
        iv_surface_tab = page.locator("#volatility-lab-tabs a[data-rb-event-key='tab-iv-surface']")
        
        # Debug visibility
        if iv_surface_tab.count() > 0:
            box = iv_surface_tab.bounding_box()
            print(f"Tab found. Bounding box: {box}")
            if box and box['width'] > 0 and box['height'] > 0:
                iv_surface_tab.click()
                print("Switched to 'IV Surface' tab.")
                page.wait_for_timeout(1000)
            else:
                print("FAIL: Tab exists but has 0 dimensions (invisible).")
                # Dump parent HTML
                print(page.locator("#volatility-lab-tabs").inner_html())
        else:
            print("FAIL: Could not find 'IV Surface' tab button via data attribute. Trying text...")
            iv_surface_tab = page.locator("text=IV Surface")
            if iv_surface_tab.count() > 0:
                iv_surface_tab.first.click()
                print("Switched to 'IV Surface' tab (generic selector).")
                page.wait_for_timeout(1000)
            else:
                print("CRITICAL FAIL: IV Surface tab absolutely not found.")
                page.screenshot(path="/home/aarav/.gemini/antigravity/brain/99986055-5ae0-45f1-b535-2d36203e17c6/debug_tabs_missing.png")

        # Check if graph is empty initially
        heatmap = page.locator("#vl-heatmap") 
        
        # Click "Compute Surface"
        compute_btn = page.locator("#vl-calc-run-btn") # Use ID directly
        if compute_btn.count() > 0:
            print("Found 'Compute Surface' button. Clicking...")
            # Force click if needed
            compute_btn.click(force=True)
            page.wait_for_timeout(5000) # Wait for computation
            
            page.screenshot(path="/home/aarav/.gemini/antigravity/brain/99986055-5ae0-45f1-b535-2d36203e17c6/debug_iv_surface_after_click.png")
            print("Screenshot saved to debug_iv_surface_after_click.png")
            
        else:
            print("FAIL: 'Compute Surface' button not found.")

        # 3. Verify Signals Dependency
        print("\n--- Verifying Signals Dependency ---")
        # Switch to Signals tab
        signals_tab = page.locator("#volatility-lab-tabs a[data-rb-event-key='tab-signals']")
        if signals_tab.count() > 0:
            signals_tab.click(force=True)
            print("Switched to 'Signals & Backtest' tab.")
            page.wait_for_timeout(1000)
            
            # Click "Scan Signals"
            scan_btn = page.locator("#vl-signal-run-btn") # Use ID directly
            if scan_btn.count() > 0:
                scan_btn.click(force=True)
                page.wait_for_timeout(2000)
                
                page.screenshot(path="/home/aarav/.gemini/antigravity/brain/99986055-5ae0-45f1-b535-2d36203e17c6/debug_signals.png")
                print("Screenshot saved to debug_signals.png")
            else:
                print("FAIL: 'Scan Signals' button not found.")
        else:
            print("FAIL: 'Signals & Backtest' tab not found.")

        browser.close()

if __name__ == "__main__":
    run()

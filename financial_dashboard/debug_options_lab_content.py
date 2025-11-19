"""Debug script to capture what's actually in the Options Lab tab."""
from playwright.sync_api import sync_playwright
import time

def capture_options_lab_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to dashboard
        page.goto("http://localhost:8000", wait_until="domcontentloaded")
        time.sleep(3)
        
        # Click Options Lab
        try:
            page.click('[data-test-id="tab-options_lab"]', timeout=5000)
        except:
            page.click('text="💹 Options Lab"', timeout=10000)
        
        time.sleep(3)
        
        # Get the full HTML
        html_content = page.content()
        
        # Save to file
        with open('_options_lab_content.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print("HTML saved to _options_lab_content.html")
        
        # Also try to find what tabs are actually there
        print("\nSearching for tab labels...")
        all_tabs = page.locator('a[role="tab"]').all()
        print(f"Found {len(all_tabs)} tabs")
        for i, tab in enumerate(all_tabs):
            try:
                text = tab.inner_text(timeout=1000)
                print(f"Tab {i}: {text}")
            except:
                pass
        
        browser.close()

if __name__ == "__main__":
    capture_options_lab_html()

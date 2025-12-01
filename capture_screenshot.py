"""Simple screenshot test to verify Research Lab tab visibility."""
from playwright.sync_api import sync_playwright
import time

print("🎬 Starting screenshot capture...")

with sync_playwright() as p:
    print("📱 Launching browser...")
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print("🔍 Loading dashboard...")
    page.goto('http://localhost:8050', wait_until='networkidle', timeout=30000)
    
    # Wait for tabs to load
    print("⏳ Waiting for UI to stabilize...")
    time.sleep(5)
    
    # Take screenshot
    print("📸 Taking screenshot...")
    page.screenshot(path='research_lab_integration_screenshot.png', full_page=True)
    
    # Check HTML content
    html = page.content()
    has_research_lab = '🔬' in html or 'Research Lab' in html or 'research-lab' in html
    
    print(f"\n✅ Screenshot saved: research_lab_integration_screenshot.png")
    print(f"✅ Research Lab in HTML: {has_research_lab}")
    print(f"✅ Page loaded: {len(html)} bytes")
    
    browser.close()
    print("\n🎉 Screenshot capture complete!")

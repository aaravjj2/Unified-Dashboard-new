"""
Find the correct Market Trends tab selector
"""

from playwright.sync_api import sync_playwright
import time

def find_market_trends_selector():
    """Discover the correct selector for Market Trends tab"""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("🔍 Loading dashboard...")
        page.goto('http://localhost:8051', wait_until='networkidle', timeout=60000)
        time.sleep(5)
        
        print("\n📋 Looking for Market Trends tab selectors...\n")
        
        # Try different possible selectors
        selectors = [
            'a.nav-link[href="#market-trends"]',
            'button.nav-link[data-rb-event-key="market-trends"]',
            'a[href="#market-trends"]',
            '#market-trends-tab',
            'text="Market Trends"',
            '[data-rr-ui-event-key="market-trends"]',
        ]
        
        for selector in selectors:
            try:
                element = page.locator(selector).first
                if element.count() > 0:
                    print(f"✅ FOUND: {selector}")
                    print(f"   Count: {element.count()}")
                    print(f"   Visible: {element.is_visible()}")
                    if element.is_visible():
                        html = element.evaluate('el => el.outerHTML')
                        print(f"   HTML: {html[:200]}")
                else:
                    print(f"❌ NOT FOUND: {selector}")
            except Exception as e:
                print(f"❌ ERROR with {selector}: {e}")
        
        # Get all nav links
        print("\n📋 All nav-link elements:")
        nav_links = page.locator('.nav-link').all()
        for i, link in enumerate(nav_links[:15]):
            try:
                text = link.inner_text()
                html = link.evaluate('el => el.outerHTML')
                print(f"\n{i+1}. Text: '{text}'")
                print(f"   HTML: {html[:150]}")
            except:
                pass
        
        browser.close()

if __name__ == '__main__':
    find_market_trends_selector()

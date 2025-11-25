"""Quick diagnostic script to check if Research Lab appears in UI"""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print("🔍 Loading dashboard...")
    page.goto('http://localhost:8050')
    time.sleep(5)
    
    print("\n📸 Taking screenshot...")
    page.screenshot(path='test-artifacts/research_lab_check.png', full_page=True)
    
    print("\n🔎 Searching for Research Lab...")
    
    # Check if tab exists in HTML
    html = page.content()
    if 'Research Lab' in html or 'research_lab' in html or 'research-lab' in html:
        print("✅ Research Lab found in HTML!")
        
        # Try to find and click the tab
        try:
            research_tab = page.locator('text=🔬 Research Lab')
            if research_tab.is_visible():
                print("✅ Research Lab tab is VISIBLE in UI!")
                research_tab.click()
                time.sleep(2)
                page.screenshot(path='test-artifacts/research_lab_clicked.png')
                print("✅ Research Lab tab clicked successfully!")
            else:
                print("❌ Research Lab tab exists but is NOT VISIBLE")
        except Exception as e:
            print(f"❌ Error clicking Research Lab: {e}")
            
            # Try alternative selectors
            try:
                alt_tab = page.locator('[tab_id="research_lab"]')
                if alt_tab.count() > 0:
                    print(f"✅ Found {alt_tab.count()} elements with tab_id='research_lab'")
                else:
                    print("❌ No elements with tab_id='research_lab'")
            except Exception as e2:
                print(f"❌ Alternative selector failed: {e2}")
    else:
        print("❌ Research Lab NOT found in HTML")
        
    print("\n📋 All tabs found:")
    tabs = page.locator('.nav-link, [role="tab"]').all()
    for i, tab in enumerate(tabs[:15]):
        try:
            text = tab.inner_text()
            print(f"  {i+1}. {text}")
        except:
            pass
    
    print(f"\nTotal tabs found: {len(tabs)}")
    
    browser.close()

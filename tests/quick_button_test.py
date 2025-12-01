"""
Quick Market Trends button test - verifies Run Analysis button works.
"""
from playwright.sync_api import sync_playwright
import time

print("=" * 60)
print("MARKET TRENDS BUTTON TEST")
print("=" * 60)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    console_log = []
    page.on('console', lambda msg: console_log.append(f"{msg.type}: {msg.text}"))
    
    print("\n📍 Step 1: Load dashboard")
    page.goto('http://localhost:8050', wait_until='domcontentloaded')
    time.sleep(3)
    
    print("📍 Step 2: Click Market Trends tab")
    page.click('#tab-market_trends')
    time.sleep(2)
    
    # Check if table rendered
    table_visible = page.is_visible('#news-table')
    print(f"📊 Table visible: {table_visible}")
    
    if table_visible:
        row_count = page.locator('#news-table tbody tr').count()
        print(f"📊 Initial row count: {row_count}")
    
    print("\n📍 Step 3: Click Run Analysis button")
    button_visible = page.is_visible('#run-btn')
    print(f"🔘 Button visible: {button_visible}")
    
    if button_visible:
        page.click('#run-btn')
        print("✅ Button clicked!")
        
        print("\n📍 Step 4: Wait for results area update (30s max)")
        for i in range(6):
            time.sleep(5)
            # Check results-area for content
            results = page.locator('#results-area').inner_text(timeout=2000)
            print(f"   {(i+1)*5}s: Results length = {len(results)}")
            if len(results) > 100:
                print("   ✅ Results updated!")
                break
        
        # Final check
        final_results = page.locator('#results-area').inner_text(timeout=2000)
        if len(final_results) > 100:
            print(f"\n✅ CALLBACK FIRED! Results length: {len(final_results)}")
        else:
            print(f"\n❌ CALLBACK DID NOT FIRE. Results: '{final_results[:50]}'")
    
    browser.close()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)

"""
Quick callback validation test - checks if duplicate callback errors are gone.
"""
from playwright.sync_api import sync_playwright
import time

print("=" * 60)
print("QUICK CALLBACK VALIDATION TEST")
print("=" * 60)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    console_errors = []
    page.on('console', lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)
    
    print("\n📍 Step 1: Loading dashboard...")
    page.goto('http://localhost:8050', wait_until='domcontentloaded')
    time.sleep(5)
    
    # Check for duplicate callback errors
    duplicate_errors = [err for err in console_errors if 'Duplicate callback' in err]
    
    if duplicate_errors:
        print(f"\n❌ FOUND {len(duplicate_errors)} DUPLICATE CALLBACK ERRORS:")
        for err in duplicate_errors[:3]:
            print(f"   - {err[:100]}...")
    else:
        print("\n✅ NO DUPLICATE CALLBACK ERRORS!")
    
    print(f"\n📊 Total console errors: {len(console_errors)}")
    
    browser.close()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)

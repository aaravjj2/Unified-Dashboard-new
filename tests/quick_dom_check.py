"""
Simple headless test - Check what's actually rendered
"""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print("Loading dashboard...")
    page.goto('http://localhost:8050', wait_until='domcontentloaded')
    time.sleep(3)
    
    print("\nClicking Market Trends tab...")
    page.click('#tab-market_trends')
    time.sleep(2)
    
    print("\n" + "="*80)
    print("MARKET TRENDS TAB CONTENT")
    print("="*80)
    
    # Get all visible text
    body_text = page.locator('body').inner_text()
    
    # Extract Market Trends specific content
    if 'Market Trends' in body_text:
        # Find buttons
        print("\nBUTTONS FOUND:")
        buttons = page.locator('button:visible').all()
        for i, btn in enumerate(buttons[:15]):
            try:
                btn_id = btn.get_attribute('id') or '(no-id)'
                btn_text = btn.inner_text(timeout=500) or '(empty)'
                print(f"  {i+1}. {btn_id}: '{btn_text}'")
            except:
                pass
        
        # Check for input fields
        print("\nINPUT FIELDS:")
        inputs = page.locator('input:visible, textarea:visible').all()
        for i, inp in enumerate(inputs[:10]):
            try:
                inp_id = inp.get_attribute('id') or '(no-id)'
                inp_val = inp.input_value(timeout=500) or '(empty)'
                print(f"  {i+1}. {inp_id}: '{inp_val[:50]}'")
            except:
                pass
        
        # Check for results-area
        print("\nRESULTS AREA:")
        if page.locator('#results-area').count() > 0:
            results = page.locator('#results-area').inner_text(timeout=2000)
            print(f"  Length: {len(results)} characters")
            print(f"  Preview: {results[:200]}")
        else:
            print("  ❌ #results-area NOT FOUND")
        
        # Check for news table
        print("\nNEWS TABLE:")
        if page.locator('#news-table').count() > 0:
            rows = page.locator('#news-table tbody tr').count()
            print(f"  Rows: {rows}")
        else:
            print("  ❌ #news-table NOT FOUND")
        
        # Save HTML for inspection
        with open('/tmp/market_trends_actual.html', 'w') as f:
            f.write(page.content())
        print("\n✅ Full HTML saved to: /tmp/market_trends_actual.html")
    
    browser.close()

#!/usr/bin/env python
"""Test Volatility Lab buttons."""
from playwright.sync_api import sync_playwright
import time

def test_volatility_lab():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("Loading dashboard...")
        page.goto('http://localhost:8050', wait_until='networkidle', timeout=30000)
        time.sleep(2)
        
        # Navigate to Volatility Lab
        print("\n1. Clicking Volatility Lab...")
        page.click('#tab-volatility_lab')
        time.sleep(2)
        
        # Find all buttons in Volatility Lab
        print("\n2. Finding buttons...")
        buttons = page.locator('button').all()
        vol_lab_buttons = []
        for btn in buttons:
            text = btn.inner_text()
            if text and len(text) < 50:  # Reasonable button text length
                try:
                    btn_id = btn.get_attribute('id') or 'no-id'
                    vol_lab_buttons.append((btn_id, text))
                except:
                    pass
        
        print(f"\n   Found {len(vol_lab_buttons)} buttons:")
        for btn_id, text in vol_lab_buttons[:10]:
            print(f"   - {btn_id}: {text}")
        
        # Test Calculate Volatility button
        print("\n3. Testing 'Calculate Volatility' button...")
        try:
            page.fill('#vl-ticker-input', 'SPY')
            time.sleep(0.5)
            page.click('#vl-calc-btn')
            time.sleep(3)
            
            # Check if any output appeared
            output_div = page.locator('#vl-output')
            if output_div.count() > 0:
                output_text = output_div.inner_text()
                print(f"   Output: {output_text[:200]}...")
            else:
                print("   ⚠️ No output div found")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
        
        # Test Forecast button
        print("\n4. Testing 'Forecast' button...")
        try:
            page.click('#vl-forecast-btn')
            time.sleep(3)
            
            forecast_div = page.locator('#vl-forecast-output')
            if forecast_div.count() > 0:
                forecast_text = forecast_div.inner_text()
                print(f"   Forecast: {forecast_text[:200]}...")
            else:
                print("   ⚠️ No forecast output found")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
        
        # Screenshot
        page.screenshot(path='/home/aarav/unified-dashboard/volatility_lab_test.png')
        print("\n📸 Screenshot: volatility_lab_test.png")
        
        print("\n✅ Volatility Lab test complete!")
        time.sleep(5)
        
        browser.close()

if __name__ == '__main__':
    test_volatility_lab()

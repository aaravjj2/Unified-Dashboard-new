"""
Quick test to verify Volatility Lab tab is accessible and functional
Phase 0.7A - Step 1: Baseline Assessment
"""
from playwright.sync_api import sync_playwright
import time
from pathlib import Path

def test_volatility_lab_baseline():
    """Test if Volatility Lab tab loads and renders basic UI elements."""
    print("\n" + "="*70)
    print("VOLATILITY LAB BASELINE TEST - Phase 0.7A")
    print("="*70 + "\n")
    
    output_dir = Path('test-artifacts/volatility_lab_baseline')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        # Collect console messages and errors
        console_messages = []
        errors = []
        
        def handle_console(msg):
            text = msg.text
            console_messages.append(f"[{msg.type}] {text}")
            if msg.type == 'error':
                errors.append(text)
        
        page.on('console', handle_console)
        
        # Navigate to dashboard
        print("📍 Step 1: Navigate to dashboard...")
        page.goto('http://127.0.0.1:8050/', wait_until='networkidle', timeout=30000)
        time.sleep(2)
        page.screenshot(path=str(output_dir / '1_home.png'))
        print("✅ Home page loaded")
        
        # Click Volatility Lab tab
        print("\n📍 Step 2: Click Volatility Lab tab...")
        volatility_selectors = [
            'a:has-text("Volatility Lab")',
            'a:has-text("⚡ Volatility Lab")',
            '#tab-volatility_lab',
            '[tab-id="volatility_lab"]'
        ]
        
        clicked = False
        for selector in volatility_selectors:
            try:
                tab = page.locator(selector).first
                if tab.count() > 0:
                    tab.click(timeout=5000)
                    clicked = True
                    print(f"✅ Clicked using: {selector}")
                    break
            except Exception:
                continue
        
        if not clicked:
            print("❌ Could not find Volatility Lab tab")
            browser.close()
            return False
        
        time.sleep(3)
        page.screenshot(path=str(output_dir / '2_volatility_lab_initial.png'))
        print("✅ Volatility Lab tab activated")
        
        # Check for key UI elements
        print("\n📍 Step 3: Verify UI elements...")
        
        elements_to_check = [
            ('vl-tickers-input', 'Ticker input'),
            ('vl-compute', 'Compute button'),
            ('vl-date-range', 'Date range picker'),
            ('vl-window', 'Window selector'),
            ('vl-type', 'Volatility type selector'),
            ('vl-price-graph', 'Price graph'),
            ('vl-vol-graph', 'Volatility graph'),
            ('vl-results-table', 'Results table')
        ]
        
        found_elements = []
        missing_elements = []
        
        for element_id, name in elements_to_check:
            try:
                element = page.locator(f'#{element_id}').first
                if element.count() > 0:
                    found_elements.append(name)
                    print(f"  ✅ {name}")
                else:
                    missing_elements.append(name)
                    print(f"  ❌ {name} NOT FOUND")
            except Exception as e:
                missing_elements.append(name)
                print(f"  ❌ {name} ERROR: {e}")
        
        # Try entering a ticker and clicking compute
        print("\n📍 Step 4: Test basic interaction...")
        try:
            ticker_input = page.locator('#vl-tickers-input').first
            if ticker_input.count() > 0:
                ticker_input.fill('SPY')
                print("  ✅ Entered ticker: SPY")
                time.sleep(1)
                
                compute_btn = page.locator('#vl-compute').first
                if compute_btn.count() > 0:
                    compute_btn.click()
                    print("  ✅ Clicked Compute button")
                    time.sleep(5)  # Wait for computation
                    
                    page.screenshot(path=str(output_dir / '3_after_compute.png'))
                    print("  ✅ Screenshot captured after compute")
                else:
                    print("  ❌ Compute button not clickable")
            else:
                print("  ❌ Ticker input not accessible")
        except Exception as e:
            print(f"  ❌ Interaction test failed: {e}")
        
        # Check for errors
        print("\n📍 Step 5: Check for errors...")
        volatility_errors = [err for err in errors if 'vl-' in err.lower() or 'volatility' in err.lower()]
        
        if volatility_errors:
            print(f"❌ Found {len(volatility_errors)} Volatility Lab errors:")
            for err in volatility_errors[:5]:
                print(f"  - {err}")
        else:
            print("✅ No Volatility Lab-specific errors detected")
        
        # Final screenshot
        page.screenshot(path=str(output_dir / '4_final_state.png'), full_page=True)
        
        browser.close()
        
        # Summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"UI Elements Found: {len(found_elements)}/{len(elements_to_check)}")
        print(f"UI Elements Missing: {len(missing_elements)}")
        print(f"Errors Detected: {len(errors)}")
        print(f"Volatility Lab Errors: {len(volatility_errors)}")
        
        if missing_elements:
            print("\nMissing Elements:")
            for elem in missing_elements:
                print(f"  - {elem}")
        
        # Pass criteria
        success = (
            len(found_elements) >= 6 and  # At least 6/8 elements found
            len(volatility_errors) == 0 and  # No VL-specific errors
            clicked  # Tab was accessible
        )
        
        if success:
            print("\n✅ BASELINE TEST PASSED")
            print("Volatility Lab is accessible and basic UI renders")
        else:
            print("\n❌ BASELINE TEST FAILED")
            print("Volatility Lab needs repairs before proceeding")
        
        return success

if __name__ == '__main__':
    try:
        success = test_volatility_lab_baseline()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test crashed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

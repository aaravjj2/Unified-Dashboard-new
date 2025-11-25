"""
Quick test to verify Plotly.js loads properly after serve_locally=True fix
Phase 0 - Portfolio Analytics Loading Spinner & Plotly Debug
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import time

def test_plotly_loading():
    """Test if Plotly.js loads without timeout errors."""
    print("\n" + "="*70)
    print("PLOTLY.JS LOADING TEST - Phase 0")
    print("="*70 + "\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        # Collect console messages
        console_messages = []
        errors = []
        
        def handle_console(msg):
            text = msg.text
            console_messages.append(f"[{msg.type}] {text}")
            if msg.type == 'error':
                errors.append(text)
        
        page.on('console', handle_console)
        
        # Navigate to dashboard
        print("📍 Navigating to dashboard...")
        page.goto('http://127.0.0.1:8050/', wait_until='networkidle', timeout=30000)
        
        # Wait for initial load
        time.sleep(3)
        
        # Navigate to Portfolio tab
        print("📍 Clicking Portfolio tab...")
        try:
            portfolio_tab = page.locator('a[href="#portfolio"]').first
            portfolio_tab.click()
            time.sleep(2)
        except Exception as e:
            print(f"⚠️  Portfolio tab not found: {e}")
        
        # Navigate to Analytics subtab
        print("📍 Clicking Analytics subtab...")
        try:
            analytics_tab = page.locator('#portfolio-tracker-subtabs a[data-value="analytics"]').first
            analytics_tab.click()
            time.sleep(8)  # Wait for analytics to calculate
        except Exception as e:
            print(f"⚠️  Analytics subtab not found: {e}")
        
        # Check for Plotly.js loading errors
        plotly_errors = [err for err in errors if 'plotly' in err.lower()]
        
        print("\n" + "="*70)
        print("RESULTS")
        print("="*70)
        print(f"Total console messages: {len(console_messages)}")
        print(f"Total errors: {len(errors)}")
        print(f"Plotly.js errors: {len(plotly_errors)}")
        
        if plotly_errors:
            print("\n❌ PLOTLY ERRORS DETECTED:")
            for err in plotly_errors[:5]:  # Show first 5
                print(f"  - {err}")
        else:
            print("\n✅ NO PLOTLY.JS LOADING ERRORS")
        
        # Check for loading spinner presence
        print("\n" + "-"*70)
        print("LOADING SPINNER CHECK")
        print("-"*70)
        
        try:
            loading_spinner = page.locator('#analytics-loading').first
            if loading_spinner.count() > 0:
                print("✅ Analytics loading spinner found in DOM")
            else:
                print("❌ Analytics loading spinner NOT found")
        except Exception as e:
            print(f"⚠️  Could not check for loading spinner: {e}")
        
        # Check for Plotly graphs
        print("\n" + "-"*70)
        print("PLOTLY GRAPH CHECK")
        print("-"*70)
        
        try:
            plotly_graphs = page.locator('.plotly').all()
            print(f"📊 Plotly graphs found: {len(plotly_graphs)}")
            
            if len(plotly_graphs) > 0:
                print("✅ Plotly graphs are rendering")
            else:
                print("⚠️  No Plotly graphs found (may need time or data)")
        except Exception as e:
            print(f"⚠️  Could not check for Plotly graphs: {e}")
        
        # Show recent console messages (last 10)
        print("\n" + "-"*70)
        print("RECENT CONSOLE MESSAGES (Last 10)")
        print("-"*70)
        for msg in console_messages[-10:]:
            print(msg)
        
        browser.close()
        
        # Summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        
        if len(plotly_errors) == 0:
            print("✅ TEST PASSED - No Plotly.js loading errors detected")
            print("✅ serve_locally=True fix appears to be working")
            return True
        else:
            print("❌ TEST FAILED - Plotly.js errors still present")
            print("❌ Further debugging required")
            return False

if __name__ == '__main__':
    try:
        success = test_plotly_loading()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test crashed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

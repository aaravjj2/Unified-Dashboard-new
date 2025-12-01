"""
Visual test to capture loading spinner in Portfolio Analytics
Phase 0 - Loading Spinner Validation
"""
from playwright.sync_api import sync_playwright
import time
from pathlib import Path

def capture_loading_spinner():
    """Capture screenshots of loading spinner in action."""
    print("\n" + "="*70)
    print("PORTFOLIO ANALYTICS LOADING SPINNER - Visual Test")
    print("="*70 + "\n")
    
    output_dir = Path('test-artifacts/loading_spinner_test')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        # Navigate to dashboard
        print("📍 Navigating to dashboard...")
        page.goto('http://127.0.0.1:8050/', wait_until='networkidle', timeout=30000)
        time.sleep(2)
        
        # Take screenshot of home page
        page.screenshot(path=str(output_dir / '1_home_page.png'))
        print("✅ Screenshot 1: Home page")
        
        # Navigate to Portfolio tab
        print("\n📍 Navigating to Portfolio...")
        try:
            # Try multiple selectors
            portfolio_selectors = [
                'a[href="#portfolio"]',
                'a:has-text("Portfolio")',
                '.nav-link:has-text("Portfolio")',
                '#main-tabs a[data-value="portfolio"]'
            ]
            
            clicked = False
            for selector in portfolio_selectors:
                try:
                    tab = page.locator(selector).first
                    if tab.count() > 0:
                        tab.click(timeout=5000)
                        clicked = True
                        print(f"✅ Clicked Portfolio using: {selector}")
                        break
                except Exception:
                    continue
            
            if not clicked:
                print("⚠️  Could not click Portfolio tab, using current view")
            
            time.sleep(2)
            page.screenshot(path=str(output_dir / '2_portfolio_tab.png'))
            print("✅ Screenshot 2: Portfolio tab")
            
        except Exception as e:
            print(f"⚠️  Portfolio navigation: {e}")
        
        # Navigate to Analytics subtab
        print("\n📍 Navigating to Analytics subtab...")
        try:
            analytics_selectors = [
                '#portfolio-tracker-subtabs a[data-value="analytics"]',
                'a:has-text("Analytics")',
                '.nav-link:has-text("Analytics")'
            ]
            
            clicked = False
            for selector in analytics_selectors:
                try:
                    tab = page.locator(selector).first
                    if tab.count() > 0:
                        # Take screenshot immediately after click (should show spinner)
                        tab.click(timeout=5000)
                        clicked = True
                        print(f"✅ Clicked Analytics using: {selector}")
                        
                        # Quick screenshot to catch loading spinner
                        time.sleep(0.5)
                        page.screenshot(path=str(output_dir / '3_analytics_loading.png'))
                        print("✅ Screenshot 3: Analytics loading (spinner)")
                        
                        # Wait for content to load
                        time.sleep(8)
                        page.screenshot(path=str(output_dir / '4_analytics_loaded.png'))
                        print("✅ Screenshot 4: Analytics loaded (content)")
                        break
                except Exception as ex:
                    print(f"  - Selector {selector} failed: {ex}")
                    continue
            
            if not clicked:
                print("⚠️  Could not click Analytics subtab")
                page.screenshot(path=str(output_dir / '3_current_view.png'))
            
        except Exception as e:
            print(f"⚠️  Analytics navigation: {e}")
        
        # Check loading spinner in DOM
        print("\n" + "-"*70)
        print("LOADING SPINNER DOM CHECK")
        print("-"*70)
        
        try:
            spinner = page.locator('#analytics-loading').first
            if spinner.count() > 0:
                print("✅ #analytics-loading found in DOM")
                
                # Get spinner HTML
                spinner_html = spinner.inner_html()
                print(f"   Spinner HTML: {spinner_html[:200]}...")
            else:
                print("❌ #analytics-loading NOT found in DOM")
        except Exception as e:
            print(f"⚠️  Could not check spinner: {e}")
        
        # Final full-page screenshot
        page.screenshot(path=str(output_dir / '5_final_state.png'), full_page=True)
        print("✅ Screenshot 5: Full page final state")
        
        browser.close()
        
        # Summary
        print("\n" + "="*70)
        print("SCREENSHOTS SAVED")
        print("="*70)
        print(f"Location: {output_dir}")
        print("\nFiles:")
        for img in sorted(output_dir.glob('*.png')):
            size_kb = img.stat().st_size / 1024
            print(f"  - {img.name} ({size_kb:.1f} KB)")
        
        print("\n✅ Visual test complete!")

if __name__ == '__main__':
    try:
        capture_loading_spinner()
    except Exception as e:
        print(f"\n❌ Test crashed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

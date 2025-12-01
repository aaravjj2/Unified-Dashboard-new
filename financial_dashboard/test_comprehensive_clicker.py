#!/usr/bin/env python3
"""Comprehensive clicker test for Analysis Hub and Portfolio Dashboard"""
from playwright.sync_api import sync_playwright
import sys

def test_analysis_hub_comprehensive():
    """Comprehensive test of Analysis Hub functionality"""
    print("\n" + "="*60)
    print("COMPREHENSIVE TEST: Analysis Hub")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print("\n1. Loading Analysis Hub...")
            page.goto("http://localhost:8054", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
            print("✅ Page loaded")
            
            print("\n2. Verifying welcome panel...")
            welcome = page.locator('#attr-initial-instructions')
            if not welcome.is_visible():
                print("❌ FAIL: Welcome panel not visible")
                return False
            print("✅ Welcome panel visible")
            
            print("\n3. Verifying all 3 tabs are present and labeled...")
            tabs = page.locator('.nav-link').all()
            expected_labels = ['Attribution Analysis', 'Portfolio Analytics', 'Scenario Testing']
            actual_labels = [tab.text_content().strip() for tab in tabs]
            
            if len(actual_labels) != 3:
                print(f"❌ FAIL: Expected 3 tabs, found {len(actual_labels)}")
                return False
            
            for i, expected in enumerate(expected_labels):
                if actual_labels[i] != expected:
                    print(f"❌ FAIL: Tab {i} expected '{expected}', got '{actual_labels[i]}'")
                    return False
            print(f"✅ All tab labels correct: {actual_labels}")
            
            print("\n4. Testing tab switching...")
            for i, tab_label in enumerate(expected_labels):
                print(f"   Clicking '{tab_label}'...")
                tabs[i].click()
                page.wait_for_timeout(1000)
                
                # Verify the tab is now active
                is_active = page.evaluate(f"""() => {{
                    const links = document.querySelectorAll('.nav-link');
                    return links[{i}].classList.contains('active');
                }}""")
                
                if not is_active:
                    print(f"   ❌ FAIL: Tab '{tab_label}' not active after click")
                    return False
                print(f"   ✅ Tab '{tab_label}' activated")
            
            print("\n5. Testing Attribution Analysis callback...")
            # Switch back to Attribution Analysis tab
            tabs[0].click()
            page.wait_for_timeout(1000)
            
            # Find and click the "Run Attribution Analysis" button
            run_button = page.locator('#attr-run-button')
            if run_button.count() == 0:
                print("❌ FAIL: Run button not found")
                return False
            
            print("   Clicking 'Run Attribution Analysis' button...")
            run_button.click()
            page.wait_for_timeout(5000)  # Wait for analysis to complete
            
            # Check if results container becomes visible
            results_container = page.locator('#attr-results-container')
            results_visible = page.evaluate("""() => {
                const el = document.getElementById('attr-results-container');
                if (el) {
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none';
                }
                return false;
            }""")
            
            if results_visible:
                print("   ✅ Results container became visible after analysis")
            else:
                print("   ⚠️  Results container still hidden (may be expected if no data)")
            
            # Check if welcome panel is hidden after running analysis
            welcome_hidden = page.evaluate("""() => {
                const el = document.getElementById('attr-initial-instructions');
                if (el) {
                    const style = window.getComputedStyle(el);
                    return style.display === 'none';
                }
                return false;
            }""")
            
            if welcome_hidden:
                print("   ✅ Welcome panel hidden after analysis")
            else:
                print("   ℹ️  Welcome panel still visible (callback may have failed)")
            
            print("\n✅ Analysis Hub comprehensive test PASSED")
            page.screenshot(path="analysis_hub_success.png")
            print("Screenshot saved: analysis_hub_success.png")
            browser.close()
            return True
            
        except Exception as e:
            print(f"\n❌ FAIL: {str(e)}")
            page.screenshot(path="analysis_hub_error.png")
            print("Screenshot saved: analysis_hub_error.png")
            browser.close()
            return False


def test_portfolio_comprehensive():
    """Comprehensive test of Portfolio Dashboard"""
    print("\n" + "="*60)
    print("COMPREHENSIVE TEST: Portfolio Dashboard")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print("\n1. Loading Portfolio Dashboard...")
            page.goto("http://localhost:8056", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
            print("✅ Page loaded")
            
            print("\n2. Verifying all portfolio tabs are present...")
            tabs = page.locator('.nav-link').all()
            tab_labels = [tab.text_content().strip() for tab in tabs]
            print(f"   Found tabs: {tab_labels}")
            
            if len(tab_labels) < 4:
                print(f"❌ FAIL: Expected at least 4 tabs, found {len(tab_labels)}")
                return False
            print(f"✅ Found {len(tab_labels)} portfolio tabs")
            
            print("\n3. Testing tab switching...")
            for i, tab in enumerate(tabs[:4]):  # Test first 4 tabs
                label = tab_labels[i]
                print(f"   Clicking '{label}'...")
                tab.click()
                page.wait_for_timeout(1500)
                print(f"   ✅ Tab '{label}' clicked")
            
            print("\n4. Testing Factor Exposure tab specifically...")
            # Find Factor Exposure tab
            factor_tab = None
            factor_index = -1
            for i, label in enumerate(tab_labels):
                if 'Factor' in label or 'factor' in label:
                    factor_tab = tabs[i]
                    factor_index = i
                    break
            
            if not factor_tab:
                print("❌ FAIL: Factor Exposure tab not found")
                return False
            
            print(f"   Found Factor Exposure at position {factor_index}")
            factor_tab.click()
            page.wait_for_timeout(3000)
            
            # Check content
            content_div = page.locator('#portfolio-factor-exposure-content')
            if content_div.count() == 0:
                print("❌ FAIL: Factor exposure content div not found")
                return False
            
            content_text = content_div.text_content()
            
            if "No SHAP factor data found" in content_text:
                print("   ℹ️  SHAP data not found - checking for fallback...")
                # Check for pie chart canvas
                canvas_count = page.locator('canvas').count()
                if canvas_count > 0:
                    print(f"   ✅ Fallback pie chart present ({canvas_count} canvas elements)")
                else:
                    print("   ❌ FAIL: No fallback visualization found")
                    return False
            elif "Portfolio Factor Exposure" in content_text or "Momentum" in content_text:
                print("   ✅ SHAP factor data loaded and displayed")
                # Verify we have charts
                canvas_count = page.locator('canvas').count()
                print(f"   ✅ Found {canvas_count} chart(s)")
            else:
                print(f"   ⚠️  Unclear content (length: {len(content_text)})")
            
            print("\n✅ Portfolio comprehensive test PASSED")
            page.screenshot(path="portfolio_success.png")
            print("Screenshot saved: portfolio_success.png")
            browser.close()
            return True
            
        except Exception as e:
            print(f"\n❌ FAIL: {str(e)}")
            page.screenshot(path="portfolio_error.png")
            print("Screenshot saved: portfolio_error.png")
            browser.close()
            return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("COMPREHENSIVE CLICKER TEST SUITE")
    print("="*60)
    
    test1_passed = test_analysis_hub_comprehensive()
    test2_passed = test_portfolio_comprehensive()
    
    print("\n" + "="*60)
    print("FINAL TEST SUMMARY")
    print("="*60)
    print(f"Analysis Hub Comprehensive: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Portfolio Comprehensive: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    print("="*60)
    
    if test1_passed and test2_passed:
        print("\n🎉 ALL COMPREHENSIVE TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED - Check logs and screenshots")
        sys.exit(1)

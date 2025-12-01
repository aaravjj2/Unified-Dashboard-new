#!/usr/bin/env python3
"""Test Analysis Hub and Portfolio Dashboard fixes"""
from playwright.sync_api import sync_playwright
import sys

def test_analysis_hub():
    """Test Analysis Hub welcome panel and tab structure"""
    print("\n" + "="*60)
    print("TEST 1: Analysis Hub - Welcome Panel & Tab Structure")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print("\n1. Loading Analysis Hub...")
            page.goto("http://localhost:8054", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
            print("✅ Page loaded")
            
            print("\n2. Checking for welcome panel...")
            welcome = page.locator('#attr-initial-instructions')
            if welcome.count() > 0 and welcome.is_visible():
                text = welcome.text_content()
                if "Welcome to Attribution Analysis" in text:
                    print("✅ Welcome panel visible with correct text")
                else:
                    print(f"❌ FAIL: Welcome panel text incorrect: {text[:100]}")
                    return False
            else:
                print(f"❌ FAIL: Welcome panel not found or not visible (count: {welcome.count()})")
                # Take screenshot for debugging
                page.screenshot(path="analysis_hub_fail.png")
                print("Screenshot saved: analysis_hub_fail.png")
                return False
            
            print("\n3. Checking tab structure...")
            tabs = page.locator('.nav-link').all()
            tab_labels = [tab.text_content().strip() for tab in tabs]
            print(f"Found tabs: {tab_labels}")
            
            if len(tab_labels) >= 2:
                print(f"✅ Found {len(tab_labels)} tabs")
            else:
                print(f"❌ FAIL: Expected at least 2 tabs, found {len(tab_labels)}")
                return False
            
            print("\n4. Checking if tabs are clickable...")
            if len(tabs) > 0:
                tabs[0].click()
                page.wait_for_timeout(1000)
                print("✅ First tab clickable")
            
            print("\n✅ Analysis Hub test PASSED")
            browser.close()
            return True
            
        except Exception as e:
            print(f"\n❌ FAIL: {str(e)}")
            page.screenshot(path="analysis_hub_error.png")
            print("Screenshot saved: analysis_hub_error.png")
            browser.close()
            return False


def test_portfolio_factor_exposure():
    """Test Portfolio Dashboard Factor Exposure tab"""
    print("\n" + "="*60)
    print("TEST 2: Portfolio Dashboard - Factor Exposure")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print("\n1. Loading Portfolio Dashboard...")
            page.goto("http://localhost:8056", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
            print("✅ Page loaded")
            
            print("\n2. Finding Factor Exposure tab...")
            tabs = page.locator('.nav-link').all()
            factor_tab = None
            for i, tab in enumerate(tabs):
                text = tab.text_content()
                if 'Factor' in text or 'factor' in text:
                    factor_tab = tab
                    print(f"✅ Found Factor Exposure tab at position {i}")
                    break
            
            if not factor_tab:
                print("❌ FAIL: Factor Exposure tab not found")
                return False
            
            print("\n3. Clicking Factor Exposure tab...")
            factor_tab.click()
            page.wait_for_timeout(3000)
            print("✅ Tab clicked")
            
            print("\n4. Checking content...")
            content = page.locator('#portfolio-factor-exposure-content').text_content()
            
            if "No SHAP factor data found" in content:
                print("⚠️  SHAP data not found message present")
                # Check for fallback pie chart
                pie_chart = page.locator('canvas').count()
                if pie_chart > 0:
                    print("✅ Fallback pie chart found")
                else:
                    print("❌ FAIL: No fallback pie chart found")
                    return False
            elif len(content) > 200:
                print(f"✅ Factor Exposure content loaded ({len(content)} chars)")
                if "Portfolio Factor Exposure" in content or "Momentum" in content:
                    print("✅ Factor data present")
                else:
                    print("⚠️  Content present but unclear format")
            else:
                print(f"❌ FAIL: Content too short ({len(content)} chars)")
                return False
            
            print("\n✅ Portfolio Factor Exposure test PASSED")
            browser.close()
            return True
            
        except Exception as e:
            print(f"\n❌ FAIL: {str(e)}")
            page.screenshot(path="portfolio_factor_error.png")
            print("Screenshot saved: portfolio_factor_error.png")
            browser.close()
            return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("AUTOMATED TEST SUITE")
    print("="*60)
    
    test1_passed = test_analysis_hub()
    test2_passed = test_portfolio_factor_exposure()
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Analysis Hub: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Portfolio Factor Exposure: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    print("="*60)
    
    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED")
        sys.exit(1)

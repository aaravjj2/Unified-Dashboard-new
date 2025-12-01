#!/usr/bin/env python3
"""
Comprehensive Market Trends Button Test with Snapshots
Tests all 3 buttons with visual verification
"""

from playwright.sync_api import sync_playwright
import time
import os
from pathlib import Path

def test_market_trends_with_snapshots():
    """Test all 3 Market Trends buttons with before/after snapshots"""
    
    # Create screenshots directory
    screenshot_dir = Path("/home/aarav/unified-dashboard/test_screenshots")
    screenshot_dir.mkdir(exist_ok=True)
    
    with sync_playwright() as p:
        # Launch browser with visible window
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        print("=" * 80)
        print("MARKET TRENDS BUTTON COMPREHENSIVE TEST")
        print("=" * 80)
        
        # Track console errors (should be 0 now)
        console_errors = []
        def handle_console(msg):
            if msg.type == 'error':
                console_errors.append(msg.text)
        
        page.on('console', handle_console)
        
        # Step 1: Load dashboard
        print("\n📍 Step 1: Loading dashboard...")
        page.goto('http://localhost:8051', timeout=60000)
        page.wait_for_load_state('networkidle', timeout=60000)
        time.sleep(5)
        
        # Take initial screenshot
        page.screenshot(path=str(screenshot_dir / "01_dashboard_loaded.png"), full_page=True)
        print("   ✅ Dashboard loaded - Screenshot saved")
        
        # Step 2: Navigate to Market Trends
        print("\n📍 Step 2: Navigating to Market Trends tab...")
        
        # Try multiple selectors to find the tab
        tab_found = False
        selectors = [
            'text="Market Trends"',
            '[href="#market_trends"]',
            'button:has-text("Market Trends")',
            'a:has-text("Market Trends")',
        ]
        
        for selector in selectors:
            try:
                element = page.locator(selector).first
                if element.count() > 0 and element.is_visible():
                    element.click()
                    tab_found = True
                    print(f"   ✅ Clicked Market Trends tab using: {selector}")
                    break
            except Exception:
                continue
        
        if not tab_found:
            print("   ❌ Could not find Market Trends tab")
            browser.close()
            return
        
        time.sleep(3)
        page.screenshot(path=str(screenshot_dir / "02_market_trends_tab.png"), full_page=True)
        print("   ✅ Market Trends tab opened - Screenshot saved")
        
        # Step 3: Test reload-model button
        print("\n📍 Step 3: Testing reload-model button...")
        try:
            reload_btn = page.locator('#reload-model')
            if reload_btn.count() > 0 and reload_btn.is_visible():
                page.screenshot(path=str(screenshot_dir / "03a_before_reload.png"), full_page=True)
                
                # Get status before click
                status_elem = page.locator('#model-status')
                status_before = status_elem.inner_text() if status_elem.count() > 0 else "N/A"
                print(f"   Status before: {status_before}")
                
                # Click button
                reload_btn.click()
                print("   ✅ Reload Model button clicked")
                time.sleep(3)
                
                page.screenshot(path=str(screenshot_dir / "03b_after_reload.png"), full_page=True)
                
                # Get status after click
                status_after = status_elem.inner_text() if status_elem.count() > 0 else "N/A"
                print(f"   Status after: {status_after}")
                
                if status_before != status_after:
                    print("   ✅ Status changed - Button works!")
                else:
                    print("   ℹ️  Status unchanged (may be expected if no cache)")
            else:
                print("   ⚠️  reload-model button not found or not visible")
        except Exception as e:
            print(f"   ❌ Error testing reload-model: {e}")
        
        # Step 4: Test toggle-brief button
        print("\n📍 Step 4: Testing toggle-brief button...")
        try:
            toggle_btn = page.locator('#toggle-brief')
            if toggle_btn.count() > 0 and toggle_btn.is_visible():
                page.screenshot(path=str(screenshot_dir / "04a_before_toggle.png"), full_page=True)
                
                # Check brief visibility before
                brief_elem = page.locator('#full-brief')
                visible_before = brief_elem.is_visible() if brief_elem.count() > 0 else False
                print(f"   Brief visible before: {visible_before}")
                
                # Click button
                toggle_btn.click()
                print("   ✅ Toggle Brief button clicked")
                time.sleep(2)
                
                page.screenshot(path=str(screenshot_dir / "04b_after_toggle.png"), full_page=True)
                
                # Check brief visibility after
                visible_after = brief_elem.is_visible() if brief_elem.count() > 0 else False
                print(f"   Brief visible after: {visible_after}")
                
                if visible_before != visible_after:
                    print("   ✅ Visibility toggled - Button works!")
                else:
                    print("   ℹ️  Visibility unchanged")
                
                # Toggle back
                toggle_btn.click()
                time.sleep(1)
            else:
                print("   ⚠️  toggle-brief button not found or not visible")
        except Exception as e:
            print(f"   ❌ Error testing toggle-brief: {e}")
        
        # Step 5: Test CSV download button
        print("\n📍 Step 5: Testing CSV download button...")
        try:
            csv_btn = page.locator('#mt-download-btn')
            if csv_btn.count() > 0 and csv_btn.is_visible():
                page.screenshot(path=str(screenshot_dir / "05a_before_download.png"), full_page=True)
                
                # Set up download handler
                with page.expect_download(timeout=10000) as download_info:
                    csv_btn.click()
                    print("   ✅ Download CSV button clicked")
                
                try:
                    download = download_info.value
                    download_path = screenshot_dir / download.suggested_filename
                    download.save_as(str(download_path))
                    print(f"   ✅ CSV downloaded: {download.suggested_filename}")
                    print(f"   ✅ Saved to: {download_path}")
                except Exception as e:
                    print(f"   ℹ️  Download not triggered: {e}")
                
                page.screenshot(path=str(screenshot_dir / "05b_after_download.png"), full_page=True)
            else:
                print("   ⚠️  mt-download-btn button not found or not visible")
        except Exception as e:
            print(f"   ❌ Error testing CSV download: {e}")
        
        # Step 6: Test tab navigation (verify no callback errors)
        print("\n📍 Step 6: Testing tab navigation for callback errors...")
        tabs_to_test = [
            ('text="Market Forecast"', 'Market Forecast'),
            ('text="Weekly Picks"', 'Weekly Picks'),
            ('text="Market Trends"', 'Market Trends'),
        ]
        
        for selector, tab_name in tabs_to_test:
            try:
                tab = page.locator(selector).first
                if tab.count() > 0 and tab.is_visible():
                    tab.click()
                    print(f"   ✅ Navigated to {tab_name}")
                    time.sleep(2)
            except Exception as e:
                print(f"   ⚠️  Could not navigate to {tab_name}: {e}")
        
        page.screenshot(path=str(screenshot_dir / "06_tab_navigation_test.png"), full_page=True)
        
        # Final report
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Console errors detected: {len(console_errors)}")
        if console_errors:
            print("\nConsole Errors:")
            for i, error in enumerate(console_errors[:5], 1):
                print(f"  {i}. {error[:100]}")
        else:
            print("✅ No console errors - Clean execution!")
        
        print(f"\n📁 Screenshots saved to: {screenshot_dir}")
        print(f"   Total screenshots: {len(list(screenshot_dir.glob('*.png')))}")
        
        # Keep browser open for manual inspection
        print("\n⏳ Browser will stay open for 15 seconds for manual inspection...")
        time.sleep(15)
        
        browser.close()
        
        print("\n" + "=" * 80)
        print("✅ TEST COMPLETE")
        print("=" * 80)

if __name__ == '__main__':
    test_market_trends_with_snapshots()

"""
Comprehensive Market Trends Button Testing - All Buttons
Tests EVERY button in Market Trends tab with screenshots and job completion verification.
"""
from playwright.sync_api import sync_playwright
import time
from datetime import datetime
import os

# Create screenshots directory
SCREENSHOT_DIR = "/mnt/c/Aarav/fin_env/unified-dashboard/tests/screenshots_market_trends"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def save_screenshot(page, name):
    """Save screenshot with timestamp."""
    timestamp = datetime.now().strftime("%H%M%S")
    filepath = f"{SCREENSHOT_DIR}/{timestamp}_{name}.png"
    page.screenshot(path=filepath)
    print(f"   📸 Screenshot saved: {filepath}")
    return filepath

def wait_for_result(page, check_selector, description, max_wait=60):
    """Wait for a result indicator to appear."""
    print(f"   ⏳ Waiting for {description} (max {max_wait}s)...")
    start = time.time()
    while time.time() - start < max_wait:
        try:
            if page.locator(check_selector).count() > 0:
                content = page.locator(check_selector).inner_text(timeout=2000)
                if len(content) > 50:
                    elapsed = int(time.time() - start)
                    print(f"   ✅ {description} appeared after {elapsed}s")
                    return True, content[:200]
        except:
            pass
        time.sleep(2)
    
    elapsed = int(time.time() - start)
    print(f"   ❌ {description} did NOT appear after {elapsed}s")
    return False, None

print("=" * 80)
print("COMPREHENSIVE MARKET TRENDS BUTTON TEST - ALL BUTTONS")
print("=" * 80)
print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Screenshots will be saved to: {SCREENSHOT_DIR}")
print()

results = {}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()
    
    # Capture console for debugging
    console_messages = []
    page.on('console', lambda msg: console_messages.append(f"{msg.type}: {msg.text}"))
    
    try:
        # STEP 0: Load dashboard
        print("📍 STEP 0: Loading dashboard...")
        page.goto('http://localhost:8050', wait_until='domcontentloaded')
        time.sleep(4)
        save_screenshot(page, "00_dashboard_loaded")
        print("   ✅ Dashboard loaded")
        
        # STEP 1: Navigate to Market Trends
        print("\n📍 STEP 1: Clicking Market Trends tab...")
        page.click('#tab-market_trends')
        time.sleep(3)
        save_screenshot(page, "01_market_trends_tab")
        print("   ✅ Market Trends tab active")
        
        # Check initial state
        table_visible = page.is_visible('#news-table')
        print(f"   📊 News table visible: {table_visible}")
        
        # ============================================================
        # BUTTON 1: Run Full Analysis (PRIMARY BUTTON)
        # ============================================================
        print("\n" + "=" * 80)
        print("🔘 BUTTON TEST 1: Run Full Analysis")
        print("=" * 80)
        
        btn_visible = page.is_visible('#run-btn')
        print(f"   Button visible: {btn_visible}")
        
        if btn_visible:
            # Get initial results state
            initial_results = page.locator('#results-area').inner_text(timeout=2000)
            print(f"   Initial results length: {len(initial_results)}")
            
            # Click button
            print("   🖱️  Clicking 'Run Full Analysis' button...")
            page.click('#run-btn')
            save_screenshot(page, "02_run_analysis_clicked")
            
            # Wait for results to update
            success, content = wait_for_result(
                page, 
                '#results-area', 
                "analysis results",
                max_wait=90
            )
            
            if success:
                save_screenshot(page, "03_run_analysis_complete")
                # Check if compact brief updated
                try:
                    brief = page.locator('#compact-brief').inner_text(timeout=2000)
                    print(f"   📝 Compact brief length: {len(brief)}")
                except:
                    print("   ⚠️  Compact brief not found")
                
                results['run_analysis'] = '✅ WORKING'
            else:
                save_screenshot(page, "03_run_analysis_FAILED")
                results['run_analysis'] = '❌ NO RESPONSE'
        else:
            results['run_analysis'] = '❌ BUTTON NOT VISIBLE'
        
        time.sleep(2)
        
        # ============================================================
        # BUTTON 2: Reload Model
        # ============================================================
        print("\n" + "=" * 80)
        print("🔘 BUTTON TEST 2: Reload Model")
        print("=" * 80)
        
        btn_visible = page.is_visible('#reload-model')
        print(f"   Button visible: {btn_visible}")
        
        if btn_visible:
            print("   🖱️  Clicking 'Reload Model' button...")
            page.click('#reload-model')
            save_screenshot(page, "04_reload_model_clicked")
            
            # Check for model status update
            time.sleep(3)
            try:
                model_status = page.locator('#model-status').inner_text(timeout=2000)
                print(f"   📝 Model status: {model_status[:100]}")
                if len(model_status) > 10:
                    results['reload_model'] = '✅ WORKING'
                    save_screenshot(page, "05_reload_model_complete")
                else:
                    results['reload_model'] = '⚠️  STATUS EMPTY'
            except:
                results['reload_model'] = '❌ NO STATUS CHANGE'
                save_screenshot(page, "05_reload_model_FAILED")
        else:
            results['reload_model'] = '❌ BUTTON NOT VISIBLE'
        
        time.sleep(2)
        
        # ============================================================
        # BUTTON 3: Refresh Cached Display
        # ============================================================
        print("\n" + "=" * 80)
        print("🔘 BUTTON TEST 3: Refresh Cached Display")
        print("=" * 80)
        
        btn_visible = page.is_visible('#refresh-cached')
        print(f"   Button visible: {btn_visible}")
        
        if btn_visible:
            # Get current table row count
            current_rows = page.locator('#news-table tbody tr').count()
            print(f"   Current table rows: {current_rows}")
            
            print("   🖱️  Clicking 'Refresh Cached Display' button...")
            page.click('#refresh-cached')
            save_screenshot(page, "06_refresh_cached_clicked")
            
            # Wait for potential refresh
            time.sleep(4)
            new_rows = page.locator('#news-table tbody tr').count()
            print(f"   New table rows: {new_rows}")
            
            if new_rows > 0:
                results['refresh_cached'] = '✅ WORKING'
                save_screenshot(page, "07_refresh_cached_complete")
            else:
                results['refresh_cached'] = '⚠️  NO TABLE CHANGE'
                save_screenshot(page, "07_refresh_cached_FAILED")
        else:
            results['refresh_cached'] = '❌ BUTTON NOT VISIBLE'
        
        time.sleep(2)
        
        # ============================================================
        # BUTTON 4: Backtest Trend Signals
        # ============================================================
        print("\n" + "=" * 80)
        print("🔘 BUTTON TEST 4: Backtest Trend Signals")
        print("=" * 80)
        
        btn_visible = page.is_visible('#backtest-btn')
        print(f"   Button visible: {btn_visible}")
        
        if btn_visible:
            print("   🖱️  Clicking 'Backtest Trend Signals' button...")
            page.click('#backtest-btn')
            save_screenshot(page, "08_backtest_clicked")
            
            # Wait for backtest results
            success, content = wait_for_result(
                page,
                '#results-area',
                "backtest results",
                max_wait=120  # Backtests can take longer
            )
            
            if success:
                # Check if "backtest" appears in results
                if 'backtest' in content.lower() or 'sharpe' in content.lower():
                    results['backtest'] = '✅ WORKING'
                    save_screenshot(page, "09_backtest_complete")
                else:
                    results['backtest'] = '⚠️  UNEXPECTED RESULTS'
                    save_screenshot(page, "09_backtest_UNEXPECTED")
            else:
                results['backtest'] = '❌ NO RESPONSE'
                save_screenshot(page, "09_backtest_FAILED")
        else:
            results['backtest'] = '❌ BUTTON NOT VISIBLE'
        
        time.sleep(2)
        
        # ============================================================
        # BUTTON 5: Debug Logs
        # ============================================================
        print("\n" + "=" * 80)
        print("🔘 BUTTON TEST 5: Debug Logs")
        print("=" * 80)
        
        btn_visible = page.is_visible('#debug-logs-btn')
        print(f"   Button visible: {btn_visible}")
        
        if btn_visible:
            print("   🖱️  Clicking 'Debug Logs' button...")
            page.click('#debug-logs-btn')
            time.sleep(2)
            save_screenshot(page, "10_debug_logs_clicked")
            
            # Check if modal appeared
            modal_visible = page.is_visible('#debug-logs-modal')
            if modal_visible:
                modal_style = page.locator('#debug-logs-modal').get_attribute('style')
                if 'none' not in modal_style:
                    results['debug_logs'] = '✅ WORKING (modal opened)'
                    save_screenshot(page, "11_debug_logs_modal_open")
                    
                    # Close modal
                    page.click('#close-debug-modal')
                    time.sleep(1)
                else:
                    results['debug_logs'] = '⚠️  MODAL HIDDEN'
            else:
                results['debug_logs'] = '❌ MODAL NOT FOUND'
                save_screenshot(page, "11_debug_logs_FAILED")
        else:
            results['debug_logs'] = '❌ BUTTON NOT VISIBLE'
        
        time.sleep(2)
        
        # ============================================================
        # BUTTON 6: Toggle Full Brief
        # ============================================================
        print("\n" + "=" * 80)
        print("🔘 BUTTON TEST 6: Toggle Full Brief")
        print("=" * 80)
        
        btn_visible = page.is_visible('#toggle-brief')
        print(f"   Button visible: {btn_visible}")
        
        if btn_visible:
            # Check initial state
            brief_visible = page.is_visible('#full-brief')
            initial_style = page.locator('#full-brief').get_attribute('style') if brief_visible else 'none'
            print(f"   Initial brief display: {initial_style}")
            
            print("   🖱️  Clicking 'Toggle Full Brief' button...")
            page.click('#toggle-brief')
            time.sleep(2)
            save_screenshot(page, "12_toggle_brief_clicked")
            
            # Check if visibility toggled
            new_style = page.locator('#full-brief').get_attribute('style')
            print(f"   New brief display: {new_style}")
            
            if new_style != initial_style:
                results['toggle_brief'] = '✅ WORKING (toggled)'
                save_screenshot(page, "13_toggle_brief_complete")
            else:
                results['toggle_brief'] = '⚠️  NO TOGGLE DETECTED'
                save_screenshot(page, "13_toggle_brief_FAILED")
        else:
            results['toggle_brief'] = '❌ BUTTON NOT VISIBLE'
        
        time.sleep(2)
        
        # ============================================================
        # BUTTON 7: Download CSV
        # ============================================================
        print("\n" + "=" * 80)
        print("🔘 BUTTON TEST 7: Download CSV")
        print("=" * 80)
        
        btn_visible = page.is_visible('#mt-download-btn')
        print(f"   Button visible: {btn_visible}")
        
        if btn_visible:
            print("   🖱️  Clicking 'Download CSV' button...")
            
            # Set up download listener
            download_started = False
            with page.expect_download(timeout=10000) as download_info:
                page.click('#mt-download-btn')
                try:
                    download = download_info.value
                    download_started = True
                    print(f"   📥 Download started: {download.suggested_filename}")
                except:
                    print("   ⚠️  No download triggered")
            
            save_screenshot(page, "14_download_csv_clicked")
            
            if download_started:
                results['download_csv'] = '✅ WORKING (download triggered)'
            else:
                results['download_csv'] = '⚠️  NO DOWNLOAD'
        else:
            results['download_csv'] = '❌ BUTTON NOT VISIBLE'
        
        # ============================================================
        # FINAL SCREENSHOT
        # ============================================================
        print("\n📸 Capturing final state...")
        save_screenshot(page, "99_final_state")
        
        # Check console for errors
        print("\n📋 Console Error Summary:")
        error_messages = [msg for msg in console_messages if 'error' in msg.lower()]
        if error_messages:
            print(f"   ⚠️  Found {len(error_messages)} console errors:")
            for err in error_messages[:5]:
                print(f"      - {err[:100]}")
        else:
            print("   ✅ No console errors detected")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        save_screenshot(page, "ERROR_crash")
    
    finally:
        print("\n⏳ Keeping browser open for 5 seconds for manual inspection...")
        time.sleep(5)
        browser.close()

# ============================================================
# RESULTS SUMMARY
# ============================================================
print("\n" + "=" * 80)
print("📊 BUTTON TEST RESULTS SUMMARY")
print("=" * 80)

for button_name, status in results.items():
    icon = "✅" if "✅" in status else ("⚠️" if "⚠️" in status else "❌")
    print(f"{icon} {button_name.replace('_', ' ').title()}: {status}")

working_count = sum(1 for s in results.values() if '✅' in s)
total_count = len(results)
success_rate = (working_count / total_count * 100) if total_count > 0 else 0

print("\n" + "=" * 80)
print(f"OVERALL: {working_count}/{total_count} buttons working ({success_rate:.1f}%)")
print("=" * 80)
print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Screenshots saved to: {SCREENSHOT_DIR}")
print("=" * 80)

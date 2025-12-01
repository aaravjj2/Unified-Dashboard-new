#!/usr/bin/env python3
"""
Market Trends - REAL Functional Test
Tests actual job queue status → processing → table update flow
"""
import os
import sys
import time
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:8050"

def start_dashboard():
    """Start dashboard."""
    print("🚀 Starting dashboard...")
    env = os.environ.copy()
    env.update({'AZURE_ENABLED': 'false', 'OPTIONS_DETERMINISTIC': '1', 'DASH_PORT': '8050'})
    
    proc = subprocess.Popen(
        ['python', 'financial_dashboard/index.py'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
        cwd='/home/aarav/unified-dashboard'
    )
    
    print(f"   PID: {proc.pid}, waiting for startup...")
    
    import requests
    for i in range(60):
        try:
            if requests.get(f"{BASE_URL}/_dash-layout", timeout=2).status_code == 200:
                print(f"   ✅ Ready after {i+1}s")
                return proc
        except:
            time.sleep(1)
    
    proc.kill()
    return None

def test_run_analysis_full_flow(page):
    """Test the complete Run Analysis flow with proper status checks."""
    print("\n" + "="*80)
    print("TESTING FULL RUN ANALYSIS FLOW")
    print("="*80)
    
    # Navigate and activate tab
    print("\n📍 Step 1: Loading dashboard...")
    page.goto(BASE_URL, wait_until='networkidle', timeout=30000)
    print("   ✅ Dashboard loaded")
    
    print("\n📍 Step 2: Activating Market Trends tab...")
    page.locator('text=Market Trends').first.click()
    time.sleep(3)
    print("   ✅ Market Trends activated")
    
    # Check initial table state (should be placeholder)
    print("\n📍 Step 3: Checking initial table state...")
    try:
        initial_table = page.locator('table').first
        initial_rows = initial_table.locator('tbody tr').all()
        print(f"   ℹ️  Initial table has {len(initial_rows)} rows (placeholder)")
        
        # Check if it's placeholder data
        if len(initial_rows) == 5:
            first_row_text = initial_rows[0].text_content()
            print(f"   ℹ️  First row: {first_row_text[:80]}...")
            if "AAPL" in first_row_text or "Placeholder" in first_row_text:
                print("   ⚠️  CONFIRMED: Table shows placeholder data")
    except:
        print("   ℹ️  No initial table found")
    
    # Click Run Analysis
    print("\n📍 Step 4: Clicking Run Analysis button...")
    run_btn = page.locator('#mt-run-analysis-btn').first
    run_btn.wait_for(state='visible', timeout=10000)
    
    # Take screenshot before click
    page.screenshot(path='/tmp/before_click.png', full_page=True)
    print("   📸 Screenshot saved: /tmp/before_click.png")
    
    run_btn.click()
    print("   ✅ Button clicked")
    
    # Check for immediate status update (queuing/starting)
    print("\n📍 Step 5: Checking for queue/start status...")
    time.sleep(3)
    
    # Take screenshot after click
    page.screenshot(path='/tmp/after_click.png', full_page=True)
    print("   📸 Screenshot saved: /tmp/after_click.png")
    
    status_found = False
    try:
        # Look for status indicators
        status_divs = page.locator('[id*="status"]').all()
        for status_div in status_divs:
            status_text = status_div.text_content()
            if status_text and ('job' in status_text.lower() or 'started' in status_text.lower() or 'running' in status_text.lower()):
                print(f"   ✅ STATUS FOUND: '{status_text}'")
                status_found = True
                break
        
        if not status_found:
            print("   ❌ NO STATUS UPDATE - button may not be working!")
            return {'result': 'FAIL', 'reason': 'No status update after click'}
            
    except Exception as e:
        print(f"   ❌ Error checking status: {e}")
        return {'result': 'FAIL', 'reason': str(e)}
    
    # Wait for job completion (poll for table update)
    print("\n📍 Step 6: Waiting for job completion and table update...")
    max_wait = 30  # 30 seconds max
    start_wait = time.time()
    table_updated = False
    
    while time.time() - start_wait < max_wait:
        try:
            # Check if table has updated (more than 5 rows or different content)
            current_table = page.locator('table').first
            current_rows = current_table.locator('tbody tr').all()
            
            if len(current_rows) != len(initial_rows):
                print(f"   ✅ TABLE UPDATED: {len(initial_rows)} → {len(current_rows)} rows")
                table_updated = True
                break
            
            # Also check if first row changed
            if len(current_rows) > 0:
                current_first = current_rows[0].text_content()
                initial_first = initial_rows[0].text_content() if len(initial_rows) > 0 else ""
                if current_first != initial_first:
                    print(f"   ✅ TABLE CONTENT UPDATED")
                    table_updated = True
                    break
                    
        except:
            pass
        
        time.sleep(2)
        elapsed = time.time() - start_wait
        if int(elapsed) % 5 == 0:
            print(f"   ⏳ Waiting... ({int(elapsed)}s elapsed)")
    
    if not table_updated:
        print(f"   ⚠️  Table did not update within {max_wait}s")
        print("   Checking final status...")
        try:
            status_divs = page.locator('[id*="status"]').all()
            for status_div in status_divs:
                final_status = status_div.text_content()
                if final_status:
                    print(f"   Final status: '{final_status}'")
        except:
            pass
        return {'result': 'PARTIAL', 'reason': 'Job started but table not updated in time'}
    
    # Verify final table has real data
    print("\n📍 Step 7: Verifying final table content...")
    try:
        final_table = page.locator('table').first
        final_rows = final_table.locator('tbody tr').all()
        print(f"   ✅ Final table has {len(final_rows)} rows")
        
        if len(final_rows) > 0:
            sample_row = final_rows[0].text_content()
            print(f"   Sample row: {sample_row[:100]}...")
            
            # Check for real stock data indicators
            has_ticker = any(ticker in sample_row for ticker in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META'])
            has_percentage = '%' in sample_row
            has_price = '$' in sample_row
            
            if has_ticker and (has_percentage or has_price):
                print(f"   ✅ TABLE HAS REAL DATA (tickers + prices/percentages)")
                return {'result': 'PASS', 'rows': len(final_rows), 'flow': 'Complete'}
            else:
                print(f"   ⚠️  Table updated but may still be placeholder")
                return {'result': 'PARTIAL', 'reason': 'Table updated but content unclear'}
                
    except Exception as e:
        print(f"   ❌ Error verifying table: {e}")
        return {'result': 'FAIL', 'reason': str(e)}

def main():
    print("=" * 80)
    print("MARKET TRENDS - REAL FUNCTIONAL TEST")
    print("Testing: Queue Status → Processing → Table Update")
    print("=" * 80)
    
    dash_proc = start_dashboard()
    if not dash_proc:
        print("\n❌ Dashboard failed to start")
        return 1
    
    try:
        with sync_playwright() as p:
            print("\n🌐 Launching browser (headed)...")
            browser = p.chromium.launch(headless=False, slow_mo=300)
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = context.new_page()
            
            # Capture console logs
            console_logs = []
            page.on('console', lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
            
            print("   ✅ Browser ready")
            
            result = test_run_analysis_full_flow(page)
            
            print("\n⏳ Keeping browser open for 8 seconds to review...")
            time.sleep(8)
            
            # Print console logs
            if console_logs:
                print("\n📋 Console Logs:")
                for log in console_logs[-20:]:  # Last 20 logs
                    print(f"   {log}")
            
            browser.close()
        
        # Summary
        print("\n" + "=" * 80)
        print("TEST RESULT")
        print("=" * 80)
        print(f"Status: {result['result']}")
        if 'reason' in result:
            print(f"Reason: {result['reason']}")
        if 'rows' in result:
            print(f"Final rows: {result['rows']}")
        if 'flow' in result:
            print(f"Flow: {result['flow']}")
        
        print("=" * 80)
        
        if result['result'] == 'PASS':
            print("\n✅ TEST PASSED - Run Analysis works correctly!")
            return 0
        elif result['result'] == 'PARTIAL':
            print("\n⚠️  TEST PARTIAL - Some functionality working")
            return 1
        else:
            print("\n❌ TEST FAILED")
            return 1
        
    finally:
        print("\n🛑 Stopping dashboard...")
        dash_proc.terminate()
        try:
            dash_proc.wait(timeout=5)
        except:
            dash_proc.kill()
        print("   ✅ Stopped")

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted")
        sys.exit(1)

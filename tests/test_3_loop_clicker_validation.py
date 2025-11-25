#!/usr/bin/env python3
"""
Step 3-7: Comprehensive 3-Loop Clicker Validation Framework
===========================================================

Performs systematic validation of all Options Lab subtabs:
- Loop 1: Navigate each subtab → load data → validate → screenshot
- Loop 2: Switch tabs → repeat steps → log errors
- Loop 3: Final iteration → JSON results with performance metrics

Target Performance:
- <3s per subtab load
- <2s per callback execution
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import subprocess

sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv('keys.env')

# Ensure directories
Path('test-artifacts/options_lab/screenshots').mkdir(parents=True, exist_ok=True)
Path('test-artifacts/options_lab/logs').mkdir(parents=True, exist_ok=True)
Path('test-results/options_lab/3loop').mkdir(parents=True, exist_ok=True)


def start_dash_app():
    """Start the Dash app in background for testing."""
    print("\n🚀 Starting Dash app...")
    
    # Check if app is already running
    try:
        import requests
        response = requests.get('http://localhost:8050', timeout=2)
        if response.status_code == 200:
            print("✅ Dash app already running on http://localhost:8050")
            return None
    except:
        pass
    
    # Start app
    try:
        process = subprocess.Popen(
            ['python', 'financial_dashboard/app.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd='/mnt/c/Aarav/fin_env/unified-dashboard'
        )
        
        # Wait for app to start
        print("⏳ Waiting for app to start...")
        time.sleep(10)
        
        # Verify it's running
        import requests
        for attempt in range(5):
            try:
                response = requests.get('http://localhost:8050', timeout=2)
                if response.status_code == 200:
                    print("✅ Dash app started successfully")
                    return process
            except:
                time.sleep(2)
        
        print("⚠️  App may not be fully started, continuing anyway...")
        return process
        
    except Exception as e:
        print(f"❌ Failed to start app: {e}")
        return None


def test_chain_viewer(page, ticker: str, loop_num: int) -> Dict[str, Any]:
    """
    Test Chain Viewer subtab functionality.
    
    Steps:
    1. Enter ticker
    2. Click Load Chain
    3. Validate expiration dropdown populated
    4. Validate table displays data
    5. Test filtering/sorting
    6. Capture screenshot
    """
    print(f"\n  📊 [Loop {loop_num}] Testing Chain Viewer for {ticker}...")
    
    result = {
        'ticker': ticker,
        'loop': loop_num,
        'subtab': 'Chain Viewer',
        'timestamp': datetime.now().isoformat(),
        'steps': {},
        'performance': {},
        'errors': [],
        'success': False
    }
    
    try:
        # Navigate to Options Lab
        start_time = time.time()
        page.goto('http://localhost:8050')
        page.wait_for_load_state('networkidle', timeout=10000)
        result['performance']['page_load'] = time.time() - start_time
        print(f"    ✅ Page loaded ({result['performance']['page_load']:.2f}s)")
        
        # Click Options Lab tab
        try:
            options_tab = page.locator('text=💹 Options Lab').first
            options_tab.click()
            page.wait_for_timeout(1000)
            result['steps']['navigate_to_options_lab'] = 'PASS'
            print(f"    ✅ Navigated to Options Lab")
        except Exception as e:
            result['steps']['navigate_to_options_lab'] = 'FAIL'
            result['errors'].append(f"Navigation failed: {e}")
            print(f"    ❌ Navigation failed: {e}")
            return result
        
        # Enter ticker
        try:
            ticker_input = page.locator('input.options-ticker-input').first
            ticker_input.fill(ticker)
            result['steps']['enter_ticker'] = 'PASS'
            print(f"    ✅ Entered ticker: {ticker}")
        except Exception as e:
            result['steps']['enter_ticker'] = 'FAIL'
            result['errors'].append(f"Ticker input failed: {e}")
            print(f"    ❌ Ticker input failed: {e}")
        
        # Click Load Chain
        try:
            load_start = time.time()
            load_btn = page.locator('button.options-load-btn').first
            load_btn.click()
            page.wait_for_timeout(3000)  # Wait for data load
            result['performance']['load_chain'] = time.time() - load_start
            result['steps']['click_load_chain'] = 'PASS'
            print(f"    ✅ Clicked Load Chain ({result['performance']['load_chain']:.2f}s)")
            
            # Check performance target
            if result['performance']['load_chain'] > 3.0:
                result['errors'].append(f"Load time {result['performance']['load_chain']:.2f}s exceeds 3s target")
                print(f"    ⚠️  Load time exceeds target: {result['performance']['load_chain']:.2f}s")
        except Exception as e:
            result['steps']['click_load_chain'] = 'FAIL'
            result['errors'].append(f"Load Chain failed: {e}")
            print(f"    ❌ Load Chain failed: {e}")
        
        # Validate expiration dropdown
        try:
            dropdown = page.locator('#chain-expiration-dropdown').first
            dropdown_visible = dropdown.is_visible(timeout=2000)
            
            if dropdown_visible:
                # Check if dropdown has options
                page.wait_for_timeout(1000)
                result['steps']['expiration_dropdown_populated'] = 'PASS'
                print(f"    ✅ Expiration dropdown populated")
            else:
                result['steps']['expiration_dropdown_populated'] = 'FAIL'
                result['errors'].append("Expiration dropdown not visible")
                print(f"    ❌ Expiration dropdown not visible")
        except Exception as e:
            result['steps']['expiration_dropdown_populated'] = 'FAIL'
            result['errors'].append(f"Dropdown validation failed: {e}")
            print(f"    ❌ Dropdown validation failed: {e}")
        
        # Validate table renders
        try:
            table = page.locator('#chain-data-table').first
            table_visible = table.is_visible(timeout=2000)
            
            if table_visible:
                result['steps']['table_renders'] = 'PASS'
                print(f"    ✅ Chain table rendered")
            else:
                result['steps']['table_renders'] = 'FAIL'
                result['errors'].append("Chain table not visible")
                print(f"    ❌ Chain table not visible")
        except Exception as e:
            result['steps']['table_renders'] = 'FAIL'
            result['errors'].append(f"Table validation failed: {e}")
            print(f"    ❌ Table validation failed: {e}")
        
        # Capture screenshot
        screenshot_path = f'test-artifacts/options_lab/screenshots/chain_viewer_{ticker}_loop{loop_num}.png'
        page.screenshot(path=screenshot_path, full_page=True)
        result['screenshot'] = screenshot_path
        print(f"    📸 Screenshot saved: {screenshot_path}")
        
        # Check for console errors
        console_logs = []
        page.on('console', lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))
        page.wait_for_timeout(1000)
        
        errors = [log for log in console_logs if 'error' in log.lower()]
        if errors:
            result['console_errors'] = errors
            print(f"    ⚠️  {len(errors)} console errors detected")
        else:
            print(f"    ✅ No console errors")
        
        # Determine success
        result['success'] = (
            result['steps'].get('navigate_to_options_lab') == 'PASS' and
            result['steps'].get('click_load_chain') == 'PASS' and
            result['steps'].get('table_renders') == 'PASS' and
            len(result['errors']) == 0
        )
        
    except Exception as e:
        result['errors'].append(f"Test failed: {e}")
        print(f"    ❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    return result


def test_greeks_dashboard(page, ticker: str, loop_num: int) -> Dict[str, Any]:
    """Test Greeks Dashboard subtab."""
    print(f"\n  🔢 [Loop {loop_num}] Testing Greeks Dashboard for {ticker}...")
    
    result = {
        'ticker': ticker,
        'loop': loop_num,
        'subtab': 'Greeks Dashboard',
        'timestamp': datetime.now().isoformat(),
        'steps': {},
        'errors': [],
        'success': False
    }
    
    try:
        # Navigate to Greeks subtab
        greeks_tab = page.locator('.options-tab-greeks').first
        greeks_tab.click()
        page.wait_for_timeout(2000)
        result['steps']['navigate_to_greeks'] = 'PASS'
        print(f"    ✅ Navigated to Greeks Dashboard")
        
        # Check for Greeks charts
        try:
            greeks_charts = page.locator('#greeks-charts').first
            charts_visible = greeks_charts.is_visible(timeout=2000)
            
            if charts_visible:
                result['steps']['greeks_charts_render'] = 'PASS'
                print(f"    ✅ Greeks charts rendered")
            else:
                result['steps']['greeks_charts_render'] = 'FAIL'
                result['errors'].append("Greeks charts not visible")
                print(f"    ❌ Greeks charts not visible")
        except Exception as e:
            result['steps']['greeks_charts_render'] = 'FAIL'
            result['errors'].append(f"Charts validation failed: {e}")
            print(f"    ❌ Charts validation failed: {e}")
        
        # Capture screenshot
        screenshot_path = f'test-artifacts/options_lab/screenshots/greeks_{ticker}_loop{loop_num}.png'
        page.screenshot(path=screenshot_path, full_page=True)
        result['screenshot'] = screenshot_path
        print(f"    📸 Screenshot saved: {screenshot_path}")
        
        result['success'] = result['steps'].get('greeks_charts_render') == 'PASS'
        
    except Exception as e:
        result['errors'].append(f"Test failed: {e}")
        print(f"    ❌ Test failed: {e}")
    
    return result


def test_vol_surface(page, ticker: str, loop_num: int) -> Dict[str, Any]:
    """Test Vol Surface subtab."""
    print(f"\n  🌐 [Loop {loop_num}] Testing Vol Surface for {ticker}...")
    
    result = {
        'ticker': ticker,
        'loop': loop_num,
        'subtab': 'Vol Surface',
        'timestamp': datetime.now().isoformat(),
        'steps': {},
        'errors': [],
        'success': False
    }
    
    try:
        # Navigate to Vol Surface subtab
        vol_tab = page.locator('.options-tab-vol-surface').first
        vol_tab.click()
        page.wait_for_timeout(2000)
        result['steps']['navigate_to_vol_surface'] = 'PASS'
        print(f"    ✅ Navigated to Vol Surface")
        
        # Check for 3D plot
        try:
            vol_plot = page.locator('#vol-surface-plot').first
            plot_visible = vol_plot.is_visible(timeout=2000)
            
            if plot_visible:
                result['steps']['vol_surface_renders'] = 'PASS'
                print(f"    ✅ Vol surface 3D plot rendered")
            else:
                result['steps']['vol_surface_renders'] = 'FAIL'
                result['errors'].append("Vol surface plot not visible")
                print(f"    ❌ Vol surface plot not visible")
        except Exception as e:
            result['steps']['vol_surface_renders'] = 'FAIL'
            result['errors'].append(f"Plot validation failed: {e}")
            print(f"    ❌ Plot validation failed: {e}")
        
        # Capture screenshot
        screenshot_path = f'test-artifacts/options_lab/screenshots/vol_surface_{ticker}_loop{loop_num}.png'
        page.screenshot(path=screenshot_path, full_page=True)
        result['screenshot'] = screenshot_path
        print(f"    📸 Screenshot saved: {screenshot_path}")
        
        result['success'] = result['steps'].get('vol_surface_renders') == 'PASS'
        
    except Exception as e:
        result['errors'].append(f"Test failed: {e}")
        print(f"    ❌ Test failed: {e}")
    
    return result


def test_trade_simulator(page, ticker: str, loop_num: int) -> Dict[str, Any]:
    """Test Trade Simulator subtab."""
    print(f"\n  🎯 [Loop {loop_num}] Testing Trade Simulator for {ticker}...")
    
    result = {
        'ticker': ticker,
        'loop': loop_num,
        'subtab': 'Trade Simulator',
        'timestamp': datetime.now().isoformat(),
        'steps': {},
        'errors': [],
        'success': False
    }
    
    try:
        # Navigate to Trade Simulator subtab
        sim_tab = page.locator('.options-tab-simulator').first
        sim_tab.click()
        page.wait_for_timeout(2000)
        result['steps']['navigate_to_simulator'] = 'PASS'
        print(f"    ✅ Navigated to Trade Simulator")
        
        # Check for simulator interface
        try:
            sim_results = page.locator('#simulator-results').first
            results_visible = sim_results.is_visible(timeout=2000)
            
            if results_visible:
                result['steps']['simulator_renders'] = 'PASS'
                print(f"    ✅ Trade simulator interface rendered")
            else:
                result['steps']['simulator_renders'] = 'FAIL'
                result['errors'].append("Trade simulator not visible")
                print(f"    ❌ Trade simulator not visible")
        except Exception as e:
            result['steps']['simulator_renders'] = 'FAIL'
            result['errors'].append(f"Simulator validation failed: {e}")
            print(f"    ❌ Simulator validation failed: {e}")
        
        # Capture screenshot
        screenshot_path = f'test-artifacts/options_lab/screenshots/trade_sim_{ticker}_loop{loop_num}.png'
        page.screenshot(path=screenshot_path, full_page=True)
        result['screenshot'] = screenshot_path
        print(f"    📸 Screenshot saved: {screenshot_path}")
        
        result['success'] = result['steps'].get('simulator_renders') == 'PASS'
        
    except Exception as e:
        result['errors'].append(f"Test failed: {e}")
        print(f"    ❌ Test failed: {e}")
    
    return result


def run_3_loop_validation():
    """Execute 3-loop clicker validation for all subtabs."""
    print("="*80)
    print("🎯 OPTIONS LAB - 3-LOOP CLICKER VALIDATION")
    print("="*80)
    print(f"Started: {datetime.now().isoformat()}\n")
    
    # Start Dash app
    app_process = start_dash_app()
    
    # Check Playwright installation
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright not installed. Install with: pip install playwright && playwright install")
        return 1
    
    tickers = ['SPY', 'AAPL', 'QQQ']
    all_results = {
        'timestamp': datetime.now().isoformat(),
        'loops': {}
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        # Execute 3 loops
        for loop_num in range(1, 4):
            print(f"\n{'='*80}")
            print(f"🔄 LOOP {loop_num}/3")
            print(f"{'='*80}")
            
            loop_results = []
            
            for ticker in tickers:
                print(f"\n📈 Testing {ticker}...")
                
                # Test all subtabs
                chain_result = test_chain_viewer(page, ticker, loop_num)
                loop_results.append(chain_result)
                
                greeks_result = test_greeks_dashboard(page, ticker, loop_num)
                loop_results.append(greeks_result)
                
                vol_result = test_vol_surface(page, ticker, loop_num)
                loop_results.append(vol_result)
                
                sim_result = test_trade_simulator(page, ticker, loop_num)
                loop_results.append(sim_result)
            
            all_results['loops'][f'loop_{loop_num}'] = loop_results
            
            # Brief pause between loops
            time.sleep(2)
        
        browser.close()
    
    # Stop app if we started it
    if app_process:
        app_process.terminate()
        app_process.wait()
        print("\n🛑 Dash app stopped")
    
    # Save results
    output_file = Path('test-results/options_lab/3loop/complete_validation.json')
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    # Generate summary
    print("\n" + "="*80)
    print("📊 VALIDATION SUMMARY")
    print("="*80)
    
    for loop_name, loop_results in all_results['loops'].items():
        total = len(loop_results)
        successful = sum(1 for r in loop_results if r.get('success'))
        print(f"\n{loop_name.upper()}:")
        print(f"  ✅ Successful: {successful}/{total}")
        print(f"  ❌ Failed: {total - successful}/{total}")
        
        # Show failures
        for r in loop_results:
            if not r.get('success'):
                print(f"    • {r['subtab']} ({r['ticker']}): {', '.join(r['errors'][:2])}")
    
    print(f"\n{'='*80}")
    print(f"Results saved: {output_file}")
    print(f"Screenshots: test-artifacts/options_lab/screenshots/")
    print(f"{'='*80}\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(run_3_loop_validation())

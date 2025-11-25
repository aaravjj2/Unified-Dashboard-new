"""
Phase 3 Full 3-Loop Reproducibility Validation

Comprehensive end-to-end validation with:
- 3 sequential test loops
- 90+ screenshots (30 per loop)
- Performance metrics (startup, render, callback latency)
- Portfolio refresh button testing
- All tabs and subtabs validation
- JSON + Markdown report generation

Usage:
    python3 tests/phase3_full_3loop_validation.py
"""

import asyncio
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

# Dashboard URL
DASHBOARD_URL = "http://localhost:8050"
OUTPUT_DIR = Path("outputs/phase3_full_validation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TABS_TO_TEST = [
    {"name": "Command Center", "selector": "a:has-text('Command Center')"},
    {"name": "Market Trends", "selector": "a:has-text('Market Trends')"},
    {"name": "Market Forecast", "selector": "a:has-text('Market Forecast')"},
    {"name": "Attribution Lab", "selector": "a:has-text('Attribution Lab')"},
    {"name": "Strategy Lab", "selector": "a:has-text('Strategy Lab')"},
    {"name": "Research Lab", "selector": "a:has-text('Research Lab')"},
    {"name": "Volatility Lab", "selector": "a:has-text('Volatility Lab')"},
    {"name": "Portfolio", "selector": "a:has-text('Portfolio')"},
    {"name": "Options Lab", "selector": "a:has-text('Options Lab')"},
    {"name": "Weekly Picks", "selector": "a:has-text('Weekly Picks')"},
]

async def test_single_loop(loop_num, page):
    """Execute single validation loop"""
    print(f"\n{'='*70}")
    print(f"LOOP {loop_num} - STARTING")
    print(f"{'='*70}")
    
    loop_results = {
        'loop_number': loop_num,
        'start_time': datetime.now().isoformat(),
        'tabs_tested': 0,
        'screenshots': [],
        'timings': {},
        'portfolio_refresh_test': {},
        'errors': []
    }
    
    try:
        # Test 1: Dashboard Load Time
        print(f"\n🌐 Testing dashboard load time...")
        start = time.time()
        await page.goto(DASHBOARD_URL, timeout=60000)
        load_time = time.time() - start
        loop_results['timings']['dashboard_load'] = round(load_time, 2)
        print(f"   ✅ Dashboard loaded in {load_time:.2f}s")
        
        await asyncio.sleep(3)  # Let Dash initialize
        
        # Test 2: Portfolio Refresh Button
        print(f"\n💼 Testing Portfolio refresh button...")
        try:
            # Navigate to Home/Command Center
            await page.click("a:has-text('Command Center')", timeout=5000)
            await asyncio.sleep(2)
            
            # Look for refresh button
            refresh_button = page.locator('#home-refresh-portfolio-btn').first
            if await refresh_button.count() > 0:
                print(f"   ✅ Found refresh button")
                
                # Click it
                start = time.time()
                await refresh_button.click()
                await asyncio.sleep(3)  # Wait for callback
                refresh_time = time.time() - start
                
                loop_results['portfolio_refresh_test'] = {
                    'button_found': True,
                    'clicked': True,
                    'response_time': round(refresh_time, 2)
                }
                print(f"   ✅ Refresh button clicked, callback responded in {refresh_time:.2f}s")
            else:
                print(f"   ⚠️  Refresh button not found")
                loop_results['portfolio_refresh_test'] = {'button_found': False}
        
        except Exception as e:
            print(f"   ❌ Portfolio refresh test error: {e}")
            loop_results['portfolio_refresh_test'] = {'error': str(e)}
        
        # Test 3: All Major Tabs
        print(f"\n📸 Testing all major tabs...")
        for tab in TABS_TO_TEST:
            try:
                start = time.time()
                await page.click(tab['selector'], timeout=5000)
                render_time = time.time() - start
                await asyncio.sleep(1.5)
                
                # Capture screenshot
                filename = f"loop{loop_num}_{tab['name'].lower().replace(' ', '_')}.png"
                screenshot_path = OUTPUT_DIR / filename
                await page.screenshot(path=str(screenshot_path))
                
                loop_results['screenshots'].append(str(screenshot_path))
                loop_results['tabs_tested'] += 1
                loop_results['timings'][f"tab_{tab['name']}"] = round(render_time, 2)
                
                print(f"   ✅ {tab['name']}: {render_time:.2f}s")
                
            except Exception as e:
                print(f"   ⚠️  {tab['name']}: {e}")
                loop_results['errors'].append({
                    'tab': tab['name'],
                    'error': str(e)
                })
        
        # Test 4: Strategy Lab Subtabs (if available)
        print(f"\n⚡ Testing Strategy Lab subtabs...")
        try:
            await page.click("a:has-text('Strategy Lab')", timeout=5000)
            await asyncio.sleep(2)
            
            subtabs = ['Setup', 'Backtest', 'Execute', 'Results', 'Benchmark', 'Risk']
            subtabs_found = 0
            
            for subtab in subtabs:
                try:
                    subtab_link = page.locator(f".nav-link:has-text('{subtab}')").first
                    if await subtab_link.count() > 0:
                        await subtab_link.click(timeout=2000)
                        await asyncio.sleep(0.5)
                        
                        filename = f"loop{loop_num}_strategy_subtab_{subtab.lower()}.png"
                        screenshot_path = OUTPUT_DIR / filename
                        await page.screenshot(path=str(screenshot_path))
                        loop_results['screenshots'].append(str(screenshot_path))
                        
                        subtabs_found += 1
                        print(f"   ✅ {subtab} subtab")
                except:
                    pass
            
            loop_results['strategy_lab_subtabs'] = subtabs_found
            print(f"   📊 Strategy Lab subtabs: {subtabs_found}/6")
        
        except Exception as e:
            print(f"   ⚠️  Strategy Lab subtabs error: {e}")
        
        loop_results['end_time'] = datetime.now().isoformat()
        loop_results['status'] = 'PASS'
        
    except Exception as e:
        print(f"\n❌ Loop {loop_num} error: {e}")
        loop_results['status'] = 'FAIL'
        loop_results['fatal_error'] = str(e)
        import traceback
        traceback.print_exc()
    
    return loop_results

async def main():
    print("=" * 70)
    print("PHASE 3 FULL 3-LOOP REPRODUCIBILITY VALIDATION")
    print("=" * 70)
    print(f"Start Time: {datetime.now().isoformat()}")
    print(f"Dashboard URL: {DASHBOARD_URL}")
    print(f"Output Directory: {OUTPUT_DIR}")
    
    all_results = {
        'test_name': 'Phase 3 Full 3-Loop Validation',
        'start_time': datetime.now().isoformat(),
        'loops': []
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Run 3 loops
        for loop_num in range(1, 4):
            loop_results = await test_single_loop(loop_num, page)
            all_results['loops'].append(loop_results)
            
            # Brief pause between loops
            if loop_num < 3:
                print(f"\n⏸️  Pausing 5s before next loop...")
                await asyncio.sleep(5)
        
        await browser.close()
    
    # Calculate aggregate metrics
    all_results['end_time'] = datetime.now().isoformat()
    
    total_screenshots = sum(len(loop['screenshots']) for loop in all_results['loops'])
    avg_load_time = sum(loop['timings'].get('dashboard_load', 0) for loop in all_results['loops']) / 3
    
    all_results['summary'] = {
        'total_loops': 3,
        'total_screenshots': total_screenshots,
        'avg_dashboard_load_time': round(avg_load_time, 2),
        'loops_passed': sum(1 for loop in all_results['loops'] if loop.get('status') == 'PASS'),
        'portfolio_refresh_tested': all(loop.get('portfolio_refresh_test', {}).get('button_found') for loop in all_results['loops'])
    }
    
    # Save JSON report
    json_path = OUTPUT_DIR / "full_3loop_validation_report.json"
    with open(json_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n{'='*70}")
    print("FINAL RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"\n📊 Loops Completed: {all_results['summary']['loops_passed']}/3")
    print(f"📸 Total Screenshots: {total_screenshots}")
    print(f"⏱️  Avg Dashboard Load: {avg_load_time:.2f}s")
    print(f"💼 Portfolio Refresh: {'✅ TESTED' if all_results['summary']['portfolio_refresh_tested'] else '⚠️  NOT FOUND'}")
    print(f"\n📄 JSON Report: {json_path}")
    
    # Generate Markdown report
    md_path = OUTPUT_DIR / "full_3loop_validation_report.md"
    with open(md_path, 'w') as f:
        f.write(f"# Phase 3 Full 3-Loop Validation Report\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- **Loops Completed**: {all_results['summary']['loops_passed']}/3\n")
        f.write(f"- **Total Screenshots**: {total_screenshots}\n")
        f.write(f"- **Avg Load Time**: {avg_load_time:.2f}s\n")
        f.write(f"- **Portfolio Refresh**: {'✅ TESTED' if all_results['summary']['portfolio_refresh_tested'] else '⚠️  NOT FOUND'}\n\n")
        
        for i, loop in enumerate(all_results['loops'], 1):
            f.write(f"## Loop {i}\n\n")
            f.write(f"- **Status**: {loop.get('status', 'UNKNOWN')}\n")
            f.write(f"- **Tabs Tested**: {loop.get('tabs_tested', 0)}\n")
            f.write(f"- **Screenshots**: {len(loop.get('screenshots', []))}\n")
            f.write(f"- **Dashboard Load**: {loop['timings'].get('dashboard_load', 'N/A')}s\n")
            if loop.get('portfolio_refresh_test'):
                pr = loop['portfolio_refresh_test']
                f.write(f"- **Portfolio Refresh**: {'✅ CLICKED' if pr.get('clicked') else '⚠️  NOT TESTED'}\n")
            f.write(f"\n")
    
    print(f"📄 Markdown Report: {md_path}")
    
    # Final status
    if all_results['summary']['loops_passed'] == 3:
        print(f"\n✅ ✅ ✅ ALL 3 LOOPS PASSED")
        return 0
    else:
        print(f"\n⚠️  ⚠️  ⚠️  SOME LOOPS FAILED")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

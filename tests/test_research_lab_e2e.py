"""
Research Lab E2E Test Suite - 3-Loop Validation

Test all 5 subtabs:
1. Market Scan
2. Factor Analysis
3. Correlation Explorer
4. Strategy Backtest
5. Research Notes

3-Loop Framework:
- Loop 1: Basic functionality, sample inputs, output verification
- Loop 2: Alternative inputs, edge cases, consistency checks
- Loop 3: Performance timing, error logging, JSON report generation
"""

import os
import sys
import time
import json
from datetime import datetime
from playwright.sync_api import sync_playwright, expect

# Test configuration
BASE_URL = 'http://localhost:8050'
ARTIFACTS_DIR = 'test-artifacts'
TIMEOUT = 15000  # 15 seconds per operation

# Ensure artifacts directory exists
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

def save_screenshot(page, name):
    """Save screenshot to artifacts directory."""
    filepath = os.path.join(ARTIFACTS_DIR, f"{name}.png")
    page.screenshot(path=filepath, full_page=True)
    print(f"  📸 Screenshot saved: {filepath}")
    return filepath

def log_test_result(results, subtab, test_name, status, duration=None, details=None):
    """Log test result to results dictionary."""
    if subtab not in results:
        results[subtab] = []
    
    result_entry = {
        'test': test_name,
        'status': status,  # 'PASS' or 'FAIL'
        'timestamp': datetime.now().isoformat(),
    }
    
    if duration:
        result_entry['duration_ms'] = duration
    if details:
        result_entry['details'] = details
    
    results[subtab].append(result_entry)
    
    icon = '✅' if status == 'PASS' else '❌'
    print(f"  {icon} {test_name}: {status}")
    if duration:
        print(f"     ⏱️ Duration: {duration}ms")

def test_market_scan(page, results, loop_num):
    """Test Market Scan subtab."""
    print(f"\n🔍 Testing Market Scan (Loop {loop_num})...")
    
    start_time = time.time()
    
    try:
        # Navigate to Research Lab
        page.goto(BASE_URL)
        page.wait_for_timeout(2000)
        
        # Click Research Lab tab
        research_lab_tab = page.locator('text=🔬 Research Lab')
        research_lab_tab.click()
        page.wait_for_timeout(1500)
        
        # Click Market Scan subtab
        market_scan_tab = page.locator('text=📊 Market Scan')
        market_scan_tab.click()
        page.wait_for_timeout(1000)
        
        save_screenshot(page, f'market_scan_loop{loop_num}_initial')
        
        # Enter tickers (different for each loop)
        tickers_input = page.locator('#market-scan-tickers')
        if loop_num == 1:
            test_tickers = 'SPY,QQQ,IWM'
        elif loop_num == 2:
            test_tickers = 'AAPL,MSFT,GOOGL'
        else:
            test_tickers = 'NVDA,AMD,INTC'
        
        tickers_input.fill(test_tickers)
        
        # Run screen
        run_button = page.locator('#market-scan-run-button')
        run_button.click()
        page.wait_for_timeout(3000)  # Wait for data fetching
        
        # Check for results
        results_container = page.locator('#market-scan-results-container')
        expect(results_container).to_be_visible(timeout=TIMEOUT)
        
        results_text = results_container.inner_text()
        
        # Verify results
        if 'passed filters' in results_text.lower() or 'tickers' in results_text.lower():
            duration = int((time.time() - start_time) * 1000)
            log_test_result(results, 'market_scan', f'Loop{loop_num}_screening', 'PASS', duration, 
                          {'tickers': test_tickers, 'results_length': len(results_text)})
            
            save_screenshot(page, f'market_scan_loop{loop_num}_success')
            return True
        else:
            log_test_result(results, 'market_scan', f'Loop{loop_num}_screening', 'FAIL', 
                          details={'error': 'No results found', 'results_text': results_text[:200]})
            save_screenshot(page, f'market_scan_loop{loop_num}_fail')
            return False
        
    except Exception as e:
        log_test_result(results, 'market_scan', f'Loop{loop_num}_screening', 'FAIL', 
                      details={'error': str(e)})
        save_screenshot(page, f'market_scan_loop{loop_num}_error')
        return False

def test_factor_analysis(page, results, loop_num):
    """Test Factor Analysis subtab."""
    print(f"\n📊 Testing Factor Analysis (Loop {loop_num})...")
    
    start_time = time.time()
    
    try:
        # Click Factor Analysis subtab
        factor_tab = page.locator('text=📈 Factor Analysis')
        factor_tab.click()
        page.wait_for_timeout(1000)
        
        save_screenshot(page, f'factor_analysis_loop{loop_num}_initial')
        
        # Enter ticker
        ticker_input = page.locator('#factor-analysis-ticker')
        test_ticker = 'SPY' if loop_num == 1 else ('QQQ' if loop_num == 2 else 'IWM')
        ticker_input.fill(test_ticker)
        
        # Run analysis
        run_button = page.locator('#factor-analysis-run-button')
        run_button.click()
        page.wait_for_timeout(4000)  # Wait for calculation
        
        # Check for results
        results_container = page.locator('#factor-analysis-results-container')
        expect(results_container).to_be_visible(timeout=TIMEOUT)
        
        results_text = results_container.inner_text()
        
        # Verify factor exposures
        if ('alpha' in results_text.lower() or 'beta' in results_text.lower() or 
            'mkt-rf' in results_text.lower()):
            duration = int((time.time() - start_time) * 1000)
            log_test_result(results, 'factor_analysis', f'Loop{loop_num}_calculation', 'PASS', duration,
                          {'ticker': test_ticker, 'results_length': len(results_text)})
            
            save_screenshot(page, f'factor_analysis_loop{loop_num}_success')
            return True
        else:
            log_test_result(results, 'factor_analysis', f'Loop{loop_num}_calculation', 'FAIL',
                          details={'error': 'No factor data', 'results_text': results_text[:200]})
            save_screenshot(page, f'factor_analysis_loop{loop_num}_fail')
            return False
        
    except Exception as e:
        log_test_result(results, 'factor_analysis', f'Loop{loop_num}_calculation', 'FAIL',
                      details={'error': str(e)})
        save_screenshot(page, f'factor_analysis_loop{loop_num}_error')
        return False

def test_correlation_explorer(page, results, loop_num):
    """Test Correlation Explorer subtab."""
    print(f"\n🔗 Testing Correlation Explorer (Loop {loop_num})...")
    
    start_time = time.time()
    
    try:
        # Click Correlation Explorer subtab
        corr_tab = page.locator('text=🔗 Correlation Explorer')
        corr_tab.click()
        page.wait_for_timeout(1000)
        
        save_screenshot(page, f'correlation_loop{loop_num}_initial')
        
        # Enter tickers
        tickers_input = page.locator('#correlation-tickers')
        if loop_num == 1:
            test_tickers = 'SPY,QQQ,IWM,TLT'
        elif loop_num == 2:
            test_tickers = 'GLD,SLV,USO,UNG'
        else:
            test_tickers = 'XLF,XLK,XLE,XLV'
        
        tickers_input.fill(test_tickers)
        
        # Run correlation
        run_button = page.locator('#correlation-run-button')
        run_button.click()
        page.wait_for_timeout(4000)  # Wait for calculation
        
        # Check for heatmap
        heatmap = page.locator('#correlation-heatmap')
        expect(heatmap).to_be_visible(timeout=TIMEOUT)
        
        # Verify heatmap rendered
        duration = int((time.time() - start_time) * 1000)
        log_test_result(results, 'correlation_explorer', f'Loop{loop_num}_heatmap', 'PASS', duration,
                      {'tickers': test_tickers})
        
        save_screenshot(page, f'correlation_loop{loop_num}_success')
        return True
        
    except Exception as e:
        log_test_result(results, 'correlation_explorer', f'Loop{loop_num}_heatmap', 'FAIL',
                      details={'error': str(e)})
        save_screenshot(page, f'correlation_loop{loop_num}_error')
        return False

def test_strategy_backtest(page, results, loop_num):
    """Test Strategy Backtest subtab."""
    print(f"\n⚙️ Testing Strategy Backtest (Loop {loop_num})...")
    
    start_time = time.time()
    
    try:
        # Click Strategy Backtest subtab
        backtest_tab = page.locator('text=⚙️ Strategy Backtest')
        backtest_tab.click()
        page.wait_for_timeout(1000)
        
        save_screenshot(page, f'backtest_loop{loop_num}_initial')
        
        # Enter portfolio
        portfolio_input = page.locator('#backtest-portfolio')
        if loop_num == 1:
            test_portfolio = 'SPY:0.6,QQQ:0.4'
        elif loop_num == 2:
            test_portfolio = 'SPY:0.5,TLT:0.5'
        else:
            test_portfolio = 'SPY:0.4,QQQ:0.3,IWM:0.3'
        
        portfolio_input.fill(test_portfolio)
        
        # Run backtest
        run_button = page.locator('#backtest-run-button')
        run_button.click()
        page.wait_for_timeout(4000)  # Wait for simulation
        
        # Check for results
        results_container = page.locator('#backtest-results-container')
        expect(results_container).to_be_visible(timeout=TIMEOUT)
        
        results_text = results_container.inner_text()
        
        # Verify metrics
        if ('return' in results_text.lower() or 'sharpe' in results_text.lower() or
            'volatility' in results_text.lower()):
            duration = int((time.time() - start_time) * 1000)
            log_test_result(results, 'strategy_backtest', f'Loop{loop_num}_simulation', 'PASS', duration,
                          {'portfolio': test_portfolio, 'results_length': len(results_text)})
            
            save_screenshot(page, f'backtest_loop{loop_num}_success')
            return True
        else:
            log_test_result(results, 'strategy_backtest', f'Loop{loop_num}_simulation', 'FAIL',
                          details={'error': 'No metrics', 'results_text': results_text[:200]})
            save_screenshot(page, f'backtest_loop{loop_num}_fail')
            return False
        
    except Exception as e:
        log_test_result(results, 'strategy_backtest', f'Loop{loop_num}_simulation', 'FAIL',
                      details={'error': str(e)})
        save_screenshot(page, f'backtest_loop{loop_num}_error')
        return False

def test_research_notes(page, results, loop_num):
    """Test Research Notes subtab."""
    print(f"\n📝 Testing Research Notes (Loop {loop_num})...")
    
    start_time = time.time()
    
    try:
        # Click Research Notes subtab
        notes_tab = page.locator('text=📝 Research Notes')
        notes_tab.click()
        page.wait_for_timeout(1000)
        
        save_screenshot(page, f'research_notes_loop{loop_num}_initial')
        
        # Enter notes
        notes_textarea = page.locator('#research-notes-text')
        test_notes = f"Test notes from Loop {loop_num}\n\nTimestamp: {datetime.now()}\n\nThis is a test."
        notes_textarea.fill(test_notes)
        
        # Save notes
        save_button = page.locator('#research-notes-save-button')
        save_button.click()
        page.wait_for_timeout(2000)
        
        # Check for success message
        status_div = page.locator('#research-notes-status')
        status_text = status_div.inner_text(timeout=5000)
        
        if 'saved' in status_text.lower() or '✅' in status_text:
            duration = int((time.time() - start_time) * 1000)
            log_test_result(results, 'research_notes', f'Loop{loop_num}_save', 'PASS', duration,
                          {'notes_length': len(test_notes)})
            
            save_screenshot(page, f'research_notes_loop{loop_num}_success')
            return True
        else:
            log_test_result(results, 'research_notes', f'Loop{loop_num}_save', 'FAIL',
                          details={'status_text': status_text})
            save_screenshot(page, f'research_notes_loop{loop_num}_fail')
            return False
        
    except Exception as e:
        log_test_result(results, 'research_notes', f'Loop{loop_num}_save', 'FAIL',
                      details={'error': str(e)})
        save_screenshot(page, f'research_notes_loop{loop_num}_error')
        return False

def generate_json_report(results, total_duration):
    """Generate JSON validation report."""
    report = {
        'test_suite': 'Research Lab E2E - 3-Loop Validation',
        'timestamp': datetime.now().isoformat(),
        'total_duration_ms': total_duration,
        'subtabs_tested': list(results.keys()),
        'results': results,
        'summary': {
            'total_tests': sum(len(tests) for tests in results.values()),
            'passed': sum(1 for tests in results.values() for test in tests if test['status'] == 'PASS'),
            'failed': sum(1 for tests in results.values() for test in tests if test['status'] == 'FAIL'),
        }
    }
    
    # Calculate success rate
    if report['summary']['total_tests'] > 0:
        report['summary']['success_rate'] = (
            report['summary']['passed'] / report['summary']['total_tests'] * 100
        )
    else:
        report['summary']['success_rate'] = 0.0
    
    # Save report
    report_path = os.path.join(ARTIFACTS_DIR, 'research_lab_e2e_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 JSON report saved: {report_path}")
    return report

def main():
    """Run 3-loop E2E test suite."""
    print("=" * 80)
    print("🧪 Research Lab E2E Test Suite - 3-Loop Validation")
    print("=" * 80)
    
    overall_start = time.time()
    results = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        # Run 3 loops
        for loop in range(1, 4):
            print(f"\n{'=' * 80}")
            print(f"🔄 LOOP {loop} - {'Basic' if loop == 1 else 'Alternative' if loop == 2 else 'Performance'}")
            print(f"{'=' * 80}")
            
            # Test all 5 subtabs
            test_market_scan(page, results, loop)
            test_factor_analysis(page, results, loop)
            test_correlation_explorer(page, results, loop)
            test_strategy_backtest(page, results, loop)
            test_research_notes(page, results, loop)
        
        browser.close()
    
    # Generate report
    total_duration = int((time.time() - overall_start) * 1000)
    report = generate_json_report(results, total_duration)
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {report['summary']['total_tests']}")
    print(f"✅ Passed: {report['summary']['passed']}")
    print(f"❌ Failed: {report['summary']['failed']}")
    print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
    print(f"Total Duration: {total_duration / 1000:.2f}s")
    print("=" * 80)
    
    # Exit with appropriate code
    if report['summary']['failed'] > 0:
        sys.exit(1)
    else:
        print("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)

if __name__ == '__main__':
    main()

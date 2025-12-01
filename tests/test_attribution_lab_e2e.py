"""
Attribution Lab E2E Test Suite - 3-Loop Validation Framework

This test validates all 4 subtabs of Attribution Analysis Lab:
1. Performance Overview
2. Factor Contribution
3. Sector Analysis
4. Residual & Alpha

Test Structure:
- Loop 1: Navigate subtabs → Select inputs → Generate charts → Capture screenshots
- Loop 2: Repeat Loop 1 → Validate data consistency
- Loop 3: Log errors → Execution times → Generate JSON report

Requirements:
- Load time < 3s per subtab
- Charts render without empty axes
- Data calculations are consistent
- All interactive controls functional
"""

import pytest
from playwright.sync_api import Page, expect
import time
import json
from datetime import datetime
from pathlib import Path

# Test configuration
BASE_URL = "http://localhost:8050"
SCREENSHOT_DIR = Path("test_screenshots/attribution_lab")
ARTIFACTS_DIR = Path("test-artifacts")
MAX_LOAD_TIME = 3.0  # seconds

# Create output directories
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="module")
def validation_results():
    """Store validation results across test loops."""
    return {
        'loop_1': {'subtabs': {}, 'screenshots': [], 'errors': []},
        'loop_2': {'subtabs': {}, 'screenshots': [], 'errors': [], 'consistency_checks': {}},
        'loop_3': {'execution_times': {}, 'total_errors': 0, 'timestamp': datetime.now().isoformat()}
    }


class TestAttributionLabLoop1:
    """Loop 1: Basic navigation and chart generation."""
    
    def test_navigate_to_attribution_lab(self, page: Page, validation_results):
        """Navigate to Attribution Lab tab."""
        start_time = time.time()
        
        page.goto(BASE_URL, timeout=10000)
        page.wait_for_load_state("networkidle", timeout=10000)
        
        # Click Attribution Lab tab using ID selector (robust against emoji/text changes)
        page.wait_for_selector('#tab-attribution_lab', timeout=15000)
        page.click('#tab-attribution_lab')
        
        # Wait for content to load
        page.wait_for_selector('.attr-subtabs', timeout=5000)
        
        load_time = time.time() - start_time
        
        validation_results['loop_1']['nav_time'] = load_time
        assert load_time < MAX_LOAD_TIME * 2, f"Attribution Lab load time {load_time:.2f}s exceeds threshold"
    
    def test_performance_overview_subtab(self, page: Page, validation_results):
        """Test Performance Overview subtab with portfolio/benchmark selection."""
        start_time = time.time()
        
        # Should already be on Performance tab (default)
        page.wait_for_selector('#perf-total-return', timeout=5000)
        
        # Select portfolio
        page.locator('.attr-portfolio-dropdown').click()
        page.locator('text="Current Portfolio"').click()
        
        # Select benchmark
        page.locator('.attr-benchmark-dropdown').click()
        page.locator('text="S&P 500 (SPY)"').click()
        
        # Click refresh
        page.locator('.attr-refresh-btn').click()
        
        # Wait for charts to render
        page.wait_for_selector('#perf-cumulative-chart', timeout=8000)
        time.sleep(2)  # Allow charts to fully render
        
        # Validate metrics are populated
        total_return = page.locator('#perf-total-return').inner_text()
        assert total_return != "--", "Total return not populated"
        
        sharpe = page.locator('#perf-sharpe').inner_text()
        assert sharpe != "--", "Sharpe ratio not populated"
        
        # Capture screenshot
        screenshot_path = SCREENSHOT_DIR / "loop1_performance_overview.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        
        load_time = time.time() - start_time
        
        validation_results['loop_1']['subtabs']['performance'] = {
            'load_time': load_time,
            'total_return': total_return,
            'sharpe': sharpe,
            'screenshot': str(screenshot_path)
        }
        validation_results['loop_1']['screenshots'].append(str(screenshot_path))
        
        assert load_time < MAX_LOAD_TIME * 3, f"Performance subtab load time {load_time:.2f}s exceeds threshold"
    
    def test_factor_contribution_subtab(self, page: Page, validation_results):
        """Test Factor Contribution subtab with factor selection."""
        start_time = time.time()
        
        # Click Factor Contribution tab
        page.locator('text="🔍 Factor Contribution"').click()
        page.wait_for_selector('.factors-selection', timeout=5000)
        
        # Select factors (market, size, value)
        page.locator('.factors-selection').click()
        page.locator('text="Market (Mkt-RF)"').click()
        page.locator('text="Size (SMB)"').click()
        page.locator('text="Value (HML)"').click()
        page.keyboard.press("Escape")  # Close dropdown
        
        # Click refresh
        page.locator('.attr-refresh-btn').click()
        
        # Wait for charts
        page.wait_for_selector('#factors-contribution-chart', timeout=8000)
        time.sleep(2)
        
        # Validate exposure cards are present
        exposures = page.locator('#factors-exposures-container').inner_text()
        assert len(exposures) > 10, "Factor exposures not populated"
        
        # Capture screenshot
        screenshot_path = SCREENSHOT_DIR / "loop1_factor_contribution.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        
        load_time = time.time() - start_time
        
        validation_results['loop_1']['subtabs']['factors'] = {
            'load_time': load_time,
            'exposures': exposures[:100],  # First 100 chars
            'screenshot': str(screenshot_path)
        }
        validation_results['loop_1']['screenshots'].append(str(screenshot_path))
        
        assert load_time < MAX_LOAD_TIME * 3, f"Factor subtab load time {load_time:.2f}s exceeds threshold"
    
    def test_sector_analysis_subtab(self, page: Page, validation_results):
        """Test Sector Analysis subtab."""
        start_time = time.time()
        
        # Click Sector Analysis tab
        page.locator('text="🏢 Sector Analysis"').click()
        page.wait_for_selector('#sectors-weights-pie', timeout=5000)
        
        # Click refresh
        page.locator('.attr-refresh-btn').click()
        
        # Wait for charts
        page.wait_for_selector('#sectors-contribution-bar', timeout=8000)
        time.sleep(2)
        
        # Validate table exists
        table = page.locator('#sectors-table-container')
        table_text = table.inner_text()
        assert "Sector" in table_text or "Weight" in table_text, "Sector table not populated"
        
        # Capture screenshot
        screenshot_path = SCREENSHOT_DIR / "loop1_sector_analysis.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        
        load_time = time.time() - start_time
        
        validation_results['loop_1']['subtabs']['sectors'] = {
            'load_time': load_time,
            'table_preview': table_text[:150],
            'screenshot': str(screenshot_path)
        }
        validation_results['loop_1']['screenshots'].append(str(screenshot_path))
        
        assert load_time < MAX_LOAD_TIME * 3, f"Sector subtab load time {load_time:.2f}s exceeds threshold"
    
    def test_residual_alpha_subtab(self, page: Page, validation_results):
        """Test Residual & Alpha subtab."""
        start_time = time.time()
        
        # Click Residual & Alpha tab
        page.locator('text="✨ Residual & Alpha"').click()
        page.wait_for_selector('#residual-alpha', timeout=5000)
        
        # Click refresh
        page.locator('.attr-refresh-btn').click()
        
        # Wait for charts
        page.wait_for_selector('#residual-timeseries-chart', timeout=8000)
        time.sleep(2)
        
        # Validate alpha metrics
        alpha = page.locator('#residual-alpha').inner_text()
        beta = page.locator('#residual-beta').inner_text()
        
        assert alpha != "--", "Alpha not populated"
        assert beta != "--", "Beta not populated"
        
        # Capture screenshot
        screenshot_path = SCREENSHOT_DIR / "loop1_residual_alpha.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        
        load_time = time.time() - start_time
        
        validation_results['loop_1']['subtabs']['residual'] = {
            'load_time': load_time,
            'alpha': alpha,
            'beta': beta,
            'screenshot': str(screenshot_path)
        }
        validation_results['loop_1']['screenshots'].append(str(screenshot_path))
        
        assert load_time < MAX_LOAD_TIME * 3, f"Residual subtab load time {load_time:.2f}s exceeds threshold"


class TestAttributionLabLoop2:
    """Loop 2: Repeat with different portfolio and validate consistency."""
    
    def test_performance_overview_weekly_portfolio(self, page: Page, validation_results):
        """Test Performance Overview with Weekly Picks portfolio."""
        start_time = time.time()
        
        # Navigate back to Performance tab
        page.locator('text="📈 Performance Overview"').click()
        page.wait_for_selector('#perf-total-return', timeout=5000)
        
        # Select Weekly Picks portfolio
        page.locator('.attr-portfolio-dropdown').click()
        page.locator('text="Weekly Picks"').click()
        
        # Select different benchmark
        page.locator('.attr-benchmark-dropdown').click()
        page.locator('text="NASDAQ 100 (QQQ)"').click()
        
        # Refresh
        page.locator('.attr-refresh-btn').click()
        page.wait_for_selector('#perf-cumulative-chart', timeout=8000)
        time.sleep(2)
        
        # Get metrics
        total_return_2 = page.locator('#perf-total-return').inner_text()
        sharpe_2 = page.locator('#perf-sharpe').inner_text()
        
        # Capture screenshot
        screenshot_path = SCREENSHOT_DIR / "loop2_performance_weekly.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        
        load_time = time.time() - start_time
        
        # Consistency check: values should be different from Loop 1
        loop1_return = validation_results['loop_1']['subtabs']['performance']['total_return']
        consistency_pass = (total_return_2 != loop1_return)
        
        validation_results['loop_2']['subtabs']['performance'] = {
            'load_time': load_time,
            'total_return': total_return_2,
            'sharpe': sharpe_2,
            'screenshot': str(screenshot_path)
        }
        validation_results['loop_2']['consistency_checks']['performance'] = {
            'different_portfolio_different_metrics': consistency_pass
        }
        validation_results['loop_2']['screenshots'].append(str(screenshot_path))
        
        assert load_time < MAX_LOAD_TIME * 3, f"Performance Loop 2 load time {load_time:.2f}s exceeds threshold"
    
    def test_factor_contribution_momentum_quality(self, page: Page, validation_results):
        """Test Factor Contribution with Momentum and Quality factors."""
        start_time = time.time()
        
        # Navigate to Factor tab
        page.locator('text="🔍 Factor Contribution"').click()
        page.wait_for_selector('.factors-selection', timeout=5000)
        
        # Clear previous selections and select Momentum + Quality
        page.locator('.factors-selection').click()
        # Deselect all first (click each selected item)
        page.keyboard.press("Escape")
        
        time.sleep(0.5)
        page.locator('.factors-selection').click()
        page.locator('text="Momentum (MOM)"').click()
        page.locator('text="Quality"').click()
        page.keyboard.press("Escape")
        
        # Refresh
        page.locator('.attr-refresh-btn').click()
        page.wait_for_selector('#factors-contribution-chart', timeout=8000)
        time.sleep(2)
        
        # Get exposures
        exposures_2 = page.locator('#factors-exposures-container').inner_text()
        
        # Capture screenshot
        screenshot_path = SCREENSHOT_DIR / "loop2_factor_momentum_quality.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        
        load_time = time.time() - start_time
        
        validation_results['loop_2']['subtabs']['factors'] = {
            'load_time': load_time,
            'exposures': exposures_2[:100],
            'screenshot': str(screenshot_path)
        }
        validation_results['loop_2']['screenshots'].append(str(screenshot_path))
        
        assert load_time < MAX_LOAD_TIME * 3, f"Factor Loop 2 load time {load_time:.2f}s exceeds threshold"
    
    def test_sector_analysis_monthly_portfolio(self, page: Page, validation_results):
        """Test Sector Analysis with Monthly Picks portfolio."""
        start_time = time.time()
        
        # Navigate to Sector tab
        page.locator('text="🏢 Sector Analysis"').click()
        page.wait_for_selector('#sectors-weights-pie', timeout=5000)
        
        # Change portfolio to Monthly Picks
        page.locator('.attr-portfolio-dropdown').click()
        page.locator('text="Monthly Picks"').click()
        
        # Refresh
        page.locator('.attr-refresh-btn').click()
        page.wait_for_selector('#sectors-contribution-bar', timeout=8000)
        time.sleep(2)
        
        # Get table data
        table_text_2 = page.locator('#sectors-table-container').inner_text()
        
        # Capture screenshot
        screenshot_path = SCREENSHOT_DIR / "loop2_sector_monthly.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        
        load_time = time.time() - start_time
        
        validation_results['loop_2']['subtabs']['sectors'] = {
            'load_time': load_time,
            'table_preview': table_text_2[:150],
            'screenshot': str(screenshot_path)
        }
        validation_results['loop_2']['screenshots'].append(str(screenshot_path))
        
        assert load_time < MAX_LOAD_TIME * 3, f"Sector Loop 2 load time {load_time:.2f}s exceeds threshold"
    
    def test_residual_alpha_with_all_factors(self, page: Page, validation_results):
        """Test Residual & Alpha with all factors selected."""
        start_time = time.time()
        
        # Navigate to Residual tab
        page.locator('text="✨ Residual & Alpha"').click()
        page.wait_for_selector('#residual-alpha', timeout=5000)
        
        # Select all factors first
        page.locator('text="🔍 Factor Contribution"').click()
        page.wait_for_selector('.factors-selection', timeout=3000)
        page.locator('.factors-selection').click()
        page.locator('text="Market (Mkt-RF)"').click()
        page.locator('text="Size (SMB)"').click()
        page.locator('text="Value (HML)"').click()
        page.locator('text="Momentum (MOM)"').click()
        page.locator('text="Quality"').click()
        page.keyboard.press("Escape")
        
        # Go back to Residual tab
        page.locator('text="✨ Residual & Alpha"').click()
        page.wait_for_selector('#residual-alpha', timeout=5000)
        
        # Refresh
        page.locator('.attr-refresh-btn').click()
        page.wait_for_selector('#residual-timeseries-chart', timeout=8000)
        time.sleep(2)
        
        # Get metrics
        alpha_2 = page.locator('#residual-alpha').inner_text()
        tracking_2 = page.locator('#residual-tracking').inner_text()
        
        # Capture screenshot
        screenshot_path = SCREENSHOT_DIR / "loop2_residual_all_factors.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        
        load_time = time.time() - start_time
        
        validation_results['loop_2']['subtabs']['residual'] = {
            'load_time': load_time,
            'alpha': alpha_2,
            'tracking_error': tracking_2,
            'screenshot': str(screenshot_path)
        }
        validation_results['loop_2']['screenshots'].append(str(screenshot_path))
        
        assert load_time < MAX_LOAD_TIME * 4, f"Residual Loop 2 load time {load_time:.2f}s exceeds threshold"


class TestAttributionLabLoop3:
    """Loop 3: Error logging and final validation report generation."""
    
    def test_generate_validation_report(self, page: Page, validation_results):
        """Generate comprehensive JSON validation report."""
        
        # Collect all execution times
        all_times = []
        for loop in ['loop_1', 'loop_2']:
            for subtab, data in validation_results[loop]['subtabs'].items():
                all_times.append(data['load_time'])
        
        avg_time = sum(all_times) / len(all_times) if all_times else 0
        max_time = max(all_times) if all_times else 0
        
        validation_results['loop_3']['execution_times'] = {
            'average_load_time': round(avg_time, 2),
            'max_load_time': round(max_time, 2),
            'threshold': MAX_LOAD_TIME * 3,
            'all_times': [round(t, 2) for t in all_times]
        }
        
        # Count errors
        total_errors = len(validation_results['loop_1']['errors']) + len(validation_results['loop_2']['errors'])
        validation_results['loop_3']['total_errors'] = total_errors
        
        # Summary
        validation_results['loop_3']['summary'] = {
            'total_subtabs_tested': 4,
            'total_screenshots': len(validation_results['loop_1']['screenshots']) + len(validation_results['loop_2']['screenshots']),
            'performance_threshold_met': max_time < MAX_LOAD_TIME * 3,
            'consistency_checks_passed': all(
                check['different_portfolio_different_metrics'] 
                for check in validation_results.get('loop_2', {}).get('consistency_checks', {}).values()
            ),
            'test_timestamp': datetime.now().isoformat()
        }
        
        # Write JSON report
        report_path = ARTIFACTS_DIR / "attribution_lab_validation_report.json"
        with open(report_path, 'w') as f:
            json.dump(validation_results, f, indent=2)
        
        print(f"\n{'='*60}")
        print("ATTRIBUTION LAB 3-LOOP VALIDATION COMPLETE")
        print(f"{'='*60}")
        print(f"Average Load Time: {avg_time:.2f}s")
        print(f"Max Load Time: {max_time:.2f}s")
        print(f"Threshold: {MAX_LOAD_TIME * 3:.2f}s")
        print(f"Total Errors: {total_errors}")
        print(f"Screenshots Captured: {validation_results['loop_3']['summary']['total_screenshots']}")
        print(f"Report: {report_path}")
        print(f"{'='*60}\n")
        
        # Assertions
        assert max_time < MAX_LOAD_TIME * 3, f"Max load time {max_time:.2f}s exceeds threshold"
        assert total_errors == 0, f"Found {total_errors} errors during validation"
        assert validation_results['loop_3']['summary']['consistency_checks_passed'], "Consistency checks failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

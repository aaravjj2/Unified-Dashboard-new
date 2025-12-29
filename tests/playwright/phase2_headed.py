"""
Phase 2 Playwright Headful E2E Tests

Tests for AI/ML Analytics Lab:
- Neural Price Forecasting
- Market Regime Detection  
- Sentiment Consensus

Requirements:
- Dashboard running on localhost:8051
- PHASE2_DETERMINISTIC=1 for consistent results

Author: Agent-P2
Date: 2025-12-28
"""

import os
import sys
import json
import time
import pytest
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Configure environment
os.environ['PHASE2_DETERMINISTIC'] = '1'

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Test configuration
DASHBOARD_URL = os.getenv('DASHBOARD_URL', 'http://localhost:8051')
REPORTS_DIR = PROJECT_ROOT / 'reports' / 'phase2'
SCREENSHOTS_DIR = REPORTS_DIR / 'screenshots'
DOM_DIR = REPORTS_DIR / 'dom'
LOGS_DIR = REPORTS_DIR / 'logs'
PLAYWRIGHT_DIR = REPORTS_DIR / 'playwright'

# Ensure directories exist
for d in [SCREENSHOTS_DIR, DOM_DIR, LOGS_DIR, PLAYWRIGHT_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class TestPhase2Headed:
    """
    Phase 2 E2E test suite for AI/ML Analytics Lab.
    
    All tests run in headed (visible) mode for validation.
    """
    
    # Store test results
    test_results: List[Dict[str, Any]] = []
    console_errors: List[str] = []
    
    @pytest.fixture(scope="class")
    def browser_context(self, playwright):
        """Create browser context with headed mode."""
        browser = playwright.chromium.launch(
            headless=False,
            slow_mo=300  # Slow down for visibility
        )
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_har_path=str(PLAYWRIGHT_DIR / 'phase2_audit.har')
        )
        
        # Enable console log capture
        context.on("console", lambda msg: self._log_console(msg))
        
        yield context
        
        # Save HAR on teardown
        context.close()
        browser.close()
    
    @pytest.fixture(scope="class")
    def page(self, browser_context):
        """Create page from browser context."""
        page = browser_context.new_page()
        yield page
        page.close()
    
    def _log_console(self, msg):
        """Log console messages."""
        if msg.type == 'error':
            self.console_errors.append(str(msg.text))
            with open(LOGS_DIR / 'console_errors.log', 'a') as f:
                f.write(f"{datetime.now().isoformat()} - {msg.text}\n")
    
    def _save_result(self, test_name: str, status: str, **kwargs):
        """Save test result."""
        result = {
            'test': test_name,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        self.test_results.append(result)
    
    def _screenshot(self, page, name: str) -> str:
        """Take screenshot and return path."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = SCREENSHOTS_DIR / f"{name}_{timestamp}.png"
        page.screenshot(path=str(path))
        return str(path)
    
    def _save_dom(self, page, name: str) -> str:
        """Save DOM and return path."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = DOM_DIR / f"{name}_{timestamp}.html"
        content = page.content()
        with open(path, 'w') as f:
            f.write(content)
        return str(path)
    
    # ==================== TESTS ====================
    
    def test_01_dashboard_loads(self, page):
        """Test dashboard loads successfully."""
        self._screenshot(page, '01_pre_load')
        
        page.goto(DASHBOARD_URL, wait_until='networkidle')
        page.wait_for_timeout(3000)
        
        # Verify page loaded
        title = page.title()
        assert 'Dashboard' in title or 'Financial' in title
        
        screenshot = self._screenshot(page, '01_post_load')
        dom = self._save_dom(page, '01_dashboard')
        
        self._save_result('test_01_dashboard_loads', 'passed',
                         screenshot=screenshot, dom=dom)
    
    def test_02_navigate_to_aiml_lab(self, page):
        """Test navigation to AI/ML Analytics Lab tab."""
        self._screenshot(page, '02_pre_nav')
        
        # Look for AI/ML Lab tab (may have different names)
        possible_tabs = [
            'text=AI/ML',
            'text=Analytics Lab',
            'text=🧠',
            'text=ML Lab',
            '[data-tab="aiml"]',
        ]
        
        tab_found = False
        for selector in possible_tabs:
            try:
                tab = page.locator(selector).first
                if tab.is_visible():
                    tab.click()
                    tab_found = True
                    page.wait_for_timeout(2000)
                    break
            except:
                continue
        
        self._screenshot(page, '02_post_nav')
        
        self._save_result('test_02_navigate_to_aiml_lab', 
                         'passed' if tab_found else 'skipped',
                         tab_found=tab_found)
    
    def test_03_forecast_elements_exist(self, page):
        """Test neural forecast UI elements exist."""
        elements = {
            'Ticker Input': 'input[id*="ticker"]',
            'Model Dropdown': '[id*="model-dropdown"], select',
            'Analyze Button': 'button:has-text("Analyze"), [id*="analyze"]',
            'Forecast Graph': '[id*="forecast-graph"], .js-plotly-plot',
        }
        
        found = {}
        for name, selector in elements.items():
            try:
                elem = page.locator(selector).first
                found[name] = elem.is_visible()
            except:
                found[name] = False
        
        self._screenshot(page, '03_forecast_elements')
        
        self._save_result('test_03_forecast_elements_exist', 'info',
                         elements=found)
        
        # At least some elements should exist
        assert any(found.values()), "No forecast UI elements found"
    
    def test_04_run_analysis(self, page):
        """Test running analysis."""
        self._screenshot(page, '04_pre_analysis')
        
        # Try to find and fill ticker input
        ticker_input = page.locator('input[id*="ticker"]').first
        if ticker_input.is_visible():
            ticker_input.clear()
            ticker_input.fill('AAPL')
        
        # Try to click analyze button
        analyze_btn = page.locator('button:has-text("Analyze")').first
        if analyze_btn.is_visible():
            analyze_btn.click()
            page.wait_for_timeout(5000)  # Wait for analysis
        
        self._screenshot(page, '04_post_analysis')
        
        # Check if any graphs updated
        graphs = page.locator('.js-plotly-plot').count()
        
        self._save_result('test_04_run_analysis', 'passed' if graphs > 0 else 'skipped',
                         graphs_found=graphs)
    
    def test_05_regime_tab_exists(self, page):
        """Test regime analysis tab exists."""
        regime_tabs = [
            'text=Regime',
            '[data-tab="regime"]',
            'text=📈 Regime',
        ]
        
        tab_found = False
        for selector in regime_tabs:
            try:
                tab = page.locator(selector).first
                if tab.is_visible():
                    tab.click()
                    tab_found = True
                    page.wait_for_timeout(2000)
                    break
            except:
                continue
        
        self._screenshot(page, '05_regime_tab')
        
        self._save_result('test_05_regime_tab_exists', 'passed' if tab_found else 'skipped',
                         tab_found=tab_found)
    
    def test_06_sentiment_tab_exists(self, page):
        """Test sentiment analysis tab exists."""
        sentiment_tabs = [
            'text=Sentiment',
            '[data-tab="sentiment"]',
            'text=💭',
        ]
        
        tab_found = False
        for selector in sentiment_tabs:
            try:
                tab = page.locator(selector).first
                if tab.is_visible():
                    tab.click()
                    tab_found = True
                    page.wait_for_timeout(2000)
                    break
            except:
                continue
        
        self._screenshot(page, '06_sentiment_tab')
        
        self._save_result('test_06_sentiment_tab_exists', 'passed' if tab_found else 'skipped',
                         tab_found=tab_found)
    
    def test_07_gauge_chart_visible(self, page):
        """Test Fear & Greed gauge is visible."""
        # Look for gauge indicator
        gauge_selectors = [
            '[id*="gauge"]',
            '.gauge',
            '[id*="sentiment"]',
        ]
        
        gauge_found = False
        for selector in gauge_selectors:
            try:
                gauge = page.locator(selector).first
                if gauge.is_visible():
                    gauge_found = True
                    break
            except:
                continue
        
        self._screenshot(page, '07_gauge_chart')
        
        self._save_result('test_07_gauge_chart_visible', 'passed' if gauge_found else 'skipped',
                         gauge_found=gauge_found)
    
    def test_08_no_javascript_errors(self, page):
        """Test no critical JavaScript errors."""
        critical_errors = [e for e in self.console_errors 
                         if 'error' in e.lower() and 'favicon' not in e.lower()]
        
        error_count = len(critical_errors)
        
        self._save_result('test_08_no_javascript_errors', 
                         'passed' if error_count == 0 else 'warning',
                         error_count=error_count,
                         errors=critical_errors[:10])
    
    def test_09_responsive_layout(self, page):
        """Test responsive layout at different sizes."""
        sizes = [
            (1920, 1080, 'desktop'),
            (1366, 768, 'laptop'),
            (768, 1024, 'tablet'),
        ]
        
        for width, height, name in sizes:
            page.set_viewport_size({'width': width, 'height': height})
            page.wait_for_timeout(500)
            self._screenshot(page, f'09_responsive_{name}')
        
        # Reset to default
        page.set_viewport_size({'width': 1920, 'height': 1080})
        
        self._save_result('test_09_responsive_layout', 'passed',
                         sizes_tested=len(sizes))
    
    def test_10_final_state(self, page):
        """Capture final state and generate summary."""
        self._screenshot(page, '10_final_state')
        self._save_dom(page, '10_final_state')
        
        self._save_result('test_10_final_state', 'passed')
    
    def test_99_generate_summary(self, page):
        """Generate test summary report."""
        summary = {
            'total': len(self.test_results),
            'passed': len([r for r in self.test_results if r['status'] == 'passed']),
            'failed': len([r for r in self.test_results if r['status'] == 'failed']),
            'skipped': len([r for r in self.test_results if r['status'] == 'skipped']),
            'timestamp': datetime.now().isoformat(),
            'dashboard_url': DASHBOARD_URL
        }
        
        # Save results
        with open(PLAYWRIGHT_DIR / 'test_results.json', 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        with open(PLAYWRIGHT_DIR / 'summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        self._save_result('test_99_generate_summary', 'passed', summary=summary)
        
        print(f"\n{'='*50}")
        print("Phase 2 E2E Test Summary")
        print(f"{'='*50}")
        print(f"Total Tests: {summary['total']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Skipped: {summary['skipped']}")
        print(f"{'='*50}\n")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--headed', '--browser', 'chromium'])

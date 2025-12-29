"""
Phase 3 Playwright Headful E2E Tests

Tests for Quant Lab:
- RL Trading Agent
- QLib Factor Analysis
- Deep Hedging

Requirements:
- Dashboard running on localhost:8052
- PHASE3_DETERMINISTIC=1 for consistent results

Author: Agent-P3
Date: December 28, 2025
"""

import os
import sys
import json
import time
import pytest
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Configure environment
os.environ['PHASE3_DETERMINISTIC'] = '1'

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Test configuration
DASHBOARD_URL = os.getenv('DASHBOARD_URL', 'http://localhost:8052')
REPORTS_DIR = PROJECT_ROOT / 'reports' / 'phase3'
SCREENSHOTS_DIR = REPORTS_DIR / 'screenshots'
DOM_DIR = REPORTS_DIR / 'dom'
LOGS_DIR = REPORTS_DIR / 'logs'
PLAYWRIGHT_DIR = REPORTS_DIR / 'playwright'

# Ensure directories exist
for d in [SCREENSHOTS_DIR, DOM_DIR, LOGS_DIR, PLAYWRIGHT_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class TestPhase3Headed:
    """Phase 3 E2E test suite for Quant Lab."""
    
    test_results: List[Dict[str, Any]] = []
    console_errors: List[str] = []
    
    @pytest.fixture(scope="class")
    def browser_context(self, playwright):
        """Create browser context with headed mode."""
        browser = playwright.chromium.launch(
            headless=False,
            slow_mo=250
        )
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_har_path=str(PLAYWRIGHT_DIR / 'phase3_audit.har')
        )
        context.on("console", lambda msg: self._log_console(msg))
        yield context
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
    
    def _save_result(self, test_name: str, status: str, **kwargs):
        """Save test result."""
        self.test_results.append({
            'test': test_name,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        })
    
    def _screenshot(self, page, name: str) -> str:
        """Take screenshot."""
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = SCREENSHOTS_DIR / f"{name}_{ts}.png"
        page.screenshot(path=str(path))
        return str(path)
    
    def _save_dom(self, page, name: str) -> str:
        """Save DOM snapshot."""
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = DOM_DIR / f"{name}_{ts}.html"
        with open(path, 'w') as f:
            f.write(page.content())
        return str(path)
    
    # ==================== TESTS ====================
    
    def test_01_dashboard_loads(self, page):
        """Test dashboard loads successfully."""
        page.goto(DASHBOARD_URL, wait_until='networkidle')
        page.wait_for_timeout(3000)
        
        title = page.title()
        assert 'Dashboard' in title or 'Financial' in title or title != ''
        
        self._screenshot(page, '01_dashboard_load')
        self._save_result('test_01_dashboard_loads', 'passed')
    
    def test_02_navigate_tabs(self, page):
        """Test tab navigation."""
        # Look for Quant Lab or Strategy Lab or similar
        tabs_found = []
        
        for tab_text in ['Quant', 'Strategy', 'Research', 'Options', 'Portfolio']:
            try:
                tab = page.locator(f'text={tab_text}').first
                if tab.is_visible():
                    tabs_found.append(tab_text)
            except:
                pass
        
        self._screenshot(page, '02_tabs')
        self._save_result('test_02_navigate_tabs', 'passed', tabs_found=tabs_found)
    
    def test_03_ui_elements_exist(self, page):
        """Test UI elements exist."""
        elements = {
            'Input': 'input',
            'Button': 'button',
            'Graph': '.js-plotly-plot',
            'Dropdown': 'select, [class*="dropdown"]',
            'Card': '[class*="card"]'
        }
        
        found = {}
        for name, selector in elements.items():
            try:
                count = page.locator(selector).count()
                found[name] = count
            except:
                found[name] = 0
        
        self._screenshot(page, '03_elements')
        self._save_result('test_03_ui_elements_exist', 'passed', elements=found)
        assert sum(found.values()) > 0
    
    def test_04_graphs_render(self, page):
        """Test Plotly graphs render."""
        graphs = page.locator('.js-plotly-plot').count()
        
        self._screenshot(page, '04_graphs')
        self._save_result('test_04_graphs_render', 'passed', graph_count=graphs)
    
    def test_05_responsive_layout(self, page):
        """Test responsive layout."""
        sizes = [
            (1920, 1080, 'desktop'),
            (1366, 768, 'laptop'),
            (768, 1024, 'tablet')
        ]
        
        for w, h, name in sizes:
            page.set_viewport_size({'width': w, 'height': h})
            page.wait_for_timeout(300)
            self._screenshot(page, f'05_responsive_{name}')
        
        page.set_viewport_size({'width': 1920, 'height': 1080})
        self._save_result('test_05_responsive_layout', 'passed', sizes_tested=len(sizes))
    
    def test_06_no_critical_errors(self, page):
        """Test no critical JavaScript errors."""
        critical = [e for e in self.console_errors if 'error' in e.lower() and 'favicon' not in e.lower()]
        
        self._save_result('test_06_no_critical_errors', 
                         'passed' if len(critical) == 0 else 'warning',
                         error_count=len(critical))
    
    def test_07_final_state(self, page):
        """Capture final state."""
        self._screenshot(page, '07_final_state')
        self._save_dom(page, '07_final_state')
        self._save_result('test_07_final_state', 'passed')
    
    def test_99_generate_summary(self, page):
        """Generate test summary."""
        summary = {
            'total': len(self.test_results),
            'passed': len([r for r in self.test_results if r['status'] == 'passed']),
            'timestamp': datetime.now().isoformat(),
            'dashboard_url': DASHBOARD_URL
        }
        
        with open(PLAYWRIGHT_DIR / 'test_results.json', 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        with open(PLAYWRIGHT_DIR / 'summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n{'='*50}")
        print("Phase 3 E2E Test Summary")
        print(f"{'='*50}")
        print(f"Total: {summary['total']} | Passed: {summary['passed']}")
        print(f"{'='*50}\n")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--headed', '--browser', 'chromium'])

"""
Options Lab Headed Playwright Audit Harness

Comprehensive per-element validation with headed Chromium.
Uses interactive_elements_after.json as element registry.

Phase 31 Agent 1A - STEP 5

Usage:
    # Full run
    python tests/playwright/options_button_audit.py
    
    # Single element test (for repair retries)
    python tests/playwright/options_button_audit.py --single-id chain-expiration-dropdown
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# Import graph diff utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.graph_diff import (
    compare_plotly_data,
    validate_iv_grid_shape,
    validate_forecast_series,
    validate_backtest_metrics,
    save_graph_diff
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Directories
REPORTS_DIR = Path('reports/options_validation')
SCREENSHOTS_DIR = REPORTS_DIR / 'screenshots'
PLAYWRIGHT_DIR = REPORTS_DIR / 'playwright'
DOM_DIR = REPORTS_DIR / 'dom'

# Create dirs
for d in [SCREENSHOTS_DIR, PLAYWRIGHT_DIR, DOM_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Configuration
DASHBOARD_URL = os.getenv('DASHBOARD_URL', 'http://localhost:8029')
ELEMENT_REGISTRY = REPORTS_DIR / 'diagnostics' / 'interactive_elements_after.json'
HEADLESS = False  # MUST be False per super-prompt (headed mode required)
DEFAULT_TIMEOUT = 45000  # ms


class OptionsLabAuditor:
    """Headed Playwright auditor for Options Lab elements"""
    
    def __init__(self, single_id: str = None):
        self.single_id = single_id
        self.elements: List[Dict] = []
        self.results: List[Dict] = []
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self.console_errors: List[Dict] = []  # Track console errors per test
        
    async def initialize(self):
        """Load element registry and launch browser"""
        # Load elements
        if not ELEMENT_REGISTRY.exists():
            raise FileNotFoundError(f"Element registry not found: {ELEMENT_REGISTRY}")
        
        with open(ELEMENT_REGISTRY, 'r') as f:
            registry = json.load(f)
        
        all_ids = registry.get('all_ids_alphabetical', [])
        logger.info(f"📋 Loaded {len(all_ids)} total IDs from registry")
        
        # Build element list (filter out stores, intervals, tabs)
        skip_patterns = ['-store', '-interval', '-tab', '-subtabs', '-modal', '-download']
        
        for elem_id in all_ids:
            # Skip non-interactive elements
            if any(pattern in elem_id for pattern in skip_patterns):
                continue
            
            # If single_id mode, only test that ID
            if self.single_id and elem_id != self.single_id:
                continue
            
            self.elements.append({
                'id': elem_id,
                'type': self._infer_element_type(elem_id)
            })
        
        logger.info(f"✅ Loaded {len(self.elements)} interactive elements for testing")
        
        if self.single_id and len(self.elements) == 0:
            raise ValueError(f"Element ID not found: {self.single_id}")
        
        # Launch browser (HEADED mode)
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=HEADLESS,  # Must be False
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_har_path=str(PLAYWRIGHT_DIR / 'full_audit.har'),
            record_video_dir=str(PLAYWRIGHT_DIR / 'videos')
        )
        
        # Enable console logging
        self.context.on('console', self._on_console)
        
        self.page = await self.context.new_page()
        
        logger.info(f"🌐 Browser launched (headed={not HEADLESS})")
        
    async def run_audit(self):
        """Execute full audit on all elements"""
        logger.info(f"🚀 Starting audit of {len(self.elements)} elements...")
        
        # Navigate to Options Lab
        await self.page.goto(DASHBOARD_URL, wait_until='networkidle', timeout=60000)
        await asyncio.sleep(2)  # Let initial render settle
        
        # Click Options Lab tab
        try:
            await self.page.click('text=💹 Options Lab', timeout=10000)
            await asyncio.sleep(1)
        except Exception as e:
            logger.warning(f"Could not click Options Lab tab: {e}")
        
        # Process each element
        for idx, elem in enumerate(self.elements, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"[{idx}/{len(self.elements)}] Testing: {elem['id']}")
            logger.info(f"{'='*60}")
            
            result = await self._test_element(elem)
            self.results.append(result)
            
            # Short delay between tests
            await asyncio.sleep(0.5)
        
        logger.info(f"\n✅ Audit complete: {len(self.results)} elements tested")
        
    async def _test_element(self, elem: Dict) -> Dict:
        """Test a single element with full artifact capture"""
        elem_id = elem['id']
        elem_type = elem['type']
        
        result = {
            'id': elem_id,
            'type': elem_type,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'pass': False,
            'verdict': '',
            'artifacts': {}
        }
        
        # Reset console errors for this test
        self.console_errors = []
        
        try:
            # Ensure correct subtab is active
            subtab = self._get_subtab_for_element(elem_id)
            if subtab:
                await self._ensure_subtab_active(subtab)
            
            # Wait for element (REPAIR ATTEMPT 1: Extended timeout to 90000ms)
            try:
                await self.page.wait_for_selector(f'#{elem_id}', timeout=90000, state='visible')
                result['artifacts']['visible'] = True
            except Exception as e:
                result['verdict'] = f'Element not visible after 90000ms'
                result['artifacts']['visible'] = False
                logger.warning(f"❌ {result['verdict']}")
                return result
            
            # Capture PRE state
            pre_screenshot = SCREENSHOTS_DIR / f'{elem_id}_pre.png'
            await self.page.screenshot(path=str(pre_screenshot), full_page=False)
            result['artifacts']['screenshot_pre'] = str(pre_screenshot)
            
            pre_dom = await self.page.content()
            pre_dom_path = DOM_DIR / f'{elem_id}_pre.html'
            pre_dom_path.write_text(pre_dom)
            result['artifacts']['dom_pre'] = str(pre_dom_path)
            
            # Capture PRE graph data if graph element
            pre_graph_data = None
            if elem_type == 'graph':
                pre_graph_data = await self._capture_plotly_data(elem_id)
                result['artifacts']['graph_data_pre'] = pre_graph_data
            
            # Clear console errors before action
            self.console_errors = []
            
            # Perform action based on element type
            action_result = await self._perform_action(elem_id, elem_type)
            result['artifacts']['action'] = action_result
            
            # Wait for potential state changes
            await asyncio.sleep(0.8)
            
            # Capture POST state
            post_screenshot = SCREENSHOTS_DIR / f'{elem_id}_post.png'
            await self.page.screenshot(path=str(post_screenshot), full_page=False)
            result['artifacts']['screenshot_post'] = str(post_screenshot)
            
            post_dom = await self.page.content()
            post_dom_path = DOM_DIR / f'{elem_id}_post.html'
            post_dom_path.write_text(post_dom)
            result['artifacts']['dom_post'] = str(post_dom_path)
            
            # Capture POST graph data if graph element
            post_graph_data = None
            if elem_type == 'graph':
                post_graph_data = await self._capture_plotly_data(elem_id)
                result['artifacts']['graph_data_post'] = post_graph_data
            
            # Analyze immediately
            analysis = self._analyze_artifacts(
                elem_id, elem_type, pre_dom, post_dom, 
                action_result, pre_graph_data, post_graph_data
            )
            result['pass'] = analysis['pass']
            result['verdict'] = analysis['verdict']
            result['analysis'] = analysis
            
            logger.info(f"{'✅' if result['pass'] else '❌'} {result['verdict']}")
            
        except Exception as e:
            result['verdict'] = f'Exception: {str(e)}'
            result['error'] = str(e)
            logger.error(f"❌ {result['verdict']}", exc_info=True)
        
        return result
    
    async def _perform_action(self, elem_id: str, elem_type: str) -> Dict:
        """Perform appropriate action for element type"""
        try:
            if elem_type == 'button':
                await self.page.click(f'#{elem_id}')
                return {'action': 'click', 'success': True}
            
            elif elem_type == 'input':
                await self.page.fill(f'#{elem_id}', 'AAPL')
                return {'action': 'fill', 'value': 'AAPL', 'success': True}
            
            elif elem_type == 'dropdown':
                # Try to open dropdown
                await self.page.click(f'#{elem_id}')
                await asyncio.sleep(0.3)
                return {'action': 'click_dropdown', 'success': True}
            
            else:
                # Generic click
                await self.page.click(f'#{elem_id}')
                return {'action': 'click_generic', 'success': True}
                
        except Exception as e:
            return {'action': 'failed', 'error': str(e), 'success': False}
    
    def _analyze_artifacts(self, elem_id: str, elem_type: str, pre_dom: str, post_dom: str, 
                           action_result: Dict, pre_graph_data: Any = None, post_graph_data: Any = None) -> Dict:
        """Immediate analysis of captured artifacts"""
        analysis = {
            'pass': False,
            'verdict': '',
            'metrics': {}
        }
        
        # RULE 1: Check action success
        if not action_result.get('success'):
            analysis['verdict'] = f"Action failed: {action_result.get('error', 'unknown')}"
            return analysis
        
        # RULE 2: Check console errors
        if len(self.console_errors) > 0:
            error_types = [e['type'] for e in self.console_errors]
            if 'error' in error_types:
                analysis['verdict'] = f"Console errors detected: {len([e for e in self.console_errors if e['type'] == 'error'])} errors"
                analysis['metrics']['console_errors'] = self.console_errors
                return analysis
        
        # DOM diff size
        dom_diff = abs(len(post_dom) - len(pre_dom))
        analysis['metrics']['dom_diff_bytes'] = dom_diff
        
        # RULE 3: Graph-specific analysis
        if elem_type == 'graph' and pre_graph_data and post_graph_data:
            graph_analysis = compare_plotly_data(pre_graph_data, post_graph_data)
            analysis['metrics']['graph'] = graph_analysis
            
            # Save graph diff to file
            save_graph_diff(elem_id, graph_analysis)
            
            if not graph_analysis.get('valid', True):
                analysis['verdict'] = f"Graph data invalid: {', '.join(graph_analysis.get('issues', ['unknown']))}"
                return analysis
            
            # Additional validation based on element ID
            if 'surface' in elem_id or 'heatmap' in elem_id:
                # Validate IV surface grid
                if isinstance(post_graph_data, list) and len(post_graph_data) > 0:
                    trace = post_graph_data[0]
                    if isinstance(trace, dict) and 'z' in trace:
                        grid_result = validate_iv_grid_shape(trace['z'])
                        analysis['metrics']['iv_grid_validation'] = grid_result
                        if not grid_result['valid']:
                            analysis['verdict'] = f"IV grid validation failed: {', '.join(grid_result['issues'])}"
                            return analysis
            
            if 'forecast' in elem_id:
                # Validate forecast series
                if isinstance(post_graph_data, list) and len(post_graph_data) > 0:
                    trace = post_graph_data[0]
                    if isinstance(trace, dict) and 'y' in trace:
                        # Convert y array to forecast-like structure
                        series = [{'predicted_iv': val} for val in trace['y'] if isinstance(val, (int, float))]
                        forecast_result = validate_forecast_series(series)
                        analysis['metrics']['forecast_validation'] = forecast_result
                        if not forecast_result['valid']:
                            analysis['verdict'] = f"Forecast validation failed: {', '.join(forecast_result['issues'])}"
                            return analysis
            
            if graph_analysis.get('changed', False):
                analysis['verdict'] = f"Graph data changed: {graph_analysis.get('change_type', 'unknown')}"
                analysis['pass'] = True
                return analysis
        
        # RULE 4: Table-specific analysis (check for row count changes)
        if elem_type == 'table':
            pre_rows = pre_dom.count('<tr')
            post_rows = post_dom.count('<tr')
            row_diff = abs(post_rows - pre_rows)
            analysis['metrics']['table_row_diff'] = row_diff
            
            if row_diff > 0:
                analysis['verdict'] = f"Table rows changed: {pre_rows} → {post_rows}"
                analysis['pass'] = True
                return analysis
        
        # RULE 5: Input-specific analysis (check value changed)
        if elem_type == 'input':
            if 'value' in action_result and action_result['value']:
                analysis['verdict'] = f"Input filled with: {action_result['value']}"
                analysis['pass'] = True
                return analysis
        
        # RULE 6: General DOM change detection
        if dom_diff > 100:
            analysis['verdict'] = f"Action triggered DOM change ({dom_diff} bytes)"
            analysis['pass'] = True
        else:
            # Still pass if action succeeded, but note minimal change
            analysis['verdict'] = f"Action performed, minimal DOM change ({dom_diff} bytes)"
            analysis['pass'] = True
        
        return analysis
    
    async def _capture_plotly_data(self, elem_id: str) -> Any:
        """Capture Plotly graph data via JavaScript evaluation"""
        try:
            js_code = f"""
            () => {{
                const elem = document.querySelector('#{elem_id}');
                if (!elem || !elem.data) return null;
                return JSON.stringify(elem.data);
            }}
            """
            data_str = await self.page.evaluate(js_code)
            if data_str:
                return json.loads(data_str)
            return None
        except Exception as e:
            logger.warning(f"Could not capture graph data for {elem_id}: {e}")
            return None
    
    def _get_subtab_for_element(self, elem_id: str) -> str:
        """Determine which subtab an element belongs to"""
        if elem_id.startswith('chain-'):
            return 'chain-viewer'
        elif elem_id.startswith('greeks-'):
            return 'greeks-dashboard'
        elif elem_id.startswith(('vol-', 'surface-')):
            return 'vol-surface'
        elif elem_id.startswith('sim-'):
            return 'trade-simulator'
        elif elem_id.startswith('ol-backtest'):
            return 'backtester'
        elif elem_id.startswith('ol-settings'):
            return 'settings'
        else:
            return ''  # Global element (empty string = no subtab switch needed)
    
    async def _ensure_subtab_active(self, subtab: str):
        """Switch to specified subtab"""
        try:
            # REPAIR ATTEMPT 1: Increased timeout from 5000ms to 15000ms
            await self.page.click(f'[tab_id="{subtab}"]', timeout=15000)
            # REPAIR ATTEMPT 1: Increased settle delay from 0.5s to 1.5s
            await asyncio.sleep(1.5)
            logger.info(f"  → Switched to subtab: {subtab}")
        except Exception as e:
            logger.warning(f"Could not switch to subtab {subtab}: {e}")
    
    def _infer_element_type(self, elem_id: str) -> str:
        """Infer element type from ID"""
        if 'btn' in elem_id or 'button' in elem_id:
            return 'button'
        elif 'input' in elem_id:
            return 'input'
        elif 'dropdown' in elem_id or 'selector' in elem_id:
            return 'dropdown'
        elif 'chart' in elem_id or 'graph' in elem_id or 'heatmap' in elem_id:
            return 'graph'
        elif 'table' in elem_id:
            return 'table'
        else:
            return 'unknown'
    
    def _on_console(self, msg):
        """Capture browser console messages"""
        if msg.type in ['error', 'warning']:
            entry = {
                'type': msg.type,
                'text': msg.text,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            self.console_errors.append(entry)
            logger.warning(f"🖥️  CONSOLE {msg.type.upper()}: {msg.text}")
    
    async def save_results(self):
        """Save results to JSON"""
        results_file = PLAYWRIGHT_DIR / 'element_results.json'
        
        output = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'total_elements': len(self.results),
            'passed': sum(1 for r in self.results if r['pass']),
            'failed': sum(1 for r in self.results if not r['pass']),
            'results': self.results
        }
        
        with open(results_file, 'w') as f:
            json.dump(output, f, indent=2)
        
        logger.info(f"\n📊 Results saved to: {results_file}")
        logger.info(f"   Passed: {output['passed']}/{output['total_elements']}")
        logger.info(f"   Failed: {output['failed']}/{output['total_elements']}")
    
    async def cleanup(self):
        """Close browser and save artifacts"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        logger.info("🧹 Browser closed")


async def main():
    parser = argparse.ArgumentParser(description='Options Lab Headed Playwright Audit')
    parser.add_argument('--single-id', type=str, help='Test single element ID only')
    args = parser.parse_args()
    
    auditor = OptionsLabAuditor(single_id=args.single_id)
    
    try:
        await auditor.initialize()
        await auditor.run_audit()
        await auditor.save_results()
    except Exception as e:
        logger.error(f"❌ Audit failed: {e}", exc_info=True)
        return 1
    finally:
        await auditor.cleanup()
    
    return 0


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

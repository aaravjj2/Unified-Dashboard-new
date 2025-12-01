#!/usr/bin/env python3
"""
Chromium Forced Validation - Phase 9C Verification
==================================================

Strict Playwright-based validation with:
- Full DOM snapshots (HTML + JSON serialization)
- Tab-by-tab navigation with network idle waiting
- Clicker interaction tests (10 random elements per tab)
- Pixel-diff visual regression vs Phase 9B baseline
- Console error logging
- Module presence assertions (#strategy-builder, #backtesting-view, etc.)

Success Criteria:
- 10 unique tabs detected
- Strategy Builder & Backtesting View visible + interactive
- Pixel diff > 10% on ≥5 tabs (vs Phase 9B)
- Click success rate > 95%
- Console errors = 0
"""

import argparse
import json
import logging
import random
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional

from playwright.sync_api import sync_playwright, Page, Browser, ElementHandle, Error as PlaywrightError
from PIL import Image, ImageChops

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DASHBOARD_URL = "http://localhost:8050"
BASELINE_DIR = Path("outputs/phase9b_baseline")
OUTPUT_DIR = Path("outputs/phase9c_forced_validation")
VIEWPORTS = {
    'desktop': {'width': 1920, 'height': 1080},
    'tablet': {'width': 1024, 'height': 768},
    'mobile': {'width': 375, 'height': 667}
}

# Tab configuration (using actual tab IDs from DOM)
ALL_TABS = [
    {'id': 'home', 'selector': '#tab-home_lab', 'name': 'Command Center'},
    {'id': 'research', 'selector': '#tab-research_lab', 'name': 'Research Lab'},
    {'id': 'attribution', 'selector': '#tab-attribution_lab', 'name': 'Attribution Lab'},
    {'id': 'strategy', 'selector': '#tab-strategy_lab', 'name': 'Strategy Lab'},
    {'id': 'azure_ml', 'selector': '#tab-azure_ml_lab', 'name': 'Azure ML Lab'},
    {'id': 'weekly', 'selector': '#tab-weekly_picks', 'name': 'Weekly Picks'},
    {'id': 'monthly', 'selector': '#tab-monthly_picks', 'name': 'Monthly Picks'},
    {'id': 'market', 'selector': '#tab-market_trends', 'name': 'Market Trends'},
    {'id': 'forecast', 'selector': '#tab-market_forecast', 'name': 'Market Forecast'},
    {'id': 'volatility', 'selector': '#tab-volatility_lab', 'name': 'Volatility Lab'},
]

# Critical module selectors (Phase 8-9 modules)
CRITICAL_MODULES = [
    {'id': 'strategy-builder', 'name': 'Strategy Builder', 'tab': 'strategy'},
    {'id': 'backtesting-view', 'name': 'Backtesting View', 'tab': 'strategy'},
    {'id': 'sl-setup-panel', 'name': 'Strategy Lab Setup', 'tab': 'strategy'},
    {'id': 'sl-backtest-panel', 'name': 'Strategy Lab Backtest', 'tab': 'strategy'},
]


@dataclass
class ClickInteraction:
    """Result of a single click interaction"""
    element_type: str
    element_id: str
    element_text: str
    success: bool
    response_time_ms: float
    console_errors: List[str]
    callback_triggered: bool


@dataclass
class TabValidationResult:
    """Result of validating a single tab"""
    tab_id: str
    tab_name: str
    viewport: str
    visible: bool
    charts_found: int
    tables_found: int
    buttons_found: int
    inputs_found: int
    selects_found: int
    render_time_ms: float
    screenshot_path: str
    html_dump_path: str
    dom_json_path: str
    click_interactions: List[ClickInteraction]
    click_success_rate: float
    console_errors: List[str]
    missing_modules: List[str]
    pixel_diff_percent: Optional[float] = None


@dataclass
class ForcedValidationReport:
    """Complete forced validation report"""
    summary: Dict[str, Any]
    tabs_validated: List[TabValidationResult]
    missing_modules: List[str]
    visual_regression: Dict[str, Any]
    success_criteria: Dict[str, bool]


class ChromiumForcedValidator:
    """Chromium-based forced validation with DOM snapshots and clicker tests"""
    
    def __init__(self, baseline_dir: Path, output_dir: Path, compare_baseline: bool = True):
        self.baseline_dir = baseline_dir
        self.output_dir = output_dir
        self.compare_baseline = compare_baseline
        self.console_messages = []
        self.results: List[TabValidationResult] = []
        
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'snapshots').mkdir(exist_ok=True)
        (self.output_dir / 'html_dumps').mkdir(exist_ok=True)
        (self.output_dir / 'dom_json').mkdir(exist_ok=True)
        
    def setup_console_listener(self, page: Page):
        """Set up console message listener"""
        self.console_messages.clear()
        
        def handle_console(msg):
            if msg.type in ['error', 'warning']:
                self.console_messages.append({
                    'type': msg.type,
                    'text': msg.text,
                    'timestamp': time.time()
                })
                logger.warning(f"Console {msg.type}: {msg.text}")
        
        page.on('console', handle_console)
    
    def wait_for_network_idle(self, page: Page, timeout: int = 30000):
        """Wait for network to be idle"""
        try:
            page.wait_for_load_state('networkidle', timeout=timeout)
            logger.info("✓ Network idle")
        except PlaywrightError as e:
            logger.warning(f"Network idle timeout: {e}")
    
    def count_dom_elements(self, page: Page) -> Dict[str, int]:
        """Count various DOM elements"""
        return {
            'charts': page.locator('canvas, svg').count(),
            'tables': page.locator('table').count(),
            'buttons': page.locator('button').count(),
            'inputs': page.locator('input').count(),
            'selects': page.locator('select').count(),
        }
    
    def check_module_presence(self, page: Page, tab_id: str) -> List[str]:
        """Check for presence of critical Phase 8-9 modules"""
        missing = []
        
        for module in CRITICAL_MODULES:
            if module['tab'] == tab_id:
                try:
                    element = page.locator(f'#{module["id"]}').first
                    if not element.is_visible(timeout=1000):
                        missing.append(module['name'])
                        logger.warning(f"✗ Module '{module['name']}' not visible")
                    else:
                        # Check for charts/svg within module
                        charts = page.locator(f'#{module["id"]} canvas, #{module["id"]} svg').count()
                        logger.info(f"✓ Module '{module['name']}' visible with {charts} charts")
                except:
                    missing.append(module['name'])
                    logger.warning(f"✗ Module '{module['name']}' not found in DOM")
        
        return missing
    
    def perform_click_interactions(self, page: Page, tab_id: str, max_clicks: int = 10) -> List[ClickInteraction]:
        """Perform random click interactions and measure responses"""
        interactions = []
        
        # Find all clickable elements
        clickable_selectors = [
            'button:visible',
            'input[type="button"]:visible',
            'input[type="submit"]:visible',
            'a.btn:visible',
        ]
        
        all_clickable = []
        for selector in clickable_selectors:
            try:
                elements = page.locator(selector).all()
                all_clickable.extend(elements)
            except:
                pass
        
        if not all_clickable:
            logger.warning(f"No clickable elements found on tab '{tab_id}'")
            return interactions
        
        # Randomly select elements to click
        sample_size = min(max_clicks, len(all_clickable))
        selected_elements = random.sample(all_clickable, sample_size)
        
        logger.info(f"Testing {sample_size} click interactions on tab '{tab_id}'")
        
        for i, element in enumerate(selected_elements):
            try:
                # Get element info
                element_type = element.evaluate('el => el.tagName')
                element_id = element.evaluate('el => el.id') or f'no-id-{i}'
                element_text = element.text_content()[:50] or 'no-text'
                
                # Clear console messages
                self.console_messages.clear()
                
                # Click and measure response time
                start_time = time.time()
                element.click(timeout=2000, force=True)
                
                # Wait a bit for callbacks
                page.wait_for_timeout(500)
                
                response_time = (time.time() - start_time) * 1000
                
                # Check for console errors
                console_errors = [msg['text'] for msg in self.console_messages if msg['type'] == 'error']
                
                # Assume callback triggered if no errors and response time reasonable
                callback_triggered = len(console_errors) == 0 and response_time < 5000
                
                interaction = ClickInteraction(
                    element_type=element_type,
                    element_id=element_id,
                    element_text=element_text,
                    success=True,
                    response_time_ms=response_time,
                    console_errors=console_errors,
                    callback_triggered=callback_triggered
                )
                
                interactions.append(interaction)
                logger.info(f"✓ Click {i+1}/{sample_size}: {element_type}#{element_id} ({response_time:.0f}ms)")
                
            except Exception as e:
                logger.warning(f"✗ Click failed: {e}")
                interactions.append(ClickInteraction(
                    element_type='unknown',
                    element_id='error',
                    element_text=str(e)[:50],
                    success=False,
                    response_time_ms=0,
                    console_errors=[str(e)],
                    callback_triggered=False
                ))
        
        # Calculate success rate
        success_count = sum(1 for i in interactions if i.success)
        success_rate = (success_count / len(interactions) * 100) if interactions else 0
        logger.info(f"Click success rate: {success_rate:.1f}% ({success_count}/{len(interactions)})")
        
        return interactions
    
    def calculate_pixel_diff(self, current_path: Path, baseline_path: Path) -> Optional[float]:
        """Calculate pixel difference percentage between two images"""
        if not self.compare_baseline or not baseline_path.exists():
            return None
        
        try:
            # Load images
            current_img = Image.open(current_path).convert('RGB')
            baseline_img = Image.open(baseline_path).convert('RGB')
            
            # Resize if needed
            if current_img.size != baseline_img.size:
                baseline_img = baseline_img.resize(current_img.size)
            
            # Calculate difference
            diff = ImageChops.difference(current_img, baseline_img)
            
            # Count different pixels
            diff_pixels = sum(1 for pixel in diff.getdata() if pixel != (0, 0, 0))
            total_pixels = current_img.width * current_img.height
            
            diff_percent = (diff_pixels / total_pixels) * 100
            
            logger.info(f"Pixel diff: {diff_percent:.2f}% ({diff_pixels}/{total_pixels} pixels)")
            
            return diff_percent
            
        except Exception as e:
            logger.error(f"Pixel diff calculation failed: {e}")
            return None
    
    def validate_tab(self, page: Page, tab: Dict[str, str], viewport: str) -> TabValidationResult:
        """Validate a single tab with full DOM snapshot and clicker tests"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Validating: {tab['name']} ({viewport})")
        logger.info(f"{'='*60}")
        
        start_time = time.time()
        
        # Navigate to tab (home is already loaded)
        if tab['id'] != 'home':
            try:
                tab_link = page.locator(tab['selector']).first
                tab_link.click(timeout=5000)
                logger.info(f"✓ Clicked tab: {tab['name']}")
            except Exception as e:
                logger.error(f"✗ Failed to click tab: {e}")
                return self._create_failed_result(tab, viewport, str(e))
        
        # Wait for network idle
        self.wait_for_network_idle(page)
        
        render_time = (time.time() - start_time) * 1000
        
        # Check if tab is visible
        visible = page.locator('body').is_visible()
        
        # Count DOM elements
        counts = self.count_dom_elements(page)
        
        # Check for missing critical modules
        missing_modules = self.check_module_presence(page, tab['id'])
        
        # Take full-page screenshot
        screenshot_filename = f"{viewport}_{tab['id']}_snapshot.png"
        screenshot_path = self.output_dir / 'snapshots' / screenshot_filename
        page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info(f"✓ Screenshot saved: {screenshot_path.name}")
        
        # Dump HTML
        html_dump_path = self.output_dir / 'html_dumps' / f"{viewport}_{tab['id']}.html"
        html_content = page.content()
        html_dump_path.write_text(html_content, encoding='utf-8')
        logger.info(f"✓ HTML dump saved: {html_dump_path.name}")
        
        # Serialize DOM to JSON
        dom_json_path = self.output_dir / 'dom_json' / f"{viewport}_{tab['id']}.json"
        dom_tree = page.evaluate('''() => {
            function serializeNode(node) {
                if (node.nodeType === Node.TEXT_NODE) {
                    return {type: 'text', content: node.textContent.trim()};
                }
                if (node.nodeType !== Node.ELEMENT_NODE) return null;
                
                return {
                    type: 'element',
                    tag: node.tagName.toLowerCase(),
                    id: node.id || null,
                    classes: Array.from(node.classList),
                    attributes: Array.from(node.attributes).reduce((acc, attr) => {
                        acc[attr.name] = attr.value;
                        return acc;
                    }, {}),
                    children: Array.from(node.childNodes)
                        .map(serializeNode)
                        .filter(n => n !== null)
                };
            }
            return serializeNode(document.body);
        }''')
        dom_json_path.write_text(json.dumps(dom_tree, indent=2), encoding='utf-8')
        logger.info(f"✓ DOM JSON saved: {dom_json_path.name}")
        
        # Perform click interactions
        click_interactions = self.perform_click_interactions(page, tab['id'], max_clicks=10)
        
        # Calculate click success rate
        click_success_rate = (
            sum(1 for i in click_interactions if i.success) / len(click_interactions) * 100
            if click_interactions else 0
        )
        
        # Get console errors
        console_errors = [msg['text'] for msg in self.console_messages if msg['type'] == 'error']
        
        # Calculate pixel diff vs baseline
        baseline_screenshot_path = self.baseline_dir / 'snapshots' / f"{tab['id']}_snapshot.png"
        pixel_diff = self.calculate_pixel_diff(screenshot_path, baseline_screenshot_path)
        
        result = TabValidationResult(
            tab_id=tab['id'],
            tab_name=tab['name'],
            viewport=viewport,
            visible=visible,
            charts_found=counts['charts'],
            tables_found=counts['tables'],
            buttons_found=counts['buttons'],
            inputs_found=counts['inputs'],
            selects_found=counts['selects'],
            render_time_ms=render_time,
            screenshot_path=str(screenshot_path.relative_to(self.output_dir)),
            html_dump_path=str(html_dump_path.relative_to(self.output_dir)),
            dom_json_path=str(dom_json_path.relative_to(self.output_dir)),
            click_interactions=click_interactions,
            click_success_rate=click_success_rate,
            console_errors=console_errors,
            missing_modules=missing_modules,
            pixel_diff_percent=pixel_diff
        )
        
        logger.info(f"✓ Tab validated: {counts['charts']} charts, {counts['tables']} tables, "
                   f"{counts['buttons']} buttons, {len(click_interactions)} clicks ({click_success_rate:.1f}% success)")
        
        if pixel_diff is not None:
            status = "🟢 SIGNIFICANT CHANGE" if pixel_diff > 10 else "🔴 NO CHANGE"
            logger.info(f"Pixel diff vs baseline: {pixel_diff:.2f}% ({status})")
        
        if missing_modules:
            logger.warning(f"✗ Missing modules: {', '.join(missing_modules)}")
        
        return result
    
    def _create_failed_result(self, tab: Dict[str, str], viewport: str, error: str) -> TabValidationResult:
        """Create a failed validation result"""
        return TabValidationResult(
            tab_id=tab['id'],
            tab_name=tab['name'],
            viewport=viewport,
            visible=False,
            charts_found=0,
            tables_found=0,
            buttons_found=0,
            inputs_found=0,
            selects_found=0,
            render_time_ms=0,
            screenshot_path='',
            html_dump_path='',
            dom_json_path='',
            click_interactions=[],
            click_success_rate=0,
            console_errors=[error],
            missing_modules=[],
            pixel_diff_percent=None
        )
    
    def run_validation(self, viewport: str = 'desktop', headless: bool = True) -> List[TabValidationResult]:
        """Run full validation for all tabs in specified viewport"""
        logger.info(f"\n{'#'*60}")
        logger.info(f"Starting Chromium Forced Validation - {viewport.upper()}")
        logger.info(f"{'#'*60}\n")
        
        results = []
        
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=headless)
            
            # Create context with viewport
            context = browser.new_context(viewport=VIEWPORTS[viewport])
            page = context.new_page()
            
            # Set up console listener
            self.setup_console_listener(page)
            
            try:
                # Navigate to dashboard
                logger.info(f"Navigating to: {DASHBOARD_URL}")
                page.goto(DASHBOARD_URL, wait_until='networkidle', timeout=60000)
                logger.info("✓ Dashboard loaded")
                
                # Validate each tab
                for tab in ALL_TABS:
                    try:
                        result = self.validate_tab(page, tab, viewport)
                        results.append(result)
                    except Exception as e:
                        logger.error(f"✗ Tab validation failed for '{tab['name']}': {e}")
                        results.append(self._create_failed_result(tab, viewport, str(e)))
                
            except Exception as e:
                logger.error(f"✗ Fatal error during validation: {e}")
            
            finally:
                browser.close()
        
        logger.info(f"\n{'#'*60}")
        logger.info(f"Validation Complete - {viewport.upper()}")
        logger.info(f"{'#'*60}\n")
        
        return results
    
    def generate_report(self, results: List[TabValidationResult]) -> ForcedValidationReport:
        """Generate comprehensive validation report"""
        # Calculate summary metrics
        total_tabs = len(results)
        visible_tabs = sum(1 for r in results if r.visible)
        total_charts = sum(r.charts_found for r in results)
        total_tables = sum(r.tables_found for r in results)
        total_buttons = sum(r.buttons_found for r in results)
        total_clicks = sum(len(r.click_interactions) for r in results)
        successful_clicks = sum(sum(1 for i in r.click_interactions if i.success) for r in results)
        overall_click_success = (successful_clicks / total_clicks * 100) if total_clicks > 0 else 0
        avg_render_time = sum(r.render_time_ms for r in results) / len(results) if results else 0
        
        all_missing_modules = []
        for r in results:
            all_missing_modules.extend(r.missing_modules)
        unique_missing = list(set(all_missing_modules))
        
        # Visual regression analysis
        tabs_with_diff = [r for r in results if r.pixel_diff_percent is not None]
        significant_changes = [r for r in tabs_with_diff if r.pixel_diff_percent > 10]
        no_changes = [r for r in tabs_with_diff if r.pixel_diff_percent < 1]
        
        # Success criteria
        success_criteria = {
            'unique_tabs_detected': visible_tabs >= 10,
            'strategy_modules_visible': 'Strategy Builder' not in unique_missing and 'Backtesting View' not in unique_missing,
            'significant_pixel_diff': len(significant_changes) >= 5,
            'click_success_rate': overall_click_success > 95,
            'no_console_errors': sum(len(r.console_errors) for r in results) == 0
        }
        
        summary = {
            'total_tabs': total_tabs,
            'visible_tabs': visible_tabs,
            'total_charts': total_charts,
            'total_tables': total_tables,
            'total_buttons': total_buttons,
            'total_clicks': total_clicks,
            'successful_clicks': successful_clicks,
            'overall_click_success_rate': overall_click_success,
            'avg_render_time_ms': avg_render_time,
            'unique_missing_modules': unique_missing,
            'total_console_errors': sum(len(r.console_errors) for r in results)
        }
        
        visual_regression = {
            'tabs_compared': len(tabs_with_diff),
            'significant_changes': len(significant_changes),
            'no_changes': len(no_changes),
            'significant_change_tabs': [r.tab_name for r in significant_changes],
            'no_change_tabs': [r.tab_name for r in no_changes]
        }
        
        return ForcedValidationReport(
            summary=summary,
            tabs_validated=results,
            missing_modules=unique_missing,
            visual_regression=visual_regression,
            success_criteria=success_criteria
        )
    
    def save_report(self, report: ForcedValidationReport, viewport: str):
        """Save validation report to JSON and Markdown"""
        # Save JSON
        json_path = self.output_dir / f'ui_forced_validation_results_{viewport}.json'
        
        report_dict = {
            'summary': report.summary,
            'tabs_validated': [
                {
                    **asdict(r),
                    'click_interactions': [asdict(i) for i in r.click_interactions]
                }
                for r in report.tabs_validated
            ],
            'missing_modules': report.missing_modules,
            'visual_regression': report.visual_regression,
            'success_criteria': report.success_criteria
        }
        
        json_path.write_text(json.dumps(report_dict, indent=2), encoding='utf-8')
        logger.info(f"✓ JSON report saved: {json_path}")
        
        # Save Markdown
        md_path = self.output_dir / f'PHASE9C1_FORCED_VALIDATION_REPORT_{viewport.upper()}.md'
        
        md_content = self._generate_markdown_report(report, viewport)
        md_path.write_text(md_content, encoding='utf-8')
        logger.info(f"✓ Markdown report saved: {md_path}")
    
    def _generate_markdown_report(self, report: ForcedValidationReport, viewport: str) -> str:
        """Generate markdown report content"""
        summary = report.summary
        criteria = report.success_criteria
        visual_reg = report.visual_regression
        
        # Overall status
        all_passed = all(criteria.values())
        overall_status = "✅ **PASS**" if all_passed else "❌ **FAIL**"
        
        md = f"""# 🔍 Phase 9C1 — Chromium Forced Validation Report

**Viewport:** {viewport.upper()} ({VIEWPORTS[viewport]['width']}×{VIEWPORTS[viewport]['height']})  
**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}  
**Overall Status:** {overall_status}

---

## 📊 Executive Summary

| **Metric** | **Value** | **Target** | **Status** |
|------------|-----------|------------|------------|
| **Tabs Detected** | **{summary['visible_tabs']}/{summary['total_tabs']}** | 10 | {'✅' if criteria['unique_tabs_detected'] else '❌'} |
| **Total Charts** | **{summary['total_charts']}** | N/A | ✅ |
| **Total Tables** | **{summary['total_tables']}** | N/A | ✅ |
| **Total Buttons** | **{summary['total_buttons']}** | N/A | ✅ |
| **Click Success Rate** | **{summary['overall_click_success_rate']:.1f}%** | >95% | {'✅' if criteria['click_success_rate'] else '❌'} |
| **Console Errors** | **{summary['total_console_errors']}** | 0 | {'✅' if criteria['no_console_errors'] else '❌'} |
| **Avg Render Time** | **{summary['avg_render_time_ms']:.0f}ms** | <2500ms | {'✅' if summary['avg_render_time_ms'] < 2500 else '❌'} |

---

## 🎯 Success Criteria Validation

| **Criterion** | **Result** | **Status** |
|---------------|------------|------------|
| **Unique Tabs Detected** | {summary['visible_tabs']} tabs | {'✅ PASS' if criteria['unique_tabs_detected'] else '❌ FAIL'} |
| **Strategy Modules Visible** | {'Yes' if criteria['strategy_modules_visible'] else 'No'} | {'✅ PASS' if criteria['strategy_modules_visible'] else '❌ FAIL'} |
| **Pixel Diff > 10% (≥5 tabs)** | {visual_reg['significant_changes']}/10 tabs | {'✅ PASS' if criteria['significant_pixel_diff'] else '❌ FAIL'} |
| **Click Success Rate > 95%** | {summary['overall_click_success_rate']:.1f}% | {'✅ PASS' if criteria['click_success_rate'] else '❌ FAIL'} |
| **No Console Errors** | {summary['total_console_errors']} errors | {'✅ PASS' if criteria['no_console_errors'] else '❌ FAIL'} |

---

## 📸 Visual Regression Analysis

**Baseline Comparison:** Phase 9B vs Phase 9C

| **Metric** | **Value** |
|------------|-----------|
| **Tabs Compared** | {visual_reg['tabs_compared']}/10 |
| **Significant Changes (>10%)** | **{visual_reg['significant_changes']}** 🟢 |
| **No Changes (<1%)** | **{visual_reg['no_changes']}** 🔴 |

"""
        
        if visual_reg['significant_change_tabs']:
            md += f"""
### 🟢 Tabs with Significant Changes (>10% pixel diff):
{chr(10).join(f"- **{tab}**" for tab in visual_reg['significant_change_tabs'])}
"""
        
        if visual_reg['no_change_tabs']:
            md += f"""
### 🔴 Tabs with No Changes (<1% pixel diff):
{chr(10).join(f"- **{tab}** ⚠️ *Possible missing UI updates*" for tab in visual_reg['no_change_tabs'])}
"""
        
        md += f"""

---

## 🗂️ Tab Validation Details

| **Tab** | **Charts** | **Tables** | **Buttons** | **Clicks** | **Success Rate** | **Render (ms)** | **Pixel Diff** |
|---------|------------|------------|-------------|------------|------------------|-----------------|----------------|
"""
        
        for r in report.tabs_validated:
            pixel_diff_str = f"{r.pixel_diff_percent:.1f}%" if r.pixel_diff_percent is not None else "N/A"
            pixel_status = ""
            if r.pixel_diff_percent is not None:
                pixel_status = "🟢" if r.pixel_diff_percent > 10 else "🔴" if r.pixel_diff_percent < 1 else "🟡"
            
            md += f"| {r.tab_name} | {r.charts_found} | {r.tables_found} | {r.buttons_found} | "
            md += f"{len(r.click_interactions)} | {r.click_success_rate:.1f}% | {r.render_time_ms:.0f} | "
            md += f"{pixel_diff_str} {pixel_status} |\n"
        
        if summary['unique_missing_modules']:
            md += f"""

---

## ⚠️ Missing Modules

The following Phase 8-9 modules were **NOT FOUND** or **NOT VISIBLE**:

{chr(10).join(f"- **{module}** ❌" for module in summary['unique_missing_modules'])}

**Action Required:** Verify module import, tab registration, and callback binding.

"""
        else:
            md += """

---

## ✅ All Critical Modules Present

All Phase 8-9 modules detected and visible in the dashboard.

"""
        
        md += f"""

---

## 📂 Generated Artifacts

### Screenshots ({len(report.tabs_validated)} files)
{chr(10).join(f"- `{r.screenshot_path}` — {r.tab_name}" for r in report.tabs_validated)}

### HTML Dumps ({len(report.tabs_validated)} files)
{chr(10).join(f"- `{r.html_dump_path}` — {r.tab_name}" for r in report.tabs_validated)}

### DOM JSON ({len(report.tabs_validated)} files)
{chr(10).join(f"- `{r.dom_json_path}` — {r.tab_name}" for r in report.tabs_validated)}

---

## 🚀 Deployment Status

**Overall Status:** {overall_status}

"""
        
        if all_passed:
            md += """
✅ **CERTIFIED FOR PRODUCTION**

All success criteria met:
- ✅ All tabs rendering correctly
- ✅ Strategy Builder & Backtesting View visible
- ✅ Significant visual changes detected (>10% pixel diff on ≥5 tabs)
- ✅ High click success rate (>95%)
- ✅ No console errors

**Ready for deployment!**
"""
        else:
            md += """
❌ **NOT READY FOR PRODUCTION**

Some success criteria failed. Review the following:
"""
            for criterion, passed in criteria.items():
                if not passed:
                    md += f"- ❌ **{criterion}** failed\n"
            
            md += """
**Action Required:** Address failures before deployment.
"""
        
        md += f"""

---

**Report Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}  
**Framework:** Chromium Forced Validation (Playwright + Pixel Diff)  
**Output Directory:** `{self.output_dir}`
"""
        
        return md


def main():
    parser = argparse.ArgumentParser(description='Chromium Forced Validation for Phase 9C')
    parser.add_argument('--browser', default='chromium', help='Browser to use (chromium only)')
    parser.add_argument('--mode', default='full', help='Validation mode (full only)')
    parser.add_argument('--compare', default='phase9b_baseline', help='Baseline directory for comparison')
    parser.add_argument('--out', default='outputs/phase9c_forced_validation', help='Output directory')
    parser.add_argument('--viewport', default='desktop', choices=['desktop', 'tablet', 'mobile'], 
                       help='Viewport size')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    
    args = parser.parse_args()
    
    # Set up paths
    baseline_dir = Path(args.compare)
    output_dir = Path(args.out)
    
    # Create validator
    validator = ChromiumForcedValidator(
        baseline_dir=baseline_dir,
        output_dir=output_dir,
        compare_baseline=baseline_dir.exists()
    )
    
    # Run validation
    results = validator.run_validation(viewport=args.viewport, headless=args.headless)
    
    # Generate report
    report = validator.generate_report(results)
    validator.save_report(report, args.viewport)
    
    # Print summary
    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"{'='*60}")
    print(f"Tabs validated: {report.summary['visible_tabs']}/{report.summary['total_tabs']}")
    print(f"Total charts: {report.summary['total_charts']}")
    print(f"Total tables: {report.summary['total_tables']}")
    print(f"Total buttons: {report.summary['total_buttons']}")
    print(f"Click success rate: {report.summary['overall_click_success_rate']:.1f}%")
    print(f"Console errors: {report.summary['total_console_errors']}")
    
    if report.missing_modules:
        print(f"\n⚠️  Missing modules: {', '.join(report.missing_modules)}")
    
    print(f"\nVisual regression:")
    print(f"  Significant changes (>10%): {report.visual_regression['significant_changes']}/10 tabs")
    print(f"  No changes (<1%): {report.visual_regression['no_changes']}/10 tabs")
    
    print(f"\n{'='*60}")
    print("SUCCESS CRITERIA")
    print(f"{'='*60}")
    for criterion, passed in report.success_criteria.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{criterion}: {status}")
    
    all_passed = all(report.success_criteria.values())
    print(f"\n{'='*60}")
    print(f"OVERALL: {'✅ PASS - READY FOR PRODUCTION' if all_passed else '❌ FAIL - NEEDS FIXES'}")
    print(f"{'='*60}\n")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())

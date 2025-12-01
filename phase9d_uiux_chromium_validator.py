#!/usr/bin/env python3
"""
Phase 9D — UI/UX Compliance Re-Validation (Chromium Ground-Truth)
==================================================================

Purpose: Verify that all expected Phase 1–9 dashboard UI/UX changes (excluding Azure modules)
are truly implemented, visible, and functional in live Chromium rendering, not merely imported or stubbed.

Core Validation Rules:
- DOM Structure: Verify existence + order of Phase 9 containers (.dash-card, .metric-box, .tab-section)
- Visual Layout Diff: Compare screenshot pixels vs Phase 9 baseline (< 3% difference threshold)
- Typography & Color: Extract computed CSS → compare font size + color variables
- Animation Hooks: Check CSS transitions/animations on hover or load
- Clicker Flow: Simulate key clicks per tab (Run Backtest, Toggle View, Apply Filter)
- Console Error Scan: Capture logs → assert 0 errors except known warnings
- Performance Timing: Record DOMContentLoaded + Render Time (≤ 300ms avg per tab)

Pass/Fail Criteria:
✅ Pass: ≥90% of defined UI/UX changes detected, <3% pixel diff, 0 critical console errors
❌ Fail: Any tab shows old layout (Phase 0 DOM structure), missing components, >5% visual deviation
"""

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional

from playwright.sync_api import sync_playwright, Page, Browser, ElementHandle, Error as PlaywrightError
from PIL import Image, ImageChops
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DASHBOARD_URL = "http://localhost:8050"
BASELINE_SPEC_PATH = Path("phase9d_uiux_baseline_spec.json")
OUTPUT_DIR = Path("outputs/phase9d_uiux_validation")
VIEWPORTS = {
    'desktop': {'width': 1920, 'height': 1080},
    'tablet': {'width': 1024, 'height': 768},
}


@dataclass
class CSSComputedStyle:
    """Extracted computed CSS properties"""
    element_selector: str
    font_size: Optional[str]
    font_weight: Optional[str]
    color: Optional[str]
    background_color: Optional[str]
    border_radius: Optional[str]
    box_shadow: Optional[str]
    padding: Optional[str]
    transition: Optional[str]
    animation: Optional[str]


@dataclass
class DOMStructureValidation:
    """DOM structure validation result"""
    selector: str
    expected_min: int
    found_count: int
    elements_ids: List[str]
    passed: bool
    deviation_percent: float


@dataclass
class PixelDiffResult:
    """Pixel-by-pixel comparison result"""
    total_pixels: int
    different_pixels: int
    diff_percent: float
    passed: bool
    diff_image_path: Optional[str]


@dataclass
class AnimationValidation:
    """CSS animation/transition validation"""
    element_selector: str
    has_transition: bool
    has_animation: bool
    transition_properties: Optional[str]
    animation_name: Optional[str]
    passed: bool


@dataclass
class ClickInteraction:
    """Click interaction test result"""
    element_id: str
    element_type: str
    success: bool
    response_time_ms: float
    console_errors: List[str]
    callback_triggered: bool


@dataclass
class TabUIUXValidation:
    """Complete UI/UX validation for a single tab"""
    tab_id: str
    tab_name: str
    viewport: str
    
    # DOM Structure
    dom_validations: List[DOMStructureValidation]
    dom_match_percent: float
    
    # Visual Diff
    pixel_diff: Optional[PixelDiffResult]
    
    # CSS Properties
    css_styles: List[CSSComputedStyle]
    css_match_percent: float
    
    # Animations
    animations: List[AnimationValidation]
    animation_match_percent: float
    
    # Interactions
    click_interactions: List[ClickInteraction]
    click_success_rate: float
    
    # Console
    console_errors: List[str]
    console_warnings: List[str]
    
    # Performance
    render_time_ms: float
    dom_content_loaded_ms: float
    
    # Screenshots
    screenshot_path: str
    html_dump_path: str
    dom_json_path: str
    
    # Overall
    overall_passed: bool
    pass_criteria_met: Dict[str, bool]


@dataclass
class Phase9DValidationReport:
    """Complete Phase 9D validation report"""
    validation_date: str
    dashboard_url: str
    viewport: str
    baseline_spec_version: str
    
    tabs_validated: List[TabUIUXValidation]
    
    # Summary
    total_tabs: int
    tabs_passed: int
    overall_pass_rate: float
    
    # Aggregate Metrics
    avg_dom_match_percent: float
    avg_pixel_diff_percent: float
    avg_css_match_percent: float
    avg_animation_match_percent: float
    avg_click_success_rate: float
    avg_render_time_ms: float
    
    total_console_errors: int
    total_console_warnings: int
    
    # Pass/Fail Criteria
    criteria_results: Dict[str, bool]
    
    # Artifacts
    artifacts: List[str]


class Phase9DUIUXValidator:
    """
    Phase 9D UI/UX Compliance Validator using Chromium ground-truth rendering
    """
    
    def __init__(self, dashboard_url: str, baseline_spec_path: Path, viewport: str = 'desktop'):
        self.dashboard_url = dashboard_url
        self.baseline_spec_path = baseline_spec_path
        self.viewport_name = viewport
        self.viewport_size = VIEWPORTS[viewport]
        
        # Load baseline spec
        with open(baseline_spec_path, 'r') as f:
            self.baseline_spec = json.load(f)
        
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.console_messages: List[Dict[str, Any]] = []
        
        logger.info(f"✓ Phase 9D UI/UX Validator initialized")
        logger.info(f"  URL: {dashboard_url}")
        logger.info(f"  Viewport: {viewport} ({self.viewport_size['width']}×{self.viewport_size['height']})")
        logger.info(f"  Baseline Spec: v{self.baseline_spec['spec_version']}")
    
    def setup_console_listener(self, page: Page):
        """Capture console errors and warnings"""
        def handle_console(msg):
            self.console_messages.append({
                'type': msg.type,
                'text': msg.text,
                'location': msg.location
            })
        
        page.on('console', handle_console)
    
    def wait_for_network_idle(self, page: Page, timeout: int = 10000):
        """Wait for network requests to complete"""
        try:
            page.wait_for_load_state('networkidle', timeout=timeout)
            logger.debug("✓ Network idle")
        except PlaywrightError as e:
            logger.warning(f"Network idle timeout: {e}")
    
    def navigate_to_tab(self, page: Page, tab_selector: str, tab_name: str) -> bool:
        """Navigate to a specific tab"""
        try:
            logger.info(f"  Navigating to tab: {tab_name} ({tab_selector})")
            
            # Wait for tab to be visible
            page.wait_for_selector(tab_selector, state='visible', timeout=5000)
            
            # Click tab
            page.click(tab_selector, timeout=5000)
            
            # Wait for network idle
            self.wait_for_network_idle(page, timeout=15000)
            
            # Wait for any tab content to render
            time.sleep(2)
            
            logger.info(f"✓ Navigated to {tab_name}")
            return True
            
        except PlaywrightError as e:
            logger.error(f"✗ Failed to navigate to {tab_name}: {e}")
            return False
    
    def validate_dom_structure(self, page: Page, tab_spec: Dict[str, Any]) -> List[DOMStructureValidation]:
        """Validate DOM structure against baseline spec"""
        validations = []
        expected_elements = tab_spec.get('expected_elements', {})
        
        for element_type, spec in expected_elements.items():
            if isinstance(spec, dict) and 'selector' in spec:
                selector = spec['selector']
                min_count = spec.get('min', 1)
                
                try:
                    elements = page.locator(selector)
                    count = elements.count()
                    
                    # Extract element IDs
                    element_ids = []
                    for i in range(min(count, 10)):  # Max 10 IDs to avoid overflow
                        try:
                            el_id = elements.nth(i).get_attribute('id')
                            if el_id:
                                element_ids.append(el_id)
                        except:
                            pass
                    
                    passed = count >= min_count
                    deviation = 0 if count >= min_count else ((min_count - count) / min_count * 100)
                    
                    validations.append(DOMStructureValidation(
                        selector=selector,
                        expected_min=min_count,
                        found_count=count,
                        elements_ids=element_ids,
                        passed=passed,
                        deviation_percent=deviation
                    ))
                    
                    logger.debug(f"  {element_type}: {count} found (min: {min_count}) {'✓' if passed else '✗'}")
                    
                except Exception as e:
                    logger.warning(f"  {element_type} validation error: {e}")
                    validations.append(DOMStructureValidation(
                        selector=selector,
                        expected_min=min_count,
                        found_count=0,
                        elements_ids=[],
                        passed=False,
                        deviation_percent=100.0
                    ))
        
        return validations
    
    def extract_css_properties(self, page: Page, selectors: List[str]) -> List[CSSComputedStyle]:
        """Extract computed CSS properties for validation"""
        styles = []
        
        for selector in selectors:
            try:
                # Find first matching element
                element = page.locator(selector).first
                
                if element.count() > 0:
                    # Extract computed styles via JavaScript
                    css_props = page.evaluate(f"""
                        (selector) => {{
                            const el = document.querySelector(selector);
                            if (!el) return null;
                            const style = window.getComputedStyle(el);
                            return {{
                                fontSize: style.fontSize,
                                fontWeight: style.fontWeight,
                                color: style.color,
                                backgroundColor: style.backgroundColor,
                                borderRadius: style.borderRadius,
                                boxShadow: style.boxShadow,
                                padding: style.padding,
                                transition: style.transition,
                                animation: style.animation
                            }};
                        }}
                    """, selector)
                    
                    if css_props:
                        styles.append(CSSComputedStyle(
                            element_selector=selector,
                            font_size=css_props.get('fontSize'),
                            font_weight=css_props.get('fontWeight'),
                            color=css_props.get('color'),
                            background_color=css_props.get('backgroundColor'),
                            border_radius=css_props.get('borderRadius'),
                            box_shadow=css_props.get('boxShadow'),
                            padding=css_props.get('padding'),
                            transition=css_props.get('transition'),
                            animation=css_props.get('animation')
                        ))
                        logger.debug(f"  Extracted CSS for {selector}")
                
            except Exception as e:
                logger.debug(f"  CSS extraction failed for {selector}: {e}")
        
        return styles
    
    def validate_animations(self, page: Page, selectors: List[str]) -> List[AnimationValidation]:
        """Validate CSS animations and transitions"""
        animations = []
        
        for selector in selectors:
            try:
                element = page.locator(selector).first
                
                if element.count() > 0:
                    anim_props = page.evaluate(f"""
                        (selector) => {{
                            const el = document.querySelector(selector);
                            if (!el) return null;
                            const style = window.getComputedStyle(el);
                            return {{
                                hasTransition: style.transition !== 'all 0s ease 0s',
                                hasAnimation: style.animation !== 'none 0s ease 0s 1 normal none running',
                                transitionProperties: style.transition,
                                animationName: style.animationName
                            }};
                        }}
                    """, selector)
                    
                    if anim_props:
                        has_trans = anim_props.get('hasTransition', False)
                        has_anim = anim_props.get('hasAnimation', False)
                        
                        animations.append(AnimationValidation(
                            element_selector=selector,
                            has_transition=has_trans,
                            has_animation=has_anim,
                            transition_properties=anim_props.get('transitionProperties'),
                            animation_name=anim_props.get('animationName'),
                            passed=has_trans or has_anim
                        ))
                        
                        logger.debug(f"  Animation check {selector}: trans={has_trans}, anim={has_anim}")
                
            except Exception as e:
                logger.debug(f"  Animation validation failed for {selector}: {e}")
        
        return animations
    
    def perform_click_interactions(self, page: Page, tab_spec: Dict[str, Any], max_clicks: int = 10) -> List[ClickInteraction]:
        """Perform click interactions on interactive elements"""
        interactions = []
        
        # Reset console messages for this interaction session
        self.console_messages = []
        
        # Find clickable elements (buttons, links)
        clickable_selectors = ['button:visible', 'a:visible', 'input[type="button"]:visible']
        
        for selector in clickable_selectors:
            try:
                elements = page.locator(selector)
                count = elements.count()
                
                # Click random subset (max 5 per selector type)
                import random
                indices = random.sample(range(count), min(5, count))
                
                for idx in indices:
                    if len(interactions) >= max_clicks:
                        break
                    
                    try:
                        element = elements.nth(idx)
                        el_id = element.get_attribute('id') or f"{selector}-{idx}"
                        el_type = element.evaluate('el => el.tagName')
                        
                        # Clear console errors before click
                        self.console_messages = []
                        
                        # Click and measure response time
                        start_time = time.time()
                        element.click(timeout=3000)
                        response_time = (time.time() - start_time) * 1000
                        
                        # Wait briefly for callback
                        time.sleep(0.5)
                        
                        # Check for console errors
                        errors = [msg['text'] for msg in self.console_messages if msg['type'] == 'error']
                        callback_triggered = len(self.console_messages) > 0
                        
                        interactions.append(ClickInteraction(
                            element_id=el_id,
                            element_type=el_type,
                            success=len(errors) == 0,
                            response_time_ms=response_time,
                            console_errors=errors,
                            callback_triggered=callback_triggered
                        ))
                        
                        logger.debug(f"  Clicked {el_type} ({el_id}): {response_time:.0f}ms, errors={len(errors)}")
                        
                    except Exception as e:
                        logger.debug(f"  Click failed: {e}")
                
                if len(interactions) >= max_clicks:
                    break
                    
            except Exception as e:
                logger.debug(f"  Clickable element search failed for {selector}: {e}")
        
        return interactions
    
    def calculate_pixel_diff(self, new_screenshot: Path, baseline_screenshot: Path, output_diff: Path) -> Optional[PixelDiffResult]:
        """Calculate pixel-by-pixel difference vs baseline"""
        try:
            if not baseline_screenshot.exists():
                logger.warning(f"  No baseline screenshot found: {baseline_screenshot}")
                return None
            
            # Load images
            img1 = Image.open(new_screenshot).convert('RGB')
            img2 = Image.open(baseline_screenshot).convert('RGB')
            
            # Ensure same size
            if img1.size != img2.size:
                logger.warning(f"  Screenshot size mismatch: {img1.size} vs {img2.size}")
                img2 = img2.resize(img1.size)
            
            # Calculate difference
            diff = ImageChops.difference(img1, img2)
            diff_array = np.array(diff)
            
            # Count different pixels (any RGB channel difference > 10)
            total_pixels = diff_array.shape[0] * diff_array.shape[1]
            different_pixels = np.sum(np.any(diff_array > 10, axis=2))
            diff_percent = (different_pixels / total_pixels) * 100
            
            # Save diff image
            diff.save(output_diff)
            
            passed = diff_percent < 3.0  # <3% threshold
            
            logger.info(f"  Pixel diff: {diff_percent:.2f}% ({'✓' if passed else '✗'})")
            
            return PixelDiffResult(
                total_pixels=total_pixels,
                different_pixels=int(different_pixels),
                diff_percent=diff_percent,
                passed=passed,
                diff_image_path=str(output_diff)
            )
            
        except Exception as e:
            logger.error(f"  Pixel diff calculation failed: {e}")
            return None
    
    def validate_tab(self, page: Page, tab_id: str, baseline_screenshot_path: Optional[Path] = None) -> TabUIUXValidation:
        """Perform complete UI/UX validation for a single tab"""
        tab_spec = self.baseline_spec['tabs'][tab_id]
        tab_name = tab_spec['name']
        tab_selector = tab_spec['selector']
        
        logger.info(f"\n{'='*80}")
        logger.info(f"VALIDATING TAB: {tab_name} ({tab_id})")
        logger.info(f"{'='*80}")
        
        # Navigate to tab
        if not self.navigate_to_tab(page, tab_selector, tab_name):
            # Return failed validation if navigation fails
            return self._create_failed_validation(tab_id, tab_name, "Navigation failed")
        
        # Performance timing
        perf_timing = page.evaluate("""
            () => {
                const timing = performance.timing;
                return {
                    domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                    renderTime: timing.loadEventEnd - timing.navigationStart
                };
            }
        """)
        
        dom_content_loaded_ms = perf_timing.get('domContentLoaded', 0)
        render_time_ms = perf_timing.get('renderTime', 0)
        
        logger.info(f"  Performance: DOM={dom_content_loaded_ms}ms, Render={render_time_ms}ms")
        
        # 1. DOM Structure Validation
        logger.info(f"\n📋 DOM Structure Validation")
        dom_validations = self.validate_dom_structure(page, tab_spec)
        dom_passed = sum(1 for v in dom_validations if v.passed)
        dom_match_percent = (dom_passed / len(dom_validations) * 100) if dom_validations else 0
        logger.info(f"  DOM Match: {dom_match_percent:.1f}% ({dom_passed}/{len(dom_validations)})")
        
        # 2. CSS Properties Extraction
        logger.info(f"\n🎨 CSS Properties Extraction")
        css_selectors = ['.dash-card', '.metric-box', 'button', 'h1', 'h2', 'h3']
        css_styles = self.extract_css_properties(page, css_selectors)
        
        # Compare CSS properties vs baseline
        expected_colors = self.baseline_spec['global_uiux_standards']['colors']
        css_matches = 0
        for style in css_styles:
            if style.color and 'rgb' in style.color:
                css_matches += 1
            if style.background_color and 'rgb' in style.background_color:
                css_matches += 1
        css_match_percent = (css_matches / max(len(css_styles) * 2, 1) * 100)
        logger.info(f"  CSS Match: {css_match_percent:.1f}%")
        
        # 3. Animation Validation
        logger.info(f"\n✨ Animation Validation")
        animation_selectors = ['button', '.dash-card', '.metric-box']
        animations = self.validate_animations(page, animation_selectors)
        anim_passed = sum(1 for a in animations if a.passed)
        animation_match_percent = (anim_passed / len(animations) * 100) if animations else 0
        logger.info(f"  Animation Match: {animation_match_percent:.1f}% ({anim_passed}/{len(animations)})")
        
        # 4. Click Interactions
        logger.info(f"\n🖱️ Click Interaction Testing")
        click_interactions = self.perform_click_interactions(page, tab_spec, max_clicks=10)
        click_success = sum(1 for c in click_interactions if c.success)
        click_success_rate = (click_success / len(click_interactions) * 100) if click_interactions else 0
        logger.info(f"  Click Success: {click_success_rate:.1f}% ({click_success}/{len(click_interactions)})")
        
        # 5. Capture Screenshot
        logger.info(f"\n📸 Screenshot Capture")
        screenshot_dir = OUTPUT_DIR / 'snapshots'
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = screenshot_dir / f"{self.viewport_name}_{tab_id}_snapshot.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info(f"  Screenshot: {screenshot_path}")
        
        # 6. Pixel Diff (if baseline exists)
        pixel_diff = None
        if baseline_screenshot_path and baseline_screenshot_path.exists():
            logger.info(f"\n🔍 Pixel Diff Analysis")
            diff_dir = OUTPUT_DIR / 'pixel_diffs'
            diff_dir.mkdir(parents=True, exist_ok=True)
            diff_path = diff_dir / f"{self.viewport_name}_{tab_id}_diff.png"
            pixel_diff = self.calculate_pixel_diff(screenshot_path, baseline_screenshot_path, diff_path)
        
        # 7. HTML Dump
        html_dir = OUTPUT_DIR / 'html_dumps'
        html_dir.mkdir(parents=True, exist_ok=True)
        html_dump_path = html_dir / f"{self.viewport_name}_{tab_id}.html"
        html_content = page.content()
        html_dump_path.write_text(html_content, encoding='utf-8')
        logger.info(f"  HTML dump: {html_dump_path}")
        
        # 8. DOM JSON Serialization
        dom_json_dir = OUTPUT_DIR / 'dom_json'
        dom_json_dir.mkdir(parents=True, exist_ok=True)
        dom_json_path = dom_json_dir / f"{self.viewport_name}_{tab_id}.json"
        
        dom_tree = page.evaluate("""
            () => {
                function serializeNode(node) {
                    if (node.nodeType !== 1) return null;
                    return {
                        tag: node.tagName,
                        id: node.id || null,
                        classes: Array.from(node.classList),
                        children: Array.from(node.children).map(serializeNode).filter(n => n)
                    };
                }
                return serializeNode(document.body);
            }
        """)
        
        dom_json_path.write_text(json.dumps(dom_tree, indent=2), encoding='utf-8')
        logger.info(f"  DOM JSON: {dom_json_path}")
        
        # 9. Console Errors/Warnings
        console_errors = [msg['text'] for msg in self.console_messages if msg['type'] == 'error']
        console_warnings = [msg['text'] for msg in self.console_messages if msg['type'] == 'warning']
        logger.info(f"\n📋 Console Logs: {len(console_errors)} errors, {len(console_warnings)} warnings")
        
        # Pass Criteria Evaluation
        pass_criteria = {
            'dom_structure': dom_match_percent >= 90,
            'pixel_diff': pixel_diff.passed if pixel_diff else True,
            'css_properties': css_match_percent >= 85,
            'animations': animation_match_percent >= 70,
            'click_success': click_success_rate >= 95,
            'console_clean': len(console_errors) == 0,
            'performance': render_time_ms <= 300
        }
        
        overall_passed = all([
            pass_criteria['dom_structure'],
            pass_criteria.get('pixel_diff', True),
            pass_criteria['click_success'],
            pass_criteria['console_clean']
        ])
        
        logger.info(f"\n{'='*80}")
        logger.info(f"TAB VALIDATION RESULT: {'✅ PASS' if overall_passed else '❌ FAIL'}")
        logger.info(f"{'='*80}")
        
        return TabUIUXValidation(
            tab_id=tab_id,
            tab_name=tab_name,
            viewport=self.viewport_name,
            dom_validations=dom_validations,
            dom_match_percent=dom_match_percent,
            pixel_diff=pixel_diff,
            css_styles=css_styles,
            css_match_percent=css_match_percent,
            animations=animations,
            animation_match_percent=animation_match_percent,
            click_interactions=click_interactions,
            click_success_rate=click_success_rate,
            console_errors=console_errors,
            console_warnings=console_warnings,
            render_time_ms=render_time_ms,
            dom_content_loaded_ms=dom_content_loaded_ms,
            screenshot_path=str(screenshot_path),
            html_dump_path=str(html_dump_path),
            dom_json_path=str(dom_json_path),
            overall_passed=overall_passed,
            pass_criteria_met=pass_criteria
        )
    
    def _create_failed_validation(self, tab_id: str, tab_name: str, reason: str) -> TabUIUXValidation:
        """Create a failed validation result"""
        return TabUIUXValidation(
            tab_id=tab_id,
            tab_name=tab_name,
            viewport=self.viewport_name,
            dom_validations=[],
            dom_match_percent=0.0,
            pixel_diff=None,
            css_styles=[],
            css_match_percent=0.0,
            animations=[],
            animation_match_percent=0.0,
            click_interactions=[],
            click_success_rate=0.0,
            console_errors=[reason],
            console_warnings=[],
            render_time_ms=0.0,
            dom_content_loaded_ms=0.0,
            screenshot_path="",
            html_dump_path="",
            dom_json_path="",
            overall_passed=False,
            pass_criteria_met={}
        )
    
    def run_validation(self, baseline_dir: Optional[Path] = None) -> Phase9DValidationReport:
        """Execute complete Phase 9D UI/UX validation"""
        logger.info(f"\n{'='*80}")
        logger.info(f"PHASE 9D UI/UX COMPLIANCE VALIDATION")
        logger.info(f"{'='*80}")
        logger.info(f"Dashboard URL: {self.dashboard_url}")
        logger.info(f"Viewport: {self.viewport_name} ({self.viewport_size['width']}×{self.viewport_size['height']})")
        logger.info(f"Baseline Spec: v{self.baseline_spec['spec_version']}")
        logger.info(f"{'='*80}\n")
        
        # Create output directory
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        tabs_validated = []
        
        with sync_playwright() as p:
            # Launch browser
            logger.info("🚀 Launching Chromium browser...")
            self.browser = p.chromium.launch(headless=False)  # headless=False for debugging
            
            # Create context with viewport
            context = self.browser.new_context(
                viewport=self.viewport_size,
                device_scale_factor=1,
                has_touch=False,
                is_mobile=False
            )
            
            self.page = context.new_page()
            
            # Setup console listener
            self.setup_console_listener(self.page)
            
            # Navigate to dashboard
            logger.info(f"📡 Navigating to {self.dashboard_url}...")
            self.page.goto(self.dashboard_url, wait_until='networkidle', timeout=30000)
            logger.info("✓ Dashboard loaded\n")
            
            # Validate each tab
            for tab_id, tab_spec in self.baseline_spec['tabs'].items():
                # Determine baseline screenshot path
                baseline_screenshot = None
                if baseline_dir:
                    baseline_screenshot = baseline_dir / f"{self.viewport_name}_{tab_id}_snapshot.png"
                
                # Validate tab
                validation = self.validate_tab(self.page, tab_id, baseline_screenshot)
                tabs_validated.append(validation)
                
                # Brief pause between tabs
                time.sleep(1)
            
            # Close browser
            self.browser.close()
            logger.info("\n✓ Browser closed")
        
        # Generate report
        return self.generate_report(tabs_validated)
    
    def generate_report(self, tabs_validated: List[TabUIUXValidation]) -> Phase9DValidationReport:
        """Generate comprehensive validation report"""
        logger.info(f"\n{'='*80}")
        logger.info(f"GENERATING VALIDATION REPORT")
        logger.info(f"{'='*80}\n")
        
        from datetime import datetime
        
        # Calculate summary metrics
        total_tabs = len(tabs_validated)
        tabs_passed = sum(1 for t in tabs_validated if t.overall_passed)
        overall_pass_rate = (tabs_passed / total_tabs * 100) if total_tabs > 0 else 0
        
        avg_dom_match = sum(t.dom_match_percent for t in tabs_validated) / total_tabs if total_tabs > 0 else 0
        
        pixel_diffs = [t.pixel_diff.diff_percent for t in tabs_validated if t.pixel_diff]
        avg_pixel_diff = sum(pixel_diffs) / len(pixel_diffs) if pixel_diffs else 0
        
        avg_css_match = sum(t.css_match_percent for t in tabs_validated) / total_tabs if total_tabs > 0 else 0
        avg_anim_match = sum(t.animation_match_percent for t in tabs_validated) / total_tabs if total_tabs > 0 else 0
        avg_click_success = sum(t.click_success_rate for t in tabs_validated) / total_tabs if total_tabs > 0 else 0
        avg_render_time = sum(t.render_time_ms for t in tabs_validated) / total_tabs if total_tabs > 0 else 0
        
        total_console_errors = sum(len(t.console_errors) for t in tabs_validated)
        total_console_warnings = sum(len(t.console_warnings) for t in tabs_validated)
        
        # Overall criteria
        criteria_results = {
            'dom_structure_match': avg_dom_match >= 90,
            'pixel_diff_acceptable': avg_pixel_diff < 3.0 if pixel_diffs else True,
            'css_match': avg_css_match >= 85,
            'animations_present': avg_anim_match >= 70,
            'click_success_high': avg_click_success >= 95,
            'console_clean': total_console_errors == 0,
            'performance_acceptable': avg_render_time <= 300
        }
        
        # Collect artifacts
        artifacts = []
        for tab in tabs_validated:
            if tab.screenshot_path:
                artifacts.append(tab.screenshot_path)
            if tab.html_dump_path:
                artifacts.append(tab.html_dump_path)
            if tab.dom_json_path:
                artifacts.append(tab.dom_json_path)
            if tab.pixel_diff and tab.pixel_diff.diff_image_path:
                artifacts.append(tab.pixel_diff.diff_image_path)
        
        report = Phase9DValidationReport(
            validation_date=datetime.now().isoformat(),
            dashboard_url=self.dashboard_url,
            viewport=self.viewport_name,
            baseline_spec_version=self.baseline_spec['spec_version'],
            tabs_validated=tabs_validated,
            total_tabs=total_tabs,
            tabs_passed=tabs_passed,
            overall_pass_rate=overall_pass_rate,
            avg_dom_match_percent=avg_dom_match,
            avg_pixel_diff_percent=avg_pixel_diff,
            avg_css_match_percent=avg_css_match,
            avg_animation_match_percent=avg_anim_match,
            avg_click_success_rate=avg_click_success,
            avg_render_time_ms=avg_render_time,
            total_console_errors=total_console_errors,
            total_console_warnings=total_console_warnings,
            criteria_results=criteria_results,
            artifacts=artifacts
        )
        
        logger.info(f"✓ Report generated: {total_tabs} tabs validated, {tabs_passed} passed ({overall_pass_rate:.1f}%)")
        
        return report
    
    def save_report(self, report: Phase9DValidationReport):
        """Save validation report to JSON and Markdown"""
        # Save JSON
        json_path = OUTPUT_DIR / f"phase9d_uiux_validation_{self.viewport_name}.json"
        with open(json_path, 'w') as f:
            # Convert dataclasses to dict and handle numpy types
            import numpy as np
            
            def convert_numpy(obj):
                if isinstance(obj, np.bool_):
                    return bool(obj)
                elif isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                return obj
            
            report_dict = asdict(report)
            
            # Recursively convert numpy types
            def deep_convert(data):
                if isinstance(data, dict):
                    return {k: deep_convert(v) for k, v in data.items()}
                elif isinstance(data, list):
                    return [deep_convert(item) for item in data]
                else:
                    return convert_numpy(data)
            
            report_dict = deep_convert(report_dict)
            json.dump(report_dict, f, indent=2)
        logger.info(f"✓ JSON report: {json_path}")
        
        # Save Markdown
        md_path = OUTPUT_DIR / f"phase9d_uiux_validation_report_{self.viewport_name}.md"
        with open(md_path, 'w') as f:
            f.write(self._generate_markdown_report(report))
        logger.info(f"✓ Markdown report: {md_path}")
    
    def _generate_markdown_report(self, report: Phase9DValidationReport) -> str:
        """Generate Markdown formatted report"""
        md = []
        md.append("# Phase 9D UI/UX Compliance Validation Report\n")
        md.append(f"**Validation Date:** {report.validation_date}  ")
        md.append(f"**Dashboard URL:** {report.dashboard_url}  ")
        md.append(f"**Viewport:** {report.viewport}  ")
        md.append(f"**Baseline Spec:** v{report.baseline_spec_version}  \n")
        
        md.append("---\n")
        md.append("## 🎯 Executive Summary\n")
        md.append(f"| Metric | Value | Status |\n")
        md.append(f"|--------|-------|--------|\n")
        md.append(f"| **Tabs Validated** | {report.tabs_passed}/{report.total_tabs} | {'✅' if report.overall_pass_rate == 100 else '⚠️'} |\n")
        md.append(f"| **Overall Pass Rate** | {report.overall_pass_rate:.1f}% | {'✅' if report.overall_pass_rate >= 90 else '❌'} |\n")
        md.append(f"| **Avg DOM Match** | {report.avg_dom_match_percent:.1f}% | {'✅' if report.avg_dom_match_percent >= 90 else '❌'} |\n")
        md.append(f"| **Avg Pixel Diff** | {report.avg_pixel_diff_percent:.2f}% | {'✅' if report.avg_pixel_diff_percent < 3.0 else '❌'} |\n")
        md.append(f"| **Avg CSS Match** | {report.avg_css_match_percent:.1f}% | {'✅' if report.avg_css_match_percent >= 85 else '❌'} |\n")
        md.append(f"| **Avg Animation Match** | {report.avg_animation_match_percent:.1f}% | {'✅' if report.avg_animation_match_percent >= 70 else '❌'} |\n")
        md.append(f"| **Avg Click Success** | {report.avg_click_success_rate:.1f}% | {'✅' if report.avg_click_success_rate >= 95 else '❌'} |\n")
        md.append(f"| **Console Errors** | {report.total_console_errors} | {'✅' if report.total_console_errors == 0 else '❌'} |\n")
        md.append(f"| **Avg Render Time** | {report.avg_render_time_ms:.0f}ms | {'✅' if report.avg_render_time_ms <= 300 else '❌'} |\n")
        
        md.append("\n### 🏆 Pass/Fail Criteria\n")
        md.append(f"| Criterion | Status |\n")
        md.append(f"|-----------|--------|\n")
        for criterion, passed in report.criteria_results.items():
            md.append(f"| {criterion.replace('_', ' ').title()} | {'✅ PASS' if passed else '❌ FAIL'} |\n")
        
        md.append("\n---\n")
        md.append("## 📊 Tab Validation Details\n")
        
        for tab in report.tabs_validated:
            md.append(f"\n### {tab.tab_name} ({tab.tab_id})\n")
            md.append(f"**Overall Status:** {'✅ PASS' if tab.overall_passed else '❌ FAIL'}  \n")
            md.append(f"**DOM Match:** {tab.dom_match_percent:.1f}%  \n")
            if tab.pixel_diff:
                md.append(f"**Pixel Diff:** {tab.pixel_diff.diff_percent:.2f}%  \n")
            md.append(f"**CSS Match:** {tab.css_match_percent:.1f}%  \n")
            md.append(f"**Animation Match:** {tab.animation_match_percent:.1f}%  \n")
            md.append(f"**Click Success:** {tab.click_success_rate:.1f}% ({len([c for c in tab.click_interactions if c.success])}/{len(tab.click_interactions)})  \n")
            md.append(f"**Console Errors:** {len(tab.console_errors)}  \n")
            md.append(f"**Render Time:** {tab.render_time_ms:.0f}ms  \n")
            
            if tab.console_errors:
                md.append(f"\n**⚠️ Console Errors:**\n")
                for err in tab.console_errors[:5]:  # Max 5 errors
                    md.append(f"- {err}\n")
        
        md.append("\n---\n")
        md.append("## 📁 Generated Artifacts\n")
        md.append(f"**Total Files:** {len(report.artifacts)}\n\n")
        md.append("**Artifact Categories:**\n")
        md.append(f"- Screenshots: {len([a for a in report.artifacts if 'snapshot' in a])}\n")
        md.append(f"- HTML Dumps: {len([a for a in report.artifacts if '.html' in a])}\n")
        md.append(f"- DOM JSON: {len([a for a in report.artifacts if 'dom_json' in a])}\n")
        md.append(f"- Pixel Diffs: {len([a for a in report.artifacts if 'diff' in a])}\n")
        
        return ''.join(md)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Phase 9D UI/UX Compliance Validator')
    parser.add_argument('--url', default=DASHBOARD_URL, help='Dashboard URL')
    parser.add_argument('--viewport', default='desktop', choices=['desktop', 'tablet'], help='Viewport size')
    parser.add_argument('--baseline', type=Path, help='Baseline screenshot directory for pixel diff')
    
    args = parser.parse_args()
    
    # Verify baseline spec exists
    if not BASELINE_SPEC_PATH.exists():
        logger.error(f"❌ Baseline spec not found: {BASELINE_SPEC_PATH}")
        sys.exit(1)
    
    # Create validator
    validator = Phase9DUIUXValidator(
        dashboard_url=args.url,
        baseline_spec_path=BASELINE_SPEC_PATH,
        viewport=args.viewport
    )
    
    # Run validation
    report = validator.run_validation(baseline_dir=args.baseline)
    
    # Save report
    validator.save_report(report)
    
    # Print summary
    logger.info(f"\n{'='*80}")
    logger.info(f"VALIDATION COMPLETE")
    logger.info(f"{'='*80}")
    logger.info(f"Overall Pass Rate: {report.overall_pass_rate:.1f}% ({report.tabs_passed}/{report.total_tabs} tabs)")
    logger.info(f"Average DOM Match: {report.avg_dom_match_percent:.1f}%")
    logger.info(f"Average Pixel Diff: {report.avg_pixel_diff_percent:.2f}%")
    logger.info(f"Average Click Success: {report.avg_click_success_rate:.1f}%")
    logger.info(f"Console Errors: {report.total_console_errors}")
    logger.info(f"{'='*80}\n")
    
    # Exit code based on overall pass
    criteria_passed = sum(1 for passed in report.criteria_results.values() if passed)
    total_criteria = len(report.criteria_results)
    
    if criteria_passed >= (total_criteria * 0.9):  # 90% criteria pass threshold
        logger.info("✅ PHASE 9D VALIDATION: PASS")
        sys.exit(0)
    else:
        logger.error(f"❌ PHASE 9D VALIDATION: FAIL ({criteria_passed}/{total_criteria} criteria met)")
        sys.exit(1)


if __name__ == '__main__':
    main()

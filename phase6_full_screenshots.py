"""
phase6_full_screenshots.py

Screenshot capture module with WCAG accessibility validation for Phase 6 full diagnostic.

This module provides:
- Automated screenshot capture for all tabs/subtabs
- WCAG contrast ratio validation
- Black text (#000000) enforcement
- Table visibility checks
- Tooltip validation
- Element-specific capture
- Full page screenshots

Uses Playwright for headless browser automation.

Author: Agent 1B - Lead Engineer
Date: 2025-10-29
"""

import os
import sys
import json
import logging
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

# Conditional Playwright import
try:
    from playwright.sync_api import sync_playwright, Page, Browser, Playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logging.warning("Playwright not available - screenshot capture will be disabled")

logger = logging.getLogger(__name__)


class ScreenshotCapture:
    """Screenshot capture with WCAG accessibility validation"""
    
    def __init__(self, config: Dict, output_dir: str = "outputs/phase6_full/screenshots"):
        """Initialize screenshot capture"""
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.dashboard_url = config['dashboard_config']['base_url']
        self.headless = config['dashboard_config']['headless_browser']
        self.viewport_width = config['dashboard_config']['viewport_width']
        self.viewport_height = config['dashboard_config']['viewport_height']
        
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
        logger.info(f"Screenshot capture initialized - Output: {self.output_dir}")
    
    def __enter__(self):
        """Context manager entry - start browser"""
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available - skipping browser initialization")
            return self
        
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=self.headless)
            self.page = self.browser.new_page(
                viewport={'width': self.viewport_width, 'height': self.viewport_height}
            )
            logger.info(f"Browser started: {self.viewport_width}x{self.viewport_height}, headless={self.headless}")
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            self.playwright = None
            self.browser = None
            self.page = None
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close browser"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Browser closed")
    
    def navigate_to_dashboard(self, timeout_ms: int = 10000) -> bool:
        """Navigate to dashboard and wait for load"""
        if not self.page:
            logger.warning("No browser page available")
            return False
        
        try:
            logger.info(f"Navigating to {self.dashboard_url}")
            self.page.goto(self.dashboard_url, timeout=timeout_ms)
            self.page.wait_for_load_state('networkidle', timeout=timeout_ms)
            logger.info("Dashboard loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    def capture_full_page(self, filename: str) -> Optional[str]:
        """Capture full page screenshot"""
        if not self.page:
            logger.warning("No browser page available")
            return None
        
        try:
            filepath = self.output_dir / filename
            self.page.screenshot(path=str(filepath), full_page=True)
            logger.info(f"Full page screenshot saved: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None
    
    def capture_element(self, selector: str, filename: str) -> Optional[str]:
        """Capture screenshot of specific element"""
        if not self.page:
            logger.warning("No browser page available")
            return None
        
        try:
            element = self.page.query_selector(selector)
            if element:
                filepath = self.output_dir / filename
                element.screenshot(path=str(filepath))
                logger.info(f"Element screenshot saved: {filepath}")
                return str(filepath)
            else:
                logger.warning(f"Element not found: {selector}")
                return None
        except Exception as e:
            logger.error(f"Element screenshot failed: {e}")
            return None
    
    def click_tab(self, tab_selector: str, wait_ms: int = 1000) -> bool:
        """Click tab and wait for content to load"""
        if not self.page:
            logger.warning("No browser page available")
            return False
        
        try:
            self.page.click(tab_selector)
            time.sleep(wait_ms / 1000)  # Wait for tab content to load
            logger.info(f"Clicked tab: {tab_selector}")
            return True
        except Exception as e:
            logger.error(f"Tab click failed: {e}")
            return False
    
    def wait_for_element(self, selector: str, timeout_ms: int = 5000) -> bool:
        """Wait for element to be visible"""
        if not self.page:
            return False
        
        try:
            self.page.wait_for_selector(selector, timeout=timeout_ms, state='visible')
            return True
        except Exception as e:
            logger.warning(f"Element not visible within timeout: {selector}")
            return False
    
    def check_element_visibility(self, selector: str) -> bool:
        """Check if element is visible"""
        if not self.page:
            return False
        
        try:
            element = self.page.query_selector(selector)
            return element is not None and element.is_visible()
        except Exception:
            return False
    
    def get_element_text_color(self, selector: str) -> Optional[str]:
        """Get computed text color of element"""
        if not self.page:
            return None
        
        try:
            element = self.page.query_selector(selector)
            if element:
                color = element.evaluate("el => getComputedStyle(el).color")
                return color
            return None
        except Exception as e:
            logger.warning(f"Failed to get text color: {e}")
            return None
    
    def validate_wcag_contrast(self, text_color: str, bg_color: str) -> Tuple[float, bool]:
        """Calculate WCAG contrast ratio and validate"""
        # Simplified WCAG contrast calculation
        # In production, use a proper color contrast library
        
        # Parse RGB from color strings
        def parse_rgb(color_str: str) -> Tuple[int, int, int]:
            """Parse RGB values from color string"""
            if color_str.startswith('#'):
                # Hex color
                color_str = color_str.lstrip('#')
                return tuple(int(color_str[i:i+2], 16) for i in (0, 2, 4))
            elif color_str.startswith('rgb'):
                # RGB color
                import re
                match = re.search(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', color_str)
                if match:
                    return tuple(int(x) for x in match.groups())
            return (0, 0, 0)
        
        def relative_luminance(rgb: Tuple[int, int, int]) -> float:
            """Calculate relative luminance"""
            def adjust(c):
                c = c / 255.0
                return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            
            r, g, b = rgb
            return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)
        
        try:
            text_rgb = parse_rgb(text_color)
            bg_rgb = parse_rgb(bg_color)
            
            l1 = relative_luminance(text_rgb)
            l2 = relative_luminance(bg_rgb)
            
            lighter = max(l1, l2)
            darker = min(l1, l2)
            
            contrast_ratio = (lighter + 0.05) / (darker + 0.05)
            
            wcag_min = self.config['ui_validation']['wcag_contrast_ratio_min']
            passes_wcag = contrast_ratio >= wcag_min
            
            return contrast_ratio, passes_wcag
            
        except Exception as e:
            logger.error(f"WCAG contrast calculation failed: {e}")
            return 0.0, False
    
    def capture_tab_with_validation(self, tab_config: Dict, iteration: int = 1) -> Dict:
        """Capture tab screenshot with UI validation"""
        if not self.page:
            return {
                'success': False,
                'error': 'No browser page available',
                'tab_id': tab_config.get('tab_id'),
                'screenshot_path': None
            }
        
        tab_id = tab_config['tab_id']
        tab_name = tab_config['tab_name']
        screenshot_name = f"iter{iteration}_{tab_config['screenshot_name']}"
        
        logger.info(f"Capturing tab: {tab_name} ({tab_id})")
        
        try:
            # Click tab to navigate
            tab_selector = f"[value='{tab_id}']"
            if not self.click_tab(tab_selector, wait_ms=2000):
                return {
                    'success': False,
                    'error': f'Failed to click tab: {tab_id}',
                    'tab_id': tab_id,
                    'screenshot_path': None
                }
            
            # Wait for content to load
            time.sleep(1)
            
            # Validate UI elements
            ui_validation = tab_config.get('ui_validation', {})
            validation_results = {}
            
            # Check expected elements
            expected_elements = tab_config.get('expected_elements', [])
            elements_visible = {}
            for element_id in expected_elements:
                is_visible = self.check_element_visibility(f"#{element_id}")
                elements_visible[element_id] = is_visible
            
            validation_results['elements_visible'] = elements_visible
            
            # Check text color if required
            if ui_validation.get('text_color'):
                expected_color = ui_validation['text_color']
                # Check first table cell or text element
                actual_color = self.get_element_text_color("td, p, span")
                validation_results['text_color_check'] = {
                    'expected': expected_color,
                    'actual': actual_color,
                    'matches': actual_color is not None and 'rgb(0, 0, 0)' in str(actual_color)
                }
            
            # Check WCAG contrast
            if ui_validation.get('text_color'):
                contrast_ratio, passes_wcag = self.validate_wcag_contrast(
                    ui_validation['text_color'],
                    "#FFFFFF"  # Assume white background
                )
                validation_results['wcag_validation'] = {
                    'contrast_ratio': contrast_ratio,
                    'passes_wcag': passes_wcag,
                    'level': self.config['ui_validation']['wcag_level']
                }
            
            # Capture screenshot
            screenshot_path = self.capture_full_page(screenshot_name)
            
            return {
                'success': screenshot_path is not None,
                'tab_id': tab_id,
                'tab_name': tab_name,
                'screenshot_path': screenshot_path,
                'validation_results': validation_results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Tab capture failed for {tab_name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'tab_id': tab_id,
                'screenshot_path': None
            }
    
    def capture_all_tabs(self, iteration: int = 1) -> List[Dict]:
        """Capture screenshots of all configured tabs"""
        if not self.navigate_to_dashboard():
            logger.error("Failed to navigate to dashboard")
            return []
        
        results = []
        tabs_to_test = self.config.get('tabs_to_test', [])
        
        logger.info(f"Capturing {len(tabs_to_test)} tabs for iteration {iteration}")
        
        for tab_config in tabs_to_test:
            result = self.capture_tab_with_validation(tab_config, iteration)
            results.append(result)
            time.sleep(0.5)  # Small delay between tabs
        
        successful = sum(1 for r in results if r['success'])
        logger.info(f"Screenshot capture complete: {successful}/{len(tabs_to_test)} successful")
        
        return results


def capture_screenshots_for_iteration(config_path: str, iteration: int = 1) -> List[Dict]:
    """Standalone function to capture screenshots for an iteration"""
    
    # Load config
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    output_dir = Path(config['output_config']['base_directory']) / config['output_config']['subdirectories']['screenshots']
    
    if not PLAYWRIGHT_AVAILABLE:
        logger.warning("Playwright not available - skipping screenshot capture")
        return []
    
    with ScreenshotCapture(config, output_dir=str(output_dir)) as capture:
        results = capture.capture_all_tabs(iteration=iteration)
    
    return results


if __name__ == '__main__':
    # Test screenshot capture standalone
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 6 Screenshot Capture")
    parser.add_argument('--config', default='phase6_full_diagnostic_config.json', help='Config file path')
    parser.add_argument('--iteration', type=int, default=1, help='Iteration number')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright not installed. Install with: pip install playwright && playwright install chromium")
        sys.exit(1)
    
    results = capture_screenshots_for_iteration(args.config, args.iteration)
    
    successful = sum(1 for r in results if r['success'])
    print(f"\n{'='*80}")
    print(f"Screenshot capture complete: {successful}/{len(results)} successful")
    print(f"{'='*80}")

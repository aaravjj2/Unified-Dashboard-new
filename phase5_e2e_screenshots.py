"""
Phase 5 E2E Screenshots Module

Automated screenshot capture for visual validation of dashboard components.
Supports headless and headed browser modes with configurable element waiting.
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

# Playwright for screenshot capture
try:
    from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logging.warning("Playwright not available - screenshots will be skipped")

logger = logging.getLogger(__name__)


class ScreenshotCapture:
    """Handles automated screenshot capture for E2E testing."""
    
    def __init__(self, config: Dict):
        """Initialize screenshot capture.
        
        Args:
            config: Test configuration dictionary
        """
        self.config = config
        self.dashboard_config = config.get('dashboard_config', {})
        self.output_config = config.get('output_config', {})
        self.visual_config = config.get('visual_validation', {})
        
        self.base_url = self.dashboard_config.get('base_url', 'http://127.0.0.1:8050')
        self.headless = self.dashboard_config.get('headless_browser', True)
        self.page_load_timeout = self.dashboard_config.get('page_load_timeout_seconds', 10) * 1000
        
        self.screenshots_dir = Path(self.output_config.get('screenshots_directory', './outputs/phase5_e2e/screenshots'))
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
    def __enter__(self):
        """Context manager entry - initialize browser."""
        if PLAYWRIGHT_AVAILABLE:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=self.headless)
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                device_scale_factor=1
            )
            self.page = self.context.new_page()
            self.page.set_default_timeout(self.page_load_timeout)
            logger.info(f"Browser launched (headless={self.headless})")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup browser."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Browser closed")
        
    def navigate_to_dashboard(self) -> bool:
        """Navigate to dashboard home page.
        
        Returns:
            True if navigation successful, False otherwise
        """
        if not self.page:
            logger.error("Browser not initialized")
            return False
            
        try:
            logger.info(f"Navigating to {self.base_url}")
            self.page.goto(self.base_url, wait_until='networkidle')
            time.sleep(2)  # Wait for Dash to initialize
            return True
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
            
    def capture_full_page(self, filename: str) -> Optional[str]:
        """Capture full page screenshot.
        
        Args:
            filename: Output filename
            
        Returns:
            Path to screenshot file, or None if failed
        """
        if not self.page:
            logger.error("Browser not initialized")
            return None
            
        try:
            filepath = self.screenshots_dir / filename
            self.page.screenshot(path=str(filepath), full_page=True)
            logger.info(f"Screenshot saved: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None
            
    def capture_element(self, selector: str, filename: str) -> Optional[str]:
        """Capture screenshot of specific element.
        
        Args:
            selector: CSS selector for element
            filename: Output filename
            
        Returns:
            Path to screenshot file, or None if failed
        """
        if not self.page:
            logger.error("Browser not initialized")
            return None
            
        try:
            element = self.page.wait_for_selector(selector, timeout=5000)
            if element:
                filepath = self.screenshots_dir / filename
                element.screenshot(path=str(filepath))
                logger.info(f"Element screenshot saved: {filepath}")
                return str(filepath)
            else:
                logger.warning(f"Element not found: {selector}")
                return None
        except Exception as e:
            logger.error(f"Element screenshot failed: {e}")
            return None
            
    def click_tab(self, tab_id: str) -> bool:
        """Click on a tab to activate it.
        
        Args:
            tab_id: Tab identifier
            
        Returns:
            True if click successful, False otherwise
        """
        if not self.page:
            return False
            
        try:
            # Try multiple selector strategies
            selectors = [
                f'[data-value="{tab_id}"]',
                f'#{tab_id}',
                f'.tab[data-tab="{tab_id}"]',
                f'button:has-text("{tab_id}")'
            ]
            
            for selector in selectors:
                try:
                    element = self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        element.click()
                        time.sleep(1)  # Wait for tab content to load
                        logger.info(f"Clicked tab: {tab_id}")
                        return True
                except:
                    continue
                    
            logger.warning(f"Tab not found: {tab_id}")
            return False
        except Exception as e:
            logger.error(f"Tab click failed: {e}")
            return False
            
    def wait_for_element(self, selector: str, timeout_ms: int = 5000) -> bool:
        """Wait for element to be visible.
        
        Args:
            selector: CSS selector
            timeout_ms: Timeout in milliseconds
            
        Returns:
            True if element found, False otherwise
        """
        if not self.page:
            return False
            
        try:
            self.page.wait_for_selector(selector, timeout=timeout_ms, state='visible')
            return True
        except:
            return False
            
    def check_element_visibility(self, selector: str) -> bool:
        """Check if element is visible.
        
        Args:
            selector: CSS selector
            
        Returns:
            True if visible, False otherwise
        """
        if not self.page:
            return False
            
        try:
            element = self.page.query_selector(selector)
            if element:
                return element.is_visible()
            return False
        except:
            return False
            
    def get_element_text_color(self, selector: str) -> Optional[str]:
        """Get text color of element.
        
        Args:
            selector: CSS selector
            
        Returns:
            Color as hex string, or None if failed
        """
        if not self.page:
            return None
            
        try:
            color = self.page.evaluate(f"""
                () => {{
                    const el = document.querySelector('{selector}');
                    if (el) {{
                        const style = window.getComputedStyle(el);
                        return style.color;
                    }}
                    return null;
                }}
            """)
            
            # Convert rgb(0, 0, 0) to #000000
            if color and color.startswith('rgb'):
                import re
                rgb = re.findall(r'\d+', color)
                if len(rgb) >= 3:
                    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))
            return color
        except Exception as e:
            logger.error(f"Failed to get text color: {e}")
            return None
            
    def capture_tab_screenshot(self, tab_config: Dict, iteration: int = 1) -> Dict:
        """Capture screenshot of a tab.
        
        Args:
            tab_config: Tab configuration dictionary
            iteration: Current test iteration
            
        Returns:
            Dictionary with screenshot results
        """
        result = {
            'tab_id': tab_config.get('tab_id'),
            'tab_name': tab_config.get('tab_name'),
            'iteration': iteration,
            'timestamp': datetime.utcnow().isoformat(),
            'screenshot_path': None,
            'elements_visible': {},
            'screenshot_success': False,
            'errors': []
        }
        
        if not PLAYWRIGHT_AVAILABLE or not self.page:
            result['errors'].append('Playwright not available or browser not initialized')
            return result
            
        try:
            # Click tab to activate
            tab_clicked = self.click_tab(tab_config['tab_id'])
            if not tab_clicked:
                result['errors'].append(f"Failed to click tab: {tab_config['tab_id']}")
                
            # Wait for tab content to load
            time.sleep(2)
            
            # Check expected elements
            for element_id in tab_config.get('expected_elements', []):
                is_visible = self.check_element_visibility(f'#{element_id}')
                result['elements_visible'][element_id] = is_visible
                if not is_visible:
                    logger.warning(f"Element not visible: {element_id}")
                    
            # Capture screenshot
            screenshot_name = tab_config.get('screenshot_name', f"{tab_config['tab_id']}.png")
            screenshot_name = f"iter{iteration}_{screenshot_name}"
            screenshot_path = self.capture_full_page(screenshot_name)
            
            if screenshot_path:
                result['screenshot_path'] = screenshot_path
                result['screenshot_success'] = True
            else:
                result['errors'].append('Screenshot capture failed')
                
        except Exception as e:
            result['errors'].append(str(e))
            logger.error(f"Tab screenshot failed: {e}")
            
        return result
        
    def capture_all_tabs(self, tabs_config: List[Dict], iteration: int = 1) -> List[Dict]:
        """Capture screenshots of all configured tabs.
        
        Args:
            tabs_config: List of tab configurations
            iteration: Current test iteration
            
        Returns:
            List of screenshot results
        """
        results = []
        
        if not self.navigate_to_dashboard():
            logger.error("Failed to navigate to dashboard")
            return results
            
        for tab_config in tabs_config:
            logger.info(f"Capturing tab: {tab_config.get('tab_name')}")
            result = self.capture_tab_screenshot(tab_config, iteration)
            results.append(result)
            
            # Handle subtabs if present
            if 'subtabs' in tab_config:
                for subtab_config in tab_config['subtabs']:
                    logger.info(f"  Capturing subtab: {subtab_config.get('subtab_name')}")
                    subtab_result = self.capture_tab_screenshot(subtab_config, iteration)
                    results.append(subtab_result)
                    
        return results


def capture_screenshots_for_iteration(config: Dict, iteration: int) -> List[Dict]:
    """Capture screenshots for a single test iteration.
    
    Args:
        config: Test configuration
        iteration: Current iteration number
        
    Returns:
        List of screenshot results
    """
    tabs_config = config.get('tabs_to_test', [])
    
    if not PLAYWRIGHT_AVAILABLE:
        logger.warning("Playwright not available - skipping screenshots")
        return []
        
    with ScreenshotCapture(config) as capture:
        return capture.capture_all_tabs(tabs_config, iteration)


# Standalone test
if __name__ == "__main__":
    import json
    
    logging.basicConfig(level=logging.INFO)
    
    # Load config
    with open('phase5_e2e_config.json', 'r') as f:
        config = json.load(f)
        
    # Capture screenshots
    results = capture_screenshots_for_iteration(config, iteration=1)
    
    print(f"\nCaptured {len(results)} screenshots")
    for result in results:
        status = "✅" if result['screenshot_success'] else "❌"
        print(f"{status} {result['tab_name']}: {result.get('screenshot_path', 'FAILED')}")

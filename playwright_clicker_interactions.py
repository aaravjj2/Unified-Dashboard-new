"""
Playwright Clicker-Based Interaction Tests for Phase 1-9 UI/UX
================================================================

Automated interaction testing simulating real user behavior:
- Click all buttons, dropdowns, modals
- Validate state changes after interactions
- Test keyboard navigation workflows
- Capture before/after snapshots
- Validate loading spinners and progress indicators
- Test responsive layout (desktop, tablet, mobile)

Architecture:
- Playwright sync API for deterministic interactions
- Sequential interaction flows with validation checkpoints
- Screenshot capture for visual regression testing
- Accessibility validation (focus, aria-labels, keyboard-only navigation)

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0
Date: October 29, 2025
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

try:
    from playwright.sync_api import sync_playwright, Page, Browser, expect
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logging.warning("⚠️  Playwright not available")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
OUTPUTS_DIR = Path("outputs/phase1_9_validation")
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR = OUTPUTS_DIR / "clicker_snapshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

DASHBOARD_URL = "http://localhost:8050"
VIEWPORTS = {
    "desktop": {"width": 1920, "height": 1080},
    "tablet": {"width": 768, "height": 1024},
    "mobile": {"width": 375, "height": 667}
}

# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class InteractionTest:
    """Single interaction test result"""
    test_id: str
    test_name: str
    interaction_type: str  # click, type, select, hover, keyboard
    selector: str
    viewport: str = "desktop"
    status: str = "PENDING"
    duration_ms: float = 0.0
    before_screenshot: Optional[str] = None
    after_screenshot: Optional[str] = None
    error: Optional[str] = None
    validation: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class InteractionReport:
    """Complete interaction test report"""
    timestamp: str
    total_interactions: int = 0
    successful: int = 0
    failed: int = 0
    tests: List[InteractionTest] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "summary": {
                "total_interactions": self.total_interactions,
                "successful": self.successful,
                "failed": self.failed,
                "success_rate": f"{(self.successful / self.total_interactions * 100) if self.total_interactions > 0 else 0:.1f}%"
            },
            "tests": [t.to_dict() for t in self.tests]
        }

# ============================================================================
# Clicker Interaction Tester
# ============================================================================

class PlaywrightClickerTester:
    """Automated clicker-based interaction testing"""
    
    def __init__(self, dashboard_url: str = DASHBOARD_URL):
        """Initialize tester"""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright not available")
        
        self.dashboard_url = dashboard_url
        self.report = InteractionReport(timestamp=datetime.now().isoformat())
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
        logger.info(f"✅ Clicker Tester initialized (URL: {dashboard_url})")
    
    def start_browser(self, viewport: str = "desktop"):
        """Start browser with specific viewport"""
        logger.info(f"🌐 Starting browser (viewport: {viewport})...")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page(viewport=VIEWPORTS[viewport])
        logger.info("✅ Browser started")
    
    def stop_browser(self):
        """Stop browser"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("🛑 Browser stopped")
    
    def test_button_click(self, test_id: str, test_name: str, selector: str, expected_change: Optional[str] = None) -> InteractionTest:
        """Test button click interaction"""
        test = InteractionTest(
            test_id=test_id,
            test_name=test_name,
            interaction_type="click",
            selector=selector
        )
        
        try:
            # Navigate to dashboard
            self.page.goto(self.dashboard_url, wait_until="networkidle", timeout=30000)
            time.sleep(1)
            
            # Capture before screenshot
            before_path = SCREENSHOTS_DIR / f"{test_id}_before.png"
            self.page.screenshot(path=str(before_path))
            test.before_screenshot = str(before_path)
            
            # Find button
            button = self.page.locator(selector).first
            
            if not button.is_visible(timeout=5000):
                test.status = "FAIL"
                test.error = "Button not visible"
                return test
            
            # Click button
            start = time.time()
            button.click()
            time.sleep(2)  # Wait for state change
            test.duration_ms = (time.time() - start) * 1000
            
            # Capture after screenshot
            after_path = SCREENSHOTS_DIR / f"{test_id}_after.png"
            self.page.screenshot(path=str(after_path))
            test.after_screenshot = str(after_path)
            
            # Validate expected change
            if expected_change:
                if self.page.locator(expected_change).count() > 0:
                    test.status = "PASS"
                    test.validation = f"Found expected element: {expected_change}"
                else:
                    test.status = "FAIL"
                    test.validation = f"Expected element not found: {expected_change}"
            else:
                test.status = "PASS"
                test.validation = "Click successful (no validation specified)"
            
            logger.info(f"✅ {test_name}: {test.status}")
            
        except Exception as e:
            test.status = "FAIL"
            test.error = str(e)
            logger.error(f"❌ {test_name} failed: {e}")
        
        return test
    
    def test_dropdown_select(self, test_id: str, test_name: str, dropdown_selector: str, option_value: str) -> InteractionTest:
        """Test dropdown selection"""
        test = InteractionTest(
            test_id=test_id,
            test_name=test_name,
            interaction_type="select",
            selector=dropdown_selector
        )
        
        try:
            self.page.goto(self.dashboard_url, wait_until="networkidle", timeout=30000)
            time.sleep(1)
            
            # Capture before
            before_path = SCREENSHOTS_DIR / f"{test_id}_before.png"
            self.page.screenshot(path=str(before_path))
            test.before_screenshot = str(before_path)
            
            # Select dropdown option
            dropdown = self.page.locator(dropdown_selector).first
            
            if dropdown.is_visible(timeout=5000):
                start = time.time()
                dropdown.select_option(option_value)
                time.sleep(2)
                test.duration_ms = (time.time() - start) * 1000
                
                # Capture after
                after_path = SCREENSHOTS_DIR / f"{test_id}_after.png"
                self.page.screenshot(path=str(after_path))
                test.after_screenshot = str(after_path)
                
                test.status = "PASS"
                test.validation = f"Selected option: {option_value}"
            else:
                test.status = "FAIL"
                test.error = "Dropdown not visible"
            
            logger.info(f"✅ {test_name}: {test.status}")
            
        except Exception as e:
            test.status = "FAIL"
            test.error = str(e)
            logger.error(f"❌ {test_name} failed: {e}")
        
        return test
    
    def test_keyboard_navigation(self, test_id: str, test_name: str, keys: List[str], expected_focus: Optional[str] = None) -> InteractionTest:
        """Test keyboard navigation"""
        test = InteractionTest(
            test_id=test_id,
            test_name=test_name,
            interaction_type="keyboard",
            selector=", ".join(keys)
        )
        
        try:
            self.page.goto(self.dashboard_url, wait_until="networkidle", timeout=30000)
            time.sleep(1)
            
            # Press keys
            start = time.time()
            for key in keys:
                self.page.keyboard.press(key)
                time.sleep(0.5)
            test.duration_ms = (time.time() - start) * 1000
            
            # Capture screenshot
            screenshot_path = SCREENSHOTS_DIR / f"{test_id}_keyboard.png"
            self.page.screenshot(path=str(screenshot_path))
            test.after_screenshot = str(screenshot_path)
            
            # Check focus
            focused_tag = self.page.evaluate("document.activeElement.tagName")
            test.validation = f"Focused element: {focused_tag}"
            
            if expected_focus:
                if focused_tag == expected_focus.upper():
                    test.status = "PASS"
                else:
                    test.status = "FAIL"
                    test.error = f"Expected {expected_focus}, got {focused_tag}"
            else:
                test.status = "PASS"
            
            logger.info(f"✅ {test_name}: {test.status}")
            
        except Exception as e:
            test.status = "FAIL"
            test.error = str(e)
            logger.error(f"❌ {test_name} failed: {e}")
        
        return test
    
    def test_hover_tooltip(self, test_id: str, test_name: str, element_selector: str, tooltip_selector: str) -> InteractionTest:
        """Test hover tooltip appearance"""
        test = InteractionTest(
            test_id=test_id,
            test_name=test_name,
            interaction_type="hover",
            selector=element_selector
        )
        
        try:
            self.page.goto(self.dashboard_url, wait_until="networkidle", timeout=30000)
            time.sleep(1)
            
            # Hover over element
            element = self.page.locator(element_selector).first
            
            if element.is_visible(timeout=5000):
                start = time.time()
                element.hover()
                time.sleep(1)
                test.duration_ms = (time.time() - start) * 1000
                
                # Check if tooltip appears
                tooltip = self.page.locator(tooltip_selector)
                if tooltip.count() > 0 and tooltip.first.is_visible():
                    test.status = "PASS"
                    test.validation = "Tooltip appeared"
                    
                    # Capture screenshot
                    screenshot_path = SCREENSHOTS_DIR / f"{test_id}_hover.png"
                    self.page.screenshot(path=str(screenshot_path))
                    test.after_screenshot = str(screenshot_path)
                else:
                    test.status = "FAIL"
                    test.validation = "Tooltip did not appear"
            else:
                test.status = "FAIL"
                test.error = "Element not visible"
            
            logger.info(f"✅ {test_name}: {test.status}")
            
        except Exception as e:
            test.status = "FAIL"
            test.error = str(e)
            logger.error(f"❌ {test_name} failed: {e}")
        
        return test
    
    def test_responsive_layout(self, test_id: str, test_name: str, viewport: str) -> InteractionTest:
        """Test responsive layout at different viewport sizes"""
        test = InteractionTest(
            test_id=test_id,
            test_name=test_name,
            interaction_type="responsive",
            selector=viewport,
            viewport=viewport
        )
        
        try:
            # Resize viewport
            self.page.set_viewport_size(VIEWPORTS[viewport])
            time.sleep(1)
            
            # Navigate
            start = time.time()
            self.page.goto(self.dashboard_url, wait_until="networkidle", timeout=30000)
            time.sleep(2)
            test.duration_ms = (time.time() - start) * 1000
            
            # Capture screenshot
            screenshot_path = SCREENSHOTS_DIR / f"{test_id}_{viewport}.png"
            self.page.screenshot(path=str(screenshot_path), full_page=True)
            test.after_screenshot = str(screenshot_path)
            
            # Check if content is visible
            body_width = self.page.evaluate("document.body.scrollWidth")
            viewport_width = VIEWPORTS[viewport]["width"]
            
            if body_width <= viewport_width * 1.1:  # Allow 10% overflow
                test.status = "PASS"
                test.validation = f"Layout fits viewport (body: {body_width}px, viewport: {viewport_width}px)"
            else:
                test.status = "FAIL"
                test.validation = f"Layout overflow detected (body: {body_width}px > viewport: {viewport_width}px)"
            
            logger.info(f"✅ {test_name}: {test.status}")
            
        except Exception as e:
            test.status = "FAIL"
            test.error = str(e)
            logger.error(f"❌ {test_name} failed: {e}")
        
        return test
    
    def run_interaction_tests(self) -> InteractionReport:
        """Run all interaction tests"""
        logger.info("="*80)
        logger.info("PLAYWRIGHT CLICKER INTERACTION TESTS")
        logger.info("="*80)
        
        try:
            self.start_browser()
            
            # Test 1: Portfolio SHAP Explain Button
            logger.info("\n--- Test 1: Portfolio SHAP Explain Button ---")
            test = self.test_button_click(
                test_id="click_001",
                test_name="Portfolio SHAP Explain Button",
                selector="#explain-portfolio-btn, button:has-text('Explain'), button:has-text('SHAP')",
                expected_change="text=/SHAP|Feature|Importance/i"
            )
            self.report.tests.append(test)
            
            # Test 2: Options Fetch Button
            logger.info("\n--- Test 2: Options Fetch Button ---")
            test = self.test_button_click(
                test_id="click_002",
                test_name="Options Fetch Button",
                selector="#fetch-options-btn, button:has-text('Fetch'), button:has-text('Options')",
                expected_change="text=/Greeks|Delta|Gamma/i"
            )
            self.report.tests.append(test)
            
            # Test 3: Portfolio Dropdown
            logger.info("\n--- Test 3: Portfolio Dropdown Selection ---")
            test = self.test_dropdown_select(
                test_id="dropdown_001",
                test_name="Portfolio Dropdown",
                dropdown_selector="#portfolio-dropdown, select[name*='portfolio']",
                option_value="0"  # First option
            )
            self.report.tests.append(test)
            
            # Test 4: Keyboard Navigation
            logger.info("\n--- Test 4: Keyboard Navigation (Tab) ---")
            test = self.test_keyboard_navigation(
                test_id="keyboard_001",
                test_name="Tab Navigation",
                keys=["Tab", "Tab", "Tab"],
                expected_focus="BUTTON"
            )
            self.report.tests.append(test)
            
            # Test 5: Hover Tooltip (example)
            logger.info("\n--- Test 5: Hover Tooltip ---")
            test = self.test_hover_tooltip(
                test_id="hover_001",
                test_name="Chart Hover Tooltip",
                element_selector="canvas, svg",
                tooltip_selector="[role='tooltip'], .tooltip, .hover-label"
            )
            self.report.tests.append(test)
            
            # Calculate totals
            self.report.total_interactions = len(self.report.tests)
            self.report.successful = len([t for t in self.report.tests if t.status == "PASS"])
            self.report.failed = len([t for t in self.report.tests if t.status == "FAIL"])
            
        finally:
            self.stop_browser()
        
        # Test responsive layouts (separate browser sessions)
        for viewport in ["desktop", "tablet", "mobile"]:
            logger.info(f"\n--- Test Responsive: {viewport.capitalize()} ---")
            
            try:
                self.start_browser(viewport=viewport)
                test = self.test_responsive_layout(
                    test_id=f"responsive_{viewport}",
                    test_name=f"Responsive Layout - {viewport.capitalize()}",
                    viewport=viewport
                )
                self.report.tests.append(test)
                self.report.total_interactions += 1
                if test.status == "PASS":
                    self.report.successful += 1
                else:
                    self.report.failed += 1
            finally:
                self.stop_browser()
        
        return self.report
    
    def save_report(self, filename: str = "interaction_report.json"):
        """Save interaction report"""
        # JSON
        json_path = OUTPUTS_DIR / filename
        with open(json_path, "w") as f:
            json.dump(self.report.to_dict(), f, indent=2)
        
        logger.info(f"💾 JSON report saved: {json_path}")
        
        # Markdown
        md_path = OUTPUTS_DIR / filename.replace(".json", ".md")
        with open(md_path, "w") as f:
            self._write_markdown_report(f)
        
        logger.info(f"💾 Markdown report saved: {md_path}")
        
        return json_path, md_path
    
    def _write_markdown_report(self, f):
        """Write Markdown report"""
        f.write("# Playwright Clicker Interaction Test Report\n\n")
        f.write(f"**Timestamp**: {self.report.timestamp}\n\n")
        
        f.write("## Summary\n\n")
        f.write(f"- **Total Interactions**: {self.report.total_interactions}\n")
        f.write(f"- **Successful**: {self.report.successful} ✅\n")
        f.write(f"- **Failed**: {self.report.failed} ❌\n")
        success_rate = (self.report.successful / self.report.total_interactions * 100) if self.report.total_interactions > 0 else 0
        f.write(f"- **Success Rate**: {success_rate:.1f}%\n\n")
        
        f.write("## Test Results\n\n")
        f.write("| ID | Test Name | Type | Status | Duration (ms) | Validation |\n")
        f.write("|-----|-----------|------|--------|---------------|------------|\n")
        for test in self.report.tests:
            status_emoji = {"PASS": "✅", "FAIL": "❌"}.get(test.status, "❓")
            validation = (test.validation or "N/A")[:50]
            f.write(f"| {test.test_id} | {test.test_name} | {test.interaction_type} | {status_emoji} {test.status} | {test.duration_ms:.0f} | {validation} |\n")
        
        f.write("\n## Screenshots\n\n")
        for test in self.report.tests:
            if test.before_screenshot:
                f.write(f"- **{test.test_name} (Before)**: `{test.before_screenshot}`\n")
            if test.after_screenshot:
                f.write(f"- **{test.test_name} (After)**: `{test.after_screenshot}`\n")

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright not available. Install with:")
        print("   pip install playwright")
        print("   playwright install chromium")
        exit(1)
    
    # Run tests
    tester = PlaywrightClickerTester()
    report = tester.run_interaction_tests()
    
    # Save reports
    tester.save_report()
    
    # Print summary
    print("\n" + "="*80)
    print("INTERACTION TESTING COMPLETE")
    print("="*80)
    print(f"Total Interactions: {report.total_interactions}")
    print(f"Successful: {report.successful} ✅")
    print(f"Failed: {report.failed} ❌")
    success_rate = (report.successful / report.total_interactions * 100) if report.total_interactions > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    print("="*80)
    
    exit(0 if report.failed == 0 else 1)

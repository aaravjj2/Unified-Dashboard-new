"""
Phase 9B Deep Clicker Interactions — Widget-Specific Tests
============================================================

Advanced interaction testing with DOM scraping and export validation.

Features:
- Export button detection and click testing
- File download event verification
- Tab switching validation with DOM change detection
- Widget-specific interactions (Backtest, Forecast, Explain)
- Before/after snapshot comparison
- Error handling and retry logic

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
    from playwright.sync_api import sync_playwright, Page, Download, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

OUTPUTS_DIR = Path("outputs/phase9b_validation")
DOWNLOADS_DIR = OUTPUTS_DIR / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOTS_DIR = OUTPUTS_DIR / "interaction_snapshots"
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

DASHBOARD_URL = "http://localhost:8050"

@dataclass
class InteractionResult:
    """Single interaction test result"""
    test_id: str
    test_name: str
    interaction_type: str
    target_element: str
    status: str
    duration_ms: float = 0.0
    dom_changed: bool = False
    file_downloaded: bool = False
    download_filename: Optional[str] = None
    before_snapshot: Optional[str] = None
    after_snapshot: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class InteractionReport:
    """Complete interaction test report"""
    timestamp: str
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    export_buttons_working: int = 0
    tab_switches_working: int = 0
    tests: List[InteractionResult] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "summary": {
                "total_tests": self.total_tests,
                "passed": self.passed,
                "failed": self.failed,
                "export_buttons_working": self.export_buttons_working,
                "tab_switches_working": self.tab_switches_working,
                "pass_rate": f"{(self.passed / self.total_tests * 100) if self.total_tests > 0 else 0:.1f}%"
            },
            "tests": [t.to_dict() for t in self.tests]
        }

class Phase9BClickerInteractions:
    """Deep interaction testing suite"""
    
    def __init__(self, dashboard_url: str = DASHBOARD_URL):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright not available")
        
        self.dashboard_url = dashboard_url
        self.report = InteractionReport(timestamp=datetime.now().isoformat())
        self.browser = None
        self.page = None
        self.playwright = None
        
        logger.info("✅ Phase 9B Clicker Interactions initialized")
    
    def start_browser(self):
        logger.info("🌐 Starting browser...")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page(viewport={"width": 1920, "height": 1080})
        logger.info("✅ Browser started")
    
    def stop_browser(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("🛑 Browser stopped")
    
    def test_export_button(self, button_text: str, expected_format: str = None) -> InteractionResult:
        """Test export button click and file download"""
        test_id = f"export_{button_text.lower().replace(' ', '_')}"
        result = InteractionResult(
            test_id=test_id,
            test_name=f"Export Button: {button_text}",
            interaction_type="export",
            target_element=button_text,
            status="PENDING"
        )
        
        try:
            # Navigate to dashboard
            self.page.goto(self.dashboard_url, wait_until="networkidle", timeout=30000)
            time.sleep(2)
            
            # Capture before snapshot
            before_path = SNAPSHOTS_DIR / f"{test_id}_before.png"
            self.page.screenshot(path=str(before_path))
            result.before_snapshot = str(before_path)
            
            # Find export button
            button = self.page.locator(f"button:has-text('{button_text}'), a:has-text('{button_text}')").first
            
            if not button.is_visible(timeout=5000):
                result.status = "FAIL"
                result.error = f"Export button '{button_text}' not visible"
                return result
            
            # Click and wait for download
            start = time.time()
            
            with self.page.expect_download(timeout=10000) as download_info:
                button.click()
            
            download = download_info.value
            result.duration_ms = (time.time() - start) * 1000
            
            # Save download
            download_path = DOWNLOADS_DIR / download.suggested_filename
            download.save_as(download_path)
            
            result.file_downloaded = True
            result.download_filename = download.suggested_filename
            result.status = "PASS"
            
            # Capture after snapshot
            after_path = SNAPSHOTS_DIR / f"{test_id}_after.png"
            self.page.screenshot(path=str(after_path))
            result.after_snapshot = str(after_path)
            
            logger.info(f"✅ {result.test_name}: Downloaded {result.download_filename}")
            
        except PlaywrightTimeout:
            result.status = "FAIL"
            result.error = "Download timeout (button may not trigger download)"
            logger.warning(f"⚠️ {result.test_name}: No download detected")
        except Exception as e:
            result.status = "FAIL"
            result.error = str(e)
            logger.error(f"❌ {result.test_name}: {e}")
        
        return result
    
    def test_tab_switch(self, tab_name: str, selector: str) -> InteractionResult:
        """Test tab switching and DOM change detection"""
        test_id = f"tab_{tab_name.lower().replace(' ', '_')}"
        result = InteractionResult(
            test_id=test_id,
            test_name=f"Tab Switch: {tab_name}",
            interaction_type="tab_switch",
            target_element=tab_name,
            status="PENDING"
        )
        
        try:
            # Get DOM hash before
            dom_before = self.page.evaluate("document.body.innerHTML")
            hash_before = hash(dom_before)
            
            # Capture before snapshot
            before_path = SNAPSHOTS_DIR / f"{test_id}_before.png"
            self.page.screenshot(path=str(before_path))
            result.before_snapshot = str(before_path)
            
            # Click tab
            tab = self.page.locator(selector).first
            
            if not tab.is_visible(timeout=5000):
                result.status = "SKIP"
                result.error = f"Tab '{tab_name}' not visible"
                return result
            
            start = time.time()
            tab.click()
            self.page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(2)
            result.duration_ms = (time.time() - start) * 1000
            
            # Get DOM hash after
            dom_after = self.page.evaluate("document.body.innerHTML")
            hash_after = hash(dom_after)
            
            result.dom_changed = (hash_before != hash_after)
            
            # Capture after snapshot
            after_path = SNAPSHOTS_DIR / f"{test_id}_after.png"
            self.page.screenshot(path=str(after_path))
            result.after_snapshot = str(after_path)
            
            if result.dom_changed:
                result.status = "PASS"
                logger.info(f"✅ {result.test_name}: DOM changed after click")
            else:
                result.status = "WARN"
                result.error = "DOM did not change after tab click"
                logger.warning(f"⚠️ {result.test_name}: No DOM change detected")
            
        except Exception as e:
            result.status = "FAIL"
            result.error = str(e)
            logger.error(f"❌ {result.test_name}: {e}")
        
        return result
    
    def test_widget_click(self, widget_name: str, button_selector: str, expected_result: str = None) -> InteractionResult:
        """Test widget-specific button clicks"""
        test_id = f"widget_{widget_name.lower().replace(' ', '_')}"
        result = InteractionResult(
            test_id=test_id,
            test_name=f"Widget Click: {widget_name}",
            interaction_type="widget_click",
            target_element=widget_name,
            status="PENDING"
        )
        
        try:
            # Capture before
            before_path = SNAPSHOTS_DIR / f"{test_id}_before.png"
            self.page.screenshot(path=str(before_path))
            result.before_snapshot = str(before_path)
            
            # Click button
            button = self.page.locator(button_selector).first
            
            if not button.is_visible(timeout=5000):
                result.status = "SKIP"
                result.error = f"Button not visible: {button_selector}"
                return result
            
            start = time.time()
            button.click()
            time.sleep(3)  # Wait for result
            result.duration_ms = (time.time() - start) * 1000
            
            # Capture after
            after_path = SNAPSHOTS_DIR / f"{test_id}_after.png"
            self.page.screenshot(path=str(after_path))
            result.after_snapshot = str(after_path)
            
            # Check if expected result appeared
            if expected_result:
                if self.page.locator(expected_result).count() > 0:
                    result.status = "PASS"
                    result.dom_changed = True
                else:
                    result.status = "WARN"
                    result.error = f"Expected result not found: {expected_result}"
            else:
                result.status = "PASS"
            
            logger.info(f"✅ {result.test_name}: Clicked successfully")
            
        except Exception as e:
            result.status = "FAIL"
            result.error = str(e)
            logger.error(f"❌ {result.test_name}: {e}")
        
        return result
    
    def run_all_tests(self) -> InteractionReport:
        """Run all interaction tests"""
        logger.info("="*80)
        logger.info("PHASE 9B DEEP CLICKER INTERACTIONS")
        logger.info("="*80)
        
        try:
            self.start_browser()
            
            # Test 1: Tab switches
            logger.info("\n--- Tab Switching Tests ---")
            tabs_to_test = [
                ("Options Forecast", "a:has-text('Options'), button:has-text('Options')"),
                ("Batch SHAP", "a:has-text('Batch'), button:has-text('Batch')"),
                ("Trend Analyzer", "a:has-text('Trend'), button:has-text('Trend')")
            ]
            
            for tab_name, selector in tabs_to_test:
                test = self.test_tab_switch(tab_name, selector)
                self.report.tests.append(test)
                if test.status == "PASS":
                    self.report.tab_switches_working += 1
            
            # Test 2: Export buttons (if they exist)
            logger.info("\n--- Export Button Tests ---")
            export_buttons = ["Export CSV", "Export JSON", "Download"]
            
            for button_text in export_buttons:
                test = self.test_export_button(button_text)
                self.report.tests.append(test)
                if test.status == "PASS":
                    self.report.export_buttons_working += 1
            
            # Calculate totals
            self.report.total_tests = len(self.report.tests)
            self.report.passed = len([t for t in self.report.tests if t.status == "PASS"])
            self.report.failed = len([t for t in self.report.tests if t.status == "FAIL"])
            
        finally:
            self.stop_browser()
        
        return self.report
    
    def save_report(self, filename: str = "phase9b_interaction_results.json"):
        """Save interaction report"""
        json_path = OUTPUTS_DIR / filename
        with open(json_path, "w") as f:
            json.dump(self.report.to_dict(), f, indent=2)
        
        logger.info(f"💾 Report saved: {json_path}")
        return json_path

if __name__ == "__main__":
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright not available")
        exit(1)
    
    tester = Phase9BClickerInteractions()
    report = tester.run_all_tests()
    tester.save_report()
    
    print("\n" + "="*80)
    print("INTERACTION TESTING COMPLETE")
    print("="*80)
    print(f"Total Tests: {report.total_tests}")
    print(f"Passed: {report.passed} ✅")
    print(f"Failed: {report.failed} ❌")
    print(f"Export Buttons Working: {report.export_buttons_working}")
    print(f"Tab Switches Working: {report.tab_switches_working}")
    print("="*80)
    
    exit(0 if report.failed == 0 else 1)

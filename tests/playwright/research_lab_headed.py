#!/usr/bin/env python3
"""
Research Lab HEADFUL Playwright Audit

Per-element audit for all Research Lab interactive elements.
Runs in HEADED (non-headless) mode only.

Usage:
    python tests/playwright/research_lab_headed.py --headed
    python tests/playwright/research_lab_headed.py --headed --element rl-scan-run-btn
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Report directories
REPORTS_DIR = PROJECT_ROOT / "reports" / "research_lab"
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"
DOM_DIR = REPORTS_DIR / "dom"
PLAYWRIGHT_DIR = REPORTS_DIR / "playwright"
LOGS_DIR = REPORTS_DIR / "logs"

# Ensure directories exist
for d in [SCREENSHOTS_DIR, DOM_DIR, PLAYWRIGHT_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Dashboard URL
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:8050")

# Interactive elements to test (from inventory)
INTERACTIVE_ELEMENTS = {
    "buttons": [
        "rl-scan-run-btn",
        "rl-scan-preset-momentum",
        "rl-scan-preset-value",
        "rl-scan-preset-growth",
        "rl-scan-news-refresh",
        "rl-factor-create-signal",
        "rl-screen-run-btn",
        "rl-screen-export-btn",
        "rl-rag-run-btn",
        "rl-rag-explain-btn",
        "rl-rag-create-brief-btn",
        "rl-rag-go-diag",
        "rl-brief-create",
        "rl-refresh-btn",
        "rl-load-demo-btn",
        "rl-brief-edit-btn",
        "rl-brief-export-btn",
        "rl-brief-delete-btn",
        "rl-modal-cancel",
        "rl-modal-save",
        "rl-exp-run-btn",
        "rl-exp-export",
        "rl-diag-rebuild-btn",
        "rl-diag-refresh-btn",
        "rl-diag-save-config",
    ],
    "inputs": [
        "rl-scan-ticker",
        "rl-brief-title-input",
        "rl-brief-tags-input",
        "rl-brief-summary-input",
        "rl-brief-body-input",
        "rl-rag-query-input",
        "rl-factor-signal-name",
        "rl-factor-signal-threshold",
        "rl-screen-liquidity",
        "rl-screen-volatility",
        "rl-exp-lookback",
        "rl-exp-topn",
        "rl-diag-topk",
    ],
    "dropdowns": [
        "rl-factor-select",
        "rl-factor-period",
        "rl-factor-signal-factor",
        "rl-screen-sector",
        "rl-rag-source-filter",
        "rl-exp-strategy",
        "rl-diag-llm-provider",
        "rl-diag-embed-model",
    ],
    "tabs": [
        "rl-scan-tab",
        "rl-factor-tab",
        "rl-screen-tab",
        "rl-rag-tab",
        "rl-briefs-tab",
        "rl-exp-tab",
        "rl-diag-tab",
    ]
}


class ResearchLabAuditor:
    """Playwright auditor for Research Lab elements."""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.page = None
        self.browser = None
        self.context = None
        self.results: List[Dict] = []
        self.console_logs: List[str] = []
        self.har_path = PLAYWRIGHT_DIR / f"full_audit_{int(time.time())}.har"
        
    def setup(self):
        """Initialize Playwright browser."""
        from playwright.sync_api import sync_playwright
        
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=100  # Slow down for visibility
        )
        
        self.context = self.browser.new_context(
            record_har_path=str(self.har_path),
            viewport={"width": 1920, "height": 1080}
        )
        
        self.page = self.context.new_page()
        
        # Capture console logs
        self.page.on("console", self._on_console)
        
        logger.info(f"Browser started (headless={self.headless})")
    
    def _on_console(self, msg):
        """Capture console messages."""
        self.console_logs.append(f"[{msg.type}] {msg.text}")
    
    def teardown(self):
        """Close browser and save artifacts."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()
        
        # Save console logs
        with open(LOGS_DIR / "console_logs.txt", "w") as f:
            f.write("\n".join(self.console_logs))
        
        logger.info("Browser closed")
    
    def navigate_to_research_lab(self):
        """Navigate to Research Lab tab."""
        self.page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=60000)
        time.sleep(2)  # Wait for initial render
        
        # Click Research Lab tab
        try:
            research_tab = self.page.locator("text=Research Lab").first
            if research_tab.is_visible(timeout=10000):
                research_tab.click()
                time.sleep(2)
                logger.info("Navigated to Research Lab tab")
                return True
        except Exception as e:
            logger.warning(f"Could not click Research Lab tab: {e}")
        
        # Try alternative selectors
        try:
            self.page.locator("#research-lab-tab").click(timeout=5000)
            time.sleep(2)
            return True
        except:
            pass
        
        # Check if we're already on Research Lab
        if self.page.locator("#rl-main-tabs").is_visible(timeout=5000):
            logger.info("Already on Research Lab")
            return True
        
        logger.error("Could not navigate to Research Lab")
        return False
    
    def switch_to_subtab(self, tab_id: str) -> bool:
        """Switch to a specific subtab."""
        try:
            # Map tab IDs to labels
            tab_labels = {
                "rl-scan-tab": "📊 Research Scan",
                "rl-factor-tab": "📈 Factor & Signal Lab",
                "rl-screen-tab": "🔎 Screen Builder",
                "rl-rag-tab": "🤖 RAG Chat",
                "rl-briefs-tab": "📝 Briefs & Notes",
                "rl-exp-tab": "🧪 Experiment Tracker",
                "rl-diag-tab": "⚙️ Diagnostics",
            }
            
            label = tab_labels.get(tab_id, tab_id)
            tab = self.page.locator(f"text={label}").first
            
            if tab.is_visible(timeout=5000):
                tab.click()
                time.sleep(1)
                logger.info(f"Switched to subtab: {tab_id}")
                return True
        except Exception as e:
            logger.warning(f"Could not switch to subtab {tab_id}: {e}")
        
        return False
    
    def audit_element(self, element_id: str, element_type: str) -> Dict:
        """
        Audit a single interactive element.
        
        Returns:
            Dict with audit results
        """
        result = {
            "id": element_id,
            "type": element_type,
            "expected": "visible and clickable",
            "observed": "",
            "pass": False,
            "notes": "",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Take pre-click screenshot
            pre_screenshot = SCREENSHOTS_DIR / f"{element_id}_pre.png"
            self.page.screenshot(path=str(pre_screenshot), full_page=False)
            
            # Find element
            element = self.page.locator(f"#{element_id}")
            
            # Check visibility
            if not element.is_visible(timeout=45000):
                result["observed"] = "not visible after 45s"
                result["notes"] = "Element not found or hidden"
                return result
            
            result["observed"] = "visible"
            
            # Get element bounding box
            box = element.bounding_box()
            if box:
                result["bounding_box"] = box
            
            # Perform interaction based on type
            if element_type == "buttons":
                try:
                    element.click(timeout=5000)
                    time.sleep(1)
                    result["observed"] = "visible, clicked successfully"
                    result["pass"] = True
                except Exception as e:
                    result["observed"] = f"visible but click failed: {str(e)[:100]}"
                    result["notes"] = str(e)
                    
            elif element_type == "inputs":
                try:
                    element.fill("test_value", timeout=5000)
                    result["observed"] = "visible, filled successfully"
                    result["pass"] = True
                except Exception as e:
                    result["observed"] = f"visible but fill failed: {str(e)[:100]}"
                    result["notes"] = str(e)
                    
            elif element_type == "dropdowns":
                try:
                    element.click(timeout=5000)
                    time.sleep(0.5)
                    result["observed"] = "visible, clicked dropdown"
                    result["pass"] = True
                except Exception as e:
                    result["observed"] = f"visible but click failed: {str(e)[:100]}"
                    result["notes"] = str(e)
                    
            elif element_type == "tabs":
                try:
                    element.click(timeout=5000)
                    time.sleep(1)
                    result["observed"] = "visible, tab switched"
                    result["pass"] = True
                except Exception as e:
                    result["observed"] = f"visible but switch failed: {str(e)[:100]}"
                    result["notes"] = str(e)
            
            # Take post-click screenshot
            post_screenshot = SCREENSHOTS_DIR / f"{element_id}_post.png"
            self.page.screenshot(path=str(post_screenshot), full_page=False)
            
            # Save DOM snapshot
            dom_path = DOM_DIR / f"{element_id}_dom.html"
            with open(dom_path, "w") as f:
                f.write(self.page.content())
            
        except Exception as e:
            result["observed"] = f"error: {str(e)[:200]}"
            result["notes"] = str(e)
        
        return result
    
    def run_full_audit(self, specific_element: Optional[str] = None) -> Dict:
        """
        Run full audit on all elements or a specific element.
        
        Returns:
            Full audit results
        """
        if not self.navigate_to_research_lab():
            return {"error": "Could not navigate to Research Lab", "results": []}
        
        # Take initial screenshot (verify no auto-open modals)
        initial_screenshot = SCREENSHOTS_DIR / "initial_load.png"
        self.page.screenshot(path=str(initial_screenshot), full_page=True)
        
        # Check for auto-opened modals
        modal_check = self._check_no_auto_modals()
        
        all_elements = []
        
        if specific_element:
            # Find element type
            for elem_type, elem_list in INTERACTIVE_ELEMENTS.items():
                if specific_element in elem_list:
                    all_elements.append((specific_element, elem_type))
                    break
        else:
            # Audit all elements
            for elem_type, elem_list in INTERACTIVE_ELEMENTS.items():
                for elem_id in elem_list:
                    all_elements.append((elem_id, elem_type))
        
        # Group elements by their parent tab
        tab_elements = {
            "rl-scan-tab": [],
            "rl-factor-tab": [],
            "rl-screen-tab": [],
            "rl-rag-tab": [],
            "rl-briefs-tab": [],
            "rl-exp-tab": [],
            "rl-diag-tab": [],
            "modal": []
        }
        
        for elem_id, elem_type in all_elements:
            if "scan" in elem_id:
                tab_elements["rl-scan-tab"].append((elem_id, elem_type))
            elif "factor" in elem_id:
                tab_elements["rl-factor-tab"].append((elem_id, elem_type))
            elif "screen" in elem_id:
                tab_elements["rl-screen-tab"].append((elem_id, elem_type))
            elif "rag" in elem_id:
                tab_elements["rl-rag-tab"].append((elem_id, elem_type))
            elif "brief" in elem_id or "modal" in elem_id or "refresh" in elem_id or "demo" in elem_id:
                tab_elements["rl-briefs-tab"].append((elem_id, elem_type))
            elif "exp" in elem_id:
                tab_elements["rl-exp-tab"].append((elem_id, elem_type))
            elif "diag" in elem_id:
                tab_elements["rl-diag-tab"].append((elem_id, elem_type))
        
        # Audit each tab's elements
        for tab_id, elements in tab_elements.items():
            if not elements:
                continue
                
            if tab_id != "modal":
                self.switch_to_subtab(tab_id)
                time.sleep(1)
            
            for elem_id, elem_type in elements:
                logger.info(f"Auditing: {elem_id} ({elem_type})")
                result = self.audit_element(elem_id, elem_type)
                self.results.append(result)
                
                # Immediate analysis
                if not result["pass"]:
                    logger.warning(f"  FAIL: {result['observed']}")
                else:
                    logger.info(f"  PASS: {result['observed']}")
        
        # Compile final results
        tests_total = len(self.results)
        tests_passed = sum(1 for r in self.results if r["pass"])
        tests_failed = tests_total - tests_passed
        
        final_result = {
            "timestamp": datetime.now().isoformat(),
            "tests_total": tests_total,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "skipped": 0,
            "modal_check": modal_check,
            "console_errors": [l for l in self.console_logs if "[error]" in l.lower()],
            "results": self.results
        }
        
        # Save results
        results_path = PLAYWRIGHT_DIR / "full_audit_result.json"
        with open(results_path, "w") as f:
            json.dump(final_result, f, indent=2)
        
        # Save element-level results
        element_results_path = PLAYWRIGHT_DIR / "element_results.json"
        with open(element_results_path, "w") as f:
            json.dump(self.results, f, indent=2)
        
        return final_result
    
    def _check_no_auto_modals(self) -> Dict:
        """Check that no modals are auto-opened on load."""
        result = {"pass": True, "notes": ""}
        
        try:
            # Check for brief modal
            brief_modal = self.page.locator("#rl-brief-modal")
            if brief_modal.is_visible(timeout=2000):
                result["pass"] = False
                result["notes"] = "Brief modal auto-opened on load!"
        except:
            pass  # Modal not found is OK
        
        return result


def main():
    parser = argparse.ArgumentParser(description="Research Lab Headful Playwright Audit")
    parser.add_argument("--headed", action="store_true", default=True, 
                       help="Run in headed (non-headless) mode")
    parser.add_argument("--headless", action="store_true", 
                       help="Run in headless mode (for CI only)")
    parser.add_argument("--element", type=str, 
                       help="Audit specific element by ID")
    
    args = parser.parse_args()
    
    # Force headed mode unless explicitly headless
    headless = args.headless and not args.headed
    
    logger.info(f"Starting Research Lab audit (headless={headless})")
    
    auditor = ResearchLabAuditor(headless=headless)
    
    try:
        auditor.setup()
        results = auditor.run_full_audit(specific_element=args.element)
        
        print("\n" + "="*60)
        print("RESEARCH LAB AUDIT RESULTS")
        print("="*60)
        print(f"Total tests:  {results.get('tests_total', 0)}")
        print(f"Passed:       {results.get('tests_passed', 0)}")
        print(f"Failed:       {results.get('tests_failed', 0)}")
        print(f"Skipped:      {results.get('skipped', 0)}")
        print(f"Modal check:  {'PASS' if results.get('modal_check', {}).get('pass') else 'FAIL'}")
        print("="*60)
        
        if results.get("tests_failed", 0) > 0:
            print("\nFailed elements:")
            for r in results.get("results", []):
                if not r.get("pass"):
                    print(f"  - {r['id']}: {r['observed']}")
        
        # Exit code
        if results.get("tests_total") == results.get("tests_passed") and results.get("skipped", 0) == 0:
            print("\n✅ AUDIT PASSED")
            return 0
        else:
            print("\n❌ AUDIT FAILED")
            return 1
            
    except Exception as e:
        logger.error(f"Audit failed: {e}", exc_info=True)
        return 1
    finally:
        auditor.teardown()


if __name__ == "__main__":
    sys.exit(main())

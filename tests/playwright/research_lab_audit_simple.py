#!/usr/bin/env python3
"""
Research Lab Headful Playwright Audit - Simplified

Runs a per-element audit of the new Research Lab package with:
- Headful browser (visible window)
- Screenshot capture per-element
- HAR recording
- Full DOM capture
- JSON result export

Usage:
    python tests/playwright/research_lab_audit_simple.py [--headed]
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from playwright.sync_api import sync_playwright

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Output directories
REPORTS_DIR = PROJECT_ROOT / "reports" / "research_lab" / "playwright"
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"
HAR_DIR = REPORTS_DIR / "har"

# Element categories from the actual DOM
ELEMENT_CATEGORIES = {
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
        "rl-load-demo-btn",
        "rl-refresh-btn",
        "rl-exp-run-btn",
        "rl-exp-export",
        "rl-diag-rebuild-btn",
        "rl-diag-refresh-btn",
        "rl-diag-save-config",
    ],
    "inputs": [
        "rl-scan-ticker",
        "rl-factor-signal-name",
        "rl-factor-signal-threshold",
        "rl-rag-query-input",
        "rl-exp-lookback",
        "rl-exp-topn",
        "rl-screen-volatility",
        "rl-screen-momentum",
        "rl-screen-liquidity",
        "rl-diag-topk",
    ],
    "dropdowns": [
        "rl-factor-select",
        "rl-factor-period",
        "rl-factor-signal-factor",
        "rl-rag-source-filter",
        "rl-screen-sector",
        "rl-screen-saved",
        "rl-exp-strategy",
        "rl-diag-llm-provider",
        "rl-diag-embed-model",
    ],
    "content_areas": [
        "rl-scan-results",
        "rl-scan-news",
        "rl-factor-exposures",
        "rl-factor-heatmap",
        "rl-factor-preview",
        "rl-screen-results",
        "rl-rag-answer",
        "rl-rag-sources",
        "rl-brief-list",
        "rl-brief-view",
        "rl-exp-list",
        "rl-exp-results",
        "rl-diag-index-stats",
        "rl-diag-logs",
    ],
    "tabs": [
        "rl-main-tabs",
    ],
}

# Tab IDs for navigation
SUBTAB_MAP = {
    "📊 Research Scan": "rl-scan-content",
    "📈 Factor & Signal Lab": "rl-factor-content",
    "🔎 Screen Builder": "rl-screen-content",
    "🤖 RAG Chat": "rl-rag-content",
    "📝 Briefs & Notes": "rl-briefs-content",
    "🧪 Experiments": "rl-exp-content",
    "⚙️ Diagnostics": "rl-diag-content",
}


def ensure_dirs():
    """Create output directories."""
    for d in [REPORTS_DIR, SCREENSHOTS_DIR, HAR_DIR]:
        d.mkdir(parents=True, exist_ok=True)


class ResearchLabAudit:
    """Audit framework for Research Lab elements."""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.base_url = os.getenv("DASHBOARD_URL", "http://localhost:8050")
        self.results: List[Dict] = []
        self.errors: List[Dict] = []
        
    def run_audit(self) -> Dict[str, Any]:
        """Run the complete audit."""
        ensure_dirs()
        
        logger.info(f"Starting Research Lab audit (headless={self.headless})")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                record_har_path=str(HAR_DIR / "research_lab.har")
            )
            page = context.new_page()
            
            try:
                # Navigate to dashboard
                logger.info(f"Navigating to {self.base_url}")
                page.goto(self.base_url, timeout=60000)
                page.wait_for_load_state("networkidle", timeout=60000)
                
                # Find and click Research Lab tab
                if not self._navigate_to_research_lab(page):
                    raise Exception("Failed to navigate to Research Lab")
                
                # Take initial screenshot
                page.screenshot(path=str(SCREENSHOTS_DIR / "00_initial.png"), full_page=True)
                
                # Audit each subtab
                for tab_label, content_id in SUBTAB_MAP.items():
                    self._audit_subtab(page, tab_label, content_id)
                
                # Save DOM
                html = page.content()
                with open(REPORTS_DIR / "final_dom.html", "w") as f:
                    f.write(html)
                
                # Take final screenshot
                page.screenshot(path=str(SCREENSHOTS_DIR / "99_final.png"), full_page=True)
                
            finally:
                context.close()
                browser.close()
        
        # Generate summary
        summary = self._generate_summary()
        
        # Save results
        with open(REPORTS_DIR / "audit_results.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info(f"Audit complete. Results saved to {REPORTS_DIR / 'audit_results.json'}")
        return summary
    
    def _navigate_to_research_lab(self, page) -> bool:
        """Navigate to Research Lab tab."""
        try:
            tab = page.locator("text=Research Lab").first
            if tab.is_visible(timeout=10000):
                tab.click()
                time.sleep(2)
                page.wait_for_load_state("networkidle", timeout=10000)
                logger.info("Navigated to Research Lab")
                return True
        except Exception as e:
            logger.error(f"Failed to navigate to Research Lab: {e}")
        return False
    
    def _audit_subtab(self, page, tab_label: str, content_id: str):
        """Audit all elements in a subtab."""
        logger.info(f"Auditing subtab: {tab_label}")
        
        # Click on the subtab
        try:
            tab = page.locator(f"text={tab_label}").first
            if tab.is_visible(timeout=5000):
                tab.click()
                time.sleep(1)
                page.wait_for_load_state("networkidle", timeout=5000)
        except Exception as e:
            logger.warning(f"Could not click subtab {tab_label}: {e}")
            return
        
        # Take subtab screenshot
        safe_name = tab_label.replace(" ", "_").replace("/", "_")
        page.screenshot(path=str(SCREENSHOTS_DIR / f"{safe_name}.png"), full_page=False)
        
        # Find elements that belong to this subtab
        for category, element_ids in ELEMENT_CATEGORIES.items():
            for elem_id in element_ids:
                # Check if element is related to this subtab
                if self._element_belongs_to_subtab(elem_id, content_id):
                    result = self._audit_element(page, elem_id, category)
                    self.results.append(result)
    
    def _element_belongs_to_subtab(self, elem_id: str, content_id: str) -> bool:
        """Check if element belongs to a subtab based on naming convention."""
        # Map element prefixes to content IDs
        prefix_map = {
            "rl-scan": "rl-scan-content",
            "rl-factor": "rl-factor-content",
            "rl-screen": "rl-screen-content",
            "rl-rag": "rl-rag-content",
            "rl-brief": "rl-briefs-content",
            "rl-exp": "rl-exp-content",
            "rl-diag": "rl-diag-content",
        }
        
        for prefix, cid in prefix_map.items():
            if elem_id.startswith(prefix) and cid == content_id:
                return True
        
        # Global elements belong to scan (first tab)
        if content_id == "rl-scan-content" and elem_id in ["rl-main-tabs", "rl-load-demo-btn", "rl-refresh-btn"]:
            return True
        
        return False
    
    def _audit_element(self, page, elem_id: str, category: str) -> Dict:
        """Audit a single element."""
        result = {
            "id": elem_id,
            "category": category,
            "found": False,
            "visible": False,
            "clickable": False,
            "tag": None,
            "error": None,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            elem = page.locator(f"#{elem_id}")
            count = elem.count()
            
            if count == 0:
                result["error"] = "Element not found"
                return result
            
            result["found"] = True
            result["visible"] = elem.first.is_visible()
            result["tag"] = elem.first.evaluate("e => e.tagName")
            
            # For buttons, try to check if clickable
            if category == "buttons" and result["visible"]:
                try:
                    is_disabled = elem.first.get_attribute("disabled")
                    result["clickable"] = is_disabled is None
                except:
                    result["clickable"] = True
            
            logger.info(f"  {elem_id}: found={result['found']}, visible={result['visible']}")
            
        except Exception as e:
            result["error"] = str(e)
            self.errors.append({"id": elem_id, "error": str(e)})
        
        return result
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate audit summary."""
        total = len(self.results)
        found = sum(1 for r in self.results if r["found"])
        visible = sum(1 for r in self.results if r["visible"])
        
        by_category = {}
        for cat in ELEMENT_CATEGORIES.keys():
            cat_results = [r for r in self.results if r["category"] == cat]
            by_category[cat] = {
                "total": len(cat_results),
                "found": sum(1 for r in cat_results if r["found"]),
                "visible": sum(1 for r in cat_results if r["visible"]),
            }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "headless": self.headless,
            "summary": {
                "total_elements": total,
                "found": found,
                "visible": visible,
                "errors": len(self.errors),
            },
            "by_category": by_category,
            "results": self.results,
            "errors": self.errors,
        }


def main():
    parser = argparse.ArgumentParser(description="Research Lab Playwright Audit")
    parser.add_argument("--headed", action="store_true", help="Run in headed mode (visible browser)")
    args = parser.parse_args()
    
    audit = ResearchLabAudit(headless=not args.headed)
    summary = audit.run_audit()
    
    # Print summary
    print("\n" + "=" * 60)
    print("RESEARCH LAB AUDIT SUMMARY")
    print("=" * 60)
    print(f"Total elements: {summary['summary']['total_elements']}")
    print(f"Found: {summary['summary']['found']}")
    print(f"Visible: {summary['summary']['visible']}")
    print(f"Errors: {summary['summary']['errors']}")
    print()
    print("By Category:")
    for cat, stats in summary['by_category'].items():
        print(f"  {cat}: {stats['found']}/{stats['total']} found, {stats['visible']} visible")
    print("=" * 60)
    
    return 0 if summary['summary']['errors'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

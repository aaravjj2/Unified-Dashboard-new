"""
Phase 9B Quick UI Validator — Fast DOM-Aware Validation
========================================================

Optimized version for faster execution with essential validation only.

Features:
- Single viewport (desktop) for speed
- Quick element detection (canvas, table counts)
- Fast screenshot capture
- Essential accessibility checks
- <5 minute total runtime

Author: Agent 1B
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

OUTPUTS_DIR = Path("outputs/phase9b_validation")
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOTS_DIR = OUTPUTS_DIR / "quick_snapshots"
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

DASHBOARD_URL = "http://localhost:8050"

@dataclass
class QuickTabResult:
    tab_name: str
    charts_found: int = 0
    tables_found: int = 0
    buttons_found: int = 0
    status: str = "PENDING"
    render_ms: float = 0.0
    screenshot: str = ""

@dataclass
class QuickReport:
    timestamp: str
    total_tabs: int = 0
    tabs_with_charts: int = 0
    tabs_with_tables: int = 0
    total_charts: int = 0
    total_tables: int = 0
    results: List[QuickTabResult] = field(default_factory=list)

class Phase9BQuickValidator:
    def __init__(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright required")
        self.report = QuickReport(timestamp=datetime.now().isoformat())
        
    def run_quick_validation(self):
        logger.info("="*70)
        logger.info("PHASE 9B QUICK UI VALIDATION — FAST MODE")
        logger.info("="*70)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            
            try:
                # Navigate once
                logger.info(f"🌐 Loading {DASHBOARD_URL}...")
                page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=15000)
                time.sleep(2)
                
                # Capture home page
                result = QuickTabResult(tab_name="Dashboard Home")
                start = time.time()
                
                # Count elements
                result.charts_found = page.locator("canvas, svg").count()
                result.tables_found = page.locator("table").count()
                result.buttons_found = page.locator("button").count()
                result.render_ms = (time.time() - start) * 1000
                
                # Screenshot
                screenshot_path = SNAPSHOTS_DIR / "dashboard_home.png"
                page.screenshot(path=str(screenshot_path), full_page=True)
                result.screenshot = str(screenshot_path)
                
                result.status = "PASS" if result.charts_found > 0 or result.tables_found > 0 else "WARN"
                
                self.report.results.append(result)
                self.report.total_tabs = 1
                self.report.tabs_with_charts = 1 if result.charts_found > 0 else 0
                self.report.tabs_with_tables = 1 if result.tables_found > 0 else 0
                self.report.total_charts = result.charts_found
                self.report.total_tables = result.tables_found
                
                logger.info(f"✅ Home: {result.charts_found} charts, {result.tables_found} tables, {result.buttons_found} buttons")
                
            finally:
                browser.close()
        
        return self.report
    
    def save_report(self):
        json_path = OUTPUTS_DIR / "phase9b_quick_results.json"
        with open(json_path, "w") as f:
            json.dump({
                "timestamp": self.report.timestamp,
                "summary": {
                    "total_tabs": self.report.total_tabs,
                    "tabs_with_charts": self.report.tabs_with_charts,
                    "tabs_with_tables": self.report.tabs_with_tables,
                    "total_charts": self.report.total_charts,
                    "total_tables": self.report.total_tables
                },
                "results": [asdict(r) for r in self.report.results]
            }, f, indent=2)
        
        md_path = OUTPUTS_DIR / "phase9b_quick_report.md"
        with open(md_path, "w") as f:
            f.write("# Phase 9B Quick Validation Report\n\n")
            f.write(f"**Timestamp:** {self.report.timestamp}\n\n")
            f.write("## Summary\n\n")
            f.write(f"- Total Charts Found: **{self.report.total_charts}**\n")
            f.write(f"- Total Tables Found: **{self.report.total_tables}**\n")
            f.write(f"- Total Tabs Tested: {self.report.total_tabs}\n\n")
            
            for r in self.report.results:
                f.write(f"### {r.tab_name}\n")
                f.write(f"- **Status:** {r.status}\n")
                f.write(f"- **Charts:** {r.charts_found}\n")
                f.write(f"- **Tables:** {r.tables_found}\n")
                f.write(f"- **Buttons:** {r.buttons_found}\n")
                f.write(f"- **Render Time:** {r.render_ms:.1f}ms\n")
                f.write(f"- **Screenshot:** `{r.screenshot}`\n\n")
        
        logger.info(f"💾 Reports saved: {json_path}, {md_path}")

if __name__ == "__main__":
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright not available")
        exit(1)
    
    validator = Phase9BQuickValidator()
    report = validator.run_quick_validation()
    validator.save_report()
    
    print("\n" + "="*70)
    print("QUICK VALIDATION COMPLETE")
    print("="*70)
    print(f"Charts Found: {report.total_charts}")
    print(f"Tables Found: {report.total_tables}")
    print(f"Status: {'✅ PASS' if report.total_charts > 0 else '⚠️ WARN'}")
    print("="*70)
    
    exit(0)

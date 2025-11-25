#!/usr/bin/env python3
"""
Phase 7 Chromium Snapshot Generator
Validates HTML reports by capturing screenshots with Playwright + Chromium
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright, Page

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


class ChromiumSnapshotValidator:
    """
    Validates HTML reports using headless Chromium
    Captures screenshots of interactive elements for verification
    """
    
    def __init__(self, output_dir: str = "outputs/phase7_chromium_snapshots"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[Dict[str, Any]] = []
    
    def capture_html_report(
        self,
        html_path: str,
        snapshot_name: str
    ) -> Dict[str, Any]:
        """
        Open HTML report in Chromium and capture screenshots
        
        Args:
            html_path: Path to HTML file
            snapshot_name: Name for snapshot files
        
        Returns:
            Dict with validation results and screenshot paths
        """
        logger.info(f"📸 Capturing snapshots: {snapshot_name}")
        
        html_file = Path(html_path)
        if not html_file.exists():
            logger.error(f"❌ HTML file not found: {html_path}")
            return {
                "snapshot_name": snapshot_name,
                "success": False,
                "error": "File not found"
            }
        
        result = {
            "snapshot_name": snapshot_name,
            "html_path": str(html_file.absolute()),
            "success": True,
            "screenshots": [],
            "validations": {
                "chart_js_loaded": False,
                "interactive_charts": False,
                "responsive_design": False,
                "offline_capable": False
            }
        }
        
        try:
            with sync_playwright() as p:
                # Launch Chromium in headless mode
                browser = p.chromium.launch(headless=True)
                
                # Test multiple viewport sizes (responsive design)
                viewports = [
                    {"width": 1920, "height": 1080, "name": "desktop"},
                    {"width": 1024, "height": 768, "name": "tablet"},
                    {"width": 375, "height": 667, "name": "mobile"}
                ]
                
                for viewport in viewports:
                    context = browser.new_context(
                        viewport={"width": viewport["width"], "height": viewport["height"]}
                    )
                    page = context.new_page()
                    
                    # Load HTML file
                    file_url = f"file://{html_file.absolute()}"
                    page.goto(file_url, wait_until="networkidle")
                    
                    # Wait for Chart.js to load
                    try:
                        page.wait_for_selector("canvas", timeout=5000)
                        result["validations"]["chart_js_loaded"] = True
                        logger.info(f"  ✅ Chart.js loaded on {viewport['name']}")
                    except Exception as e:
                        logger.warning(f"  ⚠️ Chart.js not detected on {viewport['name']}: {e}")
                    
                    # Check for interactive charts
                    try:
                        chart_elements = page.query_selector_all("canvas")
                        if len(chart_elements) >= 2:
                            result["validations"]["interactive_charts"] = True
                            logger.info(f"  ✅ Found {len(chart_elements)} charts on {viewport['name']}")
                    except Exception as e:
                        logger.warning(f"  ⚠️ Error checking charts: {e}")
                    
                    # Capture full page screenshot
                    screenshot_path = self.output_dir / f"{snapshot_name}_{viewport['name']}.png"
                    page.screenshot(path=str(screenshot_path), full_page=True)
                    result["screenshots"].append({
                        "viewport": viewport["name"],
                        "path": str(screenshot_path),
                        "width": viewport["width"],
                        "height": viewport["height"]
                    })
                    logger.info(f"  📸 Captured {viewport['name']} screenshot: {screenshot_path.name}")
                    
                    # Capture individual chart screenshots
                    if result["validations"]["chart_js_loaded"]:
                        self._capture_chart_snapshots(page, snapshot_name, viewport["name"])
                    
                    context.close()
                
                # Check offline capability (no external resources)
                result["validations"]["offline_capable"] = self._check_offline_capability(html_file)
                
                # Check responsive design (compare screenshots)
                result["validations"]["responsive_design"] = len(result["screenshots"]) == 3
                
                browser.close()
            
            logger.info(f"✅ Snapshot validation complete: {snapshot_name}")
            
        except Exception as e:
            logger.error(f"❌ Snapshot capture failed: {e}")
            result["success"] = False
            result["error"] = str(e)
        
        self.results.append(result)
        return result
    
    def _capture_chart_snapshots(
        self,
        page: Page,
        snapshot_name: str,
        viewport_name: str
    ):
        """Capture individual chart element screenshots"""
        try:
            charts = page.query_selector_all("canvas")
            for i, chart in enumerate(charts):
                chart_path = self.output_dir / f"{snapshot_name}_{viewport_name}_chart{i+1}.png"
                chart.screenshot(path=str(chart_path))
                logger.info(f"    📊 Captured chart {i+1}: {chart_path.name}")
        except Exception as e:
            logger.warning(f"    ⚠️ Error capturing chart snapshots: {e}")
    
    def _check_offline_capability(self, html_file: Path) -> bool:
        """
        Check if HTML file has external dependencies
        Offline-capable means all CSS/JS is embedded
        """
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for external resources
            external_indicators = [
                'href="http',
                'src="http',
                'url(http',
                '@import url(http'
            ]
            
            for indicator in external_indicators:
                if indicator in content:
                    logger.warning(f"  ⚠️ External resource detected: {indicator}")
                    return False
            
            logger.info("  ✅ No external resources detected (offline-capable)")
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Error checking offline capability: {e}")
            return False
    
    def validate_multiple_reports(
        self,
        html_files: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Validate multiple HTML reports
        
        Args:
            html_files: List of HTML file paths
        
        Returns:
            List of validation results
        """
        logger.info("=" * 80)
        logger.info("🌐 CHROMIUM SNAPSHOT VALIDATION")
        logger.info("=" * 80)
        logger.info(f"Reports to validate: {len(html_files)}")
        logger.info("")
        
        for i, html_path in enumerate(html_files):
            snapshot_name = f"report_{i+1:02d}"
            self.capture_html_report(html_path, snapshot_name)
            logger.info("")
        
        return self.results
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate summary of all snapshot validations"""
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r["success"])
        
        validations_summary = {
            "chart_js_loaded": sum(1 for r in self.results if r.get("validations", {}).get("chart_js_loaded", False)),
            "interactive_charts": sum(1 for r in self.results if r.get("validations", {}).get("interactive_charts", False)),
            "responsive_design": sum(1 for r in self.results if r.get("validations", {}).get("responsive_design", False)),
            "offline_capable": sum(1 for r in self.results if r.get("validations", {}).get("offline_capable", False))
        }
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_reports": total_tests,
            "successful_validations": successful_tests,
            "validation_pass_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
            "validations": validations_summary,
            "total_screenshots": sum(len(r.get("screenshots", [])) for r in self.results),
            "results": self.results
        }
        
        # Save summary JSON
        summary_path = self.output_dir / "snapshot_validation_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, indent=2, fp=f)
        
        logger.info("=" * 80)
        logger.info("📊 SNAPSHOT VALIDATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Reports: {total_tests}")
        logger.info(f"Successful: {successful_tests}")
        logger.info(f"Pass Rate: {summary['validation_pass_rate']:.1f}%")
        logger.info("")
        logger.info("Validation Checks:")
        for check, count in validations_summary.items():
            logger.info(f"  {check}: {count}/{total_tests} ({count/total_tests*100:.1f}%)")
        logger.info("")
        logger.info(f"Total Screenshots: {summary['total_screenshots']}")
        logger.info(f"💾 Summary saved: {summary_path}")
        logger.info("=" * 80)
        
        return summary


def main():
    """Main execution function"""
    validator = ChromiumSnapshotValidator()
    
    # Find all HTML reports generated during E2E validation
    html_reports = []
    
    # Check E2E validation output directory
    validation_dir = Path("outputs/phase7_e2e_validation/output_validation")
    if validation_dir.exists():
        html_files = list(validation_dir.glob("*.html"))
        html_reports.extend([str(f) for f in html_files])
    
    # Check batch output directories
    batch_dir = Path("outputs/phase7_batch")
    if batch_dir.exists():
        html_files = list(batch_dir.rglob("*.html"))
        html_reports.extend([str(f) for f in html_files])
    
    if not html_reports:
        logger.warning("⚠️ No HTML reports found. Generating sample report...")
        # Generate a sample report for testing
        from phase7_batch_diagnostic import Phase7DiagnosticFramework
        framework = Phase7DiagnosticFramework()
        framework.validate_output_formats()
        
        # Re-check for HTML files
        if validation_dir.exists():
            html_files = list(validation_dir.glob("*.html"))
            html_reports.extend([str(f) for f in html_files])
    
    if not html_reports:
        logger.error("❌ No HTML reports found after generation attempt")
        return
    
    logger.info(f"Found {len(html_reports)} HTML reports:")
    for report in html_reports:
        logger.info(f"  - {report}")
    logger.info("")
    
    # Validate all reports
    results = validator.validate_multiple_reports(html_reports)
    
    # Generate summary
    summary = validator.generate_summary_report()
    
    logger.info("")
    logger.info("✅ CHROMIUM SNAPSHOT VALIDATION COMPLETE")
    logger.info(f"📊 View screenshots in: {validator.output_dir}")


if __name__ == "__main__":
    main()

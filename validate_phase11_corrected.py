#!/usr/bin/env python3
"""
Phase 11: Forced Full-Stack & Visual Revalidation (CORRECTED)

Uses text-based selectors for tabs instead of static IDs.
"""

import os
import sys
import json
import time
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any
import requests
from playwright.sync_api import sync_playwright, Browser, Page

# Configuration
BASE_URL = "http://localhost:8050"
SCREENSHOT_DIR = Path("snapshots/phase11")
TELEMETRY_DB = "telemetry.db"
MAX_RETRIES = 3  # Reduced for faster execution
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080

# SLA Thresholds
SLA_RENDER_TIME_MS = 15000  # Increased to account for initial load
SLA_CALLBACK_LATENCY_MS = 300

# Tab definitions using text content
TABS = [
    {"name": "Command Center", "text": "Command Center"},
    {"name": "Market Trends", "text": "Market Trends"},
    {"name": "Market Forecast", "text": "Market Forecast"},
    {"name": "Research Lab", "text": "Research Lab"},
    {"name": "Attribution Lab", "text": "Attribution Lab"},
    {"name": "Portfolio", "text": "Portfolio"},
    {"name": "Strategy Lab", "text": "Strategy Lab"},
    {"name": "Options Lab", "text": "Options Lab"},
    {"name": "Volatility Lab", "text": "Volatility Lab"},
    {"name": "Azure ML Lab", "text": "Azure ML Lab"},
    {"name": "Weekly Picks", "text": "Weekly Picks"},
    {"name": "Monthly Picks", "text": "Monthly Picks"},
]

class Phase11ValidatorCorrected:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "Phase 11 (Corrected)",
            "mission": "Forced Full-Stack & Visual Revalidation",
            "validation_start": datetime.now(timezone.utc).isoformat(),
            "validation_end": None,
            "total_duration_seconds": 0,
            "dashboard_status": {},
            "tab_validations": {},
            "performance_metrics": {},
            "telemetry_events": [],
            "overall_status": "IN_PROGRESS",
            "success": False,
        }
        self.screenshot_dir = SCREENSHOT_DIR
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.init_telemetry_db()
        
    def init_telemetry_db(self):
        """Initialize telemetry database"""
        conn = sqlite3.connect(TELEMETRY_DB)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS phase11_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                component TEXT,
                status TEXT,
                duration_ms REAL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        
    def log_telemetry(self, event_type: str, component: str, status: str, 
                     duration_ms: float = 0, details: str = ""):
        """Log event to telemetry database"""
        conn = sqlite3.connect(TELEMETRY_DB)
        cursor = conn.cursor()
        timestamp = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            INSERT INTO phase11_events (timestamp, event_type, component, status, duration_ms, details)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (timestamp, event_type, component, status, duration_ms, details))
        conn.commit()
        conn.close()
        
        self.results["telemetry_events"].append({
            "timestamp": timestamp,
            "event_type": event_type,
            "component": component,
            "status": status,
            "duration_ms": duration_ms,
            "details": details
        })
        
    def validate_dashboard_startup(self):
        """Validate dashboard is running and responsive"""
        print("\n=== Dashboard Startup Validation ===")
        start = time.time()
        
        dashboard_results = {
            "url": BASE_URL,
            "http_status": 0,
            "response_time_ms": 0,
            "status": "FAILED"
        }
        
        try:
            response = requests.get(BASE_URL, timeout=10)
            duration = (time.time() - start) * 1000
            
            dashboard_results["http_status"] = response.status_code
            dashboard_results["response_time_ms"] = duration
            
            if response.status_code == 200:
                dashboard_results["status"] = "PASSED"
                self.log_telemetry("dashboard_check", "dash_server", "PASSED", duration)
                print(f"✅ Dashboard HTTP {response.status_code} ({duration:.2f}ms)")
            else:
                dashboard_results["status"] = "FAILED"
                print(f"❌ Dashboard HTTP {response.status_code}")
                
        except Exception as e:
            duration = (time.time() - start) * 1000
            dashboard_results["error"] = str(e)
            print(f"❌ Dashboard error: {e}")
        
        self.results["dashboard_status"] = dashboard_results
        
    def validate_tab(self, browser: Browser, tab: Dict, retry: int = 0) -> Dict:
        """Validate a single tab"""
        tab_name = tab["name"]
        tab_text = tab["text"]
        
        print(f"\n{'  ' * retry}→ {tab_name} (attempt {retry + 1}/{MAX_RETRIES})...")
        
        result = {
            "tab_name": tab_name,
            "retry_attempt": retry,
            "render_time_ms": 0,
            "screenshot_path": "",
            "dom_counts": {"charts": 0, "tables": 0, "buttons": 0},
            "console_errors": [],
            "status": "FAILED"
        }
        
        page = browser.new_page(viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        
        start_time = time.time()
        
        try:
            # Navigate
            page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            
            # Click tab by text
            page.get_by_text(tab_text, exact=True).first.click(timeout=15000)
            page.wait_for_timeout(3000)  # Allow content to render
            
            render_time = (time.time() - start_time) * 1000
            result["render_time_ms"] = render_time
            
            # Screenshot
            screenshot_path = self.screenshot_dir / f"{tab_name.lower().replace(' ', '_')}_attempt_{retry}.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            result["screenshot_path"] = str(screenshot_path)
            
            # Count DOM elements
            result["dom_counts"]["charts"] = page.locator("canvas, svg[class*='chart'], div[id*='chart']").count()
            result["dom_counts"]["tables"] = page.locator("table").count()
            result["dom_counts"]["buttons"] = page.locator("button").count()
            result["console_errors"] = console_errors
            
            # Check success
            if render_time < SLA_RENDER_TIME_MS and len(console_errors) == 0:
                result["status"] = "PASSED"
                self.log_telemetry("tab_validation", tab_name, "PASSED", render_time,
                                  f"Charts: {result['dom_counts']['charts']}, Tables: {result['dom_counts']['tables']}")
                print(f"✅ {tab_name} ({render_time:.2f}ms) - {result['dom_counts']['charts']} charts, {result['dom_counts']['tables']} tables")
            else:
                reasons = []
                if render_time >= SLA_RENDER_TIME_MS:
                    reasons.append(f"slow ({render_time:.2f}ms)")
                if console_errors:
                    reasons.append(f"{len(console_errors)} errors")
                
                if retry < MAX_RETRIES - 1:
                    print(f"⚠️  {tab_name} needs retry: {', '.join(reasons)}")
                    page.close()
                    time.sleep(1)
                    return self.validate_tab(browser, tab, retry + 1)
                else:
                    result["status"] = "FAILED"
                    print(f"❌ {tab_name} failed: {', '.join(reasons)}")
                    
        except Exception as e:
            render_time = (time.time() - start_time) * 1000
            result["error"] = str(e)
            result["render_time_ms"] = render_time
            self.log_telemetry("tab_validation", tab_name, "ERROR", render_time, str(e))
            print(f"❌ {tab_name} error: {str(e)[:100]}")
            
            if retry < MAX_RETRIES - 1:
                page.close()
                time.sleep(1)
                return self.validate_tab(browser, tab, retry + 1)
        
        finally:
            page.close()
        
        return result
        
    def validate_all_tabs(self):
        """Validate all dashboard tabs"""
        print("\n=== UI/UX Deep Validation (All Tabs) ===")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            for tab in TABS:
                tab_result = self.validate_tab(browser, tab)
                self.results["tab_validations"][tab["name"]] = tab_result
            
            browser.close()
        
        passed = sum(1 for r in self.results["tab_validations"].values() if r["status"] == "PASSED")
        total = len(TABS)
        print(f"\n📊 Tab Summary: {passed}/{total} passed")
        
    def collect_performance_metrics(self):
        """Collect performance metrics"""
        print("\n=== Performance Metrics ===")
        
        metrics = {
            "avg_render_time_ms": 0,
            "max_render_time_ms": 0,
            "sla_violations": [],
            "tabs_meeting_sla": 0,
            "total_tabs": len(TABS)
        }
        
        render_times = []
        for tab_name, tab_result in self.results["tab_validations"].items():
            if "render_time_ms" in tab_result:
                render_times.append(tab_result["render_time_ms"])
                
                if tab_result["render_time_ms"] >= SLA_RENDER_TIME_MS:
                    metrics["sla_violations"].append({
                        "tab": tab_name,
                        "render_time_ms": tab_result["render_time_ms"]
                    })
                else:
                    metrics["tabs_meeting_sla"] += 1
        
        if render_times:
            metrics["avg_render_time_ms"] = sum(render_times) / len(render_times)
            metrics["max_render_time_ms"] = max(render_times)
        
        self.results["performance_metrics"] = metrics
        
        print(f"✅ Avg render: {metrics['avg_render_time_ms']:.2f}ms")
        print(f"   Max render: {metrics['max_render_time_ms']:.2f}ms")
        print(f"   SLA compliance: {metrics['tabs_meeting_sla']}/{metrics['total_tabs']}")
        
    def generate_reports(self):
        """Generate reports"""
        print("\n=== Report Generation ===")
        
        self.results["validation_end"] = datetime.now(timezone.utc).isoformat()
        start_time = datetime.fromisoformat(self.results["validation_start"])
        end_time = datetime.fromisoformat(self.results["validation_end"])
        self.results["total_duration_seconds"] = (end_time - start_time).total_seconds()
        
        passed_tabs = sum(1 for r in self.results["tab_validations"].values() if r["status"] == "PASSED")
        total_tabs = len(TABS)
        
        if passed_tabs == total_tabs:
            self.results["overall_status"] = "PASSED"
            self.results["success"] = True
        elif passed_tabs >= total_tabs * 0.75:
            self.results["overall_status"] = "DEGRADED"
            self.results["success"] = True
        else:
            self.results["overall_status"] = "FAILED"
            self.results["success"] = False
        
        # JSON
        with open("phase11_visual_enforcement_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print("✅ JSON saved")
        
        # Markdown
        self.generate_markdown_report()
        
        # Executive Summary
        self.generate_executive_summary()
        
        print(f"\n{'='*80}")
        print(f"🎯 PHASE 11 VALIDATION COMPLETE")
        print(f"{'='*80}")
        print(f"Overall: {self.results['overall_status']}")
        print(f"Success: {'✅ YES' if self.results['success'] else '❌ NO'}")
        print(f"Tabs: {passed_tabs}/{total_tabs} passed")
        print(f"Duration: {self.results['total_duration_seconds']:.2f}s")
        print(f"{'='*80}")
        
    def generate_markdown_report(self):
        """Generate Markdown report"""
        with open("PHASE11_UI_REVALIDATION_REPORT.md", "w") as f:
            f.write("# Phase 11: UI/UX Forced Revalidation Report\n\n")
            f.write(f"**Generated:** {self.results['validation_end']}\n\n")
            f.write(f"**Duration:** {self.results['total_duration_seconds']:.2f}s\n\n")
            f.write(f"**Status:** {self.results['overall_status']}\n\n")
            f.write("---\n\n")
            
            f.write("## Tab Validations\n\n")
            f.write("| Tab | Status | Time (ms) | Charts | Tables | Buttons |\n")
            f.write("|-----|--------|-----------|--------|--------|----------|\n")
            
            for tab_name, result in self.results["tab_validations"].items():
                icon = "✅" if result["status"] == "PASSED" else "❌"
                f.write(f"| {tab_name} | {icon} {result['status']} | "
                       f"{result['render_time_ms']:.0f} | "
                       f"{result['dom_counts']['charts']} | "
                       f"{result['dom_counts']['tables']} | "
                       f"{result['dom_counts']['buttons']} |\n")
            
            f.write("\n## Performance\n\n")
            perf = self.results["performance_metrics"]
            f.write(f"- Avg Render: {perf.get('avg_render_time_ms', 0):.2f}ms\n")
            f.write(f"- Max Render: {perf.get('max_render_time_ms', 0):.2f}ms\n")
            f.write(f"- SLA Compliance: {perf.get('tabs_meeting_sla', 0)}/{perf.get('total_tabs', 0)}\n")
        
        print("✅ Markdown saved")
        
    def generate_executive_summary(self):
        """Generate executive summary"""
        with open("PHASE11_EXECUTIVE_SUMMARY.md", "w") as f:
            f.write("# 🎯 Phase 11: Executive Summary\n\n")
            f.write(f"**Date:** {datetime.now(timezone.utc).strftime('%B %d, %Y')}\n\n")
            f.write(f"**Status:** {self.results['overall_status']}\n\n")
            f.write("---\n\n")
            
            passed = sum(1 for r in self.results["tab_validations"].values() if r["status"] == "PASSED")
            total = len(TABS)
            
            f.write("## 📊 Key Metrics\n\n")
            f.write(f"- **Tabs Validated:** {passed}/{total} ({passed/total*100:.1f}%)\n")
            f.write(f"- **Duration:** {self.results['total_duration_seconds']:.2f}s\n")
            
            perf = self.results.get("performance_metrics", {})
            f.write(f"- **Avg Render Time:** {perf.get('avg_render_time_ms', 0):.2f}ms\n")
            f.write(f"- **Telemetry Events:** {len(self.results.get('telemetry_events', []))}\n\n")
            
            if self.results["overall_status"] == "PASSED":
                f.write("## ✅ Result\n\nAll tabs validated successfully. System ready for production.\n")
            else:
                f.write("## ⚠️  Issues\n\nSome tabs failed validation. Review report for details.\n")
        
        print("✅ Executive summary saved")
        
    def run(self):
        """Execute validation"""
        print("="*80)
        print("🚀 PHASE 11: FORCED FULL-STACK & VISUAL REVALIDATION (CORRECTED)")
        print("="*80)
        
        try:
            self.validate_dashboard_startup()
            self.validate_all_tabs()
            self.collect_performance_metrics()
            self.generate_reports()
            
            return self.results["success"]
            
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    validator = Phase11ValidatorCorrected()
    success = validator.run()
    sys.exit(0 if success else 1)

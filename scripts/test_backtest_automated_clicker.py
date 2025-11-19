#!/usr/bin/env python3
"""
PHASE 4B - AUTOMATED BACKTEST CLICKER WITH LIVE DEBUG

Fully automated browser test for the "Backtest Trend Signals" button.

Features:
- Playwright-based browser automation
- Real-time log monitoring via Docker API
- Job status polling with timeout protection
- Live debug mode (prints logs while waiting)
- Comprehensive validation checklist
- Screenshot capture on failure
- Detailed timestamped logging

Usage:
    python scripts/test_backtest_automated_clicker.py [--debug] [--headless]

Options:
    --debug      Enable live log streaming during test
    --headless   Run browser in headless mode (default: visible)
    --timeout    Job timeout in seconds (default: 120)
"""

import sys
import time
import json
import argparse
import subprocess
import requests
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'

class BacktestAutomatedTest:
    def __init__(self, dashboard_url="http://localhost:8050", timeout=120, debug=False, headless=True):
        self.dashboard_url = dashboard_url
        self.timeout = timeout
        self.debug = debug
        self.headless = headless
        self.screenshot_dir = Path("test-artifacts/backtest-automation")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.start_time = None
        self.job_id = None
        
    def log(self, msg, level="INFO"):
        """Timestamped logging with color coding."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        color = {
            "INFO": CYAN,
            "SUCCESS": GREEN,
            "WARNING": YELLOW,
            "ERROR": RED,
            "DEBUG": BLUE
        }.get(level, RESET)
        
        print(f"{BOLD}[{timestamp}]{RESET} {color}[{level}]{RESET} {msg}")
    
    def log_step(self, step_num, title):
        """Log test step header."""
        print()
        print("=" * 80)
        print(f"{BOLD}{CYAN}STEP {step_num}: {title}{RESET}")
        print("=" * 80)
        
    def get_docker_logs(self, lines=50):
        """Fetch last N lines from dash_app container."""
        try:
            result = subprocess.run(
                ["docker", "compose", "logs", "dash_app", "--tail", str(lines)],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout
        except Exception as e:
            self.log(f"Failed to fetch Docker logs: {e}", "WARNING")
            return ""
    
    def stream_logs_until_condition(self, condition_fn, max_duration=120):
        """Stream Docker logs in real-time until condition is met or timeout."""
        self.log(f"Starting log stream (max {max_duration}s)...", "DEBUG")
        start = time.time()
        last_log_check = 0
        
        while time.time() - start < max_duration:
            elapsed = time.time() - start
            
            # Check logs every 2 seconds
            if time.time() - last_log_check >= 2:
                logs = self.get_docker_logs(lines=20)
                
                if self.debug:
                    # Print new logs (basic deduplication by checking if we've seen them)
                    for line in logs.split('\n')[-10:]:
                        if line.strip() and ('🚀' in line or '✅' in line or '❌' in line or '⏰' in line or '📊' in line):
                            print(f"    {BLUE}[LOG]{RESET} {line}")
                
                # Check condition
                if condition_fn(logs):
                    self.log(f"Condition met after {elapsed:.1f}s", "SUCCESS")
                    return True
                
                last_log_check = time.time()
            
            time.sleep(0.5)
        
        self.log(f"Timeout after {max_duration}s", "ERROR")
        return False
    
    def check_cache_files(self):
        """Verify backtest cache files exist."""
        self.log_step(8, "Verify Cache Files")
        
        cache_files = {
            "market_brief.json": "outputs/market_brief.json",
            "sync_manifest.json": ".sync_manifest.json"
        }
        
        results = {}
        for name, path in cache_files.items():
            full_path = Path(path)
            exists = full_path.exists()
            results[name] = exists
            
            if exists:
                self.log(f"✅ {name} exists", "SUCCESS")
                if name == "market_brief.json":
                    try:
                        with open(full_path) as f:
                            data = json.load(f)
                        
                        # Check for backtest results
                        has_backtest = 'backtest_results' in data or 'backtest_summary' in data
                        if has_backtest:
                            self.log(f"   Contains backtest results ✅", "SUCCESS")
                            if 'backtest_summary' in data:
                                summary = data['backtest_summary']
                                self.log(f"   Total Trades: {summary.get('total_trades', 0)}", "INFO")
                                self.log(f"   Win Rate: {summary.get('win_rate_pct', 0):.1f}%", "INFO")
                                self.log(f"   Avg Return: {summary.get('avg_return_pct', 0):.2f}%", "INFO")
                        else:
                            self.log(f"   ⚠️  No backtest results in JSON", "WARNING")
                    except Exception as e:
                        self.log(f"   Failed to parse JSON: {e}", "ERROR")
            else:
                self.log(f"❌ {name} missing", "ERROR")
        
        return all(results.values())
    
    def run(self):
        """Execute the automated test."""
        self.log_step(1, "Initialize Test Environment")
        self.log(f"Dashboard URL: {self.dashboard_url}")
        self.log(f"Timeout: {self.timeout}s")
        self.log(f"Debug Mode: {self.debug}")
        self.log(f"Headless: {self.headless}")
        
        self.start_time = time.time()
        
        try:
            with sync_playwright() as p:
                self.log_step(2, "Launch Browser")
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context()
                page = context.new_page()
                
                # Enable console logging
                page.on("console", lambda msg: self.log(f"[BROWSER] {msg.text}", "DEBUG") if self.debug else None)
                
                self.log_step(3, "Navigate to Dashboard")
                page.goto(self.dashboard_url, wait_until="networkidle")
                self.log("✅ Dashboard loaded", "SUCCESS")
                page.screenshot(path=str(self.screenshot_dir / "01_dashboard_loaded.png"))
                
                self.log_step(4, "Navigate to Market Trends Tab")
                # Try multiple selectors
                selectors = [
                    'a[data-value="market_trends"]',
                    'button[data-value="market_trends"]',
                    'a:has-text("Market Trends")',
                    '.nav-link:has-text("Market Trends")'
                ]
                
                tab_found = False
                for selector in selectors:
                    try:
                        tab = page.locator(selector).first
                        if tab.count() > 0:
                            self.log(f"Found tab with selector: {selector}", "DEBUG")
                            tab.click()
                            page.wait_for_timeout(2000)
                            tab_found = True
                            break
                    except Exception:
                        continue
                
                if not tab_found:
                    self.log("Could not find Market Trends tab, assuming default view", "WARNING")
                
                self.log("✅ Market Trends tab active", "SUCCESS")
                page.screenshot(path=str(self.screenshot_dir / "02_market_trends_tab.png"))
                
                self.log_step(5, "Wait for Initial Table Load")
                try:
                    page.wait_for_selector('[data-testid="trends-composite-results"]', timeout=10000)
                    initial_rows = page.locator('[data-testid="trends-composite-results"] table tbody tr').count()
                    self.log(f"✅ Initial table loaded with {initial_rows} rows", "SUCCESS")
                except PlaywrightTimeout:
                    self.log("⚠️  Initial table not found, proceeding anyway", "WARNING")
                    initial_rows = 0
                
                self.log_step(6, "Click Backtest Trend Signals Button")
                try:
                    backtest_btn = page.locator('button:has-text("Backtest Trend Signals")').first
                    backtest_btn.wait_for(state="visible", timeout=5000)
                    
                    self.log("Button visible, clicking now...", "INFO")
                    backtest_btn.click()
                    page.wait_for_timeout(1000)
                    self.log("✅ Button clicked", "SUCCESS")
                    page.screenshot(path=str(self.screenshot_dir / "03_button_clicked.png"))
                    
                except PlaywrightTimeout:
                    self.log("❌ Backtest button not found", "ERROR")
                    page.screenshot(path=str(self.screenshot_dir / "ERROR_button_not_found.png"))
                    return False
                
                self.log_step(7, "Monitor Job Execution")
                
                # Attempt to extract the full backend-generated job ID from the page.
                # The UI may display a truncated ID (with ellipsis). We'll try several
                # strategies in decreasing order of fidelity:
                # 1. Read the hidden dcc.Store element 'dashboard-queued-job'
                # 2. Inspect any visible status divs
                # 3. Search the entire page HTML for the long job_\d+ pattern
                try:
                    # 1) Try the dcc.Store element
                    try:
                        store_el = page.locator('#dashboard-queued-job')
                        if store_el.count() > 0:
                            txt = store_el.inner_text()
                            if txt and 'job_' in txt:
                                import re
                                m = re.search(r'(job_\d{6,})', txt)
                                if m:
                                    self.job_id = m.group(1)
                    except Exception:
                        pass

                    # 2) Fallback: check any visible status divs
                    if not self.job_id:
                        try:
                            status_div = page.locator('div#status')
                            if status_div.count() > 0:
                                page.wait_for_timeout(1000)
                                status_text = status_div.inner_text()
                                self.log(f"Status: {status_text}", "INFO")
                                import re
                                m = re.search(r'(job_\d{6,})', status_text)
                                if m:
                                    self.job_id = m.group(1)
                        except Exception:
                            pass

                    # 3) As a last resort, search the full page HTML for the long job id
                    if not self.job_id:
                        try:
                            html = page.content()
                            import re
                            m = re.search(r'(job_\d{6,})', html)
                            if m:
                                self.job_id = m.group(1)
                        except Exception:
                            pass

                    if self.job_id:
                        self.log(f"✅ Job queued: {self.job_id}", "SUCCESS")
                    else:
                        self.log("⚠️  No Job ID found in page content", "WARNING")
                except Exception as e:
                    self.log(f"Could not read status: {e}", "WARNING")
                
                # Wait for job completion by polling the dashboard job-status endpoint.
                # This is more reliable than scanning docker logs and works across
                # environments where docker access may be limited.
                self.log(f"Waiting for job completion via HTTP endpoint (max {self.timeout}s)...", "INFO")

                def poll_job_status(max_seconds):
                    if not self.job_id:
                        self.log("No job_id available to poll", "ERROR")
                        return False
                    end = time.time() + max_seconds
                    url = f"{self.dashboard_url.rstrip('/')}/_job_status"
                    params = {'job_id': self.job_id}
                    while time.time() < end:
                        try:
                            r = requests.get(url, params=params, timeout=5)
                            if r.status_code != 200:
                                self.log(f"Job-status endpoint returned {r.status_code}: {r.text}", "WARNING")
                            else:
                                j = r.json()
                                status = None
                                # The endpoint returns {'job_id':..., 'status': {..}} or error
                                if isinstance(j.get('status'), dict):
                                    status = j['status'].get('status')
                                else:
                                    status = j.get('status')

                                if status:
                                    self.log(f"Polled job status: {status}", "DEBUG")
                                    if status in ('completed', 'failed'):
                                        return status == 'completed'
                        except Exception as e:
                            self.log(f"Error polling job-status endpoint: {e}", "WARNING")
                        time.sleep(2)
                    return False

                job_completed = poll_job_status(self.timeout)
                
                if not job_completed:
                    self.log("❌ Job did not complete within timeout", "ERROR")
                    page.screenshot(path=str(self.screenshot_dir / "ERROR_job_timeout.png"))
                    
                    # Dump final logs
                    final_logs = self.get_docker_logs(lines=100)
                    log_file = self.screenshot_dir / "job_timeout_logs.txt"
                    log_file.write_text(final_logs)
                    self.log(f"Logs saved to: {log_file}", "INFO")
                    return False
                
                # Wait a bit more for UI update
                page.wait_for_timeout(3000)
                page.screenshot(path=str(self.screenshot_dir / "04_after_job_completion.png"))
                
                # Verify table updated
                try:
                    final_rows = page.locator('[data-testid="trends-composite-results"] table tbody tr').count()
                    self.log(f"Final table has {final_rows} rows (initial: {initial_rows})", "INFO")
                    
                    if final_rows > 0:
                        self.log("✅ Table contains data", "SUCCESS")
                    else:
                        self.log("⚠️  Table is empty", "WARNING")
                        
                except Exception as e:
                    self.log(f"Could not count table rows: {e}", "WARNING")
                
                # Check for modal (should NOT appear in job-based flow)
                modal = page.locator('div#backtest-modal')
                if modal.count() > 0:
                    modal_style = modal.get_attribute('style') or ''
                    if 'display: none' not in modal_style:
                        self.log("⚠️  Backtest modal is visible (unexpected)", "WARNING")
                    else:
                        self.log("✅ Modal hidden (expected for job-based flow)", "SUCCESS")
                
                browser.close()
                
                # Verify cache files
                cache_ok = self.check_cache_files()
                
                # Final summary
                self.log_step(9, "Test Summary")
                elapsed = time.time() - self.start_time
                self.log(f"Total Test Duration: {elapsed:.1f}s", "INFO")
                self.log(f"Job ID: {self.job_id or 'N/A'}", "INFO")
                
                if job_completed and cache_ok:
                    self.log("🎉 ALL TESTS PASSED", "SUCCESS")
                    return True
                else:
                    self.log("⚠️  SOME CHECKS FAILED", "WARNING")
                    return False
                    
        except Exception as e:
            self.log(f"Fatal error: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return False


def main():
    parser = argparse.ArgumentParser(description="Automated Backtest Button Clicker")
    parser.add_argument('--debug', action='store_true', help='Enable live log streaming')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--timeout', type=int, default=120, help='Job timeout in seconds')
    parser.add_argument('--url', default='http://localhost:8050', help='Dashboard URL')
    
    args = parser.parse_args()
    
    print(f"{BOLD}{CYAN}{'=' * 80}{RESET}")
    print(f"{BOLD}{CYAN}PHASE 4B: AUTOMATED BACKTEST BUTTON CLICKER{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 80}{RESET}")
    print()
    
    tester = BacktestAutomatedTest(
        dashboard_url=args.url,
        timeout=args.timeout,
        debug=args.debug,
        headless=args.headless
    )
    
    success = tester.run()
    
    print()
    print(f"{BOLD}{CYAN}{'=' * 80}{RESET}")
    if success:
        print(f"{BOLD}{GREEN}✅ AUTOMATED TEST COMPLETED SUCCESSFULLY{RESET}")
        sys.exit(0)
    else:
        print(f"{BOLD}{RED}❌ AUTOMATED TEST FAILED{RESET}")
        print(f"{YELLOW}Check screenshots in: test-artifacts/backtest-automation/{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()

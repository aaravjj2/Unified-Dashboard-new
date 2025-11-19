#!/usr/bin/env python3
"""
PHASE 6D - AUTOMATED BACKTEST CLICKER WITH LOOP VALIDATION

Fully automated browser test with reliability loop and comprehensive reporting.

Features:
- Test mode activation (uses deterministic ticker set)
- Automatic retry with loop validation (up to 5 runs)
- HTTP job status polling for reliable completion detection
- Comprehensive artifact generation (screenshots, logs, metrics)
- Self-healing: auto-restart dashboard between runs
- Structured report generation (JSON + markdown)

Usage:
    python scripts/test_backtest_loop.py [--debug] [--headless] [--max-runs N]

Options:
    --debug        Enable verbose logging
    --headless     Run browser in headless mode (default: True)
    --max-runs     Maximum number of test runs (default: 5)
    --min-passes   Consecutive passes required (default: 3)
    --timeout      Job timeout per run in seconds (default: 120)
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


class BacktestLoopValidator:
    def __init__(self, dashboard_url="http://localhost:8050", timeout=120, debug=False, 
                 headless=True, max_runs=5, min_consecutive_passes=3, no_restart=False):
        self.dashboard_url = dashboard_url
        self.timeout = timeout
        self.debug = debug
        self.headless = headless
        self.max_runs = max_runs
        self.min_consecutive_passes = min_consecutive_passes
        self.no_restart = no_restart
        
        self.artifact_dir = Path("test-artifacts/backtest-automation")
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        
        self.runs = []
        self.consecutive_passes = 0
        self.start_time = None
        
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
    
    def restart_dashboard(self):
        """Restart the dash_app service with TEST_MODE enabled."""
        self.log("Restarting dash_app service with TEST_MODE=1...", "INFO")
        try:
            # Stop the service first
            subprocess.run(
                ["docker", "compose", "stop", "dash_app"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Start with TEST_MODE environment variable
            result = subprocess.run(
                ["docker", "compose", "run", "-d", "--name", "dash_app_test", 
                 "-e", "TEST_MODE=1", "-e", "JOB_TIME_LIMIT=300",
                 "--service-ports", "dash_app"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.log("✅ Dashboard restarted with TEST_MODE=1", "SUCCESS")
                time.sleep(8)  # Wait longer for service to be ready
                return True
            else:
                # Fallback: regular restart
                self.log("⚠️ TEST_MODE restart failed, trying regular restart", "WARNING")
                result = subprocess.run(
                    ["docker", "compose", "start", "dash_app"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    self.log("✅ Dashboard restarted (fallback)", "SUCCESS")
                    time.sleep(5)
                    return True
                else:
                    self.log(f"❌ Failed to restart: {result.stderr}", "ERROR")
                    return False
        except Exception as e:
            self.log(f"❌ Exception during restart: {e}", "ERROR")
            return False
    
    def get_docker_logs(self, lines=100):
        """Fetch last N lines from dash_app container."""
        try:
            result = subprocess.run(
                ["docker", "compose", "logs", "dash_app", "--tail", str(lines)],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout
        except Exception as e:
            self.log(f"Failed to fetch Docker logs: {e}", "WARNING")
            return ""
    
    def poll_job_status(self, job_id, max_seconds):
        """Poll job status endpoint until completion."""
        if not job_id:
            self.log("No job_id available to poll", "ERROR")
            return False, "no_job_id"
        
        end = time.time() + max_seconds
        url = f"{self.dashboard_url.rstrip('/')}/_job_status"
        params = {'job_id': job_id}
        
        last_status = None
        while time.time() < end:
            try:
                r = requests.get(url, params=params, timeout=5)
                if r.status_code != 200:
                    self.log(f"Job-status endpoint returned {r.status_code}", "WARNING")
                else:
                    j = r.json()
                    status = None
                    
                    # The endpoint returns {'job_id':..., 'status': {..}} or error
                    if isinstance(j.get('status'), dict):
                        status = j['status'].get('status')
                    else:
                        status = j.get('status')
                    
                    if status and status != last_status:
                        self.log(f"Job status: {status}", "DEBUG" if self.debug else "INFO")
                        last_status = status
                    
                    if status == 'completed':
                        return True, 'completed'
                    elif status == 'failed':
                        error = j.get('status', {}).get('error', 'Unknown error')
                        self.log(f"Job failed: {error}", "ERROR")
                        return False, f'failed: {error}'
                        
            except Exception as e:
                if self.debug:
                    self.log(f"Error polling job-status: {e}", "WARNING")
            
            time.sleep(2)
        
        return False, 'timeout'
    
    def extract_job_id(self, page):
        """Extract full backend job ID from page."""
        job_id = None
        
        # Strategy 1: Check job-status-display div (PHASE 6D enhancement)
        try:
            status_display = page.locator('#job-status-display')
            if status_display.count() > 0:
                txt = status_display.inner_text()
                if txt and 'job_' in txt:
                    import re
                    m = re.search(r'(job_\d{10,})', txt)
                    if m:
                        job_id = m.group(1)
                        if self.debug:
                            self.log(f"Found job ID in #job-status-display: {job_id}", "DEBUG")
        except Exception:
            pass
        
        # Strategy 2: Try dcc.Store element
        if not job_id:
            try:
                store_el = page.locator('#dashboard-queued-job')
                if store_el.count() > 0:
                    txt = store_el.inner_text()
                    if txt and 'job_' in txt:
                        import re
                        m = re.search(r'(job_\d{10,})', txt)
                        if m:
                            job_id = m.group(1)
            except Exception:
                pass
        
        # Strategy 3: Check status div
        if not job_id:
            try:
                status_div = page.locator('div#status')
                if status_div.count() > 0:
                    status_text = status_div.inner_text()
                    import re
                    m = re.search(r'(job_\d{10,})', status_text)
                    if m:
                        job_id = m.group(1)
            except Exception:
                pass
        
        # Strategy 4: Search full page HTML (last resort)
        if not job_id:
            try:
                html = page.content()
                import re
                # Look for job_ followed by at least 10 digits (millisecond timestamp)
                m = re.search(r'(job_\d{10,})', html)
                if m:
                    job_id = m.group(1)
            except Exception:
                pass
        
        return job_id
    
    def run_single_test(self, run_number):
        """Execute a single test run."""
        run_start = time.time()
        run_data = {
            'run_number': run_number,
            'start_time': datetime.now().isoformat(),
            'job_id': None,
            'status': 'not_started',
            'duration': 0,
            'error': None,
            'screenshots': []
        }
        
        self.log_step(f"{run_number}.1", f"Run #{run_number} - Launch Browser")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context()
                page = context.new_page()
                
                # Enable console logging in debug mode
                if self.debug:
                    page.on("console", lambda msg: self.log(f"[BROWSER] {msg.text}", "DEBUG"))
                
                self.log_step(f"{run_number}.2", f"Run #{run_number} - Navigate to Dashboard (Test Mode)")
                
                # PHASE 6D: Load dashboard first, then activate Market Trends tab programmatically
                test_url = f"{self.dashboard_url}?test_mode=short"
                
                try:
                    # Load with increased timeout and wait for body
                    page.goto(test_url, wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_selector('body', timeout=10000)
                    self.log("✅ Dashboard DOM loaded", "SUCCESS")
                    
                    screenshot_path = self.artifact_dir / f"run{run_number}_01_loaded.png"
                    page.screenshot(path=str(screenshot_path))
                    run_data['screenshots'].append(str(screenshot_path))
                    
                except PlaywrightTimeout:
                    self.log("❌ Dashboard navigation timeout", "ERROR")
                    screenshot_path = self.artifact_dir / f"run{run_number}_ERROR_navigation.png"
                    page.screenshot(path=str(screenshot_path))
                    run_data['screenshots'].append(str(screenshot_path))
                    run_data['status'] = 'navigation_timeout'
                    run_data['error'] = 'Page navigation timeout'
                    browser.close()
                    return run_data
                
                self.log_step(f"{run_number}.3", f"Run #{run_number} - Activate Market Trends Tab")
                
                # Try clicking Market Trends tab
                tab_activated = False
                try:
                    # Wait for tabs to render
                    page.wait_for_selector('div.tabs-container, [role="tablist"], .dash-tabs', timeout=10000)
                    
                    # Try multiple strategies to click Market Trends tab
                    selectors = [
                        'button:has-text("Market Trends")',
                        'a:has-text("Market Trends")',
                        '[data-value="market_trends"]',
                        '.tab:has-text("Market Trends")'
                    ]
                    
                    for selector in selectors:
                        try:
                            el = page.locator(selector).first
                            if el.count() > 0 and el.is_visible():
                                el.click()
                                page.wait_for_timeout(3000)  # Wait for tab content to load
                                tab_activated = True
                                self.log(f"✅ Clicked Market Trends tab via: {selector}", "SUCCESS")
                                break
                        except Exception:
                            continue
                            
                except Exception as e:
                    self.log(f"⚠️ Could not activate tab: {e}", "WARNING")
                
                if not tab_activated:
                    self.log("⚠️ Tab not explicitly activated, continuing anyway", "WARNING")
                
                self.log_step(f"{run_number}.4", f"Run #{run_number} - Click Backtest Button")
                
                # Take pre-click screenshot
                screenshot_path = self.artifact_dir / f"run{run_number}_02_before_click.png"
                page.screenshot(path=str(screenshot_path))
                run_data['screenshots'].append(str(screenshot_path))
                
                try:
                    backtest_btn = page.locator('button:has-text("Backtest Trend Signals")').first
                    backtest_btn.wait_for(state="visible", timeout=15000)
                    backtest_btn.click()
                    page.wait_for_timeout(2000)
                    self.log("✅ Button clicked", "SUCCESS")
                    
                    screenshot_path = self.artifact_dir / f"run{run_number}_03_clicked.png"
                    page.screenshot(path=str(screenshot_path))
                    run_data['screenshots'].append(str(screenshot_path))
                    
                except PlaywrightTimeout:
                    self.log("❌ Backtest button not found", "ERROR")
                    screenshot_path = self.artifact_dir / f"run{run_number}_ERROR_no_button.png"
                    page.screenshot(path=str(screenshot_path))
                    run_data['screenshots'].append(str(screenshot_path))
                    run_data['status'] = 'button_not_found'
                    run_data['error'] = 'Backtest button not found'
                    browser.close()
                    return run_data
                
                self.log_step(f"{run_number}.5", f"Run #{run_number} - Extract Job ID")
                
                # Wait a bit longer for job ID to appear
                page.wait_for_timeout(3000)
                
                job_id = self.extract_job_id(page)
                run_data['job_id'] = job_id
                
                if job_id:
                    self.log(f"✅ Job queued: {job_id}", "SUCCESS")
                else:
                    # Try one more time after additional wait
                    self.log("Job ID not found, waiting longer...", "INFO")
                    page.wait_for_timeout(5000)
                    job_id = self.extract_job_id(page)
                    run_data['job_id'] = job_id
                    
                    if job_id:
                        self.log(f"✅ Job queued (delayed): {job_id}", "SUCCESS")
                    else:
                        self.log("⚠️ No Job ID found after extended wait", "WARNING")
                        
                        # Debug: save page content for inspection
                        if self.debug:
                            html_path = self.artifact_dir / f"run{run_number}_page_content.html"
                            html_path.write_text(page.content())
                            self.log(f"Saved page HTML to {html_path} for debugging", "DEBUG")
                
                self.log_step(f"{run_number}.6", f"Run #{run_number} - Poll Job Status")
                
                if job_id:
                    success, result = self.poll_job_status(job_id, self.timeout)
                    
                    if success:
                        self.log(f"✅ Job completed successfully", "SUCCESS")
                        run_data['status'] = 'success'
                    else:
                        self.log(f"❌ Job failed or timed out: {result}", "ERROR")
                        run_data['status'] = f'job_{result}'
                        run_data['error'] = result
                else:
                    self.log("❌ Cannot poll without job ID", "ERROR")
                    run_data['status'] = 'no_job_id'
                    run_data['error'] = 'No job ID extracted'
                
                # Final screenshot
                page.wait_for_timeout(2000)
                screenshot_path = self.artifact_dir / f"run{run_number}_04_final.png"
                page.screenshot(path=str(screenshot_path))
                run_data['screenshots'].append(str(screenshot_path))
                
                browser.close()
                
        except Exception as e:
            self.log(f"❌ Fatal error in run {run_number}: {e}", "ERROR")
            run_data['status'] = 'exception'
            run_data['error'] = str(e)
            import traceback
            self.log(traceback.format_exc(), "ERROR")
        
        run_data['duration'] = time.time() - run_start
        run_data['end_time'] = datetime.now().isoformat()
        
        # Save run logs
        logs = self.get_docker_logs(lines=200)
        log_path = self.artifact_dir / f"run{run_number}_logs.txt"
        log_path.write_text(logs)
        
        return run_data
    
    def run_validation_loop(self):
        """Execute the validation loop until success criteria met."""
        self.start_time = time.time()
        
        print()
        print("=" * 80)
        print(f"{BOLD}{CYAN}PHASE 6D: AUTOMATED BACKTEST LOOP VALIDATION{RESET}")
        print("=" * 80)
        print()
        print(f"Configuration:")
        print(f"  Dashboard URL: {self.dashboard_url}")
        print(f"  Max Runs: {self.max_runs}")
        print(f"  Required Consecutive Passes: {self.min_consecutive_passes}")
        print(f"  Timeout per run: {self.timeout}s")
        print(f"  Headless: {self.headless}")
        print()
        
        for run_num in range(1, self.max_runs + 1):
            self.log(f"🚀 Starting run #{run_num}/{self.max_runs}", "INFO")
            
            # Restart dashboard before each run for clean state (unless no_restart flag is set)
            if not self.no_restart:
                if not self.restart_dashboard():
                    self.log("❌ Failed to restart dashboard, aborting", "ERROR")
                    break
            elif run_num == 1:
                self.log("🔧 Skipping dashboard restart (no_restart flag active)", "INFO")
            
            # Execute single test run
            run_data = self.run_single_test(run_num)
            self.runs.append(run_data)
            
            # Update consecutive pass counter
            if run_data['status'] == 'success':
                self.consecutive_passes += 1
                self.log(f"✅ Run #{run_num} PASSED (consecutive: {self.consecutive_passes}/{self.min_consecutive_passes})", "SUCCESS")
            else:
                self.consecutive_passes = 0
                self.log(f"❌ Run #{run_num} FAILED - {run_data.get('error', 'Unknown')}", "ERROR")
            
            # Check if we've met success criteria
            if self.consecutive_passes >= self.min_consecutive_passes:
                self.log(f"🎉 SUCCESS CRITERIA MET: {self.consecutive_passes} consecutive passes", "SUCCESS")
                break
            
            # Brief pause between runs
            if run_num < self.max_runs:
                time.sleep(3)
        
        # Generate final report
        self.generate_report()
        
        return self.consecutive_passes >= self.min_consecutive_passes
    
    def generate_report(self):
        """Generate comprehensive report and metrics."""
        total_duration = time.time() - (self.start_time or time.time())
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'configuration': {
                'dashboard_url': self.dashboard_url,
                'max_runs': self.max_runs,
                'min_consecutive_passes': self.min_consecutive_passes,
                'timeout_per_run': self.timeout,
                'headless': self.headless
            },
            'summary': {
                'total_runs': len(self.runs),
                'successful_runs': sum(1 for r in self.runs if r['status'] == 'success'),
                'failed_runs': sum(1 for r in self.runs if r['status'] != 'success'),
                'consecutive_passes': self.consecutive_passes,
                'success_criteria_met': self.consecutive_passes >= self.min_consecutive_passes,
                'total_duration': total_duration
            },
            'runs': self.runs
        }
        
        # Metrics
        successful_durations = [r['duration'] for r in self.runs if r['status'] == 'success']
        metrics = {
            'avg_duration': sum(successful_durations) / len(successful_durations) if successful_durations else 0,
            'min_duration': min(successful_durations) if successful_durations else 0,
            'max_duration': max(successful_durations) if successful_durations else 0,
            'error_categories': {}
        }
        
        for run in self.runs:
            if run['status'] != 'success':
                error_cat = run['status']
                metrics['error_categories'][error_cat] = metrics['error_categories'].get(error_cat, 0) + 1
        
        # Save JSON report
        report_path = self.artifact_dir / "report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        metrics_path = self.artifact_dir / "metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        # Generate markdown summary
        md_lines = [
            "# Phase 6D - Automated Backtest Loop Validation Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Configuration",
            f"- Dashboard URL: {self.dashboard_url}",
            f"- Max Runs: {self.max_runs}",
            f"- Required Consecutive Passes: {self.min_consecutive_passes}",
            f"- Timeout per run: {self.timeout}s",
            f"- Headless: {self.headless}",
            "",
            "## Summary",
            f"- Total Runs: {len(self.runs)}",
            f"- Successful Runs: {report['summary']['successful_runs']}",
            f"- Failed Runs: {report['summary']['failed_runs']}",
            f"- Consecutive Passes: {self.consecutive_passes}",
            f"- **Success Criteria Met:** {report['summary']['success_criteria_met']}",
            f"- Total Duration: {total_duration:.2f}s",
            "",
            "## Metrics",
            f"- Average Duration (successful): {metrics['avg_duration']:.2f}s",
            f"- Min Duration: {metrics['min_duration']:.2f}s",
            f"- Max Duration: {metrics['max_duration']:.2f}s",
            "",
            "## Error Categories"
        ]
        
        if metrics['error_categories']:
            for cat, count in metrics['error_categories'].items():
                md_lines.append(f"- {cat}: {count}")
        else:
            md_lines.append("No errors!")
        
        md_lines.extend([
            "",
            "## Run Details",
            ""
        ])
        
        for run in self.runs:
            status_icon = "✅" if run['status'] == 'success' else "❌"
            md_lines.append(f"### {status_icon} Run #{run['run_number']}")
            md_lines.append(f"- Status: {run['status']}")
            md_lines.append(f"- Duration: {run['duration']:.2f}s")
            md_lines.append(f"- Job ID: {run['job_id'] or 'N/A'}")
            if run['error']:
                md_lines.append(f"- Error: {run['error']}")
            md_lines.append(f"- Screenshots: {len(run['screenshots'])}")
            md_lines.append("")
        
        md_path = self.artifact_dir / "VALIDATION_REPORT.md"
        md_path.write_text('\n'.join(md_lines))
        
        self.log(f"📄 Report saved to: {report_path}", "INFO")
        self.log(f"📊 Metrics saved to: {metrics_path}", "INFO")
        self.log(f"📝 Markdown summary: {md_path}", "INFO")


def main():
    parser = argparse.ArgumentParser(description="Automated Backtest Loop Validator")
    parser.add_argument('--debug', action='store_true', help='Enable verbose logging')
    parser.add_argument('--headless', action='store_true', default=True, help='Run browser in headless mode')
    parser.add_argument('--max-runs', type=int, default=5, help='Maximum number of test runs')
    parser.add_argument('--min-passes', type=int, default=3, help='Consecutive passes required')
    parser.add_argument('--timeout', type=int, default=120, help='Job timeout per run in seconds')
    parser.add_argument('--url', default='http://localhost:8050', help='Dashboard URL')
    parser.add_argument('--no-restart', action='store_true', help='Skip dashboard restarts between runs (useful if TEST_MODE already set)')
    
    args = parser.parse_args()
    
    validator = BacktestLoopValidator(
        dashboard_url=args.url,
        timeout=args.timeout,
        debug=args.debug,
        headless=args.headless,
        max_runs=args.max_runs,
        min_consecutive_passes=args.min_passes,
        no_restart=args.no_restart
    )
    
    success = validator.run_validation_loop()
    
    print()
    print("=" * 80)
    if success:
        print(f"{BOLD}{GREEN}🎉 VALIDATION SUCCESSFUL{RESET}")
        print(f"{GREEN}Achieved {validator.consecutive_passes} consecutive passes{RESET}")
        sys.exit(0)
    else:
        print(f"{BOLD}{RED}❌ VALIDATION FAILED{RESET}")
        print(f"{RED}Only {validator.consecutive_passes} consecutive passes (need {validator.min_consecutive_passes}){RESET}")
        print(f"{YELLOW}Check artifacts in: test-artifacts/backtest-automation/{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()

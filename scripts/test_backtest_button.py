#!/usr/bin/env python3
"""
PHASE 4 BACKTEST BUTTON DIAGNOSTIC TEST

This script provides a step-by-step manual test workflow for the backtest button.
It verifies that the button triggers jobs, polling works, and Portfolio integrates signals.

Usage:
    python scripts/test_backtest_button.py
    
Requirements:
    - Docker containers running (dash_app on port 8050)
    - User must manually click buttons in browser
"""

import sys
import time
import json
from pathlib import Path

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(msg):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{msg.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")

def print_success(msg):
    print(f"{Colors.OKGREEN}✅ {msg}{Colors.ENDC}")

def print_warning(msg):
    print(f"{Colors.WARNING}⚠️  {msg}{Colors.ENDC}")

def print_error(msg):
    print(f"{Colors.FAIL}❌ {msg}{Colors.ENDC}")

def print_info(msg):
    print(f"{Colors.OKCYAN}ℹ️  {msg}{Colors.ENDC}")

def print_step(step_num, msg):
    print(f"\n{Colors.OKBLUE}{Colors.BOLD}STEP {step_num}: {msg}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'-' * 80}{Colors.ENDC}")

def wait_for_user(prompt="Press Enter to continue..."):
    input(f"\n{Colors.OKCYAN}{prompt}{Colors.ENDC}")

def check_docker_running():
    """Check if dash_app container is running."""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=dash_app", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            check=True
        )
        if "Up" in result.stdout:
            return True, result.stdout.strip()
        return False, "Container not running"
    except Exception as e:
        return False, str(e)

def check_dashboard_accessible():
    """Check if dashboard is accessible at http://localhost:8050."""
    import requests
    try:
        response = requests.get("http://localhost:8050", timeout=5)
        if response.status_code == 200:
            return True, f"Dashboard accessible (HTTP {response.status_code})"
        return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def check_file_exists(filepath):
    """Check if a file exists."""
    path = Path(filepath)
    if path.exists():
        size_kb = path.stat().st_size / 1024
        return True, f"File exists ({size_kb:.2f} KB)"
    return False, "File not found"

def read_json_file(filepath):
    """Read and parse JSON file."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return True, data
    except Exception as e:
        return False, str(e)

def get_docker_logs_tail(lines=50):
    """Get last N lines of Docker logs."""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "compose", "logs", "dash_app", "--tail", str(lines)],
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout
    except Exception as e:
        return False, str(e)

def search_logs_for_pattern(logs, pattern):
    """Search logs for a specific pattern."""
    lines = logs.split('\n')
    matches = [line for line in lines if pattern.lower() in line.lower()]
    return matches

def main():
    """Main test workflow."""
    print_header("PHASE 4 BACKTEST BUTTON DIAGNOSTIC TEST")
    
    print_info("This script guides you through manually testing the backtest button.")
    print_info("You will need to interact with the dashboard in your browser.")
    print_info("The script will verify logs and file outputs after each step.")
    
    wait_for_user("Press Enter to begin...")
    
    # =========================================================================
    # STEP 1: Pre-Flight Checks
    # =========================================================================
    print_step(1, "Pre-Flight Checks")
    
    print_info("Checking Docker container status...")
    running, status = check_docker_running()
    if running:
        print_success(f"Docker container running: {status}")
    else:
        print_error(f"Docker container not running: {status}")
        print_error("Please start the dashboard: docker compose up -d")
        sys.exit(1)
    
    print_info("Checking dashboard accessibility...")
    accessible, msg = check_dashboard_accessible()
    if accessible:
        print_success(f"Dashboard accessible: {msg}")
    else:
        print_error(f"Dashboard not accessible: {msg}")
        print_error("Please ensure dashboard is running on http://localhost:8050")
        sys.exit(1)
    
    print_success("Pre-flight checks passed!")
    
    # =========================================================================
    # STEP 2: Navigate to Market Trends Tab
    # =========================================================================
    print_step(2, "Navigate to Market Trends Tab")
    
    print_info("Please perform the following actions in your browser:")
    print_info("1. Open: http://localhost:8050")
    print_info("2. Click the 'Market Trends' tab")
    print_info("3. Verify the 'Backtest Trend Signals' button is visible (green button)")
    
    wait_for_user("Have you navigated to Market Trends tab? Press Enter when ready...")
    
    # =========================================================================
    # STEP 3: Click Backtest Trend Signals Button
    # =========================================================================
    print_step(3, "Click Backtest Trend Signals Button")
    
    print_info("Now click the 'Backtest Trend Signals' button and observe:")
    print_info("- Status message should appear: 'Running full analysis with backtest (Job ID: ...)...'")
    print_info("- Status bar should turn BLUE")
    print_info("- DO NOT close the browser tab")
    
    wait_for_user("Have you clicked the button? Press Enter after clicking...")
    
    # =========================================================================
    # STEP 4: Check Docker Logs for Callback Invocation
    # =========================================================================
    print_step(4, "Verify Callback Invocation in Docker Logs")
    
    print_info("Fetching Docker logs to verify callback was triggered...")
    success, logs = get_docker_logs_tail(100)
    
    if not success:
        print_error(f"Failed to fetch logs: {logs}")
        sys.exit(1)
    
    # Search for diagnostic markers
    callback_invoked = search_logs_for_pattern(logs, "BACKTEST CALLBACK INVOKED")
    button_clicked = search_logs_for_pattern(logs, "BACKTEST BUTTON CLICKED")
    job_queued = search_logs_for_pattern(logs, "Backtest job queued successfully")
    
    if callback_invoked:
        print_success(f"Callback invoked detected ({len(callback_invoked)} times)")
        for line in callback_invoked[:3]:  # Show first 3 matches
            print(f"    {line.strip()}")
    else:
        print_error("Callback invocation NOT detected in logs")
        print_error("This suggests the button click is not reaching the callback")
        print_error("Possible causes:")
        print_error("  1. Frontend JavaScript error")
        print_error("  2. Callback not registered")
        print_error("  3. Button HTML element misconfigured")
        sys.exit(1)
    
    if button_clicked:
        print_success(f"Button click detected ({len(button_clicked)} times)")
        for line in button_clicked[:2]:
            print(f"    {line.strip()}")
    else:
        print_warning("Button click marker not found (callback invoked but not via backtest-btn)")
    
    if job_queued:
        print_success(f"Job queued successfully ({len(job_queued)} times)")
        for line in job_queued[:2]:
            print(f"    {line.strip()}")
    else:
        print_error("Job NOT queued - backtest job submission failed")
        print_error("Check logs for error messages")
        sys.exit(1)
    
    print_success("Callback executed and job queued!")
    
    # =========================================================================
    # STEP 5: Wait for Job Completion
    # =========================================================================
    print_step(5, "Wait for Job Completion (30-60 seconds)")
    
    print_info("Waiting for background job to complete...")
    print_info("Expected time: 30-60 seconds")
    print_info("Watch the status bar in the dashboard - it should change to GREEN when done")
    
    wait_for_user("Press Enter once you see 'Job completed' message...")
    
    # Check logs for job completion
    success, logs = get_docker_logs_tail(150)
    if success:
        job_completed = search_logs_for_pattern(logs, "Job completed")
        sync_manifest = search_logs_for_pattern(logs, "Sync manifest updated: market_trends")
        
        if job_completed:
            print_success(f"Job completion detected in logs")
        else:
            print_warning("Job completion not detected in recent logs")
            print_warning("The job may still be running or may have failed")
        
        if sync_manifest:
            print_success(f"Sync manifest updated (Phase 4 integration working!)")
        else:
            print_warning("Sync manifest update not detected")
    
    # =========================================================================
    # STEP 6: Verify Cache Files Created
    # =========================================================================
    print_step(6, "Verify Cache Files Created")
    
    cache_dir = Path("/mnt/c/Aarav/fin_env/unified-dashboard/cache")
    
    # Check sync_manifest.json
    print_info("Checking sync_manifest.json...")
    exists, msg = check_file_exists(cache_dir / "sync_manifest.json")
    if exists:
        print_success(f"sync_manifest.json: {msg}")
        
        # Try to read it
        success, data = read_json_file(cache_dir / "sync_manifest.json")
        if success:
            if 'market_trends' in data:
                mt_data = data['market_trends']
                print_success(f"Market Trends entry found:")
                print(f"      last_updated: {mt_data.get('last_updated')}")
                print(f"      job_id: {mt_data.get('job_id')}")
                print(f"      status: {mt_data.get('status')}")
                print(f"      row_count: {mt_data.get('row_count', mt_data.get('metadata', {}).get('row_count'))}")
            else:
                print_warning("Market Trends entry NOT found in sync manifest")
        else:
            print_warning(f"Could not parse sync_manifest.json: {data}")
    else:
        print_error(f"sync_manifest.json: {msg}")
        print_error("This indicates the polling callback did not complete successfully")
    
    # Check market_brief.json
    print_info("Checking market_brief.json...")
    exists, msg = check_file_exists(cache_dir / "market_brief.json")
    if exists:
        print_success(f"market_brief.json: {msg}")
        
        # Try to read it
        success, data = read_json_file(cache_dir / "market_brief.json")
        if success:
            detailed = data.get('detailed', [])
            print_success(f"Contains {len(detailed)} ticker records")
            if detailed:
                first = detailed[0]
                print(f"      Sample ticker: {first.get('Ticker')}")
                print(f"      Signal: {first.get('Signal')}")
                print(f"      Momentum: {first.get('Momentum')}")
        else:
            print_warning(f"Could not parse market_brief.json: {data}")
    else:
        print_error(f"market_brief.json: {msg}")
    
    # =========================================================================
    # STEP 7: Verify Portfolio Tab Shows Signals
    # =========================================================================
    print_step(7, "Verify Portfolio Tab Shows Market Trends Signals")
    
    print_info("Now let's verify the Portfolio integration:")
    print_info("1. Click the 'Portfolio' tab")
    print_info("2. Click the 'Positions' subtab")
    print_info("3. Look for these NEW columns in the table:")
    print_info("     - Trend Signal (light blue background)")
    print_info("     - Momentum (light green background)")
    print_info("     - Sentiment (light yellow background)")
    print_info("     - Volatility (light red background)")
    print_info("4. Verify cells contain data (not all 'N/A')")
    
    wait_for_user("Can you see the Market Trends columns in Portfolio? Press Enter...")
    
    columns_visible = input(f"{Colors.OKCYAN}Do you see the 4 new columns? (yes/no): {Colors.ENDC}").strip().lower()
    
    if columns_visible == 'yes':
        print_success("Portfolio columns visible!")
        
        data_populated = input(f"{Colors.OKCYAN}Is data populated (not all 'N/A')? (yes/no): {Colors.ENDC}").strip().lower()
        
        if data_populated == 'yes':
            print_success("Portfolio data populated correctly!")
        else:
            print_warning("Columns visible but data not populated")
            print_warning("Check if sync_manifest.json has market_trends entry")
    else:
        print_error("Portfolio columns NOT visible")
        print_error("This indicates the Portfolio integration did not load signals")
        print_error("Check Docker logs for Portfolio tab activation")
    
    # =========================================================================
    # STEP 8: Check Docker Logs for Portfolio Sync
    # =========================================================================
    print_step(8, "Verify Portfolio Sync in Docker Logs")
    
    print_info("Fetching Docker logs to verify Portfolio sync...")
    success, logs = get_docker_logs_tail(100)
    
    if success:
        portfolio_synced = search_logs_for_pattern(logs, "Portfolio synced with Market Trends")
        signals_loaded = search_logs_for_pattern(logs, "Loaded Market Trends signals")
        
        if portfolio_synced:
            print_success(f"Portfolio sync confirmed in logs")
            for line in portfolio_synced[:2]:
                print(f"    {line.strip()}")
        else:
            print_warning("Portfolio sync not detected in logs")
        
        if signals_loaded:
            print_success(f"Signals loaded by Portfolio")
            for line in signals_loaded[:2]:
                print(f"    {line.strip()}")
        else:
            print_warning("Signal loading not detected in logs")
    
    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print_header("TEST SUMMARY")
    
    print(f"\n{Colors.BOLD}Checklist:{Colors.ENDC}")
    print(f"  ✓ Docker container running")
    print(f"  ✓ Dashboard accessible")
    print(f"  ✓ Backtest callback invoked")
    print(f"  ✓ Job queued successfully")
    
    if exists:  # sync_manifest.json check
        print(f"  ✓ sync_manifest.json created")
    else:
        print(f"  ✗ sync_manifest.json NOT created")
    
    if columns_visible == 'yes':
        print(f"  ✓ Portfolio columns visible")
    else:
        print(f"  ✗ Portfolio columns NOT visible")
    
    if columns_visible == 'yes' and data_populated == 'yes':
        print(f"  ✓ Portfolio data populated")
        print_success("\n🎉 PHASE 4 INTEGRATION SUCCESSFUL!")
        print_success("Backtest button works correctly and Portfolio shows Market Trends signals.")
    else:
        print(f"  ✗ Portfolio data NOT populated or columns missing")
        print_warning("\n⚠️  PHASE 4 INTEGRATION INCOMPLETE")
        print_warning("Some issues detected - review logs for details.")
    
    print(f"\n{Colors.BOLD}Next Steps:{Colors.ENDC}")
    print(f"  1. Review Docker logs: docker compose logs dash_app --tail 200")
    print(f"  2. Check cache files in: {cache_dir}")
    print(f"  3. Run integration tests: pytest tests/test_portfolio_reads_signals_from_trends.py")
    
    print(f"\n{Colors.OKGREEN}{Colors.BOLD}Test complete!{Colors.ENDC}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Test interrupted by user.{Colors.ENDC}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{Colors.FAIL}Test failed with exception: {e}{Colors.ENDC}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

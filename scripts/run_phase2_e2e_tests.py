#!/usr/bin/env python3
"""
Phase 2 E2E Test Runner
Orchestrates Docker startup, health check, and 3-iteration Playwright tests
"""

import subprocess
import time
import sys
import requests
from pathlib import Path

# Configuration
DASHBOARD_URL = "http://localhost:8050"
MAX_WAIT_SECONDS = 90
HEALTH_CHECK_INTERVAL = 3

def run_command(cmd, check=True):
    """Run shell command and return output"""
    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"❌ Command failed: {result.stderr}")
        sys.exit(1)
    return result

def check_dashboard_health():
    """Check if dashboard is responding"""
    try:
        response = requests.get(DASHBOARD_URL, timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    print("="*60)
    print("Phase 2 E2E Testing - 3-Iteration Validation Loop")
    print("="*60)
    
    # Step 1: Check Docker
    print("\n1️⃣ Checking Docker...")
    run_command("docker --version")
    
    # Step 2: Stop existing containers
    print("\n2️⃣ Cleaning up existing containers...")
    run_command("docker-compose down", check=False)
    time.sleep(2)
    
    # Step 3: Start dashboard
    print("\n3️⃣ Starting dashboard via Docker Compose...")
    run_command("docker-compose up --build -d dash_app")
    
    # Step 4: Wait for health check
    print(f"\n4️⃣ Waiting for dashboard (max {MAX_WAIT_SECONDS}s)...")
    elapsed = 0
    while elapsed < MAX_WAIT_SECONDS:
        if check_dashboard_health():
            print(f"✅ Dashboard is healthy! (took {elapsed}s)")
            break
        print(f"   ⏳ Waiting... ({elapsed}s/{MAX_WAIT_SECONDS}s)")
        time.sleep(HEALTH_CHECK_INTERVAL)
        elapsed += HEALTH_CHECK_INTERVAL
    else:
        print(f"❌ Dashboard failed to start after {MAX_WAIT_SECONDS}s")
        print("\nLogs:")
        run_command("docker-compose logs dash_app | tail -50", check=False)
        sys.exit(1)
    
    # Step 5: Install Playwright if needed
    print("\n5️⃣ Ensuring Playwright is installed...")
    run_command("pip install -q playwright pytest-playwright", check=False)
    run_command("python -m playwright install chromium", check=False)
    
    # Step 6: Run E2E tests
    print("\n6️⃣ Running Phase 2 E2E tests (3 iterations)...")
    print("="*60)
    
    # Run phase2 test script
    test_result = run_command("python tests/phase2_comprehensive_e2e.py", check=False)
    
    if test_result.returncode != 0:
        print(f"\n⚠️ Tests completed with some failures")
        print(test_result.stderr)
    else:
        print(f"\n✅ All tests passed!")
    
    # Step 7: Show results summary
    print("\n7️⃣ Test Results Summary")
    print("="*60)
    
    # Check for aggregate report
    aggregate_report = Path("outputs/phase2_e2e/reports/aggregate_report.md")
    if aggregate_report.exists():
        print(aggregate_report.read_text()[:1500])
        print("\n... (see full report in outputs/phase2_e2e/reports/)")
    else:
        print("⚠️ Aggregate report not found")
    
    # Step 8: Ask about cleanup
    print("\n8️⃣ Cleanup")
    print("="*60)
    response = input("Stop dashboard container? (y/N): ").strip().lower()
    if response == 'y':
        print("Stopping dashboard...")
        run_command("docker-compose down")
        print("✅ Cleanup complete")
    else:
        print(f"ℹ️ Dashboard still running on {DASHBOARD_URL}")
        print("   To stop: docker-compose down")
    
    print("\n🎉 Phase 2 Testing Complete!")
    print(f"   Reports: outputs/phase2_e2e/reports/")
    print(f"   Screenshots: outputs/phase2_e2e/screenshots/")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

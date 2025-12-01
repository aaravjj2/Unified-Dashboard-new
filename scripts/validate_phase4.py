"""
Phase 4 Manual Validation Script

This script validates the complete Phase 4 integration by:
1. Running a Market Trends backtest analysis
2. Verifying sync_manifest.json is created
3. Validating Portfolio can load the signals

Usage:
    python scripts/validate_phase4.py

Requirements:
    - Docker container must be running
    - Alpaca API credentials must be configured
"""

import os
import sys
import time
import json
import requests
from pathlib import Path
from datetime import datetime

# Colors for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_step(step, message):
    """Print formatted step message."""
    print(f"\n{BLUE}[STEP {step}]{RESET} {message}")

def print_success(message):
    """Print success message."""
    print(f"{GREEN}✅ {message}{RESET}")

def print_warning(message):
    """Print warning message."""
    print(f"{YELLOW}⚠️  {message}{RESET}")

def print_error(message):
    """Print error message."""
    print(f"{RED}❌ {message}{RESET}")

def wait_for_job_completion(job_id, max_wait=120):
    """Poll for job completion."""
    print(f"   Polling job {job_id[:12]}... (max {max_wait}s)")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        # Check manifest file directly
        cache_dir = Path(__file__).parent.parent / 'cache'
        manifest_path = cache_dir / 'sync_manifest.json'
        
        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            if 'market_trends' in manifest:
                trends_meta = manifest['market_trends']
                if trends_meta.get('job_id') == job_id and trends_meta.get('status') == 'completed':
                    print_success(f"Job completed in {int(time.time() - start_time)}s")
                    return True
        
        time.sleep(2)
        print('.', end='', flush=True)
    
    print()
    print_error(f"Job did not complete within {max_wait}s")
    return False

def main():
    """Main validation workflow."""
    print(f"\n{'='*60}")
    print(f"{BLUE}Phase 4: Portfolio + Market Trends Integration Validation{RESET}")
    print(f"{'='*60}\n")
    
    # Step 1: Check Docker container is running
    print_step(1, "Checking Docker container status")
    result = os.system('docker ps | grep dash_app > /dev/null 2>&1')
    if result != 0:
        print_error("Docker container 'dash_app' is not running")
        print("   Run: docker compose up -d dash_app")
        return 1
    print_success("Docker container is running")
    
    # Step 2: Check dashboard is accessible
    print_step(2, "Checking dashboard accessibility")
    try:
        response = requests.get('http://localhost:8050', timeout=5)
        if response.status_code == 200:
            print_success("Dashboard is accessible at http://localhost:8050")
        else:
            print_warning(f"Dashboard returned status code {response.status_code}")
    except requests.exceptions.RequestException as e:
        print_error(f"Cannot connect to dashboard: {e}")
        print("   Ensure container is running and port 8050 is accessible")
        return 1
    
    # Step 3: Trigger Market Trends backtest
    print_step(3, "Triggering Market Trends backtest analysis")
    print("   This will run a full analysis with backtest for default tickers")
    print("   Navigate to: http://localhost:8050")
    print("   Click 'Market Trends' tab → 'Backtest Trend Signals' button")
    print()
    print("   Waiting for user to trigger backtest...")
    print(f"   {YELLOW}Press ENTER after clicking 'Backtest Trend Signals'{RESET}")
    input()
    
    # Step 4: Wait for sync_manifest.json
    print_step(4, "Waiting for sync_manifest.json creation")
    cache_dir = Path(__file__).parent.parent / 'cache'
    manifest_path = cache_dir / 'sync_manifest.json'
    
    max_wait = 180  # 3 minutes
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        if manifest_path.exists():
            print_success(f"Sync manifest created: {manifest_path}")
            
            # Read and display
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            if 'market_trends' in manifest:
                trends_meta = manifest['market_trends']
                print(f"   Job ID: {trends_meta.get('job_id')}")
                print(f"   Status: {trends_meta.get('status')}")
                print(f"   Last Updated: {trends_meta.get('last_updated')}")
                print(f"   Tickers: {len(trends_meta.get('tickers', []))}")
                
                if trends_meta.get('status') == 'completed':
                    print_success("Market Trends job completed successfully")
                    break
            else:
                print_warning("Manifest exists but no market_trends data yet")
        
        time.sleep(2)
        print('.', end='', flush=True)
    else:
        print()
        print_error(f"Manifest not created within {max_wait}s")
        print("   Check Docker logs: docker compose logs dash_app --tail 100")
        return 1
    
    # Step 5: Verify market_brief.json exists
    print_step(5, "Verifying market_brief.json cache")
    market_brief_path = cache_dir / 'market_brief.json'
    
    if not market_brief_path.exists():
        print_error(f"Market brief cache not found: {market_brief_path}")
        return 1
    
    with open(market_brief_path, 'r') as f:
        brief_data = json.load(f)
    
    detailed = brief_data.get('detailed', [])
    print_success(f"Market brief cache found: {len(detailed)} tickers")
    
    # Show sample
    if detailed:
        sample = detailed[0]
        ticker = sample.get('Ticker') or sample.get('ticker')
        signal = sample.get('Signal') or sample.get('signal')
        print(f"   Sample: {ticker} → {signal}")
    
    # Step 6: Validate Portfolio integration
    print_step(6, "Validating Portfolio integration")
    print("   Navigate to 'Portfolio' tab → 'Positions' subtab")
    print("   Expected columns: Symbol, Qty, Weight %, Trend Signal, Momentum, Sentiment, Volatility")
    print()
    print("   Do you see the Market Trends columns? (y/n): ", end='')
    user_response = input().strip().lower()
    
    if user_response == 'y':
        print_success("Portfolio successfully displays Market Trends signals")
    else:
        print_error("Portfolio did not load Market Trends signals")
        print("   Check logs: docker compose logs dash_app --tail 100 | grep 'Market Trends'")
        return 1
    
    # Step 7: Check dependency tracking
    print_step(7, "Checking dependency tracking in manifest")
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    if 'portfolio' in manifest:
        portfolio_meta = manifest['portfolio']
        if 'last_synced_with_market_trends' in portfolio_meta:
            print_success("Portfolio dependency tracked in manifest")
            print(f"   Last Synced: {portfolio_meta['last_synced_with_market_trends']}")
            print(f"   Dependent Job: {portfolio_meta.get('dependent_on_job')}")
        else:
            print_warning("Portfolio in manifest but no sync timestamp")
            print("   This is OK if Portfolio tab wasn't activated yet")
    else:
        print_warning("Portfolio not in manifest yet")
        print("   Dependency will be marked when Portfolio tab is activated")
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"{GREEN}Phase 4 Validation Complete!{RESET}")
    print(f"{'='*60}\n")
    print_success("Market Trends backtest completed")
    print_success("Sync manifest created and populated")
    print_success("Market brief cache populated")
    print_success("Portfolio displays Market Trends signals")
    
    print(f"\n{BLUE}Next Steps:{RESET}")
    print("1. Test Portfolio optimization auto-refresh (Task 5)")
    print("2. Create E2E tests for cross-tab sync")
    print("3. Document the integration workflow")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

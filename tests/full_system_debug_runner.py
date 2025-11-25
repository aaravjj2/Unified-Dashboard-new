#!/usr/bin/env python3
"""
Full System Debug Runner for Market Trends and Portfolio Dashboards
Executes 4-phase validation loop with comprehensive logging and snapshot capture
"""
import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime

# Setup paths
DASH_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(DASH_ROOT))
sys.path.insert(0, str(DASH_ROOT / 'financial_dashboard'))

# Create debug log directory
DEBUG_DIR = DASH_ROOT / 'tests' / 'logs' / 'full_system_debug'
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(DEBUG_DIR / 'full_system_debug.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def phase1_observation():
    """Phase 1: Enable debug logging and capture baseline state"""
    logger.info("=" * 80)
    logger.info("PHASE 1: OBSERVATION - Capturing baseline state")
    logger.info("=" * 80)
    
    results = {
        'phase': 1,
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }
    
    # Check if server is running
    import requests
    try:
        resp = requests.get('http://127.0.0.1:8050/', timeout=5)
        results['checks']['server_running'] = True
        logger.info("✅ Server is running on http://127.0.0.1:8050/")
    except Exception as e:
        results['checks']['server_running'] = False
        logger.error(f"❌ Server not running: {e}")
        logger.warning("Please start the server before running debug validation")
        return results
    
    # Check callback registration
    try:
        resp = requests.get('http://127.0.0.1:8050/_dash-dependencies', timeout=5)
        deps = resp.json()
        results['checks']['total_callbacks'] = len(deps)
        logger.info(f"✅ Total callbacks registered: {len(deps)}")
        
        # Check for Market Trends callbacks
        mt_callbacks = [d for d in deps if any(
            'market-trends' in str(d.get(k, '')) or 'trends' in str(d.get(k, ''))
            for k in ['output', 'inputs', 'state']
        )]
        results['checks']['market_trends_callbacks'] = len(mt_callbacks)
        logger.info(f"✅ Market Trends callbacks: {len(mt_callbacks)}")
        
        # Check for Portfolio callbacks
        pf_callbacks = [d for d in deps if any(
            'portfolio' in str(d.get(k, ''))
            for k in ['output', 'inputs', 'state']
        )]
        results['checks']['portfolio_callbacks'] = len(pf_callbacks)
        logger.info(f"✅ Portfolio callbacks: {len(pf_callbacks)}")
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch callbacks: {e}")
        results['checks']['callbacks_error'] = str(e)
    
    # Check API endpoints
    for endpoint in ['/api/portfolio_summary', '/api/weekly_picks', '/api/monthly_picks']:
        try:
            resp = requests.get(f'http://127.0.0.1:8050{endpoint}', timeout=10)
            results['checks'][f'api_{endpoint}'] = {
                'status': resp.status_code,
                'success': resp.status_code == 200
            }
            if resp.status_code == 200:
                logger.info(f"✅ API {endpoint} responding")
            else:
                logger.warning(f"⚠️  API {endpoint} returned {resp.status_code}")
        except Exception as e:
            logger.error(f"❌ API {endpoint} failed: {e}")
            results['checks'][f'api_{endpoint}'] = {'error': str(e)}
    
    # Check cache files
    cache_dir = DASH_ROOT / 'cache'
    if cache_dir.exists():
        cache_files = list(cache_dir.glob('*.json'))
        results['checks']['cache_files'] = [f.name for f in cache_files]
        logger.info(f"✅ Found {len(cache_files)} cache files")
    
    # Save Phase 1 results
    with open(DEBUG_DIR / 'phase1_observation.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info("✅ Phase 1 complete - results saved to phase1_observation.json")
    return results

def phase2_interactive_validation():
    """Phase 2: Run clicker and snapshot tests"""
    logger.info("=" * 80)
    logger.info("PHASE 2: INTERACTIVE VALIDATION - Running tests")
    logger.info("=" * 80)
    
    results = {
        'phase': 2,
        'timestamp': datetime.now().isoformat(),
        'tests': {}
    }
    
    # Check if Playwright is available
    try:
        from playwright.sync_api import sync_playwright
        results['playwright_available'] = True
    except ImportError:
        logger.warning("⚠️  Playwright not available - skipping browser tests")
        results['playwright_available'] = False
    
    # Run Market Trends snapshot
    logger.info("Running Market Trends snapshot test...")
    try:
        from tests.test_market_trends_snapshot import run_market_trends_snapshot
        mt_result = run_market_trends_snapshot()
        results['tests']['market_trends_snapshot'] = mt_result
        logger.info(f"✅ Market Trends snapshot: {mt_result.get('status', 'unknown')}")
    except Exception as e:
        logger.error(f"❌ Market Trends snapshot failed: {e}")
        results['tests']['market_trends_snapshot'] = {'error': str(e)}
    
    # Run Portfolio snapshot
    logger.info("Running Portfolio snapshot test...")
    try:
        import subprocess
        proc = subprocess.run(
            ['python3', 'tools/portfolio_subtabs_snapshot.py'],
            cwd=str(DASH_ROOT),
            capture_output=True,
            text=True,
            timeout=60
        )
        results['tests']['portfolio_snapshot'] = {
            'returncode': proc.returncode,
            'stdout': proc.stdout[-2000:],  # Last 2000 chars
            'stderr': proc.stderr[-1000:] if proc.stderr else ''
        }
        if proc.returncode == 0:
            logger.info("✅ Portfolio snapshot completed")
        else:
            logger.warning(f"⚠️  Portfolio snapshot exited with code {proc.returncode}")
    except Exception as e:
        logger.error(f"❌ Portfolio snapshot failed: {e}")
        results['tests']['portfolio_snapshot'] = {'error': str(e)}
    
    # Save Phase 2 results
    with open(DEBUG_DIR / 'phase2_validation.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info("✅ Phase 2 complete - results saved to phase2_validation.json")
    return results

def phase3_remediation(phase2_results):
    """Phase 3: Analyze issues and suggest remediations"""
    logger.info("=" * 80)
    logger.info("PHASE 3: REMEDIATION - Analyzing issues")
    logger.info("=" * 80)
    
    issues = []
    remediations = []
    
    # Analyze Phase 2 results
    tests = phase2_results.get('tests', {})
    
    # Check Market Trends
    mt_snap = tests.get('market_trends_snapshot', {})
    if 'error' in mt_snap or mt_snap.get('status') != 'success':
        issues.append("Market Trends snapshot test failed or errored")
        remediations.append("Check Market Trends tab callbacks and data sources")
    
    # Check Portfolio
    pf_snap = tests.get('portfolio_snapshot', {})
    if 'error' in pf_snap or pf_snap.get('returncode', 1) != 0:
        issues.append("Portfolio snapshot test failed")
        remediations.append("Check Portfolio subtab callbacks and data store population")
    
    results = {
        'phase': 3,
        'timestamp': datetime.now().isoformat(),
        'issues_found': len(issues),
        'issues': issues,
        'recommended_remediations': remediations
    }
    
    if issues:
        logger.warning(f"⚠️  Found {len(issues)} issues requiring remediation:")
        for i, issue in enumerate(issues, 1):
            logger.warning(f"  {i}. {issue}")
        logger.info("Recommended remediations:")
        for i, rem in enumerate(remediations, 1):
            logger.info(f"  {i}. {rem}")
    else:
        logger.info("✅ No critical issues found!")
    
    # Save Phase 3 results
    with open(DEBUG_DIR / 'phase3_remediation.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return results

def phase4_loop_validation(max_iterations=3):
    """Phase 4: Loop until success or max iterations"""
    logger.info("=" * 80)
    logger.info(f"PHASE 4: VALIDATION LOOP - Max {max_iterations} iterations")
    logger.info("=" * 80)
    
    all_results = []
    
    for iteration in range(1, max_iterations + 1):
        logger.info(f"\n{'=' * 80}")
        logger.info(f"ITERATION {iteration}/{max_iterations}")
        logger.info(f"{'=' * 80}\n")
        
        # Run validation
        p2_results = phase2_interactive_validation()
        p3_results = phase3_remediation(p2_results)
        
        iter_result = {
            'iteration': iteration,
            'timestamp': datetime.now().isoformat(),
            'phase2': p2_results,
            'phase3': p3_results
        }
        all_results.append(iter_result)
        
        # Check success criteria
        issues = p3_results.get('issues_found', 999)
        if issues == 0:
            logger.info(f"✅ SUCCESS: All validations passed in iteration {iteration}")
            break
        else:
            logger.warning(f"⚠️  Iteration {iteration} found {issues} issues")
            if iteration < max_iterations:
                logger.info(f"Retrying... ({iteration + 1}/{max_iterations})")
                time.sleep(2)
    
    # Save final loop results
    final_results = {
        'phase': 4,
        'total_iterations': len(all_results),
        'max_iterations': max_iterations,
        'final_status': 'success' if all_results[-1]['phase3']['issues_found'] == 0 else 'incomplete',
        'iterations': all_results
    }
    
    with open(DEBUG_DIR / 'phase4_loop_results.json', 'w') as f:
        json.dump(final_results, f, indent=2)
    
    return final_results

def generate_final_report(p1, p2, p3, p4):
    """Generate comprehensive validation report"""
    logger.info("=" * 80)
    logger.info("GENERATING FINAL REPORT")
    logger.info("=" * 80)
    
    report_lines = [
        "=" * 80,
        "FULL SYSTEM DEBUG AND VALIDATION REPORT",
        "=" * 80,
        f"Generated: {datetime.now().isoformat()}",
        "",
        "PHASE 1: OBSERVATION",
        "-" * 80,
        f"Server Running: {p1['checks'].get('server_running', 'unknown')}",
        f"Total Callbacks: {p1['checks'].get('total_callbacks', 'unknown')}",
        f"Market Trends Callbacks: {p1['checks'].get('market_trends_callbacks', 'unknown')}",
        f"Portfolio Callbacks: {p1['checks'].get('portfolio_callbacks', 'unknown')}",
        "",
        "PHASE 4: VALIDATION LOOP",
        "-" * 80,
        f"Total Iterations: {p4['total_iterations']}",
        f"Final Status: {p4['final_status'].upper()}",
        "",
        "FINAL ASSESSMENT",
        "-" * 80
    ]
    
    final_issues = p4['iterations'][-1]['phase3']['issues_found']
    if final_issues == 0:
        report_lines.append("✅ ALL VALIDATIONS PASSED")
        report_lines.append("Market Trends and Portfolio dashboards are fully functional.")
    else:
        report_lines.append(f"⚠️  {final_issues} ISSUES REMAIN")
        report_lines.append("See phase3_remediation.json for recommended fixes.")
    
    report_lines.extend([
        "",
        "ARTIFACTS GENERATED",
        "-" * 80,
        "- phase1_observation.json",
        "- phase2_validation.json",
        "- phase3_remediation.json",
        "- phase4_loop_results.json",
        "- full_system_debug.log",
        "- market_trends_clicker_snapshots/",
        "- portfolio_snapshots/",
        "",
        "=" * 80
    ])
    
    report = "\n".join(report_lines)
    
    # Save report
    with open(DEBUG_DIR / 'playwright_validation_report.txt', 'w') as f:
        f.write(report)
    
    logger.info(report)
    logger.info(f"\n✅ Full report saved to {DEBUG_DIR / 'playwright_validation_report.txt'}")
    
    return report

def main():
    """Execute full 4-phase validation loop"""
    logger.info("Starting Full System Debug and Validation")
    logger.info(f"Debug artifacts will be saved to: {DEBUG_DIR}")
    
    try:
        # Phase 1: Observation
        p1_results = phase1_observation()
        
        if not p1_results['checks'].get('server_running'):
            logger.error("❌ Server not running - cannot proceed with validation")
            logger.info("Please start the server and re-run this script")
            return 1
        
        # Phase 2 & 3: Single validation pass
        p2_results = phase2_interactive_validation()
        p3_results = phase3_remediation(p2_results)
        
        # Phase 4: Loop validation
        p4_results = phase4_loop_validation(max_iterations=2)
        
        # Generate final report
        final_report = generate_final_report(p1_results, p2_results, p3_results, p4_results)
        
        # Exit code based on final status
        if p4_results['final_status'] == 'success':
            logger.info("✅ VALIDATION COMPLETE - All tests passed!")
            return 0
        else:
            logger.warning("⚠️  VALIDATION INCOMPLETE - Some issues remain")
            return 1
        
    except Exception as e:
        logger.exception(f"❌ Fatal error during validation: {e}")
        return 2

if __name__ == '__main__':
    sys.exit(main())

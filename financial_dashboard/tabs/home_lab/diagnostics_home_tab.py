"""
Home Lab - Diagnostic Script

6-Phase validation pipeline for Home Tab:
1. Environment check (dash + data folders)
2. Layout creation integrity
3. Callback registration
4. Portfolio data connectivity
5. Metrics cache verification
6. Cross-lab status polling

Outputs:
- home_tab_diagnostic.json (JSON summary)
- home_tab_startup.log (detailed logs)
- home_tab_validation_report.md (markdown report)
"""

import logging
import json
import sys
from pathlib import Path
from datetime import datetime

# Setup logging
log_file = Path(__file__).parent.parent.parent.parent / "home_tab_startup.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


# ============================================================================
# PHASE 1: ENVIRONMENT CHECK
# ============================================================================

def check_environment():
    """Verify required packages and folder structure."""
    logger.info("="* 60)
    logger.info("PHASE 1: Environment Check")
    logger.info("="* 60)
    
    results = {'status': 'PASS', 'details': []}
    
    try:
        # Check required imports
        import dash
        import dash_bootstrap_components as dbc
        import plotly
        import pandas as pd
        
        results['details'].append({
            'check': 'Required packages',
            'status': 'PASS',
            'message': f'dash={dash.__version__}, dbc, plotly, pandas available'
        })
        
        # Check folder structure
        base_path = Path(__file__).parent.parent.parent.parent
        required_folders = ['cache', 'outputs', 'financial_dashboard/tabs/home_lab']
        
        for folder in required_folders:
            folder_path = base_path / folder
            if folder_path.exists():
                results['details'].append({
                    'check': f'Folder: {folder}',
                    'status': 'PASS',
                    'message': f'Found at {folder_path}'
                })
            else:
                results['details'].append({
                    'check': f'Folder: {folder}',
                    'status': 'WARN',
                    'message': f'Not found at {folder_path}'
                })
        
    except Exception as e:
        results['status'] = 'FAIL'
        results['details'].append({
            'check': 'Environment',
            'status': 'FAIL',
            'message': str(e)
        })
    
    logger.info(f"Phase 1 Complete: {results['status']}")
    return results


# ============================================================================
# PHASE 2: LAYOUT CREATION
# ============================================================================

def check_layout_creation():
    """Verify Home Lab layout can be created without errors."""
    logger.info("="* 60)
    logger.info("PHASE 2: Layout Creation Integrity")
    logger.info("="* 60)
    
    results = {'status': 'PASS', 'details': []}
    
    try:
        from financial_dashboard.tabs.home_lab import layout
        
        # Attempt to create layout
        home_layout = layout.layout()
        
        results['details'].append({
            'check': 'Layout creation',
            'status': 'PASS',
            'message': 'Home Lab layout created successfully'
        })
        
        # Check for 5 main sections
        section_count = str(home_layout).count('dbc.Card')
        results['details'].append({
            'check': 'Section count',
            'status': 'PASS' if section_count >= 5 else 'WARN',
            'message': f'Found {section_count} Card components (expected 5)'
        })
        
    except Exception as e:
        results['status'] = 'FAIL'
        results['details'].append({
            'check': 'Layout creation',
            'status': 'FAIL',
            'message': str(e)
        })
    
    logger.info(f"Phase 2 Complete: {results['status']}")
    return results


# ============================================================================
# PHASE 3: CALLBACK REGISTRATION
# ============================================================================

def check_callback_registration():
    """Verify callbacks can be registered."""
    logger.info("="* 60)
    logger.info("PHASE 3: Callback Registration")
    logger.info("="* 60)
    
    results = {'status': 'PASS', 'details': []}
    
    try:
        from financial_dashboard.tabs.home_lab import callbacks
        
        # Check if register_callbacks function exists
        if hasattr(callbacks, 'register_callbacks'):
            results['details'].append({
                'check': 'Callback registration function',
                'status': 'PASS',
                'message': 'register_callbacks() found'
            })
        else:
            results['status'] = 'WARN'
            results['details'].append({
                'check': 'Callback registration function',
                'status': 'WARN',
                'message': 'register_callbacks() not found'
            })
        
        # Count decorated callbacks
        callback_funcs = [
            'run_full_diagnostic',
            'refresh_portfolio_data'
        ]
        
        for func_name in callback_funcs:
            if hasattr(callbacks, func_name):
                results['details'].append({
                    'check': f'Callback: {func_name}',
                    'status': 'PASS',
                    'message': f'{func_name}() found'
                })
        
    except Exception as e:
        results['status'] = 'FAIL'
        results['details'].append({
            'check': 'Callback registration',
            'status': 'FAIL',
            'message': str(e)
        })
    
    logger.info(f"Phase 3 Complete: {results['status']}")
    return results


# ============================================================================
# PHASE 4: PORTFOLIO DATA CONNECTIVITY
# ============================================================================

def check_portfolio_connectivity():
    """Verify portfolio data can be loaded."""
    logger.info("="* 60)
    logger.info("PHASE 4: Portfolio Data Connectivity")
    logger.info("="* 60)
    
    results = {'status': 'PASS', 'details': []}
    
    try:
        from financial_dashboard.tabs.home_lab.helpers import get_portfolio_summary
        
        portfolio_data = get_portfolio_summary()
        
        results['details'].append({
            'check': 'Portfolio data load',
            'status': 'PASS',
            'message': f'Loaded {portfolio_data.get("total_positions", 0)} positions'
        })
        
        # Verify expected keys
        expected_keys = ['total_positions', 'total_value', 'daily_change_pct', 'positions']
        for key in expected_keys:
            if key in portfolio_data:
                results['details'].append({
                    'check': f'Portfolio key: {key}',
                    'status': 'PASS',
                    'message': f'{key} present'
                })
        
    except Exception as e:
        results['status'] = 'FAIL'
        results['details'].append({
            'check': 'Portfolio connectivity',
            'status': 'FAIL',
            'message': str(e)
        })
    
    logger.info(f"Phase 4 Complete: {results['status']}")
    return results


# ============================================================================
# PHASE 5: METRICS CACHE VERIFICATION
# ============================================================================

def check_metrics_cache():
    """Verify metrics cache structure."""
    logger.info("="* 60)
    logger.info("PHASE 5: Metrics Cache Verification")
    logger.info("="* 60)
    
    results = {'status': 'PASS', 'details': []}
    
    try:
        from financial_dashboard.tabs.home_lab.helpers import get_cross_lab_metrics
        
        metrics = get_cross_lab_metrics()
        
        results['details'].append({
            'check': 'Metrics cache load',
            'status': 'PASS',
            'message': f'Loaded metrics for {len(metrics)} labs'
        })
        
        # Check expected labs
        expected_labs = ['attribution', 'volatility', 'research', 'strategy']
        for lab in expected_labs:
            if lab in metrics:
                results['details'].append({
                    'check': f'Lab metrics: {lab}',
                    'status': 'PASS',
                    'message': f'{lab} metrics present'
                })
        
    except Exception as e:
        results['status'] = 'FAIL'
        results['details'].append({
            'check': 'Metrics cache',
            'status': 'FAIL',
            'message': str(e)
        })
    
    logger.info(f"Phase 5 Complete: {results['status']}")
    return results


# ============================================================================
# PHASE 6: CROSS-LAB STATUS POLLING
# ============================================================================

def check_lab_status():
    """Verify lab status retrieval."""
    logger.info("="* 60)
    logger.info("PHASE 6: Cross-Lab Status Polling")
    logger.info("="* 60)
    
    results = {'status': 'PASS', 'details': []}
    
    try:
        from financial_dashboard.tabs.home_lab.helpers import get_lab_status
        
        lab_statuses = get_lab_status()
        
        results['details'].append({
            'check': 'Lab status retrieval',
            'status': 'PASS',
            'message': f'Retrieved status for {len(lab_statuses)} labs'
        })
        
        # Check each lab has required fields
        required_fields = ['name', 'icon', 'status', 'last_load', 'data_source']
        for lab_key, lab_info in lab_statuses.items():
            missing_fields = [f for f in required_fields if f not in lab_info]
            if not missing_fields:
                results['details'].append({
                    'check': f'Lab status: {lab_key}',
                    'status': 'PASS',
                    'message': f'{lab_key} has all required fields'
                })
            else:
                results['status'] = 'WARN'
                results['details'].append({
                    'check': f'Lab status: {lab_key}',
                    'status': 'WARN',
                    'message': f'Missing fields: {missing_fields}'
                })
        
    except Exception as e:
        results['status'] = 'FAIL'
        results['details'].append({
            'check': 'Lab status polling',
            'status': 'FAIL',
            'message': str(e)
        })
    
    logger.info(f"Phase 6 Complete: {results['status']}")
    return results


# ============================================================================
# MAIN DIAGNOSTIC RUNNER
# ============================================================================

def run_full_diagnostic():
    """Execute all 6 phases and generate reports."""
    logger.info("\n" + "="* 60)
    logger.info("HOME LAB DIAGNOSTIC - START")
    logger.info("="* 60 + "\n")
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Run all phases
    phase_results = {
        'phase1_environment': check_environment(),
        'phase2_layout': check_layout_creation(),
        'phase3_callbacks': check_callback_registration(),
        'phase4_portfolio': check_portfolio_connectivity(),
        'phase5_metrics': check_metrics_cache(),
        'phase6_lab_status': check_lab_status()
    }
    
    # Determine overall status
    overall_status = 'PASS'
    for phase, result in phase_results.items():
        if result['status'] == 'FAIL':
            overall_status = 'FAIL'
            break
        elif result['status'] == 'WARN' and overall_status != 'FAIL':
            overall_status = 'WARN'
    
    # Create summary
    summary = {
        'timestamp': timestamp,
        'overall_status': overall_status,
        'phases': phase_results
    }
    
    # Save JSON report
    base_path = Path(__file__).parent.parent.parent.parent
    json_path = base_path / "home_tab_diagnostic.json"
    with open(json_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"\n✅ JSON report saved: {json_path}")
    
    # Generate markdown report
    generate_markdown_report(summary, base_path / "home_tab_validation_report.md")
    
    logger.info("\n" + "="* 60)
    logger.info(f"HOME LAB DIAGNOSTIC - COMPLETE: {overall_status}")
    logger.info("="* 60 + "\n")
    
    return summary


def generate_markdown_report(summary, output_path):
    """Generate markdown validation report."""
    md_content = f"""# Home Lab Validation Report

**Timestamp:** {summary['timestamp']}  
**Overall Status:** {'✅ PASS' if summary['overall_status'] == 'PASS' else '⚠️ ' + summary['overall_status']}

---

## Validation Summary

| Phase | Status | Details |
|-------|--------|---------|
"""
    
    for phase_name, phase_result in summary['phases'].items():
        phase_display = phase_name.replace('_', ' ').title()
        status_icon = '✅' if phase_result['status'] == 'PASS' else ('⚠️' if phase_result['status'] == 'WARN' else '❌')
        detail_count = len(phase_result['details'])
        md_content += f"| {phase_display} | {status_icon} {phase_result['status']} | {detail_count} checks |\n"
    
    md_content += "\n---\n\n## Detailed Results\n\n"
    
    for phase_name, phase_result in summary['phases'].items():
        md_content += f"### {phase_name.replace('_', ' ').title()}\n\n"
        
        for detail in phase_result['details']:
            status_icon = '✅' if detail['status'] == 'PASS' else ('⚠️' if detail['status'] == 'WARN' else '❌')
            md_content += f"- **{detail['check']}**: {status_icon} {detail['status']}\n"
            md_content += f"  - {detail['message']}\n\n"
    
    md_content += "\n---\n\n## Next Steps\n\n"
    
    if summary['overall_status'] == 'PASS':
        md_content += "✅ All validation checks passed. Home Lab is ready for deployment.\n\n"
        md_content += "**Recommended actions:**\n"
        md_content += "1. Run Playwright snapshot tests\n"
        md_content += "2. Verify browser rendering\n"
        md_content += "3. Test all interactive elements\n"
    else:
        md_content += "⚠️ Some validation checks failed or require attention.\n\n"
        md_content += "**Recommended actions:**\n"
        md_content += "1. Review failed/warning items above\n"
        md_content += "2. Fix critical issues\n"
        md_content += "3. Re-run diagnostics\n"
    
    with open(output_path, 'w') as f:
        f.write(md_content)
    
    logger.info(f"✅ Markdown report saved: {output_path}")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    run_full_diagnostic()

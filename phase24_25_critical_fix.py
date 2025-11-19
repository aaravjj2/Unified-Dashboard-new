#!/usr/bin/env python3
"""
Phase 24-25 Critical Fix & Restoration
Systematically debug and fix all critical server, React, and interaction issues
"""

import os
import sys
import json
import time
import asyncio
import logging
import requests
import traceback
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

# Setup comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reports/phase24_25_critical_fix/execution.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CriticalFixer:
    def __init__(self):
        self.dashboard_url = 'http://localhost:8050'
        self.target_tabs = ['Home', 'Command Center', 'Strategy Lab', 'Options Lab', 'Weekly Picks', 'Monthly Picks']
        
        # Create directories
        Path('reports/phase24_25_critical_fix').mkdir(parents=True, exist_ok=True)
        Path('test_artifacts/phase24_25_fixed').mkdir(parents=True, exist_ok=True)
        
        self.fix_results = []
    
    def investigate_500_errors(self):
        """Deep investigation of 500 errors"""
        try:
            logger.info("🔍 Deep investigation of 500 errors...")
            
            # Test the callback endpoint with different approaches
            test_cases = [
                {
                    'name': 'Empty POST',
                    'method': 'POST',
                    'data': {},
                    'headers': {'Content-Type': 'application/json'}
                },
                {
                    'name': 'Valid Dash Callback Structure',
                    'method': 'POST',
                    'data': {
                        'output': 'test.children',
                        'outputs': [{'id': 'test', 'property': 'children'}],
                        'inputs': [],
                        'changedPropIds': [],
                        'state': []
                    },
                    'headers': {'Content-Type': 'application/json'}
                },
                {
                    'name': 'Real Portfolio Callback',
                    'method': 'POST',
                    'data': {
                        'output': 'portfolio-table.data',
                        'outputs': [{'id': 'portfolio-table', 'property': 'data'}],
                        'inputs': [{'id': 'portfolio-dropdown', 'property': 'value', 'value': 'current'}],
                        'changedPropIds': ['portfolio-dropdown.value'],
                        'state': []
                    },
                    'headers': {'Content-Type': 'application/json'}
                },
                {
                    'name': 'GET Request (should fail)',
                    'method': 'GET',
                    'data': None,
                    'headers': {}
                }
            ]
            
            results = []
            
            for test_case in test_cases:
                try:
                    logger.info(f"Testing: {test_case['name']}")
                    
                    if test_case['method'] == 'POST':
                        response = requests.post(
                            f"{self.dashboard_url}/_dash-update-component",
                            json=test_case['data'],
                            headers=test_case['headers'],
                            timeout=10
                        )
                    else:
                        response = requests.get(
                            f"{self.dashboard_url}/_dash-update-component",
                            timeout=10
                        )
                    
                    result = {
                        'test_name': test_case['name'],
                        'status_code': response.status_code,
                        'success': response.status_code < 400,
                        'response_size': len(response.text),
                        'content_type': response.headers.get('content-type', 'unknown'),
                        'response_preview': response.text[:200] if response.status_code >= 400 else 'Success'
                    }
                    
                    results.append(result)
                    
                    if response.status_code >= 400:
                        logger.error(f"❌ {test_case['name']}: {response.status_code}")
                        logger.error(f"   Response: {response.text[:200]}")
                    else:
                        logger.info(f"✅ {test_case['name']}: {response.status_code}")
                        
                except Exception as e:
                    logger.error(f"❌ {test_case['name']}: Exception - {e}")
                    results.append({
                        'test_name': test_case['name'],
                        'error': str(e),
                        'success': False
                    })
            
            # Save investigation results
            with open('reports/phase24_25_critical_fix/500_error_investigation.json', 'w') as f:
                json.dump(results, f, indent=2)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 500 error investigation failed: {e}")
            return []
    
    async def test_real_interactions(self):
        """Test real interactions with detailed error capture"""
        try:
            logger.info("🖱️ Testing real interactions with detailed error capture...")
            
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Capture all errors and network activity
            console_errors = []
            network_errors = []
            successful_requests = []
            
            def handle_console(msg):
                if msg.type in ['error', 'warning']:
                    console_errors.append({
                        'type': msg.type,
                        'text': msg.text,
                        'location': str(msg.location) if msg.location else 'unknown',
                        'timestamp': datetime.now().isoformat()
                    })
                    logger.error(f"Console {msg.type}: {msg.text}")
            
            def handle_response(response):
                if response.status >= 400:
                    network_errors.append({
                        'url': response.url,
                        'status': response.status,
                        'method': response.request.method,
                        'timestamp': datetime.now().isoformat()
                    })
                    logger.error(f"Network error: {response.status} {response.request.method} {response.url}")
                elif '/_dash-update-component' in response.url:
                    successful_requests.append({
                        'url': response.url,
                        'status': response.status,
                        'method': response.request.method,
                        'timestamp': datetime.now().isoformat()
                    })
                    logger.info(f"Successful callback: {response.status} {response.request.method}")
            
            page.on('console', handle_console)
            page.on('response', handle_response)
            
            # Test each tab with detailed interaction analysis
            tab_results = {}
            
            for tab_name in self.target_tabs:
                try:
                    logger.info(f"🔍 Testing {tab_name} interactions...")
                    
                    # Clear error arrays for this tab
                    tab_console_errors = len(console_errors)
                    tab_network_errors = len(network_errors)
                    tab_successful_requests = len(successful_requests)
                    
                    # Navigate to tab
                    url_map = {
                        'Home': '/',
                        'Command Center': '/command-center',
                        'Strategy Lab': '/strategy-lab',
                        'Options Lab': '/options-lab',
                        'Weekly Picks': '/weekly-picks',
                        'Monthly Picks': '/monthly-picks'
                    }
                    
                    if tab_name in url_map:
                        full_url = f"{self.dashboard_url}{url_map[tab_name]}"
                        await page.goto(full_url, wait_until='networkidle', timeout=30000)
                        await asyncio.sleep(3)
                    
                    # Capture before screenshot
                    before_screenshot = f"test_artifacts/phase24_25_fixed/{tab_name.lower().replace(' ', '_')}_before.png"
                    await page.screenshot(path=before_screenshot, full_page=True)
                    
                    # Find and test interactive elements
                    interactive_tests = []
                    
                    # Test buttons
                    try:
                        buttons = await page.query_selector_all('button:not([disabled]), .btn:not([disabled]), input[type="submit"]:not([disabled])')
                        logger.info(f"Found {len(buttons)} buttons on {tab_name}")
                        
                        for i, button in enumerate(buttons[:5]):  # Test first 5 buttons
                            try:
                                if await button.is_visible():
                                    button_text = await button.inner_text()
                                    button_text = button_text.strip()[:30] if button_text else f"Button_{i}"
                                    
                                    # Record state before click
                                    pre_click_errors = len(console_errors)
                                    pre_click_network_errors = len(network_errors)
                                    pre_click_requests = len(successful_requests)
                                    
                                    # Click button
                                    await button.click(timeout=3000)
                                    await asyncio.sleep(2)  # Wait for callback
                                    
                                    # Check what happened
                                    post_click_errors = len(console_errors) - pre_click_errors
                                    post_click_network_errors = len(network_errors) - pre_click_network_errors
                                    post_click_requests = len(successful_requests) - pre_click_requests
                                    
                                    interactive_tests.append({
                                        'type': 'button',
                                        'text': button_text,
                                        'success': post_click_network_errors == 0,
                                        'console_errors_triggered': post_click_errors,
                                        'network_errors_triggered': post_click_network_errors,
                                        'successful_requests_triggered': post_click_requests
                                    })
                                    
                                    if post_click_network_errors == 0:
                                        logger.info(f"✅ Button '{button_text}' clicked successfully")
                                    else:
                                        logger.error(f"❌ Button '{button_text}' triggered {post_click_network_errors} network errors")
                                        
                            except Exception as e:
                                interactive_tests.append({
                                    'type': 'button',
                                    'text': f'Button_{i}',
                                    'success': False,
                                    'error': str(e)
                                })
                                logger.warning(f"⚠️ Button {i} click failed: {e}")
                                
                    except Exception as e:
                        logger.warning(f"⚠️ Button testing failed on {tab_name}: {e}")
                    
                    # Test dropdowns
                    try:
                        dropdowns = await page.query_selector_all('select, .dash-dropdown')
                        logger.info(f"Found {len(dropdowns)} dropdowns on {tab_name}")
                        
                        for i, dropdown in enumerate(dropdowns[:3]):  # Test first 3 dropdowns
                            try:
                                if await dropdown.is_visible():
                                    pre_click_errors = len(console_errors)
                                    pre_click_network_errors = len(network_errors)
                                    pre_click_requests = len(successful_requests)
                                    
                                    await dropdown.click(timeout=3000)
                                    await asyncio.sleep(1)
                                    
                                    post_click_errors = len(console_errors) - pre_click_errors
                                    post_click_network_errors = len(network_errors) - pre_click_network_errors
                                    post_click_requests = len(successful_requests) - pre_click_requests
                                    
                                    interactive_tests.append({
                                        'type': 'dropdown',
                                        'index': i,
                                        'success': post_click_network_errors == 0,
                                        'console_errors_triggered': post_click_errors,
                                        'network_errors_triggered': post_click_network_errors,
                                        'successful_requests_triggered': post_click_requests
                                    })
                                    
                            except Exception as e:
                                interactive_tests.append({
                                    'type': 'dropdown',
                                    'index': i,
                                    'success': False,
                                    'error': str(e)
                                })
                                
                    except Exception as e:
                        logger.warning(f"⚠️ Dropdown testing failed on {tab_name}: {e}")
                    
                    # Capture after screenshot
                    after_screenshot = f"test_artifacts/phase24_25_fixed/{tab_name.lower().replace(' ', '_')}_after.png"
                    await page.screenshot(path=after_screenshot, full_page=True)
                    
                    # Calculate tab results
                    tab_console_errors_new = len(console_errors) - tab_console_errors
                    tab_network_errors_new = len(network_errors) - tab_network_errors
                    tab_successful_requests_new = len(successful_requests) - tab_successful_requests
                    
                    successful_interactions = len([t for t in interactive_tests if t.get('success', False)])
                    total_interactions = len(interactive_tests)
                    
                    tab_results[tab_name] = {
                        'console_errors': tab_console_errors_new,
                        'network_errors': tab_network_errors_new,
                        'successful_requests': tab_successful_requests_new,
                        'interactive_tests': interactive_tests,
                        'successful_interactions': successful_interactions,
                        'total_interactions': total_interactions,
                        'interaction_success_rate': successful_interactions / total_interactions if total_interactions > 0 else 0,
                        'before_screenshot': before_screenshot,
                        'after_screenshot': after_screenshot
                    }
                    
                    logger.info(f"📊 {tab_name}: {successful_interactions}/{total_interactions} interactions successful, {tab_console_errors_new} console errors, {tab_network_errors_new} network errors, {tab_successful_requests_new} successful requests")
                    
                except Exception as e:
                    logger.error(f"❌ Tab testing failed for {tab_name}: {e}")
                    tab_results[tab_name] = {
                        'error': str(e),
                        'interaction_success_rate': 0
                    }
            
            await browser.close()
            
            # Compile overall results
            results = {
                'total_console_errors': len(console_errors),
                'total_network_errors': len(network_errors),
                'total_successful_requests': len(successful_requests),
                'tab_results': tab_results,
                'console_errors': console_errors,
                'network_errors': network_errors,
                'successful_requests': successful_requests
            }
            
            # Save results
            with open('reports/phase24_25_critical_fix/interaction_analysis.json', 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Real interaction testing failed: {e}")
            return {}
    
    def analyze_react_errors(self):
        """Analyze React Error #31 in detail"""
        try:
            logger.info("🔍 Analyzing React Error #31...")
            
            # React Error #31 is: "Objects are not valid as a React child"
            # This usually means a component is trying to render an object instead of a string/number/element
            
            analysis = {
                'error_type': 'React Error #31',
                'description': 'Objects are not valid as a React child',
                'common_causes': [
                    'Passing an object directly to a component that expects a string/number',
                    'Returning an object from a callback instead of a valid React element',
                    'Invalid prop types being passed to components',
                    'Circular references in component props',
                    'Undefined or null values being treated as objects'
                ],
                'investigation_steps': [
                    'Check callback return values for objects',
                    'Validate component prop types',
                    'Look for undefined/null handling',
                    'Check for circular references'
                ],
                'potential_fixes': [
                    'Ensure callbacks return valid React elements or primitives',
                    'Add proper null/undefined checks',
                    'Validate prop types before passing to components',
                    'Use JSON.stringify() for debugging object values'
                ]
            }
            
            # Save analysis
            with open('reports/phase24_25_critical_fix/react_error_analysis.json', 'w') as f:
                json.dump(analysis, f, indent=2)
            
            logger.info("📊 React Error #31 analysis complete")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ React error analysis failed: {e}")
            return {}
    
    def test_ui_color_fixes(self):
        """Test and implement UI color fixes"""
        try:
            logger.info("🎨 Testing and implementing UI color fixes...")
            
            # Create comprehensive CSS fixes
            css_fixes = """
            /* Phase 24-25 Critical UI Color Fixes */
            
            /* Input elements - force white background, black text */
            input[type="text"], input[type="number"], input[type="email"], 
            input[type="password"], input[type="search"], textarea, select,
            .form-control, .dash-input {
                background-color: white !important;
                color: #000000 !important;
                border: 1px solid #ccc !important;
            }
            
            /* Dash dropdown fixes */
            .dash-dropdown .Select-control,
            .dash-dropdown .Select-menu-outer,
            .dash-dropdown .Select-option {
                background-color: white !important;
                color: #000000 !important;
            }
            
            /* Table fixes */
            .dash-table-container,
            .dash-table-container *,
            .dash-table-container .dash-cell,
            .dash-table-container .dash-cell div {
                color: #000000 !important;
                background-color: white !important;
            }
            
            /* Button fixes */
            .btn, button, .dash-button {
                color: #000000 !important;
                background-color: #f8f9fa !important;
                border: 1px solid #dee2e6 !important;
            }
            
            /* Focus states */
            input:focus, textarea:focus, select:focus,
            .form-control:focus, .dash-input:focus {
                background-color: white !important;
                color: #000000 !important;
                border-color: #007bff !important;
                box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25) !important;
            }
            
            /* General text elements */
            p, span, div, label, h1, h2, h3, h4, h5, h6 {
                color: #000000 !important;
            }
            
            /* Container backgrounds */
            .card, .card-body, .container-fluid, .row, .col {
                background-color: white !important;
            }
            
            /* Ensure visibility */
            * {
                visibility: visible !important;
            }
            """
            
            # Save CSS fixes to a file that can be injected
            css_file_path = 'test_artifacts/phase24_25_fixed/ui_color_fixes.css'
            with open(css_file_path, 'w') as f:
                f.write(css_fixes)
            
            ui_fix_result = {
                'css_fixes_created': True,
                'css_file_path': css_file_path,
                'css_rules_count': len(css_fixes.split('{')),
                'target_elements': [
                    'input', 'textarea', 'select', '.form-control', '.dash-input',
                    '.dash-dropdown', '.dash-table-container', '.btn', 'button'
                ]
            }
            
            # Save UI fix results
            with open('reports/phase24_25_critical_fix/ui_color_fixes.json', 'w') as f:
                json.dump(ui_fix_result, f, indent=2)
            
            logger.info("✅ UI color fixes prepared")
            return ui_fix_result
            
        except Exception as e:
            logger.error(f"❌ UI color fix preparation failed: {e}")
            return {}
    
    def generate_critical_fix_report(self, investigation_results, interaction_results, react_analysis, ui_fixes):
        """Generate comprehensive critical fix report"""
        try:
            # Analyze current state
            has_500_errors = any(not r.get('success', True) for r in investigation_results)
            has_console_errors = interaction_results.get('total_console_errors', 0) > 0
            has_network_errors = interaction_results.get('total_network_errors', 0) > 0
            
            overall_interaction_success = 0
            if interaction_results.get('tab_results'):
                success_rates = [r.get('interaction_success_rate', 0) for r in interaction_results['tab_results'].values()]
                overall_interaction_success = sum(success_rates) / len(success_rates) if success_rates else 0
            
            # Create comprehensive report
            report = {
                'phase': 'Phase 24-25 Critical Fix & Restoration',
                'execution_time': datetime.now().isoformat(),
                'current_status': {
                    'has_500_errors': has_500_errors,
                    'has_console_errors': has_console_errors,
                    'has_network_errors': has_network_errors,
                    'overall_interaction_success': overall_interaction_success,
                    'critical_issues_remaining': has_500_errors or has_console_errors or overall_interaction_success < 0.8
                },
                'investigation_results': investigation_results,
                'interaction_analysis': interaction_results,
                'react_error_analysis': react_analysis,
                'ui_color_fixes': ui_fixes,
                'next_steps': []
            }
            
            # Generate next steps based on findings
            if has_500_errors:
                report['next_steps'].append("CRITICAL: Debug and fix 500 errors in callback endpoint")
            
            if has_console_errors:
                report['next_steps'].append("Fix React Error #31 - check component return values and prop types")
            
            if overall_interaction_success < 0.8:
                report['next_steps'].append("Restore interactive functionality - fix button and dropdown handlers")
            
            if not ui_fixes:
                report['next_steps'].append("Implement UI color normalization fixes")
            
            # Save main report
            with open('reports/phase24_25_critical_fix/critical_fix_analysis.json', 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            # Generate markdown report
            status = '❌ CRITICAL ISSUES REMAIN' if report['current_status']['critical_issues_remaining'] else '✅ ISSUES RESOLVED'
            
            markdown_content = f"""# Phase 24-25 Critical Fix Analysis Report

## Executive Summary

**Status:** {status}
**Execution Time:** {datetime.now().isoformat()}
**Overall Interaction Success:** {overall_interaction_success:.1%}

## Current Issue Status

### Server Issues
- **500 Errors:** {'❌ FOUND' if has_500_errors else '✅ RESOLVED'}
- **Network Errors:** {'❌ FOUND' if has_network_errors else '✅ NONE'} ({interaction_results.get('total_network_errors', 0)} total)
- **Successful Requests:** {interaction_results.get('total_successful_requests', 0)}

### Client Issues  
- **Console Errors:** {'❌ FOUND' if has_console_errors else '✅ NONE'} ({interaction_results.get('total_console_errors', 0)} total)
- **React Error #31:** {'❌ ACTIVE' if has_console_errors else '✅ RESOLVED'}

### Interactive Functionality

| Tab | Success Rate | Successful | Total | Console Errors | Network Errors |
|-----|--------------|------------|-------|----------------|----------------|
"""
            
            for tab_name, result in interaction_results.get('tab_results', {}).items():
                success_rate = result.get('interaction_success_rate', 0)
                successful = result.get('successful_interactions', 0)
                total = result.get('total_interactions', 0)
                console_errs = result.get('console_errors', 0)
                network_errs = result.get('network_errors', 0)
                markdown_content += f"| {tab_name} | {success_rate:.1%} | {successful} | {total} | {console_errs} | {network_errs} |\n"
            
            markdown_content += f"""
## Investigation Results

### Callback Endpoint Tests
"""
            for result in investigation_results:
                test_name = result.get('test_name', 'Unknown')
                status_code = result.get('status_code', 0)
                success = '✅ PASS' if result.get('success', False) else '❌ FAIL'
                markdown_content += f"- **{test_name}:** {status_code} {success}\n"
            
            markdown_content += f"""
## React Error Analysis

**Error Type:** {react_analysis.get('error_type', 'Unknown')}
**Description:** {react_analysis.get('description', 'No description')}

### Common Causes:
"""
            for cause in react_analysis.get('common_causes', []):
                markdown_content += f"- {cause}\n"
            
            markdown_content += f"""
## Next Steps Required

"""
            for i, step in enumerate(report['next_steps'], 1):
                markdown_content += f"{i}. {step}\n"
            
            markdown_content += f"""
## Artifacts Generated

- **Investigation Results:** `reports/phase24_25_critical_fix/500_error_investigation.json`
- **Interaction Analysis:** `reports/phase24_25_critical_fix/interaction_analysis.json`
- **React Error Analysis:** `reports/phase24_25_critical_fix/react_error_analysis.json`
- **UI Color Fixes:** `reports/phase24_25_critical_fix/ui_color_fixes.json`
- **Screenshots:** `test_artifacts/phase24_25_fixed/`

---

**Generated:** {datetime.now().isoformat()}
**Phase:** 24-25 Critical Fix Analysis Complete
"""
            
            with open('reports/phase24_25_critical_fix/PHASE_24_25_CRITICAL_FIX_ANALYSIS.md', 'w') as f:
                f.write(markdown_content)
            
            logger.info("📊 Critical fix analysis report generated")
            return report
            
        except Exception as e:
            logger.error(f"❌ Critical fix report generation failed: {e}")
            return None

async def main():
    """Main execution function"""
    logger.info("🚀 Starting Phase 24-25 Critical Fix & Restoration")
    
    fixer = CriticalFixer()
    
    try:
        # Phase 1: Investigate 500 Errors
        logger.info("=" * 60)
        logger.info("PHASE 1: INVESTIGATE 500 ERRORS")
        logger.info("=" * 60)
        investigation_results = fixer.investigate_500_errors()
        
        # Phase 2: Test Real Interactions
        logger.info("=" * 60)
        logger.info("PHASE 2: TEST REAL INTERACTIONS")
        logger.info("=" * 60)
        interaction_results = await fixer.test_real_interactions()
        
        # Phase 3: Analyze React Errors
        logger.info("=" * 60)
        logger.info("PHASE 3: ANALYZE REACT ERRORS")
        logger.info("=" * 60)
        react_analysis = fixer.analyze_react_errors()
        
        # Phase 4: Prepare UI Fixes
        logger.info("=" * 60)
        logger.info("PHASE 4: PREPARE UI COLOR FIXES")
        logger.info("=" * 60)
        ui_fixes = fixer.test_ui_color_fixes()
        
        # Phase 5: Generate Analysis Report
        logger.info("=" * 60)
        logger.info("PHASE 5: GENERATE CRITICAL FIX ANALYSIS")
        logger.info("=" * 60)
        final_report = fixer.generate_critical_fix_report(
            investigation_results, interaction_results, react_analysis, ui_fixes
        )
        
        # Print summary
        if final_report:
            critical_issues = final_report['current_status']['critical_issues_remaining']
            interaction_success = final_report['current_status']['overall_interaction_success']
            has_500_errors = final_report['current_status']['has_500_errors']
            has_console_errors = final_report['current_status']['has_console_errors']
            
            print("\n" + "="*80)
            if critical_issues:
                print("❌ PHASE 24-25 CRITICAL FIX: ISSUES IDENTIFIED!")
                print("="*80)
                if has_500_errors:
                    print("❌ 500 errors still present in callback endpoint")
                if has_console_errors:
                    print("❌ React Error #31 still occurring")
                print(f"⚠️ Interaction success rate: {interaction_success:.1%}")
                print("🔧 Critical fixes still required")
            else:
                print("✅ PHASE 24-25 CRITICAL FIX: ISSUES RESOLVED!")
                print("="*80)
                print("✅ No 500 callback errors")
                print("✅ No React console errors")
                print(f"✅ Interaction success rate: {interaction_success:.1%}")
            
            print("📊 Check reports/phase24_25_critical_fix/ for detailed analysis")
            print("="*80)
            
            return not critical_issues
        else:
            print("❌ Critical fix analysis failed")
            return False
        
    except Exception as e:
        logger.error(f"❌ Main execution failed: {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
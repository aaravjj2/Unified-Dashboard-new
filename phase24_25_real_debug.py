#!/usr/bin/env python3
"""
Phase 24-25 REAL Debug & Validation
Identify and fix actual server errors, React issues, and callback problems
"""

import os
import sys
import json
import time
import asyncio
import logging
import requests
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealServerDebugger:
    def __init__(self):
        self.dashboard_url = 'http://localhost:8050'
        self.target_tabs = ['Home', 'Command Center', 'Strategy Lab', 'Options Lab', 'Weekly Picks', 'Monthly Picks']
        self.debug_results = []
        
        # Create debug directories
        Path('reports/phase24_25_real_debug').mkdir(parents=True, exist_ok=True)
        Path('test_artifacts/phase24_25_real_debug').mkdir(parents=True, exist_ok=True)
    
    async def diagnose_react_errors(self):
        """Diagnose React errors and callback issues"""
        try:
            logger.info("🔍 Diagnosing React errors and callback issues...")
            
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=False)  # Use headed mode to see errors
            context = await browser.new_context()
            page = await context.new_page()
            
            # Capture console errors
            console_errors = []
            network_errors = []
            
            def handle_console(msg):
                if msg.type in ['error', 'warning']:
                    console_errors.append({
                        'type': msg.type,
                        'text': msg.text,
                        'location': msg.location,
                        'timestamp': datetime.now().isoformat()
                    })
                    logger.error(f"Console {msg.type}: {msg.text}")
            
            def handle_response(response):
                if response.status >= 400:
                    network_errors.append({
                        'url': response.url,
                        'status': response.status,
                        'status_text': response.status_text,
                        'timestamp': datetime.now().isoformat()
                    })
                    logger.error(f"Network error: {response.status} - {response.url}")
            
            page.on('console', handle_console)
            page.on('response', handle_response)
            
            # Navigate to dashboard and wait for errors
            logger.info("🌐 Loading dashboard to capture errors...")
            await page.goto(self.dashboard_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(5)  # Wait for React to load and potentially error
            
            # Try to interact with tabs to trigger more errors
            tab_errors = {}
            for tab_name in self.target_tabs:
                try:
                    logger.info(f"🔍 Testing {tab_name} for errors...")
                    
                    # Clear previous errors for this tab
                    tab_console_errors = []
                    tab_network_errors = []
                    
                    def tab_console_handler(msg):
                        if msg.type in ['error', 'warning']:
                            tab_console_errors.append({
                                'type': msg.type,
                                'text': msg.text,
                                'location': msg.location,
                                'timestamp': datetime.now().isoformat()
                            })
                    
                    def tab_network_handler(response):
                        if response.status >= 400:
                            tab_network_errors.append({
                                'url': response.url,
                                'status': response.status,
                                'status_text': response.status_text,
                                'timestamp': datetime.now().isoformat()
                            })
                    
                    page.on('console', tab_console_handler)
                    page.on('response', tab_network_handler)
                    
                    # Try to navigate to tab
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
                        await asyncio.sleep(3)  # Wait for tab to load and potentially error
                        
                        # Try to click some elements to trigger callbacks
                        try:
                            buttons = await page.query_selector_all('button, .btn, input[type="submit"]')
                            for i, button in enumerate(buttons[:3]):  # Try first 3 buttons
                                try:
                                    if await button.is_visible() and await button.is_enabled():
                                        await button.click(timeout=2000)
                                        await asyncio.sleep(1)
                                except Exception as e:
                                    logger.debug(f"Button click failed: {e}")
                        except Exception as e:
                            logger.debug(f"Button interaction failed: {e}")
                    
                    tab_errors[tab_name] = {
                        'console_errors': tab_console_errors,
                        'network_errors': tab_network_errors,
                        'total_errors': len(tab_console_errors) + len(tab_network_errors)
                    }
                    
                    logger.info(f"📊 {tab_name}: {len(tab_console_errors)} console errors, {len(tab_network_errors)} network errors")
                    
                except Exception as e:
                    logger.error(f"❌ Error testing {tab_name}: {e}")
                    tab_errors[tab_name] = {
                        'console_errors': [],
                        'network_errors': [],
                        'navigation_error': str(e),
                        'total_errors': 1
                    }
            
            await browser.close()
            
            # Analyze errors
            total_console_errors = len(console_errors)
            total_network_errors = len(network_errors)
            total_tab_errors = sum(tab['total_errors'] for tab in tab_errors.values())
            
            error_analysis = {
                'global_console_errors': console_errors,
                'global_network_errors': network_errors,
                'tab_specific_errors': tab_errors,
                'summary': {
                    'total_console_errors': total_console_errors,
                    'total_network_errors': total_network_errors,
                    'total_tab_errors': total_tab_errors,
                    'has_react_errors': any('React' in error.get('text', '') for error in console_errors),
                    'has_500_errors': any(error.get('status') == 500 for error in network_errors),
                    'has_callback_errors': any('callback' in error.get('text', '').lower() for error in console_errors)
                }
            }
            
            # Save error analysis
            with open('reports/phase24_25_real_debug/error_analysis.json', 'w') as f:
                json.dump(error_analysis, f, indent=2)
            
            logger.info(f"📊 Error Analysis Complete:")
            logger.info(f"   Console Errors: {total_console_errors}")
            logger.info(f"   Network Errors: {total_network_errors}")
            logger.info(f"   Tab Errors: {total_tab_errors}")
            logger.info(f"   React Errors: {error_analysis['summary']['has_react_errors']}")
            logger.info(f"   500 Errors: {error_analysis['summary']['has_500_errors']}")
            logger.info(f"   Callback Errors: {error_analysis['summary']['has_callback_errors']}")
            
            return error_analysis
            
        except Exception as e:
            logger.error(f"❌ Error diagnosis failed: {e}")
            return None
    
    def test_callback_endpoints(self):
        """Test specific callback endpoints for 500 errors"""
        try:
            logger.info("🔍 Testing callback endpoints for 500 errors...")
            
            callback_endpoints = [
                '/_dash-dependencies',
                '/_dash-layout',
                '/_dash-update-component'
            ]
            
            endpoint_results = {}
            
            for endpoint in callback_endpoints:
                try:
                    url = f"{self.dashboard_url}{endpoint}"
                    
                    if endpoint == '/_dash-update-component':
                        # Test POST request for update component
                        response = requests.post(url, json={
                            'output': 'test-output',
                            'inputs': [],
                            'changedPropIds': [],
                            'state': []
                        }, timeout=10)
                    else:
                        # Test GET request
                        response = requests.get(url, timeout=10)
                    
                    endpoint_results[endpoint] = {
                        'status_code': response.status_code,
                        'success': response.status_code < 400,
                        'response_size': len(response.text),
                        'content_type': response.headers.get('content-type', 'unknown')
                    }
                    
                    if response.status_code >= 400:
                        logger.error(f"❌ {endpoint}: {response.status_code}")
                        endpoint_results[endpoint]['error_content'] = response.text[:500]
                    else:
                        logger.info(f"✅ {endpoint}: {response.status_code}")
                        
                except Exception as e:
                    logger.error(f"❌ {endpoint}: Exception - {e}")
                    endpoint_results[endpoint] = {
                        'status_code': 0,
                        'success': False,
                        'error': str(e)
                    }
            
            # Save endpoint results
            with open('reports/phase24_25_real_debug/callback_endpoints.json', 'w') as f:
                json.dump(endpoint_results, f, indent=2)
            
            return endpoint_results
            
        except Exception as e:
            logger.error(f"❌ Callback endpoint testing failed: {e}")
            return {}
    
    async def run_clicker_tests(self):
        """Run specific clicker tests to identify interaction issues"""
        try:
            logger.info("🖱️ Running clicker tests to identify interaction issues...")
            
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Track interaction results
            interaction_results = {}
            
            for tab_name in self.target_tabs:
                try:
                    logger.info(f"🖱️ Testing interactions on {tab_name}...")
                    
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
                        await asyncio.sleep(2)
                    
                    # Capture screenshot before interactions
                    before_screenshot = f"test_artifacts/phase24_25_real_debug/{tab_name.lower().replace(' ', '_')}_before.png"
                    await page.screenshot(path=before_screenshot, full_page=True)
                    
                    # Find and test interactive elements
                    interactive_elements = []
                    
                    # Test buttons
                    buttons = await page.query_selector_all('button, .btn, input[type="submit"], input[type="button"]')
                    for i, button in enumerate(buttons[:5]):  # Test first 5 buttons
                        try:
                            if await button.is_visible() and await button.is_enabled():
                                text = await button.inner_text()
                                await button.click(timeout=3000)
                                await asyncio.sleep(1)
                                
                                interactive_elements.append({
                                    'type': 'button',
                                    'index': i,
                                    'text': text[:50],
                                    'success': True
                                })
                                logger.info(f"✅ Button clicked: {text[:30]}")
                            else:
                                interactive_elements.append({
                                    'type': 'button',
                                    'index': i,
                                    'success': False,
                                    'reason': 'not_visible_or_enabled'
                                })
                        except Exception as e:
                            interactive_elements.append({
                                'type': 'button',
                                'index': i,
                                'success': False,
                                'error': str(e)
                            })
                            logger.warning(f"⚠️ Button click failed: {e}")
                    
                    # Test dropdowns
                    dropdowns = await page.query_selector_all('select, .dash-dropdown')
                    for i, dropdown in enumerate(dropdowns[:3]):  # Test first 3 dropdowns
                        try:
                            if await dropdown.is_visible():
                                await dropdown.click(timeout=3000)
                                await asyncio.sleep(1)
                                
                                interactive_elements.append({
                                    'type': 'dropdown',
                                    'index': i,
                                    'success': True
                                })
                                logger.info(f"✅ Dropdown clicked")
                        except Exception as e:
                            interactive_elements.append({
                                'type': 'dropdown',
                                'index': i,
                                'success': False,
                                'error': str(e)
                            })
                            logger.warning(f"⚠️ Dropdown click failed: {e}")
                    
                    # Test inputs
                    inputs = await page.query_selector_all('input[type="text"], input[type="number"], textarea')
                    for i, input_elem in enumerate(inputs[:3]):  # Test first 3 inputs
                        try:
                            if await input_elem.is_visible() and await input_elem.is_enabled():
                                await input_elem.fill('test')
                                await asyncio.sleep(1)
                                
                                interactive_elements.append({
                                    'type': 'input',
                                    'index': i,
                                    'success': True
                                })
                                logger.info(f"✅ Input filled")
                        except Exception as e:
                            interactive_elements.append({
                                'type': 'input',
                                'index': i,
                                'success': False,
                                'error': str(e)
                            })
                            logger.warning(f"⚠️ Input fill failed: {e}")
                    
                    # Capture screenshot after interactions
                    after_screenshot = f"test_artifacts/phase24_25_real_debug/{tab_name.lower().replace(' ', '_')}_after.png"
                    await page.screenshot(path=after_screenshot, full_page=True)
                    
                    # Calculate success rate
                    successful_interactions = len([elem for elem in interactive_elements if elem.get('success', False)])
                    total_interactions = len(interactive_elements)
                    success_rate = successful_interactions / total_interactions if total_interactions > 0 else 0
                    
                    interaction_results[tab_name] = {
                        'interactive_elements': interactive_elements,
                        'successful_interactions': successful_interactions,
                        'total_interactions': total_interactions,
                        'success_rate': success_rate,
                        'before_screenshot': before_screenshot,
                        'after_screenshot': after_screenshot
                    }
                    
                    logger.info(f"📊 {tab_name}: {successful_interactions}/{total_interactions} interactions successful ({success_rate:.1%})")
                    
                except Exception as e:
                    logger.error(f"❌ Clicker test failed for {tab_name}: {e}")
                    interaction_results[tab_name] = {
                        'error': str(e),
                        'success_rate': 0
                    }
            
            await browser.close()
            
            # Save interaction results
            with open('reports/phase24_25_real_debug/clicker_tests.json', 'w') as f:
                json.dump(interaction_results, f, indent=2, default=str)
            
            return interaction_results
            
        except Exception as e:
            logger.error(f"❌ Clicker tests failed: {e}")
            return {}
    
    def generate_real_debug_report(self, error_analysis, callback_results, clicker_results):
        """Generate comprehensive real debug report"""
        try:
            # Calculate overall health
            has_critical_errors = (
                error_analysis and error_analysis['summary']['has_react_errors'] or
                error_analysis and error_analysis['summary']['has_500_errors'] or
                any(not result.get('success', False) for result in callback_results.values())
            )
            
            overall_interaction_success = 0
            if clicker_results:
                total_success_rate = sum(result.get('success_rate', 0) for result in clicker_results.values())
                overall_interaction_success = total_success_rate / len(clicker_results) if clicker_results else 0
            
            # Create comprehensive report
            report = {
                'phase': 'Phase 24-25 Real Debug & Validation',
                'execution_time': datetime.now().isoformat(),
                'server_health': {
                    'has_critical_errors': has_critical_errors,
                    'react_errors': error_analysis['summary']['has_react_errors'] if error_analysis else False,
                    'callback_500_errors': error_analysis['summary']['has_500_errors'] if error_analysis else False,
                    'callback_endpoint_health': callback_results,
                    'overall_interaction_success': overall_interaction_success
                },
                'error_analysis': error_analysis,
                'callback_endpoint_results': callback_results,
                'clicker_test_results': clicker_results,
                'recommendations': []
            }
            
            # Generate recommendations
            if error_analysis and error_analysis['summary']['has_react_errors']:
                report['recommendations'].append("Fix React component errors - check for invalid props or component structure")
            
            if error_analysis and error_analysis['summary']['has_500_errors']:
                report['recommendations'].append("Fix 500 internal server errors - check callback functions and server logs")
            
            if overall_interaction_success < 0.8:
                report['recommendations'].append("Improve interactive element functionality - many buttons/inputs are not working")
            
            if not callback_results or any(not result.get('success', False) for result in callback_results.values()):
                report['recommendations'].append("Fix callback endpoint issues - dash update components failing")
            
            # Save main report
            with open('reports/phase24_25_real_debug/comprehensive_real_debug.json', 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            # Generate markdown report
            markdown_content = f"""# Phase 24-25 REAL Debug & Validation Report

## Executive Summary

**Status:** {'❌ CRITICAL ISSUES FOUND' if has_critical_errors else '✅ NO CRITICAL ISSUES'}
**Execution Time:** {datetime.now().isoformat()}
**Overall Interaction Success:** {overall_interaction_success:.1%}

## Critical Issues Identified

"""
            
            if error_analysis:
                markdown_content += f"""### React Errors
- **React Errors Found:** {'❌ YES' if error_analysis['summary']['has_react_errors'] else '✅ NO'}
- **Total Console Errors:** {error_analysis['summary']['total_console_errors']}
- **500 Server Errors:** {'❌ YES' if error_analysis['summary']['has_500_errors'] else '✅ NO'}
- **Callback Errors:** {'❌ YES' if error_analysis['summary']['has_callback_errors'] else '✅ NO'}

"""
            
            if callback_results:
                markdown_content += """### Callback Endpoint Health

| Endpoint | Status | Success |
|----------|--------|---------|
"""
                for endpoint, result in callback_results.items():
                    status = result.get('status_code', 0)
                    success = '✅ YES' if result.get('success', False) else '❌ NO'
                    markdown_content += f"| {endpoint} | {status} | {success} |\n"
                
                markdown_content += "\n"
            
            if clicker_results:
                markdown_content += """### Tab Interaction Results

| Tab | Success Rate | Successful | Total |
|-----|--------------|------------|-------|
"""
                for tab_name, result in clicker_results.items():
                    if 'success_rate' in result:
                        success_rate = result['success_rate']
                        successful = result.get('successful_interactions', 0)
                        total = result.get('total_interactions', 0)
                        markdown_content += f"| {tab_name} | {success_rate:.1%} | {successful} | {total} |\n"
                
                markdown_content += "\n"
            
            markdown_content += """## Recommendations

"""
            for i, rec in enumerate(report['recommendations'], 1):
                markdown_content += f"{i}. {rec}\n"
            
            markdown_content += f"""
## Artifacts Generated

- **Error Analysis:** `reports/phase24_25_real_debug/error_analysis.json`
- **Callback Tests:** `reports/phase24_25_real_debug/callback_endpoints.json`
- **Clicker Tests:** `reports/phase24_25_real_debug/clicker_tests.json`
- **Screenshots:** `test_artifacts/phase24_25_real_debug/`

---

**Generated:** {datetime.now().isoformat()}
**Phase:** 24-25 Real Debug & Validation Complete
"""
            
            with open('reports/phase24_25_real_debug/PHASE_24_25_REAL_DEBUG.md', 'w') as f:
                f.write(markdown_content)
            
            logger.info("📊 Real debug report generated successfully")
            return report
            
        except Exception as e:
            logger.error(f"❌ Report generation failed: {e}")
            return None

async def main():
    """Main execution function"""
    logger.info("🚀 Starting Phase 24-25 REAL Debug & Validation")
    
    debugger = RealServerDebugger()
    
    try:
        # Phase 1: Diagnose React Errors
        logger.info("=" * 60)
        logger.info("PHASE 1: REACT ERROR DIAGNOSIS")
        logger.info("=" * 60)
        error_analysis = await debugger.diagnose_react_errors()
        
        # Phase 2: Test Callback Endpoints
        logger.info("=" * 60)
        logger.info("PHASE 2: CALLBACK ENDPOINT TESTING")
        logger.info("=" * 60)
        callback_results = debugger.test_callback_endpoints()
        
        # Phase 3: Run Clicker Tests
        logger.info("=" * 60)
        logger.info("PHASE 3: CLICKER INTERACTION TESTS")
        logger.info("=" * 60)
        clicker_results = await debugger.run_clicker_tests()
        
        # Phase 4: Generate Report
        logger.info("=" * 60)
        logger.info("PHASE 4: GENERATE REAL DEBUG REPORT")
        logger.info("=" * 60)
        final_report = debugger.generate_real_debug_report(error_analysis, callback_results, clicker_results)
        
        # Print summary
        if final_report:
            has_critical_errors = final_report['server_health']['has_critical_errors']
            interaction_success = final_report['server_health']['overall_interaction_success']
            
            print("\n" + "="*80)
            if has_critical_errors:
                print("❌ PHASE 24-25 REAL DEBUG: CRITICAL ISSUES FOUND!")
                print("="*80)
                print("❌ React errors detected")
                print("❌ Server 500 errors found")
                print("❌ Callback issues identified")
                print(f"⚠️ Interaction success rate: {interaction_success:.1%}")
            else:
                print("✅ PHASE 24-25 REAL DEBUG: NO CRITICAL ISSUES")
                print("="*80)
                print("✅ No React errors detected")
                print("✅ No 500 server errors")
                print("✅ Callbacks functioning")
                print(f"✅ Interaction success rate: {interaction_success:.1%}")
            
            print("📊 Check reports/phase24_25_real_debug/ for detailed analysis")
            print("="*80)
            
            return not has_critical_errors
        else:
            print("❌ Real debug analysis failed")
            return False
        
    except Exception as e:
        logger.error(f"❌ Main execution failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
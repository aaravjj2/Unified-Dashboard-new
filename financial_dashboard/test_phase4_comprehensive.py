#!/usr/bin/env python3
"""
Comprehensive Test Suite for Phase 4 Implementation

Tests all services: Analysis Hub, Portfolio, Event Monitor, Research Lab
Includes: Health checks, curl tests, basic UI tests

Usage:
    python3 test_phase4_comprehensive.py
"""

import os
import sys
import time
import json
import requests
import subprocess
from datetime import datetime

# Test configuration
SERVICES = {
    'analysis': {'port': 8054, 'name': 'Analysis Hub'},
    'portfolio': {'port': 8056, 'name': 'Portfolio Dashboard'},
    'event_monitor': {'port': 8057, 'name': 'Event Monitor'},
    'research_lab': {'port': 8058, 'name': 'Research Lab'},
    'unified': {'port': 8055, 'name': 'Unified Dashboard'}
}

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

test_results = {'passed': 0, 'failed': 0, 'warnings': 0}


def print_header(text):
    """Print formatted header."""
    print(f"\n{BLUE}{'=' * 70}{RESET}")
    print(f"{BLUE}{text:^70}{RESET}")
    print(f"{BLUE}{'=' * 70}{RESET}\n")


def print_test(name, status, message=''):
    """Print test result."""
    if status == 'PASS':
        print(f"{GREEN}✓{RESET} {name:50} {GREEN}PASS{RESET} {message}")
        test_results['passed'] += 1
    elif status == 'FAIL':
        print(f"{RED}✗{RESET} {name:50} {RED}FAIL{RESET} {message}")
        test_results['failed'] += 1
    elif status == 'WARN':
        print(f"{YELLOW}⚠{RESET} {name:50} {YELLOW}WARN{RESET} {message}")
        test_results['warnings'] += 1


def test_service_health(service_name, service_config):
    """Test if service is running and responsive."""
    port = service_config['port']
    url = f"http://localhost:{port}/"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print_test(f"{service_name} health check", 'PASS', f"Port {port}")
            return True
        else:
            print_test(f"{service_name} health check", 'FAIL', 
                      f"Status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_test(f"{service_name} health check", 'FAIL', "Connection refused")
        return False
    except Exception as e:
        print_test(f"{service_name} health check", 'FAIL', str(e))
        return False


def test_dash_layout(service_name, service_config):
    """Test if Dash layout is accessible."""
    port = service_config['port']
    url = f"http://localhost:{port}/_dash-layout"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            layout = response.json()
            if layout and 'props' in layout:
                print_test(f"{service_name} layout endpoint", 'PASS', 
                          f"{len(str(layout))} bytes")
                return True
            else:
                print_test(f"{service_name} layout endpoint", 'FAIL', 
                          "Invalid layout structure")
                return False
        else:
            print_test(f"{service_name} layout endpoint", 'FAIL', 
                      f"Status {response.status_code}")
            return False
    except Exception as e:
        print_test(f"{service_name} layout endpoint", 'FAIL', str(e))
        return False


def test_dash_dependencies(service_name, service_config):
    """Test if Dash dependencies are accessible."""
    port = service_config['port']
    url = f"http://localhost:{port}/_dash-dependencies"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            deps = response.json()
            callback_count = len(deps) if isinstance(deps, list) else 0
            print_test(f"{service_name} dependencies endpoint", 'PASS', 
                      f"{callback_count} callbacks")
            return True
        else:
            print_test(f"{service_name} dependencies endpoint", 'WARN', 
                      f"Status {response.status_code}")
            return False
    except Exception as e:
        print_test(f"{service_name} dependencies endpoint", 'WARN', str(e))
        return False


def test_page_content(service_name, service_config):
    """Test if page contains expected content."""
    port = service_config['port']
    url = f"http://localhost:{port}/"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            content = response.text
            
            # Check for key indicators
            has_dash = 'dash' in content.lower()
            has_content = len(content) > 1000
            has_scripts = '_dash' in content
            
            if has_dash and has_content and has_scripts:
                print_test(f"{service_name} page content", 'PASS', 
                          f"{len(content)} chars")
                return True
            else:
                print_test(f"{service_name} page content", 'WARN', 
                          "Missing expected elements")
                return False
        else:
            print_test(f"{service_name} page content", 'FAIL', 
                      f"Status {response.status_code}")
            return False
    except Exception as e:
        print_test(f"{service_name} page content", 'FAIL', str(e))
        return False


def test_response_time(service_name, service_config):
    """Test service response time."""
    port = service_config['port']
    url = f"http://localhost:{port}/"
    
    try:
        start = time.time()
        response = requests.get(url, timeout=10)
        elapsed = time.time() - start
        
        if elapsed < 2.0:
            print_test(f"{service_name} response time", 'PASS', 
                      f"{elapsed:.3f}s")
            return True
        elif elapsed < 5.0:
            print_test(f"{service_name} response time", 'WARN', 
                      f"{elapsed:.3f}s (slow)")
            return False
        else:
            print_test(f"{service_name} response time", 'FAIL', 
                      f"{elapsed:.3f}s (too slow)")
            return False
    except Exception as e:
        print_test(f"{service_name} response time", 'FAIL', str(e))
        return False


def run_curl_test(service_name, service_config):
    """Run curl test with headers."""
    port = service_config['port']
    
    try:
        cmd = [
            'curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
            f'http://localhost:{port}/'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        status_code = result.stdout.strip()
        
        if status_code == '200':
            print_test(f"{service_name} curl test", 'PASS', f"HTTP {status_code}")
            return True
        else:
            print_test(f"{service_name} curl test", 'FAIL', f"HTTP {status_code}")
            return False
    except Exception as e:
        print_test(f"{service_name} curl test", 'FAIL', str(e))
        return False


def test_analysis_hub_tabs():
    """Test Analysis Hub specific features."""
    print_header("Analysis Hub Specific Tests")
    
    try:
        response = requests.get('http://localhost:8054/_dash-layout', timeout=10)
        layout = response.json()
        layout_str = json.dumps(layout)
        
        # Check for specific tabs
        has_attribution = 'Attribution Analysis' in layout_str
        has_scenario = 'Scenario Testing' in layout_str
        has_portfolio = 'Portfolio Analytics' in layout_str
        
        print_test("Attribution Analysis tab", 'PASS' if has_attribution else 'FAIL')
        print_test("Scenario Testing tab", 'PASS' if has_scenario else 'FAIL')
        print_test("Portfolio Analytics tab", 'PASS' if has_portfolio else 'FAIL')
        
    except Exception as e:
        print_test("Analysis Hub tabs test", 'FAIL', str(e))


def test_portfolio_features():
    """Test Portfolio Dashboard specific features."""
    print_header("Portfolio Dashboard Specific Tests")
    
    try:
        response = requests.get('http://localhost:8056/_dash-layout', timeout=10)
        layout = response.json()
        layout_str = json.dumps(layout)
        
        # Check for specific features
        has_positions = 'Positions' in layout_str or 'positions' in layout_str
        has_performance = 'Performance' in layout_str or 'performance' in layout_str
        has_transactions = 'Transactions' in layout_str or 'transactions' in layout_str
        
        print_test("Positions tab", 'PASS' if has_positions else 'FAIL')
        print_test("Performance tab", 'PASS' if has_performance else 'FAIL')
        print_test("Transactions tab", 'PASS' if has_transactions else 'FAIL')
        
    except Exception as e:
        print_test("Portfolio features test", 'FAIL', str(e))


def test_event_monitor_features():
    """Test Event Monitor specific features."""
    print_header("Event Monitor Specific Tests")
    
    try:
        response = requests.get('http://localhost:8057/_dash-layout', timeout=10)
        layout = response.json()
        layout_str = json.dumps(layout)
        
        # Check for specific features
        has_feed = 'Event Feed' in layout_str or 'events-feed' in layout_str
        has_alerts = 'Alert' in layout_str or 'alert' in layout_str
        
        print_test("Event feed", 'PASS' if has_feed else 'FAIL')
        print_test("Alerts system", 'PASS' if has_alerts else 'FAIL')
        
    except Exception as e:
        print_test("Event Monitor features test", 'FAIL', str(e))


def test_research_lab_features():
    """Test Research Lab specific features."""
    print_header("Research Lab Specific Tests")
    
    try:
        response = requests.get('http://localhost:8058/_dash-layout', timeout=10)
        layout = response.json()
        layout_str = json.dumps(layout)
        
        # Check for specific features
        has_experiments = 'Experiment' in layout_str or 'experiment' in layout_str
        has_results = 'Results' in layout_str or 'results' in layout_str
        
        print_test("Experiments tab", 'PASS' if has_experiments else 'FAIL')
        print_test("Results view", 'PASS' if has_results else 'FAIL')
        
    except Exception as e:
        print_test("Research Lab features test", 'FAIL', str(e))


def main():
    """Run all tests."""
    print_header("Phase 4 Comprehensive Test Suite")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test all services
    for service_key, service_config in SERVICES.items():
        service_name = service_config['name']
        
        print_header(f"Testing {service_name}")
        
        # Basic tests
        test_service_health(service_name, service_config)
        test_response_time(service_name, service_config)
        test_page_content(service_name, service_config)
        test_dash_layout(service_name, service_config)
        test_dash_dependencies(service_name, service_config)
        run_curl_test(service_name, service_config)
    
    # Feature-specific tests
    test_analysis_hub_tabs()
    test_portfolio_features()
    test_event_monitor_features()
    test_research_lab_features()
    
    # Summary
    print_header("Test Summary")
    total = test_results['passed'] + test_results['failed'] + test_results['warnings']
    print(f"{GREEN}Passed:{RESET}   {test_results['passed']}/{total}")
    print(f"{RED}Failed:{RESET}   {test_results['failed']}/{total}")
    print(f"{YELLOW}Warnings:{RESET} {test_results['warnings']}/{total}")
    
    success_rate = (test_results['passed'] / total * 100) if total > 0 else 0
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    if test_results['failed'] == 0:
        print(f"\n{GREEN}All critical tests passed! ✓{RESET}")
        return 0
    else:
        print(f"\n{RED}Some tests failed. Review logs above.{RESET}")
        return 1


if __name__ == '__main__':
    sys.exit(main())

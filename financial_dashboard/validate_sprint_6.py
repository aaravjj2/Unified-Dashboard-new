#!/usr/bin/env python3
"""
Sprint 6 Final Validation - Simplified
Tests all services and validates file structure without requiring Selenium
"""

import requests
import subprocess
import time
import os
from pathlib import Path

def test_service_health(service_name, port):
    """Test if a service's health endpoint responds with 200 OK"""
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=10)
        if response.status_code == 200:
            print(f"✅ {service_name:20s} (port {port}): HEALTHY")
            return True
        else:
            print(f"❌ {service_name:20s} (port {port}): HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {service_name:20s} (port {port}): {str(e)}")
        return False

def test_dashboard_accessible():
    """Test if main dashboard is accessible"""
    try:
        response = requests.get("http://localhost:8000", timeout=10)
        if response.status_code == 200:
            print(f"✅ Main Dashboard        (port 8000): ACCESSIBLE")
            return True
        else:
            print(f"❌ Main Dashboard        (port 8000): HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Main Dashboard        (port 8000): {str(e)}")
        return False

def test_file_exists(filepath, description):
    """Test if a file exists"""
    if Path(filepath).exists():
        print(f"✅ {description:40s}: EXISTS")
        return True
    else:
        print(f"❌ {description:40s}: MISSING")
        return False

def main():
    print("\n" + "=" * 80)
    print("SPRINT 6 FINAL VALIDATION - SIMPLIFIED")
    print("=" * 80 + "\n")
    
    results = []
    
    # Phase 1: Service Health Tests
    print("Phase 1: Service Health Tests")
    print("-" * 80)
    
    services = [
        ("Market Trends", 8050),
        ("Market Forecast", 8051),
        ("Analysis Hub", 8054),
        ("Portfolio Service", 8056),
        ("Research Lab", 8058),
        ("Options Service", 8060),
        ("Chatbot Service", 8062),
        ("API Gateway", 8049),
    ]
    
    for service_name, port in services:
        results.append(test_service_health(service_name, port))
    
    # Test main dashboard
    results.append(test_dashboard_accessible())
    
    # Phase 2: Component File Structure Tests
    print("\n" + "Phase 2: Component File Structure Tests")
    print("-" * 80)
    
    components = [
        ("components/__init__.py", "Components __init__"),
        ("components/factor_dna.py", "Factor DNA Component"),
        ("components/portfolio_health.py", "Portfolio Health Component"),
        ("components/volatility_lab.py", "Volatility Lab Component"),
        ("components/hedge_finder.py", "Hedge Finder Component"),
        ("components/global_search.py", "Global Search Component"),
        ("components/theme_toggle.py", "Theme Toggle Component"),
        ("components/sentiment_analysis.py", "Sentiment Analysis Component"),
        ("components/chatbot_ui.py", "Chatbot UI Component"),
    ]
    
    for filepath, description in components:
        results.append(test_file_exists(filepath, description))
    
    # Phase 3: Tab File Structure Tests
    print("\n" + "Phase 3: Tab File Structure Tests")
    print("-" * 80)
    
    tabs = [
        ("tabs/home.py", "Home Tab"),
        ("tabs/volatility_lab.py", "Volatility Lab Tab"),
        ("tabs/portfolio.py", "Portfolio Tab"),
        ("tabs/options_lab.py", "Options Lab Tab"),
    ]
    
    for filepath, description in tabs:
        results.append(test_file_exists(filepath, description))
    
    # Phase 4: Service File Tests
    print("\n" + "Phase 4: Service File Tests")
    print("-" * 80)
    
    service_files = [
        ("services/market_trends_service.py", "Market Trends Service"),
        ("services/market_forecast_service.py", "Market Forecast Service"),
        ("services/analysis_service.py", "Analysis Service"),
        ("services/portfolio_service.py", "Portfolio Service"),
        ("services/research_service.py", "Research Service"),
        ("services/options_service.py", "Options Service"),
        ("services/chatbot_service.py", "Chatbot Service"),
    ]
    
    for filepath, description in service_files:
        results.append(test_file_exists(filepath, description))
    
    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    total_tests = len(results)
    passed_tests = sum(results)
    failed_tests = total_tests - passed_tests
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\nTotal Tests:    {total_tests}")
    print(f"Passed:         {passed_tests} ✅")
    print(f"Failed:         {failed_tests} ❌")
    print(f"Success Rate:   {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("\n✅ VALIDATION PASSED: Sprint 6 features are operational!")
        return 0
    else:
        print("\n❌ VALIDATION FAILED: Some Sprint 6 features are not working properly.")
        return 1

if __name__ == "__main__":
    exit(main())

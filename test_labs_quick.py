#!/usr/bin/env python3
"""Quick test script to analyze Strategy Lab, Research Lab, and Volatility Lab issues."""

import sys
import time
from playwright.sync_api import sync_playwright

DASHBOARD_URL = "http://localhost:8051"


def test_strategy_lab(page):
    """Test Strategy Lab tab functionality."""
    print("\n=== Testing Strategy Lab ===")
    issues = []
    
    try:
        # Click on Strategy Lab tab
        page.click('text=Strategy Lab', timeout=5000)
        time.sleep(2)
        
        # Check if the tab content loaded
        strategy_content = page.query_selector('.container-fluid')
        if strategy_content:
            print("  ✓ Strategy Lab content container found")
        else:
            issues.append("Strategy Lab content container not found")
        
        # Check for subtabs
        subtabs = page.query_selector_all('[id="strategy-lab-tabs"] .nav-link')
        print(f"  ✓ Found {len(subtabs)} subtabs")
        if len(subtabs) < 6:
            issues.append(f"Expected 6 subtabs, found {len(subtabs)}")
        
        # Check for key UI elements
        setup_tab = page.query_selector('[data-bs-target="#setup-tab"]') or page.query_selector('text=Setup')
        if setup_tab:
            print("  ✓ Setup tab found")
        else:
            issues.append("Setup tab not found")
        
        # Check for backtest button
        backtest_btn = page.query_selector('#sl-run-backtest-btn') or page.query_selector('text=Run Backtest')
        if backtest_btn:
            print("  ✓ Backtest button found")
        else:
            issues.append("Backtest button not found")
        
        # Check for strategy type dropdown
        strategy_dropdown = page.query_selector('#sl-strategy-type')
        if strategy_dropdown:
            print("  ✓ Strategy type dropdown found")
        else:
            issues.append("Strategy type dropdown not found")
            
        # Take screenshot
        page.screenshot(path="test_strategy_lab.png")
        print("  ✓ Screenshot saved: test_strategy_lab.png")
        
    except Exception as e:
        issues.append(f"Error testing Strategy Lab: {str(e)}")
    
    return issues


def test_research_lab(page):
    """Test Research Lab tab functionality."""
    print("\n=== Testing Research Lab ===")
    issues = []
    
    try:
        # Click on Research Lab tab
        page.click('text=Research Lab', timeout=5000)
        time.sleep(2)
        
        # Check if the tab content loaded
        research_content = page.query_selector('.container-fluid')
        if research_content:
            print("  ✓ Research Lab content container found")
        else:
            issues.append("Research Lab content container not found")
        
        # Check for subtabs
        subtabs = page.query_selector_all('[id*="research"] .nav-link') or page.query_selector_all('.nav-tabs .nav-link')
        print(f"  ✓ Found {len(subtabs)} subtabs/elements")
        
        # Check for key UI elements
        scan_btn = page.query_selector('#rl-scan-run-btn') or page.query_selector('text=Run Scan') or page.query_selector('text=Market Scan')
        if scan_btn:
            print("  ✓ Scan functionality found")
        else:
            issues.append("Scan functionality not found")
        
        # Check for brief management
        brief_section = page.query_selector('#rl-brief-list') or page.query_selector('text=Research Briefs')
        if brief_section:
            print("  ✓ Brief management section found")
        else:
            issues.append("Brief management section not found")
            
        # Take screenshot
        page.screenshot(path="test_research_lab.png")
        print("  ✓ Screenshot saved: test_research_lab.png")
        
    except Exception as e:
        issues.append(f"Error testing Research Lab: {str(e)}")
    
    return issues


def test_volatility_lab(page):
    """Test Volatility Lab tab functionality."""
    print("\n=== Testing Volatility Lab ===")
    issues = []
    
    try:
        # Click on Volatility Lab tab
        page.click('text=Volatility Lab', timeout=5000)
        time.sleep(2)
        
        # Check if the tab content loaded
        vol_content = page.query_selector('.volatility-lab-container') or page.query_selector('.container-fluid')
        if vol_content:
            print("  ✓ Volatility Lab content container found")
        else:
            issues.append("Volatility Lab content container not found")
        
        # Check for subtabs
        subtabs = page.query_selector_all('[id="vl-subtabs"] .nav-link') or page.query_selector_all('.nav-tabs .nav-link')
        print(f"  ✓ Found {len(subtabs)} subtabs")
        if len(subtabs) < 4:
            issues.append(f"Expected 4 subtabs, found {len(subtabs)}")
        
        # Check for key UI elements
        compute_btn = page.query_selector('#vl-calc-run-btn') or page.query_selector('text=Compute Surface')
        if compute_btn:
            print("  ✓ Compute Surface button found")
        else:
            issues.append("Compute Surface button not found")
        
        # Check for ticker input
        ticker_input = page.query_selector('#vl-calc-ticker')
        if ticker_input:
            print("  ✓ Ticker input found")
        else:
            issues.append("Ticker input not found")
        
        # Check for heatmap
        heatmap = page.query_selector('#vl-heatmap')
        if heatmap:
            print("  ✓ Heatmap element found")
        else:
            issues.append("Heatmap element not found")
            
        # Take screenshot
        page.screenshot(path="test_volatility_lab.png")
        print("  ✓ Screenshot saved: test_volatility_lab.png")
        
    except Exception as e:
        issues.append(f"Error testing Volatility Lab: {str(e)}")
    
    return issues


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Dashboard Labs")
    print("=" * 60)
    
    all_issues = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Navigate to dashboard
            print(f"\nNavigating to {DASHBOARD_URL}...")
            page.goto(DASHBOARD_URL, timeout=30000)
            page.wait_for_load_state('networkidle', timeout=20000)
            print("  ✓ Dashboard loaded")
            
            # Take initial screenshot
            page.screenshot(path="test_dashboard_initial.png")
            print("  ✓ Initial screenshot saved")
            
            # Test each lab
            all_issues['Strategy Lab'] = test_strategy_lab(page)
            all_issues['Research Lab'] = test_research_lab(page)
            all_issues['Volatility Lab'] = test_volatility_lab(page)
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            all_issues['General'] = [str(e)]
        finally:
            browser.close()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY OF ISSUES")
    print("=" * 60)
    
    total_issues = 0
    for lab, issues in all_issues.items():
        if issues:
            print(f"\n{lab}: {len(issues)} issues")
            for issue in issues:
                print(f"  - {issue}")
            total_issues += len(issues)
        else:
            print(f"\n{lab}: ✓ No issues found")
    
    print(f"\nTotal issues: {total_issues}")
    return total_issues


if __name__ == '__main__':
    sys.exit(main())

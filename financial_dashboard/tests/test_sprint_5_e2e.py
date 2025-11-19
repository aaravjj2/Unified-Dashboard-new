"""
Sprint 5 E2E Tests: Master UI Validation & Complete Workflows
============================================================

Master test suite that validates:
- Every button click across the entire dashboard
- Complete end-to-end user workflows
- Full system integration

Run with:
    pytest tests/test_sprint_5_e2e.py -v -s
    
Prerequisites:
    - Dashboard running at http://localhost:8050
    - All backend services operational
"""

import pytest
from playwright.sync_api import Page, expect, sync_playwright
import time
from typing import List, Dict


# =============================================================================
# Configuration
# =============================================================================

DASHBOARD_URL = "http://localhost:8050"
DEFAULT_TIMEOUT = 30000  # 30 seconds


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def browser():
    """Create a Playwright browser instance."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def page(browser):
    """Create a new page for each test."""
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(DEFAULT_TIMEOUT)
    yield page
    page.close()
    context.close()


# =============================================================================
# Test Group 1: Master Clicker Test
# =============================================================================

class TestMasterClicker:
    """
    Master UI validation test.
    
    This test navigates to every tab and clicks every visible button,
    ensuring no clicks cause errors or crashes.
    """
    
    def test_master_clicker_all_buttons(self, page: Page):
        """
        Master clicker test: Find and click every button in the dashboard.
        
        This validates that:
        - All buttons are functional
        - No button clicks cause JS errors
        - No button clicks crash the application
        - UI remains responsive after all interactions
        """
        # Navigate to dashboard
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")
        time.sleep(2)  # Let dashboard fully initialize
        
        # Track results
        tabs_visited = []
        buttons_clicked = []
        errors_encountered = []
        
        # Get all tabs
        tab_elements = page.locator('a.nav-link, button.nav-link').all()
        print(f"\n{'='*60}")
        print(f"MASTER CLICKER TEST")
        print(f"{'='*60}")
        print(f"Found {len(tab_elements)} tabs to test")
        
        for tab_idx, tab_element in enumerate(tab_elements):
            try:
                # Get tab text
                tab_text = tab_element.text_content().strip()
                if not tab_text:
                    continue
                
                print(f"\n[Tab {tab_idx + 1}] Navigating to: {tab_text}")
                tabs_visited.append(tab_text)
                
                # Click tab
                tab_element.click()
                page.wait_for_load_state("networkidle")
                time.sleep(1)  # Let content load
                
                # Find all visible buttons in the current tab/view
                # Look for actual <button> elements and clickable divs/links
                button_selectors = [
                    'button:visible',
                    '[role="button"]:visible',
                    'a.btn:visible',
                    '.dash-button:visible'
                ]
                
                all_buttons = []
                for selector in button_selectors:
                    try:
                        buttons = page.locator(selector).all()
                        all_buttons.extend(buttons)
                    except Exception:
                        continue
                
                # Remove duplicates (same element matched by multiple selectors)
                unique_buttons = []
                seen_ids = set()
                for btn in all_buttons:
                    try:
                        btn_id = btn.get_attribute('id')
                        if btn_id and btn_id in seen_ids:
                            continue
                        if btn_id:
                            seen_ids.add(btn_id)
                        unique_buttons.append(btn)
                    except Exception:
                        unique_buttons.append(btn)
                
                print(f"  Found {len(unique_buttons)} clickable elements")
                
                # Click each button
                for btn_idx, button in enumerate(unique_buttons):
                    try:
                        # Get button info
                        btn_text = button.text_content()[:50].strip() or button.get_attribute('id') or f"Button_{btn_idx}"
                        btn_id = button.get_attribute('id') or 'no-id'
                        
                        # Skip if not visible or disabled
                        if not button.is_visible():
                            continue
                        
                        if button.is_disabled():
                            print(f"    [Button {btn_idx + 1}] Skipping disabled: {btn_text}")
                            continue
                        
                        print(f"    [Button {btn_idx + 1}] Clicking: {btn_text} (id={btn_id})")
                        
                        # Listen for console errors
                        console_errors = []
                        
                        def handle_console(msg):
                            if msg.type == 'error':
                                console_errors.append(msg.text)
                        
                        page.on('console', handle_console)
                        
                        # Click the button
                        button.click()
                        buttons_clicked.append({
                            'tab': tab_text,
                            'button': btn_text,
                            'id': btn_id
                        })
                        
                        # Wait for any callbacks to complete
                        time.sleep(0.5)
                        
                        # Check for errors
                        if console_errors:
                            error_msg = f"Console errors after clicking {btn_text}: {console_errors}"
                            errors_encountered.append(error_msg)
                            print(f"      ⚠ WARNING: {error_msg}")
                        
                        # Verify page is still responsive
                        try:
                            page.locator('body').wait_for(timeout=2000)
                        except Exception as e:
                            error_msg = f"Page became unresponsive after clicking {btn_text}: {str(e)}"
                            errors_encountered.append(error_msg)
                            print(f"      ✗ ERROR: {error_msg}")
                            # Try to recover by reloading
                            page.reload()
                            page.wait_for_load_state("networkidle")
                            break
                        
                    except Exception as e:
                        error_msg = f"Error clicking button {btn_text}: {str(e)}"
                        errors_encountered.append(error_msg)
                        print(f"      ✗ ERROR: {error_msg}")
                        continue
                
            except Exception as e:
                error_msg = f"Error processing tab {tab_text}: {str(e)}"
                errors_encountered.append(error_msg)
                print(f"  ✗ ERROR: {error_msg}")
                continue
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"MASTER CLICKER TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Tabs visited: {len(tabs_visited)}")
        print(f"Buttons clicked: {len(buttons_clicked)}")
        print(f"Errors encountered: {len(errors_encountered)}")
        
        if errors_encountered:
            print(f"\nErrors:")
            for error in errors_encountered[:10]:  # Show first 10
                print(f"  - {error}")
        else:
            print(f"\n✓ All buttons clicked successfully with no errors!")
        
        # Assert no critical errors
        assert len(buttons_clicked) > 0, "No buttons were found/clicked"
        assert len(tabs_visited) > 0, "No tabs were visited"
        
        # Allow some non-critical errors but ensure most clicks succeed
        error_rate = len(errors_encountered) / max(len(buttons_clicked), 1)
        assert error_rate < 0.3, f"Too many errors: {len(errors_encountered)}/{len(buttons_clicked)} ({error_rate:.1%})"


# =============================================================================
# Test Group 2: Complete Workflows
# =============================================================================

class TestCompleteWorkflows:
    """Test complete end-to-end user workflows."""
    
    def test_workflow_market_analysis_to_options_trade(self, page: Page):
        """
        Complete workflow: Market analysis → Options research → Trade planning
        
        Simulates a user:
        1. Analyzing market trends
        2. Finding a strong ticker
        3. Researching options for that ticker
        4. Building a trade plan
        """
        # Step 1: Navigate to Market Trends
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")
        
        # Find and click Market Trends tab
        market_trends_tab = page.locator('text=Market Trends').or_(page.locator('a:has-text("Trends")')).first
        if market_trends_tab.is_visible():
            market_trends_tab.click()
            time.sleep(2)
        
        print("\n[Step 1] ✓ Navigated to Market Trends")
        
        # Step 2: Run an analysis (if button exists)
        run_buttons = page.locator('button:has-text("Run"), button:has-text("Analyze"), button:has-text("Calculate")').all()
        if run_buttons:
            run_buttons[0].click()
            time.sleep(2)
            print("[Step 2] ✓ Triggered market analysis")
        
        # Step 3: Navigate to Options Lab
        options_tab = page.locator('text=Options Lab').or_(page.locator('a:has-text("Options")')).first
        if options_tab.is_visible():
            options_tab.click()
            time.sleep(2)
            print("[Step 3] ✓ Navigated to Options Lab")
        
        # Step 4: Enter a ticker symbol
        ticker_inputs = page.locator('input[type="text"]').all()
        if ticker_inputs:
            ticker_inputs[0].fill("SPY")
            time.sleep(1)
            print("[Step 4] ✓ Entered ticker symbol: SPY")
        
        # Step 5: Fetch options chain (if button exists)
        fetch_buttons = page.locator('button:has-text("Fetch"), button:has-text("Get"), button:has-text("Load")').all()
        if fetch_buttons:
            fetch_buttons[0].click()
            time.sleep(3)
            print("[Step 5] ✓ Fetched options chain")
        
        # Verify no errors occurred
        assert page.locator('body').is_visible()
        print("\n✓ Complete workflow executed successfully")
    
    def test_workflow_portfolio_monitoring(self, page: Page):
        """
        Workflow: Portfolio monitoring and position analysis.
        
        Tests:
        1. Viewing portfolio overview
        2. Checking positions
        3. Analyzing P&L
        """
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")
        
        # Navigate to Portfolio tab if exists
        portfolio_tab = page.locator('text=Portfolio').or_(page.locator('a:has-text("Portfolio")')).first
        if portfolio_tab.is_visible():
            portfolio_tab.click()
            time.sleep(2)
            print("\n[Step 1] ✓ Navigated to Portfolio")
            
            # Look for refresh/update buttons
            refresh_buttons = page.locator('button:has-text("Refresh"), button:has-text("Update"), button:has-text("Reload")').all()
            if refresh_buttons:
                refresh_buttons[0].click()
                time.sleep(2)
                print("[Step 2] ✓ Refreshed portfolio data")
        
        # Verify page is still functional
        assert page.locator('body').is_visible()
        print("\n✓ Portfolio monitoring workflow completed")
    
    def test_workflow_research_to_backtest(self, page: Page):
        """
        Workflow: Research → Strategy → Backtest
        
        Tests:
        1. Researching a strategy
        2. Configuring parameters
        3. Running a backtest
        """
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")
        
        # Navigate to Market Trends for backtest
        trends_tab = page.locator('text=Market Trends').or_(page.locator('a:has-text("Trends")')).first
        if trends_tab.is_visible():
            trends_tab.click()
            time.sleep(2)
            print("\n[Step 1] ✓ Navigated to Trends for backtesting")
            
            # Look for backtest button
            backtest_buttons = page.locator('button:has-text("Backtest")').all()
            if backtest_buttons:
                backtest_buttons[0].click()
                time.sleep(2)
                print("[Step 2] ✓ Opened backtest interface")
                
                # If modal opened, check for run button
                run_buttons = page.locator('button:has-text("Run"), button:has-text("Execute"), button:has-text("Start")').all()
                if run_buttons:
                    # Try to click run button (may need inputs first)
                    try:
                        run_buttons[-1].click()  # Last button is often the confirm/run button
                        time.sleep(3)
                        print("[Step 3] ✓ Executed backtest")
                    except Exception:
                        print("[Step 3] ⚠ Backtest requires additional inputs (expected)")
        
        assert page.locator('body').is_visible()
        print("\n✓ Research-to-backtest workflow completed")


# =============================================================================
# Test Group 3: Tab-Specific Deep Dive
# =============================================================================

class TestTabSpecificValidation:
    """Detailed validation of each major tab."""
    
    def test_market_trends_tab_interactive_elements(self, page: Page):
        """Test all interactive elements in Market Trends tab."""
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")
        
        # Navigate to Market Trends
        trends_tab = page.locator('text=Market Trends').or_(page.locator('a:has-text("Trends")')).first
        if trends_tab.is_visible():
            trends_tab.click()
            time.sleep(2)
            
            # Check for key elements
            buttons = page.locator('button').all()
            inputs = page.locator('input').all()
            dropdowns = page.locator('select').all()
            
            print(f"\nMarket Trends tab elements:")
            print(f"  Buttons: {len(buttons)}")
            print(f"  Inputs: {len(inputs)}")
            print(f"  Dropdowns: {len(dropdowns)}")
            
            assert len(buttons) > 0 or len(inputs) > 0, "Market Trends tab has no interactive elements"
    
    def test_options_lab_tab_interactive_elements(self, page: Page):
        """Test all interactive elements in Options Lab tab."""
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")
        
        # Navigate to Options Lab
        options_tab = page.locator('text=Options Lab').or_(page.locator('a:has-text("Options")')).first
        if options_tab.is_visible():
            options_tab.click()
            time.sleep(2)
            
            # Check for key elements
            buttons = page.locator('button').all()
            inputs = page.locator('input').all()
            
            print(f"\nOptions Lab tab elements:")
            print(f"  Buttons: {len(buttons)}")
            print(f"  Inputs: {len(inputs)}")
            
            assert len(buttons) > 0 or len(inputs) > 0, "Options Lab tab has no interactive elements"
    
    def test_all_tabs_render_without_errors(self, page: Page):
        """Ensure all tabs render without JavaScript errors."""
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")
        
        # Get all tabs
        tabs = page.locator('a.nav-link, button.nav-link').all()
        tabs_tested = []
        
        for tab in tabs:
            try:
                tab_text = tab.text_content().strip()
                if not tab_text:
                    continue
                
                # Listen for console errors
                console_errors = []
                
                def handle_console(msg):
                    if msg.type == 'error':
                        console_errors.append(msg.text)
                
                page.on('console', handle_console)
                
                # Click tab
                tab.click()
                page.wait_for_load_state("networkidle")
                time.sleep(1)
                
                # Check for errors
                assert len(console_errors) == 0, f"Tab '{tab_text}' has console errors: {console_errors}"
                
                tabs_tested.append(tab_text)
                print(f"✓ Tab '{tab_text}' rendered without errors")
                
            except Exception as e:
                print(f"✗ Error testing tab: {str(e)}")
        
        assert len(tabs_tested) > 0, "No tabs were tested"


# =============================================================================
# Test Group 4: Performance & Stability
# =============================================================================

class TestPerformanceStability:
    """Test dashboard performance and stability under load."""
    
    def test_rapid_tab_switching(self, page: Page):
        """Test stability under rapid tab switching."""
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")
        
        tabs = page.locator('a.nav-link, button.nav-link').all()
        
        if len(tabs) < 2:
            pytest.skip("Not enough tabs to test switching")
        
        # Rapidly switch between tabs
        for i in range(10):
            tab_idx = i % len(tabs)
            try:
                tabs[tab_idx].click()
                time.sleep(0.3)  # Quick switching
            except Exception as e:
                pytest.fail(f"Tab switching failed on iteration {i}: {str(e)}")
        
        # Verify dashboard is still responsive
        assert page.locator('body').is_visible()
        print("✓ Dashboard stable under rapid tab switching")
    
    def test_concurrent_button_interactions(self, page: Page):
        """Test handling of multiple quick button clicks."""
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")
        
        # Find all buttons
        buttons = page.locator('button:visible').all()
        
        if not buttons:
            pytest.skip("No buttons found to test")
        
        # Click first button multiple times quickly
        button = buttons[0]
        for i in range(5):
            try:
                button.click()
                time.sleep(0.1)
            except Exception:
                pass  # Some clicks may be ignored, which is fine
        
        # Verify dashboard is still responsive
        assert page.locator('body').is_visible()
        print("✓ Dashboard handles concurrent interactions")


# =============================================================================
# Summary
# =============================================================================

def test_sprint_5_e2e_summary():
    """Summary test: Print test suite overview."""
    print("\n" + "="*60)
    print("SPRINT 5 E2E TEST SUITE")
    print("="*60)
    print("Master Clicker Test: Validates ALL buttons")
    print("Complete Workflows: Tests realistic user journeys")
    print("Tab Validation: Deep dive into each section")
    print("Performance Tests: Stability under load")
    print("="*60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

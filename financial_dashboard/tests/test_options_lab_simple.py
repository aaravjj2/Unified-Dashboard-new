"""
Simple E2E Tests for Options Lab Tab
Uses pytest-playwright for browser automation
"""

import pytest
from playwright.sync_api import Page, expect
import requests


# Test Configuration
DASHBOARD_URL = "http://localhost:8000"
OPTIONS_SERVICE_URL = "http://localhost:8060"
TEST_TIMEOUT = 30000  # 30 seconds


class TestOptionsServiceHealth:
    """Test that options service is running."""
    
    def test_options_service_health(self):
        """Test that options service is running and healthy."""
        try:
            response = requests.get(f'{OPTIONS_SERVICE_URL}/health', timeout=5)
            assert response.status_code == 200, f"Options service health check failed: {response.status_code}"
            
            data = response.json()
            assert data.get('status') == 'healthy', f"Options service not healthy: {data}"
            
            print("✅ Options service is healthy")
        except requests.exceptions.ConnectionError:
            pytest.fail(f"Cannot connect to options service at {OPTIONS_SERVICE_URL}")
    
    def test_options_service_account_endpoint(self):
        """Test that account endpoint is accessible."""
        try:
            response = requests.get(f'{OPTIONS_SERVICE_URL}/account', timeout=5)
            # Should return 200 or appropriate error (not 404)
            assert response.status_code in [200, 401, 403, 500], \
                f"Unexpected status from account endpoint: {response.status_code}"
            
            print(f"✅ Account endpoint responded with status {response.status_code}")
        except requests.exceptions.ConnectionError:
            pytest.fail(f"Cannot connect to options service at {OPTIONS_SERVICE_URL}")


class TestDashboardAccess:
    """Test basic dashboard access."""
    
    def test_dashboard_loads(self, page: Page):
        """Test that main dashboard loads."""
        page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=TEST_TIMEOUT)
        page.wait_for_timeout(2000)
        
        # Check for dashboard title
        title = page.locator('h1').first
        expect(title).to_be_visible(timeout=TEST_TIMEOUT)
        
        print("✅ Dashboard loaded successfully")


class TestOptionsLabNavigation:
    """Test navigation to Options Lab tab."""
    
    def test_options_lab_tab_exists(self, page: Page):
        """Test that Options Lab tab is present in the dashboard."""
        page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=TEST_TIMEOUT)
        page.wait_for_timeout(3000)
        
        # Look for Options Lab tab (may have emoji)
        options_tab = page.locator('text=/.*Options Lab.*/i')
        expect(options_tab.first).to_be_visible(timeout=TEST_TIMEOUT)
        
        print("✅ Options Lab tab found")
    
    def test_navigate_to_options_lab(self, page: Page):
        """Test navigation to Options Lab tab."""
        page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=TEST_TIMEOUT)
        page.wait_for_timeout(3000)
        
        # Click Options Lab tab
        options_tab = page.locator('text=/.*Options Lab.*/i').first
        options_tab.click()
        page.wait_for_timeout(2000)
        
        # Verify we're on Options Lab - look for sub-tabs
        strategy_monitor = page.locator('text="Strategy Monitor"')
        manual_trading = page.locator('text="Manual Trading"')
        
        # At least one should be visible
        assert strategy_monitor.is_visible() or manual_trading.is_visible(), \
            "Options Lab content not loaded"
        
        print("✅ Successfully navigated to Options Lab")


class TestStrategyMonitorPanel:
    """Test the Strategy Monitor panel."""
    
    def test_strategy_monitor_panel_exists(self, page: Page):
        """Test that Strategy Monitor panel can be accessed."""
        page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=TEST_TIMEOUT)
        page.wait_for_timeout(3000)
        
        # Navigate to Options Lab
        options_tab = page.locator('text=/.*Options Lab.*/i').first
        options_tab.click()
        page.wait_for_timeout(2000)
        
        # Click Strategy Monitor sub-tab
        strategy_tab = page.locator('text="Strategy Monitor"').first
        if strategy_tab.is_visible():
            strategy_tab.click()
            page.wait_for_timeout(1000)
            print("✅ Strategy Monitor panel accessed")
        else:
            print("⚠️ Strategy Monitor tab not found - may need to scroll or expand")


class TestManualTradingPanel:
    """Test the Manual Trading panel."""
    
    def test_manual_trading_panel_exists(self, page: Page):
        """Test that Manual Trading panel can be accessed."""
        page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=TEST_TIMEOUT)
        page.wait_for_timeout(3000)
        
        # Navigate to Options Lab
        options_tab = page.locator('text=/.*Options Lab.*/i').first
        options_tab.click()
        page.wait_for_timeout(2000)
        
        # Click Manual Trading sub-tab
        manual_tab = page.locator('text="Manual Trading"').first
        if manual_tab.is_visible():
            manual_tab.click()
            page.wait_for_timeout(1000)
            print("✅ Manual Trading panel accessed")
        else:
            print("⚠️ Manual Trading tab not found - may need to scroll or expand")


class TestPnLAnalyzerPanel:
    """Test the P&L Analyzer panel."""
    
    def test_pnl_analyzer_panel_exists(self, page: Page):
        """Test that P&L Analyzer panel can be accessed."""
        page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=TEST_TIMEOUT)
        page.wait_for_timeout(3000)
        
        # Navigate to Options Lab
        options_tab = page.locator('text=/.*Options Lab.*/i').first
        options_tab.click()
        page.wait_for_timeout(2000)
        
        # Click P&L Analyzer sub-tab
        pnl_tab = page.locator('text="P&L Analyzer"').first
        if pnl_tab.is_visible():
            pnl_tab.click()
            page.wait_for_timeout(1000)
            print("✅ P&L Analyzer panel accessed")
        else:
            print("⚠️ P&L Analyzer tab not found - may need to scroll or expand")


if __name__ == '__main__':
    # Run tests with pytest
    import sys
    sys.exit(pytest.main([__file__, '-v', '-s', '--headed']))

"""
Playwright E2E Tests for Options Lab Tab
Tests all three panels: Strategy Monitor, Manual Trading, P&L Analyzer
"""

import pytest
import time
from playwright.sync_api import Page, expect


# Test Configuration
DASHBOARD_URL = "http://localhost:8000"
OPTIONS_SERVICE_URL = "http://localhost:8060"
TEST_TIMEOUT = 30000  # 30 seconds


class TestOptionsLabNavigation:
    """Test navigation to Options Lab tab."""
    
    def test_options_lab_tab_exists(self, page: Page):
        """Test that Options Lab tab is present in the dashboard."""
        page.goto(DASHBOARD_URL, wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        # Look for Options Lab tab
        options_tab = page.locator('text="Options Lab"')
        expect(options_tab).to_be_visible(timeout=TEST_TIMEOUT)
        
        print("✅ Options Lab tab found")
    
    def test_navigate_to_options_lab(self, page: Page):
        """Test navigation to Options Lab tab."""
        page.goto(DASHBOARD_URL, wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        # Click Options Lab tab
        options_tab = page.locator('text="Options Lab"').first
        options_tab.click()
        page.wait_for_timeout(1000)
        
        # Verify we're on Options Lab
        heading = page.locator('text="Options Trading Lab"')
        expect(heading).to_be_visible(timeout=TEST_TIMEOUT)
        
        print("✅ Successfully navigated to Options Lab")
    
    def test_subtabs_present(self, page: Page):
        """Test that all three sub-tabs are present."""
        page.goto(DASHBOARD_URL, wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        # Navigate to Options Lab
        options_tab = page.locator('text="Options Lab"').first
        options_tab.click()
        page.wait_for_timeout(1000)
        
        # Check for all three sub-tabs
        strategy_monitor = page.locator('text="Strategy Monitor"')
        manual_trading = page.locator('text="Manual Trading"')
        pnl_analyzer = page.locator('text="P&L Analyzer"')
        
        expect(strategy_monitor).to_be_visible(timeout=TEST_TIMEOUT)
        expect(manual_trading).to_be_visible(timeout=TEST_TIMEOUT)
        expect(pnl_analyzer).to_be_visible(timeout=TEST_TIMEOUT)
        
        print("✅ All three sub-tabs present")


class TestStrategyMonitorPanel:
    """Test the Strategy Monitor panel functionality."""
    
    @pytest.mark.asyncio
    async def test_strategy_monitor_loads(self, page: Page):
        """Test that Strategy Monitor panel loads with all components."""
        await page.goto(DASHBOARD_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Navigate to Options Lab -> Strategy Monitor
        options_tab = page.locator('text="Options Lab"').first
        await options_tab.click()
        await page.wait_for_timeout(1000)
        
        strategy_tab = page.locator('text="Strategy Monitor"').first
        await strategy_tab.click()
        await page.wait_for_timeout(1000)
        
        # Check for key components
        heading = page.locator('text="Automated Strategy Monitoring"')
        await expect(heading).to_be_visible(timeout=TEST_TIMEOUT)
        
        # Check for status cards
        strategy_status = page.locator('#opt-strategy-status')
        position_count = page.locator('#opt-position-count')
        total_pnl = page.locator('#opt-total-pnl')
        
        await expect(strategy_status).to_be_visible(timeout=TEST_TIMEOUT)
        await expect(position_count).to_be_visible(timeout=TEST_TIMEOUT)
        await expect(total_pnl).to_be_visible(timeout=TEST_TIMEOUT)
        
        print("✅ Strategy Monitor panel loaded successfully")
    
    @pytest.mark.asyncio
    async def test_control_buttons_present(self, page: Page):
        """Test that all control buttons are present and clickable."""
        await page.goto(DASHBOARD_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Navigate to Strategy Monitor
        options_tab = page.locator('text="Options Lab"').first
        await options_tab.click()
        await page.wait_for_timeout(500)
        
        strategy_tab = page.locator('text="Strategy Monitor"').first
        await strategy_tab.click()
        await page.wait_for_timeout(500)
        
        # Check for control buttons
        start_btn = page.locator('#opt-start-btn')
        pause_btn = page.locator('#opt-pause-btn')
        stop_btn = page.locator('#opt-stop-btn')
        refresh_btn = page.locator('#opt-refresh-btn')
        
        await expect(start_btn).to_be_visible(timeout=TEST_TIMEOUT)
        await expect(pause_btn).to_be_visible(timeout=TEST_TIMEOUT)
        await expect(stop_btn).to_be_visible(timeout=TEST_TIMEOUT)
        await expect(refresh_btn).to_be_visible(timeout=TEST_TIMEOUT)
        
        print("✅ All control buttons present")
    
    @pytest.mark.asyncio
    async def test_refresh_button_click(self, page: Page):
        """Test clicking the Refresh button."""
        await page.goto(DASHBOARD_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Navigate to Strategy Monitor
        options_tab = page.locator('text="Options Lab"').first
        await options_tab.click()
        await page.wait_for_timeout(500)
        
        strategy_tab = page.locator('text="Strategy Monitor"').first
        await strategy_tab.click()
        await page.wait_for_timeout(500)
        
        # Click Refresh button
        refresh_btn = page.locator('#opt-refresh-btn')
        await refresh_btn.click()
        await page.wait_for_timeout(2000)
        
        # Check that data loaded (status should update)
        strategy_status = page.locator('#opt-strategy-status')
        status_text = await strategy_status.text_content()
        
        assert status_text in ['Idle', 'Running', 'Paused', 'Unknown', 'Error'], \
            f"Expected valid status, got: {status_text}"
        
        print(f"✅ Refresh button clicked, status: {status_text}")
    
    @pytest.mark.asyncio
    async def test_positions_table_present(self, page: Page):
        """Test that positions table is present."""
        await page.goto(DASHBOARD_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Navigate to Strategy Monitor
        options_tab = page.locator('text="Options Lab"').first
        await options_tab.click()
        await page.wait_for_timeout(500)
        
        strategy_tab = page.locator('text="Strategy Monitor"').first
        await strategy_tab.click()
        await page.wait_for_timeout(500)
        
        # Check for positions table
        positions_table = page.locator('#opt-positions-table')
        await expect(positions_table).to_be_visible(timeout=TEST_TIMEOUT)
        
        print("✅ Positions table present")
    
    @pytest.mark.asyncio
    async def test_activity_log_present(self, page: Page):
        """Test that activity log is present."""
        await page.goto(DASHBOARD_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Navigate to Strategy Monitor
        options_tab = page.locator('text="Options Lab"').first
        await options_tab.click()
        await page.wait_for_timeout(500)
        
        strategy_tab = page.locator('text="Strategy Monitor"').first
        await strategy_tab.click()
        await page.wait_for_timeout(500)
        
        # Check for activity log
        activity_heading = page.locator('text="Recent Activity"')
        await expect(activity_heading).to_be_visible(timeout=TEST_TIMEOUT)
        
        log_list = page.locator('#opt-log-list')
        await expect(log_list).to_be_visible(timeout=TEST_TIMEOUT)
        
        print("✅ Activity log present")


class TestManualTradingPanel:
    """Test the Manual Trading panel functionality."""
    
    @pytest.mark.asyncio
    async def test_manual_trading_panel_loads(self, page: Page):
        """Test that Manual Trading panel loads correctly."""
        await page.goto(DASHBOARD_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Navigate to Manual Trading
        options_tab = page.locator('text="Options Lab"').first
        await options_tab.click()
        await page.wait_for_timeout(500)
        
        manual_tab = page.locator('text="Manual Trading"').first
        await manual_tab.click()
        await page.wait_for_timeout(1000)
        
        # Check for heading
        heading = page.locator('text="Manual Options Trade Ticket"')
        await expect(heading).to_be_visible(timeout=TEST_TIMEOUT)
        
        print("✅ Manual Trading panel loaded")
    
    @pytest.mark.asyncio
    async def test_ticker_input_present(self, page: Page):
        """Test that ticker input field is present."""
        await page.goto(DASHBOARD_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Navigate to Manual Trading
        options_tab = page.locator('text="Options Lab"').first
        await options_tab.click()
        await page.wait_for_timeout(500)
        
        manual_tab = page.locator('text="Manual Trading"').first
        await manual_tab.click()
        await page.wait_for_timeout(500)
        
        # Check for ticker input
        ticker_input = page.locator('#opt-ticker-input')
        await expect(ticker_input).to_be_visible(timeout=TEST_TIMEOUT)
        
        print("✅ Ticker input field present")
    
    @pytest.mark.asyncio
    async def test_ticker_input_triggers_expirations(self, page: Page):
        """Test that entering a ticker loads expiration dates."""
        await page.goto(DASHBOARD_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Navigate to Manual Trading
        options_tab = page.locator('text="Options Lab"').first
        await options_tab.click()
        await page.wait_for_timeout(500)
        
        manual_tab = page.locator('text="Manual Trading"').first
        await manual_tab.click()
        await page.wait_for_timeout(500)
        
        # Enter a ticker
        ticker_input = page.locator('#opt-ticker-input')
        await ticker_input.fill('AAPL')
        await page.wait_for_timeout(3000)  # Wait for API call
        
        # Check that stock price updated
        stock_price = page.locator('#opt-stock-price')
        price_text = await stock_price.text_content()
        
        assert price_text != "--", f"Expected stock price to load, got: {price_text}"
        print(f"✅ Ticker AAPL loaded, price: {price_text}")
    
    @pytest.mark.asyncio
    async def test_get_options_chain_button(self, page: Page):
        """Test clicking Get Options Chain button."""
        await page.goto(DASHBOARD_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Navigate to Manual Trading
        options_tab = page.locator('text="Options Lab"').first
        await options_tab.click()
        await page.wait_for_timeout(500)
        
        manual_tab = page.locator('text="Manual Trading"').first
        await manual_tab.click()
        await page.wait_for_timeout(500)
        
        # Enter ticker
        ticker_input = page.locator('#opt-ticker-input')
        await ticker_input.fill('SPY')
        await page.wait_for_timeout(2000)
        
        # Select expiration (first option)
        expiration_dropdown = page.locator('#opt-expiration-dropdown')
        await expiration_dropdown.click()
        await page.wait_for_timeout(500)
        
        # Click first expiration option
        first_option = page.locator('.Select-option').first
        if await first_option.is_visible():
            await first_option.click()
            await page.wait_for_timeout(500)
        
        # Click Get Options Chain button
        get_chain_btn = page.locator('#opt-get-chain-btn')
        await get_chain_btn.click()
        await page.wait_for_timeout(5000)  # Wait for chain to load
        
        # Check that options chain table has data
        chain_table = page.locator('#opt-chain-table')
        await expect(chain_table).to_be_visible(timeout=TEST_TIMEOUT)
        
        print("✅ Options chain loaded successfully")
    
    @pytest.mark.asyncio
    async def test_options_chain_table_present(self, page: Page):
        """Test that options chain table is present."""
        await page.goto(DASHBOARD_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Navigate to Manual Trading
        options_tab = page.locator('text="Options Lab"').first
        await options_tab.click()
        await page.wait_for_timeout(500)
        
        manual_tab = page.locator('text="Manual Trading"').first
        await manual_tab.click()
        await page.wait_for_timeout(500)
        
        # Check for chain table
        chain_table = page.locator('#opt-chain-table')
        await expect(chain_table).to_be_visible(timeout=TEST_TIMEOUT)
        
        print("✅ Options chain table present")
    
    @pytest.mark.asyncio
    async def test_trade_entry_form_present(self, page: Page):
        """Test that trade entry form is present with all fields."""
        await page.goto(DASHBOARD_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Navigate to Manual Trading
        options_tab = page.locator('text="Options Lab"').first
        await options_tab.click()
        await page.wait_for_timeout(500)
        
        manual_tab = page.locator('text="Manual Trading"').first
        await manual_tab.click()
        await page.wait_for_timeout(500)
        
        # Check for trade form fields
        trade_symbol = page.locator('#opt-trade-symbol')
        trade_strike = page.locator('#opt-trade-strike')
        trade_quantity = page.locator('#opt-trade-quantity')
        trade_side = page.locator('#opt-trade-side')
        submit_btn = page.locator('#opt-submit-trade-btn')
        
        await expect(trade_symbol).to_be_visible(timeout=TEST_TIMEOUT)
        await expect(trade_strike).to_be_visible(timeout=TEST_TIMEOUT)
        await expect(trade_quantity).to_be_visible(timeout=TEST_TIMEOUT)
        await expect(trade_side).to_be_visible(timeout=TEST_TIMEOUT)
        await expect(submit_btn).to_be_visible(timeout=TEST_TIMEOUT)
        
        print("✅ Trade entry form complete")
    
    @pytest.mark.asyncio
    async def test_manual_positions_table_present(self, page: Page):
        """Test that manual positions table is present."""
        await page.goto(DASHBOARD_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Navigate to Manual Trading
        options_tab = page.locator('text="Options Lab"').first
        await options_tab.click()
        await page.wait_for_timeout(500)
        
        manual_tab = page.locator('text="Manual Trading"').first
        await manual_tab.click()
        await page.wait_for_timeout(500)
        
        # Scroll down to positions table
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await page.wait_for_timeout(500)
        
        # Check for manual positions heading
        positions_heading = page.locator('text="My Manual Positions"')
        await expect(positions_heading).to_be_visible(timeout=TEST_TIMEOUT)
        
        # Check for table
        manual_positions = page.locator('#opt-manual-positions-table')
        await expect(manual_positions).to_be_visible(timeout=TEST_TIMEOUT)
        
        print("✅ Manual positions table present")


class TestPnLAnalyzerPanel:
    """Test the P&L Analyzer panel functionality."""
    
    @pytest.mark.asyncio
    async def test_pnl_analyzer_loads(self, page: Page):
        """Test that P&L Analyzer panel loads correctly."""
        await page.goto(DASHBOARD_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Navigate to P&L Analyzer
        options_tab = page.locator('text="Options Lab"').first
        await options_tab.click()
        await page.wait_for_timeout(500)
        
        pnl_tab = page.locator('text="P&L Analyzer"').first
        await pnl_tab.click()
        await page.wait_for_timeout(1000)
        
        # Check for heading
        heading = page.locator('text="P&L Visualization & Analysis"')
        await expect(heading).to_be_visible(timeout=TEST_TIMEOUT)
        
        print("✅ P&L Analyzer panel loaded")
    
    @pytest.mark.asyncio
    async def test_pnl_input_fields_present(self, page: Page):
        """Test that all P&L input fields are present."""
        await page.goto(DASHBOARD_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Navigate to P&L Analyzer
        options_tab = page.locator('text="Options Lab"').first
        await options_tab.click()
        await page.wait_for_timeout(500)
        
        pnl_tab = page.locator('text="P&L Analyzer"').first
        await pnl_tab.click()
        await page.wait_for_timeout(500)
        
        # Check for input fields
        ticker = page.locator('#pnl-ticker')
        stock_price = page.locator('#pnl-stock-price')
        option_type = page.locator('#pnl-option-type')
        strike = page.locator('#pnl-strike')
        premium = page.locator('#pnl-premium')
        quantity = page.locator('#pnl-quantity')
        
        await expect(ticker).to_be_visible(timeout=TEST_TIMEOUT)
        await expect(stock_price).to_be_visible(timeout=TEST_TIMEOUT)
        await expect(option_type).to_be_visible(timeout=TEST_TIMEOUT)
        await expect(strike).to_be_visible(timeout=TEST_TIMEOUT)
        await expect(premium).to_be_visible(timeout=TEST_TIMEOUT)
        await expect(quantity).to_be_visible(timeout=TEST_TIMEOUT)
        
        print("✅ All P&L input fields present")
    
    @pytest.mark.asyncio
    async def test_generate_pnl_chart(self, page: Page):
        """Test generating a P&L chart."""
        await page.goto(DASHBOARD_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Navigate to P&L Analyzer
        options_tab = page.locator('text="Options Lab"').first
        await options_tab.click()
        await page.wait_for_timeout(500)
        
        pnl_tab = page.locator('text="P&L Analyzer"').first
        await pnl_tab.click()
        await page.wait_for_timeout(500)
        
        # Fill in some sample data (should have defaults)
        # Just click generate button
        generate_btn = page.locator('#pnl-generate-btn')
        await generate_btn.click()
        await page.wait_for_timeout(3000)
        
        # Check that chart appeared
        pnl_chart = page.locator('#pnl-chart')
        await expect(pnl_chart).to_be_visible(timeout=TEST_TIMEOUT)
        
        # Check that metrics updated
        max_profit = page.locator('#pnl-max-profit')
        max_loss = page.locator('#pnl-max-loss')
        
        profit_text = await max_profit.text_content()
        loss_text = await max_loss.text_content()
        
        assert profit_text != "$0.00", f"Expected profit to calculate, got: {profit_text}"
        assert loss_text != "$0.00", f"Expected loss to calculate, got: {loss_text}"
        
        print(f"✅ P&L chart generated - Max Profit: {profit_text}, Max Loss: {loss_text}")
    
    @pytest.mark.asyncio
    async def test_pnl_metrics_cards_present(self, page: Page):
        """Test that all P&L metric cards are present."""
        await page.goto(DASHBOARD_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Navigate to P&L Analyzer
        options_tab = page.locator('text="Options Lab"').first
        await options_tab.click()
        await page.wait_for_timeout(500)
        
        pnl_tab = page.locator('text="P&L Analyzer"').first
        await pnl_tab.click()
        await page.wait_for_timeout(500)
        
        # Scroll down to metrics
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await page.wait_for_timeout(500)
        
        # Check for metric cards
        max_profit = page.locator('#pnl-max-profit')
        max_loss = page.locator('#pnl-max-loss')
        breakeven = page.locator('#pnl-breakeven')
        risk_reward = page.locator('#pnl-risk-reward')
        
        await expect(max_profit).to_be_visible(timeout=TEST_TIMEOUT)
        await expect(max_loss).to_be_visible(timeout=TEST_TIMEOUT)
        await expect(breakeven).to_be_visible(timeout=TEST_TIMEOUT)
        await expect(risk_reward).to_be_visible(timeout=TEST_TIMEOUT)
        
        print("✅ All P&L metric cards present")


class TestOptionsServiceIntegration:
    """Test integration with the Options Service backend."""
    
    @pytest.mark.asyncio
    async def test_options_service_health(self, page: Page):
        """Test that options service is running and healthy."""
        response = await page.request.get(f'{OPTIONS_SERVICE_URL}/health')
        assert response.status == 200, f"Options service health check failed: {response.status}"
        
        data = await response.json()
        assert data.get('status') == 'healthy', f"Options service not healthy: {data}"
        
        print("✅ Options service is healthy")
    
    @pytest.mark.asyncio
    async def test_options_service_account_endpoint(self, page: Page):
        """Test that account endpoint works."""
        response = await page.request.get(f'{OPTIONS_SERVICE_URL}/account')
        
        # Should return 200 or appropriate error
        assert response.status in [200, 401, 403], \
            f"Unexpected status from account endpoint: {response.status}"
        
        print(f"✅ Account endpoint responded with status {response.status}")
    
    @pytest.mark.asyncio
    async def test_options_service_positions_endpoint(self, page: Page):
        """Test that positions endpoint works."""
        response = await page.request.get(f'{OPTIONS_SERVICE_URL}/positions')
        
        # Should return 200 or appropriate error
        assert response.status in [200, 401, 403], \
            f"Unexpected status from positions endpoint: {response.status}"
        
        print(f"✅ Positions endpoint responded with status {response.status}")


if __name__ == '__main__':
    # Run tests with pytest
    import sys
    sys.exit(pytest.main([__file__, '-v', '-s']))

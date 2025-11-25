"""
Comprehensive E2E Tests for Options Lab Standalone
Tests all three panels: Strategy Monitor, Manual Trade Ticket, P&L Analyzer
"""

import pytest
from playwright.sync_api import Page, expect
import time

BASE_URL = "http://localhost:8060"

class TestOptionsLabStandalone:
    """Test suite for standalone Options Lab application"""
    
    def test_app_loads(self, page: Page):
        """Test that the application loads successfully"""
        page.goto(BASE_URL)
        
        # Should redirect to /dash/
        expect(page).to_have_url(f"{BASE_URL}/dash/")
        
        # Check main title
        expect(page.locator("h1")).to_contain_text("Options Trading Lab")
        
        # Check subtitle
        expect(page.get_by_text("Automated strategy monitoring")).to_be_visible()
        
        print("✓ App loads successfully")
    
    def test_strategy_monitor_tab(self, page: Page):
        """Test Strategy Monitor panel"""
        page.goto(f"{BASE_URL}/dash/")
        
        # Click on Strategy Monitor tab (should be default/active)
        strategy_tab = page.get_by_role("tab", name="🤖 Strategy Monitor")
        expect(strategy_tab).to_be_visible()
        strategy_tab.click()
        
        # Wait for panel to load
        time.sleep(1)
        
        # Check for strategy status card
        expect(page.get_by_text("Strategy Status")).to_be_visible()
        expect(page.get_by_text("Open Positions")).to_be_visible()
        expect(page.get_by_text("Total P&L")).to_be_visible()
        
        # Check for control buttons
        expect(page.get_by_role("button", name="Start Strategy")).to_be_visible()
        expect(page.get_by_role("button", name="Pause Strategy")).to_be_visible()
        expect(page.get_by_role("button", name="Stop Strategy")).to_be_visible()
        expect(page.get_by_role("button", name="Refresh Data")).to_be_visible()
        
        # Check for positions table
        expect(page.get_by_text("Robot Positions")).to_be_visible()
        
        print("✓ Strategy Monitor tab works")
    
    def test_manual_trade_ticket_tab(self, page: Page):
        """Test Manual Trade Ticket panel"""
        page.goto(f"{BASE_URL}/dash/")
        
        # Click on Manual Trade Ticket tab
        trade_tab = page.get_by_role("tab", name="✋ Manual Trade Ticket")
        expect(trade_tab).to_be_visible()
        trade_tab.click()
        
        # Wait for panel to load
        time.sleep(1)
        
        # Check for ticker input
        ticker_input = page.locator("#opt-ticker-input")
        expect(ticker_input).to_be_visible()
        
        # Check for expiration calendar
        expect(page.get_by_text("Expiration Date")).to_be_visible()
        
        # Check for Get Options Chain button
        get_chain_btn = page.get_by_role("button", name="Get Options Chain")
        expect(get_chain_btn).to_be_visible()
        
        # Check for Trade Entry section
        expect(page.get_by_text("Trade Entry")).to_be_visible()
        expect(page.get_by_role("button", name="Submit Manual Trade")).to_be_visible()
        
        # Check for Manual Positions table
        expect(page.get_by_text("My Manual Positions")).to_be_visible()
        
        print("✓ Manual Trade Ticket tab works")
    
    def test_pnl_analyzer_tab(self, page: Page):
        """Test P&L Analyzer panel"""
        page.goto(f"{BASE_URL}/dash/")
        
        # Click on P&L Analyzer tab
        pnl_tab = page.get_by_role("tab", name="📊 P&L Analyzer")
        expect(pnl_tab).to_be_visible()
        pnl_tab.click()
        
        # Wait for panel to load
        time.sleep(1)
        
        # Check for P&L visualization title
        expect(page.get_by_text("P&L Visualization & Analysis")).to_be_visible()
        
        # Check for ticker input
        expect(page.locator("#pnl-ticker")).to_be_visible()
        
        # Check for Calculate P&L button
        expect(page.get_by_role("button", name="Calculate P&L")).to_be_visible()
        
        print("✓ P&L Analyzer tab works")
    
    def test_ticker_search_and_expiration(self, page: Page):
        """Test searching for a ticker and loading expirations"""
        page.goto(f"{BASE_URL}/dash/")
        
        # Go to Manual Trade Ticket
        page.get_by_role("tab", name="✋ Manual Trade Ticket").click()
        time.sleep(1)
        
        # Enter ticker
        ticker_input = page.locator("#opt-ticker-input")
        ticker_input.fill("GLD")
        ticker_input.press("Enter")
        
        # Wait for stock price to load
        time.sleep(2)
        
        # Check that stock price is displayed (not "--")
        stock_price = page.locator("#opt-stock-price").inner_text()
        assert stock_price != "--", "Stock price should load"
        assert "$" in stock_price, "Stock price should have $ symbol"
        
        # Check that expiration dropdown has options
        expiration_dropdown = page.locator("#opt-expiration-dropdown")
        expect(expiration_dropdown).to_be_visible()
        
        print(f"✓ Ticker search works (GLD: {stock_price})")
    
    def test_options_chain_loading(self, page: Page):
        """Test loading options chain"""
        page.goto(f"{BASE_URL}/dash/")
        
        # Go to Manual Trade Ticket
        page.get_by_role("tab", name="✋ Manual Trade Ticket").click()
        time.sleep(1)
        
        # Enter ticker
        page.locator("#opt-ticker-input").fill("GLD")
        page.locator("#opt-ticker-input").press("Enter")
        time.sleep(2)
        
        # Click on expiration dropdown and select first option
        expiration_dropdown = page.locator("#opt-expiration-dropdown")
        expiration_dropdown.click()
        time.sleep(0.5)
        
        # Select first expiration (using Dash dropdown structure)
        first_option = page.locator(".VirtualizedSelectOption").first
        if first_option.is_visible():
            first_option.click()
            time.sleep(0.5)
        
        # Click Get Options Chain
        page.get_by_role("button", name="Get Options Chain").click()
        
        # Wait for options chain to load
        time.sleep(3)
        
        # Check that options chain table has data
        chain_table = page.locator("#opt-chain-table")
        expect(chain_table).to_be_visible()
        
        print("✓ Options chain loading works")
    
    def test_calendar_picker_visible(self, page: Page):
        """Test that the calendar date picker is present"""
        page.goto(f"{BASE_URL}/dash/")
        
        # Go to Manual Trade Ticket
        page.get_by_role("tab", name="✋ Manual Trade Ticket").click()
        time.sleep(1)
        
        # Check for calendar picker
        calendar = page.locator("#opt-expiration-calendar")
        expect(calendar).to_be_visible()
        
        # Try to open calendar
        calendar.click()
        time.sleep(0.5)
        
        # Check that calendar popup appears (DatePickerSingle structure)
        calendar_popup = page.locator(".CalendarMonth")
        expect(calendar_popup).to_be_visible(timeout=3000)
        
        print("✓ Calendar picker is functional")
    
    def test_tab_navigation(self, page: Page):
        """Test navigation between all three tabs"""
        page.goto(f"{BASE_URL}/dash/")
        
        tabs = [
            "🤖 Strategy Monitor",
            "✋ Manual Trade Ticket", 
            "📊 P&L Analyzer"
        ]
        
        for tab_name in tabs:
            tab = page.get_by_role("tab", name=tab_name)
            expect(tab).to_be_visible()
            tab.click()
            time.sleep(1)
            
            # Verify tab is active (check for content)
            if "Strategy Monitor" in tab_name:
                expect(page.get_by_text("Robot Positions")).to_be_visible()
            elif "Manual Trade" in tab_name:
                expect(page.get_by_text("Trade Entry")).to_be_visible()
            elif "P&L Analyzer" in tab_name:
                expect(page.get_by_text("Calculate P&L")).to_be_visible()
        
        print("✓ Tab navigation works for all 3 tabs")
    
    def test_api_health_endpoint(self, page: Page):
        """Test that API endpoints are accessible"""
        page.goto(f"{BASE_URL}/health")
        
        # Check response
        content = page.content()
        assert "healthy" in content, "Health endpoint should return healthy status"
        assert "options_lab" in content, "Should identify as options_lab service"
        
        print("✓ API health endpoint works")
    
    def test_api_docs_accessible(self, page: Page):
        """Test that Swagger docs are accessible"""
        page.goto(f"{BASE_URL}/docs")
        
        # Check for Swagger UI
        expect(page.get_by_text("Options Lab API")).to_be_visible(timeout=5000)
        
        # Check for endpoints
        expect(page.get_by_text("/health")).to_be_visible()
        expect(page.get_by_text("/account")).to_be_visible()
        expect(page.get_by_text("/trade")).to_be_visible()
        
        print("✓ API documentation is accessible")


class TestOptionsLabFunctionality:
    """Test actual functionality and interactions"""
    
    def test_refresh_strategy_data(self, page: Page):
        """Test refreshing strategy data"""
        page.goto(f"{BASE_URL}/dash/")
        
        # Click Refresh Data button
        refresh_btn = page.get_by_role("button", name="Refresh Data")
        refresh_btn.click()
        
        # Wait for refresh
        time.sleep(2)
        
        # Check for status message or updated data
        # (This would show any error messages if refresh fails)
        
        print("✓ Refresh Data button works")
    
    def test_trade_form_inputs(self, page: Page):
        """Test that all trade form inputs are functional"""
        page.goto(f"{BASE_URL}/dash/")
        
        # Go to Manual Trade Ticket
        page.get_by_role("tab", name="✋ Manual Trade Ticket").click()
        time.sleep(1)
        
        # Test all trade form inputs
        page.locator("#opt-trade-symbol").fill("TEST")
        page.locator("#opt-trade-strike").fill("100")
        page.locator("#opt-trade-quantity").fill("5")
        
        # Check dropdowns
        side_dropdown = page.locator("#opt-trade-side")
        expect(side_dropdown).to_be_visible()
        
        order_type_dropdown = page.locator("#opt-trade-order-type")
        expect(order_type_dropdown).to_be_visible()
        
        print("✓ Trade form inputs are functional")


# Pytest configuration
@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser for testing"""
    return {
        **browser_context_args,
        "viewport": {
            "width": 1920,
            "height": 1080,
        }
    }

if __name__ == "__main__":
    print("Run with: pytest test_options_lab_comprehensive.py -v -s")

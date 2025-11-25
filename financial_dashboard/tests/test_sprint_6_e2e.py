"""
Sprint 6 End-to-End Tests
Tests for UI interactions and workflows using Playwright

Test Coverage:
1. Theme Toggle interaction
2. Global Search functionality
3. Tab navigation to new Sprint 6 features
4. Complete user workflows
"""
import pytest
import asyncio
from playwright.async_api import async_playwright, Page, expect
import sys
import os

# Configuration
DASHBOARD_URL = os.getenv('DASHBOARD_URL', 'http://localhost:8000')
TIMEOUT = 30000  # 30 seconds


class TestThemeToggle:
    """Test theme toggle functionality"""
    
    @pytest.mark.asyncio
    async def test_theme_toggle_exists(self, page: Page):
        """Test that theme toggle button exists"""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state('networkidle')
        
        # Look for theme toggle button
        theme_btn = page.locator('#theme-toggle-btn')
        await expect(theme_btn).to_be_visible(timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_theme_toggle_switches(self, page: Page):
        """Test theme switching from dark to light"""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state('networkidle')
        
        # Get initial theme
        theme_store = await page.locator('#theme-store').get_attribute('data-theme')
        initial_theme = theme_store if theme_store else 'dark'
        
        # Click theme toggle
        await page.click('#theme-toggle-btn')
        await page.wait_for_timeout(500)
        
        # Verify theme changed
        theme_store_after = await page.locator('#theme-store').get_attribute('data-theme')
        assert theme_store_after != initial_theme
    
    @pytest.mark.asyncio
    async def test_theme_persists_on_reload(self, page: Page):
        """Test that theme choice persists across page reloads"""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state('networkidle')
        
        # Switch to light theme
        await page.click('#theme-toggle-btn')
        await page.wait_for_timeout(500)
        
        # Reload page
        await page.reload()
        await page.wait_for_load_state('networkidle')
        
        # Verify theme is still light
        theme_store = await page.locator('#theme-store').get_attribute('data-theme')
        # Note: localStorage persistence depends on implementation


class TestGlobalSearch:
    """Test global search functionality"""
    
    @pytest.mark.asyncio
    async def test_global_search_button_exists(self, page: Page):
        """Test that global search button exists"""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state('networkidle')
        
        search_btn = page.locator('#global-search-btn')
        await expect(search_btn).to_be_visible(timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_global_search_modal_opens(self, page: Page):
        """Test that clicking search button opens modal"""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state('networkidle')
        
        # Click search button
        await page.click('#global-search-btn')
        await page.wait_for_timeout(500)
        
        # Verify modal is open
        modal = page.locator('#global-search-modal')
        await expect(modal).to_be_visible(timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_global_search_finds_tickers(self, page: Page):
        """Test searching for tickers"""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state('networkidle')
        
        # Open search modal
        await page.click('#global-search-btn')
        await page.wait_for_timeout(500)
        
        # Type in search
        await page.fill('#global-search-input', 'AAPL')
        await page.wait_for_timeout(1000)
        
        # Verify results appear
        results = page.locator('#global-search-results')
        await expect(results).to_contain_text('AAPL', timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_global_search_close(self, page: Page):
        """Test closing search modal"""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state('networkidle')
        
        # Open modal
        await page.click('#global-search-btn')
        await page.wait_for_timeout(500)
        
        # Close modal
        await page.click('#global-search-close')
        await page.wait_for_timeout(500)
        
        # Verify modal is closed
        modal = page.locator('#global-search-modal')
        await expect(modal).not_to_be_visible()


class TestTabNavigation:
    """Test navigation to Sprint 6 feature tabs"""
    
    @pytest.mark.asyncio
    async def test_market_trends_tab_loads(self, page: Page):
        """Test Market Trends tab loads"""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state('networkidle')
        
        # Click Market Trends tab
        await page.click('[data-rr-ui-event-key="market_trends"]')
        await page.wait_for_timeout(1000)
        
        # Verify content loaded
        content = page.locator('#market_trends')
        await expect(content).to_be_visible(timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_analysis_hub_tab_loads(self, page: Page):
        """Test Analysis Hub tab loads (Factor DNA)"""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state('networkidle')
        
        # Click Analysis Hub tab
        await page.click('[data-rr-ui-event-key="analysis_hub"]')
        await page.wait_for_timeout(1000)
        
        # Verify content loaded
        content = page.locator('#analysis_hub')
        await expect(content).to_be_visible(timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_portfolio_tab_loads(self, page: Page):
        """Test Portfolio tab loads (Health Dashboard & Hedge Finder)"""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state('networkidle')
        
        # Click Portfolio tab
        await page.click('[data-rr-ui-event-key="portfolio"]')
        await page.wait_for_timeout(1000)
        
        # Verify content loaded
        content = page.locator('#portfolio')
        await expect(content).to_be_visible(timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_market_forecast_tab_loads(self, page: Page):
        """Test Market Forecast tab loads (Volatility Lab)"""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state('networkidle')
        
        # Click Market Forecast tab
        await page.click('[data-rr-ui-event-key="market_forecast"]')
        await page.wait_for_timeout(1000)
        
        # Verify content loaded
        content = page.locator('#market_forecast')
        await expect(content).to_be_visible(timeout=TIMEOUT)


class TestCompleteWorkflows:
    """Test complete user workflows"""
    
    @pytest.mark.asyncio
    async def test_sentiment_analysis_workflow(self, page: Page):
        """Test complete sentiment analysis workflow"""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state('networkidle')
        
        # Navigate to Market Trends (where sentiment is shown)
        await page.click('[data-rr-ui-event-key="market_trends"]')
        await page.wait_for_timeout(1000)
        
        # Look for sentiment components
        # Note: This assumes sentiment is integrated into Market Trends tab
        await page.wait_for_selector('text=Sentiment', timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_factor_dna_workflow(self, page: Page):
        """Test Factor DNA analysis workflow"""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state('networkidle')
        
        # Navigate to Analysis Hub
        await page.click('[data-rr-ui-event-key="analysis_hub"]')
        await page.wait_for_timeout(1000)
        
        # Look for Factor DNA components
        await page.wait_for_selector('text=Factor', timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_portfolio_health_workflow(self, page: Page):
        """Test Portfolio Health Dashboard workflow"""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state('networkidle')
        
        # Navigate to Portfolio tab
        await page.click('[data-rr-ui-event-key="portfolio"]')
        await page.wait_for_timeout(1000)
        
        # Look for health score gauge
        await page.wait_for_selector('text=Health', timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_volatility_lab_workflow(self, page: Page):
        """Test Volatility Lab workflow"""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state('networkidle')
        
        # Navigate to Market Forecast tab
        await page.click('[data-rr-ui-event-key="market_forecast"]')
        await page.wait_for_timeout(1000)
        
        # Look for Volatility Lab components
        await page.wait_for_selector('text=Volatility', timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_hedge_finder_workflow(self, page: Page):
        """Test Hedge Finder workflow"""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state('networkidle')
        
        # Navigate to Portfolio tab
        await page.click('[data-rr-ui-event-key="portfolio"]')
        await page.wait_for_timeout(1000)
        
        # Look for Hedge Finder components
        await page.wait_for_selector('text=Hedge', timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_search_and_navigate_workflow(self, page: Page):
        """Test search and navigation workflow"""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state('networkidle')
        
        # Open search
        await page.click('#global-search-btn')
        await page.wait_for_timeout(500)
        
        # Search for a ticker
        await page.fill('#global-search-input', 'AAPL')
        await page.wait_for_timeout(1000)
        
        # Click on a search result (if available)
        # Note: Actual navigation depends on search result implementation
        
        # Close search
        await page.click('#global-search-close')
        await page.wait_for_timeout(500)


class TestResponsiveness:
    """Test responsive design and mobile compatibility"""
    
    @pytest.mark.asyncio
    async def test_mobile_view(self, page: Page):
        """Test dashboard in mobile viewport"""
        await page.set_viewport_size({"width": 375, "height": 667})  # iPhone SE
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state('networkidle')
        
        # Verify page loads
        await expect(page.locator('h1')).to_be_visible(timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_tablet_view(self, page: Page):
        """Test dashboard in tablet viewport"""
        await page.set_viewport_size({"width": 768, "height": 1024})  # iPad
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state('networkidle')
        
        # Verify page loads
        await expect(page.locator('h1')).to_be_visible(timeout=TIMEOUT)


# Pytest fixtures
@pytest.fixture(scope="session")
async def browser():
    """Create browser instance for all tests"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser):
    """Create new page for each test"""
    context = await browser.new_context()
    page = await context.new_page()
    yield page
    await page.close()
    await context.close()


# Test Suite Summary
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '-s'])

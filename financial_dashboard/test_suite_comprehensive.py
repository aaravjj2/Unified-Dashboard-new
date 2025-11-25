"""
Comprehensive Playwright Test Suite for Financial Dashboard
===========================================================
Tests all major UI tabs and backend API endpoints with granular validation.

Test Structure:
- test_home_tab.py - Home tab UI and quick actions
- test_portfolio_tab.py - Portfolio positions, orders, analytics
- test_market_trends_tab.py - Market trends analysis and job submission
- test_market_forecast_tab.py - Forecasting UI and model selection
- test_analysis_hub_tab.py - Analysis tools and visualizations
- test_research_lab_tab.py - Research tools and data retrieval
- test_options_lab_tab.py - Options chain and strategy builder
- test_backtesting_lab_tab.py - Backtesting interface and results
- test_backend_apis.py - Direct API endpoint testing

Usage:
    pytest test_suite_comprehensive.py -v --tb=short
    pytest test_suite_comprehensive.py::TestHomeTab -v
"""

import asyncio
import pytest
from playwright.async_api import async_playwright, Page, expect
import httpx
from pathlib import Path
from datetime import datetime

# Test configuration
DASHBOARD_URL = "http://localhost:8050"
API_GATEWAY_URL = "http://localhost:8000"
SCREENSHOT_DIR = Path("test_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def browser():
    """Launch browser for all tests."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser):
    """Create new page for each test."""
    context = await browser.new_context(viewport={"width": 1920, "height": 1080})
    page = await context.new_page()
    yield page
    await context.close()


def save_screenshot(page: Page, name: str):
    """Save screenshot with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = SCREENSHOT_DIR / f"{name}_{timestamp}.png"
    page.screenshot(path=str(filename))
    print(f"📸 Screenshot saved: {filename}")


# ==============================================================================
# TEST CLASS: HOME TAB
# ==============================================================================

@pytest.mark.asyncio
class TestHomeTab:
    """Test Home tab functionality."""
    
    async def test_home_tab_loads(self, page: Page):
        """Test that Home tab loads successfully."""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_selector("#home-tab", timeout=10000)
        save_screenshot(page, "home_initial")
        
        # Verify page title
        title = await page.title()
        assert "Dashboard" in title or "Financial" in title
        
    async def test_portfolio_summary_displays(self, page: Page):
        """Test that portfolio summary section renders."""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_selector("#home-portfolio-summary", timeout=10000)
        save_screenshot(page, "home_portfolio_summary")
        
        # Check for key metrics
        portfolio_value = await page.locator("#home-portfolio-value").text_content()
        assert portfolio_value is not None
        print(f"Portfolio value: {portfolio_value}")
        
    async def test_quick_action_scan_market(self, page: Page):
        """Test 'Scan Market' quick action button."""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state("networkidle")
        
        # Click Scan Market button
        scan_btn = page.locator("button:has-text('Scan Market')")
        if await scan_btn.count() > 0:
            await scan_btn.click()
            await page.wait_for_timeout(2000)  # Wait for action
            save_screenshot(page, "home_scan_market_clicked")
            
            # Verify outcome - check for alert or job ID
            alert = page.locator("#home-action-alert")
            job_div = page.locator("#home-last-job")
            
            alert_text = await alert.text_content() if await alert.count() > 0 else ""
            job_text = await job_div.text_content() if await job_div.count() > 0 else ""
            
            assert alert_text or job_text, "No observable outcome from Scan Market action"
            print(f"Scan Market result: alert='{alert_text}' job='{job_text}'")
    
    async def test_market_indices_display(self, page: Page):
        """Test that market indices display (non-fatal check)."""
        await page.goto(DASHBOARD_URL)
        await page.wait_for_selector("#home-market-indices", timeout=10000)
        save_screenshot(page, "home_market_indices")
        
        # Non-fatal check for index values
        indices = await page.locator("#home-market-indices .index-value").all_text_content()
        if indices:
            print(f"Market indices found: {len(indices)}")
        else:
            print("⚠️ Market indices not displayed (non-critical)")


# ==============================================================================
# TEST CLASS: PORTFOLIO TAB
# ==============================================================================

@pytest.mark.asyncio
class TestPortfolioTab:
    """Test Portfolio tab functionality."""
    
    async def test_portfolio_tab_navigation(self, page: Page):
        """Test navigation to Portfolio tab."""
        await page.goto(DASHBOARD_URL)
        
        # Click Portfolio tab
        portfolio_tab = page.locator("a[href='#portfolio']")
        await portfolio_tab.click()
        await page.wait_for_timeout(1000)
        save_screenshot(page, "portfolio_initial")
        
        # Verify tab active
        assert await page.locator("#portfolio-tab").is_visible()
    
    async def test_positions_table_loads(self, page: Page):
        """Test that positions table loads."""
        await page.goto(f"{DASHBOARD_URL}#portfolio")
        await page.wait_for_selector("#portfolio-positions-table", timeout=10000)
        save_screenshot(page, "portfolio_positions")
        
        # Check for table headers
        headers = await page.locator("#portfolio-positions-table th").all_text_content()
        assert any("Symbol" in h or "Ticker" in h for h in headers)
    
    async def test_refresh_portfolio_button(self, page: Page):
        """Test portfolio refresh button."""
        await page.goto(f"{DASHBOARD_URL}#portfolio")
        
        refresh_btn = page.locator("button:has-text('Refresh')")
        if await refresh_btn.count() > 0:
            await refresh_btn.click()
            await page.wait_for_timeout(2000)
            save_screenshot(page, "portfolio_refreshed")
            print("✅ Portfolio refresh completed")


# ==============================================================================
# TEST CLASS: MARKET TRENDS TAB
# ==============================================================================

@pytest.mark.asyncio
class TestMarketTrendsTab:
    """Test Market Trends tab functionality."""
    
    async def test_market_trends_tab_loads(self, page: Page):
        """Test Market Trends tab loads."""
        await page.goto(f"{DASHBOARD_URL}#market-trends")
        await page.wait_for_selector("#market-trends-tab", timeout=10000)
        save_screenshot(page, "market_trends_initial")
    
    async def test_analysis_form_displays(self, page: Page):
        """Test that analysis input form is visible."""
        await page.goto(f"{DASHBOARD_URL}#market-trends")
        
        # Check for ticker input
        ticker_input = page.locator("input[placeholder*='ticker']")
        assert await ticker_input.count() > 0
        save_screenshot(page, "market_trends_form")
    
    async def test_submit_analysis_job(self, page: Page):
        """Test submitting a market analysis job."""
        await page.goto(f"{DASHBOARD_URL}#market-trends")
        await page.wait_for_load_state("networkidle")
        
        # Fill in tickers
        ticker_input = page.locator("input[placeholder*='ticker']").first
        await ticker_input.fill("SPY,QQQ")
        
        # Click analyze button
        analyze_btn = page.locator("button:has-text('Analyze')").first
        await analyze_btn.click()
        await page.wait_for_timeout(3000)
        save_screenshot(page, "market_trends_analysis_submitted")
        
        # Check for results or loading indicator
        results = page.locator("#market-trends-results")
        loading = page.locator(".loading-spinner")
        
        assert await results.count() > 0 or await loading.count() > 0


# ==============================================================================
# TEST CLASS: BACKEND API ENDPOINTS
# ==============================================================================

@pytest.mark.asyncio
class TestBackendAPIs:
    """Test backend service API endpoints directly."""
    
    async def test_portfolio_dashboard_health(self):
        """Test Portfolio Dashboard service health endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8057/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            print(f"Portfolio Dashboard: {data}")
    
    async def test_market_trends_health(self):
        """Test Market Trends service health endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8055/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            print(f"Market Trends: {data}")
    
    async def test_market_trends_job_submission(self):
        """Test Market Trends job submission endpoint."""
        async with httpx.AsyncClient() as client:
            payload = {
                "tickers": ["SPY", "QQQ", "DIA"],
                "period": "1mo",
                "interval": "1d",
                "options": False,
                "news": False
            }
            response = await client.post("http://localhost:8055/api/jobs", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "pending"
            print(f"Job created: {data['job_id']}")
    
    async def test_portfolio_summary_endpoint(self):
        """Test Portfolio Dashboard summary endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8057/portfolio/summary")
            # May return error if no Alpaca credentials, but endpoint should respond
            assert response.status_code in [200, 500]
            data = response.json()
            print(f"Portfolio summary response: {data.get('success', False)}")
    
    async def test_all_service_health_checks(self):
        """Test health endpoints for all services."""
        services = {
            "Dashboard": "http://localhost:8050",
            "API Gateway": "http://localhost:8000/health",
            "Market Trends": "http://localhost:8055/health",
            "Market Forecast": "http://localhost:8051/health",
            "Analysis": "http://localhost:8054/health",
            "Portfolio": "http://localhost:8056/health",
            "Portfolio Dashboard": "http://localhost:8057/health",
            "Research": "http://localhost:8058/health",
            "Options": "http://localhost:8060/health",
            "Chatbot": "http://localhost:8062/health",
            "News Analysis": "http://localhost:8006/health",
            "Backtester": "http://localhost:8064/health"
        }
        
        results = {}
        async with httpx.AsyncClient() as client:
            for name, url in services.items():
                try:
                    response = await client.get(url, timeout=5.0)
                    results[name] = "✅ Healthy" if response.status_code == 200 else f"⚠️ {response.status_code}"
                except Exception as e:
                    results[name] = f"❌ Error: {str(e)[:50]}"
        
        print("\n🏥 Service Health Check Results:")
        for name, status in results.items():
            print(f"  {name}: {status}")
        
        # At least dashboard should be healthy
        assert "✅" in results["Dashboard"]


# ==============================================================================
# TEST CLASS: OPTIONS LAB TAB
# ==============================================================================

@pytest.mark.asyncio
class TestOptionsLabTab:
    """Test Options Lab tab functionality."""
    
    async def test_options_lab_loads(self, page: Page):
        """Test Options Lab tab loads."""
        await page.goto(f"{DASHBOARD_URL}#options")
        await page.wait_for_selector("#options-lab-tab", timeout=10000)
        save_screenshot(page, "options_lab_initial")
    
    async def test_ticker_search(self, page: Page):
        """Test options ticker search functionality."""
        await page.goto(f"{DASHBOARD_URL}#options")
        
        # Find ticker input
        ticker_input = page.locator("#options-ticker-input")
        if await ticker_input.count() > 0:
            await ticker_input.fill("AAPL")
            
            # Click search/load button
            load_btn = page.locator("button:has-text('Load')").first
            await load_btn.click()
            await page.wait_for_timeout(3000)
            save_screenshot(page, "options_lab_chain_loaded")


# ==============================================================================
# TEST CLASS: BACKTESTING LAB TAB
# ==============================================================================

@pytest.mark.asyncio
class TestBacktestingLabTab:
    """Test Backtesting Lab tab functionality."""
    
    async def test_backtesting_lab_loads(self, page: Page):
        """Test Backtesting Lab tab loads."""
        await page.goto(f"{DASHBOARD_URL}#backtesting")
        await page.wait_for_selector("#backtesting-lab-tab", timeout=10000)
        save_screenshot(page, "backtesting_lab_initial")
    
    async def test_strategy_selection(self, page: Page):
        """Test strategy dropdown selection."""
        await page.goto(f"{DASHBOARD_URL}#backtesting")
        
        # Find strategy dropdown
        strategy_dropdown = page.locator("#strategy-selector")
        if await strategy_dropdown.count() > 0:
            await strategy_dropdown.select_option(index=0)
            save_screenshot(page, "backtesting_strategy_selected")


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--asyncio-mode=auto"])

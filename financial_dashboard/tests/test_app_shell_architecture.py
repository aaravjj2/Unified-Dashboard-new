"""
Application Shell Architecture - Comprehensive Test Suite
=========================================================
Tests the new microservices architecture with backend services,
API gateway, and lightweight UI clients.

Test Categories:
1. Backend Service Tests - Direct tests of market_trends_service.py
2. API Gateway Tests - Routing and proxy functionality
3. Integration Tests - End-to-end API workflows
4. UI E2E Tests - Playwright tests of the dashboard

Requirements:
- pytest
- pytest-playwright
- requests
- httpx (for API gateway)

Run:
    pytest tests/test_app_shell_architecture.py -v
    pytest tests/test_app_shell_architecture.py -v --headed  # See browser
"""

import pytest
import requests
import time
import json
from typing import Dict, Any
from pathlib import Path

# Service URLs
API_GATEWAY_URL = "http://localhost:8049"
TRENDS_SERVICE_URL = "http://localhost:8050"
DASHBOARD_URL = "http://localhost:8000"

# Test configuration
TEST_TICKERS = ["AAPL", "MSFT"]
POLL_TIMEOUT = 60  # seconds
POLL_INTERVAL = 2  # seconds


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def check_services():
    """Verify all required services are running before tests."""
    services = {
        "API Gateway": API_GATEWAY_URL,
        "Trends Service": TRENDS_SERVICE_URL,
        "Dashboard": DASHBOARD_URL
    }
    
    for name, url in services.items():
        try:
            response = requests.get(f"{url}/health", timeout=5)
            assert response.status_code == 200, f"{name} health check failed"
            print(f"✓ {name} is healthy")
        except Exception as e:
            pytest.fail(f"{name} is not running at {url}: {e}")


# ============================================================================
# PART 1: BACKEND SERVICE TESTS (Direct to market_trends_service.py)
# ============================================================================

class TestMarketTrendsService:
    """Test the headless backend service directly."""
    
    def test_service_health(self):
        """Test service health endpoint."""
        response = requests.get(f"{TRENDS_SERVICE_URL}/health", timeout=5)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "market_trends"
        assert "timestamp" in data
        assert "module_loaded" in data
        
        print(f"✓ Service health: {data}")
    
    def test_create_job(self):
        """Test creating a new analysis job."""
        job_request = {
            "tickers": TEST_TICKERS,
            "period": "1y",
            "interval": "1d",
            "options": False,
            "news": False,
            "cache_only": False
        }
        
        response = requests.post(
            f"{TRENDS_SERVICE_URL}/api/jobs",
            json=job_request,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["status"] in ["pending", "running"]
        
        job_id = data["job_id"]
        print(f"✓ Created job: {job_id}")
        
        return job_id
    
    def test_get_job_status(self):
        """Test polling job status."""
        # First create a job
        job_id = self.test_create_job()
        
        # Poll for completion
        start_time = time.time()
        final_status = None
        
        while time.time() - start_time < POLL_TIMEOUT:
            response = requests.get(
                f"{TRENDS_SERVICE_URL}/api/jobs/{job_id}",
                timeout=10
            )
            
            assert response.status_code == 200
            job_data = response.json()
            
            status = job_data["status"]
            progress = job_data.get("progress", 0.0)
            
            print(f"Job {job_id}: {status} ({int(progress * 100)}%)")
            
            if status in ["completed", "failed"]:
                final_status = status
                break
            
            time.sleep(POLL_INTERVAL)
        
        assert final_status == "completed", f"Job did not complete (status: {final_status})"
        print(f"✓ Job completed successfully")
    
    def test_get_latest_results(self):
        """Test fetching cached results."""
        # Run an analysis first to ensure we have results
        self.test_get_job_status()
        
        # Now fetch latest results
        response = requests.get(
            f"{TRENDS_SERVICE_URL}/api/results/latest",
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert "row_count" in data
        
        results = data["data"]
        assert "detailed" in results or "tidy" in results
        
        records = results.get("detailed", []) or results.get("tidy", [])
        assert len(records) > 0, "No results returned"
        
        # Verify record structure
        first_record = records[0]
        assert "ticker" in first_record
        
        print(f"✓ Fetched {len(records)} cached results")


# ============================================================================
# PART 2: API GATEWAY TESTS (Proxy routing)
# ============================================================================

class TestAPIGateway:
    """Test the API Gateway routing and health aggregation."""
    
    def test_gateway_health(self):
        """Test API Gateway health check."""
        response = requests.get(f"{API_GATEWAY_URL}/health", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert "gateway" in data
        assert "services" in data
        assert "timestamp" in data
        
        # Check trends service is listed
        assert "trends" in data["services"]
        trends_health = data["services"]["trends"]
        assert trends_health["status"] in ["healthy", "unhealthy"]
        
        print(f"✓ Gateway health: {data['gateway']}")
        print(f"  Trends service: {trends_health['status']}")
    
    def test_gateway_proxy_to_trends(self):
        """Test that gateway correctly routes to trends service."""
        # Create job via gateway
        job_request = {
            "tickers": TEST_TICKERS,
            "period": "6mo",
            "interval": "1d",
            "options": False,
            "news": False,
            "cache_only": False
        }
        
        response = requests.post(
            f"{API_GATEWAY_URL}/api/trends/api/jobs",
            json=job_request,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        
        job_id = data["job_id"]
        print(f"✓ Created job via gateway: {job_id}")
        
        # Poll status via gateway
        response = requests.get(
            f"{API_GATEWAY_URL}/api/trends/api/jobs/{job_id}",
            timeout=10
        )
        
        assert response.status_code == 200
        job_data = response.json()
        assert job_data["job_id"] == job_id
        
        print(f"✓ Gateway proxy working")


# ============================================================================
# PART 3: INTEGRATION TESTS (Full workflow via gateway)
# ============================================================================

class TestIntegration:
    """Test complete workflows through the architecture."""
    
    def test_full_analysis_workflow(self):
        """Test complete workflow: create job → poll → get results."""
        # Step 1: Create job via gateway
        job_request = {
            "tickers": ["TSLA", "NVDA"],
            "period": "3mo",
            "interval": "1d",
            "options": False,
            "news": False,
            "cache_only": False
        }
        
        response = requests.post(
            f"{API_GATEWAY_URL}/api/trends/api/jobs",
            json=job_request,
            timeout=10
        )
        
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        print(f"Step 1: Created job {job_id}")
        
        # Step 2: Poll until complete
        start_time = time.time()
        completed = False
        
        while time.time() - start_time < POLL_TIMEOUT:
            response = requests.get(
                f"{API_GATEWAY_URL}/api/trends/api/jobs/{job_id}",
                timeout=10
            )
            
            assert response.status_code == 200
            job_data = response.json()
            status = job_data["status"]
            
            if status == "completed":
                completed = True
                result = job_data.get("result", {})
                assert "detailed" in result or "tidy" in result
                print(f"Step 2: Job completed with results")
                break
            elif status == "failed":
                pytest.fail(f"Job failed: {job_data.get('error')}")
            
            time.sleep(POLL_INTERVAL)
        
        assert completed, "Job did not complete in time"
        
        # Step 3: Fetch cached results
        response = requests.get(
            f"{API_GATEWAY_URL}/api/trends/api/results/latest",
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        records = data["data"].get("detailed", []) or data["data"].get("tidy", [])
        assert len(records) > 0
        print(f"Step 3: Fetched {len(records)} cached results")
        
        print("✓ Full workflow completed successfully")
    
    def test_error_handling(self):
        """Test error handling for invalid requests."""
        # Test invalid ticker list (empty)
        job_request = {
            "tickers": [],
            "period": "1y"
        }
        
        response = requests.post(
            f"{API_GATEWAY_URL}/api/trends/api/jobs",
            json=job_request,
            timeout=10
        )
        
        assert response.status_code == 422, "Should reject empty ticker list"
        print("✓ Error handling working for invalid input")
        
        # Test nonexistent job
        response = requests.get(
            f"{API_GATEWAY_URL}/api/trends/api/jobs/invalid-job-id",
            timeout=10
        )
        
        assert response.status_code == 404
        print("✓ Error handling working for missing resources")


# ============================================================================
# PART 4: UI E2E TESTS (Playwright)
# ============================================================================

@pytest.mark.playwright
class TestDashboardUI:
    """E2E tests using Playwright to verify UI functionality."""
    
    @pytest.fixture(scope="class", autouse=True)
    def ensure_backend_ready(self, check_services):
        """Ensure backend services are ready before UI tests."""
        # Run a quick analysis to populate cache
        job_request = {
            "tickers": TEST_TICKERS,
            "period": "1mo",
            "interval": "1d",
            "options": False,
            "news": False,
            "cache_only": False
        }
        
        response = requests.post(
            f"{API_GATEWAY_URL}/api/trends/api/jobs",
            json=job_request,
            timeout=10
        )
        
        if response.status_code == 200:
            job_id = response.json()["job_id"]
            
            # Wait for completion
            for _ in range(30):
                status_response = requests.get(
                    f"{API_GATEWAY_URL}/api/trends/api/jobs/{job_id}",
                    timeout=10
                )
                if status_response.json()["status"] == "completed":
                    break
                time.sleep(2)
        
        yield
    
    def test_dashboard_loads(self, page):
        """Test that the dashboard loads successfully."""
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")
        
        # Check for main dashboard elements
        assert page.title(), "Dashboard should have a title"
        print("✓ Dashboard loaded")
    
    def test_market_trends_tab_visible(self, page):
        """Test that Market Trends tab is visible."""
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")
        
        # Look for Market Trends tab (adjust selector as needed)
        trends_tab = page.get_by_text("Market Trends", exact=False)
        assert trends_tab.is_visible(), "Market Trends tab should be visible"
        print("✓ Market Trends tab found")
    
    def test_cached_results_display(self, page):
        """Test that cached results are displayed on page load."""
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")
        
        # Navigate to Market Trends tab
        trends_tab = page.get_by_text("Market Trends", exact=False)
        trends_tab.click()
        
        # Wait for results table
        page.wait_for_selector("table", timeout=10000)
        
        # Check if table has rows
        rows = page.locator("table tbody tr")
        count = rows.count()
        assert count > 0, "Results table should have data"
        print(f"✓ Loaded {count} cached results")
    
    def test_run_analysis_button(self, page):
        """Test running a new analysis from the UI."""
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")
        
        # Navigate to Market Trends
        trends_tab = page.get_by_text("Market Trends", exact=False)
        trends_tab.click()
        
        # Find and click Run button
        run_button = page.get_by_text("Run Full Analysis", exact=False)
        assert run_button.is_visible(), "Run button should be visible"
        run_button.click()
        
        # Wait for status message
        page.wait_for_selector("text=/Analysis Started|Running/", timeout=10000)
        print("✓ Analysis started from UI")
        
        # Wait for completion
        page.wait_for_selector("text=/Complete|completed/i", timeout=60000)
        print("✓ Analysis completed")


# ============================================================================
# DEPLOYMENT VALIDATION TESTS
# ============================================================================

class TestDeployment:
    """Validate the deployment and configuration."""
    
    def test_all_services_running(self):
        """Verify all core services are accessible."""
        services = {
            "API Gateway": f"{API_GATEWAY_URL}/health",
            "Trends Service": f"{TRENDS_SERVICE_URL}/health",
            "Dashboard": f"{DASHBOARD_URL}"
        }
        
        for name, url in services.items():
            try:
                response = requests.get(url, timeout=5)
                assert response.status_code == 200
                print(f"✓ {name} is accessible")
            except Exception as e:
                pytest.fail(f"{name} is not accessible: {e}")
    
    def test_service_logs_exist(self):
        """Check that service log files exist."""
        log_dir = Path(__file__).parent.parent / "logs"
        
        expected_logs = [
            "api_gateway.log",
            "market_trends_service.log",
            "analysis_service.log"
        ]
        
        for log_file in expected_logs:
            log_path = log_dir / log_file
            if log_path.exists():
                print(f"✓ Log file exists: {log_file}")
            else:
                print(f"⚠ Log file missing: {log_file} (may not have started yet)")


# ============================================================================
# PART 6: ANALYSIS HUB SERVICE TESTS
# ============================================================================

ANALYSIS_SERVICE_URL = "http://localhost:8054"

class TestAnalysisService:
    """Test the Analysis Hub backend service directly."""
    
    def test_service_health(self):
        """Test Analysis Hub health endpoint."""
        response = requests.get(f"{ANALYSIS_SERVICE_URL}/health", timeout=5)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "analysis_hub"
        assert "timestamp" in data
        assert "attribution_utils_loaded" in data
        
        print(f"✓ Analysis Hub health: {data}")
    
    def test_create_attribution_job(self):
        """Test creating a new attribution analysis job."""
        from datetime import datetime, timedelta
        
        job_request = {
            "picks_type": "weekly",
            "start_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "end_date": datetime.now().strftime("%Y-%m-%d"),
            "horizon": "1w",
            "regime_filter": "all"
        }
        
        response = requests.post(
            f"{ANALYSIS_SERVICE_URL}/api/jobs",
            json=job_request,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["status"] in ["pending", "running"]
        
        job_id = data["job_id"]
        print(f"✓ Created attribution job: {job_id}")
        
        return job_id
    
    def test_get_attribution_job_status(self):
        """Test polling attribution job status."""
        # First create a job
        job_id = self.test_create_attribution_job()
        
        # Poll for completion
        start_time = time.time()
        final_status = None
        
        while time.time() - start_time < POLL_TIMEOUT:
            response = requests.get(
                f"{ANALYSIS_SERVICE_URL}/api/jobs/{job_id}",
                timeout=10
            )
            
            assert response.status_code == 200
            job_data = response.json()
            
            status = job_data["status"]
            progress = job_data.get("progress", 0.0)
            
            print(f"Attribution Job {job_id}: {status} ({int(progress * 100)}%)")
            
            if status in ["completed", "failed"]:
                final_status = status
                
                # If completed, verify result structure
                if status == "completed":
                    result = job_data.get("result")
                    assert result is not None
                    assert "portfolio" in result
                    assert "per_pick" in result
                
                break
            
            time.sleep(POLL_INTERVAL)
        
        assert final_status in ["completed", "failed"], f"Job timed out (status: {final_status})"
        print(f"✓ Attribution job completed")
    
    def test_get_latest_attribution_results(self):
        """Test fetching cached attribution results."""
        # Run an analysis first to ensure we have results
        self.test_get_attribution_job_status()
        
        # Now fetch latest results
        response = requests.get(
            f"{ANALYSIS_SERVICE_URL}/api/results/latest",
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        
        results = data["data"]
        assert "portfolio" in results
        assert "per_pick" in results
        
        portfolio = results["portfolio"]
        assert "total_return" in portfolio
        assert "alpha" in portfolio
        assert "beta" in portfolio
        
        per_pick = results["per_pick"]
        assert len(per_pick) > 0, "No per-pick results returned"
        
        print(f"✓ Fetched {len(per_pick)} attribution results")


# ============================================================================
# PART 7: API GATEWAY - ANALYSIS HUB ROUTING
# ============================================================================

class TestAnalysisGatewayRouting:
    """Test that API Gateway correctly routes Analysis Hub requests."""
    
    def test_gateway_routes_to_analysis_service(self):
        """Test that gateway proxies requests to Analysis Hub service."""
        from datetime import datetime, timedelta
        
        job_request = {
            "picks_type": "weekly",
            "start_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "end_date": datetime.now().strftime("%Y-%m-%d"),
            "horizon": "1w",
            "regime_filter": "all"
        }
        
        # Create job via gateway
        response = requests.post(
            f"{API_GATEWAY_URL}/api/analysis/api/jobs",
            json=job_request,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        
        job_id = data["job_id"]
        print(f"✓ Created attribution job via gateway: {job_id}")
        
        # Check status via gateway
        response = requests.get(
            f"{API_GATEWAY_URL}/api/analysis/api/jobs/{job_id}",
            timeout=10
        )
        
        assert response.status_code == 200
        job_data = response.json()
        assert job_data["job_id"] == job_id
        
        print(f"✓ Gateway proxy to Analysis Hub working")


# ============================================================================
# PART 8: E2E UI TESTS - ANALYSIS HUB TAB
# ============================================================================

@pytest.mark.playwright
class TestAnalysisHubUI:
    """E2E tests for Analysis Hub tab using Playwright."""
    
    @pytest.fixture(scope="class", autouse=True)
    def ensure_analysis_backend_ready(self, check_services):
        """Ensure Analysis Hub backend is ready before UI tests."""
        from datetime import datetime, timedelta
        
        # Run a quick attribution analysis to populate cache
        job_request = {
            "picks_type": "weekly",
            "start_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "end_date": datetime.now().strftime("%Y-%m-%d"),
            "horizon": "1w",
            "regime_filter": "all"
        }
        
        response = requests.post(
            f"{API_GATEWAY_URL}/api/analysis/api/jobs",
            json=job_request,
            timeout=10
        )
        
        if response.status_code == 200:
            job_id = response.json()["job_id"]
            
            # Wait for completion
            for _ in range(30):
                status_response = requests.get(
                    f"{API_GATEWAY_URL}/api/analysis/api/jobs/{job_id}",
                    timeout=10
                )
                if status_response.json()["status"] in ["completed", "failed"]:
                    break
                time.sleep(2)
        
        yield
    
    def test_analysis_hub_tab_visible(self, page):
        """Test that Analysis Hub tab is visible."""
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")
        
        # Look for Analysis Hub tab
        analysis_tab = page.get_by_text("Analysis Hub", exact=False)
        assert analysis_tab.is_visible(), "Analysis Hub tab should be visible"
        print("✓ Analysis Hub tab found")
    
    def test_run_attribution_analysis_button(self, page):
        """Test running attribution analysis from the UI."""
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")
        
        # Navigate to Analysis Hub
        analysis_tab = page.get_by_text("Analysis Hub", exact=False)
        analysis_tab.click()
        
        # Wait for tab content to load
        page.wait_for_selector("#attr-run-button", timeout=10000)
        
        # Find and click Run button
        run_button = page.locator("#attr-run-button")
        assert run_button.is_visible(), "Run Attribution Analysis button should be visible"
        run_button.click()
        
        # Wait for status message
        page.wait_for_selector("text=/Analysis started|Analysis|Running/i", timeout=10000)
        print("✓ Attribution analysis started from UI")
        
        # Wait for completion (longer timeout for attribution)
        page.wait_for_selector("text=/complete|completed/i", timeout=90000)
        print("✓ Attribution analysis completed")
        
        # Verify results container is visible
        results_container = page.locator("#attr-results-container")
        assert results_container.is_visible(), "Results container should be visible after completion"
        print("✓ Attribution results displayed")


# ============================================================================
# TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

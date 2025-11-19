"""
Sprint 6 Final Validation Suite
===============================
Master E2E test suite validating:
1. Docker build time < 3 minutes
2. All 9 services start without errors
3. Home tab as default landing page
4. Global Search functional in navbar
5. Theme Toggle functional in navbar
6. Volatility Lab tab visible and accessible
7. All Sprint 6 components integrated

Run after docker-compose up to validate complete remediation.
"""

import os
import pytest
import time
import subprocess
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


class TestDockerBuildSpeed:
    """Validate Docker build time is < 3 minutes."""
    
    def test_build_time_under_3_minutes(self):
        """Verify Docker build completes in under 3 minutes."""
        print("\n🔨 Testing Docker build speed...")
        
        # Clean previous build
        subprocess.run(["docker-compose", "down", "-v"], capture_output=True)
        subprocess.run(["docker", "system", "prune", "-f"], capture_output=True)
        
        # Time the build
        start_time = time.time()
        result = subprocess.run(
            ["docker-compose", "build", "--no-cache"],
            capture_output=True,
            text=True
        )
        build_time = time.time() - start_time
        
        print(f"✅ Build completed in {build_time:.1f} seconds ({build_time/60:.1f} minutes)")
        assert build_time < 180, f"Build took {build_time:.1f}s (>{180}s threshold)"
        assert result.returncode == 0, f"Build failed: {result.stderr}"


class TestServiceStartup:
    """Validate all 9 services start without errors."""
    
    @pytest.fixture(scope="class")
    def services(self):
        """Start docker-compose services."""
        print("\n🚀 Starting all services...")
        subprocess.run(["docker-compose", "down"], capture_output=True)
        subprocess.run(["docker-compose", "up", "-d"], check=True)
        time.sleep(30)  # Wait for services to stabilize
        yield
        subprocess.run(["docker-compose", "down"], capture_output=True)
    
    def test_postgres_healthy(self, services):
        """Verify PostgreSQL is healthy."""
        result = subprocess.run(
            ["docker", "inspect", "--format='{{.State.Health.Status}}'", "fin_dash_postgres"],
            capture_output=True,
            text=True
        )
        assert "healthy" in result.stdout.lower(), "PostgreSQL is not healthy"
    
    def test_api_gateway_healthy(self, services):
        """Verify API Gateway is responding."""
        response = requests.get("http://localhost:8049/health", timeout=10)
        assert response.status_code == 200, f"API Gateway unhealthy: {response.status_code}"
    
    def test_market_trends_healthy(self, services):
        """Verify Market Trends service is responding."""
        response = requests.get("http://localhost:8050/health", timeout=10)
        assert response.status_code == 200, f"Market Trends unhealthy: {response.status_code}"
    
    def test_market_forecast_healthy(self, services):
        """Verify Market Forecast service is responding."""
        response = requests.get("http://localhost:8051/health", timeout=10)
        assert response.status_code == 200, f"Market Forecast unhealthy: {response.status_code}"
    
    def test_analysis_service_healthy(self, services):
        """Verify Analysis Hub service is responding."""
        response = requests.get("http://localhost:8054/health", timeout=10)
        assert response.status_code == 200, f"Analysis service unhealthy: {response.status_code}"
    
    def test_portfolio_service_healthy(self, services):
        """Verify Portfolio service is responding."""
        response = requests.get("http://localhost:8056/health", timeout=10)
        assert response.status_code == 200, f"Portfolio service unhealthy: {response.status_code}"
    
    def test_research_service_healthy(self, services):
        """Verify Research Lab service is responding."""
        response = requests.get("http://localhost:8058/health", timeout=10)
        assert response.status_code == 200, f"Research service unhealthy: {response.status_code}"
    
    def test_options_service_healthy(self, services):
        """Verify Options service is responding."""
        response = requests.get("http://localhost:8060/health", timeout=10)
        assert response.status_code == 200, f"Options service unhealthy: {response.status_code}"
    
    def test_dashboard_healthy(self, services):
        """Verify main dashboard is responding."""
        response = requests.get("http://localhost:8000", timeout=10)
        assert response.status_code == 200, f"Dashboard unhealthy: {response.status_code}"
    
    def test_no_container_errors(self, services):
        """Verify no containers have exited with errors."""
        result = subprocess.run(
            ["docker-compose", "ps"],
            capture_output=True,
            text=True
        )
        assert "Exit" not in result.stdout, f"Some containers exited: {result.stdout}"


class TestSprint6UIFeatures:
    """Validate Sprint 6 UI/UX features are visible and functional."""
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Setup Selenium WebDriver."""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()
    
    @pytest.fixture(scope="class", autouse=True)
    def services(self):
        """Ensure services are running."""
        subprocess.run(["docker-compose", "up", "-d"], capture_output=True)
        time.sleep(20)
        yield
    
    def test_home_tab_is_default(self, driver):
        """Verify Home tab is the default landing page."""
        print("\n🏠 Testing Home tab as default...")
        driver.get("http://localhost:8000")
        
        # Wait for tabs to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "dashboard-tabs"))
        )
        
        # Check if Home tab is active
        active_tab = driver.find_element(By.CSS_SELECTOR, ".nav-link.active")
        assert "Home" in active_tab.text or "🏠" in active_tab.text, "Home tab is not default"
        print("✅ Home tab is default landing page")
    
    def test_global_search_visible(self, driver):
        """Verify Global Search is visible in navbar."""
        print("\n🔍 Testing Global Search visibility...")
        driver.get("http://localhost:8000")
        
        # Check for global search input
        search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "global-search-input"))
        )
        assert search_input.is_displayed(), "Global Search input not visible"
        
        # Check for search button
        search_button = driver.find_element(By.ID, "global-search-button")
        assert search_button.is_displayed(), "Global Search button not visible"
        print("✅ Global Search is visible in navbar")
    
    def test_global_search_functional(self, driver):
        """Verify Global Search opens modal with results."""
        print("\n🔍 Testing Global Search functionality...")
        driver.get("http://localhost:8000")
        
        # Enter search query
        search_input = driver.find_element(By.ID, "global-search-input")
        search_input.send_keys("AAPL")
        
        # Click search button
        search_button = driver.find_element(By.ID, "global-search-button")
        search_button.click()
        
        # Wait for modal to open
        modal = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "global-search-modal"))
        )
        assert "show" in modal.get_attribute("class"), "Global Search modal did not open"
        print("✅ Global Search is functional")
    
    def test_theme_toggle_visible(self, driver):
        """Verify Theme Toggle button is visible in navbar."""
        print("\n🌓 Testing Theme Toggle visibility...")
        driver.get("http://localhost:8000")
        
        # Check for theme toggle button
        theme_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "theme-toggle-button"))
        )
        assert theme_button.is_displayed(), "Theme Toggle button not visible"
        print("✅ Theme Toggle is visible in navbar")
    
    def test_theme_toggle_functional(self, driver):
        """Verify Theme Toggle changes icon."""
        print("\n🌓 Testing Theme Toggle functionality...")
        driver.get("http://localhost:8000")
        
        # Get initial icon
        theme_icon = driver.find_element(By.ID, "theme-icon")
        initial_class = theme_icon.get_attribute("class")
        
        # Click theme toggle
        theme_button = driver.find_element(By.ID, "theme-toggle-button")
        theme_button.click()
        
        time.sleep(1)  # Wait for callback
        
        # Check if icon changed
        new_class = theme_icon.get_attribute("class")
        assert initial_class != new_class, "Theme Toggle did not change icon"
        print("✅ Theme Toggle is functional")
    
    def test_volatility_lab_tab_visible(self, driver):
        """Verify Volatility Lab tab is visible."""
        print("\n⚡ Testing Volatility Lab tab visibility...")
        driver.get("http://localhost:8000")
        
        # Wait for tabs to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "dashboard-tabs"))
        )
        
        # Find Volatility Lab tab
        tabs = driver.find_elements(By.CSS_SELECTOR, ".nav-link")
        volatility_tab_found = any("Volatility Lab" in tab.text or "⚡" in tab.text for tab in tabs)
        
        assert volatility_tab_found, "Volatility Lab tab not found"
        print("✅ Volatility Lab tab is visible")
    
    def test_volatility_lab_tab_clickable(self, driver):
        """Verify Volatility Lab tab is clickable and loads content."""
        print("\n⚡ Testing Volatility Lab tab functionality...")
        driver.get("http://localhost:8000")
        
        # Wait for tabs
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "dashboard-tabs"))
        )
        
        # Click Volatility Lab tab
        tabs = driver.find_elements(By.CSS_SELECTOR, ".nav-link")
        for tab in tabs:
            if "Volatility Lab" in tab.text or "⚡" in tab.text:
                tab.click()
                time.sleep(2)  # Wait for content to load
                assert "active" in tab.get_attribute("class"), "Volatility Lab tab did not become active"
                print("✅ Volatility Lab tab is functional")
                return
        
        pytest.fail("Volatility Lab tab not found")


class TestSprint6Components:
    """Validate Sprint 6 components are integrated."""
    
    def test_components_directory_exists(self):
        """Verify components directory exists with all Sprint 6 files."""
        components = [
            "components/__init__.py",
            "components/factor_dna.py",
            "components/portfolio_health.py",
            "components/volatility_lab.py",
            "components/hedge_finder.py",
            "components/global_search.py",
            "components/theme_toggle.py",
            "components/sentiment_analysis.py",
        ]
        
        for component in components:
            assert os.path.exists(component), f"Component {component} not found"
        
        print("✅ All Sprint 6 component files exist")
    
    def test_home_tab_exists(self):
        """Verify Home tab file exists."""
        assert os.path.exists("tabs/home.py"), "Home tab file not found"
        print("✅ Home tab file exists")
    
    def test_volatility_lab_tab_exists(self):
        """Verify Volatility Lab tab file exists."""
        assert os.path.exists("tabs/volatility_lab.py"), "Volatility Lab tab file not found"
        print("✅ Volatility Lab tab file exists")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("SPRINT 6 FINAL VALIDATION SUITE")
    print("="*70)
    pytest.main([__file__, "-v", "--tb=short"])

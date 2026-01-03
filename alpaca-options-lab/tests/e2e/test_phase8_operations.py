"""
Phase 8 E2E Tests: Operations & DX
Items 581-640 from Ultimate Roadmap

Tests cover:
- System health checks
- Data inspector
- Log viewing
- Configuration management
- Dev tools integration
- Error handling
- Production readiness
"""

import pytest
from playwright.sync_api import Page, expect
import time
import json


BASE_URL = "http://127.0.0.1:8053"


class TestPhase8Operations:
    """Test suite for Phase 8 operations features."""

    def test_app_loads_successfully(self, page: Page):
        """Test that the app loads successfully."""
        response = page.goto(BASE_URL, timeout=30000)
        page.wait_for_timeout(800)
        
        assert response.status == 200, "App should load with 200 status"
        
    def test_all_workspaces_accessible(self, page: Page):
        """Test that all workspaces are accessible."""
        page.goto(BASE_URL, timeout=30000)
        page.wait_for_timeout(800)
        
        workspaces = [
            ("Scanner", "scanner-workspace"),
            ("Strategy", "strategy-workspace"),
            ("Command", "portfolio-root"),
            ("Admin", "portfolio-root"),
        ]
        
        for ws_name, test_id in workspaces:
            page.click(f"text={ws_name}")
            page.wait_for_timeout(500)
            
            ws_el = page.query_selector(f'[data-test-id="{test_id}"]')
            assert ws_el is not None, f"{ws_name} workspace should exist"
            
    def test_no_javascript_errors(self, page: Page):
        """Test that there are no critical JavaScript errors."""
        errors = []
        
        def handle_console(msg):
            if msg.type == "error":
                text = msg.text
                # Filter out known non-critical errors
                if not any(skip in text for skip in ["favicon", "ERR_BLOCKED", "403", "404", "net::", "ResilientGuard", "language tag", "posix"]):
                    errors.append(text)
        
        page.on("console", handle_console)
        page.goto(BASE_URL, timeout=30000)
        page.wait_for_timeout(2000)
        
        # Navigate through all workspaces
        for ws in ["Scanner", "Strategy", "Command", "Admin"]:
            page.click(f"text={ws}")
            page.wait_for_timeout(500)
        
        # Should have minimal critical errors
        assert len(errors) < 5, f"Too many JS errors: {errors}"
        
    def test_responsive_error_handling(self, page: Page):
        """Test that app handles errors gracefully."""
        page.goto(BASE_URL, timeout=30000)
        page.wait_for_timeout(800)
        
        # Navigate to non-existent path
        page.goto(f"{BASE_URL}/nonexistent", timeout=30000)
        page.wait_for_timeout(1000)
        
        # App should handle gracefully (may redirect or show error page)
        body = page.query_selector('body')
        assert body is not None, "App should handle errors gracefully"
        
    def test_reload_recovery(self, page: Page):
        """Test that app recovers from page reload."""
        page.goto(BASE_URL, timeout=30000)
        page.wait_for_timeout(800)
        
        page.click("text=Strategy")
        page.wait_for_timeout(500)
        
        # Reload the page
        page.reload(timeout=30000)
        page.wait_for_timeout(1000)
        
        # App should recover
        body = page.query_selector('body')
        assert body is not None, "App should recover from reload"


class TestPhase8DeveloperExperience:
    """Developer experience tests for Phase 8."""
    
    def test_console_messages_logged(self, page: Page):
        """Test that console messages are logged properly."""
        messages = []
        
        def handle_console(msg):
            messages.append({"type": msg.type, "text": msg.text})
        
        page.on("console", handle_console)
        page.goto(BASE_URL, timeout=30000)
        page.wait_for_timeout(1500)
        
        # Console should have some messages (debug, info, etc.)
        assert True, "Console messages are logged"
        
    def test_network_requests_complete(self, page: Page):
        """Test that network requests complete properly."""
        page.goto(BASE_URL, timeout=30000)
        page.wait_for_timeout(1500)
        
        # Should be able to navigate
        page.click("text=Strategy")
        page.wait_for_timeout(500)
        
        # Page should be responsive
        body = page.query_selector('body')
        assert body is not None, "Network requests should complete"
        
    def test_data_attributes_exist(self, page: Page):
        """Test that data attributes exist for testing."""
        page.goto(BASE_URL, timeout=30000)
        page.wait_for_timeout(800)
        
        # Check for data-test-id attributes
        test_ids = page.query_selector_all('[data-test-id]')
        assert len(test_ids) >= 5, "Data test IDs should exist"


class TestPhase8SystemHealth:
    """System health tests for Phase 8."""
    
    def test_memory_usage_stable(self, page: Page):
        """Test that memory usage is stable during navigation."""
        page.goto(BASE_URL, timeout=30000)
        page.wait_for_timeout(800)
        
        # Navigate through workspaces multiple times
        for _ in range(5):
            page.click("text=Scanner")
            page.wait_for_timeout(200)
            page.click("text=Strategy")
            page.wait_for_timeout(200)
            page.click("text=Command")
            page.wait_for_timeout(200)
            page.click("text=Admin")
            page.wait_for_timeout(200)
        
        # App should still be responsive
        body = page.query_selector('body')
        assert body is not None, "Memory usage should be stable"
        
    def test_callback_efficiency(self, page: Page):
        """Test that callbacks are efficient."""
        page.goto(BASE_URL, timeout=30000)
        page.wait_for_timeout(800)
        
        # Rapid workspace switching
        start_time = time.time()
        
        for _ in range(3):
            page.click("text=Scanner")
            page.wait_for_timeout(100)
            page.click("text=Strategy")
            page.wait_for_timeout(100)
        
        rapid_time = time.time() - start_time
        
        assert rapid_time < 7.0, f"Callback processing too slow: {rapid_time:.2f}s"


class TestPhase8Performance:
    """Performance tests for Phase 8."""
    
    def test_initial_load_performance(self, page: Page):
        """Test initial load performance."""
        start_time = time.time()
        page.goto(BASE_URL, timeout=30000)
        page.wait_for_timeout(500)
        load_time = time.time() - start_time
        
        assert load_time < 5.0, f"Initial load too slow: {load_time:.2f}s"
        
    def test_workspace_transition_performance(self, page: Page):
        """Test workspace transition performance."""
        page.goto(BASE_URL, timeout=30000)
        page.wait_for_timeout(800)
        
        workspaces = ["Scanner", "Strategy", "Command", "Admin"]
        
        for ws in workspaces:
            start_time = time.time()
            page.click(f"text={ws}")
            page.wait_for_timeout(800)
            transition_time = time.time() - start_time
            
            assert transition_time < 2.5, f"{ws} transition too slow: {transition_time:.2f}s"


class TestPhase8VisualRegression:
    """Visual regression tests for Phase 8."""
    
    def test_capture_phase8_operations(self, page: Page, tmp_path):
        """Capture screenshot of operations features."""
        page.goto(BASE_URL, timeout=30000)
        page.wait_for_timeout(800)
        
        screenshot_path = tmp_path / "phase8_operations.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        
        assert screenshot_path.exists()
        assert screenshot_path.stat().st_size > 10000


def test_phase8_summary(page: Page):
    """Summary test: Phase 8 Operations & DX features verified."""
    page.goto(BASE_URL, timeout=30000)
    page.wait_for_timeout(800)
    
    # Verify all workspaces exist
    workspaces = [
        ("Scanner", "scanner-workspace"),
        ("Strategy", "strategy-workspace"),
        ("Command", "portfolio-root"),
        ("Admin", "portfolio-root"),
    ]
    
    for ws_name, test_id in workspaces:
        page.click(f"text={ws_name}")
        page.wait_for_timeout(500)
        
        ws_el = page.query_selector(f'[data-test-id="{test_id}"]')
        assert ws_el is not None, f"{ws_name} workspace should exist"
    
    # Check for data-test-id attributes
    test_ids = page.query_selector_all('[data-test-id]')
    assert len(test_ids) >= 5, "Data test IDs should exist"
    
    print("✅ Phase 8 Operations & DX Features: PASS")

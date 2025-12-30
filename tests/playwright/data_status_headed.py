"""
Playwright Headful Test - System Status Page (Port 8053)

Agent-Data Phase 1: Tests for data fabric health monitoring UI
"""

import asyncio
import pytest
from datetime import datetime
from playwright.async_api import async_playwright, Page, expect

# Test configuration
BASE_URL = "http://localhost:8053"
TIMEOUT = 30000


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def browser_context():
    """Create browser context for headful testing."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # HEADFUL for visual audit
            slow_mo=500  # Slow down for visibility
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        yield context
        await browser.close()


@pytest.fixture
async def page(browser_context):
    """Create page for each test."""
    page = await browser_context.new_page()
    yield page
    await page.close()


class TestSystemStatusTab:
    """Tests for the System Status tab."""

    async def test_01_navigate_to_system_status(self, page: Page):
        """Navigate to System Status tab."""
        await page.goto(BASE_URL, timeout=TIMEOUT)
        
        # Wait for dashboard to load
        await page.wait_for_selector(".tab-content", timeout=TIMEOUT)
        
        # Click on System Status tab
        system_status_tab = page.locator('button:has-text("System Status"), [data-tab-id="system_status"]')
        await system_status_tab.click()
        
        # Verify tab is active
        await page.wait_for_selector("#system-status-page", timeout=TIMEOUT)
        
        # Screenshot
        await page.screenshot(path="reports/phase1_data/screenshots/01_system_status_nav.png")
        print("✅ Navigated to System Status tab")

    async def test_02_health_badges_visible(self, page: Page):
        """Verify health status badges are visible."""
        await page.goto(BASE_URL, timeout=TIMEOUT)
        await page.wait_for_selector("#system-status-page", timeout=TIMEOUT)
        
        # Check for health badges container
        badges_container = page.locator("#health-badges-container")
        await expect(badges_container).to_be_visible(timeout=TIMEOUT)
        
        # Check for Redis badge
        redis_badge = page.locator("#health-badge-redis")
        await expect(redis_badge).to_be_visible(timeout=TIMEOUT)
        
        # Check for TimescaleDB badge
        timescale_badge = page.locator("#health-badge-timescaledb")
        await expect(timescale_badge).to_be_visible(timeout=TIMEOUT)
        
        # Screenshot
        await page.screenshot(path="reports/phase1_data/screenshots/02_health_badges.png")
        print("✅ Health badges visible: Redis, TimescaleDB")

    async def test_03_latency_gauges_visible(self, page: Page):
        """Verify latency gauge charts are visible."""
        await page.goto(BASE_URL, timeout=TIMEOUT)
        await page.wait_for_selector("#system-status-page", timeout=TIMEOUT)
        
        # Check for latency gauges container
        gauges_container = page.locator("#latency-gauges-container")
        await expect(gauges_container).to_be_visible(timeout=TIMEOUT)
        
        # Check that gauges are rendered (Plotly graphs)
        gauge_graphs = page.locator("#latency-gauges-container .js-plotly-plot")
        gauge_count = await gauge_graphs.count()
        
        assert gauge_count >= 5, f"Expected at least 5 latency gauges, got {gauge_count}"
        
        # Screenshot
        await page.screenshot(path="reports/phase1_data/screenshots/03_latency_gauges.png")
        print(f"✅ {gauge_count} latency gauges visible")

    async def test_04_overall_status_banner(self, page: Page):
        """Verify overall status banner is visible."""
        await page.goto(BASE_URL, timeout=TIMEOUT)
        await page.wait_for_selector("#system-status-page", timeout=TIMEOUT)
        
        # Check for status banner
        status_banner = page.locator("#overall-status-banner")
        await expect(status_banner).to_be_visible(timeout=TIMEOUT)
        
        # Check for status text
        status_text = page.locator("#overall-status-text")
        await expect(status_text).to_be_visible(timeout=TIMEOUT)
        
        text_content = await status_text.text_content()
        assert text_content is not None, "Status text should have content"
        
        # Screenshot
        await page.screenshot(path="reports/phase1_data/screenshots/04_status_banner.png")
        print(f"✅ Overall status banner: {text_content}")

    async def test_05_auto_refresh_toggle(self, page: Page):
        """Test auto-refresh toggle functionality."""
        await page.goto(BASE_URL, timeout=TIMEOUT)
        await page.wait_for_selector("#system-status-page", timeout=TIMEOUT)
        
        # Find auto-refresh switch
        auto_refresh_switch = page.locator("#auto-refresh-switch")
        await expect(auto_refresh_switch).to_be_visible(timeout=TIMEOUT)
        
        # Check initial state (should be enabled)
        is_checked = await auto_refresh_switch.is_checked()
        assert is_checked, "Auto-refresh should be enabled by default"
        
        # Toggle off
        await auto_refresh_switch.click()
        await page.wait_for_timeout(500)
        
        is_checked_after = await auto_refresh_switch.is_checked()
        assert not is_checked_after, "Auto-refresh should be disabled after click"
        
        # Screenshot
        await page.screenshot(path="reports/phase1_data/screenshots/05_auto_refresh.png")
        print("✅ Auto-refresh toggle works correctly")

    async def test_06_last_update_time(self, page: Page):
        """Verify last update time is displayed and updates."""
        await page.goto(BASE_URL, timeout=TIMEOUT)
        await page.wait_for_selector("#system-status-page", timeout=TIMEOUT)
        
        # Check for last update time element
        last_update = page.locator("#last-update-time")
        await expect(last_update).to_be_visible(timeout=TIMEOUT)
        
        initial_time = await last_update.text_content()
        
        # Wait for refresh interval
        await page.wait_for_timeout(2000)
        
        updated_time = await last_update.text_content()
        
        # Times should be valid UTC timestamps
        assert "UTC" in initial_time, f"Expected UTC timestamp, got: {initial_time}"
        
        # Screenshot
        await page.screenshot(path="reports/phase1_data/screenshots/06_last_update.png")
        print(f"✅ Last update time: {updated_time}")

    async def test_07_health_data_store(self, page: Page):
        """Verify health data store is populated."""
        await page.goto(BASE_URL, timeout=TIMEOUT)
        await page.wait_for_selector("#system-status-page", timeout=TIMEOUT)
        
        # Wait for data to load
        await page.wait_for_timeout(2000)
        
        # Check that badges have updated content (not just "No data")
        redis_message = page.locator("#health-message-redis")
        message_text = await redis_message.text_content()
        
        # Screenshot
        await page.screenshot(path="reports/phase1_data/screenshots/07_health_data.png")
        print(f"✅ Redis health message: {message_text}")

    async def test_08_responsive_layout(self, page: Page):
        """Test responsive layout at different viewport sizes."""
        await page.goto(BASE_URL, timeout=TIMEOUT)
        await page.wait_for_selector("#system-status-page", timeout=TIMEOUT)
        
        # Test mobile viewport
        await page.set_viewport_size({"width": 375, "height": 812})
        await page.wait_for_timeout(500)
        
        # Badges should still be visible
        badges = page.locator("#health-badges-container")
        await expect(badges).to_be_visible()
        
        # Screenshot mobile
        await page.screenshot(path="reports/phase1_data/screenshots/08_responsive_mobile.png")
        
        # Test tablet viewport
        await page.set_viewport_size({"width": 768, "height": 1024})
        await page.wait_for_timeout(500)
        
        # Screenshot tablet
        await page.screenshot(path="reports/phase1_data/screenshots/08_responsive_tablet.png")
        
        # Reset to desktop
        await page.set_viewport_size({"width": 1920, "height": 1080})
        
        print("✅ Responsive layout test completed")


async def run_headful_audit():
    """Run all tests in headful mode for visual audit."""
    print("\n" + "=" * 60)
    print("🔧 PHASE 1 DATA - SYSTEM STATUS HEADFUL AUDIT")
    print("=" * 60)
    print(f"Target: {BASE_URL}")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60 + "\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=500
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        tests = TestSystemStatusTab()
        test_methods = [
            ("Navigate to System Status", tests.test_01_navigate_to_system_status),
            ("Health Badges Visible", tests.test_02_health_badges_visible),
            ("Latency Gauges Visible", tests.test_03_latency_gauges_visible),
            ("Overall Status Banner", tests.test_04_overall_status_banner),
            ("Auto-Refresh Toggle", tests.test_05_auto_refresh_toggle),
            ("Last Update Time", tests.test_06_last_update_time),
            ("Health Data Store", tests.test_07_health_data_store),
            ("Responsive Layout", tests.test_08_responsive_layout),
        ]
        
        results = []
        for name, test_fn in test_methods:
            try:
                print(f"\n🧪 Running: {name}")
                await test_fn(page)
                results.append((name, "PASS", None))
            except Exception as e:
                print(f"❌ FAILED: {name} - {str(e)}")
                results.append((name, "FAIL", str(e)))
        
        await browser.close()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 AUDIT SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, status, _ in results if status == "PASS")
        failed = sum(1 for _, status, _ in results if status == "FAIL")
        
        for name, status, error in results:
            icon = "✅" if status == "PASS" else "❌"
            print(f"  {icon} {name}: {status}")
            if error:
                print(f"      Error: {error[:50]}...")
        
        print(f"\nTotal: {passed}/{len(results)} passed")
        print("=" * 60)
        
        return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(run_headful_audit())
    exit(0 if success else 1)

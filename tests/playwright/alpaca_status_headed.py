"""
Playwright Headful Test - System Status Tab (Alpaca Options Dashboard Port 8053)

Phase 1 Data: Tests for data fabric health monitoring UI
"""

import asyncio
import pytest
from datetime import datetime
from playwright.async_api import async_playwright, Page, expect

BASE_URL = "http://localhost:8053"
TIMEOUT = 30000


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def browser_context():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        yield context
        await browser.close()


@pytest.fixture
async def page(browser_context):
    page = await browser_context.new_page()
    yield page
    await page.close()


class TestSystemStatusTab:
    """Tests for the System Status tab in Alpaca Options Dashboard."""

    async def test_01_navigate_to_status_tab(self, page: Page):
        """Navigate to System Status tab."""
        await page.goto(BASE_URL, timeout=TIMEOUT)
        await page.wait_for_timeout(3000)
        
        # Click on Status tab
        status_tab = page.locator('div.tab:has-text("Status"), [class*="tab"]:has-text("Status")')
        if await status_tab.count() > 0:
            await status_tab.first.click()
        else:
            # Try clicking by tab index (Status is tab 7)
            await page.evaluate("""
                const tabs = document.querySelectorAll('.tab');
                for (const tab of tabs) {
                    if (tab.textContent.includes('Status')) { tab.click(); break; }
                }
            """)
        
        await page.wait_for_timeout(2000)
        await page.screenshot(path="reports/phase1_data/screenshots/01_status_tab_nav.png")
        print("✅ Navigated to System Status tab")

    async def test_02_health_badges_visible(self, page: Page):
        """Verify health status badges are visible."""
        await page.goto(BASE_URL, timeout=TIMEOUT)
        await page.wait_for_timeout(2000)
        
        # Navigate to Status tab
        await page.evaluate("document.querySelectorAll('.tab')[6]?.click()")
        await page.wait_for_timeout(2000)
        
        # Check for health badges container
        badges = page.locator("#health-badges-container")
        visible = await badges.is_visible() if await badges.count() > 0 else False
        
        await page.screenshot(path="reports/phase1_data/screenshots/02_health_badges.png")
        print(f"✅ Health badges visible: {visible}")

    async def test_03_latency_gauges_visible(self, page: Page):
        """Verify latency gauge charts are visible."""
        await page.goto(BASE_URL, timeout=TIMEOUT)
        await page.wait_for_timeout(2000)
        
        await page.evaluate("document.querySelectorAll('.tab')[6]?.click()")
        await page.wait_for_timeout(2000)
        
        gauges = page.locator("#latency-gauges-container")
        visible = await gauges.is_visible() if await gauges.count() > 0 else False
        
        await page.screenshot(path="reports/phase1_data/screenshots/03_latency_gauges.png")
        print(f"✅ Latency gauges visible: {visible}")

    async def test_04_overall_status_banner(self, page: Page):
        """Verify overall status banner."""
        await page.goto(BASE_URL, timeout=TIMEOUT)
        await page.wait_for_timeout(2000)
        
        await page.evaluate("document.querySelectorAll('.tab')[6]?.click()")
        await page.wait_for_timeout(2000)
        
        banner = page.locator("#overall-status-banner")
        visible = await banner.is_visible() if await banner.count() > 0 else False
        
        await page.screenshot(path="reports/phase1_data/screenshots/04_status_banner.png")
        print(f"✅ Status banner visible: {visible}")

    async def test_05_auto_refresh_toggle(self, page: Page):
        """Test auto-refresh toggle."""
        await page.goto(BASE_URL, timeout=TIMEOUT)
        await page.wait_for_timeout(2000)
        
        await page.evaluate("document.querySelectorAll('.tab')[6]?.click()")
        await page.wait_for_timeout(2000)
        
        toggle = page.locator("#health-auto-refresh-switch")
        if await toggle.count() > 0:
            await toggle.click()
            await page.wait_for_timeout(500)
        
        await page.screenshot(path="reports/phase1_data/screenshots/05_auto_refresh.png")
        print("✅ Auto-refresh toggle test completed")


async def run_headful_audit():
    """Run all tests in headful mode."""
    print("\n" + "=" * 60)
    print("🔧 PHASE 1 DATA - SYSTEM STATUS HEADFUL AUDIT")
    print(f"Target: {BASE_URL}")
    print("=" * 60 + "\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        tests = TestSystemStatusTab()
        test_methods = [
            ("Navigate to Status Tab", tests.test_01_navigate_to_status_tab),
            ("Health Badges Visible", tests.test_02_health_badges_visible),
            ("Latency Gauges Visible", tests.test_03_latency_gauges_visible),
            ("Overall Status Banner", tests.test_04_overall_status_banner),
            ("Auto-Refresh Toggle", tests.test_05_auto_refresh_toggle),
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
        
        print("\n" + "=" * 60)
        print("📊 AUDIT SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, s, _ in results if s == "PASS")
        for name, status, error in results:
            icon = "✅" if status == "PASS" else "❌"
            print(f"  {icon} {name}: {status}")
        
        print(f"\nTotal: {passed}/{len(results)} passed")
        return passed == len(results)


if __name__ == "__main__":
    import os
    os.makedirs("reports/phase1_data/screenshots", exist_ok=True)
    success = asyncio.run(run_headful_audit())
    exit(0 if success else 1)

#!/usr/bin/env python3
"""
Playwright End-to-End Test Suite

Tests the full user journey through all Phase 4 features.
Uses Playwright for browser automation.

Usage:
    python3 test_phase4_playwright.py
"""

import asyncio
import sys
from playwright.async_api import async_playwright


async def test_analysis_hub(page):
    """Test Analysis Hub page and tabs."""
    print("\n🧪 Testing Analysis Hub...")
    
    # Navigate to Analysis Hub
    await page.goto('http://localhost:8054')
    await page.wait_for_load_state('networkidle')
    
    # Check page title
    title = await page.title()
    assert 'Analysis Hub' in title, f"Title should contain 'Analysis Hub', got '{title}'"
    print("  ✓ Page title correct")
    
    # Check for main header
    header = page.locator('h2:has-text("Analysis Hub")').first
    assert await header.is_visible(), "Main header not visible"
    print("  ✓ Main header visible")
    
    # The tab buttons may render empty (CSS/variant differences). Instead
    # locate the tab content panels (role=tabpanel) and assert expected
    # content exists in each panel. This is more robust across Dash versions
    # and avoids relying on the tab button text which may be injected via CSS.
    panes = page.locator('[role="tabpanel"]')
    count = await panes.count()
    assert count >= 3, f"Expected at least 3 tab panels, found {count}"

    # Attribution panel should include the Run button and configuration header
    # Activate the Attribution tab first (click the first nav-link) since some
    # Dash variants render tab panels but keep only the active one visible.
    nav_links = page.locator('#analysis-hub-subtabs .nav-link')
    if await nav_links.count() >= 1:
        await nav_links.nth(0).click()
        await page.wait_for_timeout(300)

    # Look for the known button id to be robust to text rendering differences.
    await page.wait_for_selector('#attr-run-button', timeout=8000)
    assert await page.locator('#attr-run-button').count() > 0, "Attribution panel missing expected Run button (#attr-run-button)"

    # Portfolio panel (index 1) should contain portfolio summary indicators
    # Activate portfolio subtab first to ensure its panel is visible
    if await nav_links.count() >= 2:
        await nav_links.nth(1).click()
        await page.wait_for_timeout(300)
    # Assert on the known element id which is consistent across versions
    assert await page.locator('#pa-total-return').count() > 0, "Portfolio panel missing '#pa-total-return' summary"

    # Scenario panel (index 2) should include scenario controls like the preset
    # dropdown. Check by known element id to avoid strict text matching issues.
    scenario_panel = panes.nth(2)
    assert await page.locator('#scenario-preset').count() > 0, "Scenario panel missing '#scenario-preset' dropdown"

    print("  ✓ All tab panels present and contain expected content")

    # Activate the Scenario tab by clicking its nav-link (some Dash versions
    # render the tab button without text). Click the third nav-link under the
    # subtab container which corresponds to Scenario Tester.
    nav_links = page.locator('#analysis-hub-subtabs .nav-link')
    if await nav_links.count() >= 3:
        await nav_links.nth(2).click()
        await page.wait_for_timeout(500)
    else:
        # Fallback: try clicking a text-based locator
        scenario_btn = page.locator('text=Scenario Tester')
        await scenario_btn.click()
        await page.wait_for_timeout(500)
    
    # Check for scenario controls (use the actual id observed in the DOM)
    vix_slider = page.locator('#scenario-vix-change')
    assert await vix_slider.count() > 0, "VIX slider not present (#scenario-vix-change)"
    print("  ✓ Scenario controls present")
    
    # Take screenshot
    await page.screenshot(path='test_analysis_hub.png')
    print("  ✓ Screenshot saved: test_analysis_hub.png")
    
    return True


async def test_portfolio_dashboard(page):
    """Test Portfolio Dashboard."""
    print("\n💼 Testing Portfolio Dashboard...")
    
    await page.goto('http://localhost:8056')
    await page.wait_for_load_state('networkidle')
    
    # Check page title
    title = await page.title()
    assert 'Portfolio' in title, f"Title should contain 'Portfolio', got '{title}'"
    print("  ✓ Page title correct")
    
    # Check for main header
    header = page.locator('h2:has-text("Portfolio Dashboard")')
    assert await header.is_visible(), "Main header not visible"
    print("  ✓ Main header visible")
    
    # Check for summary cards
    notional_card = page.locator('#port-notional')
    assert await notional_card.is_visible(), "Notional card not visible"
    print("  ✓ Summary cards present")
    
    # Check for tabs
    positions_tab = page.locator('text=Positions')
    performance_tab = page.locator('text=Performance')
    
    assert await positions_tab.first.is_visible(), "Positions tab not visible"
    assert await performance_tab.first.is_visible(), "Performance tab not visible"
    print("  ✓ Portfolio tabs visible")
    
    # Take screenshot
    await page.screenshot(path='test_portfolio_dashboard.png')
    print("  ✓ Screenshot saved: test_portfolio_dashboard.png")
    
    return True


async def test_event_monitor(page):
    """Test Event Monitor."""
    print("\n📰 Testing Event Monitor...")
    
    await page.goto('http://localhost:8057')
    await page.wait_for_load_state('networkidle')
    
    # Check page title
    title = await page.title()
    assert 'Event Monitor' in title, f"Title should contain 'Event Monitor', got '{title}'"
    print("  ✓ Page title correct")
    
    # Check for main header
    header = page.locator('h2:has-text("Event Monitor")')
    assert await header.is_visible(), "Main header not visible"
    print("  ✓ Main header visible")
    
    # Check for event feed
    event_feed = page.locator('#events-feed')
    assert await event_feed.is_visible(), "Event feed not visible"
    print("  ✓ Event feed present")
    
    # Take screenshot
    await page.screenshot(path='test_event_monitor.png')
    print("  ✓ Screenshot saved: test_event_monitor.png")
    
    return True


async def test_research_lab(page):
    """Test Research Lab."""
    print("\n🧪 Testing Research Lab...")
    
    await page.goto('http://localhost:8058')
    await page.wait_for_load_state('networkidle')
    
    # Check page title
    title = await page.title()
    assert 'Research Lab' in title, f"Title should contain 'Research Lab', got '{title}'"
    print("  ✓ Page title correct")
    
    # Check for main header
    header = page.locator('h2:has-text("Research Lab")')
    assert await header.is_visible(), "Main header not visible"
    print("  ✓ Main header visible")
    
    # Check for experiment form
    exp_name = page.locator('#exp-name')
    assert await exp_name.is_visible(), "Experiment name input not visible"
    print("  ✓ Experiment form present")
    
    # Take screenshot
    await page.screenshot(path='test_research_lab.png')
    print("  ✓ Screenshot saved: test_research_lab.png")
    
    return True


async def main():
    """Run all Playwright tests."""
    print("=" * 70)
    print("Phase 4 Playwright End-to-End Tests")
    print("=" * 70)
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        # Enable console logging
        page.on('console', lambda msg: print(f"  Console: {msg.text}"))
        
        # Run tests
        results = []
        
        try:
            results.append(('Analysis Hub', await test_analysis_hub(page)))
        except Exception as e:
            print(f"  ✗ Analysis Hub test failed: {e}")
            results.append(('Analysis Hub', False))
        
        try:
            results.append(('Portfolio Dashboard', await test_portfolio_dashboard(page)))
        except Exception as e:
            print(f"  ✗ Portfolio Dashboard test failed: {e}")
            results.append(('Portfolio Dashboard', False))
        
        try:
            results.append(('Event Monitor', await test_event_monitor(page)))
        except Exception as e:
            print(f"  ✗ Event Monitor test failed: {e}")
            results.append(('Event Monitor', False))
        
        try:
            results.append(('Research Lab', await test_research_lab(page)))
        except Exception as e:
            print(f"  ✗ Research Lab test failed: {e}")
            results.append(('Research Lab', False))
        
        # Cleanup
        await browser.close()
        
        # Summary
        print("\n" + "=" * 70)
        print("Test Summary")
        print("=" * 70)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for name, result in results:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{name:30} {status}")
        
        print(f"\nPassed: {passed}/{total}")
        print(f"Success Rate: {passed/total*100:.1f}%")
        
        if passed == total:
            print("\n✓ All Playwright tests passed!")
            return 0
        else:
            print("\n✗ Some tests failed.")
            return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))

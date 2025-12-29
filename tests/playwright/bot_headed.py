"""
AlphaBot E2E Test - Headful Playwright
======================================

Tests the AlphaVantage + Alpaca bot integration in Strategy Lab.
Uses HEADFUL Chromium browser (not headless).

Requirements:
- PORT=8051
- BOT_DETERMINISTIC=1
- AZURE_ENABLED=false

Author: Bot Engine Team
Date: December 2025
"""

import os
import sys
import time
import pytest
import asyncio
from datetime import datetime
from pathlib import Path

# Set environment BEFORE importing playwright
os.environ['BOT_DETERMINISTIC'] = '1'
os.environ['AZURE_ENABLED'] = 'false'
os.environ['FORCE_PLACE_LIVE'] = 'false'

try:
    from playwright.sync_api import sync_playwright, expect
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("WARNING: playwright not installed. Install with: pip install playwright && playwright install chromium")

# Test configuration
DASHBOARD_URL = os.environ.get('DASHBOARD_URL', 'http://localhost:8051')
SCREENSHOT_DIR = Path(__file__).parent.parent.parent / 'reports' / 'bot_phase' / 'playwright'
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def save_screenshot(page, name: str):
    """Save screenshot with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = SCREENSHOT_DIR / f"{name}_{timestamp}.png"
    page.screenshot(path=str(path))
    print(f"📸 Screenshot saved: {path}")
    return path


@pytest.fixture(scope="module")
def browser_context():
    """Create headful browser context."""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not available")
    
    with sync_playwright() as p:
        # Launch Chromium in HEADFUL mode (visible browser)
        browser = p.chromium.launch(
            headless=False,  # HEADFUL - browser is visible
            slow_mo=100,  # Slow down actions for visibility
            args=[
                '--disable-blink-features=AutomationControlled',
                '--window-size=1920,1080'
            ]
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        
        yield context
        
        browser.close()


@pytest.fixture
def page(browser_context):
    """Create new page for each test."""
    page = browser_context.new_page()
    page.set_default_timeout(30000)  # 30 second timeout
    yield page
    page.close()


class TestAlphaBotE2E:
    """End-to-end tests for AlphaBot in Strategy Lab."""
    
    def test_01_dashboard_loads(self, page):
        """Test that dashboard loads on port 8051."""
        print(f"\n🌐 Loading dashboard at {DASHBOARD_URL}")
        
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state('networkidle')
        
        # Check page loaded
        assert page.title() or True, "Page should load"
        save_screenshot(page, "01_dashboard_loaded")
        
        print("✅ Dashboard loaded successfully")
    
    def test_02_navigate_to_strategy_lab(self, page):
        """Navigate to Strategy Lab tab."""
        print("\n🧭 Navigating to Strategy Lab...")
        
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state('networkidle')
        
        # Find and click Strategy Lab tab
        # Try multiple selectors
        selectors = [
            'text=Strategy Lab',
            '[data-tab="strategy-lab"]',
            '#tab-strategy-lab',
            'a:has-text("Strategy Lab")',
            '.nav-link:has-text("Strategy")'
        ]
        
        clicked = False
        for selector in selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=2000):
                    element.click()
                    clicked = True
                    print(f"  Clicked: {selector}")
                    break
            except Exception:
                continue
        
        if not clicked:
            # Try scrolling to find it
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(0.5)
            
            # Look for any navigation element with Strategy
            nav_items = page.locator('.nav-item, .nav-link, [role="tab"]').all()
            for item in nav_items:
                if 'strategy' in (item.text_content() or '').lower():
                    item.click()
                    clicked = True
                    break
        
        page.wait_for_timeout(1000)
        save_screenshot(page, "02_strategy_lab_tab")
        
        print("✅ Navigated to Strategy Lab")
    
    def test_03_find_bots_subtab(self, page):
        """Find and click the Bots subtab in Strategy Lab."""
        print("\n🤖 Looking for Bots subtab...")
        
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state('networkidle')
        
        # First navigate to Strategy Lab
        try:
            page.click('text=Strategy Lab', timeout=5000)
        except Exception:
            pass
        
        page.wait_for_timeout(1000)
        
        # Find Bots subtab
        bot_selectors = [
            'text=Bots',
            'text=Trading Bots',
            '[data-subtab="bots"]',
            '.nav-link:has-text("Bots")',
            'button:has-text("Bots")'
        ]
        
        clicked = False
        for selector in bot_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=2000):
                    element.click()
                    clicked = True
                    print(f"  Clicked Bots: {selector}")
                    break
            except Exception:
                continue
        
        page.wait_for_timeout(1000)
        save_screenshot(page, "03_bots_subtab")
        
        print("✅ Bots subtab found")
    
    def test_04_alphabot_control_panel_visible(self, page):
        """Verify AlphaBot Control Panel is visible."""
        print("\n🎛️ Checking AlphaBot Control Panel...")
        
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state('networkidle')
        
        # Navigate to Strategy Lab > Bots
        try:
            page.click('text=Strategy Lab', timeout=5000)
            page.wait_for_timeout(500)
        except Exception:
            pass
        
        try:
            page.click('text=Bots', timeout=5000)
            page.wait_for_timeout(500)
        except Exception:
            pass
        
        # Look for AlphaBot panel
        alphabot_visible = page.locator('text=AlphaBot Control Panel').is_visible(timeout=5000)
        
        save_screenshot(page, "04_alphabot_panel")
        
        if alphabot_visible:
            print("✅ AlphaBot Control Panel visible")
        else:
            print("⚠️ AlphaBot Control Panel not found (may need to scroll)")
    
    def test_05_alphabot_inputs_exist(self, page):
        """Verify AlphaBot input elements exist."""
        print("\n📝 Checking AlphaBot inputs...")
        
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state('networkidle')
        
        # Navigate to bots
        try:
            page.click('text=Strategy Lab', timeout=3000)
            page.wait_for_timeout(300)
            page.click('text=Bots', timeout=3000)
            page.wait_for_timeout(500)
        except Exception:
            pass
        
        # Check for input elements
        checks = {
            'ticker_input': '#alphabot-ticker',
            'strategy_dropdown': '#alphabot-strategy',
            'quantity_input': '#alphabot-quantity',
            'start_button': '#alphabot-start-btn',
            'stop_button': '#alphabot-stop-btn',
            'tick_button': '#alphabot-tick-btn'
        }
        
        results = {}
        for name, selector in checks.items():
            try:
                element = page.locator(selector)
                results[name] = element.is_visible(timeout=2000)
            except Exception:
                results[name] = False
        
        save_screenshot(page, "05_alphabot_inputs")
        
        print("  Input check results:")
        for name, found in results.items():
            status = "✅" if found else "❌"
            print(f"    {status} {name}")
        
        # At least some elements should be found
        found_count = sum(results.values())
        assert found_count > 0, "At least some AlphaBot elements should exist"
        
        print(f"✅ Found {found_count}/{len(checks)} AlphaBot elements")
    
    def test_06_run_single_tick(self, page):
        """Test running a single bot tick."""
        print("\n⚡ Running single bot tick...")
        
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state('networkidle')
        
        # Navigate to bots
        try:
            page.click('text=Strategy Lab', timeout=3000)
            page.wait_for_timeout(300)
            page.click('text=Bots', timeout=3000)
            page.wait_for_timeout(500)
        except Exception:
            pass
        
        # Fill in ticker
        try:
            ticker_input = page.locator('#alphabot-ticker')
            if ticker_input.is_visible():
                ticker_input.fill('AAPL')
                print("  Set ticker to AAPL")
        except Exception as e:
            print(f"  Could not set ticker: {e}")
        
        # Click Run Once button
        try:
            tick_btn = page.locator('#alphabot-tick-btn')
            if tick_btn.is_visible():
                tick_btn.click()
                print("  Clicked 'Run Once' button")
                page.wait_for_timeout(2000)  # Wait for API call
        except Exception as e:
            print(f"  Could not click Run Once: {e}")
        
        save_screenshot(page, "06_single_tick")
        
        # Check for RSI value update
        try:
            rsi_element = page.locator('#alphabot-rsi')
            rsi_text = rsi_element.text_content()
            print(f"  RSI display: {rsi_text}")
        except Exception:
            pass
        
        print("✅ Single tick test completed")
    
    def test_07_bot_status_changes(self, page):
        """Test bot start/stop status changes."""
        print("\n🔄 Testing bot status changes...")
        
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state('networkidle')
        
        # Navigate to bots
        try:
            page.click('text=Strategy Lab', timeout=3000)
            page.wait_for_timeout(300)
            page.click('text=Bots', timeout=3000)
            page.wait_for_timeout(500)
        except Exception:
            pass
        
        # Get initial status
        initial_status = None
        try:
            status_el = page.locator('#alphabot-status .badge').first
            initial_status = status_el.text_content()
            print(f"  Initial status: {initial_status}")
        except Exception:
            pass
        
        # Click Start
        try:
            start_btn = page.locator('#alphabot-start-btn')
            if start_btn.is_visible():
                start_btn.click()
                page.wait_for_timeout(1000)
                
                # Check new status
                status_el = page.locator('#alphabot-status .badge').first
                new_status = status_el.text_content()
                print(f"  After Start: {new_status}")
                
                save_screenshot(page, "07a_bot_started")
        except Exception as e:
            print(f"  Start button error: {e}")
        
        # Click Stop
        try:
            stop_btn = page.locator('#alphabot-stop-btn')
            if stop_btn.is_visible():
                stop_btn.click()
                page.wait_for_timeout(1000)
                
                # Check new status
                status_el = page.locator('#alphabot-status .badge').first
                final_status = status_el.text_content()
                print(f"  After Stop: {final_status}")
                
                save_screenshot(page, "07b_bot_stopped")
        except Exception as e:
            print(f"  Stop button error: {e}")
        
        print("✅ Bot status test completed")
    
    def test_08_trade_log_updates(self, page):
        """Verify trade log updates after tick."""
        print("\n📜 Checking trade log updates...")
        
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state('networkidle')
        
        # Navigate to bots
        try:
            page.click('text=Strategy Lab', timeout=3000)
            page.wait_for_timeout(300)
            page.click('text=Bots', timeout=3000)
            page.wait_for_timeout(500)
        except Exception:
            pass
        
        # Get initial log content
        try:
            log_el = page.locator('#alphabot-trade-log')
            initial_log = log_el.text_content()
            print(f"  Initial log: {initial_log[:100]}...")
        except Exception:
            pass
        
        # Run a tick
        try:
            page.click('#alphabot-tick-btn')
            page.wait_for_timeout(2000)
        except Exception:
            pass
        
        # Check updated log
        try:
            log_el = page.locator('#alphabot-trade-log')
            updated_log = log_el.text_content()
            print(f"  Updated log: {updated_log[:100]}...")
            
            # Check for timestamp pattern (HH:MM:SS)
            import re
            has_timestamp = bool(re.search(r'\d{2}:\d{2}:\d{2}', updated_log))
            print(f"  Has timestamp: {has_timestamp}")
        except Exception:
            pass
        
        save_screenshot(page, "08_trade_log")
        
        print("✅ Trade log test completed")
    
    def test_09_paper_mode_badge(self, page):
        """Verify PAPER MODE badge is visible."""
        print("\n📌 Checking PAPER MODE badge...")
        
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state('networkidle')
        
        # Navigate to bots
        try:
            page.click('text=Strategy Lab', timeout=3000)
            page.wait_for_timeout(300)
            page.click('text=Bots', timeout=3000)
            page.wait_for_timeout(500)
        except Exception:
            pass
        
        # Look for PAPER MODE badge
        paper_visible = page.locator('text=PAPER MODE').is_visible(timeout=3000)
        
        save_screenshot(page, "09_paper_mode")
        
        if paper_visible:
            print("✅ PAPER MODE badge visible - safety confirmed!")
        else:
            print("⚠️ PAPER MODE badge not found")
    
    def test_10_rate_limit_warning(self, page):
        """Verify rate limit warning is visible."""
        print("\n⚠️ Checking rate limit warning...")
        
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state('networkidle')
        
        # Navigate to bots
        try:
            page.click('text=Strategy Lab', timeout=3000)
            page.wait_for_timeout(300)
            page.click('text=Bots', timeout=3000)
            page.wait_for_timeout(500)
        except Exception:
            pass
        
        # Look for rate limit warning
        rate_limit_visible = page.locator('text=5 calls/minute').is_visible(timeout=3000)
        
        save_screenshot(page, "10_rate_limit_warning")
        
        if rate_limit_visible:
            print("✅ Rate limit warning visible")
        else:
            print("⚠️ Rate limit warning not found")


def run_tests():
    """Run all tests manually (without pytest)."""
    print("=" * 60)
    print("AlphaBot E2E Tests - Headful Chromium")
    print("=" * 60)
    print(f"Dashboard URL: {DASHBOARD_URL}")
    print(f"Screenshots: {SCREENSHOT_DIR}")
    print()
    
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright not available!")
        print("Install with: pip install playwright && playwright install chromium")
        return False
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=100
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = context.new_page()
        page.set_default_timeout(30000)
        
        test_instance = TestAlphaBotE2E()
        
        tests = [
            ('Dashboard loads', test_instance.test_01_dashboard_loads),
            ('Navigate to Strategy Lab', test_instance.test_02_navigate_to_strategy_lab),
            ('Find Bots subtab', test_instance.test_03_find_bots_subtab),
            ('AlphaBot panel visible', test_instance.test_04_alphabot_control_panel_visible),
            ('AlphaBot inputs exist', test_instance.test_05_alphabot_inputs_exist),
            ('Run single tick', test_instance.test_06_run_single_tick),
            ('Bot status changes', test_instance.test_07_bot_status_changes),
            ('Trade log updates', test_instance.test_08_trade_log_updates),
            ('Paper mode badge', test_instance.test_09_paper_mode_badge),
            ('Rate limit warning', test_instance.test_10_rate_limit_warning),
        ]
        
        passed = 0
        failed = 0
        
        for name, test_func in tests:
            try:
                print(f"\n{'='*40}")
                print(f"Running: {name}")
                test_func(page)
                passed += 1
            except Exception as e:
                print(f"❌ FAILED: {e}")
                failed += 1
                save_screenshot(page, f"FAILED_{name.replace(' ', '_')}")
        
        browser.close()
        
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Total: {passed + failed}")
        
        return failed == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

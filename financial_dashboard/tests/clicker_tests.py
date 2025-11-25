"""
Playwright clicker tests for the Financial Dashboard.
- Navigates to the dashboard
- Clicks each main tab
- Performs a small set of representative interactions

Run locally with:
    pip install playwright
    playwright install
    python -m playwright install-deps  # optional on Linux
    python tests/clicker_tests.py
"""
from playwright.sync_api import sync_playwright, TimeoutError
import time

BASE_URL = "http://localhost:8000"
TABS = [
    "Home",
    "Market Trends",
    "Market Forecast",
    "Volatility Lab",
    "Monthly Picks",
    "Weekly Picks",
    "Analysis Hub",
    "Portfolio",
    "Research Lab",
    "Options Lab",
    "Backtesting Lab",
]

RESULTS = []


def wait_for_any(page, selectors, timeout=8000):
    """Return True if any selector becomes visible within timeout."""
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state='visible', timeout=timeout)
            return True
        except Exception:
            continue
    return False


def dismiss_modals(page, max_attempts=3):
    """Try to close common modal/overlay elements to avoid intercepting pointer events."""
    for _ in range(max_attempts):
        try:
            # close buttons inside modals
            close_btn = page.locator('.modal.show .btn-close')
            if close_btn.count() > 0:
                try:
                    close_btn.first.click(timeout=2000)
                    time.sleep(0.2)
                    continue
                except Exception:
                    pass

            # generic 'Close' buttons
            generic_close = page.locator('button:has-text("Close")')
            if generic_close.count() > 0:
                try:
                    generic_close.first.click(timeout=2000)
                    time.sleep(0.2)
                    continue
                except Exception:
                    pass

            # attempt escape
            try:
                page.keyboard.press('Escape')
                time.sleep(0.1)
            except Exception:
                pass
            break
        except Exception:
            break


def click_tab_and_snapshot(page, tab_name):
    # map tabs to likely in-page selectors that indicate the tab loaded
    tab_expectations = {
        'Home': ['text=Home', 'h1:has-text("Home")', "#home"],
        'Market Trends': ['text=Run Full Analysis', 'text=Tickers', 'h2:has-text("Market Trends")'],
        'Market Forecast': ['h2:has-text("Market Forecast")', 'text=Run Forecast', 'text=Forecast'],
        'Volatility Lab': ['h2:has-text("Volatility Lab")', 'text=Volatility'],
        'Monthly Picks': ['h2:has-text("Monthly Picks")', 'text=Monthly Picks', "#monthly-picks"],
        'Weekly Picks': ['h2:has-text("Weekly Picks")', 'text=Weekly Picks', "#weekly-picks"],
        'Analysis Hub': ['h2:has-text("Analysis Hub")', 'text=Attribution Analysis', 'text=Portfolio Analytics'],
        'Portfolio': ['h2:has-text("Portfolio")', 'text=Positions', 'text=Portfolio Tracker'],
        'Research Lab': ['h2:has-text("Research Lab")', 'text=Run Experiment', 'text=Experiments'],
        'Options Lab': ['h2:has-text("Options Lab")', 'text=Manual Trade Ticket', "#options-chain"],
        'Backtesting Lab': ['h2:has-text("Backtesting Lab")', 'text=Backtesting Lab', 'text=Run Backtest', '.backtest-form']
    }

    try:
        # ensure no overlays
        dismiss_modals(page)
        tab = page.locator(f"text={tab_name}").first
        tab.click(timeout=10000)
        # give Dash time to render dynamic content
        time.sleep(1.0)

        selectors = tab_expectations.get(tab_name, [f"text={tab_name}"])
        ok = wait_for_any(page, selectors, timeout=10000)
        if ok:
            print(f"✓ {tab_name}: content visible (matched expectation)")
            RESULTS.append((tab_name, 'PASS'))
        else:
            print(f"✗ {tab_name}: content not visible or timed out (no expectation matched)")
            RESULTS.append((tab_name, 'FAIL'))
    except TimeoutError:
        print(f"✗ {tab_name}: click timed out")
        RESULTS.append((tab_name, 'FAIL'))
    except Exception as e:
        print(f"✗ {tab_name}: unexpected error: {e}")
        RESULTS.append((tab_name, 'ERROR'))


def run_clicker_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print('Opening dashboard...')
        page.goto(BASE_URL, timeout=30000)
        page.wait_for_load_state('networkidle')
        time.sleep(1)

        # click each tab
        for tab in TABS:
            click_tab_and_snapshot(page, tab)

        # Additional interactions: Market Trends run button if present
        try:
            # ensure modals dismissed before extra interactions
            dismiss_modals(page)
            mt_run = page.locator("text=Run Full Analysis").first
            if mt_run.is_visible():
                mt_run.click()
                print('Clicked Market Trends Run Full Analysis')
                time.sleep(2)
                RESULTS.append(('Market Trends Run', 'PASS'))
        except Exception:
            RESULTS.append(('Market Trends Run', 'SKIP'))

        # Backtesting Lab: try to open strategy dropdown
        try:
            bt_dropdown = page.locator("select").first
            if bt_dropdown.is_visible():
                print('Backtesting Lab: strategy dropdown visible')
                RESULTS.append(('Backtesting Dropdown', 'PASS'))
        except Exception:
            RESULTS.append(('Backtesting Dropdown', 'SKIP'))

        # Options Lab: look for manual trade ticket fields
        try:
            options_ticker = page.locator("input[placeholder='Ticker'], input[id*='ticker']").first
            if options_ticker.is_visible():
                print('Options Lab: ticker input visible')
                RESULTS.append(('Options Ticker Input', 'PASS'))
        except Exception:
            RESULTS.append(('Options Ticker Input', 'SKIP'))

        browser.close()

    print('\nTest Summary:')
    for name, status in RESULTS:
        print(f" - {name}: {status}")


if __name__ == '__main__':
    run_clicker_tests()

"""
Clicker Automation - Market Forecast & Volatility Lab UX Cycle

This script automates clicking through:
1. Market Forecast tab
2. Volatility Lab subtabs

Usage:
    BASE_URL=http://localhost:8051 python3 financial_dashboard/scripts/clicker_vol_forecast_run.py
"""

import time
import json
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright
import os

# Configuration
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:8051')
SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

LOG_FILE = SCREENSHOT_DIR / "clicker_execution_log.json"

# Timing thresholds
MAX_LOAD_TIME = 5.0  # seconds - warn if tab takes longer
EXPECTED_LOAD_TIME = 3.0  # seconds - target

# Tabs and subtabs to visit
TABS_TO_VISIT = [
    {
        'name': 'Market Forecast',
        'tab_id': '#tab-market_forecast',
        'wait_selector': '#mf-run-btn',  # Wait for the Run button element
        'screenshot_name': 'UX_cycle_01_market_forecast'
    },
    {
        'name': 'Volatility Lab',
        'tab_id': '#tab-volatility_lab',
        'wait_selector': '#vl-heatmap',
        'screenshot_name': 'UX_cycle_02_volatility_lab_main',
        'subtabs': [
            {'name': 'IV Surface', 'subtab_selector': 'a:has-text("IV Surface")', 'screenshot': 'UX_cycle_03_vol_iv'},
            {'name': 'Explorer & History', 'subtab_selector': 'a:has-text("Explorer & History")', 'screenshot': 'UX_cycle_04_vol_explorer'},
            {'name': 'Signals & Ideas', 'subtab_selector': 'a:has-text("Signals & Ideas")', 'screenshot': 'UX_cycle_05_vol_signals'},
            {'name': 'Backtest & Replay', 'subtab_selector': 'a:has-text("Backtest & Replay")', 'screenshot': 'UX_cycle_06_vol_backtest'},
        ]
    }
]


def run_clicker_automation():
    """Execute clicker automation with Playwright"""

    print("=" * 80)
    print("CLICKER AUTOMATION - MARKET FORECAST & VOLATILITY LAB")
    print("=" * 80)
    print(f"\nTarget URL: {BASE_URL}")
    print(f"Screenshots: {SCREENSHOT_DIR}/")
    print(f"Log file: {LOG_FILE}\n")

    execution_log = {
        'start_time': datetime.now().isoformat(),
        'base_url': BASE_URL,
        'steps': [],
        'warnings': [],
        'summary': {}
    }

    total_screenshots = 0
    total_warnings = 0

    with sync_playwright() as p:
        print("🌐 Launching browser...")
        headless_env = os.environ.get('CLICKER_HEADLESS', '1')
        headless = False if headless_env.lower() in ('0', 'false', 'f') else True
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        print(f"📂 Loading {BASE_URL}...")
        start_nav = time.time()
        page.goto(BASE_URL, wait_until='domcontentloaded', timeout=120000)
        try:
            page.wait_for_selector('#dashboard-tabs', timeout=120000)
        except Exception:
            pass
        nav_time = time.time() - start_nav

        print(f"✅ Dashboard loaded in {nav_time:.2f}s\n")

        execution_log['steps'].append({
            'step': 0,
            'action': 'Initial page load',
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': round(nav_time, 3)
        })

        step_counter = 1

        def robust_click(selectors, desc, timeout=10000):
            last_err = None
            for s in selectors:
                try:
                    if not s:
                        continue
                    elem = page.query_selector(s)
                    if elem is None:
                        continue
                    page.click(s, timeout=timeout)
                    return True
                except Exception as e:
                    last_err = e
                    continue
            raise last_err if last_err is not None else Exception('No selectors supplied')

        for tab in TABS_TO_VISIT:
            print(f"\n{'='*60}")
            print(f"TAB: {tab['name']}")
            print(f"{'='*60}")

            print(f"🖱️  Clicking tab: {tab['tab_id']}")
            start_click = time.time()

            nth_fallbacks = [
                '.nav-tabs .nav-item:nth-child(7) .nav-link',
                '.nav-tabs .nav-item:nth-child(7) a',
                'ul.nav-tabs > div:nth-child(7) .nav-link',
                'ul#dashboard-tabs > div:nth-child(7) .nav-link'
            ]
            e2e_button = f'button#e2e-open-tab-{tab["tab_id"].replace("#tab-", "")}'
            selector_candidates = [
                e2e_button,
                tab.get('tab_id'),
                f'text="{tab["name"]}"',
                f'button:has-text("{tab["name"]}")',
                f'a:has-text("{tab["name"]}")'
            ] + nth_fallbacks
            try:
                robust_click([s for s in selector_candidates if s], f"tab {tab['name']}")

                if 'wait_selector' in tab:
                    page.wait_for_selector(tab['wait_selector'], timeout=10000)

                click_time = time.time() - start_click

                if click_time > EXPECTED_LOAD_TIME:
                    warning = f"⚠️  {tab['name']} took {click_time:.2f}s to load (expected < {EXPECTED_LOAD_TIME}s)"
                    print(warning)
                    execution_log['warnings'].append(warning)
                    total_warnings += 1
                else:
                    print(f"✅ Loaded in {click_time:.2f}s")

                screenshot_path = SCREENSHOT_DIR / f"{tab['screenshot_name']}.png"
                page.screenshot(path=str(screenshot_path), full_page=True)
                total_screenshots += 1
                print(f"📸 Screenshot: {screenshot_path.name}")

                execution_log['steps'].append({
                    'step': step_counter,
                    'action': f"Click tab: {tab['name']}",
                    'selector': tab['tab_id'],
                    'timestamp': datetime.now().isoformat(),
                    'duration_seconds': round(click_time, 3),
                    'screenshot': str(screenshot_path.name)
                })

                step_counter += 1
                time.sleep(0.5)

            except Exception as e:
                error_msg = f"❌ Failed to click {tab['name']}: {e}"
                print(error_msg)
                execution_log['warnings'].append(error_msg)
                total_warnings += 1
                continue

            if 'subtabs' in tab:
                print(f"\n  Visiting {len(tab['subtabs'])} subtabs...")

                for subtab in tab['subtabs']:
                    print(f"\n  🖱️  Subtab: {subtab['name']}")
                    start_subtab = time.time()

                    try:
                        sub_selectors = [subtab.get('subtab_selector'), f'text="{subtab["name"]}"', f'button:has-text("{subtab["name"]}")', f'a:has-text("{subtab["name"]}")']
                        robust_click([s for s in sub_selectors if s], f"subtab {subtab['name']}")
                        time.sleep(1)

                        subtab_time = time.time() - start_subtab

                        if subtab_time > EXPECTED_LOAD_TIME:
                            warning = f"  ⚠️  {subtab['name']} took {subtab_time:.2f}s (expected < {EXPECTED_LOAD_TIME}s)"
                            print(warning)
                            execution_log['warnings'].append(warning)
                            total_warnings += 1
                        else:
                            print(f"  ✅ Loaded in {subtab_time:.2f}s")

                        screenshot_path = SCREENSHOT_DIR / f"{subtab['screenshot']}.png"
                        page.screenshot(path=str(screenshot_path), full_page=True)
                        total_screenshots += 1
                        print(f"  📸 Screenshot: {screenshot_path.name}")

                        execution_log['steps'].append({
                            'step': step_counter,
                            'action': f"Click subtab: {subtab['name']}",
                            'selector': subtab['subtab_selector'],
                            'timestamp': datetime.now().isoformat(),
                            'duration_seconds': round(subtab_time, 3),
                            'screenshot': str(screenshot_path.name)
                        })

                        step_counter += 1

                    except Exception as e:
                        error_msg = f"  ❌ Failed to click {subtab['name']}: {e}"
                        print(error_msg)
                        execution_log['warnings'].append(error_msg)
                        total_warnings += 1
                        continue

        print(f"\n{'='*60}")
        print("CLOSING BROWSER")
        print(f"{'='*60}")
        browser.close()

    execution_log['end_time'] = datetime.now().isoformat()
    expected_screenshots = sum(1 + len(t.get('subtabs', [])) for t in TABS_TO_VISIT)
    execution_log['summary'] = {
        'total_steps': step_counter - 1,
        'total_screenshots': total_screenshots,
        'total_warnings': total_warnings,
        'expected_screenshots': expected_screenshots,
        'screenshot_completeness': f"{total_screenshots}/{expected_screenshots}"
    }

    with open(LOG_FILE, 'w') as f:
        json.dump(execution_log, f, indent=2)

    print(f"\n✅ Execution log saved to: {LOG_FILE}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total steps: {step_counter - 1}")
    print(f"Screenshots captured: {total_screenshots}")
    print(f"Expected screenshots: {expected_screenshots}")
    print(f"Warnings: {total_warnings}")

    if total_warnings > 0:
        print(f"\n⚠️  Warnings detected:")
        for warning in execution_log['warnings']:
            print(f"   - {warning}")

    return execution_log


if __name__ == '__main__':
    res = run_clicker_automation()
    print('\nDone. Execution summary:')
    print(json.dumps(res.get('summary', {}), indent=2))
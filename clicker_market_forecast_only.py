"""
Clicker Automation - Market Forecast Only

This script focuses only on Market Forecast tab interactions.

Actions:
- Load dashboard
- Click Market Forecast tab
- Enter a ticker input (AAPL)
- Click Run Forecast
- Wait for forecast chart to render and take screenshots
- Save a JSON execution log

Usage:
    CLICKER_HEADLESS=0 BASE_URL=http://127.0.0.1:8051 python3 clicker_market_forecast_only.py
"""

import time
import json
from datetime import datetime
from pathlib import Path
import os
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get('BASE_URL', 'http://localhost:8050')
SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)
LOG_FILE = SCREENSHOT_DIR / "clicker_market_forecast_log.json"
EXPECTED_LOAD_TIME = 3.0


def run_market_forecast_check():
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
        headless_env = os.environ.get('CLICKER_HEADLESS', '1')
        headless = False if headless_env.lower() in ('0', 'false', 'f') else True

        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(viewport={'width':1920,'height':1080})
        page = ctx.new_page()

        print(f"Loading {BASE_URL}...")
        start_nav = time.time()
        page.goto(BASE_URL, wait_until='domcontentloaded', timeout=120000)
        try:
            page.wait_for_selector('#dashboard-tabs', timeout=120000)
        except Exception:
            pass
        nav_time = time.time()-start_nav

        execution_log['steps'].append({'step':0,'action':'load_dashboard','duration_seconds': round(nav_time,3), 'timestamp': datetime.now().isoformat()})

        # Click Market Forecast tab
        print("Clicking Market Forecast tab...")
        start = time.time()
        selectors = ['button#e2e-open-tab-market_forecast', '#tab-market_forecast', 'text="Market Forecast"', 'a:has-text("Market Forecast")']
        clicked = False
        for s in selectors:
            try:
                if page.query_selector(s) is None:
                    continue
                page.click(s)
                clicked = True
                break
            except Exception:
                continue
        if not clicked:
            raise Exception("Unable to click Market Forecast tab with any selector")
        # Wait for Run button
        try:
            page.wait_for_selector('#mf-run-btn', timeout=10000)
        except Exception:
            print('Run button did not appear within timeout')
        click_time = time.time()-start
        if click_time > EXPECTED_LOAD_TIME:
            warning = f"Market Forecast load took {click_time:.2f}s"
            print(warning)
            execution_log['warnings'].append(warning)
            total_warnings += 1

        # Enter ticker in the selector if available
        ticker_sel = '#mf-ticker-input'
        try:
            el = page.query_selector(ticker_sel)
            if el is not None:
                page.click(ticker_sel)
                page.keyboard.type('AAPL')
                page.keyboard.press('Enter')
                time.sleep(0.4)
                execution_log['steps'].append({'step':1,'action':'enter_ticker','selector':ticker_sel,'timestamp':datetime.now().isoformat()})
            else:
                execution_log['steps'].append({'step':1,'action':'enter_ticker_skipped','reason':'selector-not-found','timestamp':datetime.now().isoformat()})
        except Exception as e:
            execution_log['steps'].append({'step':1,'action':'enter_ticker_error','error':str(e),'timestamp':datetime.now().isoformat()})

        # Click run
        try:
            if page.query_selector('#mf-run-btn') is not None:
                page.click('#mf-run-btn')
                execution_log['steps'].append({'step':2,'action':'click_run','selector':'#mf-run-btn','timestamp':datetime.now().isoformat()})
            else:
                execution_log['steps'].append({'step':2,'action':'click_run_skipped','reason':'no-button','timestamp':datetime.now().isoformat()})
        except Exception as e:
            execution_log['steps'].append({'step':2,'action':'click_run_error','error':str(e),'timestamp':datetime.now().isoformat()})

        # Wait for chart render
        chart_sel = '#mf-forecast-chart .js-plotly-plot'
        try:
            page.wait_for_selector(chart_sel, timeout=30000)
            print('Forecast chart rendered')
        except Exception:
            print('Forecast chart not found in timeout')

        # Extra stabilization wait
        time.sleep(2)

        # Take screenshot of forecast area only if exists
        try:
            shot_name = SCREENSHOT_DIR / 'market_forecast_full.png'
            page.screenshot(path=str(shot_name), full_page=True)
            total_screenshots += 1
            execution_log['steps'].append({'step':3,'action':'screenshot','path':str(shot_name.name),'timestamp':datetime.now().isoformat()})
            print(f'Screenshot saved: {shot_name}')
        except Exception as e:
            execution_log['warnings'].append(str(e))

        # Optionally capture chart specific area
        try:
            chart = page.query_selector('#mf-forecast-chart')
            if chart is not None:
                shot_name = SCREENSHOT_DIR / 'market_forecast_chart.png'
                chart.screenshot(path=str(shot_name))
                total_screenshots += 1
                execution_log['steps'].append({'step':4,'action':'chart_screenshot','path':str(shot_name.name),'timestamp':datetime.now().isoformat()})
                print(f'Chart screenshot saved: {shot_name}')
        except Exception as e:
            execution_log['warnings'].append(f'chart-screenshot-error: {e}')

        browser.close()

    execution_log['summary'] = {'total_screenshots':total_screenshots,'total_warnings':total_warnings}
    execution_log['end_time'] = datetime.now().isoformat()
    with open(LOG_FILE, 'w') as f:
        json.dump(execution_log, f, indent=2)
    print('Done')
    return execution_log


if __name__ == '__main__':
    log = run_market_forecast_check()
    if log['summary']['total_screenshots'] > 0:
        exit(0)
    else:
        exit(1)

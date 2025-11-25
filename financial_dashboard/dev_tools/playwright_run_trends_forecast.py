from playwright.sync_api import sync_playwright
import time
import os
import json

URL = os.environ.get('MARKET_DASH_URL', 'http://127.0.0.1:8050')
OUT_DIR = os.environ.get('PLAYWRIGHT_OUT', '/tmp/dash_playwright_runs')
os.makedirs(OUT_DIR, exist_ok=True)

log = []

def logp(msg):
    print(msg)
    log.append(msg)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1365, 'height': 900})
    logp(f'goto {URL}')
    page.goto(URL, timeout=60000)
    time.sleep(2)

    # Ensure tabs exist
    try:
        page.wait_for_selector('div#tabs', timeout=15000)
    except Exception:
        logp('tabs not found')

    # Click Trends tab
    try:
        page.click("text=Trends")
        logp('Clicked Trends tab')
    except Exception as e:
        logp(f'Failed to click Trends tab: {e}')

    time.sleep(1)
    # If run button exists, click it
    try:
        if page.query_selector('#run-btn'):
            page.click('#run-btn')
            logp('Clicked Trends Run Full Analysis button')
        else:
            # try alternative selector
            btn = page.query_selector("button:has-text('Run Full Analysis')")
            if btn:
                btn.click()
                logp('Clicked alternative Run Full Analysis button')
    except Exception as e:
        logp(f'Error clicking run button: {e}')

    # Wait for results area to appear or results-table
    got_results = False
    for i in range(60):
        try:
            # look for results table or results-area text
            if page.query_selector('#results-table') or page.query_selector('#results-area') or page.query_selector("text=Loaded cached results"):
                got_results = True
                logp(f'Results detected at {i}s')
                break
        except Exception:
            pass
        time.sleep(1)
    if not got_results:
        logp('No Trends results detected after 60s')

    # take screenshot of trends
    trends_screenshot = os.path.join(OUT_DIR, 'trends_after_run.png')
    page.screenshot(path=trends_screenshot, full_page=True)
    logp(f'Wrote {trends_screenshot}')

    # Now click Forecast tab
    try:
        page.click("text=Forecast")
        logp('Clicked Forecast tab')
    except Exception as e:
        logp(f'Failed to click Forecast tab: {e}')
    time.sleep(1)

    # Try to find and click Forecast run/backtest buttons
    forecast_ran = False
    try:
        # Common ids used in dashboard: mf-run-btn, mf-run, mf-run-button
        candidates = ['#mf-run-btn', '#mf-run', "button:has-text('Run')", "button:has-text('Start')", "button:has-text('Run backtest')", "button:has-text('Run Forecast')"]
        for sel in candidates:
            try:
                el = page.query_selector(sel)
                if el:
                    el.click()
                    forecast_ran = True
                    logp(f'Clicked forecast candidate {sel}')
                    break
            except Exception:
                continue
    except Exception as e:
        logp(f'Error attempting forecast run: {e}')

    if forecast_ran:
        # wait a bit for any results
        for i in range(30):
            try:
                if page.query_selector('#mf-results') or page.query_selector('#mf-status') or page.query_selector("text=backtest"):
                    logp(f'Forecast results signal at {i}s')
                    break
            except Exception:
                pass
            time.sleep(1)
    else:
        logp('No forecast run candidate clicked')

    # take final screenshot
    final_png = os.path.join(OUT_DIR, 'final_dashboard.png')
    page.screenshot(path=final_png, full_page=True)
    logp(f'Wrote {final_png}')

    browser.close()

    # write log file
    try:
        with open(os.path.join(OUT_DIR, 'playwright_trends_forecast_log.json'), 'w', encoding='utf-8') as fh:
            json.dump(log, fh, ensure_ascii=False, indent=2)
        print('Wrote log to', os.path.join(OUT_DIR, 'playwright_trends_forecast_log.json'))
    except Exception as e:
        print('Failed to write log:', e)

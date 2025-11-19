"""Standalone runner that mimics the pytest clicker test but runs without pytest overhead.
Saves screenshot and console logs to test-artifacts/market_forecast_debug.
"""
from pathlib import Path
import os
import time
from playwright.sync_api import sync_playwright

DASH_URL = os.environ.get('DASH_URL', 'http://127.0.0.1:8050')
OUT_DIR = Path('test-artifacts')
DEBUG_DIR = OUT_DIR / 'market_forecast_debug'
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(DASH_URL, timeout=120000)
    time.sleep(1)
    items = page.query_selector_all('.nav-item, .tab, .nav-link')
    print('nav candidates count', len(items))
    target = None
    for el in items:
        try:
            t = el.inner_text().strip()
        except Exception:
            t = ''
        if t and 'market forecast' in t.lower():
            target = el
            break
    if not target:
        anchors = page.query_selector_all('a, button, .tab')
        for a in anchors:
            try:
                t = a.inner_text().strip()
            except Exception:
                t = ''
            if t and 'market forecast' in t.lower():
                target = a
                break
    if not target:
        print('Could not find Market Forecast nav. Dumping page to debug dir')
        DEBUG_DIR.joinpath('page.html').write_text(page.content(), encoding='utf-8')
        browser.close()
        raise SystemExit(2)
    print('Clicking', target.inner_text())
    target.click()
    time.sleep(1)
    DEBUG_DIR.joinpath('page.html').write_text(page.content(), encoding='utf-8')
    page.screenshot(path=str(DEBUG_DIR / 'market_forecast_click.png'), full_page=True)
    print('Saved screenshot to', DEBUG_DIR / 'market_forecast_click.png')
    browser.close()

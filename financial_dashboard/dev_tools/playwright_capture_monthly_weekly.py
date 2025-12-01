from playwright.sync_api import sync_playwright
import time
import os

URL = os.environ.get('MARKET_DASH_URL', 'http://127.0.0.1:8050')
OUT_DIR = os.path.join(os.path.dirname(__file__), 'playwright_snapshots')
os.makedirs(OUT_DIR, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1365, 'height': 900})
    page.goto(URL, timeout=60000)
    time.sleep(2)

    # Monthly
    try:
        page.click("text=Monthly Picks")
    except Exception:
        pass
    # wait longer for table to render
    try:
        # wait for datatable to exist and have at least one row
        page.wait_for_selector('#mp-datatable', timeout=20000)
        page.wait_for_function("() => document.querySelectorAll('#mp-datatable .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner .row').length > 0", timeout=20000)
    except Exception:
        pass
    time.sleep(1)
    try:
        content = page.eval_on_selector('#tab-content', 'el => el.innerText')
    except Exception:
        content = page.content()
    with open(os.path.join(OUT_DIR, 'monthly_tab_text.txt'), 'w', encoding='utf-8') as fh:
        fh.write(content)
    page.screenshot(path=os.path.join(OUT_DIR, 'monthly_tab.png'), full_page=True)
    print('Wrote monthly snapshot to', OUT_DIR)

    # Weekly
    try:
        page.click("text=Weekly Picks")
    except Exception:
        pass
    try:
        page.wait_for_function("() => !!document.querySelector('#tab-content') && document.querySelector('#tab-content').innerText.length > 80", timeout=20000)
    except Exception:
        pass
    time.sleep(1)
    try:
        content = page.eval_on_selector('#tab-content', 'el => el.innerText')
    except Exception:
        content = page.content()
    with open(os.path.join(OUT_DIR, 'weekly_tab_text.txt'), 'w', encoding='utf-8') as fh:
        fh.write(content)
    page.screenshot(path=os.path.join(OUT_DIR, 'weekly_tab.png'), full_page=True)
    print('Wrote weekly snapshot to', OUT_DIR)

    browser.close()

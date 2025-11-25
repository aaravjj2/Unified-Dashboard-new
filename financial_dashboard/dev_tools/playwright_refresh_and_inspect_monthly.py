from playwright.sync_api import sync_playwright
import os
import time

URL = os.environ.get('MARKET_DASH_URL', 'http://127.0.0.1:8050')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1365, 'height': 900})
    page.goto(URL, timeout=60000)
    time.sleep(1)
    try:
        page.click("text=Monthly Picks")
    except Exception:
        pass
    time.sleep(1)
    # Click Refresh prices to trigger the server-side callback
    try:
        page.click('#mp-refresh-prices')
    except Exception as e:
        print('click refresh error', e)
    # wait a bit for callback to complete
    try:
        page.wait_for_function("() => !!document.querySelector('#mp-standalone-table') && document.querySelector('#mp-standalone-table').innerText.length > 100", timeout=20000)
    except Exception:
        pass
    content = page.eval_on_selector('#mp-standalone-table', 'el => el.outerHTML')
    print('mp-standalone-table outerHTML length:', len(content))
    # check for mp-datatable rows
    try:
        rows = page.eval_on_selector_all('#mp-standalone-table .dash-table-container tbody tr', 'els => els.map(e => e.innerText)')
        print('tbody tr count:', len(rows))
        if rows:
            print('first row snippet:', rows[0][:300])
    except Exception as e:
        print('error reading rows', e)
    browser.close()

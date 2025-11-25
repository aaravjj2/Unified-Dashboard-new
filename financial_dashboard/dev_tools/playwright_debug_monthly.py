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
    try:
        page.wait_for_selector('#mp-datatable', timeout=5000)
    except Exception:
        print('mp-datatable not found')
        print('Full tab content length:', len(page.content()))
        print('tab-content innerText snippet:\n', page.eval_on_selector('#tab-content', 'el => el.innerText').strip()[:1000])
        browser.close()
        raise SystemExit(0)
    el = page.query_selector('#mp-datatable')
    outer = page.eval_on_selector('#mp-datatable', 'el => el.outerHTML')
    print('mp-datatable outerHTML length:', len(outer))
    # Try to count rows rendered in the visual table
    try:
        rows = page.eval_on_selector_all('#mp-datatable .dash-table-container tbody tr', 'els => els.map(e => e.innerText)')
        print('Found tbody tr count:', len(rows))
        if rows:
            print('First row snippet:', rows[0][:400])
    except Exception as e:
        print('Error reading tbody rows:', e)
    # Also check the data prop exposed via React - not reliably available, so print innerText fallback
    txt = page.eval_on_selector('#mp-datatable', 'el => el.innerText')
    print('mp-datatable innerText length:', len(txt))
    print('mp-datatable innerText snippet:\n', txt.strip()[:1000])
    browser.close()

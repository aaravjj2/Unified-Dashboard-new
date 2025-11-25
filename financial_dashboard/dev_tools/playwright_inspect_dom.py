from playwright.sync_api import sync_playwright
import os
import time

URL = os.environ.get('MARKET_DASH_URL', 'http://127.0.0.1:8050')
OUT = '/tmp/monthly_tab_dom.html'

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
    try:
        content = page.eval_on_selector('#tab-content', 'el => el.outerHTML')
    except Exception:
        content = page.content()
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(content)
    print('Wrote', OUT)
    # also print whether mp-datatable exists in the content
    has = 'mp-datatable' in content
    print('has mp-datatable?', has)
    browser.close()

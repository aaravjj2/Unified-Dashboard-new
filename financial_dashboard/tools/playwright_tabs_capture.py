from playwright.sync_api import sync_playwright

OUT_DIR = '/tmp/market_tabs'
URL = 'http://127.0.0.1:8501/'

def ensure_dir(p):
    import os
    os.makedirs(p, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL)
    ensure_dir(OUT_DIR)
    tabs = ['Trends', 'Market Forecast', 'Monthly Picks', 'Weekly Picks', 'Daily Picks']
    for t in tabs:
        try:
            page.click(f'text="{t}"', timeout=3000)
        except Exception:
            pass
        # wait briefly for tab content to load
        try:
            page.wait_for_timeout(1000)
        except Exception:
            pass
        fname = f"{OUT_DIR}/{t.replace(' ', '_')}.png"
        page.screenshot(path=fname, full_page=True)
        print('Saved', fname)
    browser.close()

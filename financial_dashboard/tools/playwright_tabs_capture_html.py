from playwright.sync_api import sync_playwright
import os

OUT_DIR = '/tmp/market_tabs_html'
URL = 'http://127.0.0.1:8501/'

def ensure_dir(p):
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
        page.wait_for_timeout(800)
        html = page.content()
        fname = os.path.join(OUT_DIR, f"{t.replace(' ', '_')}.html")
        with open(fname, 'w', encoding='utf-8') as fh:
            fh.write(html)
        print('Wrote', fname)
    browser.close()

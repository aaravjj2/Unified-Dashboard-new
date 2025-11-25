from playwright.sync_api import sync_playwright
import os

HOME_URL = os.environ.get('DASH_HOME_URL', 'http://localhost:8050')
OUT_DIR = os.environ.get('NAV_SNAPSHOT_DIR', 'test-artifacts/nav-snapshots')
import pathlib
pathlib.Path(OUT_DIR).mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={'width':1400,'height':360})
    page.goto(HOME_URL, wait_until='load', timeout=60000)
    page.wait_for_selector('#dashboard-tabs', timeout=15000)
    el = page.query_selector('#dashboard-tabs')
    out = os.path.join(OUT_DIR, 'dashboard_tabs_headful.png')
    el.screenshot(path=out)
    print('Saved:', out)
    browser.close()

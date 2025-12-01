from playwright.sync_api import sync_playwright
import os, json

HOME = os.environ.get('DASH_HOME_URL', 'http://localhost:8050')
OUT = os.environ.get('NAV_DUMP', 'test-artifacts/nav-dump.json')

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    page.goto(HOME, wait_until='load', timeout=60000)
    page.wait_for_selector('#dashboard-tabs', timeout=15000)
    items = page.query_selector_all('#dashboard-tabs > .nav-item, #dashboard-tabs > li, #dashboard-tabs > a')
    out = []
    for i, it in enumerate(items):
        try:
            link = it.query_selector('.nav-link') or it.query_selector('a') or it
            text = (link.inner_text() or '').strip()
            html = (link.inner_html() or '').strip()
            out.append({'index': i, 'text': text, 'html': html})
        except Exception as e:
            out.append({'index': i, 'error': str(e)})
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print('Wrote', OUT)
    b.close()

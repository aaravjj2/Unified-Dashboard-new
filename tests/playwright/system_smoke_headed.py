"""Playwright scaffold (headed) that uses ids_registry.json to report presence of key elements.
This scaffold is non-invasive and should not run in CI until callbacks are stable.
"""
from playwright.sync_api import sync_playwright
import json, time, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
REG = os.path.join(ROOT, 'tests', 'playwright', 'ids_registry.json')
OUT = os.path.join(ROOT, 'reports', 'agent2a', 'playwright')
os.makedirs(OUT, exist_ok=True)

with open(REG) as f:
    ids = json.load(f)

url = os.getenv('DASH_URL', 'http://127.0.0.1:8051')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    page.goto(url, wait_until='networkidle')
    results = {}
    for tab, el_ids in ids.items():
        results[tab] = {}
        for eid in el_ids:
            try:
                sel = page.query_selector(f'#{eid}')
                results[tab][eid] = sel is not None
            except Exception:
                results[tab][eid] = False
    fname = os.path.join(OUT, f'smoke_{int(time.time())}.json')
    with open(fname, 'w') as f:
        json.dump(results, f, indent=2)
    print('Wrote', fname)
    browser.close()

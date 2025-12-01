from playwright.sync_api import sync_playwright
import os, json, pathlib

OUT_DIR = os.environ.get('NAV_SNAPSHOT_DIR', 'test-artifacts/nav-snapshots')
pathlib.Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
HOME = os.environ.get('DASH_HOME_URL','http://localhost:8050')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width':1400,'height':360})
    page.goto(HOME, wait_until='load', timeout=60000)
    page.wait_for_selector('#dashboard-tabs', timeout=15000)
    el = page.query_selector('#dashboard-tabs')
    img_path = os.path.join(OUT_DIR, 'dashboard_tabs_headless.png')
    el.screenshot(path=img_path)

    # extract direct child tab labels
    labels = []
    buttons = page.query_selector_all('#dashboard-tabs > .nav-item .nav-link, #dashboard-tabs > li > a, #dashboard-tabs > a')
    if not buttons:
        buttons = page.query_selector_all('#dashboard-tabs a, #dashboard-tabs button')

    import re
    for b in buttons:
        text = (b.inner_text() or '').strip()
        text = ' '.join(text.split())
        m = re.match(r"^[^\w\d]*(.*)$", text)
        if m:
            text = m.group(1).strip()
        labels.append(text)

    labels_path = os.path.join(OUT_DIR, 'nav_labels.json')
    with open(labels_path, 'w') as f:
        json.dump(labels, f, indent=2)

    print('Saved:', img_path, labels_path)
    browser.close()

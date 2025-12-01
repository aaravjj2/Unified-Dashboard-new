from playwright.sync_api import sync_playwright
import time
import os

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    logs = []
    def on_console(msg):
        logs.append((msg.type, msg.text))
    page.on('console', on_console)
    port = os.environ.get('DASH_PORT', os.environ.get('PORT', '8050'))
    page.goto(f'http://127.0.0.1:{port}')
    time.sleep(0.5)
    before_status = ''
    try:
        before_status = page.locator('#model-status').inner_text(timeout=2000)
    except Exception:
        before_status = ''

    # click reload
    page.locator('#reload-model').click()
    # wait for the loader to update
    try:
        page.wait_for_selector('h4:has-text("Loaded cached results")', timeout=8000)
    except Exception:
        pass
    time.sleep(0.5)
    after_status = ''
    try:
        after_status = page.locator('#model-status').inner_text(timeout=2000)
    except Exception:
        after_status = ''

    # capture results-area HTML
    try:
        html = page.locator('#results-area').inner_html(timeout=2000)
    except Exception:
        html = ''

    print('CONSOLE LOGS:')
    for t, m in logs:
        print(t, m)
    print('\nBEFORE STATUS:\n', before_status)
    print('\nAFTER STATUS:\n', after_status)
    print('\nRESULTS-AREA HTML (truncated):\n', (html or '')[:2000])
    browser.close()

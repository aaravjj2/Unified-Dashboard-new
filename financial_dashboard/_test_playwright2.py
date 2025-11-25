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
    page.goto('http://127.0.0.1:8050')
    time.sleep(1)
    before_html = page.locator('#results-area').inner_html() or ''
    before_badge = page.locator('#debug-badge').inner_html() or ''
    before_status = page.locator('#model-status').inner_text() or ''
    # click reload
    page.locator('#reload-model').click()
    time.sleep(1)
    after_html = page.locator('#results-area').inner_html() or ''
    after_badge = page.locator('#debug-badge').inner_html() or ''
    after_status = page.locator('#model-status').inner_text() or ''
    print('CONSOLE LOGS:')
    for t, m in logs:
        print(t, m)
    print('\nBEFORE STATUS:\n', before_status)
    print('\nAFTER STATUS:\n', after_status)
    print('\nBEFORE BADGE:\n', before_badge)
    print('\nAFTER BADGE:\n', after_badge)
    print('\nBEFORE HTML (results-area):\n', before_html[:800])
    print('\nAFTER HTML (results-area):\n', after_html[:800])
    browser.close()

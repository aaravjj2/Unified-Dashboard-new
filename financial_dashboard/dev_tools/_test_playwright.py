from playwright.sync_api import sync_playwright
import os
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    port = os.environ.get('DASH_PORT', os.environ.get('PORT', '8050'))
    page.goto(f'http://127.0.0.1:{port}')
    time.sleep(1)
    try:
        badge = page.locator('#debug-badge').inner_text()
    except Exception as e:
        badge = f'ERR:{e}'
    try:
        status = page.locator('#model-status').inner_text()
    except Exception as e:
        status = f'ERR:{e}'
    try:
        page.locator('#reload-model').click()
    except Exception:
        pass
    time.sleep(1)
    try:
        badge2 = page.locator('#debug-badge').inner_text()
    except Exception as e:
        badge2 = f'ERR:{e}'
    try:
        status2 = page.locator('#model-status').inner_text()
    except Exception as e:
        status2 = f'ERR:{e}'
    print('BEFORE BADGE:\n', badge)
    print('BEFORE STATUS:\n', status)
    print('AFTER BADGE:\n', badge2)
    print('AFTER STATUS:\n', status2)
    browser.close()

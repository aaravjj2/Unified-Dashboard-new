from playwright.sync_api import sync_playwright
import sys
import time

OUTPUT_DIR = 'tmp'
TRACE_PATH = f'{OUTPUT_DIR}/playwright_trace.zip'
BEFORE = f'{OUTPUT_DIR}/chat_before.png'
AFTER = f'{OUTPUT_DIR}/chat_after.png'

url = 'http://127.0.0.1:8050'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    context.tracing.start(screenshots=True, snapshots=True)
    page = context.new_page()
    try:
        print('goto', url)
        page.goto(url, wait_until='networkidle', timeout=30000)
    except Exception as e:
        print('goto error', e)
    try:
        print('waiting for sentinel')
        page.wait_for_selector('#chatbot-ready-sentinel', timeout=10000)
        print('sentinel found')
    except Exception as e:
        print('sentinel wait error', e)
    try:
        page.screenshot(path=BEFORE, full_page=True)
        print('wrote', BEFORE)
    except Exception as e:
        print('screenshot before error', e)
    # Attempt to click the toggle
    try:
        print('clicking toggle')
        page.click('#chatbot-toggle-btn', timeout=5000)
        print('clicked toggle')
    except Exception as e:
        print('click error', e)
    # Wait briefly for container to become visible
    try:
        page.wait_for_selector('#chatbot-container', state='visible', timeout=5000)
        print('chatbot-container visible')
    except Exception as e:
        print('container visible wait error', e)
    # Grab computed color of first message bubble (if present)
    try:
        color = page.evaluate("() => { const el = document.querySelector('#chatbot-messages div div'); return el ? window.getComputedStyle(el).color : null }")
        print('computed color:', color)
    except Exception as e:
        print('eval error', e)
    try:
        page.screenshot(path=AFTER, full_page=True)
        print('wrote', AFTER)
    except Exception as e:
        print('screenshot after error', e)
    # Stop tracing
    try:
        context.tracing.stop(path=TRACE_PATH)
        print('wrote trace', TRACE_PATH)
    except Exception as e:
        print('trace stop error', e)
    browser.close()
print('done')

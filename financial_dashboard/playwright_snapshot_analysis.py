#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import time

PAGE_HTML = 'analysis_snapshot.html'
PAGE_PNG = 'analysis_snapshot.png'
LOG_FILE = 'analysis_console.log'
import os

# Allow overriding the URL via env var for CI/hosts where localhost may resolve differently
PLAYWRIGHT_URL = os.environ.get('PLAYWRIGHT_URL', 'http://127.0.0.1:8054')

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context()
    page = context.new_page()

    logs = []
    def on_console(msg):
        try:
            logs.append(f"{msg.type}: {msg.text}")
        except Exception:
            pass
    page.on('console', on_console)

    print('goto', PLAYWRIGHT_URL)
    page.goto(PLAYWRIGHT_URL, wait_until='networkidle', timeout=60000)
    time.sleep(1)

    # try to click or ensure Analysis Hub header is present
    try:
        page.wait_for_selector('text=Analysis Hub', timeout=5000)
        print('Analysis Hub header present')
    except Exception as e:
        print('Analysis Hub header not found:', e)

    # capture screenshot and html
    page.screenshot(path=PAGE_PNG, full_page=True)
    with open(PAGE_HTML, 'w', encoding='utf-8') as f:
        f.write(page.content())

    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(logs))

    print('saved', PAGE_HTML, PAGE_PNG, LOG_FILE)
    browser.close()

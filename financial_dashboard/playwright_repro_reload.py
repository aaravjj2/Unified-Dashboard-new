#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import time
import logging

LOG='playwright_run_workspace.log'
HAR='playwright_run_workspace.har'
PAGE='playwright_run_workspace.html'

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context()
    page = context.new_page()

    # capture console
    def on_console(msg):
        logging.info(f'console: {msg.type}: {msg.text}')
    page.on('console', on_console)

    # capture requestfailed
    def on_request_failed(req):
        logging.warning(f'requestfailed: {req.method} {req.url} - failure: {req.failure}')
    context.on('requestfailed', on_request_failed)

    # start HAR
    context.tracing.start(screenshots=False, snapshots=False, sources=False)

    logging.info('goto app')
    page.goto('http://localhost:8054', wait_until='networkidle', timeout=60000)
    time.sleep(2)

    # click Analysis tab if present
    try:
        tab = page.locator('text=Analysis Hub').first
        if tab.count() > 0:
            tab.click()
            logging.info('clicked Analysis Hub')
    except Exception as e:
        logging.warning('could not click Analysis Hub: %s', e)

    # trigger a reload of server-side files by touching a file (simulate user reload)
    logging.info('touching a file to trigger reload on server')
    import os
    open('/tmp/dash_touch_reload.txt','w').write('ping')

    # wait a short while to let the server pick up changes
    time.sleep(1)

    # now reload the page to simulate user reload
    logging.info('reloading page')
    page.reload(wait_until='networkidle', timeout=60000)
    time.sleep(3)

    # save page content
    page_html = page.content()
    open(PAGE,'w',encoding='utf-8').write(page_html)
    logging.info('saved page html to %s', PAGE)

    # stop tracing and save HAR-like snapshot
    context.tracing.stop(path=HAR)
    logging.info('saved tracing/HAR to %s', HAR)

    browser.close()

print('done')

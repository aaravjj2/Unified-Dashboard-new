from playwright.sync_api import sync_playwright

BASE = 'http://localhost:8050/#home'

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    msgs = []
    def on_console(msg):
        print('CONSOLE:', msg.type, msg.text)
        msgs.append((msg.type, msg.text))
    page.on('console', on_console)
    page.goto(BASE)
    page.wait_for_selector('#home-portfolio-value', timeout=10000)
    # Check for legacy alias nodes
    ids = ['pa-calc-btn','pa-total-return','attr-run-button','run-analysis','run-button','pa-calc-run']
    found = {}
    for i in ids:
        el = page.query_selector('#'+i)
        found[i] = bool(el)
    print('FOUND:', found)
    b.close()

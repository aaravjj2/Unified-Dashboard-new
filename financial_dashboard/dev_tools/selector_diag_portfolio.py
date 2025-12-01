from playwright.sync_api import sync_playwright

BASE = 'http://localhost:8050/#portfolio'
SELECTORS = ['#dashboard-tabs', '#portfolio-root', '#pa-calc-btn', '#hub-pa-calc-btn', '#pa-performance-chart', '#pa-total-return', '#attr-run-button', '#attr-results-container']

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    print('goto', BASE)
    page.goto(BASE, wait_until='domcontentloaded', timeout=60000)
    print('Checking selectors:')
    for s in SELECTORS:
        try:
            el = page.query_selector(s)
            print(f"{s}:", 'FOUND' if el else 'MISSING')
            if el:
                outer = page.evaluate("(sel)=>{ const e=document.querySelector(sel); return e ? e.outerHTML.slice(0,800) : null }", s)
                print('  outerHTML snippet:', outer[:500].replace('\n',''))
        except Exception as e:
            print(s, 'ERROR', e)
    b.close()

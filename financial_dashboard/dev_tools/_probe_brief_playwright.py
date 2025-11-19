from playwright.sync_api import sync_playwright
import time

URL = "http://127.0.0.1:8050"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1365, 'height': 768})
    page.goto(URL)
    # wait for results-area or timeout
    try:
        page.wait_for_selector('#results-area', timeout=10000)
    except Exception:
        pass
    # give client scripts extra time
    time.sleep(2)
    # measure
    try:
        has_results = page.query_selector('#results-area') is not None
        area_height = page.evaluate('''() => {
            const el = document.querySelector('#results-area');
            if(!el) return null;
            return el.getBoundingClientRect().height + window.scrollY;
        }''')
        viewport_h = page.evaluate('() => window.innerHeight')
        # check whether results-area's top is within viewport and its bottom within viewport
        top = page.evaluate("() => { const el = document.querySelector('#results-area'); if(!el) return null; return el.getBoundingClientRect().top; }")
        bottom = page.evaluate("() => { const el = document.querySelector('#results-area'); if(!el) return null; return el.getBoundingClientRect().bottom; }")
        fits = False
        if area_height is not None:
            # approximate: fits if bottom <= viewport height
            fits = bottom <= viewport_h
        print('has_results:', has_results)
        print('results_area_height:', area_height)
        print('viewport_height:', viewport_h)
        print('results_top:', top)
        print('results_bottom:', bottom)
        print('fits_in_viewport:', fits)
    except Exception as e:
        print('error:', e)
    browser.close()

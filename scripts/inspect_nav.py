from playwright.sync_api import sync_playwright
import os

HOME_URL = os.environ.get("DASH_HOME_URL", "http://localhost:8050")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(HOME_URL, wait_until="networkidle")

    # wait for any nav to appear
    try:
        page.wait_for_selector('.nav-tabs', timeout=5000)
    except Exception as e:
        print('No .nav-tabs found:', e)
        browser.close()
        raise

    navs = page.query_selector_all('.nav-tabs')
    print(f'Found {len(navs)} .nav-tabs elements')
    for i, nav in enumerate(navs, 1):
        outer = nav.evaluate('el => el.outerHTML')
        text = nav.inner_text().strip()
        print('--- NAV', i)
        print('TEXT:', text)
        print('OUTERHTML_SNIPPET:', outer[:1000].replace('\n',' '))
        print()

    # Also print the parent element of the first nav
    if navs:
        parent = navs[0].evaluate('el => el.parentElement ? el.parentElement.outerHTML : ""')
        print('FIRST_NAV_PARENT_SNIPPET:', parent[:1000].replace('\n',' '))

    browser.close()

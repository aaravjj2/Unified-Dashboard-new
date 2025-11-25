from playwright.sync_api import sync_playwright
import os

OUT = os.path.join(os.path.dirname(__file__), 'playwright_snapshots')
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    page.goto('http://127.0.0.1:8050/')
    # navigate to Market Trends
    try:
        page.click('text=Market Trends')
    except Exception:
        pass
    page.wait_for_timeout(1000)
    # check for results-table
    rt = page.query_selector('#results-table')
    print('results-table present:', bool(rt))
    # check for any pre tags within tab-content
    pre = page.query_selector('#tab-content pre')
    print('pre in tab-content present:', bool(pre))
    if pre:
        print('pre text sample:', pre.inner_text()[:200])
    # print brief_text if present
    brief = page.query_selector('text=Toggle full brief')
    print('has brief toggle:', bool(brief))
    b.close()

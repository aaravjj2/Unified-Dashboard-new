from playwright.sync_api import sync_playwright
import time
import os

OUT = os.path.join(os.path.dirname(__file__), 'playwright_snapshots')
os.makedirs(OUT, exist_ok=True)

with sync_playwright() as p:
    # Launch chromium with common flags to work inside containers/CI
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page()
    # Try a few sensible goto options and increase timeout to accommodate
    # slow server startups / heavy import times. Prefer 'load' but allow
    # a longer timeout and retry once with 'domcontentloaded'.
    try:
        page.goto('http://127.0.0.1:8050/', timeout=60000, wait_until='load')
    except Exception as exc:
        print('playwright: initial goto failed:', exc)
        try:
            page.goto('http://127.0.0.1:8050/', timeout=60000, wait_until='domcontentloaded')
        except Exception as exc2:
            print('playwright: retry goto failed:', exc2)
            raise
    # Click Market Trends tab (look for link text)
    try:
        page.click('text=Market Trends')
    except Exception:
        # fallback: click tab by role
        pass
    time.sleep(1)
    # Click Run Full Analysis (button text may differ)
    try:
        page.click('text=Run Full Analysis')
    except Exception:
        try:
            page.click('text=Run')
        except Exception:
            pass
    # Also click Refresh cached display to force the app to load persisted
    # cached results into the results-area (this triggers the server-side
    # flow that populates the DataTable). If the button isn't present the
    # click will be ignored.
    try:
        page.click('#refresh-cached')
    except Exception:
        try:
            page.click('text=Refresh cached')
        except Exception:
            pass
    # wait up to 45s for the dash_table client grid (div[role="grid"]) or
    # the results-table container to appear. We intentionally do NOT treat
    # textual brief messages as completion because those can appear earlier
    # than the client-side datatable hydration and would cause premature
    # snapshots.
    max_wait = 45
    found = False
    # First preference: wait for the client-side hydration flag if the app
    # set it via the injected script. This is the most reliable signal that
    # the DataTable inner content is ready.
    try:
        # prefer the window flag if present
        page.wait_for_function('() => !!window.__results_table_ready', timeout=45000)
        found = True
    except Exception:
        # fallback to scanning the DOM for the grid element for up to max_wait
        # also wait for the explicit DOM marker that the app now creates
        try:
            page.wait_for_selector('#results-table-ready', timeout=30000)
            found = True
        except Exception:
            for _ in range(max_wait):
                time.sleep(1)
                try:
                    if page.query_selector('div[role="grid"]') is not None:
                        found = True
                        break
                    if page.query_selector('#results-table') is not None:
                        found = True
                        break
                except Exception:
                    pass
    page.screenshot(path=os.path.join(OUT, 'trends_after_run.png'))
    # Save textual snapshot and full HTML for debugging hydration issues.
    # Try several selectors to extract meaningful textual content.
    text_content = ''
    for sel in ('#tab-content', '#results-table', '#results-table-client', '#results-table table', '#results-table-client table', 'body'):
        try:
            text_content = page.inner_text(sel)
            if text_content and len(text_content.strip()) > 0:
                break
        except Exception:
            continue
    with open(os.path.join(OUT, 'trends_after_run.txt'), 'w', encoding='utf-8') as fh:
        fh.write(text_content or '')
    try:
        html = page.content()
        with open(os.path.join(OUT, 'trends_after_run.html'), 'w', encoding='utf-8') as fh:
            fh.write(html)
    except Exception:
        pass
    # write a small debug marker whether the datatable grid was found.
    # Consider our explicit marker, the results-table host, or inner table/grid as success.
    matches = []
    try:
        if page.query_selector('div[role="grid"]') is not None:
            matches.append('role=grid')
    except Exception:
        pass
    try:
        if page.query_selector('#results-table-ready') is not None:
            matches.append('#results-table-ready')
    except Exception:
        pass
    try:
        if page.query_selector('#results-table') is not None:
            matches.append('#results-table')
    except Exception:
        pass
    try:
        if page.query_selector('.dash-spreadsheet-inner table') is not None:
            matches.append('dash-spreadsheet-inner table')
    except Exception:
        pass
    try:
        if page.query_selector('table.cell-table') is not None:
            matches.append('table.cell-table')
    except Exception:
        pass

    found_grid = len(matches) > 0
    with open(os.path.join(OUT, 'trends_after_run.debug'), 'w', encoding='utf-8') as fh:
        fh.write(f'found_grid={found_grid}\n')
        fh.write('matches=' + ','.join(matches) + '\n')
    browser.close()
print('Done')

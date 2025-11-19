def test_debug_table_inspect(page):
    """Debug helper: visit app, click Market Trends tab, and print table info."""
    BASE_URL = "http://localhost:8050"
    page.goto(BASE_URL, wait_until="domcontentloaded")
    # Click the Market Trends tab if present
    try:
        page.locator('#tab-market_trends').click()
    except Exception:
        pass
    # Give the page a moment to settle
    page.wait_for_timeout(1500)

    # Collect info about all tables on the page
    tables = page.eval_on_selector_all('table', "(nodes) => nodes.map(n => ({id: n.id || null, 'visible': !!(n.offsetWidth||n.offsetHeight), 'class': n.className || null, outer: n.outerHTML ? n.outerHTML.slice(0,200) : ''}))")
    print('\n--- DEBUG: found tables (count=%d) ---' % (len(tables)))
    for i, t in enumerate(tables[:30]):
        print(i, t)
    # Also print whether the trends container exists
    exists = page.query_selector('#trends-results-table-container') is not None
    print('\ntrends-results-table-container exists:', exists)
    # Fail so pytest prints output
    assert False, 'debug complete'

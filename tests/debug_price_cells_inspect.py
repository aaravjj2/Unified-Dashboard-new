def test_debug_price_cells(page):
    BASE_URL = "http://localhost:8050"
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    try:
        page.locator('#tab-market_trends').click()
    except Exception:
        pass
    page.wait_for_timeout(2000)

    # Get price-related td cells (current_price and last_price columns)
    cells = page.eval_on_selector_all('td[data-col="current_price"], td[data-col="last_price"]',
                                     "(nodes) => nodes.map(n => ({text: n.innerText, data_value: n.getAttribute('data-value'), outer: n.outerHTML ? n.outerHTML.slice(0,200) : ''}))")
    print('\n--- PRICE CELLS (count=%d) ---' % (len(cells)))
    for i, c in enumerate(cells[:60]):
        print(i, c)

    assert False, 'debug price cells printed'

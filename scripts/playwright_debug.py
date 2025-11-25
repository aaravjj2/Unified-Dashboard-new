from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width':1920,'height':1080})
    page.goto('http://localhost:8050')
    page.wait_for_load_state('networkidle')
    content = page.content()
    print('CONTENT-LENGTH:', len(content))
    # Check toggle existence
    exists = page.query_selector('#chatbot-toggle-btn')
    print('TOGGLE EXISTS:', bool(exists))
    if exists:
        try:
            box = exists.bounding_box()
            print('BOX:', box)
        except Exception as e:
            print('BOX-ERR', e)
        try:
            vis = exists.is_visible()
            print('IS_VISIBLE:', vis)
        except Exception as e:
            print('VIS-ERR', e)
        print('OUTER HTML SNIPPET:', exists.evaluate('e => e.outerHTML')[:400])
    # check container
    cont = page.query_selector('#chatbot-container')
    print('CONTAINER EXISTS:', bool(cont))
    if cont:
        try:
            box = cont.bounding_box()
            print('CONTAINER BOX:', box)
        except Exception as e:
            print('CONTAINER BOX ERR', e)
        try:
            vis = cont.is_visible()
            print('CONTAINER IS_VISIBLE:', vis)
        except Exception as e:
            print('CONTAINER VIS ERR', e)
        print('CONTAINER OUTER HTML SNIPPET:', cont.evaluate('e => e.outerHTML')[:400])
    browser.close()

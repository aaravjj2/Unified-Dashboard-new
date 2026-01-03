from playwright.sync_api import sync_playwright

URL = 'http://127.0.0.1:8053/'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL)
    page.wait_for_timeout(1000)
    # Try navigating to Command tab like the tests do
    try:
        page.click("text=Command")
        page.wait_for_timeout(2000)
    except Exception:
        pass
    print('data-test-id elements count:', page.eval_on_selector_all('[data-test-id]', 'els => els.length'))
    print('Has command-workspace by id:', page.eval_on_selector_all('#command-workspace', 'els => els.length'))
    # print small dump of main-workspace-tabs innerText
    try:
        tabs = page.query_selector('#main-workspace-tabs')
        if tabs:
            print('tabs innerText:', tabs.inner_text()[:200])
    except Exception as e:
        print('tabs error', e)
        try:
            outer = page.eval_on_selector('#command-workspace', 'el => el ? el.outerHTML.slice(0,500) : null')
            print('command-workspace outerHTML snippet:', outer)
        except Exception as e:
            print('command outerHTML error', e)
    # show first 200 chars of body
    print('body snippet:', page.content()[:1200])
    try:
        scripts = page.evaluate("() => Array.from(document.querySelectorAll('script')).map(s=>s.src || s.innerText.slice(0,120)).slice(0,30)")
        print('scripts (first 30):')
        for s in scripts:
            print(' -', s[:200])
    except Exception as e:
        print('scripts list error', e)
    browser.close()

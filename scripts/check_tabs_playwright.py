from playwright.sync_api import sync_playwright

URL = 'http://localhost:8050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    print(f"Loading {URL}...")
    try:
        page.goto(URL, wait_until='networkidle', timeout=20000)
    except Exception as e:
        print('Error loading page:', e)
        browser.close()
        p.stop()
        raise SystemExit(1)

    page.wait_for_selector('.nav-tabs', timeout=20000)
    # Prefer direct children of #dashboard-tabs if present
    tabs = page.query_selector_all('#dashboard-tabs .nav-item > .nav-link, #dashboard-tabs .nav-link')
    if not tabs:
        tabs = page.query_selector_all('.nav-tabs > .nav-item > .nav-link, .nav-tabs .nav-link')
    if not tabs:
        # fallback to any nav-link
        tabs = page.query_selector_all('.nav-tabs .nav-link')

    print(f"Found {len(tabs)} candidate tab elements\n")
    for i, el in enumerate(tabs):
        try:
            inner = el.inner_text().strip()
        except Exception:
            inner = None
        try:
            inner_html = el.inner_html()
        except Exception:
            inner_html = None
        try:
            outer_html = page.evaluate("(el) => el.outerHTML", el)
        except Exception:
            outer_html = None
        try:
            before = page.evaluate("(element) => { const s = window.getComputedStyle(element, '::before'); return s ? s.getPropertyValue('content') : ''; }", el)
        except Exception:
            before = None
        try:
            visible = el.is_visible()
        except Exception:
            visible = None
    print(f"Tab {i}: visible={visible}, innerText={inner!r}, ::before={before!r}")
    print(f"    innerHTML: {inner_html!r}")
    print(f"    outerHTML: {outer_html!r}\n")

    browser.close()
    p.stop()

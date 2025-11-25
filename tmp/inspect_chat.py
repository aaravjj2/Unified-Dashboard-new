from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    page.goto("http://localhost:8050")
    page.wait_for_load_state('networkidle')

    def get(sel):
        el = page.query_selector(sel)
        if el:
            try:
                html = el.evaluate("el => el.outerHTML")
            except Exception:
                html = str(el)
            print(f"--- {sel} ---\n{html[:2000]}\n")
        else:
            print(f"{sel} not found")

    get('#chatbot-toggle-btn')
    get('#chatbot-container')
    get('#chatbot-messages')
    b.close()

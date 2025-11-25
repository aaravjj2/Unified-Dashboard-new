from playwright.sync_api import sync_playwright
import os

def main():
    url = os.getenv('DASHBOARD_URL','http://localhost:8051')
    out = 'reports/market_trends_fix/diagnostics/inspect_mt_status.txt'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # initialize inspection variables so linters know they're always defined
    exists = False
    outer = ''
    hidden_attr = None
    style_attr = None
    computed = None

    with sync_playwright() as p:
        browser = None
        context = None
        try:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(viewport={'width':1280,'height':800})
            page = context.new_page()
            page.goto(url, wait_until='networkidle')

            # Click Market Trends tab
            try:
                page.locator('text=Market Trends').first.click()
            except Exception:
                pass
            page.wait_for_timeout(1000)

            # Click reload if present
            try:
                btn = page.locator('#reload-model')
                if btn.is_visible():
                    btn.click()
            except Exception:
                pass
            page.wait_for_timeout(2000)

            # Inspect element
            try:
                el = page.locator('#mt-model-status')
                exists = el.count() > 0
                outer = el.evaluate('el => el.outerHTML') if exists else ''
                hidden_attr = el.get_attribute('hidden')
                style_attr = el.get_attribute('style')
                computed = page.evaluate('''() => {
                    const el = document.querySelector('#mt-model-status');
                    if (!el) return null;
                    const cs = window.getComputedStyle(el);
                    return {display: cs.display, visibility: cs.visibility, opacity: cs.opacity};
                }''')
            except Exception:
                # keep defaults
                pass

        finally:
            # Ensure resources are always closed
            try:
                if context:
                    context.close()
            except Exception:
                pass
            try:
                if browser:
                    browser.close()
            except Exception:
                pass

    with open(out, 'w') as f:
        f.write(f"URL: {url}\n")
        f.write(f"exists: {exists}\n")
        f.write(f"outerHTML:\n{outer}\n")
        f.write(f"hidden_attr: {hidden_attr}\n")
        f.write(f"style_attr: {style_attr}\n")
        f.write(f"computed: {computed}\n")

if __name__=='__main__':
    main()

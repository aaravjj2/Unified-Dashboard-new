from playwright.sync_api import sync_playwright

from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("http://127.0.0.1:8054/")
        # Ensure the Attribution Analysis tab/pane is active before interacting
        # Try a few common selectors that activate the tab (nav link, tab button, or sidebar item)
        selectors = [
            "#attribution-tab",        # hypothetical id for the tab
            "a[data-tab='attribution']",
            "button[data-target='#attribution']",
            "#attr-run-button"
        ]

        # Attempt to click any selector that will make the run button visible
        for sel in selectors:
            try:
                el = page.query_selector(sel)
                if el is not None:
                    try:
                        el.click()
                    except Exception:
                        pass
            except Exception:
                pass

        # As a fallback, remove 'hidden' attributes/styles from the run button via JS
        page.evaluate("""
            (() => {
                const btn = document.querySelector('#attr-run-button');
                if (btn) {
                    btn.style.display = 'inline-block';
                    btn.style.visibility = 'visible';
                    btn.removeAttribute('hidden');
                }
            })();
        """)

        # Try to wait for the run button to be visible and click it.
        # If it remains hidden (common in headless/tabbed layouts), fall back to a direct JS click.
        try:
            page.wait_for_selector('#attr-run-button', timeout=5000)
            page.click('#attr-run-button')
            print('Clicked run (regular)')
        except Exception:
            # Directly invoke the button's click handler via JS as a fallback.
            clicked = page.evaluate("""
                (() => {
                    const btn = document.querySelector('#attr-run-button');
                    if (!btn) return false;
                    try { btn.click(); return true; } catch (e) { return false; }
                })();
            """)
            print('Clicked run via JS fallback:', clicked)

        # Wait for server-side processing to complete (yfinance + aggregation) before closing
        page.wait_for_timeout(35000)

        # Snapshot results container HTML (trimmed) for local inspection
        try:
            results_html = page.evaluate("""(() => {
                const el = document.querySelector('#attr-results-container');
                return el ? el.innerHTML.slice(0, 2000) : null;
            })();""")
            print('RESULTS_SNAPSHOT_PRESENT:', bool(results_html))
            if results_html:
                print(results_html)
        except Exception as e:
            print('Could not snapshot results:', e)

        browser.close()


if __name__ == '__main__':
    run()

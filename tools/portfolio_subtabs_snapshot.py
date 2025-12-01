from playwright.sync_api import sync_playwright
import os

def run():
    out_dir = 'test-artifacts'
    os.makedirs(out_dir, exist_ok=True)
    url = os.getenv('DASH_URL', 'http://127.0.0.1:8050')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print(f"Opening {url}")
        page.goto(url, wait_until='networkidle', timeout=30000)
        page.wait_for_timeout(1000)

        # Ensure Dashboard -> Portfolio is selected
        try:
            # Click the Dashboard top-level tab if needed
            portfolio_tab = page.locator('text=Portfolio')
            portfolio_tab.first.click(timeout=3000)
        except Exception as e:
            print('Could not click Portfolio tab by text:', e)

        page.wait_for_selector('#portfolio-tracker-subtabs', timeout=5000)

        # Per-tab expected selectors (more precise to capture inner content)
        subtabs = [
            ('positions', 'Positions', {'wait_for': ['#positions-datatable', '#portfolio-positions-table'], 'refresh_btn': '#portfolio-positions-refresh-btn'}),
            ('orders', 'Order History', {'wait_for': ['#portfolio-orders-table table', '#portfolio-orders-table .dash-table-container'], 'refresh_btn': None}),
            ('analytics', 'Analytics', {'wait_for': ['#portfolio-analytics-content'], 'refresh_btn': None}),
            ('factors', 'Factor Exposure', {'wait_for': ['#portfolio-factor-exposure-content'], 'refresh_btn': None}),
            ('optimization', 'Optimization', {'wait_for': ['#opt-tickers-input', '#opt-results-container'], 'refresh_btn': '#opt-run-btn'})
        ]

        # capture initial portfolio value
        try:
            pv = page.locator('#portfolio-value').inner_text()
        except Exception:
            pv = '<missing>'
        print('Initial #portfolio-value:', pv)

        for tab_id, tab_label, wait_sel in subtabs:
            print('\n---')
            print(f'Clicking subtab: {tab_label}')
            try:
                # Ensure a tab change actually occurs: click a different sibling tab first
                # so that callbacks with prevent_initial_call=True will fire when we
                # click the target tab.
                sibling_clicked = False
                try:
                    all_tabs = page.locator('#portfolio-tracker-subtabs button')
                    for i in range(all_tabs.count()):
                        txt = all_tabs.nth(i).inner_text().strip()
                        if txt and txt.lower() != tab_label.lower():
                            try:
                                all_tabs.nth(i).click()
                                sibling_clicked = True
                                break
                            except Exception:
                                continue
                except Exception:
                    sibling_clicked = False

                # Now click the desired tab
                tab_locator = page.locator(f"#portfolio-tracker-subtabs button:has-text(\"{tab_label}\")")
                if not tab_locator.count():
                    tab_locator = page.locator(f"text= {tab_label}")
                tab_locator.first.click(timeout=3000)
            except Exception as e:
                print(f'  Failed to click tab {tab_label}:', e)

            # wait for an expected selector or short delay
            # Try to wait for any of the expected selectors; if none appear, optionally click a refresh button
            waited = False
            expect = wait_sel['wait_for'] if isinstance(wait_sel, dict) else [wait_sel]
            for sel in expect:
                try:
                    page.wait_for_selector(sel, timeout=8000)
                    print('  Found expected selector:', sel)
                    waited = True
                    break
                except Exception:
                    continue

            if not waited:
                # If a refresh button is provided, click it and wait again briefly
                refresh_btn = wait_sel.get('refresh_btn') if isinstance(wait_sel, dict) else None
                if refresh_btn:
                    try:
                        print('  Attempting to click refresh button to populate tab content:', refresh_btn)
                        page.locator(refresh_btn).first.click(timeout=2000)
                        # wait for datatable or content after refresh
                        for sel in expect:
                            try:
                                page.wait_for_selector(sel, timeout=8000)
                                print('  Found expected selector after refresh:', sel)
                                waited = True
                                break
                            except Exception:
                                continue
                    except Exception as e:
                        print('  Failed to click refresh button or no button:', e)

            if not waited:
                print('  Expected selector not found (selector may be missing or content empty):', expect)

            # print a few tracked values
            try:
                pv = page.locator('#portfolio-value').inner_text()
            except Exception:
                pv = '<missing>'
            print('  #portfolio-value after click:', pv)

            # screenshot
            path = os.path.join(out_dir, f'portfolio_subtab_{tab_id}.png')
            try:
                # try to screenshot the main container for the tab
                container = page.locator('#portfolio-tracker-subtabs')
                if container.count():
                    container.screenshot(path=path)
                else:
                    page.screenshot(path=path, full_page=True)
                print('  Screenshot saved to', path)
            except Exception as e:
                print('  Failed to capture screenshot:', e)

            page.wait_for_timeout(500)

        browser.close()

if __name__ == '__main__':
    run()

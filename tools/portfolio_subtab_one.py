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
        page.goto(url, timeout=15000)
        page.wait_for_timeout(1000)

        # Click Portfolio top-level tab
        try:
            portfolio_tab = page.locator('text=Portfolio')
            portfolio_tab.first.click(timeout=3000)
        except Exception as e:
            print('Could not click Portfolio tab by text:', e)

        page.wait_for_selector('#portfolio-tracker-subtabs', timeout=5000)

        # Click only Positions subtab
        tab_label = 'Positions'
        wait_sel = '#portfolio-positions-table'
        print('\n---')
        print(f'Clicking subtab: {tab_label}')
        try:
            tab_locator = page.locator(f"#portfolio-tracker-subtabs button:has-text(\"{tab_label}\")")
            if not tab_locator.count():
                tab_locator = page.locator(f"text= {tab_label}")
            tab_locator.first.click(timeout=3000)
        except Exception as e:
            print(f'  Failed to click tab {tab_label}:', e)

        try:
            page.wait_for_selector(wait_sel, timeout=3000)
            print('  Found expected selector:', wait_sel)
        except Exception:
            print('  Expected selector not found:', wait_sel)

        try:
            pv = page.locator('#portfolio-value').inner_text()
        except Exception:
            pv = '<missing>'
        print('  #portfolio-value after click:', pv)

        path = os.path.join(out_dir, 'portfolio_subtab_positions_one.png')
        try:
            container = page.locator('#portfolio-tracker-subtabs')
            if container.count():
                container.screenshot(path=path)
            else:
                page.screenshot(path=path, full_page=True)
            print('  Screenshot saved to', path)
        except Exception as e:
            print('  Failed to capture screenshot:', e)

        browser.close()

if __name__ == '__main__':
    run()

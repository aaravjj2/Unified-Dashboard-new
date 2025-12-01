from playwright.sync_api import sync_playwright
import time
import json

# Headless adaptation of test_chain_via_callback.py

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("Loading dashboard...")
        page.goto('http://localhost:8050', wait_until='networkidle', timeout=60000)
        time.sleep(1)

        print("Clicking Options Lab tab...")
        try:
            page.click('#tab-options_lab', timeout=5000)
        except Exception as e:
            print('Could not click options tab:', e)
        time.sleep(0.5)

        print("Entering ticker SPY...")
        try:
            page.fill('#options-ticker-input', 'SPY', timeout=3000)
        except Exception as e:
            print('Could not fill ticker input:', e)
        time.sleep(0.25)

        print("Clicking Load Chain button...")
        try:
            page.click('#options-load-btn', timeout=5000)
        except Exception as e:
            print('Could not click load button:', e)
        time.sleep(2)

        # Save screenshot
        screenshot_path = 'reports/picks/playwright/chain_headless.png'
        page.screenshot(path=screenshot_path, full_page=True)
        print('Screenshot saved to', screenshot_path)

        # Check status message
        try:
            status = page.locator('#options-status-message').inner_text(timeout=3000)
            print('Status message:', status)
        except Exception as e:
            print('Could not read status message:', e)

        # Try to read Dash stores
        try:
            store_data = page.evaluate('''
                () => {
                    if (window.dash && window.dash._dashprivate) {
                        const stores = window.dash._dashprivate.stores || {};
                        return { keys: Object.keys(stores) };
                    }
                    return { keys: [] };
                }
            ''')
            print('Window.dash stores keys:', json.dumps(store_data))
        except Exception as e:
            print('Could not evaluate window.dash:', e)

        # Click Greeks tab and check graphs
        try:
            page.click('#options-greeks-tab', timeout=5000)
            time.sleep(1)
        except Exception as e:
            print('Could not click greeks tab:', e)

        graphs = ['greeks-delta-chart', 'greeks-gamma-chart', 'greeks-theta-chart', 'greeks-vega-chart']
        for g in graphs:
            try:
                result = page.evaluate(f"() => {{ const el=document.getElementById('{g}'); return !!el; }}")
                print(f'{g}: exists={result}')
            except Exception as e:
                print(f'{g}: error {e}')

        browser.close()

if __name__ == '__main__':
    run()

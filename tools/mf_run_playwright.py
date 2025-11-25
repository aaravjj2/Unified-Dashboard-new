from playwright.sync_api import sync_playwright
import time
import json
import os
from pathlib import Path

BASE_URL = os.environ.get('BASE_URL', 'http://localhost:8050')
OUT_DIR = Path(os.environ.get('OUT_DIR', 'reports/market_forecast_playwright'))
OUT_DIR.mkdir(parents=True, exist_ok=True)

SCREENSHOT = OUT_DIR / 'mf_after_run.png'
STORE_JSON = OUT_DIR / 'mf_forecast_store.json'


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1400, 'height': 900})
        page = context.new_page()
        page.goto(BASE_URL, wait_until='networkidle', timeout=30000)

        # Click the Market Forecast tab
        page.click('#tab-market_forecast', timeout=10000)
        page.wait_for_selector('#mf-run-btn', timeout=10000)

        # Click run
        page.click('#mf-run-btn')

        # Wait for the forecast store to be updated (poll)
        store_selector = '#mf-forecast-store'
        # Dash stores are not visible elements; retrieve via window.dash_clientside or DOM
        # We'll poll using page.evaluate to access window.dash_clientside or stores
        def get_store():
            try:
                return page.evaluate("() => { const s = window.dash_clientside && window.dash_clientside._dashprivate_clientside_funcs; return null }")
            except Exception:
                return None

        # Instead, attempt to read the store element's textContent if present in DOM
        # Poll for a JSON string inside the page that includes 'forecast_id'
        store_value = None
        timeout = 25
        elapsed = 0
        while elapsed < timeout:
            try:
                # Many Dash apps render dcc.Store as a div[data-dash-is-loading] or hidden input; try reading text from element
                res = page.evaluate("() => { const el = document.getElementById('mf-forecast-store'); if (!el) return null; return el.textContent || el.innerText || null }")
                if res:
                    try:
                        parsed = json.loads(res)
                        store_value = parsed
                        break
                    except Exception:
                        # Might be string or other, try to parse loosely
                        try:
                            store_value = json.loads(JSON.stringify(res))
                        except Exception:
                            store_value = res
                            break
            except Exception:
                pass
            time.sleep(1)
            elapsed += 1

        # Take screenshot regardless
        page.screenshot(path=str(SCREENSHOT), full_page=True)

        # Save store
        with open(STORE_JSON, 'w') as f:
            json.dump({'store': store_value}, f, default=str, indent=2)

        browser.close()
        print('Saved screenshot to', SCREENSHOT)
        print('Saved store to', STORE_JSON)


if __name__ == '__main__':
    run()

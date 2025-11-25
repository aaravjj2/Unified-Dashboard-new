# Playwright clicker test for Market Forecast tab
# Saves a screenshot and logs basic DOM info.

import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

DASH_URL = os.environ.get('DASH_URL', 'http://127.0.0.1:8050')
OUT_DIR = Path(os.environ.get('TEST_ARTIFACTS_DIR', 'test-artifacts'))
DEBUG_DIR = OUT_DIR / 'market_forecast_debug'
DEBUG_DIR.mkdir(parents=True, exist_ok=True)


def _save_console_and_errors(page, out_dir: Path):
    # collect console messages and page inner text
    try:
        console_log = page.context.console_messages if hasattr(page.context, 'console_messages') else []
    except Exception:
        console_log = []
    # fallback: fetch console via evaluate hook
    try:
        logs = page.evaluate('window._captured_console || []')
    except Exception:
        logs = []

    with open(out_dir / 'page_text.txt', 'w', encoding='utf-8') as f:
        try:
            f.write(page.content())
        except Exception as e:
            f.write(f'error reading page.content(): {e}')

    with open(out_dir / 'console_logs.txt', 'w', encoding='utf-8') as f:
        for l in logs:
            f.write(str(l) + "\n")


def test_click_market_forecast():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # inject console capture array so evaluate can return it later if needed
        page.add_init_script("window._captured_console = []; ['log','warn','error','info'].forEach(function(k){ var o=console[k]; console[k]=function(){ window._captured_console.push([k, Array.from(arguments).map(String).join(' ')].join(': ')); o.apply(console, arguments); } })")

        console_messages = []

        def _on_console(msg):
            try:
                console_messages.append(f"[{msg.type}] {msg.text}")
            except Exception:
                console_messages.append(repr(msg))

        page.on('console', _on_console)

        print(f"Opening {DASH_URL}")
        page.goto(DASH_URL, timeout=120000)
        time.sleep(1)

        # find nav items
        items = page.query_selector_all('.nav-item, .tab, .nav-link')
        print('nav candidates count', len(items))

        # attempt to click an element with visible text 'Market Forecast' (case-insensitive)
        target = None
        for el in items:
            try:
                text = el.inner_text().strip()
            except Exception:
                text = ''
            if text and 'market forecast' in text.lower():
                target = el
                break

        if not target:
            # fallback: query by exact anchor text
            anchors = page.query_selector_all('a, button, .tab')
            for a in anchors:
                try:
                    t = a.inner_text().strip()
                except Exception:
                    t = ''
                if t and 'market forecast' in t.lower():
                    target = a
                    break

        assert target, 'Could not find Market Forecast tab in nav; inspect page structure.'

        clicked_text = ''
        try:
            clicked_text = target.inner_text()
        except Exception:
            clicked_text = '<unreadable text>'

        print('Clicking target with text:', clicked_text)
        target.click()
        time.sleep(1)

        # capture page content and console
        page_path = DEBUG_DIR / 'market_forecast_click.png'
        page.screenshot(path=str(page_path), full_page=True)
        print('Saved screenshot to', page_path)

        # write console messages
        with open(DEBUG_DIR / 'console_messages.txt', 'w', encoding='utf-8') as f:
            for m in console_messages:
                f.write(m + '\n')

        # save page content and evaluate for known error text
        page_html = page.content()
        with open(DEBUG_DIR / 'page_content.html', 'w', encoding='utf-8') as f:
            f.write(page_html)

        # look for known error patterns
        error_indicators = ['Error loading Market Forecast', 'received an unexpected keyword argument', 'Traceback', 'Exception']
        found_error = None
        for e in error_indicators:
            if e in page_html:
                found_error = e
                break

        if found_error:
            print('Detected error indicator in page:', found_error)
            # save extra diagnostics
            _save_console_and_errors(page, DEBUG_DIR)
            browser.close()
            raise AssertionError(f'Forecast page contains error marker: {found_error}. See {DEBUG_DIR} for artifacts.')

        # also assert forecast-specific controls exist
        expected_selectors = ['#forecast-pane', '#mf-run', '#mf-tickers', "text='Run Forecast'", "text=Market Forecast"]
        present = False
        for sel in expected_selectors:
            try:
                if page.query_selector(sel):
                    present = True
                    break
            except Exception:
                continue

        if not present:
            _save_console_and_errors(page, DEBUG_DIR)
            browser.close()
            raise AssertionError(f'Forecast UI controls not found; see {DEBUG_DIR} for page dump and console logs')

        browser.close()

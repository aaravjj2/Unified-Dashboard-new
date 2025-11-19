from playwright.sync_api import sync_playwright
import traceback
import pathlib


def test_volatility_playwright_snapshot():
    """Use Playwright to load the Volatility Lab page and assert client-rendered DOM.

    This test intentionally waits longer and dumps the page content to
    /tmp/vol_playwright_debug.html on failure to aid debugging.
    """
    url = "http://127.0.0.1:8050/"
    debug_path = pathlib.Path('/tmp/vol_playwright_debug.html')
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # capture console messages to help debugging
        console_messages = []
        page.on('console', lambda msg: console_messages.append((msg.type, msg.text)))
        page.on('pageerror', lambda exc: console_messages.append(('pageerror', str(exc))))
        try:
            page.goto(url, timeout=60000)
            # Wait for the VIX graph element which is rendered client-side
            page.wait_for_selector('#vix-chart', timeout=60000)
            content = page.content().lower()
            assert 'vix-chart' in content, "vix-chart not present in DOM"
            assert 'undefined' not in content, "Found 'undefined' in page content"
        except Exception as e:
            # Dump page content and console for diagnosis
            try:
                debug_path.write_text(page.content())
            except Exception:
                pass
            print("Playwright debug: exception while waiting for #vix-chart:\n", traceback.format_exc())
            print("Console messages (most recent first):")
            for t, text in console_messages[-20:]:
                print(t, text)
            raise
        finally:
            browser.close()

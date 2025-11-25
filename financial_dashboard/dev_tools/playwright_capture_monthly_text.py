from playwright.sync_api import sync_playwright
import time
import os

URL = os.environ.get('MARKET_DASH_URL', 'http://127.0.0.1:8050')
OUT = os.path.join(os.path.dirname(__file__), 'monthly_tab_text.txt')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL, timeout=60000)
    # wait for tabs
    try:
        page.wait_for_selector('div#tabs', timeout=15000)
    except Exception:
        pass
    # click the Monthly Picks tab by visible text
    try:
        page.click("text=Monthly Picks", timeout=5000)
    except Exception:
        pass
    # wait for content to render
    try:
        page.wait_for_function("() => !!document.querySelector('#tab-content') && document.querySelector('#tab-content').innerText.length > 20", timeout=10000)
    except Exception:
        pass
    time.sleep(1)
    try:
        content = page.eval_on_selector('#tab-content', 'el => el.innerText')
    except Exception:
        try:
            content = page.content()
        except Exception:
            content = ''
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write(content)
        print('Wrote Monthly tab text to', OUT)
    except Exception as e:
        print('Failed to write output:', e)
    browser.close()

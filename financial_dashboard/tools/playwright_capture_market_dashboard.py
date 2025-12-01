from playwright.sync_api import sync_playwright
import time

OUT = '/tmp/market_dashboard_monthly.png'
URL = 'http://127.0.0.1:8501/'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL)
    # click the tab labeled 'Monthly Picks'
    try:
        page.click("text=Monthly Picks", timeout=5000)
    except Exception:
        pass
    # wait for the server-side header used in fallback
    try:
        page.wait_for_selector('text=Monthly Picks — latest', timeout=10000)
    except Exception:
        # fallback: wait for the generic H3 inside the tab
        try:
            page.wait_for_selector('h3:has-text("Monthly Picks")', timeout=5000)
        except Exception:
            pass
    time.sleep(1)
    # take full page screenshot
    page.screenshot(path=OUT, full_page=True)
    print('Saved screenshot to', OUT)
    browser.close()

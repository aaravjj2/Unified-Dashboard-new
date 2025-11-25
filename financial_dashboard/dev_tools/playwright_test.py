from playwright.sync_api import sync_playwright
import time

OUT_PATH = r"C:\Aarav\fin_env\Dash\forecast_dash_screenshot.png"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://127.0.0.1:8052', timeout=30000)
    # click the backtest refresh button if present to populate outputs
    try:
        btn = page.query_selector("#mf-backtest-refresh")
        if btn:
            btn.click()
            time.sleep(1)
    except Exception:
        pass
    time.sleep(1)
    page.screenshot(path=OUT_PATH, full_page=True)
    print('screenshot saved to', OUT_PATH)
    browser.close()

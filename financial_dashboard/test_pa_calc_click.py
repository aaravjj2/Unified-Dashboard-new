from playwright.sync_api import sync_playwright, expect
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    page = browser.new_page()
    page.goto('http://localhost:8054', timeout=60000)
    page.wait_for_load_state('networkidle')
    time.sleep(1)

    # Ensure we're on Portfolio Analytics subtab
    try:
        page.locator('a:has-text("Portfolio Analytics")').first.click()
        time.sleep(1)
    except Exception:
        pass

    # Read current total return value
    total_return_el = page.locator('#pa-total-return')
    print('Before:', total_return_el.inner_text())

    # Click Calculate Analytics
    calc_btn = page.locator('button#pa-calc-btn')
    print('calc_btn exists:', calc_btn.count())
    try:
        print('calc_btn visible:', calc_btn.is_visible())
    except Exception as e:
        print('is_visible failed:', e)
    try:
        print('calc_btn enabled:', calc_btn.is_enabled())
    except Exception as e:
        print('is_enabled failed:', e)
    calc_btn.click()
    time.sleep(4)

    # Read the total return after clicking
    try:
        print('After:', total_return_el.inner_text())
    except Exception as e:
        print('After read failed:', e)

    page.screenshot(path='pa_calc_click.png', full_page=True)
    browser.close()

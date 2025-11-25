from playwright.sync_api import sync_playwright
import os
import time

URL = os.getenv('DASHBOARD_URL', 'http://127.0.0.1:8050')
OUT = 'reports/console_capture.log'

os.makedirs('reports', exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    logs = []

    def on_console(msg):
        try:
            logs.append(f"CONSOLE [{msg.type}] {msg.text}\n")
        except Exception as e:
            logs.append(f"CONSOLE [error] could not read message: {e}\n")

    page.on('console', on_console)
    page.on('pageerror', lambda e: logs.append(f"PAGE ERROR: {e}\n"))

    print(f"Opening {URL}")
    page.goto(URL)
    time.sleep(2)

    # Try to click market trends tab and reload button if present
    try:
        # open Market Trends tab if a tab exists
        page.click('#tab-market-trends', timeout=2000)
    except Exception:
        pass

    try:
        page.click('#reload-model', timeout=2000)
    except Exception:
        pass

    # Wait for console messages for a short period
    time.sleep(6)

    with open(OUT, 'w') as f:
        f.writelines(logs)

    print(f"Wrote {len(logs)} console entries to {OUT}")
    browser.close()

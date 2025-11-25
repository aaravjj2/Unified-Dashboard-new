from playwright.sync_api import sync_playwright
import time
import os

OUT = os.path.join(os.path.dirname(__file__), 'playwright_snapshots')
os.makedirs(OUT, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page()

    console_lines = []
    def on_console(msg):
        try:
            console_lines.append(f"{msg.type}: {msg.text}")
        except Exception:
            console_lines.append(f"console: (could not serialize)")
    page.on('console', on_console)

    page.goto('http://127.0.0.1:8050/', timeout=60000, wait_until='load')
    time.sleep(1)

    # find tab labels
    labels = ['Market Trends', 'Market Forecast', 'Monthly Picks', 'Market Trends Rebuild', 'Weekly Picks']
    for lbl in labels:
        try:
            page.click(f'text={lbl}', timeout=5000)
        except Exception:
            # try clicking via role/tab
            try:
                els = page.query_selector_all('div[role="tab"]')
                for el in els:
                    try:
                        if lbl.lower() in el.inner_text().lower():
                            el.click()
                            break
                    except Exception:
                        continue
            except Exception:
                pass

        # Wait up to 10s for the client to set a deterministic '#tab-ready' marker
        captured_html = ''
        try:
            page.wait_for_selector('#tab-ready', timeout=10000)
            # prefer inner_html of tab-content after marker appears
            try:
                captured_html = page.inner_html('#tab-content')
            except Exception:
                captured_html = page.content()
        except Exception:
            # fallback to previous heuristic wait (short)
            timeout_s = 3
            poll_interval = 0.5
            waited = 0.0
            while waited < timeout_s:
                try:
                    captured_html = page.inner_html('#tab-content')
                except Exception:
                    try:
                        captured_html = page.content()
                    except Exception:
                        captured_html = ''
                if captured_html and any(x in captured_html for x in ['<table', '<svg', 'class="dataframe"']):
                    break
                if len(page.locator('#tab-content').inner_text().strip()) > 5:
                    break
                time.sleep(poll_interval)
                waited += poll_interval

        # capture tab-content html and a screenshot (fallbacks handled above)
        fn = os.path.join(OUT, f'tab_{lbl.replace(" ","_")}.html')
        try:
            with open(fn, 'w', encoding='utf-8') as fh:
                fh.write(captured_html)
        except Exception:
            try:
                with open(fn, 'w', encoding='utf-8') as fh:
                    fh.write(page.content())
            except Exception:
                pass
        try:
            page.screenshot(path=os.path.join(OUT, f'tab_{lbl.replace(" ","_")}.png'))
        except Exception:
            pass

    # write console
    with open(os.path.join(OUT, 'console.log'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(console_lines))

    browser.close()
print('done')

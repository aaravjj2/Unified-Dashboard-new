from playwright.sync_api import sync_playwright
import time
import os

OUT_DIR = '/tmp/market_trends_run'
URL = 'http://127.0.0.1:8050/'

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)

def main(headed=True):
    ensure_dir(OUT_DIR)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        context = browser.new_context(viewport={'width': 1400, 'height': 900})
        page = context.new_page()
        page.on('console', lambda msg: print('BROWSER CONSOLE:', msg.type, msg.text))
        try:
            page.goto(URL, timeout=20000)
        except Exception as e:
            print('ERROR: Could not navigate to', URL, e)
            browser.close()
            return 2

        # Click Market Trends tab
        clicked = False
        for sel in ["text=Market Trends", "#tabs >> text=Market Trends", ".nav-link:has-text('Market Trends')"]:
            try:
                page.click(sel, timeout=3000)
                clicked = True
                break
            except Exception:
                continue

        time.sleep(1)
        page.screenshot(path=os.path.join(OUT_DIR, 'before_run.png'), full_page=True)

        try:
            page.click('#run-btn', timeout=5000)
            print('Clicked run')
        except Exception as e:
            print('Could not click run:', e)
            page.screenshot(path=os.path.join(OUT_DIR, 'run_click_failed.png'), full_page=True)
            browser.close()
            return 2

        # poll status
        status_text = ''
        for i in range(30):
            time.sleep(1)
            try:
                status = page.query_selector('#status')
                if status:
                    status_text = status.inner_text().strip()
                    print('Status:', status_text)
                    if 'completed' in status_text.lower() or 'failed' in status_text.lower():
                        break
            except Exception:
                pass

        page.screenshot(path=os.path.join(OUT_DIR, 'after_run.png'), full_page=True)
        # save results area HTML
        try:
            ra = page.query_selector('#results-area')
            if ra:
                html = ra.inner_html()
                with open(os.path.join(OUT_DIR, 'results_area.html'), 'w', encoding='utf-8') as f:
                    f.write(html)
        except Exception:
            pass

        with open(os.path.join(OUT_DIR, 'status.txt'), 'w', encoding='utf-8') as f:
            f.write(status_text or '')

        browser.close()
    return 0


if __name__ == '__main__':
    import sys
    headed = True
    if '--headless' in sys.argv:
        headed = False
    raise SystemExit(main(headed=headed))

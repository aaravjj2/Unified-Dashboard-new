from playwright.sync_api import sync_playwright
import os

OUT_DIR = '/tmp/market_tabs'
URL = 'http://127.0.0.1:8050/'

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)

def main():
    ensure_dir(OUT_DIR)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(URL, timeout=15000)
        except Exception as e:
            print('ERROR: Could not navigate to', URL, '-', e)
            browser.close()
            return 2

        tabs = ['Market Trends', 'Market Forecast', 'Monthly Picks', 'Weekly Picks', 'Daily Picks']
        for t in tabs:
            try:
                # Try several ways to click the tab text
                selectors = [f'text="{t}"', f'#tabs >> text={t}', f'.nav-link:has-text("{t}")']
                clicked = False
                for sel in selectors:
                    try:
                        page.click(sel, timeout=3000)
                        clicked = True
                        break
                    except Exception:
                        continue

                # Wait briefly for content
                page.wait_for_timeout(1000)
                fname = os.path.join(OUT_DIR, t.replace(' ', '_') + '.png')
                page.screenshot(path=fname, full_page=True)
                print('Saved', fname, 'clicked=', clicked)
            except Exception as e:
                print('Error capturing tab', t, e)

        browser.close()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

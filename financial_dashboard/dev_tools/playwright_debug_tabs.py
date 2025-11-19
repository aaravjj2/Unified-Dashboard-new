from playwright.sync_api import sync_playwright
import os, time

URL = os.environ.get('MARKET_DASH_URL', 'http://127.0.0.1:8050')

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1200, 'height': 900})
        # log console
        def on_console(msg):
            try:
                loc = msg.location or {}
            except Exception:
                loc = {}
            print('CONSOLE:', msg.type, repr(msg.text), 'location=', loc)
        page.on('console', on_console)
        # log requests to see _dash-update-component
        def on_request(req):
            url = req.url
            if '_dash-update-component' in url:
                print('REQUEST:', req.method, url)
        page.on('request', on_request)
        page.goto(URL, timeout=60000)
        # fetch the dependency map as the client sees it
        try:
            client_deps = page.evaluate("() => fetch('/_dash-dependencies').then(r => r.json())")
            print('CLIENT _dash-dependencies entries:', len(client_deps))
            try:
                from collections import Counter
                outs = []
                idx_map = {}
                for i, cb in enumerate(client_deps):
                    # cb is a JS object converted to Python dict
                    outs_list = cb.get('outputs') or cb.get('outputs', [])
                    for o in outs_list:
                        oid = o.get('id') if isinstance(o, dict) else None
                        prop = o.get('property') if isinstance(o, dict) else None
                        key = f"{oid}.{prop}"
                        outs.append(key)
                        idx_map.setdefault(key, []).append(i)
                dup = {k:v for k,v in Counter(outs).items() if v>1}
                print('CLIENT duplicate outputs (client-side):', dup)
                for k, v in dup.items():
                    print(' ->', k, 'callback indices:', idx_map.get(k))
            except Exception as e:
                print('Error parsing client deps:', e)
        except Exception as e:
            print('failed to fetch client deps:', e)
        time.sleep(1)
        tabs = ['Market Trends', 'Market Forecast', 'Monthly Picks', 'Market Trends Rebuild', 'Weekly Picks']
        for t in tabs:
            try:
                print('\n--- Clicking tab:', t)
                page.click(f"text={t}")
            except Exception as e:
                print('Click failed:', e)
            # wait up to 8s for #tab-ready
            try:
                page.wait_for_selector('#tab-ready', timeout=8000)
                print('#tab-ready present:', page.query_selector('#tab-ready').inner_text())
            except Exception:
                print('#tab-ready not present after wait')
            # dump a short outerHTML snippet for diagnosis
            try:
                outer = page.eval_on_selector('#tab-content', 'el => el.outerHTML') or ''
            except Exception:
                outer = ''
            print('tab-content outerHTML snippet:', (outer or '')[:800].replace('\n',' '))
            try:
                txt = page.eval_on_selector('#tab-content', 'el => el.innerText')
            except Exception:
                txt = ''
            print('tab-content length:', len((txt or '').strip()))
            # small pause between clicks
            time.sleep(0.5)
        browser.close()

if __name__ == '__main__':
    run()

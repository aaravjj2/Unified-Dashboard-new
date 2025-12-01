from playwright.sync_api import sync_playwright
import os, json

OUTDIR = os.path.join('test-artifacts', 'diag_nav_overlay')
os.makedirs(OUTDIR, exist_ok=True)

def run_capture():
    records = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        def on_console(msg):
            try:
                records.append({'type': msg.type, 'text': msg.text, 'args': [a.to_string() for a in msg.args]})
            except Exception:
                records.append({'type': msg.type, 'text': msg.text})

        page.on('console', on_console)
        page.goto('http://localhost:8050', wait_until='load')
        try:
            page.wait_for_selector('#dashboard-tabs', timeout=15000)
        except Exception:
            pass

        path = os.path.join(OUTDIR, 'console.json')
        with open(path, 'w') as f:
            json.dump(records, f, indent=2)
        print('Wrote', path)
        browser.close()

if __name__ == '__main__':
    run_capture()

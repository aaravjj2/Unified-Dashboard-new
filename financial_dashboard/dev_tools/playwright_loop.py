from playwright.sync_api import sync_playwright
import time
import json
import os

OUT_CONSOLE = r"c:\Aarav\fin_env\Dash\playwright_loop_console.json"
OUT_CORRELATE = r"c:\Aarav\fin_env\Dash\playwright_loop_correlate.txt"
SERVER_DEBUG = r"c:\Aarav\fin_env\market_forecast_debug.log"
SERVER_REQS = r"c:\Aarav\fin_env\market_dashboard_requests.log"


def read_server_logs():
    logs = {'debug': [], 'reqs': []}
    try:
        if os.path.exists(SERVER_DEBUG):
            with open(SERVER_DEBUG, 'r', encoding='utf-8') as f:
                logs['debug'] = [l.strip() for l in f.readlines() if l.strip()]
    except Exception:
        pass
    try:
        if os.path.exists(SERVER_REQS):
            with open(SERVER_REQS, 'r', encoding='utf-8') as f:
                logs['reqs'] = [l.strip() for l in f.readlines() if l.strip()]
    except Exception:
        pass
    return logs


def main():
    entries = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def on_console(msg):
            ts = time.time()
            try:
                text = msg.text
            except Exception:
                text = '<unserializable>'
            entries.append({'ts': ts, 'type': msg.type, 'text': text})

        page.on('console', on_console)
        page.goto('http://127.0.0.1:8051', timeout=20000)
        time.sleep(0.5)

        # Click the Forecast tab
        try:
            tab = page.query_selector('text=Market Forecast')
            if tab:
                tab.click()
                time.sleep(0.5)
        except Exception:
            pass

        # Try running a ping to ensure callbacks fire
        try:
            ping = page.query_selector('#mf-ping')
            if ping:
                ping.click()
                time.sleep(0.6)
        except Exception:
            pass

        # Try to click run forecast (best effort)
        try:
            run_btn = page.query_selector('#mf-run')
            if run_btn:
                run_btn.click()
                time.sleep(0.6)
        except Exception:
            pass

        # Click backtest refresh if present
        try:
            refresh = page.query_selector('#mf-backtest-refresh')
            if refresh:
                refresh.click()
                time.sleep(0.6)
        except Exception:
            pass

        # wait 2 seconds to capture console spams
        time.sleep(2)
        browser.close()

    # save console entries
    try:
        with open(OUT_CONSOLE, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2)
    except Exception:
        pass

    # correlate any 'Object' logs with server logs around timestamps
    logs = read_server_logs()
    correl = []
    for e in entries:
        if e['text'] == 'Object' or e['text'].strip() == 'Object':
            t = e['ts']
            window = []
            for l in logs.get('debug', []):
                try:
                    ts = float(l.split()[0])
                    if abs(ts - t) < 5:
                        window.append(l)
                except Exception:
                    continue
            for l in logs.get('reqs', []):
                try:
                    parts = l.split()
                    if parts:
                        ts = float(parts[0])
                        if abs(ts - t) < 5:
                            window.append(l)
                except Exception:
                    continue
            correl.append({'console': e, 'nearby_server': window})

    try:
        with open(OUT_CORRELATE, 'w', encoding='utf-8') as f:
            f.write('Console entries:\n')
            json.dump(entries, f, indent=2)
            f.write('\n\nCorrelations:\n')
            json.dump(correl, f, indent=2)
    except Exception:
        pass

    print('Done. console:', OUT_CONSOLE, 'correl:', OUT_CORRELATE)


if __name__ == "__main__":
    main()

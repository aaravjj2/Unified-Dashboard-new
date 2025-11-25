#!/usr/bin/env python3
"""
Playwright test: Select NVDA in Market Forecast and run forecast
Saves screenshot and DOM for inspection.
"""
from pathlib import Path
import time
import sys
from datetime import datetime
import os

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "reports" / "systemfix" / "playwright"
DOM_DIR = REPO / "reports" / "systemfix" / "dom"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DOM_DIR.mkdir(parents=True, exist_ok=True)

from playwright.sync_api import sync_playwright
import json

PORT = os.environ.get('PORT', '8050')
URL = f"http://localhost:{PORT}"

def run(headless=True, timeout=120000):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()
        try:
            page.goto(URL, wait_until="networkidle", timeout=timeout)
            # navigate to Market Forecast tab
            mf_tab = page.locator("a.nav-link:has-text('Market Forecast')")
            if mf_tab.count() == 0:
                print("Market Forecast tab not found")
                return 2
            mf_tab.first.click()
            page.wait_for_timeout(1500)

            # open ticker dropdown
            ticker = page.locator("#mf-ticker-input")
            if ticker.count() == 0:
                # try fallback: dcc dropdown renders input inside div
                page.locator("div[role='listbox']").first.click()
            else:
                try:
                    ticker.first.click()
                except Exception:
                    page.locator("div[role='listbox']").first.click()
            page.wait_for_timeout(700)

            # choose NVDA option
            opt = page.locator("div[role='option']:has-text('NVDA')")
            if opt.count() > 0:
                opt.first.click()
                print("Selected NVDA option")
            else:
                print("NVDA option not visible - trying to type into dropdown input")
                # try typing
                try:
                    inp = page.locator("#mf-ticker-input input")
                    inp.fill('NVDA')
                    page.wait_for_timeout(300)
                    sel = page.locator("div[role='option']:has-text('NVDA')")
                    if sel.count() > 0:
                        sel.first.click()
                        print("Selected NVDA via typing")
                except Exception:
                    print("Could not select NVDA option - proceeding to click Run (may use current ticker)")

            # Click Run Forecast button (try several possible ids/labels)
            run_candidates = ['#mf-generate-btn', '#mf-run-btn', "button:has-text('Run Forecast')", "button:has-text('Generate Forecast')"]
            clicked = False
            for sel in run_candidates:
                try:
                    el = page.locator(sel)
                    if el.count() > 0:
                        el.first.click()
                        print(f"Clicked run button: {sel}")
                        clicked = True
                        break
                except Exception:
                    continue
            if not clicked:
                print("Run Forecast button not found")

            # wait for server to process and for the client store mirror to update
            page.wait_for_timeout(2500)

            # Attempt to read the client-side store mirror for authoritative result
            try:
                store = page.evaluate("""
                    () => {
                        try {
                            if (window.__mf_forecast_store__) return window.__mf_forecast_store__;
                        } catch(e){}
                        try {
                            const dbg = document.getElementById('mf-store-debug');
                            if (dbg) {
                                const txt = dbg.textContent || dbg.innerText || '';
                                try { return JSON.parse(txt); } catch(e) { return txt || null; }
                            }
                        } catch(e){}
                        return null;
                    }
                """)
                if store:
                    sf = OUT_DIR / f"mf_forecast_store_{int(time.time())}.json"
                    sf.write_text(json.dumps(store, indent=2))
                    print("Saved mf-forecast-store mirror:", sf)
                else:
                    print("No mf-forecast-store found on client")
            except Exception as e:
                print("Error reading mf-forecast-store:", e)

            # Save screenshot and DOM
            ts = int(time.time())
            ss = OUT_DIR / f"nvda_forecast_{ts}.png"
            dom = DOM_DIR / f"nvda_forecast_{ts}.html"
            page.screenshot(path=str(ss), full_page=True)
            dom.write_text(page.content())
            print(f"Saved screenshot: {ss}")
            print(f"Saved DOM: {dom}")

            # Try to extract plotly traces length
            try:
                chart_info = page.evaluate("""
                    () => {
                        const el = document.getElementById('mf-forecast-chart');
                        if(!el) return {found:false};
                        // find plotly graph inside
                        const plot = el.querySelector('.js-plotly-plot');
                        if(!plot) return {found:true, traces: 0};
                        // Plotly stores data as window.Plotly ? Try reading Plotly react data
                        // Attempt to read Plotly._plots
                        try{
                            const gd = plot;
                            const traces = gd.data ? gd.data.length : 0;
                            return {found:true, traces: traces};
                        } catch(e) { return {found:true, traces:0}; }
                    }
                """)
                print("Chart info:", chart_info)
                # If traces present, attempt to extract trace names and sample y-values
                try:
                    traces = page.evaluate("""
                        () => {
                            const el = document.getElementById('mf-forecast-chart');
                            if(!el) return null;
                            const plot = el.querySelector('.js-plotly-plot');
                            if(!plot) return null;
                            try {
                                const raw = plot.data || [];
                                return raw.map(t => ({name: t.name||null, type: t.type||null, sampleY: (t.y && t.y.slice(0,10))||null}));
                            } catch(e){ return null }
                        }
                    """)
                    if traces:
                        ts2 = int(time.time())
                        traces_file = OUT_DIR / f"nvda_traces_{ts2}.json"
                        traces_file.write_text(json.dumps(traces, indent=2))
                        print(f"Saved traces: {traces_file}")
                except Exception:
                    pass
            except Exception as e:
                print("Could not extract chart info:", e)

            return 0
        finally:
            try:
                context.close()
                browser.close()
            except:
                pass

if __name__ == '__main__':
    headless = True
    if '--headed' in sys.argv or '--headful' in sys.argv:
        headless = False
    rc = run(headless=headless)
    sys.exit(rc)

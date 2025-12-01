#!/usr/bin/env python3
"""
Open dashboard, ensure Market Forecast tab selected, and extract Plotly traces (names and sample values).

This version is defensive: it hides common overlays, triggers clicks via in-page JS
to avoid pointer interception, polls for Plotly traces, and writes results to JSON.
"""
from playwright.sync_api import sync_playwright
from pathlib import Path
import json
import time
import os

PORT = os.environ.get('PORT', '8050')
URL = f'http://localhost:{PORT}'
OUT = Path('reports/systemfix/playwright')
OUT.mkdir(parents=True, exist_ok=True)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={'width':1200,'height':900})
        page = ctx.new_page()
        page.goto(URL, wait_until='networkidle', timeout=120000)

        # Defensive: remove/hide modal overlays that may block clicks
        page.evaluate("""
            () => {
                try {
                    const sel = ['.modal-backdrop', '.modal', '.overlay', '[data-blocking]', '.ReactModal__Overlay'];
                    sel.forEach(s => document.querySelectorAll(s).forEach(el => el.style.display = 'none'));
                    // also disable pointer-events for any high z-index element
                    document.querySelectorAll('*').forEach(el => {
                        const z = window.getComputedStyle(el).zIndex;
                        if (z && Number(z) > 1000) el.style.pointerEvents = 'none';
                    });
                } catch(e) { /* ignore */ }
            }
        """)

        # Ensure Market Forecast tab or the chart is visible. Try non-fragile JS click if needed.
        chart_selector = '#mf-forecast-chart .js-plotly-plot'
        if not page.locator(chart_selector).count():
            # try to click the Market Forecast nav via in-page JS (avoids overlay pointer issues)
            page.evaluate("""
                () => {
                    const tabs = Array.from(document.querySelectorAll('a.nav-link'));
                    const mf = tabs.find(t => (t.textContent||'').trim().includes('Market Forecast'));
                    if (mf) try { mf.click(); } catch(e) { mf.dispatchEvent(new MouseEvent('click',{bubbles:true})); }
                }
            """)
            page.wait_for_timeout(1200)

        # If run button exists, trigger it via JS click (less likely to be intercepted)
        # Select NVDA in ticker input (match behavior in nvda_forecast_test)
        try:
            # open dropdown/input
            if page.locator("#mf-ticker-input").count() > 0:
                try:
                    page.locator("#mf-ticker-input").first.click()
                except Exception:
                    page.locator("div[role='listbox']").first.click()
            else:
                # fallback
                if page.locator("div[role='listbox']").count() > 0:
                    page.locator("div[role='listbox']").first.click()
            page.wait_for_timeout(700)

            opt = page.locator("div[role='option']:has-text('NVDA')")
            if opt.count() > 0:
                opt.first.click()
            else:
                # typing fallback
                try:
                    inp = page.locator("#mf-ticker-input input")
                    if inp.count() > 0:
                        inp.first.fill('NVDA')
                        page.wait_for_timeout(300)
                        sel = page.locator("div[role='option']:has-text('NVDA')")
                        if sel.count() > 0:
                            sel.first.click()
                except Exception:
                    pass
            # verify selection; if not selected, try keyboard typing into the input
            try:
                sel_label = page.locator("#mf-ticker-input .Select-value-label")
                if sel_label.count() == 0 or sel_label.first.inner_text().strip() != 'NVDA':
                    # focus input and type NVDA then Enter
                    try:
                        if inp.count() > 0:
                            inp.first.click()
                            page.keyboard.type('NVDA')
                            page.wait_for_timeout(300)
                            page.keyboard.press('Enter')
                            page.wait_for_timeout(300)
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass

        # If run button exists, trigger it via JS click (less likely to be intercepted)
        if page.locator('#mf-run-btn').count()>0:
            page.evaluate("""
                () => {
                    const btn = document.getElementById('mf-run-btn');
                    if (btn) try { btn.click(); } catch(e) { btn.dispatchEvent(new MouseEvent('click',{bubbles:true})); }
                }
            """)

        # Wait for plotly plot to render and expose data (polling)
        def wait_for_traces(timeout_ms=60000, poll_interval=500):
            waited = 0
            while waited < timeout_ms:
                res = page.evaluate("""
                    () => {
                        const el = document.getElementById('mf-forecast-chart');
                        if (!el) return {found:false, reason:'chart-el-not-found'};
                        // Try direct Plotly gd.data first
                        const plot = el.querySelector('.js-plotly-plot');
                        try {
                            if (plot && plot.data && Array.isArray(plot.data) && plot.data.length>0){
                                const raw = plot.data || [];
                                const traces = raw.map(t => ({name: t.name||null, type: t.type||null, sampleY: (t.y && t.y.slice(0,5))||null}));
                                return {found: true, traces, rawLen: raw.length, method: 'gd.data'}
                            }
                        } catch(e) { /* continue to fallback */ }

                        // Fallback: read legend text nodes rendered in SVG
                        try {
                            const labels = Array.from(el.querySelectorAll('.legendtext')).map(n => n.textContent && n.textContent.trim()).filter(Boolean);
                            if (labels.length>0) return {found:true, traces: labels.map(l=>({name:l})), rawLen: labels.length, method: 'legendtext'}
                        } catch(e) { /* ignore */ }

                        return {found:false, reason:'no-traces-yet'};
                    }
                """)
                if isinstance(res, dict) and res.get('found'):
                    return res
                page.wait_for_timeout(poll_interval)
                waited += poll_interval
            return {'found': False, 'reason': 'timeout_waiting_for_traces'}

        # give the chart some time to update after clicking Run
        page.wait_for_timeout(3000)
    
        res = wait_for_traces()
        # Save traces to file for evidence
        outf = OUT / f"nvda_traces_{int(time.time())}.json"
        outf.write_text(json.dumps(res, indent=2))
        print(f"Saved traces to: {outf}")
        print(json.dumps(res, indent=2))

        browser.close()

if __name__ == '__main__':
    main()

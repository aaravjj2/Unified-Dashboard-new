"""Capture a screenshot and full HTML after attempting to open the Attribution select.

Saves files to /tmp for manual inspection.
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright


def test_capture_select_screenshot():
    out_png = Path('/tmp/analysis_hub_attr_select.png')
    out_html = Path('/tmp/analysis_hub_attr_select.html')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto('http://localhost:8000', wait_until='domcontentloaded')
        page.wait_for_timeout(500)
        # open Analysis Hub
        try:
            page.wait_for_selector('#dashboard-tabs', timeout=3000)
            page.locator('#dashboard-tabs a, #dashboard-tabs button').nth(4).click()
        except Exception:
            pass
        page.wait_for_timeout(600)
        # open Attribution subtab
        page.evaluate("()=>{ const ss = document.querySelectorAll('#analysis-hub-subtabs a, #analysis-hub-subtabs button'); for(const s of ss){ if(s.textContent && s.textContent.includes('Attribution')){ s.click(); return; } }}")
        page.wait_for_timeout(500)

        # attempt to open the select
        try:
            page.eval_on_selector('#hub-attr-picks-type .Select-control, #hub-attr-picks-type', "el => { el.scrollIntoView({block:'center'}); el.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true,view:window})); el.click(); }")
        except Exception:
            try:
                page.eval_on_selector('#hub-attr-picks-type', "el => el.click()")
            except Exception:
                pass

        page.wait_for_timeout(600)

        # save screenshot and full HTML
        page.screenshot(path=str(out_png), full_page=True)
        html = page.content()
        out_html.write_text(html)
        print('wrote', out_png, out_html)

        page.close()
        ctx.close()
        browser.close()

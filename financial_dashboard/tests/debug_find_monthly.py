"""Find DOM nodes that contain 'Monthly' and print visibility/rect/outerHTML.

Helps diagnose why the Monthly option isn't being selected by the test helper.
"""

import pytest


from playwright.sync_api import sync_playwright


def test_find_monthly_nodes():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto('http://localhost:8000', wait_until='domcontentloaded')
        page.wait_for_timeout(500)

        # click Analysis Hub tab (index 4)
        try:
            page.wait_for_selector('#dashboard-tabs', timeout=3000)
            page.locator("#dashboard-tabs a, #dashboard-tabs button").nth(4).click()
        except Exception as e:
            print('could not click hub tab', e)
        page.wait_for_timeout(600)

        # open Attribution subtab
        page.evaluate("()=>{ const ss = document.querySelectorAll('#analysis-hub-subtabs a, #analysis-hub-subtabs button'); for(const s of ss){ if(s.textContent && s.textContent.includes('Attribution')){ s.click(); return; } }}")
        page.wait_for_timeout(500)

        nodes = page.evaluate(
            "() => Array.from(document.querySelectorAll('div, li, button, span, a, p')).filter(n => n.innerText && n.innerText.toLowerCase().includes('monthly')).map(n => ({text: n.innerText.slice(0,200), outer: n.outerHTML.slice(0,600), rect: (function(){ try{ const r = n.getBoundingClientRect(); return {w:r.width,h:r.height,top:r.top,left:r.left}; }catch(e){return null;} })(), visible: (function(){ try{ const r = n.getBoundingClientRect(); const cs = getComputedStyle(n); return r.width>0 && r.height>0 && cs.visibility!=='hidden'; }catch(e){return false;} })(), parent: n.parentElement ? n.parentElement.outerHTML.slice(0,200) : null } ))"
        )

        print('\nFOUND', len(nodes), 'nodes containing Monthly')
        for i, n in enumerate(nodes):
            print('--- node', i)
            print('text:', n['text'])
            print('visible:', n['visible'], 'rect:', n['rect'])
            print('outer snippet:', n['outer'])
            print('parent snippet:', n['parent'][:200] if n['parent'] else None)
            print()

        page.close()
        ctx.close()
        browser.close()

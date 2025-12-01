"""Diagnostics for Analysis Hub: capture attribution picks and portfolio calc behavior.

This test prints DOM snapshots and element properties to help determine why
the Attribution pick remains 'weekly' and why Portfolio Analytics doesn't start.
"""

import time
import pytest
from playwright.sync_api import Page


DASHBOARD_URL = "http://localhost:8000"
NAV_WAIT = "domcontentloaded"


def click_tab_by_index(page: Page, idx: int) -> bool:
    try:
        page.wait_for_selector('#dashboard-tabs', timeout=5000)
        loc = page.locator("#dashboard-tabs a, #dashboard-tabs button")
        if loc.count() <= idx:
            return False
        loc.nth(idx).click()
        return True
    except Exception:
        return False


@pytest.fixture(scope='module')
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context()
    page = context.new_page()
    yield page
    page.close()
    context.close()


def _dump(sel, page: Page):
    return page.evaluate(
        "sel => { const e = document.querySelector(sel); if(!e) return null; return {outer: e.outerHTML, text: e.innerText || e.value || null, disabled: e.disabled || null, classes: e.className || null}; }",
        sel,
    )


def test_diag_attribution_and_portfolio(page: Page):
    page.goto(DASHBOARD_URL, wait_until=NAV_WAIT)
    assert click_tab_by_index(page, 4), "Could not open Analysis Hub tab"
    page.wait_for_timeout(800)

    # -- Attribution diagnostics --
    page.evaluate("()=>{ const ss = document.querySelectorAll('#analysis-hub-subtabs a, #analysis-hub-subtabs button'); for(const s of ss){ if(s.textContent && s.textContent.includes('Attribution')){ s.click(); return; } }}")
    page.wait_for_timeout(500)

    print('\n--- Attribution container snapshot ---')
    cont = page.query_selector('#hub-attr-container')
    if cont:
        print(cont.inner_html()[:4000])
    else:
        print('No #hub-attr-container found')

    # dropdown element
    dd = page.query_selector('#hub-attr-picks-type')
    if not dd:
        print('No #hub-attr-picks-type found; dumping nearest selects...')
        sels = page.query_selector_all('select, .dash-dropdown')
        for i, s in enumerate(sels[:10]):
            print(f"nearby[{i}] -> {s.get_attribute('id') or s.get_attribute('class')}")
        assert False, 'Attribution picks element not present'

    # dump dropdown outerHTML and possible options
    print('\n#hub-attr-picks-type before click:')
    print(_dump('#hub-attr-picks-type', page))

    # try to open and pick Monthly Picks by searching for visible menu items
    try:
        page.eval_on_selector('#hub-attr-picks-type', "el => el.scrollIntoView({block:'center'})")
        page.eval_on_selector('#hub-attr-picks-type', "el => el.click()")
    except Exception as e:
        print('click dropdown error:', e)

    page.wait_for_timeout(300)
    # look for candidate labels
    candidates = page.evaluate(
        "() => Array.from(document.querySelectorAll('div, li, button, span')).filter(n => n.innerText && n.innerText.toLowerCase().includes('monthly')).slice(0,20).map(n => ({text: n.innerText, outer: n.outerHTML.slice(0,300)}))"
    )
    print('\nMonthly candidates found:', len(candidates))
    for c in candidates:
        print('-', c['text'][:120])

    # attempt to click a candidate that contains Monthly
    if candidates:
        page.evaluate("txt => { const nodes = Array.from(document.querySelectorAll('div, li, button, span')).filter(n => n.innerText && n.innerText.includes(txt)); if(nodes.length) nodes[nodes.length-1].click(); }", candidates[0]['text'])
        page.wait_for_timeout(300)

    # check what the component reports selected
    selected_val = page.evaluate("() => { const e = document.querySelector('#hub-attr-picks-type'); if(!e) return null; return e.innerText || e.value || e.getAttribute('aria-label') || e.getAttribute('data-value'); }")
    print('\nselected after attempt:', repr(selected_val))

    # -- Portfolio analytics diagnostics --
    page.evaluate("()=>{ const ss = document.querySelectorAll('#analysis-hub-subtabs a, #analysis-hub-subtabs button'); for(const s of ss){ if(s.textContent && s.textContent.includes('Portfolio')){ s.click(); return; } }}")
    page.wait_for_timeout(500)

    print('\n--- Portfolio container snapshot ---')
    pc = page.query_selector('#hub-portfolio-container')
    if pc:
        print(pc.inner_html()[:4000])
    else:
        print('No #hub-portfolio-container found')

    btn = page.query_selector('#hub-pa-calc-btn')
    if not btn:
        print('No #hub-pa-calc-btn found; listing buttons nearby')
        bts = page.query_selector_all('button')
        for i, b in enumerate(bts[:20]):
            print(i, b.get_attribute('id'), b.inner_text()[:80])
        assert False, 'Calculate button not present'

    print('\n#hub-pa-calc-btn dump:', _dump('#hub-pa-calc-btn', page))
    # check disabled/aria-disabled attribute
    is_disabled = page.evaluate("() => { const e = document.querySelector('#hub-pa-calc-btn'); if(!e) return null; return {disabled: e.disabled || null, aria: e.getAttribute('aria-disabled')}; }")
    print('button state:', is_disabled)

    # click calculate and monitor status nodes
    status_sel = '#pa-total-return, #hub-pa-status, #pa-status'
    pre_status = page.query_selector_all(status_sel)
    print('pre-click status nodes count:', len(pre_status))

    try:
        page.eval_on_selector('#hub-pa-calc-btn', "el => { el.scrollIntoView({block:'center'}); el.click(); }")
    except Exception as e:
        print('calc click error:', e)
        # try normal click
        try:
            page.click('#hub-pa-calc-btn', timeout=3000)
        except Exception as e2:
            print('fallback click failed:', e2)

    page.wait_for_timeout(1500)

    post_nodes = page.query_selector_all(status_sel)
    print('post-click status nodes count:', len(post_nodes))
    for n in post_nodes:
        print('status node text:', n.inner_text()[:400])

    # final check: does pa-total-return exist and have numeric content?
    total = page.query_selector('#pa-total-return')
    if total:
        ttxt = total.inner_text()[:400]
        print('\npa-total-return:', ttxt)
    else:
        print('\npa-total-return not present after click')

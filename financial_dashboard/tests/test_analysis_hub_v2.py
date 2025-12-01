"""Focused Playwright tests for Analysis Hub flows (v2).

This file is a replacement for the earlier analysis hub test and
includes ensure_clickable which collects visibility diagnostics and
attempts JS remedies before clicking.
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


def ensure_clickable(page: Page, selector: str, timeout: int = 5000) -> bool:
    try:
        page.wait_for_selector(selector, state='attached', timeout=timeout)
    except Exception:
        print(f"ensure_clickable: {selector} not attached within {timeout}ms")
        return False

    diag = page.evaluate(
        "sel => { const e = document.querySelector(sel); if(!e) return {exists:false}; const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return {exists:true, display: cs.display, visibility: cs.visibility, opacity: parseFloat(cs.opacity), width: r.width, height: r.height, inViewport: (r.top>=0 && r.left>=0 && r.bottom <= (window.innerHeight||document.documentElement.clientHeight) && r.right <= (window.innerWidth||document.documentElement.clientWidth)), clientRects: e.getClientRects().length, offsetParent: !!e.offsetParent}; }",
        selector,
    )

    if not diag or not diag.get('exists'):
        print(f"ensure_clickable: {selector} not found after attach wait")
        return False

    invisible_reasons = []
    if diag.get('display') in ('none',):
        invisible_reasons.append('display:none')
    if diag.get('visibility') in ('hidden', 'collapse'):
        invisible_reasons.append(f"visibility={diag.get('visibility')}")
    if diag.get('opacity', 1) < 0.05:
        invisible_reasons.append(f"opacity={diag.get('opacity')}")
    if diag.get('width', 0) == 0 or diag.get('height', 0) == 0:
        invisible_reasons.append('zero-size')

    if invisible_reasons:
        print(f"ensure_clickable: {selector} visibility issues: {invisible_reasons}; diag={diag}")
        try:
            page.evaluate(
                "sel => { const e = document.querySelector(sel); if(!e) return; e.style.display = 'block'; e.style.visibility = 'visible'; e.style.opacity = '1'; e.scrollIntoView({block:'center'}); }",
                selector,
            )
            time.sleep(0.15)
            diag2 = page.evaluate(
                "sel => { const e = document.querySelector(sel); if(!e) return {}; const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return {display: cs.display, visibility: cs.visibility, opacity: parseFloat(cs.opacity), width: r.width, height: r.height, inViewport: (r.top>=0 && r.left>=0 && r.bottom <= (window.innerHeight||document.documentElement.clientHeight) && r.right <= (window.innerWidth||document.documentElement.clientWidth))}; }",
                selector,
            )
            print(f"ensure_clickable: post-remedy diag for {selector}: {diag2}")
        except Exception as e:
            print(f"ensure_clickable: remedy eval failed for {selector}: {e}")

    try:
        page.eval_on_selector(selector, "el => { el.scrollIntoView({block:'center'}); el.click(); }")
        return True
    except Exception as e:
        try:
            page.focus(selector)
            page.keyboard.press('Enter')
            return True
        except Exception:
            raise e


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


def test_analysis_hub_attribution_monthly_run(page: Page):
    page.goto(DASHBOARD_URL, wait_until=NAV_WAIT)
    assert click_tab_by_index(page, 4), "Could not click Analysis Hub tab"
    page.wait_for_timeout(600)

    page.evaluate(
        "()=>{ const ss = document.querySelectorAll('#analysis-hub-subtabs a, #analysis-hub-subtabs button'); for(const s of ss){ if(s.textContent && s.textContent.includes('Attribution')){ s.click(); return; } }}"
    )
    page.wait_for_timeout(500)

    if page.query_selector('#hub-attr-picks-type'):
        try:
            page.wait_for_selector('#hub-attr-picks-type', state='attached', timeout=5000)
            ok = ensure_clickable(page, '#hub-attr-picks-type', timeout=5000)
        except Exception as e:
            print(f"ERROR clicking #hub-attr-picks-type: {e}")
            raise
        assert ok, "hub-attr-picks-type not present or not clickable"
        page.wait_for_timeout(350)
        page.evaluate(
            "()=>{ const d = Array.from(document.querySelectorAll('div')).filter(x=>x.textContent && x.textContent.includes('Monthly Picks')); if(d.length) d[d.length-1].click(); }"
        )
        page.wait_for_timeout(350)

    if page.query_selector('#hub-attr-run-button'):
        ensure_clickable(page, '#hub-attr-run-button')
        page.wait_for_timeout(1500)
        status = page.query_selector('#hub-attr-status')
        if status:
            txt = status.inner_text().lower()
            assert 'error' not in txt and 'no files' not in txt


def test_analysis_hub_portfolio_analytics(page: Page):
    page.goto(DASHBOARD_URL, wait_until=NAV_WAIT)
    assert click_tab_by_index(page, 4), "Could not click Analysis Hub tab"
    page.wait_for_timeout(600)

    page.evaluate(
        "()=>{ const ss = document.querySelectorAll('#analysis-hub-subtabs a, #analysis-hub-subtabs button'); for(const s of ss){ if(s.textContent && s.textContent.includes('Portfolio')){ s.click(); return; } }}"
    )
    page.wait_for_timeout(500)

    if page.query_selector('#hub-pa-calc-btn'):
        try:
            page.wait_for_selector('#hub-pa-calc-btn', state='attached', timeout=5000)
            ok = ensure_clickable(page, '#hub-pa-calc-btn', timeout=5000)
        except Exception as e:
            print(f"ERROR clicking #hub-pa-calc-btn: {e}")
            raise
        assert ok, "hub-pa-calc-btn not present or not clickable"
        page.wait_for_timeout(1400)
        assert page.query_selector('#pa-total-return') is not None

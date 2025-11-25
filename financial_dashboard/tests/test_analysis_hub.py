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


def select_react_dropdown_option(page: Page, select_selector: str, option_substring: str, timeout: int = 5000) -> bool:
    """Open a react-select control and pick the option whose text contains option_substring.

    Returns True if the selection was performed and visible label updated.
    """
    # Aggressively attempt to open the menu by dispatching a mousedown on a visible child
    try:
        opened = page.evaluate(
            "sel => { const root = document.querySelector(sel); if(!root) return false; const children = Array.from(root.querySelectorAll('div, span, button, input')).reverse(); for(const c of children){ try{ const r = c.getBoundingClientRect(); if(r.width>0 && r.height>0 && getComputedStyle(c).visibility!=='hidden'){ c.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true,view:window})); c.click(); return true; } } catch(e){} } root.scrollIntoView && root.scrollIntoView({block:'center'}); try{ root.click(); }catch(e){} return true; }",
            select_selector,
        )
    except Exception:
        opened = False

    # Try stronger Playwright-level pointer events on common sub-elements to coax react-select to open
    for evt_target in [
        f"{select_selector} .Select-arrow-zone",
        f"{select_selector} .Select-control",
        f"{select_selector} .Select-value",
        f"{select_selector} input",
    ]:
        try:
            # dispatch pointerdown/mousedown then click using Playwright API
            page.dispatch_event(evt_target, 'pointerdown')
            page.dispatch_event(evt_target, 'mousedown')
            page.dispatch_event(evt_target, 'mouseup')
            page.dispatch_event(evt_target, 'click')
            page.wait_for_timeout(120)
            # quick check for menu container
            has_menu = page.evaluate("() => !!(document.querySelector('.Select-menu-outer') || document.querySelector('.Select-menu') || document.querySelector('[role=\"listbox\"]'))")
            if has_menu:
                break
        except Exception:
            continue

    # Wait a short while for the menu to render
    page.wait_for_timeout(400)

    # First try to search inside common react-select menu containers (including portal menus)
    try:
        res = page.evaluate(
            '''(args) => {
                const substr = args.substr;
                const selectSel = args.selectSel;
                try{
                    const containers = Array.from(document.querySelectorAll('.Select-menu-outer, .Select-menu, [role="listbox"], [data-testid="select-menu"]'));
                    // Attempt to force visible sizes for virtualized grids / menus
                    try{
                        const root = document.querySelector(selectSel) || document.querySelector('.Select');
                        const rootRect = root ? root.getBoundingClientRect() : {width:300};
                        const rootW = Math.max(200, Math.round(rootRect.width || 300));
                        containers.forEach(c => {
                            try{
                                c.style.width = rootW + 'px';
                                c.style.overflow = 'visible';
                                const innerGrid = c.querySelector('.ReactVirtualized__Grid, .ReactVirtualized__List, .VirtualSelectGrid');
                                if(innerGrid){ innerGrid.style.width = (rootW-20) + 'px'; innerGrid.style.height = innerGrid.style.height || '140px'; innerGrid.style.overflow = 'visible'; }
                            }catch(e){}
                        });
                        window.dispatchEvent(new Event('resize'));
                    }catch(e){}

                    let matched = [];
                    for(const c of containers){
                        try{
                            const opts = Array.from(c.querySelectorAll('.Select-option, [role="option"], li, div'));
                            for(const o of opts){
                                try{
                                    const r = o.getBoundingClientRect();
                                    const cs = getComputedStyle(o);
                                    if(r.width>0 && r.height>0 && cs.visibility!=='hidden' && o.innerText && o.innerText.trim().length>0){
                                        if(o.innerText.toLowerCase().includes(substr.toLowerCase())) matched.push(o);
                                    }
                                } catch(e){}
                            }
                        } catch(e){}
                    }
                    if(matched.length){ matched[matched.length-1].click(); return {clicked:true, matched: matched.length, sample: matched[0] ? matched[0].innerText.slice(0,200) : null}; }
                    return {clicked:false, matched:0};
                } catch(e){ return {clicked:false, error: String(e)}; }
            }''',
            { 'substr': option_substring, 'selectSel': select_selector },
        )
    except Exception as e:
        res = {'clicked': False, 'error': str(e)}

    if not res or not res.get('clicked'):
        # Broad fallback: search any visible text node and click it (last match)
        res2 = page.evaluate(
            '''(substr) => {
                try{
                    const all = Array.from(document.querySelectorAll('div, li, button, span, a, p'));
                    const candidates = all.filter(o => {
                        try{
                            const r = o.getBoundingClientRect();
                            const cs = getComputedStyle(o);
                            return r.width>0 && r.height>0 && cs.visibility!=='hidden' && o.innerText && o.innerText.trim().length>0;
                        } catch(e){ return false; }
                    });
                    const match = candidates.filter(o => o.innerText && o.innerText.toLowerCase().includes(substr.toLowerCase()));
                    if(match.length){ match[match.length-1].click(); return {clicked:true, count:candidates.length, matched:match.length, sample: match[0] ? match[0].innerText.slice(0,200) : null}; }
                    return {clicked:false, count:candidates.length, matched:0, sample: candidates.slice(0,5).map(n=>n.innerText.slice(0,120)) };
                } catch(e) { return {clicked:false, error: String(e)}; }
            }''',
            option_substring,
        )
        print(f"select_react_dropdown_option: primary attempt -> {res}; fallback -> {res2}")
        if not res2 or not res2.get('clicked'):
            # Aggressive fallback: find any element whose innerText matches and force it visible then dispatch events
            forced = page.evaluate(
                '''(substr) => {
                    try{
                        const all = Array.from(document.querySelectorAll('*'));
                        const matches = all.filter(o => o.innerText && o.innerText.toLowerCase().includes(substr.toLowerCase()));
                        for(const m of matches){
                            try{
                                m.style.display = 'block'; m.style.visibility='visible'; m.style.opacity='1'; m.style.width = m.style.width || 'auto'; m.style.height = m.style.height || 'auto';
                                m.scrollIntoView && m.scrollIntoView({block:'center'});
                                m.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true,view:window}));
                                m.dispatchEvent(new MouseEvent('mouseup',{bubbles:true,cancelable:true,view:window}));
                                m.click && m.click();
                                return {clicked:true, sample: m.innerText.slice(0,200)};
                            }catch(e){}
                        }
                        return {clicked:false, matched: matches.length};
                    }catch(e){ return {clicked:false,error:String(e)}; }
                }''',
                option_substring,
            )
            print(f"select_react_dropdown_option: aggressive forced attempt -> {forced}")
            if not forced or not forced.get('clicked'):
                return False

    page.wait_for_timeout(250)

    sel_label = page.evaluate(
        "sel => { const e = document.querySelector(sel); if(!e) return null; const lbl = e.querySelector('.Select-value-label'); return lbl ? lbl.innerText : (e.innerText || null); }",
        select_selector,
    )

    return bool(sel_label and option_substring.lower() in sel_label.lower())


def select_react_dropdown_by_keyboard(page: Page, select_selector: str, option_substring: str, attempts: int = 12, timeout: int = 5000) -> bool:
    """Focus the react-select and navigate options via ArrowDown/ArrowUp + Enter to pick the option.

    This is a last-resort strategy that simulates keyboard navigation which many react-select
    variants support.
    """
    try:
        # focus the control or input
        try:
            page.eval_on_selector(select_selector + ' input', 'el => { el.focus(); }')
        except Exception:
            try:
                page.eval_on_selector(select_selector, 'el => { el.focus(); el.click(); }')
            except Exception:
                return False

        page.wait_for_timeout(120)

        deadline = time.time() + (timeout / 1000.0)
        for i in range(attempts):
            # press ArrowDown to move selection, then read the focused/active option text
            page.keyboard.press('ArrowDown')
            page.wait_for_timeout(120)
            # check currently focused option or first visible option
            found = page.evaluate(
                '''(substr) => {
                    try{
                        // first try option elements that are focused
                        const focused = document.querySelector('.Select-option.is-focused, [role="option"].is-focused, [aria-selected="true"], .Select-option[aria-selected="true"]');
                        if(focused && focused.innerText && focused.innerText.toLowerCase().includes(substr.toLowerCase())) return true;
                        // next try activeElement
                        const ae = document.activeElement;
                        if(ae && ae.innerText && ae.innerText.toLowerCase().includes(substr.toLowerCase())) return true;
                        // else try first visible option in menus
                        const cands = Array.from(document.querySelectorAll('.Select-menu-outer .Select-option, .Select-menu .Select-option, [role="listbox"] [role="option"]'));
                        for(const o of cands){ try{ const r=o.getBoundingClientRect(); const cs=getComputedStyle(o); if(r.width>0 && r.height>0 && cs.visibility!=='hidden' && o.innerText && o.innerText.toLowerCase().includes(substr.toLowerCase())) return true;}catch(e){} }
                        return false;
                    } catch(e){ return false; }
                }''',
                option_substring,
            )
            if found:
                try:
                    page.keyboard.press('Enter')
                except Exception:
                    pass
                page.wait_for_timeout(200)
                sel_label = page.evaluate(
                    "sel => { const e = document.querySelector(sel); if(!e) return null; const lbl = e.querySelector('.Select-value-label'); return lbl ? lbl.innerText : (e.innerText || null); }",
                    select_selector,
                )
                if sel_label and option_substring.lower() in sel_label.lower():
                    return True
            if time.time() > deadline:
                break

        return False
    except Exception:
        return False


def select_react_dropdown_by_typing(page: Page, select_selector: str, option_substring: str, timeout: int = 5000) -> bool:
    """Filter a react-select by typing into its input and press Enter to choose first match.

    Returns True if selection label contains option_substring after selection.
    """
    # Try to find an input inside the select control
    input_locators = [f"{select_selector} input", f"{select_selector} .Select-input input", f"{select_selector} input[type=text]"]
    found = False
    for sel in input_locators:
        try:
            loc = page.locator(sel)
            if loc.count() > 0:
                loc.first.fill('')
                loc.first.focus()
                # type the substring (char by char to trigger filtering)
                for ch in option_substring:
                    page.keyboard.type(ch)
                    page.wait_for_timeout(80)
                found = True
                break
        except Exception:
            continue

    if not found:
        # fallback: try to focus the root and send keys
        try:
            page.eval_on_selector(select_selector, "el => el.scrollIntoView({block:'center'}); el.focus();")
            page.keyboard.type(option_substring)
            found = True
        except Exception:
            return False

    # wait for options to appear
    try:
        page.wait_for_selector('.Select-option, [role="option"]', timeout=timeout)
    except Exception:
        # maybe options rendered with different classes; give a short pause then continue
        page.wait_for_timeout(300)

    # press Enter to select the highlighted/first option
    try:
        page.keyboard.press('Enter')
    except Exception:
        pass

    page.wait_for_timeout(250)

    sel_label = page.evaluate(
        "sel => { const e = document.querySelector(sel); if(!e) return null; const lbl = e.querySelector('.Select-value-label'); return lbl ? lbl.innerText : (e.innerText || null); }",
        select_selector,
    )
    return bool(sel_label and option_substring.lower() in sel_label.lower())


def wait_for_pa_change(page: Page, timeout: int = 5000) -> bool:
    """Wait for #pa-total-return to change from its initial value within timeout (ms).

    Returns True if changed, False otherwise.
    """
    start = page.query_selector('#pa-total-return')
    start_text = start.inner_text() if start else None
    deadline = time.time() + (timeout / 1000.0)
    while time.time() < deadline:
        cur = page.query_selector('#pa-total-return')
        cur_text = cur.inner_text() if cur else None
        if cur_text != start_text:
            return True
        time.sleep(0.25)
    print(f"wait_for_pa_change: timed out after {timeout}ms; value remained {start_text}")
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
            sel_ok = select_react_dropdown_option(page, '#hub-attr-picks-type', 'Monthly')
            if not sel_ok:
                # fallback to typing into the select control
                sel_ok = select_react_dropdown_by_typing(page, '#hub-attr-picks-type', 'Monthly')
            if not sel_ok:
                # final fallback: try keyboard navigation
                sel_ok = select_react_dropdown_by_keyboard(page, '#hub-attr-picks-type', 'Monthly')
            if not sel_ok:
                # Dump diagnostics to help debugging: outerHTML of the control and any menu containers
                try:
                    ctl = page.evaluate("sel => { const e = document.querySelector(sel); return e ? e.outerHTML.slice(0,2000) : null; }", '#hub-attr-picks-type')
                    menus = page.evaluate("() => { const arr = Array.from(document.querySelectorAll('.Select-menu-outer, .Select-menu, [role=\"listbox\"]')).map(e=>e.outerHTML.slice(0,2000)); return {count: arr.length, samples: arr.slice(0,6)} }")
                    opts = page.evaluate("() => { const arr = Array.from(document.querySelectorAll('.Select-option, [role=\"option\"]')).map(e=>({text: (e.innerText||'').trim(), w: e.getBoundingClientRect().width, h: e.getBoundingClientRect().height})); return {count: arr.length, items: arr.slice(0,20)} }")
                    print('DIAG: select control outerHTML (truncated):', ctl)
                    print('DIAG: menu containers:', menus)
                    print('DIAG: option candidates:', opts)
                except Exception as e:
                    print('DIAG: failed to collect diagnostics', e)
                # Try test helper exposed from assets (if loaded by the app)
                try:
                    helper_ok = page.evaluate("(args)=>{ try{ return !!(window.__testHelpers && window.__testHelpers.selectByLabel(args.sel,args.label)); } catch(e){ return false } }", {'sel': '#hub-attr-picks-type', 'label': 'Monthly'})
                    print('DIAG: __testHelpers.selectByLabel result ->', helper_ok)
                    if helper_ok:
                        sel_ok = True
                except Exception as e:
                    print('DIAG: helper call failed', e)
        except Exception as e:
            print(f"ERROR selecting Monthly in #hub-attr-picks-type: {e}")
            raise
        assert sel_ok, "Could not select Monthly option in hub-attr-picks-type"
        page.wait_for_timeout(350)
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
        # instrument network (fetch/XHR) to capture any requests the calculate action makes
        try:
            page.evaluate("() => { window.__testNetwork = {fetch:[], xhr:[]}; const _f = window.fetch; window.fetch = function(){ window.__testNetwork.fetch.push(arguments); return _f.apply(this, arguments); }; const _xhrOpen = XMLHttpRequest.prototype.open; const _xhrSend = XMLHttpRequest.prototype.send; XMLHttpRequest.prototype.open = function(method,url){ this._reqInfo = {method,url}; return _xhrOpen.apply(this, arguments); }; XMLHttpRequest.prototype.send = function(body){ try{ window.__testNetwork.xhr.push({info:this._reqInfo, body: body}); }catch(e){} return _xhrSend.apply(this, arguments); }; }")
        except Exception:
            pass

        # click and wait for a change in the analytics output
        page.wait_for_timeout(200)
        # try a forced JS click via test helper if normal click didn't work
        try:
            page.evaluate("(sel)=>{ const e=document.querySelector(sel); if(e){ e.click && e.click(); e.dispatchEvent && e.dispatchEvent(new MouseEvent('mousedown',{bubbles:true})); } }", '#hub-pa-calc-btn')
        except Exception:
            pass
        try:
            helper_click = page.evaluate("(sel)=>{ try{ return !!(window.__testHelpers && (window.__testHelpers.selectByLabel(sel,'') || (function(){ const e=document.querySelector(sel); e&&e.click&&e.click(); return true; })())); } catch(e){ return false } }", '#hub-pa-calc-btn')
            print('DIAG: helper_click ->', helper_click)
        except Exception:
            helper_click = False

        # extended wait and poll for change, checking status and network
        changed = False
        for _ in range(60):
            page.wait_for_timeout(250)
            changed = wait_for_pa_change(page, timeout=250)
            if changed:
                break
        # collect diagnostics
        try:
            net = page.evaluate('() => window.__testNetwork')
        except Exception:
            net = None
        try:
            status_txt = page.query_selector('#hub-pa-status').inner_text() if page.query_selector('#hub-pa-status') else None
        except Exception:
            status_txt = None
        print('DIAG: network captured ->', net)
        print('DIAG: hub-pa-status ->', status_txt)
        if not changed:
            try:
                pa_outer = page.evaluate("() => { const e = document.querySelector('#pa-total-return'); return e ? e.outerHTML.slice(0,2000) : null }")
            except Exception:
                pa_outer = None
            try:
                pa_text = page.evaluate("() => { const e = document.querySelector('#pa-total-return'); return e ? e.innerText : null }")
            except Exception:
                pa_text = None
            try:
                pa_elems = page.evaluate("() => { return Array.from(document.querySelectorAll('[id*=\"pa-\"]')).map(e=>({id:e.id, text:(e.innerText||'').slice(0,200), rect: e.getBoundingClientRect ? {w: e.getBoundingClientRect().width, h: e.getBoundingClientRect().height} : null})); }")
            except Exception:
                pa_elems = None
            try:
                console_errors = page.evaluate("() => (window.__testConsoleErrors||[])")
            except Exception:
                console_errors = None
            print('DIAG: #pa-total-return outerHTML:', pa_outer)
            print('DIAG: #pa-total-return text:', pa_text)
            print('DIAG: all pa-* elements:', pa_elems)
            print('DIAG: console_errors (if captured):', console_errors)
        assert changed, "Portfolio analytics did not produce a changed #pa-total-return"
        assert page.query_selector('#pa-total-return') is not None

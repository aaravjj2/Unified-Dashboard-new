from playwright.sync_api import sync_playwright
import time

URL = 'http://127.0.0.1:8000'

def find_and_click_nav_by_text(page, text):
    # Try a few strategies to activate a tab by visible text
    # 1) button[data-tab]
    try:
        btn = page.query_selector(f'button[data-tab]')
        if btn:
            # try to find matching among many
            for b in page.query_selector_all('button[data-tab]'):
                if text.lower() in (b.inner_text() or '').lower():
                    b.click()
                    return True
    except Exception:
        pass

    # 2) nav links under #dashboard-tabs
    try:
        links = page.query_selector_all('#dashboard-tabs .nav-link')
        for l in links:
            if text.lower() in (l.inner_text() or '').lower():
                l.click()
                return True
    except Exception:
        pass

    # 3) generic search by visible text
    try:
        elems = page.query_selector_all('a,button,div,span')
        for e in elems:
            txt = (e.inner_text() or '').strip().lower()
            if text.lower() in txt and len(txt) < 100:
                e.click()
                return True
    except Exception:
        pass

    return False

    # Fallback: try client-side helper if available
    # (note: Playwright sync page.evaluate_string requires passing text)
    try:
        res = page.evaluate("(t) => window.selectDashboardTab ? window.selectDashboardTab(t) : false", text)
        if res:
            return True
    except Exception:
        pass

    return False

def read_text_if_present(page, selector, timeout=5):
    try:
        el = page.query_selector(selector)
        if el:
            return el.inner_text()
        return None
    except Exception:
        return None

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print('Opening', URL)
        # Use domcontentloaded (lighter) and wait for the tabs container explicitly
        try:
            page.goto(URL, wait_until='domcontentloaded', timeout=60000)
        except Exception as e:
            print('Initial goto failed:', e)
            try:
                page.goto(URL, wait_until='domcontentloaded', timeout=120000)
            except Exception as e2:
                print('Second goto attempt failed:', e2)
                raise

        # Wait for the dashboard tabs element to appear (this ensures the Dash app finished rendering)
        try:
            page.wait_for_selector('#dashboard-tabs', timeout=60000)
        except Exception:
            print('Warning: #dashboard-tabs not found within timeout; continuing anyway')
        # Wait for client-side test helper to be available (assets/test_helpers.js)
        try:
            page.wait_for_function('() => window.selectDashboardTab !== undefined', timeout=10000)
            print('Client-side test helper available')
        except Exception:
            print('Client-side test helper not available; proceeding without it')

        # 1) Open Portfolio tab (top-level)
        # Activate Portfolio top-level tab (use client helper if possible)
        try:
            res = page.evaluate("(t) => window.selectDashboardTab ? window.selectDashboardTab(t) : false", 'Portfolio')
            print('Activated Portfolio via client helper:', res)
        except Exception:
            res = find_and_click_nav_by_text(page, 'Portfolio')
            print('Activated Portfolio via fallback:', res)
        time.sleep(1)

        # Activate Portfolio Analytics subtab
        try:
            res2 = page.evaluate("(t) => window.selectDashboardTab ? window.selectDashboardTab(t) : false", 'Portfolio Analytics')
            print('Activated Portfolio Analytics via client helper:', res2)
        except Exception:
            res2 = find_and_click_nav_by_text(page, 'Portfolio Analytics')
            print('Activated Portfolio Analytics via fallback:', res2)
        time.sleep(1)

        # 3) Try to click the Calculate Analytics button (try legacy and refactored ids)
        clicked_calc = False
        try:
            calc_selectors = ['#pa-calc-btn', '#hub-pa-calc-btn', '#hub-pa-calc-btn']
            found = None
            for sel in calc_selectors:
                try:
                    # avoid long waits here; attempt presence
                    if page.query_selector(sel):
                        found = sel
                        break
                except Exception:
                    continue

            if found:
                try:
                    # ensure visible by scrolling into view then click via JS if needed
                    page.eval_on_selector(found, "el => el.scrollIntoView({block:'center'})")
                    try:
                        page.click(found)
                    except Exception:
                        page.evaluate(f"() => document.querySelector('{found}') && document.querySelector('{found}').click()")
                    clicked_calc = True
                except Exception as e:
                    print('Error clicking calculate via selector', found, e)
            else:
                # fallback: click button with text 'Calculate Analytics'
                for b in page.query_selector_all('button'):
                    try:
                        if 'calculate' in (b.inner_text() or '').lower():
                            b.scroll_into_view_if_needed()
                            try:
                                b.click()
                            except Exception:
                                page.evaluate("el => el.click()", b)
                            clicked_calc = True
                            break
                    except Exception:
                        continue
        except Exception as e:
            print('Error clicking calculate:', e)

        print('Clicked Calculate Analytics button?', clicked_calc)
        time.sleep(2)

        # 4) Read pa-cost-breakdown and pa-total-return
        pa_cost = read_text_if_present(page, '#pa-cost-breakdown')
        pa_total = read_text_if_present(page, '#pa-total-return')
        print('\npa-cost-breakdown:\n', pa_cost)
        print('\npa-total-return:\n', pa_total)

        # 5) Now test Attribution tab monthly vs weekly
        # Activate Analysis Hub / Attribution tab
        try:
            res_attr = page.evaluate("(t) => window.selectDashboardTab ? window.selectDashboardTab(t) : false", 'Analysis Hub')
            print('Activated Analysis Hub via client helper:', res_attr)
        except Exception:
            res_attr = find_and_click_nav_by_text(page, 'Analysis Hub') or find_and_click_nav_by_text(page, 'Attribution')
            print('Activated Analysis Hub via fallback:', res_attr)
        time.sleep(1)

        # attempt to find picks-type control (id 'attr-picks-type') and set to monthly then run
        def set_picks_and_run(option_text):
            print(f"Setting picks_type to: {option_text}")
            try:
                # Try multiple possible selectors for the picks control
                val = 'monthly' if 'monthly' in option_text.lower() else 'weekly'
                picks_selectors = ['#attr-picks-type', '#hub-attr-picks-type', '#attr-picks-type']
                picked = False
                for ps in picks_selectors:
                    try:
                        if page.query_selector(ps):
                            try:
                                page.select_option(ps, val)
                                picked = True
                                break
                            except Exception:
                                # fallback JS for React/select controls
                                try:
                                    page.evaluate("(p,v)=>{ const el=document.querySelector(p); if(!el) return false; const s=el.querySelector('select'); if(s){ s.value=v; s.dispatchEvent(new Event('change',{bubbles:true})); return true;} const opts=el.querySelectorAll('[role=option], .Select-option'); for(const o of opts){ if((o.innerText||'').toLowerCase().includes(v)){ o.click(); return true; } } return false;}", ps, val)
                                    picked = True
                                    break
                                except Exception:
                                    pass
                    except Exception:
                        continue

                if not picked:
                    # fallback: click button with text 'Monthly' or 'Weekly'
                    for b in page.query_selector_all('button'):
                        try:
                            if option_text.lower() in (b.inner_text() or '').lower():
                                try:
                                    b.scroll_into_view_if_needed()
                                    b.click()
                                except Exception:
                                    page.evaluate("el=>el.click()", b)
                                picked = True
                                break
                        except Exception:
                            continue
            except Exception as e:
                print('Error setting picks type:', e)

            # click run button (try several ids and fallbacks)
            try:
                run_selectors = ['#attr-run-button', '#hub-attr-run-button', '#hub-attr-run-button']
                run_clicked = False
                for rs in run_selectors:
                    try:
                        if page.query_selector(rs):
                            try:
                                page.eval_on_selector(rs, "el => el.scrollIntoView({block:'center'})")
                                page.click(rs)
                                run_clicked = True
                                break
                            except Exception:
                                try:
                                    page.evaluate(f"() => document.querySelector('{rs}') && document.querySelector('{rs}').click()")
                                    run_clicked = True
                                    break
                                except Exception:
                                    continue
                    except Exception:
                        continue

                if not run_clicked:
                    for b in page.query_selector_all('button'):
                        try:
                            txt = (b.inner_text() or '').lower()
                            if 'run' in txt or 'attribution' in txt:
                                try:
                                    b.scroll_into_view_if_needed(); b.click(); run_clicked = True; break
                                except Exception:
                                    page.evaluate("el=>el.click()", b); run_clicked = True; break
                        except Exception:
                            continue

                if not run_clicked:
                    # try test-helpers selectByLabel to trigger
                    try:
                        page.evaluate("() => window.__testHelpers && window.__testHelpers.selectByLabel('#attr-picks-type','')")
                    except Exception:
                        pass
            except Exception as e:
                print('Error clicking run:', e)

            time.sleep(2)
            # read results area
            picks_text = read_text_if_present(page, '#attr-results-store') or read_text_if_present(page, '#attr-results') or read_text_if_present(page, '#attr-picks-list')
            print(f"Resulting picks area (for {option_text}):\n", picks_text)

        set_picks_and_run('Monthly')
        set_picks_and_run('Weekly')

        browser.close()

if __name__ == '__main__':
    run()

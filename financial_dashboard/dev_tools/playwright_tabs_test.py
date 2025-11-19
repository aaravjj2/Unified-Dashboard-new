from playwright.sync_api import sync_playwright
import time
import os

# Default to the integrated dashboard which runs on port 8000
URL = os.environ.get('MARKET_DASH_URL', 'http://127.0.0.1:8000')
OUT_DIR = os.environ.get('PLAYWRIGHT_OUT', '/tmp/dash_tab_screens')


def ensure_out_dir():
    try:
        os.makedirs(OUT_DIR, exist_ok=True)
    except Exception:
        pass


def main():
    TABS = None

    with sync_playwright() as p:
        ensure_out_dir()
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, timeout=60000)
        # wait longer for Dash renderer to hydrate
        time.sleep(4)
        # dump rendered page HTML into workspace for inspection
        try:
            rendered = page.content()
            with open('/mnt/c/Aarav/fin_env/Dash/dev_tools/last_rendered_page.html', 'wb') as fh:
                fh.write(rendered.encode('utf-8'))
        except Exception:
            pass
        # Ensure the main app content loads
        try:
            page.wait_for_selector("body", timeout=15000)
        except Exception:
            pass

        results = []
        # Discover tab labels dynamically from the DOM using multiple selector fallbacks.
        # Special handling: some labels are injected via CSS ::before and not present as innerText.
        discovered = []
        try:
            anchors = page.query_selector_all('a.nav-link, .nav-link')
            for idx, a in enumerate(anchors):
                label = ''
                try:
                    # Try inner text first
                    txt = (a.inner_text() or '').strip()
                    if txt:
                        label = txt
                except Exception:
                    label = ''

                if not label:
                    # Try aria-label or title attributes
                    try:
                        label = a.get_attribute('aria-label') or a.get_attribute('title') or ''
                    except Exception:
                        label = ''

                if not label:
                    # Try reading computed ::before content via JS evaluate
                    try:
                        js = "(el) => { const s = window.getComputedStyle(el, '::before'); return s && s.content ? s.content.replace(/^\"|\"$/g, '') : ''; }"
                        label = page.evaluate(js, a) or ''
                        label = label.strip()
                    except Exception:
                        label = ''

                if not label:
                    label = f'tab_{idx+1}'

                discovered.append({'label': label, 'element': a})
        except Exception:
            discovered = []

        for t in discovered:
            try:
                # Click by ElementHandle when available (discovery path), otherwise use selector
                if t.get('element'):
                    try:
                        t['element'].click()
                    except Exception:
                        # fallback to clicking by index-based selector
                        pass
                else:
                    el = page.wait_for_selector(t['selector'], timeout=15000)
                    el.click()
                # Wait for one of several signals that the tab has meaningful content:
                #  - a table inside #tab-content
                #  - an iframe inside #tab-content
                #  - a plotly graph (div.js-plotly-plot)
                #  - OR the text length inside #tab-content grows beyond a small threshold
                try:
                    # Wait for an active tab pane (.tab-pane.active or with style/display) to contain content
                    page.wait_for_function(
                        "() => { const panes = Array.from(document.querySelectorAll('.tab-pane')); for (const p of panes) { const visible = p.offsetParent !== null || window.getComputedStyle(p).display !== 'none' || p.classList.contains('active'); if (!visible) continue; if (p.querySelector('table')) return true; if (p.querySelector('iframe')) return true; if (p.querySelector('.js-plotly-plot')) return true; const txt = p.innerText || ''; if (txt.replace(/\\s+/g, ' ').trim().length > 40) return true; } return false; }",
                        timeout=8000,
                    )
                except Exception:
                    # fallback short sleep to allow partial renders
                    page.wait_for_timeout(1200)
                safe_label = t['label'].replace(' ', '_').replace('/', '_')
                fname = os.path.join(OUT_DIR, f"tab_{safe_label}.png")
                page.screenshot(path=fname, full_page=True)
                # Save the per-tab HTML snapshot to help debug blank content cases
                try:
                    tab_html = page.content()
                    html_path = os.path.join(OUT_DIR, f"tab_{safe_label}.html")
                    with open(html_path, 'wb') as fh:
                        fh.write(tab_html.encode('utf-8'))
                except Exception:
                    pass
                results.append((t['label'], 'ok', fname))
            except Exception as e:
                # dump page HTML to help debugging selectors
                try:
                    html = page.content()
                    dump_path = '/tmp/tab_page_content.html'
                    with open(dump_path, 'wb') as fh:
                        fh.write(html.encode('utf-8'))
                except Exception:
                    dump_path = '<failed to write page content>'
                lbl = t.get('label') or t.get('selector') or '<unknown>'
                results.append((lbl, 'error', str(e), dump_path))
        browser.close()
        for r in results:
            print(r)


if __name__ == '__main__':
    main()

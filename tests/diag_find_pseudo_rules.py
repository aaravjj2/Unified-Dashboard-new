from playwright.sync_api import sync_playwright
import os, json

OUTDIR = os.path.join('test-artifacts', 'diag_nav_overlay')
os.makedirs(OUTDIR, exist_ok=True)

def run_find_rules():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width":1400, "height":900})
        page.goto('http://localhost:8050', wait_until='load')
        page.wait_for_selector('#dashboard-tabs', timeout=20000)

        rules = page.evaluate('''() => {
            const sheets = Array.from(document.styleSheets);
            const out = [];
            for (const s of sheets) {
                let href = s.href || null;
                try {
                    const cssRules = s.cssRules || [];
                    for (const r of cssRules) {
                        try {
                            const sel = r.selectorText || '';
                            const txt = r.cssText || '';
                            if (sel.includes('::before') || sel.includes(':before') || txt.includes('content:')) {
                                out.push({href: href, selector: sel, cssText: txt});
                            }
                        } catch (e) {
                            /* ignore individual rule errors */
                        }
                    }
                } catch (e) {
                    // Could be cross-origin stylesheet; record href only
                    out.push({href: href, selector: null, cssText: null, note: 'cannot access rules (maybe cross-origin)'});
                }
            }
            return out;
        }''')

        path = os.path.join(OUTDIR, 'pseudo_rules.json')
        with open(path, 'w') as f:
            json.dump(rules, f, indent=2)
        print('Wrote', path)
        browser.close()

if __name__ == '__main__':
    run_find_rules()

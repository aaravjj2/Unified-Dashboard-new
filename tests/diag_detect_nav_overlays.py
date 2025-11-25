from playwright.sync_api import sync_playwright
import os, json, time

ARTIFACT_DIR = os.path.join('test-artifacts', 'diag_nav_overlay')
os.makedirs(ARTIFACT_DIR, exist_ok=True)

def run_diagnostic():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width":1400, "height":600})
        page.goto('http://localhost:8050', wait_until='load')
        page.wait_for_selector('#dashboard-tabs', timeout=20000)
        # give additional time for client-side scripts/styles to settle
        page.wait_for_timeout(800)

        # capture screenshot
        ss_path = os.path.join(ARTIFACT_DIR, f"nav_screenshot_{int(time.time())}.png")
        page.screenshot(path=ss_path, full_page=False)

        # collect nav-link elements info
        info = []
        els = page.query_selector_all('#dashboard-tabs .nav-link')
        for i, el in enumerate(els):
            rect = el.bounding_box() or {}
            txt = el.inner_text().strip()
            html = el.inner_html()
            # computed styles and pseudo-element content
            comp = page.evaluate("(e)=>{const s=getComputedStyle(e); return {whiteSpace:s.whiteSpace, overflow:s.overflow, display:s.display, position:s.position};}", el)
            before = page.evaluate("(e)=>{const s=getComputedStyle(e, '::before'); return {content: s.content, display: s.display, width: s.width, height: s.height, left: s.left, right: s.right};}", el)
            after = page.evaluate("(e)=>{const s=getComputedStyle(e, '::after'); return {content: s.content, display: s.display, width: s.width, height: s.height, left: s.left, right: s.right};}", el)

            info.append({
                'index': i,
                'text': txt,
                'html': html,
                'rect': rect,
                'computed': comp,
                'pseudo_before': before,
                'pseudo_after': after
            })

        # also capture other elements that could overlay (nav container ::before/after, .nav-item)
        container = page.query_selector('#dashboard-tabs')
        cont_before = page.evaluate("(e)=>{const s=getComputedStyle(e, '::before'); return {content: s.content, display: s.display, width: s.width, height: s.height};}", container)
        cont_after = page.evaluate("(e)=>{const s=getComputedStyle(e, '::after'); return {content: s.content, display: s.display, width: s.width, height: s.height};}", container)

        out = {
            'screenshot': ss_path,
            'nav_info': info,
            'container_before': cont_before,
            'container_after': cont_after
        }

        with open(os.path.join(ARTIFACT_DIR, 'diag.json'), 'w') as f:
            json.dump(out, f, indent=2)

        print('Wrote artifacts to', ARTIFACT_DIR)
        browser.close()

if __name__ == '__main__':
    run_diagnostic()

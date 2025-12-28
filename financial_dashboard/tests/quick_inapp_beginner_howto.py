from playwright.sync_api import sync_playwright
import os, sys, time

URL = "http://localhost:8051"
OUT = "screenshots/research_lab/beginner_guide_inapp.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(URL, wait_until="load", timeout=60000)

    # Use hidden E2E button to open Research Lab reliably
    try:
        page.click('#e2e-open-tab-research_lab', timeout=5000)
    except Exception:
        # fallback: click tab by text
        try:
            page.click('button:has-text("Research Lab")', timeout=5000)
        except Exception:
            pass

    # Give the app a moment to switch tabs and render
    page.wait_for_timeout(1500)
    # Scroll to top/header
    page.evaluate('window.scrollTo(0, 0)')

    # Click the accordion toggle to expand the guide (button inside header)
    try:
        # The accordion toggle uses its own button; try clicking header by finding any button with 'Beginner' in text
        # Programmatically expand the Beginner's Guide accordion by finding a header/button with 'beginner' text
        page.evaluate("""
        (() => {
            try {
                const all = Array.from(document.querySelectorAll('button, h2, div'));
                for (const el of all) {
                    const txt = (el.innerText || '').toLowerCase();
                    if (txt.includes("beginner") && txt.includes("guide")) {
                        // try to find a button ancestor
                        let btn = el.closest('button') || el.querySelector('button') || document.querySelector('button:contains("Beginner")');
                        if (btn) { btn.click(); return true; }
                        // fallback: click the element directly
                        el.click();
                        return true;
                    }
                }
            } catch(e) { return false; }
            return false;
        })();
        """)
    except Exception:
        pass

    # Click the Open Full Guide button (wait for it to appear)
    page.wait_for_selector('#rl-beginner-open-howto', timeout=10000)
    page.click('#rl-beginner-open-howto')

    # Wait for modal and content
    page.wait_for_selector('#rl-beginner-howto-modal .modal-dialog', timeout=8000)
    page.wait_for_selector('#rl-beginner-howto-md', timeout=8000)
    time.sleep(0.3)

    page.screenshot(path=OUT, full_page=False)
    print('✅ Saved in-app screenshot to', OUT)
    browser.close()

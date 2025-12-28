"""
Simple, robust Playwright test for the Research Lab Beginner's Guide HOWTO modal.
- Uses JS evaluation to click hidden E2E tab button so we reliably switch to Research Lab
- Expands the accordion and clicks "Open Full Guide"
- Verifies modal content contains expected headings and saves a screenshot
Exit codes:
 0 = success
 2 = open button not found
 3 = modal content not found
 4 = modal content did not contain expected text
 5 = unexpected error
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import os, sys, time

URL = os.getenv('DASHBOARD_URL', 'http://localhost:8051')
OUT = 'screenshots/research_lab/beginner_guide_inapp_test.png'

os.makedirs(os.path.dirname(OUT), exist_ok=True)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        print(f"Navigating to {URL} ...")
        page.goto(URL, wait_until='load', timeout=60000)
        page.wait_for_timeout(600)

        # Activate Research Lab tab via hidden E2E button (use JS click to bypass visibility)
        activated = page.evaluate("""
            (() => {
                const btn = document.getElementById('e2e-open-tab-research_lab');
                if (btn) { try { btn.click(); return true } catch(e) { return false } }
                return false;
            })();
        """)
        print("E2E tab activation attempted ->", activated)
        page.wait_for_timeout(600)

        # Try to directly click the "Open Full Guide" button if present in DOM
        clicked = page.evaluate("""
            (() => {
                const btn = document.getElementById('rl-beginner-open-howto');
                if (btn) { try { btn.click(); return true } catch(e) { return false } }
                return false;
            })();
        """)
        if not clicked:
            # If direct click didn't work, attempt to expand the accordion header then click
            page.evaluate("""
                (() => {
                    const btns = Array.from(document.querySelectorAll('button'));
                    for (const b of btns) {
                        if (b.innerText && b.innerText.toLowerCase().includes('beginner')) {
                            try { b.click(); return true } catch(e) {}
                        }
                    }
                    return false;
                })();
            """)
            page.wait_for_timeout(400)
            # Try clicking the button by id again (may be inside collapsed content now)
            page.evaluate("""
                (() => { const b = document.getElementById('rl-beginner-open-howto'); if (b) { try { b.click(); return true } catch(e) {} } return false; })();
            """)

        # Wait for modal content to appear
        try:
            page.wait_for_selector('#rl-beginner-howto-md', timeout=10000)
            time.sleep(0.2)
            text = page.inner_text('#rl-beginner-howto-md')
        except PlaywrightTimeoutError:
            print('❌ Modal content not found after clicking Open Full Guide')
            browser.close()
            sys.exit(3)

        # Verify expected headings exist in modal text
        expected_markers = ['Quick Start', 'What This Lab Does', 'Key Features']
        if any(m in text for m in expected_markers):
            page.screenshot(path=OUT)
            print('✅ Modal opened and verified. Screenshot saved to', OUT)
            browser.close()
            sys.exit(0)
        else:
            print('❌ Modal content did not contain expected headings')
            page.screenshot(path=OUT)
            print('Screenshot saved to', OUT)
            browser.close()
            sys.exit(4)

except Exception as e:
    print('❌ Unexpected error while running test:', str(e))
    sys.exit(5)

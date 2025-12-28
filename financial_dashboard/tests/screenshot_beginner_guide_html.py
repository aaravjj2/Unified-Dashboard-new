from playwright.sync_api import sync_playwright
import os

HTML_PATH = '/tmp/research_lab_beginner_guide.html'
OUT_PNG = 'screenshots/research_lab/beginner_guide_expanded.png'

os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)

if not os.path.exists(HTML_PATH):
    print('❌ HTML preview not found:', HTML_PATH)
    raise SystemExit(2)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1200, "height": 900})
    page.goto('file://' + HTML_PATH)
    # Wait a bit for styles to settle
    page.wait_for_timeout(300)
    page.screenshot(path=OUT_PNG, full_page=True)
    print('✅ Screenshot saved:', OUT_PNG)
    browser.close()

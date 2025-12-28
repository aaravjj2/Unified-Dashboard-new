from playwright.sync_api import sync_playwright
import os
import sys

URL = "http://localhost:8051"
OUT_DIR = "screenshots/research_lab"
OUT_FILE = os.path.join(OUT_DIR, "beginner_guide_expanded.png")

os.makedirs(OUT_DIR, exist_ok=True)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 900})
        page.goto(URL, wait_until="networkidle", timeout=15000)

        # Wait for Research Lab content container to be present
        page.wait_for_selector('#rl-alphasim-content', timeout=15000)

        # Find the Beginner's Guide accordion button and click it
        # Match partial text to be robust against emojis
        locator = page.locator('button:has-text("Beginner\'s Guide to Research Lab")').first
        if locator.count() == 0:
            # try without escaped apostrophe
            locator = page.locator('button:has-text("Beginner")').first

        if locator.count() == 0:
            print("❌ Beginner guide accordion button not found on page.")
            page.screenshot(path=OUT_FILE)
            browser.close()
            sys.exit(2)

        locator.click()

        # Wait for the markdown content to appear
        try:
            page.wait_for_selector('text="What This Lab Does"', timeout=5000)
        except Exception:
            # fallback: wait for any accordion body
            page.wait_for_selector('.accordion-body', timeout=5000)

        # Give a small pause for animations
        page.wait_for_timeout(500)

        page.screenshot(path=OUT_FILE, full_page=False)
        print(f"✅ Screenshot saved: {OUT_FILE}")
        browser.close()
except Exception as e:
    print("❌ Error during quick check:", e)
    sys.exit(1)

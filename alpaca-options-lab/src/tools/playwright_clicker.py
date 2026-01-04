from playwright.sync_api import sync_playwright
import time

BASE = "http://localhost:8053"
OUT_SCREEN = "tests/e2e_screenshots/command_workspace_playwright.png"

def run_clicker():
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as e:
            print('Could not launch Chromium:', e)
            return 2

        context = browser.new_context(viewport={"width":1920, "height":1080})
        page = context.new_page()
        try:
            page.goto(BASE, timeout=60000)
            page.wait_for_load_state('networkidle', timeout=30000)
        except Exception as e:
            print('Navigation failed:', e)
            browser.close()
            return 3

        # Try to click the Command tab
        try:
            cmd = page.locator("text=Command").first
            if cmd and cmd.is_visible():
                cmd.click()
                page.wait_for_timeout(1000)
        except Exception as e:
            print('Command tab click failed:', e)

        # Wait for command workspace
        try:
            page.wait_for_selector('#command-workspace', timeout=10000)
            print('Command workspace detected')
        except Exception as e:
            print('Command workspace not detected:', e)

        # Click a visible button
        try:
            btn = page.locator('button:visible').first
            if btn and btn.is_enabled():
                btn.click()
                page.wait_for_timeout(500)
                print('Clicked first visible button')
        except Exception as e:
            print('Button click failed:', e)

        # Take screenshot
        try:
            page.screenshot(path=OUT_SCREEN, full_page=True)
            print('Screenshot saved to', OUT_SCREEN)
        except Exception as e:
            print('Screenshot failed:', e)

        browser.close()
        return 0

if __name__ == '__main__':
    exit_code = run_clicker()
    raise SystemExit(exit_code)

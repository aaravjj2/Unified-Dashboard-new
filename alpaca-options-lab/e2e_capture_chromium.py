import asyncio
import os
from playwright.async_api import async_playwright

OUTPUT_DIR = "proof_shots"
URL = "http://localhost:8053"

async def run():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    chromium_path = os.path.expanduser("~/.cache/ms-playwright/chromium-1194/chrome-linux/chrome")
    print(f"Using chromium at: {chromium_path}")

    async with async_playwright() as pw:
        browser = None
        try:
            browser = await pw.chromium.launch(executable_path=chromium_path, headless=False, args=['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage'])
            context = await browser.new_context(viewport={"width":1280, "height":900})
            page = await context.new_page()
            print(f"Navigating to {URL}")
            await page.goto(URL, timeout=60000)
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=os.path.join(OUTPUT_DIR, '01_dashboard_initial.png'), full_page=True)
            print("Captured initial dashboard")

            # Capture workspaces
            for path in ["/scanner", "/strategy", "/command", "/admin"]:
                await page.goto(URL + path, timeout=60000)
                await page.wait_for_load_state('networkidle')
                name = path.strip('/').lower() or 'root'
                fp = os.path.join(OUTPUT_DIR, f'02_workspace_{name}.png')
                await page.screenshot(path=fp, full_page=True)
                print(f"Captured {path} -> {fp}")

            # Capture Greeks panel area by selector if present
            try:
                await page.goto(URL + '/strategy', timeout=60000)
                await page.wait_for_selector("#greeks-chart", timeout=5000)
                await page.screenshot(path=os.path.join(OUTPUT_DIR, '03_greeks_panel.png'))
                print("Captured greeks panel screenshot")
            except Exception as e:
                print(f"Greeks panel selector not found: {e}")

        except Exception as e:
            print(f"Error during capture: {e}")
        finally:
            if browser:
                await browser.close()

if __name__ == '__main__':
    asyncio.run(run())

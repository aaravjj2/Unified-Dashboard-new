
import asyncio
from playwright.async_api import async_playwright
import time

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Capture console logs
        page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))

        await page.goto("http://127.0.0.1:8050/")
        print("Navigated to page.")

        # Click the Market Trends tab if it's not already active
        try:
            await page.click('text="Market Trends"', timeout=5000)
            print("Clicked 'Market Trends' tab.")
        except Exception as e:
            print(f"Could not click Market Trends tab, assuming it is active. Error: {e}")

        # Wait for the initial table to potentially load
        time.sleep(5)

        # Click the run button
        await page.click("#run-btn")
        print("Clicked 'Run Full Analysis' button.")

        # Wait for job to start and potentially finish
        time.sleep(10)

        # Print final page content
        content = await page.content()
        print("\n--- FINAL PAGE CONTENT ---")
        print(content)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

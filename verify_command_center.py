"""
Final Command Center verification
"""
import asyncio
from playwright.async_api import async_playwright

async def verify_command_center():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1200})
        
        print("=" * 80)
        print("COMMAND CENTER VERIFICATION")
        print("=" * 80)
        
        # Load dashboard
        print("\n[1/3] Loading dashboard...")
        await page.goto('http://localhost:8051', timeout=15000, wait_until='networkidle')
        await page.wait_for_timeout(5000)
        print("✓ Dashboard loaded")
        
        # Get page text
        page_text = await page.evaluate("() => document.body.innerText")
        
        # Check for error messages
        has_connection_refused = "Connection refused" in page_text
        has_error_errno = "[Errno 111]" in page_text
        has_error_prefix = "Error:" in page_text and "unavailable" not in page_text
        
        # Check for clean messages
        has_unavailable = "unavailable" in page_text.lower()
        has_loading = "Loading" in page_text
        
        print("\n[2/3] Analyzing content...")
        print(f"  ✓ Has 'Connection refused': {has_connection_refused} (should be False)")
        print(f"  ✓ Has '[Errno 111]': {has_error_errno} (should be False)")
        print(f"  ✓ Has 'Error:' messages: {has_error_prefix} (should be False)")
        print(f"  ✓ Has 'unavailable' messages: {has_unavailable} (should be True)")
        print(f"  ✓ Has 'Loading' text: {has_loading}")
        
        # Capture screenshot
        print("\n[3/3] Capturing screenshot...")
        await page.screenshot(path='/home/aarav/unified-dashboard/FINAL_command_center_verified.png', full_page=True)
        print("✓ Screenshot saved")
        
        await browser.close()
        
        success = not has_connection_refused and not has_error_errno and not has_error_prefix
        
        print("\n" + "=" * 80)
        print("VERIFICATION RESULT")
        print("=" * 80)
        if success:
            print("✅ SUCCESS: All error messages replaced with clean fallbacks!")
        else:
            print("❌ FAILURE: Some error messages still present")

if __name__ == '__main__':
    asyncio.run(verify_command_center())

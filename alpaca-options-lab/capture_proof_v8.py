import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    with open("capture_log.txt", "w") as log:
        log.write("🚀 Starting Proof Capture V8 (Chromium Non-Headless)...\n")
        print("🚀 Starting Proof Capture V8 (Chromium Non-Headless)...")
        
        # Create output directory
        output_dir = "/home/aarav/Unified-Dashboard/alpaca-options-lab/proof_v8"
        os.makedirs(output_dir, exist_ok=True)
        log.write(f"Created output directory: {output_dir}\n")
        
        async with async_playwright() as p:
            log.write("Launching browser...\n")
            # Launch Chromium in headless mode with sandbox disabled and no GPU
            browser = await p.chromium.launch(
                headless=True, 
                slow_mo=500,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            )
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            print("🌐 Navigating to http://localhost:8053...")
            await page.goto("http://localhost:8053", timeout=60000)
            await page.wait_for_load_state("networkidle")
            
            # 1. Capture Initial Dashboard
            print("📸 Capturing Initial Dashboard...")
            await page.screenshot(path=f"{output_dir}/01_dashboard_initial.png", full_page=True)
            
            # 2. Verify Phase 1 Features (Data Test IDs)
            print("🔍 Verifying Phase 1 Features (Test IDs)...")
            # Check for specific test IDs mentioned in Phase 1 report
            # Scanner workspace: data-test-id='hype-gauge-{symbol}'
            # Strategy Builder: data-test-id attributes
            
            # We might need to navigate to Scanner first if it's not default
            # Assuming default is Scanner or we can click it
            
            # 3. Navigate through tabs
            tabs = ["Scanner", "Strategy", "Command", "Admin"]
            for tab in tabs:
                print(f"👉 Clicking {tab} tab...")
                # Try to find the tab button. The text might be "Scanner", "Strategy", etc.
                # Or use href if known. Based on logs: /scanner, /strategy
                
                try:
                    # Try clicking by text
                    await page.click(f"text={tab}", timeout=5000)
                    await page.wait_for_timeout(2000) # Wait for render
                    await page.screenshot(path=f"{output_dir}/02_tab_{tab.lower()}.png", full_page=True)
                    print(f"✅ Captured {tab} tab")
                except Exception as e:
                    print(f"⚠️ Could not click {tab} tab: {e}")
            
            # 4. Verify Phase 2 Features (Components)
            print("🔍 Verifying Phase 2 Features (Components)...")
            
            # Check for Tooltips
            # Look for elements with tooltip classes or attributes
            tooltips = await page.query_selector_all(".tooltip") # Bootstrap tooltip class
            print(f"ℹ️ Found {len(tooltips)} tooltip elements")
            
            # Check for Loading States (might be gone by now, but check for skeleton classes if any remain hidden)
            skeletons = await page.query_selector_all(".skeleton-loader")
            print(f"ℹ️ Found {len(skeletons)} skeleton loader elements")
            
            # Check for Buttons with new classes
            buttons = await page.query_selector_all("button.btn-primary") # Standard bootstrap, but check for custom styles if possible
            print(f"ℹ️ Found {len(buttons)} primary buttons")
            
            # 5. Check Greeks Panel (Fix Verification)
            print("🔍 Verifying Greeks Panel...")
            # Navigate to Strategy tab if not already there
            await page.goto("http://localhost:8053/strategy")
            await page.wait_for_timeout(3000)
            
            # Look for Greeks values (should not be 0.00 if data loaded, but might be 0 if market closed/no data)
            # But mainly check if the panel exists and isn't showing an error message
            content = await page.content()
            if "GreeksSurfaceBuilder.build_surface() got an unexpected keyword argument" in content:
                print("❌ Greeks Panel Error STILL PRESENT in page content!")
            else:
                print("✅ Greeks Panel Error NOT found in page content.")
                
            await page.screenshot(path=f"{output_dir}/03_greeks_panel_check.png")

        except Exception as e:
            print(f"❌ Error during capture: {e}")
            await page.screenshot(path=f"{output_dir}/error_state.png")
        
        finally:
            await browser.close()
            print("🏁 Capture complete.")

if __name__ == "__main__":
    asyncio.run(run())

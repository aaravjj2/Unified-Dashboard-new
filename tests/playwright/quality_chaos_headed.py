"""
Phase 12 Chaos Testing: Playwright Headed Audit
===============================================
Scenario: "Poison Pill" Injection
Goal: Verify Dashboard handles malformed server responses gracefully.
Steps:
1. Load Dashboard.
2. Intercept `/_dash-update-component` requests.
3. Inject garbage JSON or non-JSON response (Poison Pill).
4. Assert UI does NOT blank out (Crash).
5. Assert "Data Error" or "Server Error" toast/alert is displayed.
"""

import pytest
from playwright.sync_api import sync_playwright, expect
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DASHBOARD_URL = "http://127.0.0.1:8053"

def test_poison_pill_resilience():
    with sync_playwright() as p:
        # Launch Headful Chromium as requested
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # 1. Load Dashboard
            logger.info("Step 1: Loading Dashboard...")
            page.goto(DASHBOARD_URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            expect(page.locator("body")).not_to_be_empty()
            logger.info("Dashboard loaded.")

            # 2. Setup Poison Pill Interception
            # Intercept the next update call (triggered by interval or interaction)
            logger.info("Step 2: Arming Poison Pill...")
            
            def handle_route(route):
                if "options-load-btn" in route.request.post_data or "interval" in route.request.post_data:
                    logger.info("💊 Injecting Poison Pill into " + route.request.url)
                    route.fulfill(
                        status=200,
                        content_type="application/json",
                        body='{"response": "TOXIC_DATA_GARBAGE_JSON_STRUCTURE_MISMATCH"}'
                    )
                else:
                    route.continue_()

            # Enable routing
            page.route("**/_dash-update-component", handle_route)

            # 3. Trigger an update (Wait or Interact)
            # Find a button to click to force a request, or wait for interval
            logger.info("Step 3: Triggering update...")
            # Try clicking refresh if available, or just wait for interval
            # The dashboard has intervals enabled.
            time.sleep(5) 
            
            # 4. Assert Resilience
            logger.info("Step 4: Verifying Resilience...")
            
            # A. UI should still be visible (not blank body)
            expect(page.locator("#dashboard-tabs")).to_be_visible()
            
            # B. Check for Error Toast
            # Dash standard error is often in specific divs
            # Or we look for our custom "Data Error" toast if required
            # The requirement: "Verify UI displays 'Data Error' toast"
            
            # Check for Dash Error Overlay (we want to suppress this or handle it)
            # Or check for a specific Toast
            
            # For Phase 12, we expect a robust handling.
            # If the dashboard crashes to white screen, it fails.
            
            # Let's check if the "Reconnecting" badge from Step 3 appears? No, this is data error.
            # We look for a toast.
            
            # If we haven't implemented the toast yet, this test will FAIL.
            # Then we Auto-Repair.
            
            # Search for "Error" or "Exception" on screen text
            # But "Data Error" specifically.
            found_error = False
            try:
                # Look for toast-like elements or text
                expect(page.locator("text=Data Error")).to_be_visible(timeout=5000)
                found_error = True
            except:
                logger.warning("❌ 'Data Error' Toast NOT found.")
            
            if not found_error:
                # Determine if it crashed
                if page.locator("._dash-error-display").is_visible():
                     logger.info("Found standard Dash Error Display (Dev Mode).")
                     # In prod, this might be suppressed.
                
                # We assert failure here to trigger the Auto-Repair
                raise AssertionError("UI did not show 'Data Error' toast after Poison Pill.")

            logger.info("✅ Test Passed: Poison Pill handled gracefully.")

        except Exception as e:
            logger.error(f"Test Failed: {e}")
            page.screenshot(path="reports/phase12_quality/screenshots/poison_pill_failure.png")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    test_poison_pill_resilience()

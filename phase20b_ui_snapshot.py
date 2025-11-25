#!/usr/bin/env python3
"""
Phase 20B UI Snapshot Test
Capture screenshots of Azure ML Lab tab to verify display callbacks working
"""
import sys
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

def test_azure_ml_ui():
    """Test Azure ML Lab UI with screenshots"""
    print("=" * 60)
    print("PHASE 20B UI SNAPSHOT TEST")
    print("Verify predictions table and metrics display data from PostgreSQL")
    print("=" * 60)
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            # Navigate directly to Azure ML Lab page
            print("\n[1/5] Loading Azure ML Lab page...")
            page.goto('http://dash_app:8050/azure-ml-lab', wait_until='networkidle', timeout=30000)
            time.sleep(3)
            print("✅ Azure ML Lab page loaded")
            
            # Take screenshot of initial state
            page.screenshot(path='/app/phase20b_initial.png', full_page=True)
            print("✅ Screenshot saved: phase20b_initial.png")
            
            # Check if predictions table is visible
            print("\n[2/5] Checking predictions table...")
            try:
                table = page.locator('table').first
                if table.is_visible():
                    print("✅ Predictions table found")
                    
                    # Check for "No predictions available" message
                    page_content = page.content()
                    if "No predictions available" in page_content:
                        print("⚠️ WARNING: Table shows 'No predictions available'")
                        print("   (Database has 13 predictions but UI not displaying them)")
                    elif "Showing" in page_content and "predictions from PostgreSQL" in page_content:
                        print("✅ SUCCESS: Database footer found!")
                        print("   (UI is reading from PostgreSQL database)")
                    else:
                        print("⚠️ Table visible but status unclear")
                else:
                    print("❌ Predictions table not visible")
            except Exception as e:
                print(f"❌ Error checking table: {e}")
            
            # Click Run Prediction button
            print("\n[3/5] Clicking Run Prediction button...")
            try:
                run_btn = page.locator('#azure-ml-run-btn, button:has-text("Run Prediction")')
                if run_btn.count() > 0:
                    run_btn.first.click()
                    print("✅ Run Prediction button clicked")
                    time.sleep(5)  # Wait for prediction to complete
                    
                    # Take screenshot after prediction
                    page.screenshot(path='/app/phase20b_after_prediction.png', full_page=True)
                    print("✅ Screenshot saved: phase20b_after_prediction.png")
                    
                    # Check if table updated
                    page_content = page.content()
                    if "Showing" in page_content and "predictions from PostgreSQL" in page_content:
                        print("✅ SUCCESS: Table updated with PostgreSQL data!")
                    else:
                        print("⚠️ Table may not have updated")
                else:
                    print("❌ Run Prediction button not found")
            except Exception as e:
                print(f"❌ Error clicking Run Prediction: {e}")
            
            # Check performance metrics
            print("\n[4/5] Checking performance metrics...")
            try:
                page_content = page.content()
                if "Metrics from PostgreSQL database" in page_content:
                    print("✅ SUCCESS: Performance metrics footer found!")
                    print("   (Metrics reading from ml_prediction_runs table)")
                elif "Total Prediction Runs" in page_content:
                    print("⚠️ Metrics visible but database footer not found")
                else:
                    print("❌ Metrics not visible")
            except Exception as e:
                print(f"❌ Error checking metrics: {e}")
            
            print("\n" + "=" * 60)
            print("TEST COMPLETE")
            print("Screenshots saved:")
            print("  - /app/phase20b_initial.png")
            print("  - /app/phase20b_after_prediction.png")
            print("=" * 60)
            
        except PlaywrightTimeout as e:
            print(f"\n❌ TIMEOUT: {e}")
            page.screenshot(path='/app/phase20b_timeout.png')
            return 1
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            page.screenshot(path='/app/phase20b_error.png')
            return 1
        finally:
            browser.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(test_azure_ml_ui())

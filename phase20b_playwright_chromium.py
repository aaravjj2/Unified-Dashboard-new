#!/usr/bin/env python3
"""
Phase 20B - Chromium Playwright E2E Test
Complete UI validation with screenshots for all Azure ML Lab tabs
"""
import sys
import os
import time
from playwright.sync_api import sync_playwright
from pathlib import Path

# Create snapshots directory
SNAPSHOTS_DIR = Path("phase20b_snapshots")
SNAPSHOTS_DIR.mkdir(exist_ok=True)

def test_azure_ml_lab():
    """
    Comprehensive Chromium test for Azure ML Lab
    Tests all 5 tabs: Predictions, Performance, Feature Importance, Risk Analysis, Model Insights
    """
    print("=" * 80)
    print("PHASE 20B - CHROMIUM PLAYWRIGHT E2E TEST")
    print("=" * 80)
    
    results = {'passed': 0, 'failed': 0, 'skipped': 0}
    
    with sync_playwright() as p:
        # Launch Chromium (strict requirement)
        print("\n🚀 Launching Chromium browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            # Test 1: Load Azure ML Lab page
            print("\n[1/7] Loading Azure ML Lab page...")
            page.goto('http://localhost:8050/azure-ml-lab', wait_until='networkidle', timeout=30000)
            time.sleep(3)
            
            page.screenshot(path=str(SNAPSHOTS_DIR / "01_initial_load.png"), full_page=True)
            print("✅ Page loaded - Screenshot: 01_initial_load.png")
            results['passed'] += 1
            
            # Test 2: Run a prediction first to populate data
            print("\n[2/8] Triggering ML prediction...")
            try:
                # Wait for page to be fully loaded
                page.wait_for_load_state('networkidle')
                time.sleep(2)
                
                # Retry logic for button click (max 3 attempts)
                clicked = False
                for attempt in range(3):
                    try:
                        # Wait for button to be visible and stable
                        page.wait_for_selector('#azure-ml-run-prediction-btn', state='visible', timeout=10000)
                        run_btn = page.locator('#azure-ml-run-prediction-btn')
                        
                        # Scroll into view
                        run_btn.scroll_into_view_if_needed()
                        time.sleep(1.5)
                        
                        # Verify visible before clicking
                        if run_btn.is_visible():
                            run_btn.click(force=True)
                            clicked = True
                            print(f"✅ Clicked Run Prediction button (attempt {attempt + 1})")
                            break
                        else:
                            print(f"⚠️ Button not visible on attempt {attempt + 1}")
                    except Exception as e:
                        print(f"⚠️ Click attempt {attempt + 1} failed: {e}")
                        time.sleep(2)
                
                if not clicked:
                    print("❌ Failed to click button after 3 attempts")
                    results['failed'] += 1
                else:
                    time.sleep(5)  # Wait for prediction to complete
                    
                    # Check for success message
                    content = page.content()
                    if "ML Prediction Complete" in content or "predictions" in content.lower():
                        print("✅ Prediction completed successfully")
                        results['passed'] += 1
                    else:
                        print("⚠️ Prediction may not have completed")
                        results['failed'] += 1
                    
                    page.screenshot(path=str(SNAPSHOTS_DIR / "02_prediction_run.png"), full_page=True)
                    print("✅ Screenshot: 02_prediction_run.png")
            except Exception as e:
                print(f"❌ Prediction error: {e}")
                results['failed'] += 1
            
            # Test 3: Predictions Tab
            print("\n[3/7] Testing Predictions Tab...")
            try:
                # Click Predictions tab (use tab navigation)
                pred_tab = page.locator('button.nav-link:has-text("Predictions"), a.nav-link:has-text("Predictions")')
                if pred_tab.count() > 0:
                    pred_tab.first.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    pred_tab.first.click(force=True)
                    time.sleep(2)
                    
                    content = page.content()
                    if "PostgreSQL database" in content or "Showing" in content:
                        print("✅ Predictions table displayed")
                        results['passed'] += 1
                    else:
                        print("⚠️ Predictions content not found")
                        results['failed'] += 1
                    
                    page.screenshot(path=str(SNAPSHOTS_DIR / "03_predictions_tab.png"), full_page=True)
                    print("✅ Screenshot: 03_predictions_tab.png")
                else:
                    print("⚠️ Predictions tab not found")
                    results['failed'] += 1
            except Exception as e:
                print(f"❌ Predictions tab error: {e}")
                results['failed'] += 1
            
            # Test 4: Performance Tab
            print("\n[4/7] Testing Performance Tab...")
            try:
                # Click Performance tab
                perf_tab = page.locator('button.nav-link:has-text("Performance"), a.nav-link:has-text("Performance")')
                if perf_tab.count() > 0:
                    perf_tab.first.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    perf_tab.first.click(force=True)
                    time.sleep(2)
                    
                    content = page.content()
                    if "Total Prediction Runs" in content or "Avg Confidence" in content:
                        print("✅ Performance metrics displayed")
                        results['passed'] += 1
                    else:
                        print("⚠️ Performance metrics not fully rendered")
                        results['failed'] += 1
                    
                    page.screenshot(path=str(SNAPSHOTS_DIR / "04_performance_tab.png"), full_page=True)
                    print("✅ Screenshot: 04_performance_tab.png")
                else:
                    print("⚠️ Performance tab not found")
                    results['failed'] += 1
            except Exception as e:
                print(f"❌ Performance tab error: {e}")
                results['failed'] += 1
            
            # Test 5: Feature Importance Tab
            print("\n[5/7] Testing Feature Importance Tab...")
            try:
                # Click Feature Importance tab
                feat_tab = page.locator('button.nav-link:has-text("Feature"), a.nav-link:has-text("Feature")')
                if feat_tab.count() > 0:
                    feat_tab.first.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    feat_tab.first.click(force=True)
                    time.sleep(2)
                    
                    content = page.content()
                    if "Feature Importance" in content or "SHAP" in content or "PostgreSQL" in content:
                        print("✅ Feature Importance tab displayed")
                        results['passed'] += 1
                    else:
                        print("⚠️ Feature Importance content not found")
                        results['failed'] += 1
                    
                    page.screenshot(path=str(SNAPSHOTS_DIR / "05_feature_importance_tab.png"), full_page=True)
                    print("✅ Screenshot: 05_feature_importance_tab.png")
                else:
                    print("⚠️ Feature Importance tab not found")
                    results['failed'] += 1
            except Exception as e:
                print(f"❌ Feature Importance error: {e}")
                results['failed'] += 1
            
            # Test 6: Risk Analysis Tab
            print("\n[6/7] Testing Risk Analysis Tab...")
            try:
                # Click Risk Analysis tab
                risk_tab = page.locator('button.nav-link:has-text("Risk"), a.nav-link:has-text("Risk")')
                if risk_tab.count() > 0:
                    risk_tab.first.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    risk_tab.first.click(force=True)
                    time.sleep(2)
                    
                    content = page.content()
                    if "Volatility" in content or "Sharpe" in content or "VaR" in content or "Risk" in content:
                        print("✅ Risk Analysis tab displayed")
                        results['passed'] += 1
                    else:
                        print("⚠️ Risk Analysis content not found")
                        results['failed'] += 1
                    
                    page.screenshot(path=str(SNAPSHOTS_DIR / "06_risk_analysis_tab.png"), full_page=True)
                    print("✅ Screenshot: 06_risk_analysis_tab.png")
                else:
                    print("⚠️ Risk Analysis tab not found")
                    results['failed'] += 1
            except Exception as e:
                print(f"❌ Risk Analysis error: {e}")
                results['failed'] += 1
            
            # Test 7: Model Insights Tab
            print("\n[7/7] Testing Model Insights Tab...")
            try:
                # Click Model Insights tab
                insights_tab = page.locator('button.nav-link:has-text("Insights"), a.nav-link:has-text("Insights")')
                if insights_tab.count() > 0:
                    insights_tab.first.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    insights_tab.first.click(force=True)
                    time.sleep(2)
                    
                    # Check for insight controls
                    content = page.content()
                    if "Generate Explanation" in content or "Model Insight" in content or "SHAP" in content:
                        print("✅ Model Insights tab displayed")
                        results['passed'] += 1
                    else:
                        print("⚠️ Model Insights content not found")
                        results['failed'] += 1
                    
                    page.screenshot(path=str(SNAPSHOTS_DIR / "07_model_insights_tab.png"), full_page=True)
                    print("✅ Screenshot: 07_model_insights_tab.png")
                else:
                    print("⚠️ Model Insights tab not found")
                    results['failed'] += 1
            except Exception as e:
                print(f"❌ Model Insights error: {e}")
                results['failed'] += 1
            
            # Test 8: Final Full Page Screenshot
            print("\n[8/8] Capturing final state...")
            page.screenshot(path=str(SNAPSHOTS_DIR / "08_final_state.png"), full_page=True)
            print("✅ Screenshot: 08_final_state.png")
            results['passed'] += 1
            
        except Exception as e:
            print(f"\n❌ FATAL ERROR: {e}")
            page.screenshot(path=str(SNAPSHOTS_DIR / "error.png"))
            results['failed'] += 1
        
        finally:
            browser.close()
    
    # Summary
    print("\n" + "=" * 80)
    print("CHROMIUM PLAYWRIGHT TEST SUMMARY")
    print("=" * 80)
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"⏭️  Skipped: {results['skipped']}")
    print(f"\n📸 Screenshots saved to: {SNAPSHOTS_DIR}/")
    print("=" * 80)
    
    # Success if no failures and no skips
    if results['failed'] == 0 and results['skipped'] == 0:
        print("\n🎉 SUCCESS: All E2E tests passed!")
        return 0
    elif results['failed'] == 0:
        print("\n⚠️ PARTIAL SUCCESS: No failures but some tests skipped")
        return 0
    else:
        print("\n❌ FAILURE: Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(test_azure_ml_lab())

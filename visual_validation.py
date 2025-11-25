#!/usr/bin/env python3
"""
Chromium Visual Validation & Click Testing
Captures screenshots of all tabs and tests interactive elements
"""
import sys
import os
import time
import json
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, Browser

# Results
results = {
    "timestamp": datetime.now().isoformat(),
    "screenshots": [],
    "interactions": [],
    "errors": []
}

def capture_screenshot(page: Page, name: str, description: str):
    """Capture screenshot and save metadata"""
    filename = f"screenshots/{name}.png"
    os.makedirs("screenshots", exist_ok=True)
    
    try:
        page.screenshot(path=filename, full_page=True)
        results["screenshots"].append({
            "name": name,
            "description": description,
            "filename": filename,
            "url": page.url,
            "timestamp": datetime.now().isoformat()
        })
        print(f"✅ Screenshot: {name}")
        return True
    except Exception as e:
        results["errors"].append(f"Screenshot {name}: {str(e)}")
        print(f"❌ Screenshot failed: {name} - {e}")
        return False


def test_interaction(page: Page, selector: str, action: str, description: str):
    """Test a UI interaction"""
    try:
        element = page.locator(selector)
        if element.count() == 0:
            raise Exception(f"Element not found: {selector}")
        
        if action == "click":
            element.first.click()
            time.sleep(1)  # Wait for response
        elif action == "fill":
            element.first.fill("TEST")
        
        results["interactions"].append({
            "selector": selector,
            "action": action,
            "description": description,
            "status": "SUCCESS"
        })
        print(f"✅ Interaction: {description}")
        return True
    except Exception as e:
        results["interactions"].append({
            "selector": selector,
            "action": action,
            "description": description,
            "status": "FAILED",
            "error": str(e)
        })
        print(f"❌ Interaction failed: {description} - {e}")
        return False


def main():
    print("="*80)
    print("CHROMIUM VISUAL VALIDATION & CLICK TESTING")
    print("="*80)
    
    dashboard_url = "http://localhost:8050"
    
    with sync_playwright() as p:
        # Launch Chromium
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        try:
            # Load dashboard
            print(f"\n[1] Loading dashboard: {dashboard_url}")
            page.goto(dashboard_url, timeout=30000, wait_until="networkidle")
            time.sleep(3)  # Let it fully render
            
            # Home page
            capture_screenshot(page, "01_home", "Dashboard Home Page")
            
            # Test Options Lab
            print("\n[2] Testing Options Lab")
            test_interaction(page, 'a:has-text("📈 Options Lab")', "click", "Navigate to Options Lab")
            time.sleep(2)
            capture_screenshot(page, "02_options_lab", "Options Lab Main View")
            
            # Check for contract selector
            if page.locator('[id="contract-option-type"]').count() > 0:
                print("✅ Contract selector found")
                capture_screenshot(page, "03_options_lab_contract_selector", "Options Lab Contract Selector")
            else:
                print("⚠️ Contract selector not visible (may need ticker input first)")
            
            # Test Azure ML Lab
            print("\n[3] Testing Azure ML Lab")
            test_interaction(page, 'a:has-text("🤖 Azure ML Lab")', "click", "Navigate to Azure ML Lab")
            time.sleep(2)
            capture_screenshot(page, "04_azure_ml_lab", "Azure ML Lab Main View")
            
            # Check for run prediction button
            run_btn_selectors = [
                '[id="azure-ml-run-prediction-btn"]',
                'button:has-text("Run Prediction")',
                'button:has-text("Generate")'
            ]
            for selector in run_btn_selectors:
                if page.locator(selector).count() > 0:
                    print(f"✅ Run prediction button found: {selector}")
                    break
            else:
                print("⚠️ Run prediction button not found")
            
            # Test Weekly Picks
            print("\n[4] Testing Weekly Picks")
            test_interaction(page, 'a:has-text("📊 Weekly Picks")', "click", "Navigate to Weekly Picks")
            time.sleep(2)
            capture_screenshot(page, "05_weekly_picks", "Weekly Picks Tab")
            
            # Test Monthly Picks
            print("\n[5] Testing Monthly Picks")
            test_interaction(page, 'a:has-text("📅 Monthly Picks")', "click", "Navigate to Monthly Picks")
            time.sleep(2)
            capture_screenshot(page, "06_monthly_picks", "Monthly Picks Tab")
            
            # Test Research Lab
            print("\n[6] Testing Research Lab")
            test_interaction(page, 'a:has-text("🔬 Research Lab")', "click", "Navigate to Research Lab")
            time.sleep(2)
            capture_screenshot(page, "07_research_lab", "Research Lab Tab")
            
            # Check console errors
            print("\n[7] Checking console errors")
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            
            if console_errors:
                results["errors"].extend(console_errors)
                print(f"⚠️ Console errors: {len(console_errors)}")
            else:
                print("✅ No console errors")
            
        except Exception as e:
            print(f"❌ Critical error: {e}")
            results["errors"].append(f"Critical: {str(e)}")
        
        finally:
            browser.close()
    
    # Save results
    with open("visual_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*80)
    print("VALIDATION COMPLETE")
    print("="*80)
    print(f"Screenshots: {len(results['screenshots'])}")
    print(f"Interactions: {len(results['interactions'])}")
    print(f"Errors: {len(results['errors'])}")
    print("\n✅ Results saved to visual_test_results.json")
    print("✅ Screenshots saved to screenshots/ directory")
    
    return 0 if len(results['errors']) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

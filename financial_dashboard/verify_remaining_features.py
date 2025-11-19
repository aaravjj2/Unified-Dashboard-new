"""Quick verification of the two features that had issues in automated test."""
import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print("\n" + "="*80)
    print("VERIFYING REMAINING FEATURES")
    print("="*80 + "\n")
    
    page.goto('http://127.0.0.1:8054')
    page.wait_for_selector('h2:has-text("Analysis Hub")')
    print("✓ Loaded Analysis Hub\n")
    
    # Go to Scenario Tester
    page.locator('a:has-text("Scenario Tester")').first.click()
    time.sleep(1)
    print("="*80)
    print("TEST 1: Compare Mode Selector Visibility")
    print("="*80)
    
    # Check initial state
    compare_selector = page.locator('#scenario-compare-selector')
    print(f"Initial state - Compare selector visible: {compare_selector.is_visible()}")
    print(f"Initial state - Compare selector count: {compare_selector.count()}")
    
    # Enable compare mode
    print("\nEnabling compare mode via JS...")
    page.evaluate("""
        const checklist = document.querySelector('#scenario-compare-mode');
        if (checklist && checklist._reactProps) {
            checklist._reactProps.setProps({value: ['compare']});
        }
    """)
    time.sleep(2)  # Give it more time
    
    print(f"After enabling - Compare selector visible: {compare_selector.is_visible()}")
    print(f"After enabling - Compare selector count: {compare_selector.count()}")
    
    # Check if it's maybe just hidden with CSS
    display_style = page.evaluate("""
        const elem = document.querySelector('#scenario-compare-selector');
        if (elem) {
            const style = window.getComputedStyle(elem);
            return {display: style.display, visibility: style.visibility, opacity: style.opacity};
        }
        return null;
    """)
    print(f"CSS properties: {display_style}")
    
    page.screenshot(path='verify_compare_mode.png')
    print("Screenshot saved: verify_compare_mode.png")
    
    print("\n" + "="*80)
    print("TEST 2: Hedging Candidates in Scenario Results")
    print("="*80)
    
    # Disable compare mode and run a factor scenario
    page.evaluate("""
        const checklist = document.querySelector('#scenario-compare-mode');
        if (checklist && checklist._reactProps) {
            checklist._reactProps.setProps({value: []});
        }
    """)
    time.sleep(0.5)
    
    # Set to factor type and momentum_crash
    page.evaluate("""
        const typeDropdown = document.querySelector('#scenario-type');
        if (typeDropdown && typeDropdown._reactProps) {
            typeDropdown._reactProps.setProps({value: 'factor'});
        }
    """)
    time.sleep(0.5)
    
    page.evaluate("""
        const presetDropdown = document.querySelector('#scenario-preset');
        if (presetDropdown && presetDropdown._reactProps) {
            presetDropdown._reactProps.setProps({value: 'momentum_crash'});
        }
    """)
    time.sleep(0.5)
    
    print("Running Momentum Crash scenario...")
    page.locator('button#scenario-run-btn').click()
    time.sleep(3)
    
    # Get the full results text
    results_text = page.locator('#scenario-results').text_content()
    print(f"\nResults length: {len(results_text)} characters")
    print("\nFirst 1000 characters of results:")
    print("-" * 80)
    print(results_text[:1000])
    print("-" * 80)
    
    # Search for hedging-related keywords
    keywords = ['hedg', 'candidate', 'protect', 'offset', 'recommended']
    print("\nSearching for keywords:")
    for keyword in keywords:
        if keyword.lower() in results_text.lower():
            print(f"  ✓ Found '{keyword}'")
            # Show context
            idx = results_text.lower().find(keyword.lower())
            context = results_text[max(0, idx-50):min(len(results_text), idx+100)]
            print(f"    Context: ...{context}...")
        else:
            print(f"  ✗ Not found: '{keyword}'")
    
    page.screenshot(path='verify_hedging_candidates.png')
    print("\nScreenshot saved: verify_hedging_candidates.png")
    
    print("\n" + "="*80)
    print("VERIFICATION COMPLETE")
    print("="*80 + "\n")
    
    input("Press Enter to close browser...")
    browser.close()

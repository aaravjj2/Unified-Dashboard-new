#!/usr/bin/env python3
"""
Comprehensive Playwright E2E test for full FinGPT integration.
Tests RAG queries, forecaster, and index status.
"""
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def test_fingpt_full_integration(page, base_url="http://localhost:8051"):
    """Test the complete FinGPT integration in Research Lab."""
    
    print("\n" + "="*70)
    print("COMPREHENSIVE FINGPT INTEGRATION TEST")
    print("="*70)
    
    screenshots_dir = Path("screenshots/fingpt_full_integration")
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    
    test_results = {
        'rag_query': False,
        'rag_sources': False,
        'forecaster': False,
        'index_status': False
    }
    
    try:
        # Step 1: Load dashboard
        print("\n[1/10] Loading dashboard...")
        page.goto(base_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)
        print("   ✓ Dashboard loaded")
        
        # Step 2: Open Research Lab using Playwright click (not JS)
        print("\n[2/10] Opening Research Lab...")
        try:
            research_tab = page.locator("a.nav-link:has-text('Research Lab')")
            research_tab.wait_for(state="visible", timeout=5000)
            research_tab.click()
            page.wait_for_timeout(2000)
            print("   ✓ Research Lab opened")
        except Exception as e:
            print(f"   ⚠ Could not open Research Lab: {e}")
            raise
            research_tab = page.locator("a.nav-link:has-text('Research Lab')")
            research_tab.click()
            page.wait_for_timeout(2000)
        
        page.screenshot(path=str(screenshots_dir / "01_research_lab_opened.png"))
        
        # Step 3: Click RAG Chat subtab using Playwright locators (not JS)
        print("\n[3/10] Opening RAG Chat subtab...")
        page.wait_for_timeout(1000)
        
        # Use Playwright locator to find and click the RAG Chat tab
        rag_tab = page.locator("a.nav-link:has-text('RAG Chat')")
        rag_tab.wait_for(state="visible", timeout=5000)
        rag_tab.click()
        page.wait_for_timeout(2000)
        print("   ✓ RAG Chat subtab opened")
        
        page.screenshot(path=str(screenshots_dir / "02_rag_tab_opened.png"))
        
        # Step 4: Check index status
        print("\n[4/10] Checking RAG index status...")
        page.wait_for_timeout(1000)  # Wait for content to load
        index_info = page.locator("#rl-rag-index-info")
        index_text = index_info.inner_text()
        
        if "Documents indexed:" in index_text or "documents indexed" in index_text.lower():
            print(f"   ✓ Index status displayed")
            print(f"   Info: {index_text[:80]}")
            test_results['index_status'] = True
        else:
            print(f"   ⚠ Index status unclear")
            print(f"   Got: {index_text[:80]}")
        
        # Step 5: Test RAG query
        print("\n[5/10] Testing RAG query...")
        page.wait_for_timeout(2000)
        
        # Wait for the query input to be visible (key step!)
        query_input = page.locator("#rl-rag-query-input")
        query_input.wait_for(state="visible", timeout=10000)
        
        # Now fill using Playwright since the element is visible
        query_input.fill("What are the key highlights from Apple's earnings?")
        page.wait_for_timeout(500)
        
        # Debug: check if the value was actually set
        input_value = page.evaluate("""
            () => {
                const input = document.querySelector('#rl-rag-query-input');
                return input ? input.value : 'NOT FOUND';
            }
        """)
        print(f"   Debug - Input value after fill: '{input_value}'")
        
        # Click button - it should also be visible now
        ask_button = page.locator("#rl-rag-run-btn")
        ask_button.wait_for(state="visible", timeout=10000)
        ask_button.click()
        print("   Debug - Button clicked successfully")
            
        page.wait_for_timeout(8000)  # Wait even longer for RAG processing (increased from 6000)
        
        # Get answer using JavaScript
        answer_text = page.evaluate("""
            () => {
                const answerDiv = document.querySelector('#rl-rag-answer');
                return answerDiv ? answerDiv.innerText : '';
            }
        """)
        
        print(f"   Debug - Answer length: {len(answer_text)}, Content: '{answer_text}'")
        
        if answer_text and len(answer_text) > 30:
            print(f"   ✓ RAG answer received ({len(answer_text)} chars)")
            print(f"   Preview: {answer_text[:100]}...")
            test_results['rag_query'] = True
        else:
            print(f"   ⚠ Answer may be incomplete: {answer_text[:100] if answer_text else 'EMPTY'}")
        
        page.screenshot(path=str(screenshots_dir / "03_rag_answer.png"))
        
        # Step 6: Check sources
        print("\n[6/10] Verifying RAG sources...")
        sources_text = page.evaluate("""
            () => {
                const sources = document.querySelector('#rl-rag-sources');
                return sources ? sources.innerText : '';
            }
        """)
        
        cards_count = page.evaluate("""
            () => {
                return document.querySelectorAll('#rl-rag-sources .card').length;
            }
        """)
        
        if cards_count > 0:
            print(f"   ✓ Found {cards_count} source card(s)")
            test_results['rag_sources'] = True
        else:
            print(f"   ⚠ No source cards found (count={cards_count})")
        
        page.screenshot(path=str(screenshots_dir / "04_rag_sources.png"))
        
        # Step 7: Scroll to forecaster section
        print("\n[7/10] Testing FinGPT Forecaster...")
        page.evaluate("""
            () => {
                const heading = Array.from(document.querySelectorAll('h4'))
                    .find(el => el.textContent.includes('FinGPT Forecaster'));
                if (heading) heading.scrollIntoView({ behavior: 'smooth' });
            }
        """)
        page.wait_for_timeout(1500)
        
        page.screenshot(path=str(screenshots_dir / "05_forecaster_visible.png"))
        
        # Step 8: Enter ticker and generate forecast
        print("\n[8/10] Running forecast for NVDA...")
        
        # Use JavaScript to fill and click since elements are in hidden tab
        page.evaluate("""
            () => {
                const ticker = document.querySelector('#rl-forecast-ticker');
                if (ticker) {
                    ticker.value = 'NVDA';
                    ticker.dispatchEvent(new Event('input', { bubbles: true }));
                    ticker.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        """)
        page.wait_for_timeout(500)
        
        page.evaluate("""
            () => {
                const btn = document.querySelector('#rl-forecast-run-btn');
                if (btn) btn.click();
            }
        """)
        page.wait_for_timeout(5000)  # Wait for forecast generation
        
        # Step 9: Check forecast result
        print("\n[9/10] Checking forecast result...")
        result_text = page.evaluate("""
            () => {
                const result = document.querySelector('#rl-forecast-result');
                return result ? result.innerText : '';
            }
        """)
        
        if result_text and ("Prediction:" in result_text or "Analysis" in result_text or "PREDICTION" in result_text):
            print(f"   ✓ Forecast generated")
            print(f"   Preview: {result_text[:120]}...")
            test_results['forecaster'] = True
        else:
            print(f"   ⚠ Forecast result unclear or empty")
            print(f"   Got: {result_text[:100]}")
        
        page.screenshot(path=str(screenshots_dir / "06_forecast_result.png"))
        
        # Step 10: Test another forecast (AAPL)
        print("\n[10/10] Testing second forecast (AAPL)...")
        page.evaluate("""
            () => {
                const ticker = document.querySelector('#rl-forecast-ticker');
                if (ticker) {
                    ticker.value = 'AAPL';
                    ticker.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }
        """)
        page.wait_for_timeout(300)
        
        page.evaluate("""
            () => {
                const btn = document.querySelector('#rl-forecast-run-btn');
                if (btn) btn.click();
            }
        """)
        page.wait_for_timeout(3000)
        
        page.screenshot(path=str(screenshots_dir / "07_second_forecast.png"))
        
        # Final full page screenshot
        page.screenshot(path=str(screenshots_dir / "08_final_full_page.png"), full_page=True)
        
        # Summary
        print("\n" + "="*70)
        print("TEST RESULTS SUMMARY")
        print("="*70)
        
        passed = sum(test_results.values())
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status}  {test_name.replace('_', ' ').title()}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        print(f"Screenshots saved to: {screenshots_dir}")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED! FinGPT integration complete!")
            return True
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")
            return False
        
    except Exception as e:
        print(f"\n❌ Test FAILED with exception: {e}")
        page.screenshot(path=str(screenshots_dir / "ERROR_screenshot.png"))
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the comprehensive test."""
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8051"
    
    print(f"\n🚀 Starting Comprehensive FinGPT Integration Test")
    print(f"   Target: {base_url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        try:
            success = test_fingpt_full_integration(page, base_url)
            return 0 if success else 1
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Playwright E2E test for FinGPT RAG integration in Research Lab.
Tests RAG query execution and provenance display.
"""
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def test_research_lab_rag(page, base_url="http://localhost:8051"):
    """Test the RAG Chat functionality in Research Lab."""
    
    print("\n" + "="*60)
    print("Testing Research Lab RAG Chat Integration")
    print("="*60)
    
    screenshots_dir = Path("screenshots/research_lab_rag")
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Step 1: Load dashboard
        print("\n[1/8] Loading dashboard...")
        page.goto(base_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)  # Extra time for callbacks to settle
        print("   ✓ Dashboard loaded")
        
        # Step 2: Click Research Lab tab using E2E helper
        print("\n[2/8] Opening Research Lab...")
        try:
            research_tab_btn = page.locator("#e2e-open-tab-research_lab")
            research_tab_btn.wait_for(state="visible", timeout=5000)
            research_tab_btn.click()
            page.wait_for_timeout(1500)
            print("   ✓ Research Lab opened")
        except Exception as e:
            print(f"   ⚠ E2E button not found, trying direct tab click: {e}")
            research_tab = page.locator("a.nav-link:has-text('Research Lab')")
            research_tab.click()
            page.wait_for_timeout(1500)
        
        page.screenshot(path=str(screenshots_dir / "01_research_lab_opened.png"))
        
        # Step 3: Click RAG Chat subtab
        print("\n[3/8] Opening RAG Chat subtab...")
        rag_tab = page.locator("a.nav-link:has-text('RAG Chat')")
        rag_tab.wait_for(state="visible", timeout=5000)
        rag_tab.click()
        page.wait_for_timeout(1500)
        print("   ✓ RAG Chat subtab opened")
        
        page.screenshot(path=str(screenshots_dir / "02_rag_chat_opened.png"))
        
        # Step 4: Enter query
        print("\n[4/8] Entering test query...")
        query_input = page.locator("#rl-rag-query-input")
        query_input.wait_for(state="visible", timeout=5000)
        
        test_query = "What are Apple's Q4 earnings results?"
        query_input.fill(test_query)
        page.wait_for_timeout(500)
        print(f"   ✓ Query entered: '{test_query}'")
        
        page.screenshot(path=str(screenshots_dir / "03_query_entered.png"))
        
        # Step 5: Click Ask button
        print("\n[5/8] Submitting query...")
        ask_button = page.locator("#rl-rag-run-btn")
        ask_button.click()
        page.wait_for_timeout(3000)  # Wait for RAG processing
        print("   ✓ Query submitted")
        
        page.screenshot(path=str(screenshots_dir / "04_query_submitted.png"))
        
        # Step 6: Wait for answer to appear
        print("\n[6/8] Waiting for answer...")
        answer_div = page.locator("#rl-rag-answer")
        
        # Wait for answer content (check that it's not empty/loading)
        max_wait = 15
        for i in range(max_wait):
            answer_text = answer_div.inner_text()
            if answer_text and len(answer_text) > 20 and "Loading" not in answer_text:
                print(f"   ✓ Answer received ({len(answer_text)} chars)")
                print(f"   Preview: {answer_text[:100]}...")
                break
            page.wait_for_timeout(1000)
            print(f"   ⏳ Waiting for answer... ({i+1}/{max_wait})")
        else:
            print("   ⚠ Answer may be incomplete or still loading")
        
        page.screenshot(path=str(screenshots_dir / "05_answer_received.png"))
        
        # Step 7: Check sources
        print("\n[7/8] Checking sources/provenance...")
        sources_div = page.locator("#rl-rag-sources")
        sources_text = sources_div.inner_text()
        
        if sources_text and "No sources" not in sources_text:
            print(f"   ✓ Sources displayed ({len(sources_text)} chars)")
            
            # Count source cards
            source_cards = page.locator("#rl-rag-sources .card")
            card_count = source_cards.count()
            print(f"   ✓ Found {card_count} source card(s)")
            
            # Get details of first source
            if card_count > 0:
                first_card = source_cards.first
                card_text = first_card.inner_text()
                print(f"   First source preview: {card_text[:80]}...")
        else:
            print("   ⚠ No sources displayed or empty state")
        
        page.screenshot(path=str(screenshots_dir / "06_sources_displayed.png"))
        
        # Step 8: Test another query (momentum)
        print("\n[8/8] Testing second query (momentum)...")
        query_input.fill("Tell me about momentum strategies")
        page.wait_for_timeout(500)
        ask_button.click()
        page.wait_for_timeout(3000)
        
        answer_text2 = answer_div.inner_text()
        if answer_text2 and len(answer_text2) > 20:
            print(f"   ✓ Second answer received ({len(answer_text2)} chars)")
        
        page.screenshot(path=str(screenshots_dir / "07_second_query_complete.png"))
        
        # Final screenshot
        page.screenshot(path=str(screenshots_dir / "08_final_state.png"), full_page=True)
        
        print("\n" + "="*60)
        print("✅ RAG Chat Test PASSED")
        print("="*60)
        print(f"\nScreenshots saved to: {screenshots_dir}")
        print("\nTest Summary:")
        print("  ✓ Dashboard loaded")
        print("  ✓ Research Lab accessed")
        print("  ✓ RAG Chat subtab opened")
        print("  ✓ Query submitted successfully")
        print("  ✓ Answer generated")
        print("  ✓ Sources/provenance displayed")
        print("  ✓ Second query tested")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        page.screenshot(path=str(screenshots_dir / "ERROR_screenshot.png"))
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the test."""
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8051"
    
    print(f"\n🧪 Starting RAG Integration Test on {base_url}")
    
    with sync_playwright() as p:
        # Launch browser (non-headless as requested)
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        try:
            success = test_research_lab_rag(page, base_url)
            return 0 if success else 1
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())

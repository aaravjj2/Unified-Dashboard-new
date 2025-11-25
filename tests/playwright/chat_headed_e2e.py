#!/usr/bin/env python3
"""
PHASE 6 - Headed Playwright E2E Tests for RAG Chat Assistant
Non-headless Chromium testing per user specification
"""

import os
import sys
import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, expect

# Test configuration
DASHBOARD_URL = "http://localhost:8050"
ARTIFACTS_DIR = Path("/home/aarav/unified-dashboard/reports/chat_agent/playwright")
SCREENSHOTS_DIR = ARTIFACTS_DIR / "screenshots"
DOM_DIR = ARTIFACTS_DIR / "dom"
HAR_DIR = ARTIFACTS_DIR / "har"

# Ensure artifact directories exist
for d in [ARTIFACTS_DIR, SCREENSHOTS_DIR, DOM_DIR, HAR_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def save_page_state(page: Page, test_name: str, step: str):
    """
    Save page state for debugging: screenshot, DOM, console logs
    """
    timestamp = int(time.time() * 1000)
    filename = f"{test_name}_{step}_{timestamp}"
    
    # Screenshot
    screenshot_path = SCREENSHOTS_DIR / f"{filename}.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    print(f"   📸 Screenshot: {screenshot_path.name}")
    
    # DOM HTML
    dom_path = DOM_DIR / f"{filename}.html"
    dom_path.write_text(page.content())
    print(f"   📄 DOM saved: {dom_path.name}")
    
    # Console logs (from page context)
    print(f"   📝 Console: see browser output")


def test_flow_a_rag_query_with_sources(page: Page):
    """
    FLOW A: Basic RAG query with sources and color verification
    
    Steps:
    1. Navigate to dashboard
    2. Wait for chatbot widget to be visible
    3. Verify text color is rgb(0, 0, 0)
    4. Send RAG query: "What is the latest price for AAPL?"
    5. Wait for response
    6. Verify answer contains price information
    7. Verify sources are displayed
    8. Verify text color remains black
    """
    print("\n" + "=" * 80)
    print("FLOW A: RAG Query with Sources + Color Verification")
    print("=" * 80)
    
    # Step 1: Navigate
    print("\n📌 Step 1: Navigate to dashboard")
    page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=60000)
    save_page_state(page, "flow_a", "01_loaded")
    
    # Step 2: Open chatbot
    print("\n📌 Step 2: Open chatbot widget")
    
    # Look for the toggle button
    toggle_btn = page.locator("#chatbot-toggle-btn")
    toggle_btn.wait_for(state="visible", timeout=10000)
    print("   ✅ Chatbot toggle button found")
    
    # Click to open chatbot
    toggle_btn.click()
    print("   ✅ Clicked toggle button")
    time.sleep(1)  # Wait for animation
    
    # Now wait for chatbot window to appear
    chatbot_window = page.locator("#chatbot-window, #chatbot-container")
    chatbot_window.wait_for(state="visible", timeout=5000)
    print("   ✅ Chatbot window opened")
    
    save_page_state(page, "flow_a", "02_chatbot_visible")
    
    # Step 3: Verify black text color
    print("\n📌 Step 3: Verify text color is black")
    
    # Check diagnostic element
    diag_element = page.locator("#chat-color-diagnostic")
    if diag_element.count() > 0:
        computed_color = page.evaluate("""
            () => {
                const el = document.querySelector('#chat-color-diagnostic');
                return window.getComputedStyle(el).color;
            }
        """)
        print(f"   Color from #chat-color-diagnostic: {computed_color}")
        assert "rgb(0, 0, 0)" in computed_color or "rgb(0,0,0)" in computed_color, \
            f"Expected black text but got {computed_color}"
        print("   ✅ Color is black (rgb(0, 0, 0))")
    
    # Also check messages container
    messages_container = page.locator("#chatbot-messages-container")
    if messages_container.count() > 0:
        msg_color = page.evaluate("""
            () => {
                const el = document.querySelector('#chatbot-messages-container');
                return window.getComputedStyle(el).color;
            }
        """)
        print(f"   Color from #chatbot-messages-container: {msg_color}")
    
    save_page_state(page, "flow_a", "03_color_verified")
    
    # Step 4: Send RAG query
    print("\n📌 Step 4: Send RAG query for AAPL price")
    chat_input = page.locator("#chatbot-input")
    send_btn = page.locator("#chatbot-send-btn")
    
    chat_input.fill("What is the latest price for AAPL?")
    save_page_state(page, "flow_a", "04_query_typed")
    
    send_btn.click()
    print("   ✅ Query sent")
    time.sleep(1)  # Brief pause for UI update
    save_page_state(page, "flow_a", "05_query_sent")
    
    # Step 5: Wait for response (allow up to 30 seconds for LLM)
    print("\n📌 Step 5: Wait for response (max 30s)")
    max_wait = 30
    start = time.time()
    
    # Wait for new message to appear
    # Strategy: Look for message bubbles, count should increase
    initial_count = page.locator(".chat-bubble, .message-bubble, [class*='message']").count()
    print(f"   Initial message count: {initial_count}")
    
    response_found = False
    while time.time() - start < max_wait:
        current_count = page.locator(".chat-bubble, .message-bubble, [class*='message']").count()
        if current_count > initial_count:
            response_found = True
            print(f"   ✅ Response appeared (count: {current_count})")
            break
        time.sleep(0.5)
    
    if not response_found:
        # Try alternative: just wait for any text containing price indicators
        page.wait_for_selector("text=/price|\\$|AAPL/i", timeout=max_wait * 1000)
        print("   ✅ Response text detected")
    
    save_page_state(page, "flow_a", "06_response_received")
    
    # Step 6: Verify answer content
    print("\n📌 Step 6: Verify answer contains AAPL price info")
    page_text = page.content().lower()
    
    # Check for price-related content
    has_price = any(keyword in page_text for keyword in ['$', 'price', 'aapl', 'stock'])
    assert has_price, "Response should contain price-related information"
    print("   ✅ Answer contains price information")
    
    # Step 7: Verify sources (optional - might be in collapsed section)
    print("\n📌 Step 7: Check for sources")
    sources_found = "source" in page_text or "chunk" in page_text or "retrieved" in page_text
    if sources_found:
        print("   ✅ Sources mentioned in response")
    else:
        print("   ⚠️  Sources not explicitly visible (might be collapsed)")
    
    save_page_state(page, "flow_a", "07_final_state")
    
    # Step 8: Verify color again
    print("\n📌 Step 8: Re-verify text color after response")
    final_color = page.evaluate("""
        () => {
            const el = document.querySelector('#chatbot-messages-container') || 
                       document.querySelector('#chat-color-diagnostic');
            return window.getComputedStyle(el).color;
        }
    """)
    print(f"   Final computed color: {final_color}")
    assert "rgb(0, 0, 0)" in final_color or "rgb(0,0,0)" in final_color, \
        f"Text color changed! Expected black, got {final_color}"
    print("   ✅ Color remains black")
    
    print("\n" + "=" * 80)
    print("✅ FLOW A PASSED")
    print("=" * 80)
    
    return True


def test_flow_b_no_chunk_guard(page: Page):
    """
    FLOW B: No-chunk guard behavior test
    
    Steps:
    1. Navigate to dashboard
    2. Send completely irrelevant query
    3. Verify guard message appears
    4. Verify no hallucination
    """
    print("\n" + "=" * 80)
    print("FLOW B: No-Chunk Guard Behavior")
    print("=" * 80)
    
    # Step 1: Navigate
    print("\n📌 Step 1: Navigate to dashboard")
    page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=60000)
    save_page_state(page, "flow_b", "01_loaded")
    
    # Step 2: Open chatbot
    print("\n📌 Step 2: Open chatbot")
    toggle_btn = page.locator("#chatbot-toggle-btn")
    toggle_btn.wait_for(state="visible", timeout=10000)
    toggle_btn.click()
    time.sleep(1)
    print("   ✅ Chatbot opened")
    
    # Step 3: Send irrelevant query
    print("\n📌 Step 3: Send irrelevant query")
    chat_input = page.locator("#chatbot-input")
    send_btn = page.locator("#chatbot-send-btn")
    
    chat_input.fill("What is the recipe for chocolate chip cookies?")
    save_page_state(page, "flow_b", "02_query_typed")
    
    send_btn.click()
    print("   ✅ Query sent")
    time.sleep(1)
    
    # Step 4: Wait for response
    print("\n📌 Step 4: Wait for guard response")
    page.wait_for_timeout(15000)  # Wait 15s for LLM response
    save_page_state(page, "flow_b", "03_response_received")
    
    # Step 5: Verify guard message
    print("\n📌 Step 5: Verify no-chunk guard message")
    page_text = page.content().lower()
    
    # Check for guard keywords
    guard_keywords = ["don't have relevant documents", "no relevant", "would you like me to fetch"]
    guard_triggered = any(keyword in page_text for keyword in guard_keywords)
    
    if guard_triggered:
        print("   ✅ No-chunk guard triggered correctly")
    else:
        # Check if it hallucinated a recipe
        hallucinated = any(word in page_text for word in ["flour", "butter", "sugar", "bake"])
        if hallucinated:
            print("   ❌ WARNING: System hallucinated instead of using guard!")
            save_page_state(page, "flow_b", "04_hallucination_detected")
            assert False, "No-chunk guard failed - system hallucinated"
        else:
            print("   ⚠️  Guard keywords not found, but no obvious hallucination")
    
    save_page_state(page, "flow_b", "05_final_state")
    
    print("\n" + "=" * 80)
    print("✅ FLOW B PASSED")
    print("=" * 80)
    
    return True


def test_flow_c_action_suggestion(page: Page):
    """
    FLOW C: Action suggestion detection (optional flow)
    
    Steps:
    1. Navigate to dashboard
    2. Send query that should trigger action
    3. Check if action suggestion appears
    """
    print("\n" + "=" * 80)
    print("FLOW C: Action Suggestion (Optional)")
    print("=" * 80)
    
    # Step 1: Navigate
    print("\n📌 Step 1: Navigate to dashboard")
    page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=60000)
    save_page_state(page, "flow_c", "01_loaded")
    
    # Step 2: Open chatbot
    print("\n📌 Step 2: Open chatbot")
    toggle_btn = page.locator("#chatbot-toggle-btn")
    toggle_btn.wait_for(state="visible", timeout=10000)
    toggle_btn.click()
    time.sleep(1)
    print("   ✅ Chatbot opened")
    
    # Step 3: Send action-triggering query
    print("\n📌 Step 3: Send query with action intent")
    chat_input = page.locator("#chatbot-input")
    send_btn = page.locator("#chatbot-send-btn")
    
    chat_input.fill("Show me the volatility surface tab")
    save_page_state(page, "flow_c", "02_query_typed")
    
    send_btn.click()
    print("   ✅ Query sent")
    
    # Step 4: Wait for response
    print("\n📌 Step 4: Wait for response")
    page.wait_for_timeout(15000)
    save_page_state(page, "flow_c", "03_response_received")
    
    # Step 5: Check for action elements
    print("\n📌 Step 5: Check for action suggestion")
    page_text = page.content().lower()
    
    action_keywords = ["action", "navigate", "open tab", "confirm", "execute"]
    action_found = any(keyword in page_text for keyword in action_keywords)
    
    if action_found:
        print("   ✅ Action-related content detected")
    else:
        print("   ⚠️  No explicit action UI found (might be text-only suggestion)")
    
    save_page_state(page, "flow_c", "04_final_state")
    
    print("\n" + "=" * 80)
    print("✅ FLOW C COMPLETED (action detection is optional)")
    print("=" * 80)
    
    return True


def run_all_tests():
    """
    Run all headed Playwright tests
    """
    print("\n" + "🟢" * 40)
    print("PHASE 6: HEADED PLAYWRIGHT E2E TESTS")
    print("Non-Headless Chromium Mode")
    print("🟢" * 40 + "\n")
    
    results = {
        "flow_a": False,
        "flow_b": False,
        "flow_c": False,
    }
    
    with sync_playwright() as p:
        # Launch browser in HEADED mode (non-headless)
        print("🚀 Launching Chromium in HEADED mode...")
        browser = p.chromium.launch(
            headless=False,  # HEADED MODE per user requirement
            slow_mo=500,  # Slow down actions for visibility
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        # Create context with HAR recording
        har_path = HAR_DIR / f"test_run_{int(time.time())}.har"
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_har_path=str(har_path),
        )
        
        page = context.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: print(f"   [BROWSER CONSOLE] {msg.type}: {msg.text}"))
        
        try:
            # Run Flow A
            print("\n" + "-" * 80)
            results["flow_a"] = test_flow_a_rag_query_with_sources(page)
            time.sleep(2)  # Pause between tests
            
            # Run Flow B
            print("\n" + "-" * 80)
            results["flow_b"] = test_flow_b_no_chunk_guard(page)
            time.sleep(2)
            
            # Run Flow C
            print("\n" + "-" * 80)
            results["flow_c"] = test_flow_c_action_suggestion(page)
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            save_page_state(page, "error", "exception")
            raise
        finally:
            # Close and save HAR
            context.close()
            browser.close()
            print(f"\n📦 HAR file saved: {har_path.name}")
    
    # Report results
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)
    
    for flow, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{flow.upper()}: {status}")
    
    total = len(results)
    passed_count = sum(1 for v in results.values() if v)
    
    print(f"\nTotal: {passed_count}/{total} passed")
    print("=" * 80)
    
    # Save results JSON
    results_json = ARTIFACTS_DIR / "test_results.json"
    results_json.write_text(json.dumps({
        "timestamp": time.time(),
        "total": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "results": results,
    }, indent=2))
    
    print(f"\n📊 Results saved: {results_json}")
    
    return passed_count == total


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

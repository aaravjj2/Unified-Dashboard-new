#!/usr/bin/env python3
"""
GPU Chat E2E Test
Tests chat with GPU acceleration using headed browser
"""

import time
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

def test_gpu_chat():
    """Test chat with GPU and measure response time"""
    
    print("=" * 70)
    print("GPU-ACCELERATED CHAT E2E TEST")
    print("=" * 70)
    
    with sync_playwright() as p:
        # Launch headed Chromium
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        try:
            print("\n1. Loading dashboard...")
            page.goto("http://localhost:8050", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            
            print("2. Opening chat (clicking FAB)...")
            # Try FAB first
            fab_btn = page.locator("#chatbot-toggle-btn").first
            if fab_btn.is_visible(timeout=5000):
                fab_btn.click()
                print("   ✓ Chat opened via FAB")
            else:
                # Fallback to minibar
                minibar_btn = page.locator("button:has-text('Assistant')").first
                minibar_btn.click()
                print("   ✓ Chat opened via minibar")
            
            page.wait_for_timeout(1000)
            
            print("\n3. Entering test message...")
            test_query = "What is portfolio optimization?"
            print(f"   Query: '{test_query}'")
            
            input_field = page.locator("#chatbot-input").first
            input_field.fill(test_query)
            page.wait_for_timeout(500)
            
            print("\n4. Sending message and measuring response time...")
            print("   [Waiting for LLM response...]")
            
            # Get initial message count BEFORE clicking send (count children of #chatbot-messages)
            messages_container = page.locator("#chatbot-messages").first
            initial_count = messages_container.locator("> div").count()
            print(f"   Initial message count: {initial_count}")
            
            send_btn = page.locator("#chatbot-send-btn").first
            
            # Start timer and send
            start_time = time.time()
            send_btn.click()
            
            # Wait for AI response to appear
            try:
                # Wait for new message to appear in #chatbot-messages
                # Expect at least initial_count + 2 (user message + AI response)
                page.wait_for_function(
                    f"document.querySelectorAll('#chatbot-messages > div').length >= {initial_count + 2}",
                    timeout=45000  # 45 seconds max
                )
                end_time = time.time()
                elapsed = end_time - start_time
                
                print(f"\n   ✅ Response received in {elapsed:.2f} seconds")
                
                # Get response text (last message in #chatbot-messages)
                all_messages = messages_container.locator("> div").all()
                if len(all_messages) >= 2:
                    ai_response = all_messages[-1].inner_text()
                    print(f"\n   AI Response Preview:")
                    print(f"   {ai_response[:200]}...")
                
                # Performance evaluation
                print(f"\n{'='*70}")
                print(f"PERFORMANCE ANALYSIS")
                print(f"{'='*70}")
                print(f"Response Time: {elapsed:.2f}s")
                
                if elapsed < 10:
                    improvement = ((60 - elapsed) / 60) * 100
                    print(f"\n✅ EXCELLENT - LLM response time optimal!")
                    print(f"✅ {improvement:.0f}% faster than 60s baseline")
                    success = True
                elif elapsed < 20:
                    improvement = ((60 - elapsed) / 60) * 100
                    print(f"\n✅ GOOD - LLM responding quickly")
                    print(f"✅ {improvement:.0f}% faster than baseline")
                    print(f"⚠️  Some optimization possible (reduce max_tokens or enable GPU)")
                    success = True
                elif elapsed < 30:
                    print(f"\n⚠️  MODERATE - Acceptable performance")
                    print(f"   Consider reducing max_tokens or optimizing RAG pipeline")
                    success = True
                else:
                    print(f"\n❌ SLOW - Performance degraded")
                    print(f"   Check logs for errors or increase timeout")
                    success = False
                
                print(f"{'='*70}")
                
                # Keep browser open to show result
                print(f"\n[Browser will stay open for 10 seconds to verify visually]")
                page.wait_for_timeout(10000)
                
                return success
                
            except PlaywrightTimeout:
                end_time = time.time()
                elapsed = end_time - start_time
                print(f"\n❌ TIMEOUT after {elapsed:.2f} seconds")
                print(f"   Response not received within 45 seconds")
                print(f"   Check dashboard logs: tail -50 /tmp/dashboard_8050.log")
                
                page.wait_for_timeout(5000)
                return False
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            page.wait_for_timeout(5000)
            return False
            
        finally:
            browser.close()

if __name__ == "__main__":
    success = test_gpu_chat()
    sys.exit(0 if success else 1)

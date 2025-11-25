"""
Chatbot Send Button Fix - Headed Browser Testing
Tests the chatbot send button functionality with visible Chrome browser
"""
import time
import logging
from playwright.sync_api import sync_playwright, expect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DASHBOARD_URL = "http://localhost:8050"
TEST_MESSAGE = "What is the current price of AAPL?"

def test_chatbot_send_button():
    """Test chatbot send button with headed browser"""
    
    with sync_playwright() as p:
        # Launch VISIBLE Chrome browser
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_video_dir="./reports/chatbot_test"
        )
        page = context.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: logger.info(f"BROWSER: {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: logger.error(f"PAGE ERROR: {err}"))
        
        try:
            logger.info(f"Step 1: Loading dashboard at {DASHBOARD_URL}")
            page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            
            logger.info("Step 2: Looking for chatbot toggle button...")
            # Try different selectors
            toggle_selectors = [
                "#chatbot-toggle-btn",
                "button[id='chatbot-toggle-btn']",
                ".chatbot-toggle",
                "button:has-text('Chat')"
            ]
            
            toggle_btn = None
            for selector in toggle_selectors:
                try:
                    toggle_btn = page.locator(selector).first
                    if toggle_btn.is_visible(timeout=2000):
                        logger.info(f"✓ Found toggle button with selector: {selector}")
                        break
                except:
                    continue
            
            if not toggle_btn or not toggle_btn.is_visible():
                logger.error("✗ Chatbot toggle button not found!")
                page.screenshot(path="./reports/chatbot_test/no_toggle.png")
                return False
            
            logger.info("Step 3: Clicking chatbot toggle button...")
            toggle_btn.click()
            page.wait_for_timeout(2000)
            page.screenshot(path="./reports/chatbot_test/after_toggle.png")
            
            logger.info("Step 4: Looking for chatbot window...")
            chatbot_window = page.locator("#chatbot-window, .chatbot-window").first
            if not chatbot_window.is_visible():
                logger.error("✗ Chatbot window did not appear!")
                page.screenshot(path="./reports/chatbot_test/no_window.png")
                return False
            
            logger.info("✓ Chatbot window is visible")
            
            logger.info("Step 5: Looking for input field...")
            input_selectors = [
                "#chatbot-input",
                "input[id='chatbot-input']",
                ".chatbot-input",
                "input[placeholder*='Ask']"
            ]
            
            input_field = None
            for selector in input_selectors:
                try:
                    input_field = page.locator(selector).first
                    if input_field.is_visible(timeout=2000):
                        logger.info(f"✓ Found input field with selector: {selector}")
                        break
                except:
                    continue
            
            if not input_field or not input_field.is_visible():
                logger.error("✗ Input field not found!")
                page.screenshot(path="./reports/chatbot_test/no_input.png")
                return False
            
            logger.info(f"Step 6: Typing message: '{TEST_MESSAGE}'")
            input_field.fill(TEST_MESSAGE)
            page.wait_for_timeout(1000)
            page.screenshot(path="./reports/chatbot_test/message_typed.png")
            
            logger.info("Step 7: Looking for send button...")
            send_selectors = [
                "#chatbot-send-btn",
                "button[id='chatbot-send-btn']",
                ".chatbot-send-btn",
                "button:has-text('Send')",
                "button i.fa-paper-plane"
            ]
            
            send_btn = None
            for selector in send_selectors:
                try:
                    send_btn = page.locator(selector).first
                    if send_btn.is_visible(timeout=2000):
                        logger.info(f"✓ Found send button with selector: {selector}")
                        break
                except:
                    continue
            
            if not send_btn:
                logger.error("✗ Send button not found!")
                page.screenshot(path="./reports/chatbot_test/no_send_btn.png")
                # Get all buttons for debugging
                all_buttons = page.locator("button").all()
                logger.info(f"Found {len(all_buttons)} buttons on page")
                for i, btn in enumerate(all_buttons[:10]):
                    try:
                        logger.info(f"  Button {i}: id={btn.get_attribute('id')}, class={btn.get_attribute('class')}")
                    except:
                        pass
                return False
            
            logger.info("Step 8: Clicking send button...")
            
            # Check if button is enabled
            is_disabled = send_btn.is_disabled()
            logger.info(f"Send button disabled: {is_disabled}")
            
            if is_disabled:
                logger.warning("⚠ Send button is disabled! Checking why...")
                page.screenshot(path="./reports/chatbot_test/btn_disabled.png")
            
            # Click anyway and wait for response
            send_btn.click()
            logger.info("✓ Send button clicked")
            page.wait_for_timeout(1000)
            page.screenshot(path="./reports/chatbot_test/after_send_click.png")
            
            logger.info("Step 9: Waiting for AI response...")
            # Wait for message bubbles to appear
            page.wait_for_timeout(5000)  # Give time for API call
            
            # Check for user message bubble
            user_bubble = page.locator(".user-message, .message-user, [class*='user']").first
            if user_bubble.is_visible():
                logger.info("✓ User message bubble appeared")
            else:
                logger.warning("⚠ User message bubble not visible")
            
            # Check for AI response bubble
            ai_bubble = page.locator(".ai-message, .message-ai, .bot-message, [class*='bot']").first
            if ai_bubble.is_visible():
                logger.info("✓ AI response bubble appeared")
                response_text = ai_bubble.inner_text()
                logger.info(f"AI Response: {response_text[:100]}...")
            else:
                logger.warning("⚠ AI response bubble not visible yet, waiting longer...")
                page.wait_for_timeout(5000)
                
                if ai_bubble.is_visible():
                    logger.info("✓ AI response appeared after waiting")
                    response_text = ai_bubble.inner_text()
                    logger.info(f"AI Response: {response_text[:100]}...")
                else:
                    logger.error("✗ AI response never appeared!")
                    page.screenshot(path="./reports/chatbot_test/no_response.png")
                    return False
            
            page.screenshot(path="./reports/chatbot_test/final_success.png")
            logger.info("✅ CHATBOT SEND BUTTON TEST PASSED!")
            
            # Keep browser open for inspection
            logger.info("Browser will remain open for 10 seconds for inspection...")
            page.wait_for_timeout(10000)
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            page.screenshot(path="./reports/chatbot_test/error.png")
            return False
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    import os
    os.makedirs("./reports/chatbot_test", exist_ok=True)
    
    logger.info("=" * 80)
    logger.info("CHATBOT SEND BUTTON TEST - HEADED BROWSER")
    logger.info("=" * 80)
    
    success = test_chatbot_send_button()
    
    logger.info("=" * 80)
    if success:
        logger.info("✅ TEST PASSED - Chatbot send button works!")
    else:
        logger.info("✗ TEST FAILED - Chatbot send button broken")
    logger.info("=" * 80)

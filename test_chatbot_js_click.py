"""
Chatbot Test - Force Click with JavaScript
"""
import time
import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DASHBOARD_URL = "http://localhost:8050"

def test_chatbot_force_click():
    """Test chatbot with JavaScript force click"""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        page.on("console", lambda msg: logger.info(f"BROWSER: {msg.type}: {msg.text}"))
        
        try:
            logger.info("Loading dashboard...")
            page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            
            # Force click toggle using JavaScript
            logger.info("Force clicking toggle button with JavaScript...")
            page.evaluate("""
                () => {
                    const btn = document.getElementById('chatbot-toggle-btn');
                    if (btn) {
                        console.log('Toggle button found, clicking...');
                        btn.click();
                        return true;
                    } else {
                        console.error('Toggle button NOT found!');
                        return false;
                    }
                }
            """)
            
            page.wait_for_timeout(2000)
            page.screenshot(path="reports/chatbot_test/js_click.png")
            
            # Check if window appeared
            window_visible = page.evaluate("""
                () => {
                    const win = document.getElementById('chatbot-window');
                    if (!win) return false;
                    const style = window.getComputedStyle(win);
                    return style.display !== 'none' && style.visibility !== 'hidden';
                }
            """)
            
            logger.info(f"Chatbot window visible: {window_visible}")
            
            if not window_visible:
                logger.error("Window not visible after toggle!")
                return False
            
            # Type message
            logger.info("Typing message...")
            page.evaluate("""
                () => {
                    const input = document.getElementById('chatbot-input');
                    if (input) {
                        input.value = 'What is AAPL price?';
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                }
            """)
            
            page.wait_for_timeout(1000)
            page.screenshot(path="reports/chatbot_test/message_typed_js.png")
            
            # Click send button
            logger.info("Clicking send button...")
            send_clicked = page.evaluate("""
                () => {
                    const btn = document.getElementById('chatbot-send-btn');
                    if (btn) {
                        console.log('Send button found, clicking...');
                        btn.click();
                        return true;
                    }
                    return false;
                }
            """)
            
            logger.info(f"Send button clicked: {send_clicked}")
            page.wait_for_timeout(1000)
            page.screenshot(path="reports/chatbot_test/send_clicked_js.png")
            
            # Wait for response
            logger.info("Waiting for AI response...")
            page.wait_for_timeout(8000)
            
            # Check for messages
            messages = page.evaluate("""
                () => {
                    const container = document.getElementById('chatbot-messages');
                    if (!container) return [];
                    const msgs = container.querySelectorAll('[class*="message"], [class*="bubble"]');
                    return Array.from(msgs).map(m => ({
                        text: m.innerText.substring(0, 100),
                        class: m.className
                    }));
                }
            """)
            
            logger.info(f"Found {len(messages)} messages")
            for i, msg in enumerate(messages):
                logger.info(f"  Message {i}: {msg['text'][:50]}...")
            
            page.screenshot(path="reports/chatbot_test/final_js.png")
            
            if len(messages) >= 2:
                logger.info("✅ TEST PASSED - Messages sent and received!")
                page.wait_for_timeout(10000)  # Keep open for inspection
                return True
            else:
                logger.error(f"✗ TEST FAILED - Expected 2+ messages, got {len(messages)}")
                page.wait_for_timeout(10000)
                return False
                
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            page.screenshot(path="reports/chatbot_test/error_js.png")
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    import os
    os.makedirs("reports/chatbot_test", exist_ok=True)
    
    logger.info("=" * 80)
    logger.info("CHATBOT TEST - JAVASCRIPT FORCE CLICK")
    logger.info("=" * 80)
    
    success = test_chatbot_force_click()
    
    logger.info("=" * 80)
    logger.info("✅ PASSED" if success else "✗ FAILED")
    logger.info("=" * 80)

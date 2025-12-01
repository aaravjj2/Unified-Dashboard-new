"""
PHASE 0 Color Diagnostic Verification
Tests that chat text color is black rgb(0, 0, 0)
"""
from playwright.sync_api import sync_playwright
import time

def test_chat_color():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("Navigating to dashboard...")
        page.goto("http://localhost:8050", wait_until="networkidle")
        
        # Wait a moment for JS to load
        time.sleep(2)
        
        # Check if diagnostic element exists
        print("Checking for diagnostic element...")
        diagnostic = page.query_selector("#chat-color-diagnostic")
        if diagnostic:
            print("✓ Diagnostic element found")
            color = page.evaluate("() => window.getComputedStyle(document.getElementById('chat-color-diagnostic')).color")
            print(f"Diagnostic element color: {color}")
        else:
            print("✗ Diagnostic element NOT found")
        
        # Check messages container
        print("\nChecking messages container...")
        messages = page.query_selector("#chatbot-messages-container")
        if messages:
            print("✓ Messages container found")
            messages_color = page.evaluate("() => window.getComputedStyle(document.getElementById('chatbot-messages-container')).color")
            print(f"Messages container color: {messages_color}")
        else:
            print("✗ Messages container NOT found")
        
        # Check window diagnostic variable
        print("\nChecking window.__chat_last_computed_color...")
        window_color = page.evaluate("() => window.__chat_last_computed_color")
        print(f"Window diagnostic color: {window_color}")
        
        # Take screenshot
        print("\nTaking screenshot...")
        page.screenshot(path="reports/chat_agent/screenshots/chat_color_after.png", full_page=True)
        print("✓ Screenshot saved to reports/chat_agent/screenshots/chat_color_after.png")
        
        # Verify color is black
        expected = "rgb(0, 0, 0)"
        if window_color == expected or (diagnostic and color == expected):
            print(f"\n✅ SUCCESS: Chat color is black ({expected})")
            return True
        else:
            print(f"\n⚠️  WARNING: Chat color may not be exactly black")
            print(f"   Expected: {expected}")
            print(f"   Got: {window_color or color}")
            return False
        
        browser.close()

if __name__ == "__main__":
    test_chat_color()

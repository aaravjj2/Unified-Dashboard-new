from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={"width":1920, "height":1080})
    page.goto("http://localhost:8050")
    page.wait_for_load_state("networkidle")
    
    # Open chat
    page.click("#chatbot-toggle-btn")
    time.sleep(1)
    
    # Fill input
    inp = page.locator("#chatbot-input")
    inp.fill("Test query from Playwright")
    print(f"Input filled with: {inp.input_value()}")
    
    # Take screenshot before click
    page.screenshot(path="reports/chat_manual/before_send.png")
    
    # Click send button
    send_btn = page.locator("#chatbot-send-btn")
    print(f"Send button visible: {send_btn.is_visible()}")
    send_btn.click()
    print("Clicked send button")
    
    # Wait a bit
    time.sleep(3)
    
    # Take screenshot after
    page.screenshot(path="reports/chat_manual/after_send.png")
    
    # Dump HTML
    with open("reports/chat_manual/after_send.html", "w") as f:
        f.write(page.content())
    
    print("Done - keeping browser open 3s")
    time.sleep(3)
    browser.close()

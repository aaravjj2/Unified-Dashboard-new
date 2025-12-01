from playwright.sync_api import sync_playwright, TimeoutError
import os, time, sys

OUT_DIR = "reports/chat_manual"
os.makedirs(OUT_DIR, exist_ok=True)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width":1920, "height":1080})
        print("Opening dashboard...")
        page.goto("http://localhost:8050")
        page.wait_for_load_state("networkidle")

        print("Opening chat widget...")
        page.click("#chatbot-toggle-btn")
        # Wait for the chat container to become visible according to computed styles
        try:
            page.wait_for_function(
                "() => { const el = document.querySelector('#chatbot-container'); if(!el) return false; const s = window.getComputedStyle(el); return s.display !== 'none' && s.visibility !== 'hidden' && parseFloat(s.opacity||'1')>0.05 }",
                timeout=8000,
            )
        except TimeoutError:
            print("Chat container did not become visible according to computed styles; dumping outerHTML for debug...")
            hd = page.evaluate("() => ({outer: document.querySelector('#chatbot-container')?document.querySelector('#chatbot-container').outerHTML:'', computed: window.getComputedStyle(document.querySelector('#chatbot-container')||document.body)})")
            print(hd)
            raise

        query = "What is the volatility for AAPL?"
        print(f"Sending query: {query}")
        page.fill("#chatbot-input", query)
        page.click("#chatbot-send-btn")

        print("Waiting for diagnostic to show response...")
        try:
            page.wait_for_function(
                "() => { const el = document.querySelector('#chat-color-diagnostic'); return el && el.dataset && el.dataset.lastResponse && parseInt(el.dataset.lastResponseLen||'0')>0 }",
                timeout=30000,
            )
            print("Diagnostic indicates response received")
        except TimeoutError:
            print("Timed out waiting for diagnostic response")

        # Capture dataset values
        diag = page.evaluate("() => { const el = document.querySelector('#chat-color-diagnostic'); if(!el || !el.dataset) return null; return {lastResponse: el.dataset.lastResponse||'', lastResponseLen: el.dataset.lastResponseLen||'0'} }")
        print(f"Diagnostic dataset: {diag}")

        # Save screenshot and page dump
        screenshot_path = os.path.join(OUT_DIR, "diag_chat_response.png")
        html_path = os.path.join(OUT_DIR, "diag_chat_page.html")
        page.screenshot(path=screenshot_path, full_page=True)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(page.content())
        print(f"Saved screenshot: {screenshot_path}")
        print(f"Saved page dump: {html_path}")

        # Also try to print last few chat messages text
        try:
            msgs = page.locator('[data-testid="chat-message"]').all_inner_texts()
            print(f"Found {len(msgs)} chat messages; last 3:\n" + "\n---\n".join(msgs[-3:]))
        except Exception as e:
            print(f"Could not read chat messages: {e}")

        # Keep the browser open briefly so user can observe
        print("Keeping browser open for 5s then closing...")
        time.sleep(5)
        browser.close()

except Exception as e:
    print(f"Error during headed check: {e}")
    sys.exit(1)

print("Done")

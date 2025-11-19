from playwright.sync_api import sync_playwright

OUT_PATH = r"c:\Aarav\fin_env\Dash\playwright_results.html"
LOG_PATH = r"c:\Aarav\fin_env\Dash\playwright_console.log"

def main():
    messages = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        def on_console(msg):
            try:
                messages.append(f"{msg.type}: {msg.text}")
            except Exception:
                messages.append("console: <unserializable>")

        page.on("console", on_console)

        page.goto("http://127.0.0.1:8050")

        # Try to click reload/refresh buttons if available (best-effort)
        for sel in ["text=Reload cached model", "text=Refresh cached display", "text=Reload"]:
            try:
                page.click(sel, timeout=1200)
            except Exception:
                pass

        # Wait up to 15s for the results header to appear
        try:
            page.wait_for_selector("h4:has-text('Loaded cached results')", timeout=15000)
        except Exception:
            # proceed anyway
            pass

        # Grab the inner HTML of the results area
        try:
            html = page.inner_html("#results-area")
        except Exception:
            html = page.content()

        # Write to output file
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            f.write(html)

        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(messages))

        print("Captured results to:", OUT_PATH)
        print("Captured console to:", LOG_PATH)

        browser.close()

if __name__ == '__main__':
    main()

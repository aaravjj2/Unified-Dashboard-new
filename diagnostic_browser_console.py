"""
Browser console diagnostic for Dash rendering issue.
Captures JavaScript errors and network requests to diagnose why tabs aren't rendering.
"""
from playwright.sync_api import sync_playwright
import time

def diagnose_dash_rendering():
    with sync_playwright() as p:
        # Launch browser in headless mode
        browser = p.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        
        # Capture console messages
        console_logs = []
        def handle_console(msg):
            console_logs.append(f"[{msg.type}] {msg.text}")
        page.on("console", handle_console)
        
        # Capture network requests
        network_requests = []
        def handle_request(request):
            network_requests.append({
                'url': request.url,
                'method': request.method,
                'resource_type': request.resource_type
            })
        page.on("request", handle_request)
        
        # Capture JavaScript errors
        js_errors = []
        def handle_page_error(error):
            js_errors.append(str(error))
        page.on("pageerror", handle_page_error)
        
        print("🌐 Loading http://localhost:8050/...")
        try:
            # Load the page with increased timeout
            page.goto('http://localhost:8050/', timeout=30000, wait_until='networkidle')
            
            # Wait a bit for any async operations
            time.sleep(2)
            
            # Check if layout was fetched
            layout_requests = [r for r in network_requests if '_dash-layout' in r['url']]
            dependencies_requests = [r for r in network_requests if '_dash-dependencies' in r['url']]
            
            # Get page content
            html = page.content()
            
            # Check for specific elements
            has_nav = page.locator('.nav-item').count()
            has_tabs = page.locator('[id="dashboard-tabs"]').count()
            has_loading = '_dash-loading' in html
            
            print(f"\n📊 PAGE ANALYSIS:")
            print(f"  HTML size: {len(html)} bytes")
            print(f"  Nav items found: {has_nav}")
            print(f"  Dashboard tabs found: {has_tabs}")
            print(f"  Still showing loading: {has_loading}")
            
            print(f"\n🌐 NETWORK REQUESTS:")
            print(f"  Total requests: {len(network_requests)}")
            print(f"  Layout requests: {len(layout_requests)}")
            print(f"  Dependencies requests: {len(dependencies_requests)}")
            
            if layout_requests:
                print(f"  ✅ Layout WAS requested")
                for req in layout_requests:
                    print(f"     - {req['method']} {req['url']}")
            else:
                print(f"  ❌ Layout was NEVER requested!")
            
            print(f"\n🖥️  CONSOLE LOGS ({len(console_logs)} messages):")
            for log in console_logs[:20]:  # Show first 20
                print(f"  {log}")
            
            if len(console_logs) > 20:
                print(f"  ... ({len(console_logs) - 20} more messages)")
            
            print(f"\n❌ JAVASCRIPT ERRORS ({len(js_errors)}):")
            for error in js_errors:
                print(f"  {error}")
            
            if not js_errors:
                print(f"  ✅ No JavaScript errors detected")
            
            # Try to find specific Dash renderer elements
            renderer_script = page.locator('script:has-text("dash_renderer")').count()
            react_entry = page.locator('#react-entry-point').count()
            
            print(f"\n🔧 DASH COMPONENTS:")
            print(f"  Dash renderer script: {renderer_script}")
            print(f"  React entry point: {react_entry}")
            
            # Check if React actually mounted
            react_mounted = page.evaluate("""
                () => {
                    const entry = document.getElementById('react-entry-point');
                    if (!entry) return false;
                    return entry.children.length > 0 && entry.children[0].className !== '_dash-loading';
                }
            """)
            print(f"  React mounted: {react_mounted}")
            
            # Check for any data attributes that might indicate layout status
            data_dash_config = page.evaluate("""
                () => {
                    const scripts = Array.from(document.querySelectorAll('script'));
                    const configScript = scripts.find(s => s.text.includes('dash_clientside'));
                    return configScript ? configScript.text.substring(0, 500) : null;
                }
            """)
            
            if data_dash_config:
                print(f"\n⚙️  DASH CONFIG (first 500 chars):")
                print(f"  {data_dash_config}")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
        
        finally:
            browser.close()

if __name__ == '__main__':
    diagnose_dash_rendering()

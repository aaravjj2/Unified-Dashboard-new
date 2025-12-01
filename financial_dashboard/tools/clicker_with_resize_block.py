"""
Playwright clicker that injects a patch to block resize dispatches and ignore future resize listeners.
This helps avoid DataTable handleResize recursion causing 'Maximum call stack size exceeded'.

Run: python3 tools/clicker_with_resize_block.py
"""
from playwright.sync_api import sync_playwright, TimeoutError
import time, os, signal, sys
from datetime import datetime

WORKDIR = os.path.dirname(os.path.dirname(__file__))
DIAG_DIR = os.path.join(WORKDIR, 'diagnostics')
os.makedirs(DIAG_DIR, exist_ok=True)
BUTTON_SELECTOR = '#run-trends-analysis'
PAGE_URL = 'http://localhost:8050'
CLICK_INTERVAL = 5  # seconds between clicks
keep_running = True


def timestamp():
    return datetime.utcnow().strftime('%Y%m%dT%H%M%S')


def handle_sigint(sig, frame):
    global keep_running
    print('\nReceived SIGINT, stopping clicker...')
    keep_running = False


signal.signal(signal.SIGINT, handle_sigint)


def save_diagnostics(page, console_messages, reason='unknown'):
    ts = timestamp()
    base = os.path.join(DIAG_DIR, f'diag_{ts}_{reason}')
    try:
        content = page.content()
        with open(base + '.html', 'w', encoding='utf-8') as f:
            f.write(content)
        page.screenshot(path=base + '.png', full_page=True)
    except Exception as e:
        print(f'Failed to save page snapshot: {e}')
    try:
        with open(base + '.console.log', 'w', encoding='utf-8') as f:
            f.write('\n'.join(console_messages[-500:]))
    except Exception as e:
        print(f'Failed to save console log: {e}')
    print(f'[diag] Saved diagnostics to {base}.*')


def ensure_page(page):
    try:
        print(f'[nav] Going to {PAGE_URL}...')
        page.goto(PAGE_URL, wait_until='networkidle', timeout=30000)
        time.sleep(1)
        return True
    except Exception as e:
        print(f'[nav error] {e}')
        return False


RESIZE_PATCH = r"""
(() => {
  if (window.__resize_patch_installed) return 'already';
  window.__resize_patch_installed = true;
  // Prevent resize events from invoking handlers
  window.__orig_dispatchEvent = window.dispatchEvent;
  window.dispatchEvent = function(ev) {
    try {
      if (ev && ev.type === 'resize') return true;
    } catch (e) {}
    return window.__orig_dispatchEvent.call(this, ev);
  };
  // Ignore future addEventListener calls for 'resize'
  window.__orig_addEventListener = window.addEventListener;
  window.addEventListener = function(type, handler, opts) {
    try {
      if (type === 'resize') return; // noop
    } catch (e) {}
    return window.__orig_addEventListener.call(this, type, handler, opts);
  };
  // Also set onresize to null
  try { window.onresize = null; } catch (e) {}
  return 'patched';
})();
"""

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    console_messages = []

    def on_console(msg):
        text = msg.text
        typ = msg.type
        entry = f"[{datetime.utcnow().isoformat()}] console.{typ}: {text}"
        print(entry)
        console_messages.append(entry)

    page.on('console', on_console)
    page.on('pageerror', lambda e: print(f'[{datetime.utcnow().isoformat()}] pageerror: {e}'))

    if not ensure_page(page):
        print('[error] Initial navigation failed; attempting browser restart...')
        try:
            browser.close()
        except:
            pass
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.on('console', on_console)
        page.on('pageerror', lambda e: print(f'[{datetime.utcnow().isoformat()}] pageerror: {e}'))
        if not ensure_page(page):
            print('[fatal] Could not reach app; exiting')
            sys.exit(1)

    # Inject resize-block patch
    try:
        res = page.evaluate(RESIZE_PATCH)
        print(f'[patch] resize patch result: {res}')
    except Exception as e:
        print(f'[patch error] {e}')

    print('Starting robust click loop with resize-block. Press Ctrl+C in this terminal to stop.')
    iteration = 0
    while keep_running:
        iteration += 1
        print(f'--- Iteration {iteration} @ {datetime.utcnow().isoformat()} ---')
        try:
            btns = page.locator(BUTTON_SELECTOR)
            count = btns.count()
            if count == 0:
                print('[warn] Run button not found')
            else:
                print(f'[action] Clicking run button (found {count})')
                start = time.time()
                btns.first.click(timeout=10000)
                elapsed = (time.time()-start)*1000
                print(f'[info] Click executed in {elapsed:.0f}ms')

            # Wait & monitor
            for i in range(int(CLICK_INTERVAL*10)):
                if not keep_running:
                    break
                try:
                    alive = page.evaluate('''() => { return !!document && document.readyState }''')
                except Exception as e:
                    print(f'[warn] Page evaluate failed: {e}')
                    save_diagnostics(page, console_messages, reason='evaluate_failure')
                    try:
                        print('[action] Attempting page.reload()')
                        page.reload(wait_until='networkidle', timeout=15000)
                        time.sleep(1)
                        print('[info] Reload succeeded')
                    except Exception as e2:
                        print(f'[error] Reload failed: {e2}')
                        save_diagnostics(page, console_messages, reason='reload_failed')
                        try:
                            browser.close()
                        except:
                            pass
                        print('[action] Restarting browser')
                        browser = p.chromium.launch(headless=False)
                        page = browser.new_page()
                        page.on('console', on_console)
                        page.on('pageerror', lambda e: print(f'[{datetime.utcnow().isoformat()}] pageerror: {e}'))
                        if not ensure_page(page):
                            print('[fatal] Could not re-open page after crash; saving diag and exiting loop')
                            save_diagnostics(page, console_messages, reason='reopen_failed')
                            keep_running = False
                            break
                time.sleep(0.1)
        except TimeoutError as te:
            print(f'[timeout] {te}')
            save_diagnostics(page, console_messages, reason='timeout')
        except KeyboardInterrupt:
            print('\nKeyboardInterrupt received')
            keep_running = False
            break
        except Exception as e:
            print(f'[exception] {e}')
            save_diagnostics(page, console_messages, reason='exception')

    print('Shutting down: saving final diagnostics')
    try:
        save_diagnostics(page, console_messages, reason='final')
    except:
        pass
    try:
        browser.close()
    except:
        pass

print('Clicker terminated')

#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import time

OUT_HTML='analysis_run_snapshot.html'
OUT_PNG='analysis_run_snapshot.png'
OUT_LOG='analysis_run_console.log'

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context()
    page = context.new_page()

    logs = []
    def on_console(msg):
        try:
            logs.append(f"{msg.type}: {msg.text}")
        except Exception:
            pass
    page.on('console', on_console)

    print('goto app')
    page.goto('http://localhost:8054', wait_until='networkidle', timeout=60000)
    time.sleep(1)

    # Wait for run button to be attached, then ensure it's visible and click.
    try:
        # wait for the element to exist in DOM (attached) rather than visible
        page.wait_for_selector('#attr-run-button', state='attached', timeout=8000)
        print('run button attached')

        # Force inline styles to make it appear clickable for automation, then try a normal click
        page.evaluate("""
            (function(){
                try{
                    var b = document.getElementById('attr-run-button');
                    if(b){
                        b.style.display = 'inline-block';
                        b.style.visibility = 'visible';
                        b.style.opacity = 1;
                        b.removeAttribute('hidden');
                        b.scrollIntoView({behavior:'auto', block:'center', inline:'center'});
                    }
                    var res = document.getElementById('attr-results-container');
                    if(res){ res.style.display='block'; res.style.visibility='visible'; res.style.opacity=1; }
                }catch(e){ console.warn('force style failed', e); }
            })();
        """
        )

        try:
            page.click('#attr-run-button', timeout=3000)
            print('clicked run button (normal click)')
        except Exception:
            # Fallback: perform a DOM click via evaluate which doesn't require Playwright visibility
            try:
                page.evaluate("document.getElementById('attr-run-button') && document.getElementById('attr-run-button').click();")
                print('clicked run button (DOM click fallback)')
            except Exception as e:
                print('failed to click run button:', e)
    except Exception as e:
        print('run button not found / attached:', e)

    # After clicking, poll for the portfolio summary to be populated as a
    # reliable indicator that the callback completed and results were rendered.
    try:
        success = False
        for _ in range(20):
            try:
                # check innerText length of portfolio summary
                text_len = page.evaluate("() => { const el = document.getElementById('attr-portfolio-summary'); return el ? el.innerText.trim().length : 0 }")
                if text_len and int(text_len) > 0:
                    success = True
                    break
            except Exception:
                pass
            time.sleep(0.5)

        if success:
            print('portfolio summary populated')
        else:
            print('results container not populated after wait')
    except Exception as e:
        print('error while waiting for results content:', e)

    # short wait to let network finish
    time.sleep(2)

    page.screenshot(path=OUT_PNG, full_page=True)
    with open(OUT_HTML, 'w', encoding='utf-8') as f:
        f.write(page.content())
    with open(OUT_LOG, 'w', encoding='utf-8') as f:
        f.write('\n'.join(logs))

    print('saved', OUT_HTML, OUT_PNG, OUT_LOG)
    browser.close()

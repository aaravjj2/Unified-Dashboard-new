#!/usr/bin/env python3
"""
Comprehensive Market Forecast Test - All 4 Tickers
Tests AAPL, MSFT, GOOGL, NVDA and auto-analyzes screenshots
"""
from pathlib import Path
import time
import sys
import os
import json
from datetime import datetime
import re

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "reports" / "systemfix" / "playwright"
DOM_DIR = REPO / "reports" / "systemfix" / "dom"
ANALYSIS_DIR = REPO / "reports" / "systemfix" / "analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DOM_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

from playwright.sync_api import sync_playwright

PORT = os.environ.get('PORT', '8050')
URL = f"http://localhost:{PORT}"

TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'NVDA']

def analyze_dom(dom_path, ticker_expected):
    """
    Analyze DOM to extract visible ticker from chart title and dropdown
    Returns dict with analysis results
    """
    try:
        html_content = dom_path.read_text()
        
        # Look for ticker in chart title (various patterns)
        title_patterns = [
            rf'{ticker_expected}\s+Price\s+Forecast',
            rf'Forecast.*{ticker_expected}',
            rf'{ticker_expected}.*Forecast',
        ]
        
        found_in_title = any(re.search(p, html_content, re.IGNORECASE) for p in title_patterns)
        
        # Check all tickers
        all_found = [t for t in TICKERS if re.search(rf'\b{t}\b', html_content)]
        
        # Look for selected value in dropdown
        dropdown_match = re.search(r'id="mf-ticker-input"[^>]*value="([^"]+)"', html_content)
        dropdown_value = dropdown_match.group(1) if dropdown_match else None
        
        # Also check react-select value
        select_match = re.search(rf'data-value="{ticker_expected}"[^>]*class="[^"]*--is-selected', html_content)
        found_selected = select_match is not None
        
        return {
            'expected_ticker': ticker_expected,
            'found_in_title': found_in_title,
            'dropdown_value': dropdown_value,
            'found_selected': found_selected,
            'all_tickers_in_dom': all_found,
            'match': found_in_title or (dropdown_value == ticker_expected),
        }
    except Exception as e:
        return {
            'expected_ticker': ticker_expected,
            'error': str(e),
            'match': False
        }

def test_ticker(page, ticker, ts):
    """Test a single ticker: select, run, capture, analyze"""
    print(f"\n{'='*60}")
    print(f"Testing ticker: {ticker}")
    print(f"{'='*60}")
    
    try:
        # Navigate to Market Forecast tab
        mf_tab = page.locator("a.nav-link:has-text('Market Forecast')")
        if mf_tab.count() == 0:
            print(f"❌ Market Forecast tab not found")
            return None
        mf_tab.first.click()
        page.wait_for_timeout(1000)
        
        # Select ticker from dropdown
        dropdown = page.locator("#mf-ticker-input")
        if dropdown.count() > 0:
            dropdown.first.click()
            page.wait_for_timeout(500)
            
            # Click the option with this ticker
            option = page.locator(f"div[role='option']:has-text('{ticker}')")
            if option.count() > 0:
                option.first.click()
                print(f"✓ Selected {ticker} from dropdown")
            else:
                print(f"⚠ Could not find {ticker} option - trying to type")
                # Fallback: type ticker
                try:
                    inp = page.locator("#mf-ticker-input input")
                    inp.fill(ticker)
                    page.wait_for_timeout(300)
                except:
                    pass
        
        page.wait_for_timeout(800)
        
        # Click Run Forecast button
        run_candidates = ['#mf-run-btn', "button:has-text('Run Forecast')"]
        clicked = False
        for sel in run_candidates:
            try:
                el = page.locator(sel)
                if el.count() > 0:
                    el.first.click()
                    print(f"✓ Clicked run button: {sel}")
                    clicked = True
                    break
            except Exception:
                continue
        
        if not clicked:
            print("❌ Run Forecast button not found")
            return None
        
        # Wait for forecast to complete
        page.wait_for_timeout(3000)
        
        # Save screenshot
        ss_file = OUT_DIR / f"{ticker}_forecast_{ts}.png"
        page.screenshot(path=str(ss_file), full_page=True)
        print(f"✓ Saved screenshot: {ss_file.name}")
        
        # Save DOM
        dom_file = DOM_DIR / f"{ticker}_forecast_{ts}.html"
        dom_file.write_text(page.content())
        print(f"✓ Saved DOM: {dom_file.name}")
        
        # Read client-side store
        store_data = None
        try:
            store_data = page.evaluate("""
                () => {
                    try {
                        if (window.__mf_forecast_store__) return window.__mf_forecast_store__;
                    } catch(e){}
                    try {
                        const dbg = document.getElementById('mf-store-debug');
                        if (dbg) {
                            const txt = dbg.textContent || dbg.innerText || '';
                            if (txt) return JSON.parse(txt);
                        }
                    } catch(e){}
                    return null;
                }
            """)
            if store_data:
                store_file = OUT_DIR / f"{ticker}_store_{ts}.json"
                store_file.write_text(json.dumps(store_data, indent=2))
                print(f"✓ Saved store: {store_file.name}")
            else:
                print(f"⚠ No store data found for {ticker}")
        except Exception as e:
            print(f"⚠ Error reading store: {e}")
        
        # Analyze DOM
        analysis = analyze_dom(dom_file, ticker)
        analysis['ticker'] = ticker
        analysis['timestamp'] = ts
        analysis['screenshot'] = str(ss_file)
        analysis['dom'] = str(dom_file)
        analysis['store_found'] = store_data is not None
        
        if store_data and isinstance(store_data, list) and len(store_data) > 0:
            # Extract ticker from first result
            first_result = store_data[0]
            if isinstance(first_result, dict):
                analysis['store_ticker'] = first_result.get('ticker', 'UNKNOWN')
        
        print(f"\n📊 Analysis for {ticker}:")
        print(f"  - Match: {'✅ YES' if analysis.get('match') else '❌ NO'}")
        print(f"  - Found in title: {analysis.get('found_in_title', False)}")
        print(f"  - Dropdown value: {analysis.get('dropdown_value', 'N/A')}")
        print(f"  - Store ticker: {analysis.get('store_ticker', 'N/A')}")
        
        return analysis
        
    except Exception as e:
        print(f"❌ Error testing {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'ticker': ticker,
            'error': str(e),
            'match': False
        }

def run_all_tests(headless=True):
    """Run tests for all 4 tickers"""
    ts = int(time.time())
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()
        
        try:
            # Initial navigation
            print(f"🌐 Navigating to {URL}")
            page.goto(URL, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(2000)
            
            # Test each ticker
            for ticker in TICKERS:
                result = test_ticker(page, ticker, ts)
                if result:
                    results.append(result)
                page.wait_for_timeout(1000)  # Brief pause between tests
            
        finally:
            try:
                context.close()
                browser.close()
            except:
                pass
    
    # Save comprehensive report
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'url': URL,
        'tickers_tested': TICKERS,
        'results': results,
        'summary': {
            'total': len(results),
            'passed': sum(1 for r in results if r.get('match')),
            'failed': sum(1 for r in results if not r.get('match')),
            'errors': sum(1 for r in results if 'error' in r)
        }
    }
    
    report_file = ANALYSIS_DIR / f"forecast_test_report_{ts}.json"
    report_file.write_text(json.dumps(report, indent=2))
    
    print(f"\n{'='*60}")
    print("📋 TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total tickers tested: {report['summary']['total']}")
    print(f"✅ Passed (ticker matched): {report['summary']['passed']}")
    print(f"❌ Failed (ticker mismatch): {report['summary']['failed']}")
    print(f"⚠️  Errors: {report['summary']['errors']}")
    print(f"\nFull report saved: {report_file}")
    
    # Print detailed results
    print(f"\n{'='*60}")
    print("DETAILED RESULTS")
    print(f"{'='*60}")
    for r in results:
        ticker = r.get('ticker', 'UNKNOWN')
        match = r.get('match', False)
        status = "✅ PASS" if match else "❌ FAIL"
        print(f"\n{ticker}: {status}")
        if 'error' in r:
            print(f"  Error: {r['error']}")
        else:
            print(f"  Found in title: {r.get('found_in_title', False)}")
            print(f"  Dropdown value: {r.get('dropdown_value', 'N/A')}")
            print(f"  Store ticker: {r.get('store_ticker', 'N/A')}")
            print(f"  Screenshot: {Path(r['screenshot']).name}")
    
    return 0 if report['summary']['failed'] == 0 else 1

if __name__ == '__main__':
    headless = True
    if '--headed' in sys.argv or '--headful' in sys.argv:
        headless = False
    
    rc = run_all_tests(headless=headless)
    sys.exit(rc)

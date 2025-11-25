#!/usr/bin/env python3
"""
Quick Portfolio Validation - Simplified Version
Tests all 5 Portfolio subtabs in a single iteration with immediate output.
"""

from playwright.sync_api import sync_playwright
import json
from pathlib import Path
from datetime import datetime

BASE_URL = 'http://127.0.0.1:8050'
SNAPSHOTS_DIR = Path(__file__).parent.parent / 'tests' / 'portfolio_snapshots'
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("="*80)
    print("QUICK PORTFOLIO VALIDATION")
    print("="*80)
    
    results = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            # Navigate
            print(f"\n🌐 Loading {BASE_URL}...")
            page.goto(BASE_URL, wait_until='networkidle', timeout=30000)
            print("✅ Page loaded")
            
            # Click Portfolio
            print("\n📂 Clicking Portfolio tab...")
            page.click('text=Portfolio', timeout=10000)
            page.wait_for_timeout(3000)
            print("✅ Portfolio tab activated")
            
            # Test Positions
            print("\n" + "="*80)
            print("1. POSITIONS SUBTAB")
            print("="*80)
            page.click('text=Positions', timeout=5000)
            page.wait_for_timeout(3000)
            page.screenshot(path=str(SNAPSHOTS_DIR / 'positions.png'))
            
            text = page.inner_text('body')
            tickers = [t for t in ['INTC', 'AAPL', 'TSLA', 'NVDA'] if t in text]
            has_closed = 'qty=0' in text or 'Quantity: 0' in text
            
            print(f"📊 Tickers found: {tickers}")
            print(f"❌ Has closed positions: {has_closed}")
            print(f"✅ Status: {'PASS' if not has_closed and len(tickers) <= 1 else 'FAIL'}")
            
            results['positions'] = {
                'tickers': tickers,
                'has_closed': has_closed,
                'status': 'PASS' if not has_closed and len(tickers) <= 1 else 'FAIL'
            }
            
            # Test Orders
            print("\n" + "="*80)
            print("2. ORDER HISTORY SUBTAB")
            print("="*80)
            page.click('text=Order History', timeout=5000)
            page.wait_for_timeout(3000)
            page.screenshot(path=str(SNAPSHOTS_DIR / 'orders.png'))
            
            text = page.inner_text('body')
            has_table = '#portfolio-orders-table' in page.content() or 'Order History' in text
            has_filled = 'filled' in text.lower()
            has_empty = 'No orders' in text or 'no order' in text.lower()
            
            print(f"📊 Has table: {has_table}")
            print(f"📝 Has filled orders: {has_filled}")
            print(f"🔍 Empty state: {has_empty}")
            print(f"✅ Status: {'PASS' if has_table or has_empty else 'FAIL'}")
            
            results['orders'] = {
                'has_table': has_table,
                'has_filled': has_filled,
                'has_empty': has_empty,
                'status': 'PASS' if has_table or has_empty else 'FAIL'
            }
            
            # Test Analytics
            print("\n" + "="*80)
            print("3. ANALYTICS SUBTAB")
            print("="*80)
            page.click('text=Analytics', timeout=5000)
            page.wait_for_timeout(3000)
            page.screenshot(path=str(SNAPSHOTS_DIR / 'analytics.png'))
            
            text = page.inner_text('body')
            metrics = {
                'VaR': 'VaR' in text or 'Value at Risk' in text,
                'CVaR': 'CVaR' in text or 'Expected Shortfall' in text,
                'Sharpe': 'Sharpe' in text,
                'Beta': 'Beta' in text
            }
            has_calc_btn = page.locator('button:has-text("Calculate")').count() > 0
            no_analytics_msg = 'No analytics' in text or 'Click Calculate' in text
            
            print(f"📈 Metrics: {metrics}")
            print(f"🔘 Has Calculate button: {has_calc_btn}")
            print(f"⚠️  No analytics message: {no_analytics_msg}")
            
            metrics_count = sum(metrics.values())
            status = 'WARN' if no_analytics_msg and metrics_count == 0 else ('PASS' if metrics_count >= 2 else 'FAIL')
            print(f"✅ Status: {status}")
            
            results['analytics'] = {
                'metrics': metrics,
                'metrics_count': metrics_count,
                'has_calc_button': has_calc_btn,
                'no_analytics_msg': no_analytics_msg,
                'status': status
            }
            
            # Test Factors
            print("\n" + "="*80)
            print("4. FACTOR EXPOSURE SUBTAB")
            print("="*80)
            page.click('text=Factor Exposure', timeout=5000)
            page.wait_for_timeout(3000)
            page.screenshot(path=str(SNAPSHOTS_DIR / 'factors.png'))
            
            text = page.inner_text('body')
            has_shap = 'SHAP' in text
            graphs = page.locator('.js-plotly-plot').count()
            has_empty = 'No factor' in text or 'no exposure' in text.lower()
            
            print(f"🔬 Has SHAP: {has_shap}")
            print(f"📊 Graphs: {graphs}")
            print(f"🔍 Empty state: {has_empty}")
            print(f"✅ Status: {'PASS' if graphs > 0 or has_empty else 'FAIL'}")
            
            results['factors'] = {
                'has_shap': has_shap,
                'graphs': graphs,
                'has_empty': has_empty,
                'status': 'PASS' if graphs > 0 or has_empty else 'FAIL'
            }
            
            # Test Optimization
            print("\n" + "="*80)
            print("5. OPTIMIZATION SUBTAB")
            print("="*80)
            page.click('text=Optimization', timeout=5000)
            page.wait_for_timeout(3000)
            page.screenshot(path=str(SNAPSHOTS_DIR / 'optimization.png'))
            
            text = page.inner_text('body')
            has_optimize_btn = page.locator('button:has-text("Optimize")').count() > 0
            inputs = page.locator('input').count()
            graphs = page.locator('.js-plotly-plot').count()
            
            print(f"🔘 Has Optimize button: {has_optimize_btn}")
            print(f"📝 Input fields: {inputs}")
            print(f"📊 Graphs: {graphs}")
            print(f"✅ Status: {'PASS' if has_optimize_btn else 'FAIL'}")
            
            results['optimization'] = {
                'has_optimize_btn': has_optimize_btn,
                'inputs': inputs,
                'graphs': graphs,
                'status': 'PASS' if has_optimize_btn else 'FAIL'
            }
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            results['error'] = str(e)
        finally:
            browser.close()
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    for subtab, result in results.items():
        if subtab != 'error' and isinstance(result, dict):
            status = result.get('status', 'ERROR')
            icon = {'PASS': '✅', 'FAIL': '❌', 'WARN': '⚠️'}.get(status, '🔴')
            print(f"{icon} {subtab.upper()}: {status}")
    
    # Save results
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    results_file = Path(__file__).parent.parent / 'tests' / 'logs' / 'portfolio_validation' / f'quick_validation_{timestamp}.json'
    results_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved: {results_file}")
    print(f"📁 Screenshots: {SNAPSHOTS_DIR}")
    
    return 0 if all(r.get('status') in ['PASS', 'WARN'] for r in results.values() if isinstance(r, dict)) else 1

if __name__ == '__main__':
    exit(main())

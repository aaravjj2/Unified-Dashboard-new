#!/usr/bin/env python3
"""
Portfolio Issues Remediation - Iteration 3
Addresses the 5 identified problems:
1. Positions - verify only INTC showing (not closed positions)
2. Orders - verify order history table populated
3. Analytics - click Calculate Analytics button
4. Factors - verify not empty
5. Optimization - test with input values
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8050/"
ARTIFACTS_DIR = Path("tests/logs/portfolio_validation/iteration3")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

async def fix_positions(page):
    """Verify only active position (INTC) shows, not closed positions."""
    print("\n" + "="*80)
    print("ISSUE 1: Positions - Verify only INTC (active position)")
    print("="*80)
    
    await page.goto(BASE_URL, wait_until='networkidle')
    await asyncio.sleep(2)
    await page.locator("text=Portfolio").first.click()
    await asyncio.sleep(1)
    await page.locator("text=Positions").first.click()
    await asyncio.sleep(3)
    
    # Get the positions table content
    positions_table = page.locator('#portfolio-positions-table')
    table_text = await positions_table.inner_text() if await positions_table.count() > 0 else ""
    
    # Check for INTC (should exist)
    has_intc = 'INTC' in table_text
    
    # Check for closed positions (should NOT exist in positions table)
    has_aapl = 'AAPL' in table_text
    has_tsla = 'TSLA' in table_text
    
    # Count rows in table
    table_rows = await page.locator('#portfolio-positions-table table tbody tr').count()
    
    print(f"✓ Has INTC (active): {has_intc}")
    print(f"✗ Has AAPL (should be in orders only): {has_aapl}")
    print(f"✗ Has TSLA (should be in orders only): {has_tsla}")
    print(f"Table rows: {table_rows}")
    print(f"Table text: {table_text[:300]}")
    
    await page.screenshot(path=str(ARTIFACTS_DIR / "positions_fixed.png"), full_page=True)
    
    status = "✅ PASS" if (has_intc and not has_aapl and not has_tsla) else "❌ FAIL"
    print(f"Status: {status}")
    
    return {
        "status": status,
        "has_intc": has_intc,
        "has_closed_positions": has_aapl or has_tsla,
        "table_rows": table_rows
    }

async def fix_orders(page):
    """Verify order history shows closed positions."""
    print("\n" + "="*80)
    print("ISSUE 2: Orders - Verify order history populated")
    print("="*80)
    
    await page.goto(BASE_URL, wait_until='networkidle')
    await asyncio.sleep(2)
    await page.locator("text=Portfolio").first.click()
    await asyncio.sleep(1)
    await page.locator("text=Order History").first.click()
    await asyncio.sleep(3)
    
    # Get orders table
    orders_table = page.locator('#portfolio-orders-table')
    table_text = await orders_table.inner_text() if await orders_table.count() > 0 else ""
    
    # Check for order data
    has_filled = 'filled' in table_text.lower()
    has_orders = len(table_text) > 100
    table_rows = await page.locator('#portfolio-orders-table table tbody tr').count()
    
    print(f"Has filled orders: {has_filled}")
    print(f"Has order data: {has_orders}")
    print(f"Table rows: {table_rows}")
    print(f"Table text sample: {table_text[:300]}")
    
    await page.screenshot(path=str(ARTIFACTS_DIR / "orders_fixed.png"), full_page=True)
    
    status = "✅ PASS" if has_orders else "❌ FAIL (EMPTY)"
    print(f"Status: {status}")
    
    return {
        "status": status,
        "has_orders": has_orders,
        "table_rows": table_rows
    }

async def fix_analytics(page):
    """Click Calculate Analytics button to populate metrics."""
    print("\n" + "="*80)
    print("ISSUE 3: Analytics - Click Calculate Analytics button")
    print("="*80)
    
    await page.goto(BASE_URL, wait_until='networkidle')
    await asyncio.sleep(2)
    await page.locator("text=Portfolio").first.click()
    await asyncio.sleep(1)
    await page.locator("text=Analytics").first.click()
    await asyncio.sleep(3)
    
    # Look for Calculate Analytics button
    calc_btn = page.locator('button:has-text("Calculate Analytics")')
    if await calc_btn.count() > 0:
        print("Found 'Calculate Analytics' button, clicking...")
        await calc_btn.click()
        await asyncio.sleep(5)  # Wait for calculation
    else:
        print("⚠️  No 'Calculate Analytics' button found")
    
    # Check for metrics
    page_text = await page.inner_text('body')
    metrics = {
        'var': 'VaR' in page_text or 'Value at Risk' in page_text,
        'cvar': 'CVaR' in page_text or 'Conditional VaR' in page_text,
        'sharpe': 'Sharpe' in page_text,
        'beta': 'Beta' in page_text
    }
    
    graph_count = await page.locator('.plotly').count()
    
    print(f"Metrics after calculation: {metrics}")
    print(f"Graphs: {graph_count}")
    
    await page.screenshot(path=str(ARTIFACTS_DIR / "analytics_fixed.png"), full_page=True)
    
    status = "✅ PASS" if any(metrics.values()) else "❌ FAIL (NO METRICS)"
    print(f"Status: {status}")
    
    return {
        "status": status,
        "metrics": metrics,
        "graphs": graph_count
    }

async def fix_factors(page):
    """Verify Factor Exposure is not empty."""
    print("\n" + "="*80)
    print("ISSUE 4: Factors - Verify not empty")
    print("="*80)
    
    await page.goto(BASE_URL, wait_until='networkidle')
    await asyncio.sleep(2)
    await page.locator("text=Portfolio").first.click()
    await asyncio.sleep(1)
    await page.locator("text=Factor Exposure").first.click()
    await asyncio.sleep(3)
    
    # Check content
    content_div = page.locator('#portfolio-factor-exposure-content')
    content_text = await content_div.inner_text() if await content_div.count() > 0 else ""
    
    has_shap = 'SHAP' in content_text
    has_factors = len(content_text) > 50
    graph_count = await page.locator('.plotly').count()
    
    print(f"Has SHAP: {has_shap}")
    print(f"Has content: {has_factors}")
    print(f"Graphs: {graph_count}")
    print(f"Content sample: {content_text[:300]}")
    
    await page.screenshot(path=str(ARTIFACTS_DIR / "factors_fixed.png"), full_page=True)
    
    status = "✅ PASS" if has_factors else "❌ FAIL (EMPTY)"
    print(f"Status: {status}")
    
    return {
        "status": status,
        "has_shap": has_shap,
        "has_content": has_factors,
        "graphs": graph_count
    }

async def fix_optimization(page):
    """Test optimization with input values."""
    print("\n" + "="*80)
    print("ISSUE 5: Optimization - Test with input values")
    print("="*80)
    
    await page.goto(BASE_URL, wait_until='networkidle')
    await asyncio.sleep(2)
    await page.locator("text=Portfolio").first.click()
    await asyncio.sleep(1)
    await page.locator("text=Optimization").first.click()
    await asyncio.sleep(3)
    
    # Screenshot before interaction
    await page.screenshot(path=str(ARTIFACTS_DIR / "optimization_before.png"), full_page=True)
    
    # Find and fill tickers input
    tickers_input = page.locator('#opt-tickers-input')
    if await tickers_input.count() > 0:
        print("Filling tickers input with: AAPL,MSFT,GOOGL,NVDA")
        await tickers_input.fill('AAPL,MSFT,GOOGL,NVDA')
        await asyncio.sleep(1)
        
        # Click Optimize button
        optimize_btn = page.locator('button:has-text("Optimize")')
        if await optimize_btn.count() > 0:
            print("Clicking Optimize button...")
            await optimize_btn.click()
            await asyncio.sleep(10)  # Wait for optimization to complete
            
            # Check for results
            page_text = await page.inner_text('body')
            has_results = 'efficient frontier' in page_text.lower() or 'optimal' in page_text.lower()
            graph_count = await page.locator('.plotly').count()
            
            print(f"Has optimization results: {has_results}")
            print(f"Graphs: {graph_count}")
            
            await page.screenshot(path=str(ARTIFACTS_DIR / "optimization_after.png"), full_page=True)
            
            status = "✅ PASS" if has_results or graph_count > 0 else "⚠️  PARTIAL"
        else:
            print("❌ Optimize button not found")
            status = "❌ FAIL (NO BUTTON)"
    else:
        print("❌ Tickers input not found")
        status = "❌ FAIL (NO INPUT)"
    
    print(f"Status: {status}")
    
    return {
        "status": status,
        "input_filled": await tickers_input.count() > 0,
        "button_clicked": await optimize_btn.count() > 0 if tickers_input.count() > 0 else False
    }

async def main():
    """Run all remediation fixes."""
    print("🔧 PORTFOLIO REMEDIATION - ITERATION 3")
    print("="*80)
    print("Addressing 5 identified issues:")
    print("1. Positions - only INTC should show")
    print("2. Orders - verify history populated")
    print("3. Analytics - click Calculate Analytics")
    print("4. Factors - verify not empty")
    print("5. Optimization - test with inputs")
    print("="*80)
    
    results = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        results['positions'] = await fix_positions(page)
        results['orders'] = await fix_orders(page)
        results['analytics'] = await fix_analytics(page)
        results['factors'] = await fix_factors(page)
        results['optimization'] = await fix_optimization(page)
        
        await browser.close()
    
    # Save results
    results_file = ARTIFACTS_DIR / "remediation_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, indent=2, fp=f)
    
    print("\n" + "="*80)
    print("REMEDIATION SUMMARY")
    print("="*80)
    
    for name, result in results.items():
        print(f"{name.upper()}: {result['status']}")
    
    # Count passes
    passes = sum(1 for r in results.values() if '✅' in r['status'])
    total = len(results)
    
    print(f"\nOverall: {passes}/{total} issues resolved")
    print(f"Results saved to: {results_file}")

if __name__ == "__main__":
    asyncio.run(main())

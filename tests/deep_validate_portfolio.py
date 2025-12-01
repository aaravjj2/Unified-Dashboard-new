#!/usr/bin/env python3
"""
Deep Portfolio Content Validation
Analyzes actual rendered content in each subtab.
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8050/"
ARTIFACTS_DIR = Path("tests/logs/portfolio_validation")

async def deep_validate_positions(page):
    """Deep validation of Positions subtab."""
    print("\n" + "="*80)
    print("DEEP VALIDATION: Positions Subtab")
    print("="*80)
    
    # Navigate and click
    await page.goto(BASE_URL, wait_until='networkidle')
    await asyncio.sleep(2)
    await page.locator("text=Portfolio").first.click()
    await asyncio.sleep(1)
    await page.locator("text=Positions").first.click()
    await asyncio.sleep(3)
    
    # Check for table/data
    page_text = await page.inner_text('body')
    
    # Look for specific elements
    has_positions_table = await page.locator('#portfolio-positions-table').count() > 0
    has_datatable = await page.locator('.dash-table').count() > 0
    
    # Check for ticker symbols
    tickers_found = []
    for ticker in ['INTC', 'AAPL', 'TSLA', 'MSFT', 'GOOGL', 'NVDA']:
        if ticker in page_text:
            tickers_found.append(ticker)
    
    # Check for "No positions" or empty state
    is_empty = "No positions" in page_text or "no data" in page_text.lower()
    
    print(f"Has positions table element: {has_positions_table}")
    print(f"Has DataTable: {has_datatable}")
    print(f"Tickers found: {tickers_found}")
    print(f"Is empty state: {is_empty}")
    print(f"Page text sample: {page_text[:500]}")
    
    await page.screenshot(path=str(ARTIFACTS_DIR / "positions_deep_validation.png"), full_page=True)
    
    return {
        "has_table": has_positions_table or has_datatable,
        "tickers": tickers_found,
        "is_empty": is_empty,
        "positions_count": len(tickers_found)
    }

async def deep_validate_orders(page):
    """Deep validation of Order History subtab."""
    print("\n" + "="*80)
    print("DEEP VALIDATION: Order History Subtab")
    print("="*80)
    
    await page.goto(BASE_URL, wait_until='networkidle')
    await asyncio.sleep(2)
    await page.locator("text=Portfolio").first.click()
    await asyncio.sleep(1)
    await page.locator("text=Order History").first.click()
    await asyncio.sleep(3)
    
    page_text = await page.inner_text('body')
    
    has_orders_table = await page.locator('#portfolio-orders-table').count() > 0
    has_datatable = await page.locator('.dash-table').count() > 0
    
    # Check for order-related keywords
    has_orders = "filled" in page_text.lower() or "order" in page_text.lower()
    is_empty = "No orders" in page_text or "no data" in page_text.lower()
    
    print(f"Has orders table element: {has_orders_table}")
    print(f"Has DataTable: {has_datatable}")
    print(f"Has order data: {has_orders}")
    print(f"Is empty state: {is_empty}")
    print(f"Page text sample: {page_text[:500]}")
    
    await page.screenshot(path=str(ARTIFACTS_DIR / "orders_deep_validation.png"), full_page=True)
    
    return {
        "has_table": has_orders_table or has_datatable,
        "has_orders": has_orders,
        "is_empty": is_empty
    }

async def deep_validate_analytics(page):
    """Deep validation of Analytics subtab."""
    print("\n" + "="*80)
    print("DEEP VALIDATION: Analytics Subtab")
    print("="*80)
    
    await page.goto(BASE_URL, wait_until='networkidle')
    await asyncio.sleep(2)
    await page.locator("text=Portfolio").first.click()
    await asyncio.sleep(1)
    await page.locator("text=Analytics").first.click()
    await asyncio.sleep(3)
    
    page_text = await page.inner_text('body')
    
    # Check for analytics metrics
    metrics = {
        'var': 'VaR' in page_text or 'Value at Risk' in page_text,
        'cvar': 'CVaR' in page_text or 'Conditional VaR' in page_text,
        'sharpe': 'Sharpe' in page_text,
        'beta': 'Beta' in page_text
    }
    
    graph_count = await page.locator('.plotly').count()
    
    print(f"Graphs found: {graph_count}")
    print(f"Metrics found: {metrics}")
    print(f"Page text sample: {page_text[:500]}")
    
    await page.screenshot(path=str(ARTIFACTS_DIR / "analytics_deep_validation.png"), full_page=True)
    
    return {
        "graphs": graph_count,
        "metrics": metrics,
        "has_content": any(metrics.values())
    }

async def deep_validate_factors(page):
    """Deep validation of Factor Exposure subtab."""
    print("\n" + "="*80)
    print("DEEP VALIDATION: Factor Exposure Subtab")
    print("="*80)
    
    await page.goto(BASE_URL, wait_until='networkidle')
    await asyncio.sleep(2)
    await page.locator("text=Portfolio").first.click()
    await asyncio.sleep(1)
    await page.locator("text=Factor Exposure").first.click()
    await asyncio.sleep(3)
    
    page_text = await page.inner_text('body')
    
    # Check for SHAP or factor-related content
    has_shap = 'SHAP' in page_text
    has_factors = 'factor' in page_text.lower()
    is_empty = len(page_text.strip()) < 100 or "no data" in page_text.lower()
    
    graph_count = await page.locator('.plotly').count()
    
    print(f"Has SHAP: {has_shap}")
    print(f"Has factors: {has_factors}")
    print(f"Graphs found: {graph_count}")
    print(f"Is empty: {is_empty}")
    print(f"Page text sample: {page_text[:500]}")
    
    await page.screenshot(path=str(ARTIFACTS_DIR / "factors_deep_validation.png"), full_page=True)
    
    return {
        "graphs": graph_count,
        "has_shap": has_shap,
        "has_factors": has_factors,
        "is_empty": is_empty
    }

async def deep_validate_optimization(page):
    """Deep validation of Optimization subtab with input test."""
    print("\n" + "="*80)
    print("DEEP VALIDATION: Optimization Subtab")
    print("="*80)
    
    await page.goto(BASE_URL, wait_until='networkidle')
    await asyncio.sleep(2)
    await page.locator("text=Portfolio").first.click()
    await asyncio.sleep(1)
    await page.locator("text=Optimization").first.click()
    await asyncio.sleep(3)
    
    page_text = await page.inner_text('body')
    
    # Look for input fields
    input_fields = await page.locator('input[type="text"], textarea').count()
    buttons = await page.locator('button').count()
    
    print(f"Input fields found: {input_fields}")
    print(f"Buttons found: {buttons}")
    
    # Try to interact if inputs exist
    tickers_input = page.locator('#opt-tickers-input')
    if await tickers_input.count() > 0:
        print("Found tickers input, attempting to fill...")
        await tickers_input.fill('AAPL,MSFT,GOOGL')
        await asyncio.sleep(1)
        
        # Look for optimize button
        optimize_btn = page.locator('button:has-text("Optimize")')
        if await optimize_btn.count() > 0:
            print("Clicking Optimize button...")
            await optimize_btn.click()
            await asyncio.sleep(5)  # Wait for optimization
    
    graph_count = await page.locator('.plotly').count()
    
    print(f"Graphs found: {graph_count}")
    print(f"Page text sample: {page_text[:500]}")
    
    await page.screenshot(path=str(ARTIFACTS_DIR / "optimization_deep_validation.png"), full_page=True)
    
    return {
        "input_fields": input_fields,
        "buttons": buttons,
        "graphs": graph_count,
        "has_interaction": input_fields > 0
    }

async def main():
    """Run deep validation on all subtabs."""
    print("🔍 DEEP PORTFOLIO VALIDATION")
    print("="*80)
    
    results = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        results['positions'] = await deep_validate_positions(page)
        results['orders'] = await deep_validate_orders(page)
        results['analytics'] = await deep_validate_analytics(page)
        results['factors'] = await deep_validate_factors(page)
        results['optimization'] = await deep_validate_optimization(page)
        
        await browser.close()
    
    # Save results
    results_file = ARTIFACTS_DIR / "deep_validation_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, indent=2, fp=f)
    
    print("\n" + "="*80)
    print("DEEP VALIDATION SUMMARY")
    print("="*80)
    
    # Positions
    pos = results['positions']
    print(f"\n📊 Positions:")
    print(f"  - Has table: {pos['has_table']}")
    print(f"  - Positions count: {pos['positions_count']}")
    print(f"  - Tickers: {pos['tickers']}")
    print(f"  - Status: {'✅ OK' if pos['positions_count'] > 0 else '❌ EMPTY'}")
    
    # Orders
    ord = results['orders']
    print(f"\n📜 Orders:")
    print(f"  - Has table: {ord['has_table']}")
    print(f"  - Has orders: {ord['has_orders']}")
    print(f"  - Status: {'✅ OK' if ord['has_orders'] else '❌ EMPTY'}")
    
    # Analytics
    ana = results['analytics']
    print(f"\n📈 Analytics:")
    print(f"  - Graphs: {ana['graphs']}")
    print(f"  - Metrics: {ana['metrics']}")
    print(f"  - Status: {'✅ OK' if ana['has_content'] else '❌ EMPTY'}")
    
    # Factors
    fac = results['factors']
    print(f"\n🔬 Factors:")
    print(f"  - Graphs: {fac['graphs']}")
    print(f"  - Has SHAP: {fac['has_shap']}")
    print(f"  - Status: {'✅ OK' if not fac['is_empty'] else '❌ EMPTY'}")
    
    # Optimization
    opt = results['optimization']
    print(f"\n⚙️  Optimization:")
    print(f"  - Input fields: {opt['input_fields']}")
    print(f"  - Graphs: {opt['graphs']}")
    print(f"  - Status: {'✅ OK' if opt['has_interaction'] else '❌ NO INPUTS'}")
    
    print(f"\n📁 Results saved to: {results_file}")

if __name__ == "__main__":
    asyncio.run(main())

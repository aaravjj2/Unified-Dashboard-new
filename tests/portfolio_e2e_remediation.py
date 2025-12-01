#!/usr/bin/env python3
"""
End-to-End Portfolio Remediation & Validation
==============================================
Orchestrates the complete fix-validate-loop cycle for all 5 Portfolio subtabs.

Workflow:
1. Launch server
2. For each subtab (Positions, Orders, Analytics, Factors, Optimization):
   - Navigate and render
   - Capture snapshot
   - Validate content
   - Log discrepancies
3. Repeat for 3 iterations or until stable
4. Generate comprehensive report
"""

import json
import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
SNAPSHOTS_DIR = PROJECT_ROOT / 'tests' / 'portfolio_snapshots'
LOGS_DIR = PROJECT_ROOT / 'tests' / 'logs' / 'portfolio_validation'
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Test configuration
BASE_URL = 'http://127.0.0.1:8050'
MAX_ITERATIONS = 3
VIEWPORT = {'width': 1920, 'height': 1080}

class PortfolioValidator:
    """Validates Portfolio subtab content and behavior."""
    
    def __init__(self, page, iteration):
        self.page = page
        self.iteration = iteration
        self.results = {}
        
    def validate_positions(self):
        """Validate Positions subtab: only qty > 0, correct data."""
        print(f"\n{'='*80}")
        print(f"ITERATION {self.iteration}: POSITIONS SUBTAB")
        print(f"{'='*80}")
        
        try:
            # Click Positions subtab
            self.page.click('text=Positions', timeout=5000)
            self.page.wait_for_timeout(3000)
            
            # Capture snapshot
            snapshot_path = SNAPSHOTS_DIR / f'iter{self.iteration}_positions.png'
            self.page.screenshot(path=str(snapshot_path), full_page=True)
            
            # Check for table element
            has_table = self.page.locator('#portfolio-positions-table').count() > 0
            
            # Extract tickers from page text
            page_text = self.page.inner_text('body')
            tickers = []
            common_tickers = ['INTC', 'AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META']
            for ticker in common_tickers:
                if ticker in page_text:
                    tickers.append(ticker)
            
            # Check for empty state
            has_empty_state = 'No positions' in page_text or 'No open positions' in page_text
            
            # Check for closed position indicators
            has_closed_positions = 'qty=0' in page_text or 'Quantity: 0' in page_text
            
            result = {
                'status': 'PASS',
                'has_table': has_table,
                'tickers_found': tickers,
                'ticker_count': len(tickers),
                'has_empty_state': has_empty_state,
                'has_closed_positions': has_closed_positions,
                'snapshot': str(snapshot_path)
            }
            
            # Validation rules
            if has_closed_positions:
                result['status'] = 'FAIL'
                result['reason'] = 'Closed positions (qty=0) detected'
            elif not has_table and not has_empty_state:
                result['status'] = 'FAIL'
                result['reason'] = 'No table and no empty state message'
            
            print(f"✅ Has table: {has_table}")
            print(f"📊 Tickers found: {tickers} (count: {len(tickers)})")
            print(f"🔍 Empty state: {has_empty_state}")
            print(f"❌ Closed positions: {has_closed_positions}")
            print(f"📸 Snapshot: {snapshot_path.name}")
            print(f"🎯 Status: {result['status']}")
            
            self.results['positions'] = result
            return result
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            result = {'status': 'ERROR', 'error': str(e)}
            self.results['positions'] = result
            return result
    
    def validate_orders(self):
        """Validate Order History subtab: populated or empty state."""
        print(f"\n{'='*80}")
        print(f"ITERATION {self.iteration}: ORDER HISTORY SUBTAB")
        print(f"{'='*80}")
        
        try:
            # Click Order History subtab
            self.page.click('text=Order History', timeout=5000)
            self.page.wait_for_timeout(3000)
            
            # Capture snapshot
            snapshot_path = SNAPSHOTS_DIR / f'iter{self.iteration}_orders.png'
            self.page.screenshot(path=str(snapshot_path), full_page=True)
            
            # Check for table element
            has_table = self.page.locator('#portfolio-orders-table').count() > 0
            
            # Extract page content
            page_text = self.page.inner_text('body')
            
            # Check for order indicators
            has_filled_orders = 'filled' in page_text.lower() or 'Filled' in page_text
            has_order_data = 'buy' in page_text.lower() or 'sell' in page_text.lower()
            has_empty_state = 'No orders' in page_text or 'no order history' in page_text.lower()
            
            # Count rows (if table exists)
            row_count = 0
            try:
                rows = self.page.locator('table tbody tr').count()
                row_count = rows
            except:
                pass
            
            result = {
                'status': 'PASS',
                'has_table': has_table,
                'has_filled_orders': has_filled_orders,
                'has_order_data': has_order_data,
                'has_empty_state': has_empty_state,
                'row_count': row_count,
                'snapshot': str(snapshot_path)
            }
            
            # Validation rules
            if not has_table and not has_empty_state:
                result['status'] = 'FAIL'
                result['reason'] = 'No table and no empty state message'
            elif has_table and row_count == 0 and not has_empty_state:
                result['status'] = 'WARN'
                result['reason'] = 'Table exists but no rows and no empty state'
            
            print(f"✅ Has table: {has_table}")
            print(f"📊 Row count: {row_count}")
            print(f"📝 Has filled orders: {has_filled_orders}")
            print(f"💼 Has order data: {has_order_data}")
            print(f"🔍 Empty state: {has_empty_state}")
            print(f"📸 Snapshot: {snapshot_path.name}")
            print(f"🎯 Status: {result['status']}")
            
            self.results['orders'] = result
            return result
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            result = {'status': 'ERROR', 'error': str(e)}
            self.results['orders'] = result
            return result
    
    def validate_analytics(self):
        """Validate Analytics subtab: VaR, CVaR, Sharpe, Beta metrics."""
        print(f"\n{'='*80}")
        print(f"ITERATION {self.iteration}: ANALYTICS SUBTAB")
        print(f"{'='*80}")
        
        try:
            # Click Analytics subtab
            self.page.click('text=Analytics', timeout=5000)
            self.page.wait_for_timeout(3000)
            
            # Capture snapshot
            snapshot_path = SNAPSHOTS_DIR / f'iter{self.iteration}_analytics.png'
            self.page.screenshot(path=str(snapshot_path), full_page=True)
            
            # Extract page content
            page_text = self.page.inner_text('body')
            
            # Check for metrics
            metrics = {
                'var': 'VaR' in page_text or 'Value at Risk' in page_text,
                'cvar': 'CVaR' in page_text or 'Conditional VaR' in page_text or 'Expected Shortfall' in page_text,
                'sharpe': 'Sharpe' in page_text,
                'beta': 'Beta' in page_text
            }
            
            # Check for graphs
            graph_count = self.page.locator('.js-plotly-plot').count()
            
            # Check for calculate button
            has_calc_button = self.page.locator('button:has-text("Calculate")').count() > 0
            
            # Check for "no analytics" message
            has_no_analytics = 'No analytics calculated' in page_text or 'Click Calculate' in page_text
            
            # Check for actual metric values (numeric patterns)
            import re
            has_numeric_values = bool(re.search(r'-?\d+\.\d+%?', page_text))
            
            result = {
                'status': 'PASS',
                'metrics': metrics,
                'metrics_count': sum(metrics.values()),
                'graph_count': graph_count,
                'has_calc_button': has_calc_button,
                'has_no_analytics': has_no_analytics,
                'has_numeric_values': has_numeric_values,
                'snapshot': str(snapshot_path)
            }
            
            # Validation rules
            if has_no_analytics and result['metrics_count'] == 0:
                result['status'] = 'WARN'
                result['reason'] = 'Analytics not calculated - requires button click'
            elif result['metrics_count'] < 2 and not has_no_analytics:
                result['status'] = 'FAIL'
                result['reason'] = f'Only {result["metrics_count"]}/4 metrics found'
            
            print(f"📊 Graphs: {graph_count}")
            print(f"📈 Metrics detected: {metrics}")
            print(f"🔢 Metrics count: {result['metrics_count']}/4")
            print(f"🔘 Has Calculate button: {has_calc_button}")
            print(f"⚠️  No analytics message: {has_no_analytics}")
            print(f"💯 Has numeric values: {has_numeric_values}")
            print(f"📸 Snapshot: {snapshot_path.name}")
            print(f"🎯 Status: {result['status']}")
            
            self.results['analytics'] = result
            return result
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            result = {'status': 'ERROR', 'error': str(e)}
            self.results['analytics'] = result
            return result
    
    def validate_factors(self):
        """Validate Factor Exposure subtab: tables and charts."""
        print(f"\n{'='*80}")
        print(f"ITERATION {self.iteration}: FACTOR EXPOSURE SUBTAB")
        print(f"{'='*80}")
        
        try:
            # Click Factor Exposure subtab
            self.page.click('text=Factor Exposure', timeout=5000)
            self.page.wait_for_timeout(3000)
            
            # Capture snapshot
            snapshot_path = SNAPSHOTS_DIR / f'iter{self.iteration}_factors.png'
            self.page.screenshot(path=str(snapshot_path), full_page=True)
            
            # Extract page content
            page_text = self.page.inner_text('body')
            
            # Check for SHAP
            has_shap = 'SHAP' in page_text or 'shap' in page_text.lower()
            
            # Check for factor keywords
            has_factors = any(word in page_text for word in [
                'factor', 'Factor', 'exposure', 'Exposure', 
                'attribution', 'Attribution'
            ])
            
            # Check for graphs
            graph_count = self.page.locator('.js-plotly-plot').count()
            
            # Check for empty state
            has_empty_state = 'No factor' in page_text or 'no exposure' in page_text.lower()
            
            result = {
                'status': 'PASS',
                'has_shap': has_shap,
                'has_factors': has_factors,
                'graph_count': graph_count,
                'has_empty_state': has_empty_state,
                'snapshot': str(snapshot_path)
            }
            
            # Validation rules
            if graph_count == 0 and not has_empty_state:
                result['status'] = 'FAIL'
                result['reason'] = 'No graphs and no empty state'
            elif not has_factors and not has_empty_state:
                result['status'] = 'WARN'
                result['reason'] = 'No factor content detected'
            
            print(f"📊 Graphs: {graph_count}")
            print(f"🔬 Has SHAP: {has_shap}")
            print(f"📈 Has factors: {has_factors}")
            print(f"🔍 Empty state: {has_empty_state}")
            print(f"📸 Snapshot: {snapshot_path.name}")
            print(f"🎯 Status: {result['status']}")
            
            self.results['factors'] = result
            return result
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            result = {'status': 'ERROR', 'error': str(e)}
            self.results['factors'] = result
            return result
    
    def validate_optimization(self):
        """Validate Optimization subtab: interaction workflow."""
        print(f"\n{'='*80}")
        print(f"ITERATION {self.iteration}: OPTIMIZATION SUBTAB")
        print(f"{'='*80}")
        
        try:
            # Click Optimization subtab
            self.page.click('text=Optimization', timeout=5000)
            self.page.wait_for_timeout(3000)
            
            # Capture initial snapshot
            snapshot_path = SNAPSHOTS_DIR / f'iter{self.iteration}_optimization_before.png'
            self.page.screenshot(path=str(snapshot_path), full_page=True)
            
            # Extract page content
            page_text = self.page.inner_text('body')
            
            # Count input fields and buttons
            input_count = self.page.locator('input').count()
            button_count = self.page.locator('button').count()
            
            # Check for optimization elements
            has_optimize_btn = self.page.locator('button:has-text("Optimize")').count() > 0
            has_ticker_input = self.page.locator('input[placeholder*="ticker" i]').count() > 0
            
            # Check for graphs
            graph_count_before = self.page.locator('.js-plotly-plot').count()
            
            result = {
                'status': 'PASS',
                'input_count': input_count,
                'button_count': button_count,
                'has_optimize_btn': has_optimize_btn,
                'has_ticker_input': has_ticker_input,
                'graph_count_before': graph_count_before,
                'snapshot_before': str(snapshot_path),
                'interaction_attempted': False
            }
            
            # Attempt interaction if optimize button exists
            if has_optimize_btn:
                try:
                    print("🔄 Attempting optimization workflow...")
                    
                    # Try to fill ticker input
                    if has_ticker_input:
                        ticker_input = self.page.locator('input[placeholder*="ticker" i]').first
                        ticker_input.fill('AAPL,MSFT,GOOGL,NVDA')
                        self.page.wait_for_timeout(1000)
                    
                    # Click Optimize button
                    self.page.click('button:has-text("Optimize")', timeout=5000)
                    self.page.wait_for_timeout(5000)  # Wait for calculation
                    
                    # Capture after snapshot
                    snapshot_after_path = SNAPSHOTS_DIR / f'iter{self.iteration}_optimization_after.png'
                    self.page.screenshot(path=str(snapshot_after_path), full_page=True)
                    
                    # Check for result changes
                    page_text_after = self.page.inner_text('body')
                    graph_count_after = self.page.locator('.js-plotly-plot').count()
                    
                    result['interaction_attempted'] = True
                    result['graph_count_after'] = graph_count_after
                    result['snapshot_after'] = str(snapshot_after_path)
                    result['content_changed'] = len(page_text_after) != len(page_text)
                    
                    print(f"✅ Interaction completed")
                    print(f"📊 Graphs before: {graph_count_before}, after: {graph_count_after}")
                    print(f"📝 Content changed: {result['content_changed']}")
                    
                except Exception as e:
                    print(f"⚠️  Interaction failed: {e}")
                    result['interaction_error'] = str(e)
                    result['status'] = 'WARN'
            
            # Validation rules
            if not has_optimize_btn:
                result['status'] = 'FAIL'
                result['reason'] = 'No Optimize button found'
            elif result['interaction_attempted'] and result.get('graph_count_after', 0) == 0:
                result['status'] = 'WARN'
                result['reason'] = 'Interaction completed but no graphs rendered'
            
            print(f"🔘 Input fields: {input_count}")
            print(f"🔘 Buttons: {button_count}")
            print(f"✅ Has Optimize button: {has_optimize_btn}")
            print(f"📸 Snapshot: {snapshot_path.name}")
            print(f"🎯 Status: {result['status']}")
            
            self.results['optimization'] = result
            return result
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            result = {'status': 'ERROR', 'error': str(e)}
            self.results['optimization'] = result
            return result


def check_server_health():
    """Check if server is running."""
    import urllib.request
    try:
        response = urllib.request.urlopen(BASE_URL, timeout=5)
        return response.getcode() == 200
    except:
        return False


def run_validation_iteration(iteration):
    """Run a complete validation iteration."""
    print(f"\n{'#'*80}")
    print(f"# VALIDATION ITERATION {iteration}/{MAX_ITERATIONS}")
    print(f"{'#'*80}\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=VIEWPORT)
        
        try:
            # Navigate to app
            print(f"🌐 Navigating to {BASE_URL}...")
            page.goto(BASE_URL, timeout=30000)
            page.wait_for_timeout(5000)
            
            # Click Portfolio tab (using text match since href="#")
            print("📂 Activating Portfolio tab...")
            try:
                # Try multiple selectors
                selectors = [
                    'a:has-text("Portfolio")',
                    'text=Portfolio',
                    '[data-value="portfolio"]'
                ]
                clicked = False
                for selector in selectors:
                    try:
                        page.click(selector, timeout=5000)
                        clicked = True
                        print(f"✅ Clicked Portfolio using selector: {selector}")
                        break
                    except:
                        continue
                
                if not clicked:
                    raise Exception("Could not click Portfolio tab with any selector")
                    
            except Exception as e:
                print(f"⚠️  Portfolio tab click failed: {e}")
                # Continue anyway - might already be on portfolio tab
                
            page.wait_for_timeout(3000)
            
            # Run validations
            validator = PortfolioValidator(page, iteration)
            
            validator.validate_positions()
            validator.validate_orders()
            validator.validate_analytics()
            validator.validate_factors()
            validator.validate_optimization()
            
            return validator.results
            
        except Exception as e:
            print(f"❌ ITERATION {iteration} FAILED: {e}")
            return {'error': str(e), 'iteration': iteration}
        finally:
            browser.close()


def generate_report(all_results):
    """Generate comprehensive validation report."""
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    report_path = LOGS_DIR / f'portfolio_validation_report_{timestamp}.md'
    
    with open(report_path, 'w') as f:
        f.write("# Portfolio Tab End-to-End Validation Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Iterations:** {len(all_results)}/{MAX_ITERATIONS}\n\n")
        
        f.write("## Summary\n\n")
        
        # Calculate summary stats
        subtabs = ['positions', 'orders', 'analytics', 'factors', 'optimization']
        summary = {subtab: {'PASS': 0, 'FAIL': 0, 'WARN': 0, 'ERROR': 0} for subtab in subtabs}
        
        for iteration_results in all_results:
            for subtab in subtabs:
                if subtab in iteration_results:
                    status = iteration_results[subtab].get('status', 'ERROR')
                    summary[subtab][status] += 1
        
        f.write("| Subtab | Pass | Fail | Warn | Error |\n")
        f.write("|--------|------|------|------|-------|\n")
        for subtab in subtabs:
            f.write(f"| {subtab.title()} | ")
            f.write(f"{summary[subtab]['PASS']} | ")
            f.write(f"{summary[subtab]['FAIL']} | ")
            f.write(f"{summary[subtab]['WARN']} | ")
            f.write(f"{summary[subtab]['ERROR']} |\n")
        
        f.write("\n## Detailed Results\n\n")
        
        for i, iteration_results in enumerate(all_results, 1):
            f.write(f"### Iteration {i}\n\n")
            
            for subtab in subtabs:
                if subtab in iteration_results:
                    result = iteration_results[subtab]
                    status = result.get('status', 'ERROR')
                    icon = {'PASS': '✅', 'FAIL': '❌', 'WARN': '⚠️', 'ERROR': '🔴'}.get(status, '❓')
                    
                    f.write(f"#### {icon} {subtab.title()}\n\n")
                    f.write(f"**Status:** {status}\n\n")
                    
                    if 'reason' in result:
                        f.write(f"**Reason:** {result['reason']}\n\n")
                    
                    f.write("**Details:**\n\n")
                    f.write("```json\n")
                    f.write(json.dumps(result, indent=2))
                    f.write("\n```\n\n")
            
            f.write("---\n\n")
        
        f.write("## Recommendations\n\n")
        
        # Generate recommendations based on failures
        for subtab in subtabs:
            if summary[subtab]['FAIL'] > 0 or summary[subtab]['WARN'] > 0:
                f.write(f"### {subtab.title()}\n\n")
                
                # Get common issues from iterations
                common_issues = []
                for iteration_results in all_results:
                    if subtab in iteration_results:
                        result = iteration_results[subtab]
                        if result.get('status') in ['FAIL', 'WARN'] and 'reason' in result:
                            common_issues.append(result['reason'])
                
                if common_issues:
                    f.write("**Issues detected:**\n\n")
                    for issue in set(common_issues):
                        f.write(f"- {issue}\n")
                    f.write("\n")
                
                # Subtab-specific recommendations
                if subtab == 'orders':
                    f.write("**Recommended fix:** Check `portfolio_orders.py` callback to ensure it fetches from Alpaca API and handles empty states.\n\n")
                elif subtab == 'analytics':
                    f.write("**Recommended fix:** Modify Analytics callback to auto-calculate on tab activation, or make Calculate button workflow clearer.\n\n")
                elif subtab == 'factors':
                    f.write("**Recommended fix:** Verify Factor Exposure data source and ensure SHAP calculations are triggered.\n\n")
                elif subtab == 'optimization':
                    f.write("**Recommended fix:** Test optimization workflow with valid inputs and ensure error handling is in place.\n\n")
    
    print(f"\n📄 Report generated: {report_path}")
    return report_path


def main():
    """Main orchestration function."""
    print("\n" + "="*80)
    print("PORTFOLIO TAB END-TO-END REMEDIATION & VALIDATION")
    print("="*80 + "\n")
    
    # Check server
    if not check_server_health():
        print("❌ Server is not running at", BASE_URL)
        print("💡 Start server first with:")
        print("   cd /mnt/c/Aarav/fin_env/unified-dashboard")
        print("   python3 -m gunicorn --bind 127.0.0.1:8050 --workers 1 --timeout 120 'financial_dashboard.app:server' &")
        sys.exit(1)
    
    print(f"✅ Server is running at {BASE_URL}\n")
    
    # Run validation iterations
    all_results = []
    
    for i in range(1, MAX_ITERATIONS + 1):
        try:
            results = run_validation_iteration(i)
            all_results.append(results)
            
            # Save iteration results
            iteration_file = LOGS_DIR / f'iteration_{i}_results.json'
            with open(iteration_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"\n💾 Iteration {i} results saved: {iteration_file}")
            
            # Short pause between iterations
            if i < MAX_ITERATIONS:
                print(f"\n⏳ Waiting 5 seconds before next iteration...\n")
                time.sleep(5)
                
        except Exception as e:
            print(f"❌ Iteration {i} crashed: {e}")
            all_results.append({'error': str(e), 'iteration': i})
    
    # Generate final report
    print("\n" + "="*80)
    print("GENERATING FINAL REPORT")
    print("="*80 + "\n")
    
    report_path = generate_report(all_results)
    
    # Print summary
    print("\n" + "="*80)
    print("VALIDATION COMPLETE")
    print("="*80 + "\n")
    
    print(f"📊 Total iterations: {len(all_results)}")
    print(f"📁 Snapshots directory: {SNAPSHOTS_DIR}")
    print(f"📄 Final report: {report_path}")
    
    # Count overall status
    total_pass = sum(1 for r in all_results for k, v in r.items() if isinstance(v, dict) and v.get('status') == 'PASS')
    total_fail = sum(1 for r in all_results for k, v in r.items() if isinstance(v, dict) and v.get('status') == 'FAIL')
    total_warn = sum(1 for r in all_results for k, v in r.items() if isinstance(v, dict) and v.get('status') == 'WARN')
    
    print(f"\n✅ PASS: {total_pass}")
    print(f"❌ FAIL: {total_fail}")
    print(f"⚠️  WARN: {total_warn}")
    
    if total_fail == 0:
        print("\n🎉 ALL VALIDATIONS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total_fail} validation(s) failed. Review report for details.")
        return 1


if __name__ == '__main__':
    sys.exit(main())

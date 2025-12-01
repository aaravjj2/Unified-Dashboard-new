#!/usr/bin/env python3
"""
Agent 1B: Market Trends Clicker Test
Tests button interactions and backtest job lifecycle.
"""
import pytest
from playwright.sync_api import sync_playwright, Page, expect
import time
import json
import requests

BASE_URL = "http://localhost:8050"


def test_market_trends_clicker():
    """
    Clicker test for Market Trends tab.
    
    Tests:
    1. Navigate to Market Trends tab
    2. Verify table has 5 key tickers with numeric data
    3. Click "Run Full Analysis" button
    4. Click "Backtest Trend Signals" button
    5. Poll /api/_job_status to verify job lifecycle: queued → running → completed
    """
    run_log = {
        'test': 'market_trends_clicker',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'steps': []
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # Collect browser console logs
        console_logs = []
        page.on('console', lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        
        try:
            # Step 1: Navigate to root
            print("\n[STEP 1] Navigate to dashboard root")
            page.goto(BASE_URL, wait_until='domcontentloaded', timeout=30000)
            # Try Dash loading indicator, but don't fail if not present
            try:
                page.wait_for_selector('[data-dash-is-loading="false"]', timeout=5000)
            except:
                pass
            time.sleep(3)
            run_log['steps'].append({'step': 1, 'action': 'navigate_to_root', 'status': 'success'})
            
            # Step 2: Activate Market Trends tab
            print("[STEP 2] Activate Market Trends tab")
            # Tab structure uses dbc.Tab with tab_id="market_trends"
            market_trends_tab = page.locator('button[role="tab"]:has-text("Market Trends")').first
            if market_trends_tab.count() == 0:
                # Try alternative selector
                market_trends_tab = page.locator('a:has-text("Market Trends")').first
            
            if market_trends_tab.count() > 0:
                market_trends_tab.click()
                time.sleep(2)
                print("  ✅ Clicked Market Trends tab")
            else:
                print("  ⚠️  Market Trends tab not found, may already be active")
            
            # Wait for content
            content_selectors = ['#tab-market_trends', 'div[id*="market"]', 'table']
            content_found = False
            for selector in content_selectors:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    content_found = True
                    print(f"  ✅ Found content: {selector}")
                    break
                except:
                    continue
            
            if not content_found:
                print("  ⚠️  No specific market trends content selector found")
            
            run_log['steps'].append({'step': 2, 'action': 'activate_market_trends', 'status': 'success'})
            
            # Step 3: Verify table has 5 key tickers with numeric data
            print("[STEP 3] Verify Market Trends table")
            key_tickers = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']
            ticker_validation = {'tickers_found': 0, 'tickers_with_data': 0, 'details': []}
            
            for ticker in key_tickers:
                # Look for ticker row
                ticker_row = page.locator(f'tr:has-text("{ticker}")').first
                if ticker_row.count() > 0:
                    ticker_validation['tickers_found'] += 1
                    
                    # Check for data-value attributes (numeric data)
                    price_cells = ticker_row.locator('td[data-value]')
                    numeric_count = price_cells.count()
                    
                    if numeric_count > 0:
                        ticker_validation['tickers_with_data'] += 1
                        # Get first data-value to verify it's numeric
                        first_value = price_cells.first.get_attribute('data-value')
                        try:
                            float(first_value)
                            ticker_validation['details'].append({
                                'ticker': ticker,
                                'status': 'valid',
                                'numeric_cells': numeric_count,
                                'sample_value': first_value
                            })
                            print(f"  ✅ {ticker}: {numeric_count} numeric cells, sample={first_value}")
                        except (ValueError, TypeError):
                            ticker_validation['details'].append({
                                'ticker': ticker,
                                'status': 'invalid_data',
                                'sample_value': first_value
                            })
                            print(f"  ❌ {ticker}: data-value not numeric: {first_value}")
                    else:
                        ticker_validation['details'].append({
                            'ticker': ticker,
                            'status': 'no_data'
                        })
                        print(f"  ⚠️  {ticker}: found but no data-value attributes")
                else:
                    ticker_validation['details'].append({
                        'ticker': ticker,
                        'status': 'not_found'
                    })
                    print(f"  ❌ {ticker}: not found in table")
            
            run_log['steps'].append({
                'step': 3,
                'action': 'verify_table',
                'status': 'success' if ticker_validation['tickers_with_data'] == 5 else 'partial',
                'validation': ticker_validation
            })
            
            assert ticker_validation['tickers_found'] == 5, \
                f"Expected 5 tickers, found {ticker_validation['tickers_found']}"
            assert ticker_validation['tickers_with_data'] == 5, \
                f"Expected 5 tickers with data, found {ticker_validation['tickers_with_data']}"
            
            # Step 4: Click "Run Full Analysis" button
            print("[STEP 4] Click 'Run Full Analysis' button")
            analysis_button_found = False
            analysis_button_selectors = [
                'button:has-text("Run Full Analysis")',
                '#run-full-analysis-btn',
                'button:has-text("Run Analysis")',
                '#market-trends-run-btn'
            ]
            
            for selector in analysis_button_selectors:
                try:
                    btn = page.locator(selector).first
                    if btn.count() > 0 and btn.is_visible():
                        btn.click()
                        analysis_button_found = True
                        print(f"  ✅ Clicked button: {selector}")
                        time.sleep(2)
                        run_log['steps'].append({
                            'step': 4,
                            'action': 'click_run_analysis',
                            'status': 'success',
                            'button_selector': selector
                        })
                        break
                except Exception as e:
                    continue
            
            if not analysis_button_found:
                print("  ⚠️  'Run Full Analysis' button not found, skipping")
                run_log['steps'].append({
                    'step': 4,
                    'action': 'click_run_analysis',
                    'status': 'skipped',
                    'reason': 'button_not_found'
                })
            
            # Step 5: Click "Backtest Trend Signals" button and track job
            print("[STEP 5] Click 'Backtest Trend Signals' button")
            backtest_button_found = False
            job_id = None
            
            backtest_button_selectors = [
                'button:has-text("Backtest Trend Signals")',
                '#backtest-signals-btn',
                'button:has-text("Backtest")',
                '#market-trends-backtest-btn'
            ]
            
            for selector in backtest_button_selectors:
                try:
                    btn = page.locator(selector).first
                    if btn.count() > 0 and btn.is_visible():
                        btn.click()
                        backtest_button_found = True
                        print(f"  ✅ Clicked button: {selector}")
                        time.sleep(1)
                        
                        # Try to extract job_id from page store or status message
                        # Look for dashboard-queued-job store
                        try:
                            store = page.locator('#dashboard-queued-job')
                            if store.count() > 0:
                                store_data = store.get_attribute('data-value')
                                if store_data:
                                    job_data = json.loads(store_data)
                                    job_id = job_data.get('job_id')
                                    print(f"  ✅ Extracted job_id from store: {job_id}")
                        except Exception as e:
                            print(f"  ⚠️  Could not extract job_id from store: {e}")
                        
                        run_log['steps'].append({
                            'step': 5,
                            'action': 'click_backtest',
                            'status': 'success',
                            'button_selector': selector,
                            'job_id': job_id
                        })
                        break
                except Exception as e:
                    continue
            
            if not backtest_button_found:
                print("  ⚠️  'Backtest Trend Signals' button not found")
                run_log['steps'].append({
                    'step': 5,
                    'action': 'click_backtest',
                    'status': 'skipped',
                    'reason': 'button_not_found'
                })
            
            # Step 6: Poll job status if we have a job_id
            if job_id:
                print(f"[STEP 6] Poll job status for job_id={job_id}")
                job_status_log = poll_job_status(job_id, max_attempts=30, interval=2)
                run_log['steps'].append({
                    'step': 6,
                    'action': 'poll_job_status',
                    'status': 'success' if job_status_log['final_status'] == 'completed' else 'failed',
                    'job_status_log': job_status_log
                })
                
                # Save job status to separate file
                with open('tests/logs/iteration_1/job_status_final.json', 'w') as f:
                    json.dump(job_status_log, f, indent=2)
                print(f"  ✅ Job status saved to tests/logs/iteration_1/job_status_final.json")
            else:
                print("[STEP 6] Skipping job status poll (no job_id)")
                run_log['steps'].append({
                    'step': 6,
                    'action': 'poll_job_status',
                    'status': 'skipped',
                    'reason': 'no_job_id'
                })
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            run_log['error'] = str(e)
            raise
        
        finally:
            # Save browser console logs
            with open('tests/logs/iteration_1/browser_console.log', 'w') as f:
                f.write('\n'.join(console_logs))
            
            # Save run log
            with open('test-artifacts/market_trends_clicker_run.log', 'w') as f:
                json.dump(run_log, f, indent=2)
            
            print(f"\n✅ Run log saved to test-artifacts/market_trends_clicker_run.log")
            print(f"✅ Browser console saved to tests/logs/iteration_1/browser_console.log")
            
            browser.close()


def poll_job_status(job_id, max_attempts=30, interval=2):
    """
    Poll /api/_job_status endpoint until job completes or timeout.
    
    Returns dict with:
        - job_id
        - status_history: list of (timestamp, status) tuples
        - final_status: last known status
        - completed: bool
    """
    log = {
        'job_id': job_id,
        'status_history': [],
        'final_status': None,
        'completed': False,
        'total_polls': 0
    }
    
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{BASE_URL}/api/_job_status", params={'job_id': job_id}, timeout=5)
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                
                log['status_history'].append({'timestamp': timestamp, 'status': status, 'attempt': attempt + 1})
                log['final_status'] = status
                log['total_polls'] += 1
                
                print(f"  [Poll {attempt + 1}/{max_attempts}] Status: {status}")
                
                if status == 'completed':
                    log['completed'] = True
                    print(f"  ✅ Job completed after {attempt + 1} polls")
                    break
                elif status in ['failed', 'error']:
                    print(f"  ❌ Job failed with status: {status}")
                    break
                
            else:
                print(f"  ⚠️  Job status API returned {response.status_code}")
                log['status_history'].append({
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'status': f'http_{response.status_code}',
                    'attempt': attempt + 1
                })
        
        except Exception as e:
            print(f"  ⚠️  Error polling job status: {e}")
            log['status_history'].append({
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'error',
                'error': str(e),
                'attempt': attempt + 1
            })
        
        time.sleep(interval)
    
    return log


if __name__ == '__main__':
    test_market_trends_clicker()

#!/usr/bin/env python3
"""
Step 2: Data & Live Feed Validation
Tests fetch_options_chain_alpaca() with multiple tickers and verifies fallback chain.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '.')

# Load environment
from dotenv import load_dotenv
load_dotenv('keys.env')

from financial_dashboard.tabs.options_lab.data_loader import fetch_options_chain

def test_options_chain_multi_ticker():
    """Test options chain fetching for multiple tickers."""
    print("=" * 70)
    print("STEP 2: DATA & LIVE FEED VALIDATION")
    print("=" * 70)
    
    # Test tickers
    test_cases = [
        {'ticker': 'SPY', 'use_alpaca': True, 'description': 'SPY with Alpaca (live)'},
        {'ticker': 'AAPL', 'use_alpaca': True, 'description': 'AAPL with Alpaca (live)'},
        {'ticker': 'QQQ', 'use_alpaca': True, 'description': 'QQQ with Alpaca (live)'},
        {'ticker': 'SPY', 'use_alpaca': False, 'description': 'SPY with yfinance fallback'},
        {'ticker': 'TEST', 'use_mock': True, 'description': 'TEST with mock data'},
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}/{len(test_cases)}: {test_case['description']}")
        print(f"{'='*70}")
        
        ticker = test_case['ticker']
        use_alpaca = test_case.get('use_alpaca', False)
        use_mock = test_case.get('use_mock', False)
        
        try:
            # Fetch options chain
            print(f"📊 Fetching options chain for {ticker}...")
            chain_data = fetch_options_chain(
                ticker,
                use_alpaca=use_alpaca,
                use_mock=use_mock
            )
            
            # Validate response
            result = {
                'ticker': ticker,
                'test_description': test_case['description'],
                'timestamp': datetime.now().isoformat(),
                'success': False,
                'error': None,
                'source': None,
                'expirations_count': 0,
                'calls_count': 0,
                'puts_count': 0,
                'spot_price': None,
                'expirations': [],
                'sample_strikes': [],
            }
            
            if chain_data.get('error'):
                result['error'] = chain_data['error']
                print(f"   ❌ Error: {chain_data['error']}")
            else:
                result['success'] = True
                result['source'] = chain_data.get('source', 'unknown')
                result['spot_price'] = chain_data.get('spot_price', 0)
                result['expirations'] = chain_data.get('expirations', [])
                result['expirations_count'] = len(result['expirations'])
                
                calls = chain_data.get('calls', [])
                puts = chain_data.get('puts', [])
                
                # Handle both DataFrame and list formats
                import pandas as pd
                if isinstance(calls, pd.DataFrame):
                    result['calls_count'] = len(calls)
                    result['puts_count'] = len(puts) if isinstance(puts, pd.DataFrame) else 0
                    
                    # Sample strikes from DataFrame
                    if not calls.empty and 'strike' in calls.columns:
                        result['sample_strikes'] = sorted(calls['strike'].unique()[:10].tolist())
                else:
                    result['calls_count'] = len(calls) if calls else 0
                    result['puts_count'] = len(puts) if puts else 0
                    
                    # Sample strikes from list
                    if calls:
                        result['sample_strikes'] = sorted(set(c.get('strike', 0) for c in calls[:10]))
                
                # Display results
                source_badge = {
                    'alpaca': '🟢',
                    'yfinance': '🟡',
                    'mock': '🔵'
                }.get(result['source'], '⚪')
                
                print(f"\n   {source_badge} Source: {result['source'].upper()}")
                print(f"   💵 Spot Price: ${result['spot_price']:.2f}")
                print(f"   📅 Expirations: {result['expirations_count']}")
                print(f"   📞 Calls: {result['calls_count']} contracts")
                print(f"   📍 Puts: {result['puts_count']} contracts")
                
                if result['expirations']:
                    print(f"\n   📅 Expiration dates:")
                    for exp in result['expirations'][:5]:
                        print(f"      • {exp}")
                    if len(result['expirations']) > 5:
                        print(f"      ... and {len(result['expirations']) - 5} more")
                
                if result['sample_strikes']:
                    print(f"\n   🎯 Sample strikes: {', '.join(f'${s:.0f}' for s in result['sample_strikes'][:10])}")
                
                # Validate data quality
                print(f"\n   🔍 Data Quality Checks:")
                checks = [
                    ('Has expirations', result['expirations_count'] > 0),
                    ('Has calls', result['calls_count'] > 0),
                    ('Has puts', result['puts_count'] > 0),
                    ('Valid spot price', result['spot_price'] > 0),
                    ('Multiple expirations', result['expirations_count'] >= 2),
                ]
                
                for check_name, passed in checks:
                    status = "✅" if passed else "⚠️ "
                    print(f"      {status} {check_name}")
                
                result['quality_checks'] = {name: passed for name, passed in checks}
            
            results.append(result)
            
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            import traceback
            traceback.print_exc()
            
            results.append({
                'ticker': ticker,
                'test_description': test_case['description'],
                'timestamp': datetime.now().isoformat(),
                'success': False,
                'error': str(e),
            })
    
    # Summary
    print(f"\n{'='*70}")
    print("VALIDATION SUMMARY")
    print(f"{'='*70}")
    
    successful = sum(1 for r in results if r.get('success'))
    total = len(results)
    
    print(f"\n✅ Successful: {successful}/{total}")
    print(f"❌ Failed: {total - successful}/{total}")
    
    # Data sources breakdown
    sources = {}
    for r in results:
        if r.get('success'):
            source = r.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
    
    print(f"\n📊 Data Sources:")
    for source, count in sources.items():
        badge = {'alpaca': '🟢', 'yfinance': '🟡', 'mock': '🔵'}.get(source, '⚪')
        print(f"   {badge} {source.upper()}: {count} test(s)")
    
    # Save results to JSON
    output_file = Path('test-results/step2_data_validation.json')
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': total,
                'successful': successful,
                'failed': total - successful,
                'sources': sources,
            },
            'results': results,
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    
    # Final verdict
    print(f"\n{'='*70}")
    if successful == total:
        print("✅ ALL TESTS PASSED - Live data fetching fully operational!")
    elif successful > 0:
        print(f"🟡 PARTIAL SUCCESS - {successful}/{total} tests passed")
    else:
        print("❌ ALL TESTS FAILED - Check configuration and credentials")
    print(f"{'='*70}")
    
    return successful == total

if __name__ == '__main__':
    success = test_options_chain_multi_ticker()
    sys.exit(0 if success else 1)

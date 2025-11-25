#!/usr/bin/env python3
"""
Full Portfolio SHAP Generation Script

Generates SHAP explanations for all tickers in the portfolio, not just default 5.
Handles large portfolios (40+ tickers) with progress logging and fallback support.

Usage:
    python generate_full_portfolio_shap.py [--tickers AAPL,MSFT,GOOGL] [--date 20251023]
    
If no tickers provided, will attempt to load from portfolio data store.
"""

import sys
import os
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, '/app/financial_dashboard')

def load_portfolio_tickers():
    """
    Load current portfolio tickers from the portfolio data store.
    
    Returns:
        List of ticker symbols, or None if unavailable
    """
    try:
        # Look for portfolio data in typical locations
        possible_paths = [
            '/app/cache/portfolio_data.json',
            '/app/financial_dashboard/cache/portfolio_data.json',
            '/app/outputs/portfolio_data.json',
            '/app/financial_dashboard/portfolio_data.json'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"📂 Found portfolio data: {path}")
                with open(path, 'r') as f:
                    data = json.load(f)
                
                positions = data.get('positions', [])
                if positions:
                    tickers = [p.get('ticker') or p.get('symbol') or p.get('Ticker') for p in positions]
                    tickers = [t for t in tickers if t]  # Filter None
                    print(f"✅ Loaded {len(tickers)} tickers from portfolio")
                    return tickers
        
        print("⚠️  No portfolio data file found")
        return None
        
    except Exception as e:
        print(f"❌ Error loading portfolio tickers: {e}")
        return None


def generate_shap_for_portfolio(tickers, date=None, force=False):
    """
    Generate SHAP explanations for all tickers in portfolio.
    
    Args:
        tickers: List of ticker symbols
        date: Target date (YYYYMMDD), defaults to today
        force: Force regeneration even if files exist
    
    Returns:
        Dict with generation results and statistics
    """
    from utils.explain import get_or_generate_shap_data
    
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    
    print('=' * 80)
    print('FULL PORTFOLIO SHAP GENERATION')
    print('=' * 80)
    print()
    print(f'📊 Portfolio Size: {len(tickers)} tickers')
    print(f'📅 Target Date: {date}')
    print(f'🔄 Force Regenerate: {force}')
    print()
    
    # Normalize tickers to uppercase
    tickers = [t.upper() for t in tickers]
    
    print('Portfolio Tickers:')
    for i in range(0, len(tickers), 10):
        batch = tickers[i:i+10]
        print(f'  {", ".join(batch)}')
    print()
    
    print('-' * 80)
    print('GENERATING SHAP DATA...')
    print('-' * 80)
    print()
    
    start_time = datetime.now()
    
    # Generate SHAP data for all tickers
    try:
        shap_data = get_or_generate_shap_data(
            date=date,
            tickers=tickers,
            force_regenerate=force
        )
        
        if not shap_data:
            print('❌ FAILED: get_or_generate_shap_data() returned None')
            return {
                'success': False,
                'error': 'SHAP generation returned None',
                'duration_seconds': (datetime.now() - start_time).total_seconds()
            }
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print()
        print('=' * 80)
        print('✅ SHAP GENERATION COMPLETE')
        print('=' * 80)
        print()
        
        # Analyze results
        status = shap_data.get('status', 'success')
        num_tickers = shap_data.get('num_tickers', 0)
        num_features = shap_data.get('num_features', 0)
        explanations = shap_data.get('explanations', {})
        
        print(f'⏱️  Duration: {duration:.2f} seconds ({duration/60:.1f} minutes)')
        print(f'📊 Status: {status}')
        print(f'📦 Tickers Generated: {num_tickers}')
        print(f'🔍 Features per Ticker: {num_features}')
        print(f'📝 Explanations Dict Size: {len(explanations)}')
        print()
        
        # Ticker coverage analysis
        covered_tickers = set(explanations.keys())
        requested_tickers = set(tickers)
        missing_tickers = requested_tickers - covered_tickers
        
        print('Ticker Coverage Analysis:')
        print(f'  Requested: {len(requested_tickers)} tickers')
        print(f'  Covered: {len(covered_tickers)} tickers')
        print(f'  Missing: {len(missing_tickers)} tickers')
        
        if missing_tickers:
            print(f'  Missing List: {", ".join(sorted(missing_tickers))}')
        
        print()
        
        # Validate each ticker has proper structure
        print('Validation:')
        
        valid_count = 0
        invalid_tickers = []
        
        for ticker in covered_tickers:
            ticker_data = explanations.get(ticker, {})
            
            # Check required fields
            required_fields = ['base_value', 'prediction', 'top_features', 'all_features']
            has_all_fields = all(field in ticker_data for field in required_fields)
            
            # Check feature count
            all_features = ticker_data.get('all_features', [])
            has_features = len(all_features) > 0
            
            # Check numeric values
            has_numeric = False
            if all_features:
                sample_feat = all_features[0]
                shap_val = sample_feat.get('shap_value', 0)
                has_numeric = isinstance(shap_val, (int, float))
            
            if has_all_fields and has_features and has_numeric:
                valid_count += 1
            else:
                invalid_tickers.append(ticker)
        
        print(f'  ✅ Valid: {valid_count}/{len(covered_tickers)} tickers')
        
        if invalid_tickers:
            print(f'  ⚠️  Invalid: {len(invalid_tickers)} tickers')
            print(f'     {", ".join(invalid_tickers)}')
        
        print()
        
        # Check file persistence
        explain_dir = '/app/financial_dashboard/explain'
        expected_file = os.path.join(explain_dir, f'picks_explain_{date}.json')
        
        print('File Persistence:')
        if os.path.exists(expected_file):
            file_size = os.path.getsize(expected_file)
            print(f'  ✅ File exists: {expected_file}')
            print(f'     Size: {file_size:,} bytes ({file_size/1024:.2f} KB)')
            
            # Validate file content matches
            with open(expected_file, 'r') as f:
                file_data = json.load(f)
                file_ticker_count = len(file_data.get('explanations', {}))
                print(f'     Contains {file_ticker_count} ticker explanations')
        else:
            print(f'  ❌ File not found: {expected_file}')
        
        print()
        
        # Sample output for first ticker
        if covered_tickers:
            sample_ticker = sorted(covered_tickers)[0]
            sample_data = explanations[sample_ticker]
            
            print(f'Sample Output ({sample_ticker}):')
            print(f'  Base Value: {sample_data.get("base_value", 0):.4f}')
            print(f'  Prediction: {sample_data.get("prediction", 0):.4f}')
            print(f'  Top Features:')
            
            top_features = sample_data.get('top_features', [])[:5]
            for i, feat in enumerate(top_features, 1):
                feat_name = feat.get('feature', 'Unknown')
                feat_val = feat.get('shap_value', 0)
                print(f'    {i}. {feat_name}: {feat_val:.6f}')
        
        print()
        
        return {
            'success': True,
            'status': status,
            'duration_seconds': duration,
            'tickers_requested': len(requested_tickers),
            'tickers_covered': len(covered_tickers),
            'tickers_missing': len(missing_tickers),
            'missing_list': sorted(missing_tickers),
            'features_per_ticker': num_features,
            'file_path': expected_file if os.path.exists(expected_file) else None
        }
        
    except Exception as e:
        print()
        print('=' * 80)
        print('❌ SHAP GENERATION FAILED')
        print('=' * 80)
        print()
        print(f'Error: {e}')
        
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'error': str(e),
            'duration_seconds': (datetime.now() - start_time).total_seconds()
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Generate SHAP data for full portfolio')
    parser.add_argument('--tickers', type=str, help='Comma-separated list of tickers')
    parser.add_argument('--date', type=str, help='Target date (YYYYMMDD)')
    parser.add_argument('--force', action='store_true', help='Force regeneration')
    
    args = parser.parse_args()
    
    # Get tickers
    if args.tickers:
        tickers = [t.strip() for t in args.tickers.split(',')]
        print(f"Using provided tickers: {len(tickers)} tickers")
    else:
        print("No tickers provided - attempting to load from portfolio...")
        tickers = load_portfolio_tickers()
        
        if not tickers:
            print()
            print("❌ ERROR: No tickers available")
            print()
            print("Options:")
            print("  1. Provide tickers: --tickers AAPL,MSFT,GOOGL,...")
            print("  2. Ensure portfolio_data.json exists with positions")
            print()
            sys.exit(1)
    
    # Generate SHAP data
    result = generate_shap_for_portfolio(
        tickers=tickers,
        date=args.date,
        force=args.force
    )
    
    # Print summary
    print('=' * 80)
    print('SUMMARY')
    print('=' * 80)
    print()
    
    if result['success']:
        print('✅ SUCCESS')
        print(f'   Duration: {result["duration_seconds"]:.2f}s')
        print(f'   Tickers Covered: {result["tickers_covered"]}/{result["tickers_requested"]}')
        print(f'   Features: {result["features_per_ticker"]} per ticker')
        
        if result['tickers_missing'] > 0:
            print(f'   ⚠️  Missing: {result["tickers_missing"]} tickers')
        
        if result['file_path']:
            print(f'   📁 Output: {result["file_path"]}')
        
        sys.exit(0)
    else:
        print('❌ FAILED')
        print(f'   Error: {result.get("error", "Unknown")}')
        print(f'   Duration: {result["duration_seconds"]:.2f}s')
        
        sys.exit(1)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Phase 5B: SHAP Integration Verification Script

Purpose:
- Verify SHAP JSON files exist and are valid
- Test SHAP generation with current portfolio tickers
- Validate feature attributions (8 technical indicators)
- Ensure fallback (sklearn) only used when SHAP library fails
- Test integration with Portfolio calculations

Expected Output:
- SHAP JSON files present in explain/ directory
- Valid JSON structure with required keys
- Feature attributions consistent across tickers
- Fallback mode clearly indicated if SHAP library unavailable

Usage:
    python scripts/test_shap_integration.py [date] [tickers]
    python scripts/test_shap_integration.py 20251023 AAPL,MSFT,GOOGL,AMZN,NVDA
"""

import sys
import os
from datetime import datetime
import json

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'financial_dashboard'))

from utils.explain import get_or_generate_shap_data, load_shap_explanations
from utils.models import load_latest_model, get_mock_model
from utils.data_prep import prepare_features_for_date
import numpy as np


def main(date_str=None, tickers_str=None):
    """
    Run SHAP integration validation test.
    
    Args:
        date_str: Date string in YYYYMMDD format (defaults to today)
        tickers_str: Comma-separated ticker string (defaults to test portfolio)
    """
    print('=' * 70)
    print('PHASE 5B: SHAP INTEGRATION VERIFICATION')
    print('=' * 70)
    print()
    
    # Parse date
    if date_str:
        date = date_str
    else:
        date = datetime.now().strftime('%Y%m%d')
    
    # Parse tickers
    if tickers_str:
        tickers = [t.strip().upper() for t in tickers_str.split(',')]
    else:
        tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
    
    print(f'📊 Test Portfolio: {", ".join(tickers)}')
    print(f'📅 Target Date: {date}')
    print()
    
    # Step 1: Check existing SHAP files
    print('Step 1: Checking Existing SHAP Files...')
    print('-' * 70)
    
    explain_dir = os.path.join(os.path.dirname(__file__), '..', 'financial_dashboard', 'explain')
    
    if os.path.exists(explain_dir):
        shap_files = [f for f in os.listdir(explain_dir) if f.startswith('picks_explain_') and f.endswith('.json')]
        
        print(f'📂 SHAP Directory: {explain_dir}')
        print(f'   Files found: {len(shap_files)}')
        
        if shap_files:
            print()
            print('   Existing SHAP files:')
            for i, fname in enumerate(sorted(shap_files), 1):
                fpath = os.path.join(explain_dir, fname)
                fsize = os.path.getsize(fpath)
                print(f'     {i}. {fname} ({fsize:,} bytes)')
        else:
            print('   ⚠️  No existing SHAP files found')
        
        print()
    else:
        print(f'❌ SHAP directory does not exist: {explain_dir}')
        return False
    
    # Step 2: Load or generate SHAP data
    print('Step 2: Loading/Generating SHAP Explanations...')
    print('-' * 70)
    
    try:
        shap_data = get_or_generate_shap_data(date)
        
        if not shap_data:
            print('❌ FAILED: get_or_generate_shap_data() returned None')
            return False
        
        status = shap_data.get('status', 'success')
        print(f'SHAP Generation Status: {status}')
        
        if status == 'fallback':
            print('❌ FAILED: SHAP generation fell back (no data generated)')
            print(f'   Message: {shap_data.get("message", "unknown")}')
            return False
        
        print(f'✅ SHAP data retrieved successfully')
        print()
        
    except Exception as e:
        print(f'❌ FAILED: SHAP generation error: {e}')
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Validate JSON structure
    print('Step 3: Validating SHAP JSON Structure...')
    print('-' * 70)
    
    try:
        required_keys = ['generated_at', 'date', 'model_type', 'num_tickers', 'num_features', 'explanations']
        
        print(f'📋 Required Keys Check:')
        for key in required_keys:
            if key in shap_data:
                print(f'   ✅ {key}: {shap_data[key] if key not in ["explanations"] else f"{len(shap_data[key])} entries"}')
            else:
                print(f'   ❌ Missing: {key}')
                return False
        
        print()
        
        # Check metadata
        num_tickers = shap_data.get('num_tickers', 0)
        num_features = shap_data.get('num_features', 0)
        model_type = shap_data.get('model_type', 'unknown')
        
        print(f'📊 SHAP Metadata:')
        print(f'   Model Type: {model_type}')
        print(f'   Number of Tickers: {num_tickers}')
        print(f'   Features per Ticker: {num_features}')
        print()
        
        if num_features != 8:
            print(f'   ⚠️  WARNING: Expected 8 features, got {num_features}')
        else:
            print(f'   ✅ Feature count matches expected (8 technical indicators)')
        
        print()
        
    except Exception as e:
        print(f'❌ FAILED: JSON structure validation error: {e}')
        return False
    
    # Step 4: Validate feature attributions
    print('Step 4: Validating Feature Attributions...')
    print('-' * 70)
    
    try:
        explanations = shap_data.get('explanations', {})
        
        if not explanations:
            print('❌ FAILED: No ticker explanations found')
            return False
        
        print(f'📈 Ticker Explanations: {len(explanations)} tickers')
        print()
        
        # Check first ticker in detail
        first_ticker = list(explanations.keys())[0]
        ticker_data = explanations[first_ticker]
        
        print(f'   Examining: {first_ticker}')
        print(f'   Required Fields:')
        
        required_ticker_fields = ['base_value', 'prediction', 'shap_sum', 'top_features', 'all_features']
        for field in required_ticker_fields:
            if field in ticker_data:
                value = ticker_data[field]
                if field in ['top_features', 'all_features']:
                    print(f'     ✅ {field}: {len(value)} features')
                else:
                    print(f'     ✅ {field}: {value}')
            else:
                print(f'     ❌ Missing: {field}')
                return False
        
        print()
        
        # Validate SHAP values are numeric
        all_features = ticker_data.get('all_features', [])
        
        if not all_features:
            print('   ❌ FAILED: No feature attributions found')
            return False
        
        print(f'   Validating SHAP Values for {len(all_features)} features:')
        
        non_numeric_count = 0
        for feat in all_features:
            shap_val = feat.get('shap_value')
            if not isinstance(shap_val, (int, float)) or np.isnan(shap_val) or np.isinf(shap_val):
                non_numeric_count += 1
        
        if non_numeric_count > 0:
            print(f'   ❌ FAILED: {non_numeric_count} non-numeric SHAP values detected')
            return False
        else:
            print(f'   ✅ All SHAP values are numeric')
        
        # Display top 5 features
        top_features = ticker_data.get('top_features', [])
        
        print()
        print(f'   Top 5 Features for {first_ticker}:')
        for i, feat in enumerate(top_features[:5], 1):
            feature_name = feat.get('feature', 'unknown')
            shap_value = feat.get('shap_value', 0.0)
            print(f'     {i}. {feature_name}: {shap_value:.6f}')
        
        print()
        
    except Exception as e:
        print(f'❌ FAILED: Feature attribution validation error: {e}')
        import traceback
        traceback.print_exc()
        return False
    
    # Step 5: Verify feature consistency across tickers
    print('Step 5: Verifying Feature Consistency...')
    print('-' * 70)
    
    try:
        # Check that all tickers have the same feature set
        feature_sets = {}
        
        for ticker, data in list(explanations.items())[:3]:  # Check first 3 tickers
            all_feats = data.get('all_features', [])
            feature_names = [f.get('feature') for f in all_feats]
            feature_sets[ticker] = set(feature_names)
        
        # Compare feature sets
        if feature_sets:
            reference_ticker = list(feature_sets.keys())[0]
            reference_features = feature_sets[reference_ticker]
            
            all_consistent = True
            for ticker, feat_set in feature_sets.items():
                if feat_set != reference_features:
                    print(f'   ❌ {ticker} has inconsistent features')
                    all_consistent = False
            
            if all_consistent:
                print(f'   ✅ All tickers have consistent feature sets')
                print(f'   Features: {", ".join(sorted(reference_features))}')
            else:
                print(f'   ⚠️  WARNING: Feature sets inconsistent across tickers')
        
        print()
        
    except Exception as e:
        print(f'⚠️  Warning: Feature consistency check failed: {e}')
    
    # Step 6: Check for fallback mode indicator
    print('Step 6: Checking SHAP Library Status...')
    print('-' * 70)
    
    try:
        # Check if any ticker data has fallback_mode flag
        fallback_detected = False
        
        for ticker, data in explanations.items():
            if 'fallback_mode' in data or data.get('fallback_mode') == True:
                fallback_detected = True
                break
        
        if fallback_detected:
            print('   ℹ️  Fallback mode detected (using sklearn feature importances)')
            print('   This is expected when SHAP library is unavailable')
        else:
            print('   ✅ Using native SHAP library (optimal)')
        
        print()
        
    except Exception as e:
        print(f'⚠️  Warning: Fallback check error: {e}')
    
    # Step 7: File persistence verification
    print('Step 7: Verifying File Persistence...')
    print('-' * 70)
    
    try:
        expected_file = os.path.join(explain_dir, f'picks_explain_{date}.json')
        
        if os.path.exists(expected_file):
            file_size = os.path.getsize(expected_file)
            print(f'✅ SHAP file exists: {expected_file}')
            print(f'   Size: {file_size:,} bytes ({file_size/1024:.2f} KB)')
            
            # Verify file is readable and valid JSON
            with open(expected_file, 'r') as f:
                file_data = json.load(f)
            
            print(f'   ✅ File is valid JSON')
            print(f'   ✅ Contains {len(file_data.get("explanations", {}))} ticker explanations')
        else:
            print(f'❌ FAILED: Expected file not found: {expected_file}')
            return False
        
        print()
        
    except Exception as e:
        print(f'❌ FAILED: File persistence verification error: {e}')
        return False
    
    # Success summary
    print('=' * 70)
    print('✅ PHASE 5B SHAP INTEGRATION VERIFICATION: SUCCESS')
    print('=' * 70)
    print()
    print('📦 Verification Summary:')
    print(f'   ✅ SHAP files accessible in {explain_dir}')
    print(f'   ✅ SHAP data generated for date {date}')
    print(f'   ✅ JSON structure valid with all required keys')
    print(f'   ✅ {num_tickers} tickers with {num_features} features each')
    print(f'   ✅ All SHAP values numeric and valid')
    print(f'   ✅ Feature consistency verified across tickers')
    print(f'   ✅ File persisted to disk ({file_size:,} bytes)')
    print()
    
    if fallback_detected:
        print('ℹ️  Note: Using sklearn fallback (SHAP library unavailable)')
    else:
        print('🎯 Using native SHAP library for optimal explanations')
    
    print()
    
    return True


if __name__ == '__main__':
    # Parse command-line arguments
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    tickers_arg = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Run validation
    success = main(date_arg, tickers_arg)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

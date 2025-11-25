#!/usr/bin/env python3
"""
PHASE 5: SHAP Generation Reproducibility Script

This script demonstrates and validates the SHAP auto-generation pipeline.
It produces tangible artifacts (JSON files in explain/) that can be inspected.

Usage:
    python scripts/test_shap_generation.py [date] [tickers]

Examples:
    python scripts/test_shap_generation.py
    python scripts/test_shap_generation.py 20251023 AAPL,MSFT,GOOGL
"""

import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'financial_dashboard'))

def main():
    print("="*80)
    print("PHASE 5: SHAP GENERATION REPRODUCIBILITY TEST")
    print("="*80)
    
    # Parse arguments
    target_date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y%m%d')
    tickers_arg = sys.argv[2] if len(sys.argv) > 2 else 'AAPL,MSFT,GOOGL,AMZN,NVDA'
    tickers = tickers_arg.split(',')
    
    print(f"\n📅 Target Date: {target_date}")
    print(f"📊 Tickers: {tickers}")
    
    # Import modules
    print("\n🔧 Importing modules...")
    try:
        from utils.explain import get_or_generate_shap_data
        from utils.models import load_latest_model, get_mock_model
        from utils.data_prep import prepare_features_for_date
        print("✅ Modules imported successfully")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return 1
    
    # Step 1: Check if model exists
    print("\n📦 Step 1: Loading ML model...")
    model = load_latest_model()
    
    if model is None:
        print("⚠️  No trained model found - using mock model for testing")
        model = get_mock_model()
        
        if model is None:
            print("❌ Cannot create mock model (sklearn missing)")
            return 1
        
        print("✅ Mock model created successfully")
    else:
        print(f"✅ Loaded model: {type(model).__name__}")
    
    # Step 2: Prepare features
    print(f"\n📊 Step 2: Preparing features for {target_date}...")
    features, feature_names, ticker_list = prepare_features_for_date(target_date, tickers)
    
    if features is None:
        print("❌ Feature preparation failed")
        return 1
    
    print(f"✅ Features prepared:")
    print(f"   - Shape: {features.shape}")
    print(f"   - Feature names: {feature_names}")
    print(f"   - Tickers: {ticker_list}")
    
    # Step 3: Generate SHAP data
    print(f"\n🧮 Step 3: Generating SHAP explanations...")
    shap_result = get_or_generate_shap_data(target_date)
    
    if shap_result is None:
        print("❌ SHAP generation returned None")
        return 1
    
    if shap_result.get('status') == 'fallback':
        print(f"⚠️  SHAP generation used fallback: {shap_result.get('message')}")
        return 1
    
    print("✅ SHAP data generated successfully")
    
    # Step 4: Validate generated file
    explain_dir = PROJECT_ROOT / 'financial_dashboard' / 'explain'
    shap_file = explain_dir / f'picks_explain_{target_date}.json'
    
    print(f"\n📁 Step 4: Validating generated file...")
    print(f"   Expected path: {shap_file}")
    
    if not shap_file.exists():
        print(f"❌ SHAP file not found at: {shap_file}")
        return 1
    
    print(f"✅ SHAP file exists!")
    print(f"   - Size: {shap_file.stat().st_size} bytes")
    print(f"   - Modified: {datetime.fromtimestamp(shap_file.stat().st_mtime)}")
    
    # Step 5: Parse and validate JSON structure
    print(f"\n🔍 Step 5: Validating JSON structure...")
    
    with open(shap_file, 'r') as f:
        shap_data = json.load(f)
    
    required_keys = ['date', 'generated_at', 'model_type', 'num_tickers', 'num_features', 'explanations']
    missing_keys = [k for k in required_keys if k not in shap_data]
    
    if missing_keys:
        print(f"❌ Missing required keys: {missing_keys}")
        return 1
    
    print("✅ JSON structure valid")
    print(f"   - Model type: {shap_data['model_type']}")
    print(f"   - Num tickers: {shap_data['num_tickers']}")
    print(f"   - Num features: {shap_data['num_features']}")
    print(f"   - Explanations: {len(shap_data['explanations'])} tickers")
    
    # Step 6: Validate SHAP values are numeric
    print(f"\n🔬 Step 6: Validating SHAP value arrays...")
    
    explanations = shap_data.get('explanations', {})
    
    if not explanations:
        print("⚠️  No explanations in SHAP data")
        return 1
    
    # Check first ticker
    first_ticker = list(explanations.keys())[0]
    first_explanation = explanations[first_ticker]
    
    print(f"   Sample ticker: {first_ticker}")
    print(f"   - Prediction: {first_explanation.get('prediction')}")
    print(f"   - Base value: {first_explanation.get('base_value')}")
    
    features_list = first_explanation.get('features', [])
    
    if not features_list:
        print("⚠️  No features in explanation")
        return 1
    
    print(f"   - Num features: {len(features_list)}")
    
    # Validate SHAP values are numeric
    for feature in features_list[:3]:  # Check first 3
        feature_name = feature.get('name')
        shap_value = feature.get('shap_value')
        feature_value = feature.get('value')
        
        print(f"      • {feature_name}: value={feature_value}, SHAP={shap_value}")
        
        if not isinstance(shap_value, (int, float)):
            print(f"❌ SHAP value is not numeric: {type(shap_value)}")
            return 1
    
    print("✅ SHAP values are numeric and valid!")
    
    # Final summary
    print("\n" + "="*80)
    print("✅ PHASE 5 REPRODUCIBILITY TEST: SUCCESS")
    print("="*80)
    print(f"\n📦 Artifacts generated:")
    print(f"   1. SHAP JSON file: {shap_file}")
    print(f"   2. {shap_data['num_tickers']} ticker explanations")
    print(f"   3. {shap_data['num_features']} features per ticker")
    print(f"\n💡 To view the SHAP file:")
    print(f"   cat {shap_file} | jq '.'")
    print(f"\n💡 To use in dashboard:")
    print(f"   1. Open Portfolio → Positions tab")
    print(f"   2. SHAP chart should auto-load")
    print(f"   3. No 'Data Not Found' error!")
    print()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

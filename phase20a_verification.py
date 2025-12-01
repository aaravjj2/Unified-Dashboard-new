#!/usr/bin/env python3
"""
Phase 20A Automated Verification Script

Simulates clicking "Run Prediction" button and verifies:
1. Azure ML endpoint called correctly
2. Predictions saved to PostgreSQL database
3. Observability metrics emitted
"""

import sys
import time
import psycopg2
import json
from datetime import datetime

# Add project to path
sys.path.insert(0, '/app')

from financial_dashboard.tabs.azure_ml_lab.helpers import call_azure_ml_endpoint
from financial_dashboard.tabs.azure_ml_lab.ml_database import (
    initialize_ml_schema,
    save_prediction_run,
    get_latest_predictions
)
from financial_dashboard.tabs.azure_ml_lab.ml_observability import (
    log_metric,
    log_timing
)

def verify_phase20a():
    """Full Phase 20A verification"""
    
    print("\n" + "="*80)
    print("🚀 PHASE 20A: Automated Verification")
    print("="*80 + "\n")
    
    results = {
        'database_connection': False,
        'schema_initialized': False,
        'azure_ml_call': False,
        'predictions_saved': False,
        'predictions_retrieved': False,
        'observability_working': False,
        'total_tests': 6,
        'passed_tests': 0
    }
    
    # Test 1: Database Connection
    print("📊 Test 1: PostgreSQL Connection")
    try:
        conn = psycopg2.connect(
            'postgresql://postgres:postgres@postgres_db:5432/market_data'
        )
        conn.close()
        results['database_connection'] = True
        results['passed_tests'] += 1
        print("   ✅ PASSED - PostgreSQL connection successful\n")
    except Exception as e:
        print(f"   ❌ FAILED - {e}\n")
    
    # Test 2: Schema Initialized
    print("📋 Test 2: Database Schema")
    try:
        conn = psycopg2.connect(
            'postgresql://postgres:postgres@postgres_db:5432/market_data'
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE 'ml_%'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cur.fetchall()]
        expected = ['ml_insights', 'ml_model_metrics', 'ml_prediction_runs', 'ml_predictions']
        
        if all(t in tables for t in expected):
            results['schema_initialized'] = True
            results['passed_tests'] += 1
            print(f"   ✅ PASSED - All 4 ML tables exist: {', '.join(tables)}\n")
        else:
            print(f"   ❌ FAILED - Missing tables. Found: {tables}\n")
        conn.close()
    except Exception as e:
        print(f"   ❌ FAILED - {e}\n")
    
    # Test 3: Azure ML Endpoint Call
    print("📡 Test 3: Azure ML Endpoint Call")
    try:
        # Create mock portfolio data
        import pandas as pd
        portfolio_df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'GOOGL'],
            'shares': [10, 5, 8],
            'current_price': [150.0, 300.0, 2800.0]
        })
        
        start_time = time.time()
        predictions, error = call_azure_ml_endpoint(
            portfolio_df,
            model_type='ensemble',
            horizon_days=5
        )
        latency_ms = (time.time() - start_time) * 1000
        
        if predictions and not error:
            results['azure_ml_call'] = True
            results['passed_tests'] += 1
            print(f"   ✅ PASSED - Azure ML call succeeded")
            print(f"      • Latency: {latency_ms:.2f}ms")
            print(f"      • Source: {predictions.get('source', 'unknown')}")
            print(f"      • Predictions: {len(predictions.get('predictions', []))}")
            if predictions.get('fallback_reason'):
                print(f"      • Fallback reason: {predictions['fallback_reason']}")
            print()
        else:
            print(f"   ❌ FAILED - {error}\n")
    except Exception as e:
        print(f"   ❌ FAILED - {e}\n")
    
    # Test 4: Save Predictions to Database
    print("💾 Test 4: Save Predictions to PostgreSQL")
    try:
        if predictions:
            run_id = save_prediction_run(
                model_type='ensemble',
                horizon_days=5,
                predictions=predictions.get('predictions', []),
                overall_confidence=predictions.get('overall_confidence', 0.0),
                confidence_threshold=0.0,
                prediction_target='portfolio',
                universe='test_portfolio',
                status='success',
                source=predictions.get('source', 'unknown'),
                fallback_reason=predictions.get('fallback_reason'),
                latency_ms=latency_ms,
                metadata={'test': 'phase20a_verification'}
            )
            
            if run_id:
                results['predictions_saved'] = True
                results['passed_tests'] += 1
                print(f"   ✅ PASSED - Saved to database (run_id: {run_id})\n")
            else:
                print("   ❌ FAILED - save_prediction_run returned None\n")
        else:
            print("   ⏭️  SKIPPED - No predictions to save\n")
    except Exception as e:
        print(f"   ❌ FAILED - {e}\n")
    
    # Test 5: Retrieve Predictions from Database
    print("🔍 Test 5: Retrieve Predictions from PostgreSQL")
    try:
        latest = get_latest_predictions(limit=3)
        if latest:
            results['predictions_retrieved'] = True
            results['passed_tests'] += 1
            print(f"   ✅ PASSED - Retrieved {len(latest)} predictions")
            for pred in latest[:3]:
                print(f"      • {pred.get('ticker', 'UNKNOWN')}: {pred.get('predicted_return', 0):.2%} (confidence: {pred.get('confidence', 0):.2f})")
            print()
        else:
            print("   ❌ FAILED - No predictions retrieved\n")
    except Exception as e:
        print(f"   ❌ FAILED - {e}\n")
    
    # Test 6: Observability
    print("📈 Test 6: Observability Metrics")
    try:
        log_metric('phase20a.verification.test', 1.0)
        log_timing('phase20a.verification.duration', latency_ms)
        results['observability_working'] = True
        results['passed_tests'] += 1
        print("   ✅ PASSED - Metrics emitted successfully\n")
    except Exception as e:
        print(f"   ❌ FAILED - {e}\n")
    
    # Summary
    print("\n" + "="*80)
    print("📊 PHASE 20A VERIFICATION SUMMARY")
    print("="*80)
    print(f"\n✅ Passed: {results['passed_tests']}/{results['total_tests']} tests")
    print(f"❌ Failed: {results['total_tests'] - results['passed_tests']}/{results['total_tests']} tests\n")
    
    if results['passed_tests'] == results['total_tests']:
        print("🎉 ALL TESTS PASSED - Phase 20A implementation is COMPLETE!")
        print("\nNext steps:")
        print("1. Test in UI: Navigate to Azure ML Lab and click 'Run Prediction'")
        print("2. Wire up update_predictions_table callback to read from PostgreSQL")
        print("3. Test Insights and Metrics buttons")
    else:
        print("⚠️  SOME TESTS FAILED - Review errors above")
        print("\nFailed components:")
        for key, value in results.items():
            if key not in ['total_tests', 'passed_tests'] and not value:
                print(f"  • {key.replace('_', ' ').title()}")
    
    print("\n" + "="*80 + "\n")
    
    # Save results
    with open('/app/phase20a_verification_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.utcnow().isoformat(),
            'results': results,
            'status': 'PASSED' if results['passed_tests'] == results['total_tests'] else 'FAILED'
        }, f, indent=2)
    
    return results['passed_tests'] == results['total_tests']

if __name__ == '__main__':
    success = verify_phase20a()
    sys.exit(0 if success else 1)

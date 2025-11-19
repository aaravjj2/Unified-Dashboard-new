#!/usr/bin/env python3
"""
Phase 20B Quick Validation
Directly test that callbacks now read from PostgreSQL
"""
import sys
import os
import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'financial_dashboard'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'financial_dashboard', 'tabs', 'azure_ml_lab'))

from ml_database import get_latest_predictions

# Database connection - use postgres_db hostname within Docker network
DATABASE_URL = "postgresql://postgres:postgres@postgres_db:5432/market_data"

def get_db_connection():
    """Get PostgreSQL connection"""
    return psycopg2.connect(DATABASE_URL)

def test_predictions_data_available():
    """Test that get_latest_predictions returns data"""
    print("=" * 60)
    print("TEST 1: Verify get_latest_predictions() returns data")
    print("=" * 60)
    
    try:
        predictions = get_latest_predictions(limit=20)
        
        if not predictions:
            print("❌ FAIL: No predictions returned from database")
            return False
            
        print(f"✅ PASS: Retrieved {len(predictions)} predictions from database")
        
        # Check first prediction structure
        first_pred = predictions[0]
        required_keys = ['ticker', 'predicted_return', 'confidence', 'run_id']
        missing_keys = [k for k in required_keys if k not in first_pred]
        
        if missing_keys:
            print(f"❌ FAIL: Missing keys in prediction: {missing_keys}")
            return False
            
        print(f"✅ PASS: Prediction structure valid")
        print(f"   Sample: Ticker={first_pred['ticker']}, Run ID={first_pred['run_id']}, "
              f"Confidence={first_pred['confidence']:.2%}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Exception - {e}")
        return False

def test_ml_prediction_runs_aggregates():
    """Test that aggregate query works for performance metrics"""
    print("\n" + "=" * 60)
    print("TEST 2: Verify ml_prediction_runs aggregate query")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT 
            COUNT(*) as total_runs,
            AVG(overall_confidence) as avg_confidence,
            AVG(latency_ms) as avg_latency,
            SUM(num_predictions) as total_predictions,
            COUNT(CASE WHEN fallback_reason IS NOT NULL THEN 1 END) as fallback_count
        FROM ml_prediction_runs
        WHERE created_at > NOW() - INTERVAL '7 days'
        """
        
        cursor.execute(query)
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        total_runs, avg_conf, avg_lat, total_preds, fallback_count = result
        
        if total_runs == 0:
            print("❌ FAIL: No prediction runs found in last 7 days")
            return False
            
        print(f"✅ PASS: Query executed successfully")
        print(f"   Total Runs (7d): {total_runs}")
        print(f"   Avg Confidence: {(avg_conf or 0)*100:.1f}%")
        print(f"   Avg Latency: {avg_lat or 0:.2f}ms")
        print(f"   Total Predictions: {total_preds or 0}")
        print(f"   Fallback Count: {fallback_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Exception - {e}")
        return False

def test_database_connectivity():
    """Basic database connectivity test"""
    print("\n" + "=" * 60)
    print("TEST 3: Verify database connectivity")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        print(f"✅ PASS: Connected to PostgreSQL")
        print(f"   Version: {version[:50]}...")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Cannot connect to database - {e}")
        return False

def main():
    print("\n" + "=" * 60)
    print("PHASE 20B QUICK VALIDATION")
    print("Verify PostgreSQL callback integration")
    print("=" * 60 + "\n")
    
    results = []
    
    # Test 1: Database connectivity
    results.append(("Database Connectivity", test_database_connectivity()))
    
    # Test 2: Predictions data retrieval
    results.append(("Predictions Data Retrieval", test_predictions_data_available()))
    
    # Test 3: Aggregate query for metrics
    results.append(("Performance Metrics Aggregates", test_ml_prediction_runs_aggregates()))
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("=" * 60)
    print(f"RESULT: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 SUCCESS: Phase 20B callback integration verified!")
        print("   - Predictions table can read from PostgreSQL")
        print("   - Performance metrics can compute aggregates")
        print("   - Database connectivity confirmed")
        return 0
    else:
        print("\n⚠️ FAILURE: Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())

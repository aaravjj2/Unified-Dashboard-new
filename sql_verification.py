#!/usr/bin/env python3
"""
SQL Verification Script for Pre-Phase 24 Validation
Queries all critical tables and exports results.
"""
import os
import sys
import json
import psycopg2
import psycopg2.extras
from datetime import datetime

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/market_data")

def run_query(cur, query_name, sql):
    """Execute query and return results"""
    print(f"\n{'='*80}")
    print(f"QUERY: {query_name}")
    print(f"{'='*80}")
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        print(f"✅ Returned {len(rows)} rows")
        
        # Print first 5 rows
        for i, row in enumerate(rows[:5]):
            print(f"  Row {i+1}: {dict(row)}")
        
        if len(rows) > 5:
            print(f"  ... and {len(rows) - 5} more rows")
        
        return {
            "query": query_name,
            "sql": sql,
            "row_count": len(rows),
            "sample_rows": [dict(r) for r in rows[:10]],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return {
            "query": query_name,
            "sql": sql,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

def main():
    """Run all verification queries"""
    print("="*80)
    print("PRE-PHASE 24 SQL VERIFICATION")
    print("="*80)
    print(f"Database: {DB_URL}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print("="*80)
    
    results = []
    
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Query 1: Price cache recent updates
        results.append(run_query(
            cur,
            "price_cache_recent",
            "SELECT symbol, close_price, updated_at FROM price_cache ORDER BY updated_at DESC LIMIT 10"
        ))
        
        # Query 2: Options forecasts
        results.append(run_query(
            cur,
            "options_forecasts_all",
            "SELECT id, symbol, strike, forecast_data, created_at FROM options_forecasts ORDER BY created_at DESC LIMIT 10"
        ))
        
        # Query 3: Backtest results
        results.append(run_query(
            cur,
            "backtest_results_all",
            "SELECT id, strategy_name, metrics, created_at FROM backtest_results ORDER BY created_at DESC LIMIT 10"
        ))
        
        # Query 4: Chat conversations
        results.append(run_query(
            cur,
            "chat_conversations_all",
            "SELECT id, session_id, message, response, created_at FROM chat_conversations ORDER BY created_at DESC LIMIT 10"
        ))
        
        # Query 5: Table counts
        results.append(run_query(
            cur,
            "table_counts",
            """
            SELECT 
                'price_cache' as table_name, COUNT(*) as row_count FROM price_cache
            UNION ALL
            SELECT 'options_forecasts', COUNT(*) FROM options_forecasts
            UNION ALL
            SELECT 'backtest_results', COUNT(*) FROM backtest_results
            UNION ALL
            SELECT 'chat_conversations', COUNT(*) FROM chat_conversations
            """
        ))
        
        cur.close()
        conn.close()
        
        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        
        successful = sum(1 for r in results if "error" not in r)
        total = len(results)
        
        print(f"✅ Successful queries: {successful}/{total}")
        
        # Write results to JSON
        output = {
            "timestamp": datetime.utcnow().isoformat(),
            "database_url": DB_URL.replace("postgres:", "postgres:****@").replace("@", "****@"),
            "queries": results,
            "summary": {
                "total_queries": total,
                "successful": successful,
                "failed": total - successful
            }
        }
        
        output_file = "test-artifacts/pre24/sql_verification_results.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, "w") as f:
            json.dump(output, f, indent=2, default=str)
        
        print(f"\n✅ Results written to: {output_file}")
        
        return 0 if successful == total else 1
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

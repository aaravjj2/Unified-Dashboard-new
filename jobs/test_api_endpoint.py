#!/usr/bin/env python3
"""
Test /api/weekly_picks endpoint directly without starting full Flask app.
This validates the PostgreSQL query logic.
"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor

# Database connection config
db_config = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'financial_dashboard'),
    'user': os.getenv('POSTGRES_USER', 'dashboard_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'newpassword')
}

print("=" * 80)
print("Testing /api/weekly_picks Endpoint Logic")
print("=" * 80)

try:
    # Connect to PostgreSQL
    print(f"\n📡 Connecting to PostgreSQL at {db_config['host']}:{db_config['port']}")
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Query latest weekly picks from production table
    query = """
        SELECT 
            week_start_date,
            ticker,
            rank,
            rationale,
            momentum_score,
            sentiment_score,
            fundamental_score,
            combined_score,
            chart_array,
            metadata,
            generated_at
        FROM weekly_picks_production
        WHERE week_start_date = (
            SELECT MAX(week_start_date) 
            FROM weekly_picks_production
        )
        ORDER BY rank ASC
    """
    
    print("✅ Connected! Executing query...")
    cursor.execute(query)
    picks = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    if not picks:
        print("⚠️  No weekly picks data available in PostgreSQL")
        exit(1)
    
    # Convert to JSON-serializable format
    picks_data = []
    tickers = []
    
    for pick in picks:
        tickers.append(pick['ticker'])
        picks_data.append({
            'rank': pick['rank'],
            'ticker': pick['ticker'],
            'combined_score': float(pick['combined_score']),
            'momentum_score': float(pick['momentum_score']),
            'sentiment_score': float(pick['sentiment_score']),
            'fundamental_score': float(pick['fundamental_score']),
            'rationale': pick['rationale'],
            'chart_array': pick['chart_array'],  # Already JSON from JSONB column
            'metadata': pick['metadata'],
            'week_start_date': pick['week_start_date'].isoformat() if pick['week_start_date'] else None,
            'generated_at': pick['generated_at'].isoformat() if pick['generated_at'] else None
        })
    
    # Construct API response
    response = {
        'status': 'success',
        'count': len(picks_data),
        'tickers': tickers,
        'week_start_date': picks[0]['week_start_date'].isoformat() if picks[0]['week_start_date'] else None,
        'data': picks_data,
        'source': 'postgresql_production'
    }
    
    print(f"\n✅ SUCCESS: Retrieved {len(picks_data)} weekly picks from PostgreSQL")
    print(f"Week Start Date: {response['week_start_date']}")
    print(f"Tickers: {tickers}")
    print("\nAPI Response Structure:")
    print(json.dumps(response, indent=2, default=str))
    
    print("\n" + "=" * 80)
    print("DETAILED PICKS:")
    print("=" * 80)
    
    for pick in picks_data:
        print(f"\nRank #{pick['rank']}: {pick['ticker']} (Combined Score: {pick['combined_score']:.2f})")
        print(f"  Momentum: {pick['momentum_score']:.2f}")
        print(f"  Sentiment: {pick['sentiment_score']:.2f}")
        print(f"  Fundamental: {pick['fundamental_score']:.2f}")
        print(f"  Rationale: {pick['rationale'][:100]}...")
        print(f"  Chart Points: {len(pick['chart_array'])} data points")
    
    print("\n✅ /api/weekly_picks endpoint logic validated!")
    
except psycopg2.Error as e:
    print(f"\n❌ PostgreSQL error: {e}")
    exit(1)
except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

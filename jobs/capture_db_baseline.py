#!/usr/bin/env python3
"""
Capture baseline database state for idempotency validation.
This will be compared against post-iteration state.
"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Database connection config
db_config = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'financial_dashboard'),
    'user': os.getenv('POSTGRES_USER', 'dashboard_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'newpassword')
}

print("=" * 80)
print("CAPTURING DATABASE BASELINE FOR IDEMPOTENCY VALIDATION")
print("=" * 80)

try:
    # Connect to PostgreSQL
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Query current weekly picks
    query = """
        SELECT 
            week_start_date,
            ticker,
            rank,
            combined_score,
            momentum_score,
            sentiment_score,
            fundamental_score,
            generated_at
        FROM weekly_picks_production
        ORDER BY week_start_date DESC, rank ASC
    """
    
    cursor.execute(query)
    picks = cursor.fetchall()
    
    # Convert to serializable format
    baseline = {
        'timestamp': datetime.now().isoformat(),
        'total_picks': len(picks),
        'picks': []
    }
    
    for pick in picks:
        baseline['picks'].append({
            'week_start_date': pick['week_start_date'].isoformat() if pick['week_start_date'] else None,
            'ticker': pick['ticker'],
            'rank': pick['rank'],
            'combined_score': float(pick['combined_score']),
            'momentum_score': float(pick['momentum_score']),
            'sentiment_score': float(pick['sentiment_score']),
            'fundamental_score': float(pick['fundamental_score']),
            'generated_at': pick['generated_at'].isoformat() if pick['generated_at'] else None
        })
    
    cursor.close()
    conn.close()
    
    # Save baseline
    output_path = 'outputs/phase14/db_baseline.json'
    with open(output_path, 'w') as f:
        json.dump(baseline, f, indent=2)
    
    print(f"\n✅ Baseline captured: {len(picks)} picks")
    print(f"📝 Saved to: {output_path}")
    
    print("\nCurrent Picks:")
    for pick in baseline['picks']:
        print(f"  {pick['rank']}. {pick['ticker']} - Score: {pick['combined_score']:.2f} (Week: {pick['week_start_date']})")
    
    print(f"\n✅ Baseline capture complete!")
    
except Exception as e:
    print(f"\n❌ Error capturing baseline: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

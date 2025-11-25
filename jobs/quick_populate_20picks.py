#!/usr/bin/env python3
"""Quick script to populate 20 test picks for the current week to verify UI display."""

import os
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv('keys.env')

# Mock picks data - 20 tickers with varied scores
MOCK_PICKS = [
    ("AAPL", 1, "Strong momentum with bullish technical indicators", 85.2, 78.5, 91.0, 86.3),
    ("MSFT", 2, "Cloud growth driving strong fundamentals", 83.1, 75.2, 89.5, 84.7),
    ("GOOGL", 3, "AI leadership positioning for growth", 81.5, 82.1, 77.8, 83.2),
    ("NVDA", 4, "GPU demand sustained across sectors", 80.3, 88.9, 69.2, 82.8),
    ("AMZN", 5, "E-commerce resilience with AWS strength", 78.9, 71.3, 84.7, 80.1),
    ("META", 6, "Social platform monetization improving", 77.2, 76.8, 75.5, 78.9),
    ("TSLA", 7, "EV market leader with expansion plans", 75.6, 82.3, 65.2, 77.4),
    ("BRK.B", 8, "Diversified holdings provide stability", 74.1, 68.5, 78.9, 75.8),
    ("JPM", 9, "Financial sector strength continues", 72.8, 70.1, 74.2, 74.1),
    ("V", 10, "Payment processing growth intact", 71.5, 73.4, 68.9, 72.9),
    ("JNJ", 11, "Healthcare demand remains robust", 70.2, 65.8, 73.1, 71.6),
    ("WMT", 12, "Retail resilience with digital growth", 69.1, 67.2, 70.5, 70.3),
    ("PG", 13, "Consumer staples providing stability", 68.3, 64.9, 71.2, 69.8),
    ("MA", 14, "Transaction volume growth strong", 67.5, 71.8, 62.1, 68.9),
    ("HD", 15, "Home improvement demand sustained", 66.8, 69.3, 63.8, 68.2),
    ("UNH", 16, "Healthcare services expansion", 65.9, 63.2, 68.1, 67.1),
    ("DIS", 17, "Entertainment portfolio diversification", 64.7, 66.5, 61.9, 66.3),
    ("BAC", 18, "Banking sector momentum building", 63.5, 62.8, 63.9, 65.2),
    ("CSCO", 19, "Networking infrastructure demand", 62.3, 61.1, 63.2, 64.1),
    ("ADBE", 20, "Creative software suite leadership", 61.2, 60.5, 61.8, 63.0),
]

def populate_20_picks():
    """Delete current week's picks and insert 20 new ones."""
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database=os.getenv('POSTGRES_DB'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD')
    )
    cur = conn.cursor()
    
    # Get current Monday (week start)
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    
    print(f"Populating 20 picks for week starting {week_start}")
    
    # Delete existing picks for this week
    cur.execute("DELETE FROM weekly_picks_production WHERE week_start_date = %s", (week_start,))
    deleted = cur.rowcount
    print(f"Deleted {deleted} existing picks")
    
    # Insert 20 new picks
    for ticker, rank, rationale, combined, momentum, sentiment, fundamental in MOCK_PICKS:
        cur.execute("""
            INSERT INTO weekly_picks_production 
            (week_start_date, ticker, rank, rationale, combined_score, 
             momentum_score, sentiment_score, fundamental_score, 
             chart_array, metadata, generated_at, generator_version)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            week_start, ticker, rank, rationale, combined,
            momentum, sentiment, fundamental,
            '[]',  # empty chart array for now
            '{}',  # empty metadata
            datetime.now(),
            '1.0.0-quick-populate'
        ))
    
    conn.commit()
    print(f"✅ Inserted 20 picks for week {week_start}")
    
    # Verify
    cur.execute("SELECT COUNT(*) FROM weekly_picks_production WHERE week_start_date = %s", (week_start,))
    count = cur.fetchone()[0]
    print(f"Verification: {count} picks in database for this week")
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    populate_20_picks()

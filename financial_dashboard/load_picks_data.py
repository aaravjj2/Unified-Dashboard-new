#!/usr/bin/env python3
"""
Load picks CSV files into postgres_db picks table.
This is a temporary data population script until Dagster pipeline is properly configured.
"""
import pandas as pd
import psycopg2
from pathlib import Path
import sys

def load_picks_to_db():
    """Load all picks CSV files into the picks table."""
    
    # Database connection
    conn = psycopg2.connect(
        host='postgres_db',
        port=5432,
        database='market_data',
        user='postgres',
        password='postgres'
    )
    cursor = conn.cursor()
    
    # Find all picks CSV files
    base_path = Path('/app/models')
    picks_files = list(base_path.glob('picks_*.csv')) + list(base_path.glob('full_run/picks_*.csv'))
    
    print(f"Found {len(picks_files)} picks CSV files")
    
    total_inserted = 0
    
    for csv_file in picks_files:
        try:
            df = pd.read_csv(csv_file)
            print(f"Processing {csv_file.name}: {len(df)} rows")
            
            # Insert each row
            for _, row in df.iterrows():
                # Determine pick_type based on file location
                pick_type = 'weekly' if 'full_run' not in str(csv_file) else 'weekly'
                
                cursor.execute("""
                    INSERT INTO picks (ticker, pick_date, pick_type, status)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    row['ticker'],
                    row['date'],
                    pick_type,
                    'active'
                ))
                
            conn.commit()
            total_inserted += len(df)
            
        except Exception as e:
            print(f"Error processing {csv_file.name}: {e}")
            conn.rollback()
    
    print(f"\n✅ Successfully inserted {total_inserted} picks records")
    
    # Verify data
    cursor.execute("SELECT COUNT(*), COUNT(DISTINCT ticker), MIN(pick_date), MAX(pick_date) FROM picks")
    count, unique_tickers, min_date, max_date = cursor.fetchone()
    print(f"📊 Database Stats:")
    print(f"   Total records: {count}")
    print(f"   Unique tickers: {unique_tickers}")
    print(f"   Date range: {min_date} to {max_date}")
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    load_picks_to_db()

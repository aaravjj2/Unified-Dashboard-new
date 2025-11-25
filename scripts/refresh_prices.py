#!/usr/bin/env python3
"""
Price refresh script for Weekly/Monthly Picks
Updates price_cache with fresh prices for testing
"""
import os
import sys
import datetime
import psycopg2
import psycopg2.extras

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/market_data")

def refresh_prices():
    """Update price cache with small increments for testing"""
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get current prices (price_cache uses close_price column)
        cur.execute("SELECT symbol, close_price FROM price_cache ORDER BY updated_at DESC LIMIT 50")
        rows = cur.fetchall()
        
        if not rows:
            print("⚠️  No prices found in cache")
            return
        
        now = datetime.datetime.utcnow()
        updated_count = 0
        
        # Update each price with small increment for testing
        for row in rows:
            symbol = row['symbol']
            current_price = float(row['close_price']) if row['close_price'] else 100.0
            # Add 1 cent for deterministic test
            new_price = round(current_price + 0.01, 2)
            
            cur.execute("""
                UPDATE price_cache 
                SET close_price = %s, updated_at = %s 
                WHERE symbol = %s
            """, (new_price, now, symbol))
            updated_count += 1
        
        conn.commit()
        print(f"✅ Refreshed {updated_count} symbols at {now.isoformat()}")
        
        cur.close()
        conn.close()
        
        return {"status": "success", "updated": updated_count, "timestamp": now.isoformat()}
        
    except Exception as e:
        print(f"❌ Error refreshing prices: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    result = refresh_prices()
    print(f"Result: {result}")

#!/usr/bin/env python3
"""
Phase 20B Database Schema Inspector
Check available tables and columns for Azure ML Lab integration
"""
import psycopg2
import psycopg2.extras

DATABASE_URL = "postgresql://postgres:postgres@postgres_db:5432/market_data"

def inspect_schema():
    """Inspect database schema for Azure ML tables"""
    print("=" * 80)
    print("PHASE 20B DATABASE SCHEMA INSPECTION")
    print("=" * 80)
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Find all ml_* tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE 'ml_%'
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        
        print(f"\n✅ Found {len(tables)} ML-related tables:\n")
        
        for table in tables:
            table_name = table['table_name']
            print(f"📊 Table: {table_name}")
            
            # Get columns
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                print(f"   - {col['column_name']}: {col['data_type']} ({nullable})")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            count = cursor.fetchone()['count']
            print(f"   📈 Rows: {count}\n")
        
        # Check for stock_metadata table
        print("\n🔍 Checking for stock_metadata table...")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'stock_metadata'
            )
        """)
        exists = cursor.fetchone()['exists']
        
        if exists:
            print("✅ stock_metadata table exists")
            cursor.execute("SELECT COUNT(*) as count FROM stock_metadata")
            count = cursor.fetchone()['count']
            print(f"   📈 Rows: {count}")
        else:
            print("⚠️ stock_metadata table NOT FOUND - will need to create")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 80)
        print("SCHEMA INSPECTION COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(inspect_schema())

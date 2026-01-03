"""
Database Utilities - PostgreSQL Connection Pool
================================================
Centralized database access with connection pooling for production.

Features:
- PostgreSQL connection pooling (psycopg2.pool)
- Configuration from keys.env
- Thread-safe connection management
- Historical picks data storage
- Portfolio snapshots tracking
- Health check support

Migration Note:
- Upgraded from SQLite to PostgreSQL in Sprint 2
- Maintains backward compatibility for existing functions
- Connection parameters read from keys.env
"""

import os
import logging
from datetime import datetime
import json
from typing import Optional, Dict, List, Any
from contextlib import contextmanager
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from keys.env
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'keys.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
    logger.info(f"Loaded database config from {env_path}")
else:
    logger.warning(f"keys.env not found at {env_path}, using defaults")

# PostgreSQL connection pool (initialized on first use)
_connection_pool = None
_pool_lock = None

# Fallback SQLite path for legacy compatibility
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'portfolio.db')


def initialize_database():
    """Initialize SQLite database with snapshots table."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create snapshots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                portfolio_value REAL,
                equity REAL,
                buying_power REAL,
                cash REAL,
                num_positions INTEGER,
                unrealized_pl REAL,
                positions_json TEXT,
                account_json TEXT
            )
        ''')
        
        # Create index on timestamp
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON snapshots(timestamp)
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info(f"Database initialized: {DB_PATH}")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False


def save_daily_snapshot(account_info, positions_data):
    """
    Save daily portfolio snapshot to database.
    
    Args:
        account_info: Dict with portfolio_value, equity, buying_power, cash
        positions_data: List of position dicts
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure database exists
        if not os.path.exists(DB_PATH):
            initialize_database()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Calculate aggregates
        portfolio_value = account_info.get('portfolio_value', 0)
        equity = account_info.get('equity', 0)
        buying_power = account_info.get('buying_power', 0)
        cash = account_info.get('cash', 0)
        num_positions = len(positions_data) if positions_data else 0
        
        # Calculate total unrealized P/L
        unrealized_pl = 0.0
        if positions_data:
            for pos in positions_data:
                unrealized_pl += pos.get('unrealized_pl', 0)
        
        # Serialize to JSON
        positions_json = json.dumps(positions_data) if positions_data else '[]'
        account_json = json.dumps(account_info)
        
        # Insert snapshot
        cursor.execute('''
            INSERT INTO snapshots (
                portfolio_value, equity, buying_power, cash, 
                num_positions, unrealized_pl, positions_json, account_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            portfolio_value, equity, buying_power, cash,
            num_positions, unrealized_pl, positions_json, account_json
        ))
        
        conn.commit()
        snapshot_id = cursor.lastrowid
        conn.close()
        
        logger.info(f"Saved portfolio snapshot #{snapshot_id}: ${portfolio_value:,.2f}, {num_positions} positions")
        return True
        
    except Exception as e:
        logger.error(f"Error saving daily snapshot: {e}")
        return False


def get_recent_snapshots(days=30):
    """
    Retrieve recent portfolio snapshots.
    
    Args:
        days: Number of days to retrieve
    
    Returns:
        List of snapshot dicts, or empty list on error
    """
    try:
        if not os.path.exists(DB_PATH):
            return []
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                id, timestamp, portfolio_value, equity, buying_power, cash,
                num_positions, unrealized_pl, positions_json, account_json
            FROM snapshots
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp DESC
        ''', (days,))
        
        rows = cursor.fetchall()
        conn.close()
        
        snapshots = []
        for row in rows:
            snapshots.append({
                'id': row[0],
                'timestamp': row[1],
                'portfolio_value': row[2],
                'equity': row[3],
                'buying_power': row[4],
                'cash': row[5],
                'num_positions': row[6],
                'unrealized_pl': row[7],
                'positions': json.loads(row[8]) if row[8] else [],
                'account': json.loads(row[9]) if row[9] else {}
            })
        
        return snapshots
        
    except Exception as e:
        logger.error(f"Error retrieving snapshots: {e}")
        return []


def get_snapshot_history(days=90):
    """
    Get portfolio value history for charting.
    
    Args:
        days: Number of days to retrieve
    
    Returns:
        Dict with 'timestamps' and 'values' lists
    """
    try:
        if not os.path.exists(DB_PATH):
            return {'timestamps': [], 'values': []}
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, portfolio_value
            FROM snapshots
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp ASC
        ''', (days,))
        
        rows = cursor.fetchall()
        conn.close()
        
        timestamps = [row[0] for row in rows]
        values = [row[1] for row in rows]
        
        return {'timestamps': timestamps, 'values': values}
        
    except Exception as e:
        logger.error(f"Error retrieving snapshot history: {e}")
        return {'timestamps': [], 'values': []}


def cleanup_old_snapshots(days=365):
    """
    Delete snapshots older than specified days.
    
    Args:
        days: Keep snapshots from this many days back
    
    Returns:
        Number of deleted records, or -1 on error
    """
    try:
        if not os.path.exists(DB_PATH):
            return 0
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM snapshots
            WHERE timestamp < datetime('now', '-' || ? || ' days')
        ''', (days,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"Cleaned up {deleted_count} old snapshots (older than {days} days)")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error cleaning up old snapshots: {e}")
        return -1


# ==================== PostgreSQL Connection Pool ====================
# Sprint 2: Centralized database for picks history

import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
from pathlib import Path

# PostgreSQL connection pool (initialized once)
_pg_connection_pool = None


def _load_pg_credentials():
    """Load PostgreSQL credentials from keys.env file."""
    keys_env_path = Path(__file__).parent.parent / "keys.env"
    
    if not keys_env_path.exists():
        logger.warning(f"keys.env not found at {keys_env_path}, using defaults")
        return {
            'host': 'localhost',
            'port': 5432,
            'database': 'financial_db',
            'user': 'postgres',
            'password': ''
        }
    
    credentials = {}
    with open(keys_env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                credentials[key.strip()] = value.strip()
    
    # Extract PostgreSQL credentials
    db_config = {
        'host': credentials.get('POSTGRES_HOST', 'localhost'),
        'port': int(credentials.get('POSTGRES_PORT', '5432')),
        'database': credentials.get('POSTGRES_DB', 'financial_db'),
        'user': credentials.get('POSTGRES_USER', 'postgres'),
        'password': credentials.get('POSTGRES_PASSWORD', '')
    }
    
    logger.info(f"Loaded PG config: host={db_config['host']}, db={db_config['database']}")
    return db_config


def initialize_pg_pool(minconn=1, maxconn=10):
    """Initialize the PostgreSQL connection pool."""
    global _pg_connection_pool
    
    if _pg_connection_pool is not None:
        logger.info("PostgreSQL connection pool already initialized")
        return
    
    try:
        db_config = _load_pg_credentials()
        _pg_connection_pool = psycopg2.pool.SimpleConnectionPool(
            minconn,
            maxconn,
            **db_config
        )
        logger.info(f"Initialized PostgreSQL connection pool (min={minconn}, max={maxconn})")
    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL pool: {e}")
        raise


@contextmanager
def get_pg_connection():
    """
    Context manager for getting a PostgreSQL connection from the pool.
    
    Usage:
        with get_pg_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM picks_history")
            results = cursor.fetchall()
    """
    if _pg_connection_pool is None:
        initialize_pg_pool()
    
    conn = None
    try:
        conn = _pg_connection_pool.getconn()
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"PostgreSQL error: {e}")
        raise
    finally:
        if conn:
            _pg_connection_pool.putconn(conn)


def execute_pg_query(query, params=None, fetch=True):
    """
    Execute a PostgreSQL query and optionally fetch results.
    
    Args:
        query: SQL query string
        params: Query parameters (tuple or dict)
        fetch: If True, return results; if False, commit changes
    
    Returns:
        List of tuples (if fetch=True) or None
    """
    with get_pg_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            
            if fetch:
                results = cursor.fetchall()
                return results
            else:
                conn.commit()
                return None
        finally:
            cursor.close()


def execute_pg_many(query, params_list):
    """
    Execute a PostgreSQL query with multiple parameter sets (bulk insert/update).
    
    Args:
        query: SQL query string with placeholders
        params_list: List of parameter tuples
    """
    with get_pg_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.executemany(query, params_list)
            conn.commit()
            logger.info(f"Executed bulk PostgreSQL query: {len(params_list)} rows affected")
        finally:
            cursor.close()


def create_picks_history_table():
    """Create the picks_history table if it doesn't exist."""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS picks_history (
        id SERIAL PRIMARY KEY,
        ticker VARCHAR(20) NOT NULL,
        pick_date DATE NOT NULL,
        pick_type VARCHAR(20) NOT NULL,
        predicted_return FLOAT,
        confidence FLOAT,
        sector VARCHAR(50),
        market_cap FLOAT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(ticker, pick_date, pick_type)
    );
    
    CREATE INDEX IF NOT EXISTS idx_picks_ticker ON picks_history(ticker);
    CREATE INDEX IF NOT EXISTS idx_picks_date ON picks_history(pick_date);
    CREATE INDEX IF NOT EXISTS idx_picks_type ON picks_history(pick_type);
    """
    
    try:
        execute_pg_query(create_table_sql, fetch=False)
        logger.info("picks_history table created/verified successfully")
    except Exception as e:
        logger.error(f"Failed to create picks_history table: {e}")
        raise


def close_pg_pool():
    """Close all PostgreSQL connections in the pool."""
    global _pg_connection_pool
    if _pg_connection_pool:
        _pg_connection_pool.closeall()
        _pg_connection_pool = None
        logger.info("Closed all PostgreSQL connections")

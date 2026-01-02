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
- Legacy SQLite fallback for development

Migration Note:
- Upgraded from SQLite to PostgreSQL in Sprint 2
- Maintains backward compatibility for existing functions
- Connection parameters read from keys.env
"""

import os
import logging
from datetime import datetime
import json
from typing import Optional, Dict, List, Any, Tuple
from contextlib import contextmanager
from threading import Lock
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from keys.env
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'keys.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
    logger.info(f"Loaded database config from {env_path}")
else:
    logger.warning(f"keys.env not found at {env_path}, using defaults")

# Try to import PostgreSQL and create connection pool
POSTGRES_AVAILABLE = False
_connection_pool = None
_pool_lock = Lock()

try:
    import psycopg2
    from psycopg2 import pool
    POSTGRES_AVAILABLE = True
    logger.info("✓ PostgreSQL (psycopg2) available")
except ImportError:
    logger.warning("PostgreSQL (psycopg2) not available, falling back to SQLite")
    import sqlite3

# Fallback SQLite path for legacy compatibility
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'portfolio.db')


# ==============================================================================
# POSTGRESQL CONNECTION POOL
# ==============================================================================

def get_postgres_config() -> Dict[str, Any]:
    """
    Get PostgreSQL configuration from environment variables.
    
    Returns:
        Dict with host, port, user, password, database
    """
    return {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', ''),
        'database': os.getenv('POSTGRES_DB', 'financial_dashboard'),
    }


def initialize_postgres_pool(minconn=2, maxconn=10):
    """
    Initialize PostgreSQL connection pool.
    
    Args:
        minconn: Minimum number of connections in pool
        maxconn: Maximum number of connections in pool
    
    Returns:
        True if successful, False otherwise
    """
    global _connection_pool
    
    if not POSTGRES_AVAILABLE:
        logger.error("PostgreSQL not available")
        return False
    
    with _pool_lock:
        if _connection_pool is not None:
            logger.info("Connection pool already initialized")
            return True
        
        try:
            config = get_postgres_config()
            logger.info(f"Initializing connection pool: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
            
            _connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=minconn,
                maxconn=maxconn,
                host=config['host'],
                port=config['port'],
                user=config['user'],
                password=config['password'],
                database=config['database']
            )
            
            logger.info(f"✓ PostgreSQL connection pool initialized ({minconn}-{maxconn} connections)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL connection pool: {e}")
            return False


@contextmanager
def get_postgres_connection():
    """
    Context manager to get a connection from the pool.
    
    Usage:
        with get_postgres_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM table")
            results = cursor.fetchall()
    
    Yields:
        PostgreSQL connection from pool
    """
    if not POSTGRES_AVAILABLE or _connection_pool is None:
        raise RuntimeError("PostgreSQL connection pool not initialized")
    
    conn = None
    try:
        conn = _connection_pool.getconn()
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            _connection_pool.putconn(conn)


def close_postgres_pool():
    """Close all connections in the pool."""
    global _connection_pool
    
    with _pool_lock:
        if _connection_pool:
            _connection_pool.closeall()
            _connection_pool = None
            logger.info("PostgreSQL connection pool closed")


def check_postgres_health() -> Tuple[bool, Optional[str]]:
    """
    Check PostgreSQL database connectivity.
    
    Returns:
        Tuple of (is_healthy, error_message)
    """
    if not POSTGRES_AVAILABLE:
        return False, "PostgreSQL not available"
    
    if _connection_pool is None:
        if not initialize_postgres_pool():
            return False, "Failed to initialize connection pool"
    
    try:
        with get_postgres_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return True, None
    except Exception as e:
        return False, str(e)


# ==============================================================================
# DATABASE SCHEMA INITIALIZATION
# ==============================================================================

def initialize_postgres_schema():
    """
    Initialize PostgreSQL database schema.
    Creates tables for portfolio snapshots and picks history.
    
    Returns:
        True if successful, False otherwise
    """
    if not POSTGRES_AVAILABLE or _connection_pool is None:
        logger.error("PostgreSQL not available")
        return False
    
    try:
        with get_postgres_connection() as conn:
            cursor = conn.cursor()
            
            # Create snapshots table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS snapshots (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    portfolio_value NUMERIC(15, 2),
                    equity NUMERIC(15, 2),
                    buying_power NUMERIC(15, 2),
                    cash NUMERIC(15, 2),
                    num_positions INTEGER,
                    unrealized_pl NUMERIC(15, 2),
                    positions_json JSONB,
                    account_json JSONB
                )
            ''')
            
            # Create index on timestamp
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp 
                ON snapshots(timestamp DESC)
            ''')
            
            # Create picks_history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS picks_history (
                    id SERIAL PRIMARY KEY,
                    pick_date DATE NOT NULL,
                    ticker VARCHAR(20) NOT NULL,
                    price NUMERIC(10, 2),
                    target_price NUMERIC(10, 2),
                    stop_loss NUMERIC(10, 2),
                    sector VARCHAR(100),
                    catalyst TEXT,
                    timeframe VARCHAR(50),
                    risk_level VARCHAR(20),
                    confidence NUMERIC(3, 2),
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB
                )
            ''')
            
            # Create indexes for picks_history
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_picks_date 
                ON picks_history(pick_date DESC)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_picks_ticker 
                ON picks_history(ticker)
            ''')
            
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_picks_unique
                ON picks_history(pick_date, ticker)
            ''')
            
            conn.commit()
            logger.info("✓ PostgreSQL schema initialized")
            return True
            
    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL schema: {e}")
        return False


# ==============================================================================
# PORTFOLIO SNAPSHOT FUNCTIONS (PostgreSQL Primary, SQLite Fallback)
# ==============================================================================

def save_daily_snapshot(account_info: Dict, positions_data: List[Dict]) -> bool:
    """
    Save daily portfolio snapshot to database.
    Uses PostgreSQL if available, falls back to SQLite.
    
    Args:
        account_info: Dict with portfolio_value, equity, buying_power, cash
        positions_data: List of position dicts
    
    Returns:
        True if successful, False otherwise
    """
    if POSTGRES_AVAILABLE and _connection_pool:
        return _save_snapshot_postgres(account_info, positions_data)
    else:
        return _save_snapshot_sqlite(account_info, positions_data)


def _save_snapshot_postgres(account_info: Dict, positions_data: List[Dict]) -> bool:
    """Save snapshot to PostgreSQL."""
    try:
        with get_postgres_connection() as conn:
            cursor = conn.cursor()
            
            # Calculate aggregates
            portfolio_value = account_info.get('portfolio_value', 0)
            equity = account_info.get('equity', 0)
            buying_power = account_info.get('buying_power', 0)
            cash = account_info.get('cash', 0)
            num_positions = len(positions_data) if positions_data else 0
            
            # Calculate total unrealized P/L
            unrealized_pl = sum(pos.get('unrealized_pl', 0) for pos in positions_data) if positions_data else 0.0
            
            # Insert snapshot (JSON columns automatically handled)
            cursor.execute('''
                INSERT INTO snapshots (
                    portfolio_value, equity, buying_power, cash, 
                    num_positions, unrealized_pl, positions_json, account_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                portfolio_value, equity, buying_power, cash,
                num_positions, unrealized_pl,
                json.dumps(positions_data) if positions_data else '[]',
                json.dumps(account_info)
            ))
            
            conn.commit()
            logger.info(f"✓ Saved portfolio snapshot (PostgreSQL): ${portfolio_value:,.2f}, {num_positions} positions")
            return True
            
    except Exception as e:
        logger.error(f"Error saving snapshot to PostgreSQL: {e}")
        return False


def _save_snapshot_sqlite(account_info: Dict, positions_data: List[Dict]) -> bool:
    """Save snapshot to SQLite (legacy fallback)."""
    try:
        import sqlite3
        
        # Ensure database exists
        if not os.path.exists(DB_PATH):
            _initialize_sqlite_db()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Calculate aggregates
        portfolio_value = account_info.get('portfolio_value', 0)
        equity = account_info.get('equity', 0)
        buying_power = account_info.get('buying_power', 0)
        cash = account_info.get('cash', 0)
        num_positions = len(positions_data) if positions_data else 0
        
        # Calculate total unrealized P/L
        unrealized_pl = sum(pos.get('unrealized_pl', 0) for pos in positions_data) if positions_data else 0.0
        
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
        conn.close()
        
        logger.info(f"✓ Saved portfolio snapshot (SQLite): ${portfolio_value:,.2f}, {num_positions} positions")
        return True
        
    except Exception as e:
        logger.error(f"Error saving snapshot to SQLite: {e}")
        return False


def _initialize_sqlite_db():
    """Initialize SQLite database (legacy fallback)."""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
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
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp ON snapshots(timestamp)
    ''')
    
    conn.commit()
    conn.close()


# Legacy function names for backward compatibility
def initialize_database():
    """Legacy function - redirects to PostgreSQL or SQLite initialization."""
    if POSTGRES_AVAILABLE:
        if _connection_pool is None:
            initialize_postgres_pool()
        return initialize_postgres_schema()
    else:
        _initialize_sqlite_db()
        return True


# ==============================================================================
# MODULE INITIALIZATION
# ==============================================================================

# Auto-initialize PostgreSQL pool on module import if available
if POSTGRES_AVAILABLE:
    try:
        initialize_postgres_pool()
        initialize_postgres_schema()
    except Exception as e:
        logger.warning(f"Failed to auto-initialize PostgreSQL: {e}")

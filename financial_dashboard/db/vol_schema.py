"""
Volatility Lab Database Schema
================================

Phase 34: SQLite schema for 4 tables to persist IV surfaces, runs, signals, and backtests.

Tables:
- vol_surfaces: Core IV surface data
- vol_surface_runs: Computation run metadata
- vol_signals: Trading signals generated from surfaces
- vol_backtests: Backtest results
"""

CREATE_TABLES_SQL = """
-- vol_surfaces: Store computed IV grids
CREATE TABLE IF NOT EXISTS vol_surfaces (
    surface_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    grid_json TEXT NOT NULL,  -- JSON array of IV grid
    strikes_json TEXT NOT NULL,  -- JSON array of strikes
    tenors_json TEXT NOT NULL,  -- JSON array of tenors (days)
    atm_iv REAL,
    solver_method TEXT,
    converged INTEGER,  -- 0 or 1
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- vol_surface_runs: Track computation runs
CREATE TABLE IF NOT EXISTS vol_surface_runs (
    run_id TEXT PRIMARY KEY,
    surface_id TEXT,
    ticker TEXT NOT NULL,
    mode TEXT,  -- 'sync' or 'async'
    deterministic INTEGER,  -- 0 or 1
    solver_iterations INTEGER,
    solver_runtime_ms REAL,
    status TEXT,  -- 'completed', 'failed', 'pending'
    error_message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (surface_id) REFERENCES vol_surfaces(surface_id)
);

-- vol_signals: Trading signals from IV analysis
CREATE TABLE IF NOT EXISTS vol_signals (
    signal_id TEXT PRIMARY KEY,
    surface_id TEXT,
    ticker TEXT NOT NULL,
    strategy TEXT NOT NULL,  -- 'iv_rank', 'skew', 'straddle'
    strike REAL,
    tenor INTEGER,  -- days to expiry
    signal_type TEXT,  -- 'buy_call', 'sell_put', etc.
    confidence REAL,  -- 0.0 to 1.0
    risk_level TEXT,  -- 'low', 'medium', 'high'
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (surface_id) REFERENCES vol_surfaces(surface_id)
);

-- vol_backtests: Backtest results
CREATE TABLE IF NOT EXISTS vol_backtests (
    backtest_id TEXT PRIMARY KEY,
    signal_id TEXT,
    strategy TEXT NOT NULL,
    seed INTEGER,  -- Random seed for deterministic backtests
    total_return REAL,
    sharpe_ratio REAL,
    max_drawdown REAL,
    total_trades INTEGER,
    trades_json TEXT,  -- JSON array of trade details
    equity_curve_json TEXT,  -- JSON array of equity values
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (signal_id) REFERENCES vol_signals(signal_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_vol_surfaces_ticker ON vol_surfaces(ticker);
CREATE INDEX IF NOT EXISTS idx_vol_surfaces_timestamp ON vol_surfaces(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_vol_runs_ticker ON vol_surface_runs(ticker);
CREATE INDEX IF NOT EXISTS idx_vol_signals_ticker ON vol_signals(ticker);
CREATE INDEX IF NOT EXISTS idx_vol_signals_surface ON vol_signals(surface_id);
"""


def init_vol_db(db_path='vol_lab.db'):
    """
    Initialize Volatility Lab database with schema.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        Connection object
    """
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    conn.executescript(CREATE_TABLES_SQL)
    conn.commit()
    
    return conn


__all__ = ['CREATE_TABLES_SQL', 'init_vol_db']

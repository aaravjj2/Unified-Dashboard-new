-- Volatility Lab Database Schema
-- Agent-1B Implementation
-- Created: 2025-11-18
--
-- Tables:
--   - vol_surfaces: IV surface computation results
--   - vol_surface_runs: Solver execution metadata
--   - vol_signals: Trading signals from surface analysis
--   - vol_backtests: Strategy backtest results

-- ============================================================================
-- Table: vol_surfaces
-- Stores computed IV surfaces with strike/expiry grids
-- ============================================================================
CREATE TABLE IF NOT EXISTS vol_surfaces (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    as_of TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Grid data
    xs DOUBLE PRECISION[] NOT NULL,  -- Strike prices
    ys DOUBLE PRECISION[] NOT NULL,  -- Days to expiry
    grid JSONB NOT NULL,              -- 2D IV grid [[float]]
    
    -- Metadata
    meta JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    CONSTRAINT vol_surfaces_ticker_asof_key UNIQUE (ticker, as_of)
);

CREATE INDEX IF NOT EXISTS idx_vol_surfaces_ticker ON vol_surfaces(ticker);
CREATE INDEX IF NOT EXISTS idx_vol_surfaces_asof ON vol_surfaces(as_of DESC);

COMMENT ON TABLE vol_surfaces IS 'Computed IV surfaces with solver results';
COMMENT ON COLUMN vol_surfaces.xs IS 'Strike prices array';
COMMENT ON COLUMN vol_surfaces.ys IS 'Days to expiry array';
COMMENT ON COLUMN vol_surfaces.grid IS '2D IV grid as JSONB [[float]]';


-- ============================================================================
-- Table: vol_surface_runs
-- Tracks solver execution details for each surface computation
-- ============================================================================
CREATE TABLE IF NOT EXISTS vol_surface_runs (
    id SERIAL PRIMARY KEY,
    vol_surface_id INTEGER REFERENCES vol_surfaces(id) ON DELETE CASCADE,
    
    -- Solver info
    solver_name VARCHAR(50) NOT NULL,
    iterations INTEGER DEFAULT 0,
    converged BOOLEAN DEFAULT FALSE,
    fallback_used BOOLEAN DEFAULT FALSE,
    runtime_ms DOUBLE PRECISION DEFAULT 0.0,
    
    -- Additional metadata
    meta JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vol_surface_runs_surface_id ON vol_surface_runs(vol_surface_id);
CREATE INDEX IF NOT EXISTS idx_vol_surface_runs_created_at ON vol_surface_runs(created_at DESC);

COMMENT ON TABLE vol_surface_runs IS 'Solver execution metadata for each surface computation';
COMMENT ON COLUMN vol_surface_runs.solver_name IS 'newton_raphson or brent';
COMMENT ON COLUMN vol_surface_runs.fallback_used IS 'True if Brent fallback was used';


-- ============================================================================
-- Table: vol_signals
-- Trading signals generated from IV surface analysis
-- ============================================================================
CREATE TABLE IF NOT EXISTS vol_signals (
    id SERIAL PRIMARY KEY,
    vol_surface_id INTEGER REFERENCES vol_surfaces(id) ON DELETE SET NULL,
    
    -- Signal details
    ticker VARCHAR(10) NOT NULL,
    strategy VARCHAR(50) NOT NULL,
    confidence DOUBLE PRECISION CHECK (confidence >= 0 AND confidence <= 1),
    risk VARCHAR(20) DEFAULT 'medium',
    notes TEXT,
    
    -- Additional data
    meta JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vol_signals_ticker ON vol_signals(ticker);
CREATE INDEX IF NOT EXISTS idx_vol_signals_strategy ON vol_signals(strategy);
CREATE INDEX IF NOT EXISTS idx_vol_signals_created_at ON vol_signals(created_at DESC);

COMMENT ON TABLE vol_signals IS 'Trading signals from IV surface analysis';
COMMENT ON COLUMN vol_signals.confidence IS 'Signal confidence [0.0, 1.0]';
COMMENT ON COLUMN vol_signals.risk IS 'Risk level: low, medium, high';


-- ============================================================================
-- Table: vol_backtests
-- Strategy backtest results
-- ============================================================================
CREATE TABLE IF NOT EXISTS vol_backtests (
    id SERIAL PRIMARY KEY,
    
    -- Backtest details
    strategy VARCHAR(50) NOT NULL,
    params JSONB DEFAULT '{}',
    seed INTEGER,
    
    -- Summary metrics
    total_return DOUBLE PRECISION,
    sharpe_ratio DOUBLE PRECISION,
    max_drawdown DOUBLE PRECISION,
    total_trades INTEGER DEFAULT 0,
    win_rate DOUBLE PRECISION,
    
    -- Trade history
    trades JSONB DEFAULT '[]',
    
    -- Additional metadata
    meta JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vol_backtests_strategy ON vol_backtests(strategy);
CREATE INDEX IF NOT EXISTS idx_vol_backtests_created_at ON vol_backtests(created_at DESC);

COMMENT ON TABLE vol_backtests IS 'Strategy backtest results';
COMMENT ON COLUMN vol_backtests.trades IS 'Array of trade objects as JSONB';


-- ============================================================================
-- Sample Data (for development/testing)
-- ============================================================================

-- Insert sample surface
INSERT INTO vol_surfaces (ticker, as_of, xs, ys, grid, meta)
VALUES (
    'SPY',
    CURRENT_TIMESTAMP,
    ARRAY[450, 460, 470, 480, 490]::DOUBLE PRECISION[],
    ARRAY[30, 60, 90]::DOUBLE PRECISION[],
    '[[0.15, 0.16, 0.17, 0.18, 0.19], [0.16, 0.17, 0.18, 0.19, 0.20], [0.17, 0.18, 0.19, 0.20, 0.21]]'::JSONB,
    '{"solver_info": {"solver_name": "newton_raphson", "converged": true}}'::JSONB
)
ON CONFLICT (ticker, as_of) DO NOTHING;

-- Grant permissions (adjust user as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO dashboard_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO dashboard_user;

COMMENT ON SCHEMA public IS 'Volatility Lab schema - Agent-1B implementation';

-- ============================================================================
-- Alpaca Options Lab - TimescaleDB Schema
-- ============================================================================
-- Production-grade schema with:
-- - TimescaleDB hypertables for time-series data
-- - Automatic compression policies
-- - Optimized indexes for options queries
-- - Symbol normalization tables
-- 
-- Performance Targets:
-- - >50k tick writes/second
-- - <5ms P99 read latency
-- - >85% compression ratio
-- ============================================================================

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ============================================================================
-- SYMBOL NORMALIZATION
-- ============================================================================

-- Option contracts table (normalized symbols)
CREATE TABLE IF NOT EXISTS option_contracts (
    id SERIAL PRIMARY KEY,
    osi_symbol TEXT UNIQUE NOT NULL,
    root_symbol TEXT NOT NULL,
    underlying TEXT NOT NULL,
    expiration DATE NOT NULL,
    strike NUMERIC(12, 4) NOT NULL,
    option_type CHAR(1) NOT NULL CHECK (option_type IN ('C', 'P')),
    
    -- Metadata
    multiplier INT DEFAULT 100,
    exercise_style CHAR(1) DEFAULT 'A' CHECK (exercise_style IN ('A', 'E')), -- American/European
    settlement_type CHAR(1) DEFAULT 'S' CHECK (settlement_type IN ('S', 'C')), -- Stock/Cash
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_strike CHECK (strike > 0),
    CONSTRAINT valid_expiration CHECK (expiration >= '2020-01-01')
);

-- Index for fast symbol lookups
CREATE INDEX IF NOT EXISTS idx_contracts_underlying ON option_contracts(underlying);
CREATE INDEX IF NOT EXISTS idx_contracts_expiration ON option_contracts(expiration);
CREATE INDEX IF NOT EXISTS idx_contracts_underlying_exp ON option_contracts(underlying, expiration);
CREATE INDEX IF NOT EXISTS idx_contracts_osi ON option_contracts(osi_symbol);

-- Underlyings table
CREATE TABLE IF NOT EXISTS underlyings (
    symbol TEXT PRIMARY KEY,
    name TEXT,
    sector TEXT,
    industry TEXT,
    market_cap NUMERIC,
    has_options BOOLEAN DEFAULT TRUE,
    
    -- Dividend info
    dividend_yield NUMERIC(6, 4),
    ex_dividend_date DATE,
    dividend_amount NUMERIC(10, 4),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- MARKET DATA - TICKS
-- ============================================================================

-- Option ticks (high-frequency data)
CREATE TABLE IF NOT EXISTS option_ticks (
    time TIMESTAMPTZ NOT NULL,
    contract_id INT NOT NULL,
    
    -- Quote data
    bid NUMERIC(12, 4),
    ask NUMERIC(12, 4),
    bid_size INT,
    ask_size INT,
    
    -- Trade data
    last NUMERIC(12, 4),
    last_size INT,
    
    -- Greeks (calculated)
    iv NUMERIC(8, 6),
    delta NUMERIC(8, 6),
    gamma NUMERIC(12, 10),
    theta NUMERIC(8, 6),
    vega NUMERIC(8, 6),
    
    -- Market context
    underlying_price NUMERIC(12, 4),
    
    -- Metadata
    exchange TEXT,
    conditions TEXT[],
    
    CONSTRAINT fk_contract FOREIGN KEY (contract_id) 
        REFERENCES option_contracts(id) ON DELETE CASCADE
);

-- Convert to hypertable
SELECT create_hypertable('option_ticks', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_ticks_contract_time 
    ON option_ticks(contract_id, time DESC);

-- Enable compression
ALTER TABLE option_ticks SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'contract_id',
    timescaledb.compress_orderby = 'time DESC'
);

-- Auto-compress data older than 7 days
SELECT add_compression_policy('option_ticks',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- ============================================================================
-- MARKET DATA - OHLCV BARS
-- ============================================================================

-- Option bars (aggregated data)
CREATE TABLE IF NOT EXISTS option_bars (
    time TIMESTAMPTZ NOT NULL,
    contract_id INT NOT NULL,
    
    -- OHLCV
    open NUMERIC(12, 4),
    high NUMERIC(12, 4),
    low NUMERIC(12, 4),
    close NUMERIC(12, 4),
    volume BIGINT,
    
    -- Aggregated IV
    iv_open NUMERIC(8, 6),
    iv_high NUMERIC(8, 6),
    iv_low NUMERIC(8, 6),
    iv_close NUMERIC(8, 6),
    
    -- Open interest
    open_interest BIGINT,
    
    -- Trade count
    trade_count INT,
    
    -- Bar resolution
    resolution TEXT DEFAULT '1min', -- 1min, 5min, 15min, 1h, 1d
    
    CONSTRAINT fk_contract_bars FOREIGN KEY (contract_id) 
        REFERENCES option_contracts(id) ON DELETE CASCADE
);

-- Convert to hypertable
SELECT create_hypertable('option_bars', 'time',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_bars_contract_time 
    ON option_bars(contract_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_bars_resolution 
    ON option_bars(resolution, time DESC);

-- Enable compression
ALTER TABLE option_bars SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'contract_id,resolution',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('option_bars',
    INTERVAL '30 days',
    if_not_exists => TRUE
);

-- ============================================================================
-- UNDERLYING MARKET DATA
-- ============================================================================

-- Stock/ETF ticks
CREATE TABLE IF NOT EXISTS underlying_ticks (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    
    -- Quote
    bid NUMERIC(12, 4),
    ask NUMERIC(12, 4),
    bid_size INT,
    ask_size INT,
    
    -- Trade
    last NUMERIC(12, 4),
    last_size INT,
    
    -- Metadata
    exchange TEXT,
    conditions TEXT[]
);

SELECT create_hypertable('underlying_ticks', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_underlying_ticks_symbol_time 
    ON underlying_ticks(symbol, time DESC);

ALTER TABLE underlying_ticks SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('underlying_ticks',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Underlying bars
CREATE TABLE IF NOT EXISTS underlying_bars (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    
    -- OHLCV
    open NUMERIC(12, 4),
    high NUMERIC(12, 4),
    low NUMERIC(12, 4),
    close NUMERIC(12, 4),
    volume BIGINT,
    vwap NUMERIC(12, 4),
    
    -- Resolution
    resolution TEXT DEFAULT '1min',
    
    -- Trade count
    trade_count INT
);

SELECT create_hypertable('underlying_bars', 'time',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_underlying_bars_symbol_time 
    ON underlying_bars(symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_underlying_bars_resolution 
    ON underlying_bars(resolution, time DESC);

ALTER TABLE underlying_bars SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol,resolution',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('underlying_bars',
    INTERVAL '30 days',
    if_not_exists => TRUE
);

-- ============================================================================
-- VOLATILITY SURFACES
-- ============================================================================

-- Volatility surface snapshots
CREATE TABLE IF NOT EXISTS volatility_surfaces (
    time TIMESTAMPTZ NOT NULL,
    underlying TEXT NOT NULL,
    
    -- Surface parameters
    spot NUMERIC(12, 4) NOT NULL,
    forward_price NUMERIC(12, 4),
    risk_free_rate NUMERIC(8, 6),
    dividend_yield NUMERIC(8, 6),
    
    -- Surface data (JSONB for flexibility)
    surface_data JSONB NOT NULL, -- {expiry: {strike: iv}}
    
    -- Metadata
    model_type TEXT DEFAULT 'raw', -- raw, svi, sabr
    calibration_error NUMERIC(12, 8)
);

SELECT create_hypertable('volatility_surfaces', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_vol_surface_underlying 
    ON volatility_surfaces(underlying, time DESC);

ALTER TABLE volatility_surfaces SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'underlying',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('volatility_surfaces',
    INTERVAL '90 days',
    if_not_exists => TRUE
);

-- ============================================================================
-- POSITIONS AND TRADES
-- ============================================================================

-- Positions table
CREATE TABLE IF NOT EXISTS positions (
    id TEXT PRIMARY KEY,
    contract_id INT REFERENCES option_contracts(id),
    symbol TEXT NOT NULL,
    underlying TEXT NOT NULL,
    
    -- Position
    quantity INT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('long', 'short')),
    
    -- Cost basis
    avg_cost NUMERIC(12, 4) NOT NULL,
    total_cost NUMERIC(12, 4) NOT NULL,
    
    -- State
    state TEXT NOT NULL DEFAULT 'open',
    
    -- P&L
    realized_pnl NUMERIC(12, 4) DEFAULT 0,
    
    -- Timestamps
    opened_at TIMESTAMPTZ NOT NULL,
    closed_at TIMESTAMPTZ,
    
    -- Metadata
    strategy TEXT,
    tags TEXT[]
);

CREATE INDEX IF NOT EXISTS idx_positions_state ON positions(state);
CREATE INDEX IF NOT EXISTS idx_positions_underlying ON positions(underlying);
CREATE INDEX IF NOT EXISTS idx_positions_opened ON positions(opened_at DESC);

-- Trades table
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    position_id TEXT REFERENCES positions(id),
    contract_id INT REFERENCES option_contracts(id),
    symbol TEXT NOT NULL,
    
    -- Trade details
    side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    quantity INT NOT NULL,
    price NUMERIC(12, 4) NOT NULL,
    
    -- Cost
    commission NUMERIC(10, 4) DEFAULT 0,
    fees NUMERIC(10, 4) DEFAULT 0,
    
    -- Execution
    order_type TEXT DEFAULT 'market',
    fill_time TIMESTAMPTZ NOT NULL,
    
    -- Metadata
    broker TEXT DEFAULT 'alpaca',
    order_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_trades_position ON trades(position_id);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_fill_time ON trades(fill_time DESC);

-- ============================================================================
-- PORTFOLIO SNAPSHOTS
-- ============================================================================

-- Portfolio snapshots (for historical analysis)
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    time TIMESTAMPTZ NOT NULL,
    
    -- Values
    equity NUMERIC(14, 4) NOT NULL,
    cash NUMERIC(14, 4) NOT NULL,
    positions_value NUMERIC(14, 4) NOT NULL,
    
    -- Greeks (portfolio-level)
    total_delta NUMERIC(12, 6),
    total_gamma NUMERIC(12, 8),
    total_theta NUMERIC(12, 6),
    total_vega NUMERIC(12, 6),
    
    -- Dollar Greeks
    dollar_delta NUMERIC(14, 4),
    dollar_gamma NUMERIC(14, 4),
    dollar_theta NUMERIC(14, 4),
    dollar_vega NUMERIC(14, 4),
    
    -- Risk metrics
    margin_used NUMERIC(14, 4),
    buying_power NUMERIC(14, 4),
    
    -- Positions summary
    position_count INT,
    underlying_count INT,
    
    -- P&L
    daily_pnl NUMERIC(14, 4),
    unrealized_pnl NUMERIC(14, 4)
);

SELECT create_hypertable('portfolio_snapshots', 'time',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

ALTER TABLE portfolio_snapshots SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('portfolio_snapshots',
    INTERVAL '90 days',
    if_not_exists => TRUE
);

-- ============================================================================
-- EVENTS AND AUDIT LOG
-- ============================================================================

-- Events log
CREATE TABLE IF NOT EXISTS events_log (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type TEXT NOT NULL,
    severity TEXT DEFAULT 'info',
    
    -- Context
    symbol TEXT,
    position_id TEXT,
    
    -- Data
    data JSONB,
    
    -- Message
    message TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_time ON events_log(time DESC);
CREATE INDEX IF NOT EXISTS idx_events_type ON events_log(event_type, time DESC);
CREATE INDEX IF NOT EXISTS idx_events_symbol ON events_log(symbol, time DESC);

-- ============================================================================
-- CONTINUOUS AGGREGATES (Real-time Materialized Views)
-- ============================================================================

-- Hourly option bars from ticks
CREATE MATERIALIZED VIEW IF NOT EXISTS option_bars_hourly
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', time) AS bucket,
    contract_id,
    first(last, time) AS open,
    max(COALESCE(ask, last)) AS high,
    min(COALESCE(bid, last)) AS low,
    last(last, time) AS close,
    sum(last_size) AS volume,
    avg(iv) AS avg_iv,
    count(*) AS tick_count
FROM option_ticks
GROUP BY bucket, contract_id
WITH NO DATA;

-- Add refresh policy
SELECT add_continuous_aggregate_policy('option_bars_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Daily underlying bars
CREATE MATERIALIZED VIEW IF NOT EXISTS underlying_bars_daily
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', time) AS bucket,
    symbol,
    first(open, time) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, time) AS close,
    sum(volume) AS volume,
    sum(volume * vwap) / NULLIF(sum(volume), 0) AS vwap,
    sum(trade_count) AS trade_count
FROM underlying_bars
WHERE resolution = '1min'
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy('underlying_bars_daily',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to get contract ID by OSI symbol (with caching via INSERT)
CREATE OR REPLACE FUNCTION get_or_create_contract_id(
    p_osi_symbol TEXT,
    p_underlying TEXT DEFAULT NULL,
    p_expiration DATE DEFAULT NULL,
    p_strike NUMERIC DEFAULT NULL,
    p_option_type CHAR(1) DEFAULT NULL
) RETURNS INT AS $$
DECLARE
    v_contract_id INT;
BEGIN
    -- Try to find existing
    SELECT id INTO v_contract_id
    FROM option_contracts
    WHERE osi_symbol = p_osi_symbol;
    
    -- If not found and we have details, create it
    IF v_contract_id IS NULL AND p_underlying IS NOT NULL THEN
        INSERT INTO option_contracts (
            osi_symbol, root_symbol, underlying, expiration, strike, option_type
        ) VALUES (
            p_osi_symbol,
            split_part(p_osi_symbol, regexp_replace(p_osi_symbol, '^[A-Z]+', ''), 1),
            p_underlying,
            p_expiration,
            p_strike,
            p_option_type
        )
        ON CONFLICT (osi_symbol) DO UPDATE SET updated_at = NOW()
        RETURNING id INTO v_contract_id;
    END IF;
    
    RETURN v_contract_id;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate time to expiry in years
CREATE OR REPLACE FUNCTION time_to_expiry_years(p_expiration DATE) 
RETURNS NUMERIC AS $$
BEGIN
    RETURN GREATEST(0, (p_expiration - CURRENT_DATE)::NUMERIC / 365.25);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- DATA RETENTION POLICIES
-- ============================================================================

-- Drop tick data older than 90 days (can be adjusted)
SELECT add_retention_policy('option_ticks',
    INTERVAL '90 days',
    if_not_exists => TRUE
);

SELECT add_retention_policy('underlying_ticks',
    INTERVAL '90 days',
    if_not_exists => TRUE
);

-- Keep bars data for 2 years
SELECT add_retention_policy('option_bars',
    INTERVAL '730 days',
    if_not_exists => TRUE
);

SELECT add_retention_policy('underlying_bars',
    INTERVAL '730 days',
    if_not_exists => TRUE
);

-- ============================================================================
-- PERMISSIONS
-- ============================================================================

-- Create app role
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'alpaca_app') THEN
        CREATE ROLE alpaca_app WITH LOGIN PASSWORD 'changeme';
    END IF;
END
$$;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO alpaca_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO alpaca_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO alpaca_app;

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Alpaca Options Lab schema created successfully!';
    RAISE NOTICE 'Tables: option_contracts, option_ticks, option_bars, underlying_ticks, underlying_bars';
    RAISE NOTICE 'Views: option_bars_hourly, underlying_bars_daily';
    RAISE NOTICE 'Compression: Enabled with 7-day policy for ticks, 30-day for bars';
END
$$;

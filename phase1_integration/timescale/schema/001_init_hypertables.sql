-- TimescaleDB Schema for Alpaca Options Lab
-- Hypertables for time-series data with automatic partitioning

-- ============================================================================
-- Extensions
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- ============================================================================
-- OHLCV Data (Stock Prices)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ohlcv (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    open        DOUBLE PRECISION,
    high        DOUBLE PRECISION,
    low         DOUBLE PRECISION,
    close       DOUBLE PRECISION,
    volume      BIGINT,
    vwap        DOUBLE PRECISION,
    trades      INTEGER,
    source      TEXT DEFAULT 'alpaca'
);

-- Convert to hypertable (partition by day)
SELECT create_hypertable('ohlcv', 'time', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_time ON ohlcv (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol ON ohlcv (symbol);

-- ============================================================================
-- Option Chains
-- ============================================================================

CREATE TABLE IF NOT EXISTS option_chains (
    time            TIMESTAMPTZ NOT NULL,
    symbol          TEXT NOT NULL,         -- Option symbol
    underlying      TEXT NOT NULL,         -- Underlying symbol
    expiry          DATE NOT NULL,
    strike          DOUBLE PRECISION NOT NULL,
    option_type     TEXT NOT NULL,         -- call, put
    
    -- Prices
    bid             DOUBLE PRECISION,
    ask             DOUBLE PRECISION,
    last            DOUBLE PRECISION,
    mid             DOUBLE PRECISION,
    
    -- Volume & OI
    volume          INTEGER,
    open_interest   INTEGER,
    
    -- Greeks
    delta           DOUBLE PRECISION,
    gamma           DOUBLE PRECISION,
    theta           DOUBLE PRECISION,
    vega            DOUBLE PRECISION,
    rho             DOUBLE PRECISION,
    
    -- IV
    implied_volatility DOUBLE PRECISION,
    
    -- Metadata
    source          TEXT DEFAULT 'alpaca'
);

SELECT create_hypertable('option_chains', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_options_underlying_time ON option_chains (underlying, time DESC);
CREATE INDEX IF NOT EXISTS idx_options_expiry ON option_chains (expiry);
CREATE INDEX IF NOT EXISTS idx_options_symbol ON option_chains (symbol);

-- ============================================================================
-- IV Surface Data
-- ============================================================================

CREATE TABLE IF NOT EXISTS iv_surface (
    time            TIMESTAMPTZ NOT NULL,
    underlying      TEXT NOT NULL,
    expiry          DATE NOT NULL,
    dte             INTEGER NOT NULL,
    moneyness       DOUBLE PRECISION NOT NULL,  -- strike/spot
    strike          DOUBLE PRECISION NOT NULL,
    
    -- IV metrics
    iv              DOUBLE PRECISION,
    iv_bid          DOUBLE PRECISION,
    iv_ask          DOUBLE PRECISION,
    
    -- Surface derivatives
    skew            DOUBLE PRECISION,
    term_slope      DOUBLE PRECISION,
    
    source          TEXT DEFAULT 'calculated'
);

SELECT create_hypertable('iv_surface', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_iv_underlying_time ON iv_surface (underlying, time DESC);
CREATE INDEX IF NOT EXISTS idx_iv_dte ON iv_surface (dte);

-- ============================================================================
-- Signals (Trading Signals)
-- ============================================================================

CREATE TABLE IF NOT EXISTS signals (
    time            TIMESTAMPTZ NOT NULL,
    signal_id       TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    signal_type     TEXT NOT NULL,          -- buy, sell, hold
    strategy        TEXT,
    confidence      DOUBLE PRECISION,
    source          TEXT,                   -- lstm, xgb, ensemble
    
    -- Signal details
    direction       TEXT,                   -- bullish, bearish, neutral
    target_price    DOUBLE PRECISION,
    stop_loss       DOUBLE PRECISION,
    take_profit     DOUBLE PRECISION,
    
    -- Metadata (JSON)
    metadata        JSONB,
    
    PRIMARY KEY (time, signal_id)
);

SELECT create_hypertable('signals', 'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals (symbol);

-- ============================================================================
-- Orders (Order Lifecycle)
-- ============================================================================

CREATE TABLE IF NOT EXISTS orders (
    time            TIMESTAMPTZ NOT NULL,
    order_id        TEXT NOT NULL,
    client_order_id TEXT,
    symbol          TEXT NOT NULL,
    side            TEXT NOT NULL,          -- buy, sell
    order_type      TEXT NOT NULL,          -- market, limit
    quantity        INTEGER,
    limit_price     DOUBLE PRECISION,
    
    status          TEXT,                   -- pending, filled, cancelled
    filled_qty      INTEGER DEFAULT 0,
    avg_fill_price  DOUBLE PRECISION,
    
    strategy        TEXT,
    signal_id       TEXT,
    paper_mode      BOOLEAN DEFAULT TRUE,
    
    metadata        JSONB,
    
    PRIMARY KEY (time, order_id)
);

SELECT create_hypertable('orders', 'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders (symbol);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status);

-- ============================================================================
-- Trades (Executed Trades)
-- ============================================================================

CREATE TABLE IF NOT EXISTS trades (
    time            TIMESTAMPTZ NOT NULL,
    trade_id        TEXT NOT NULL,
    order_id        TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    side            TEXT NOT NULL,
    quantity        INTEGER,
    price           DOUBLE PRECISION,
    commission      DOUBLE PRECISION DEFAULT 0,
    
    -- PnL tracking
    pnl             DOUBLE PRECISION,
    pnl_pct         DOUBLE PRECISION,
    
    strategy        TEXT,
    metadata        JSONB,
    
    PRIMARY KEY (time, trade_id)
);

SELECT create_hypertable('trades', 'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades (symbol);
CREATE INDEX IF NOT EXISTS idx_trades_order ON trades (order_id);

-- ============================================================================
-- Positions (Current Positions)
-- ============================================================================

CREATE TABLE IF NOT EXISTS positions (
    time            TIMESTAMPTZ NOT NULL,
    symbol          TEXT NOT NULL,
    underlying      TEXT,
    
    -- Position details
    side            TEXT,                   -- long, short
    quantity        INTEGER,
    avg_cost        DOUBLE PRECISION,
    current_price   DOUBLE PRECISION,
    
    -- Greeks (for options)
    delta           DOUBLE PRECISION,
    gamma           DOUBLE PRECISION,
    theta           DOUBLE PRECISION,
    vega            DOUBLE PRECISION,
    
    -- PnL
    unrealized_pnl  DOUBLE PRECISION,
    realized_pnl    DOUBLE PRECISION,
    
    strategy        TEXT,
    metadata        JSONB,
    
    PRIMARY KEY (time, symbol)
);

SELECT create_hypertable('positions', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ============================================================================
-- Alerts (Alert History)
-- ============================================================================

CREATE TABLE IF NOT EXISTS alerts (
    time            TIMESTAMPTZ NOT NULL,
    alert_id        TEXT NOT NULL,
    severity        TEXT NOT NULL,          -- info, warning, critical
    alert_type      TEXT NOT NULL,          -- price, iv, skew, flow
    symbol          TEXT,
    message         TEXT,
    
    -- Alert state
    acknowledged    BOOLEAN DEFAULT FALSE,
    resolved        BOOLEAN DEFAULT FALSE,
    
    metadata        JSONB,
    
    PRIMARY KEY (time, alert_id)
);

SELECT create_hypertable('alerts', 'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_alerts_symbol ON alerts (symbol);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts (severity);

-- ============================================================================
-- Model Predictions (ML Model Outputs)
-- ============================================================================

CREATE TABLE IF NOT EXISTS model_predictions (
    time            TIMESTAMPTZ NOT NULL,
    prediction_id   TEXT NOT NULL,
    model_name      TEXT NOT NULL,
    model_version   TEXT,
    symbol          TEXT,
    
    -- Prediction
    prediction      TEXT,                   -- up, down, neutral
    confidence      DOUBLE PRECISION,
    probability     JSONB,                  -- {"up": 0.6, "down": 0.3, "neutral": 0.1}
    
    -- Performance tracking
    actual_outcome  TEXT,
    was_correct     BOOLEAN,
    
    -- Latency
    latency_ms      DOUBLE PRECISION,
    
    metadata        JSONB,
    
    PRIMARY KEY (time, prediction_id)
);

SELECT create_hypertable('model_predictions', 'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_predictions_model ON model_predictions (model_name);

-- ============================================================================
-- Feature Store
-- ============================================================================

CREATE TABLE IF NOT EXISTS features (
    time            TIMESTAMPTZ NOT NULL,
    symbol          TEXT NOT NULL,
    feature_set     TEXT NOT NULL,          -- price, technical, options, sentiment
    
    -- Features as JSON for flexibility
    features        JSONB NOT NULL,
    
    version         INTEGER DEFAULT 1,
    
    PRIMARY KEY (time, symbol, feature_set)
);

SELECT create_hypertable('features', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ============================================================================
-- Materialized Views for Common Queries
-- ============================================================================

-- Daily OHLCV aggregates
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_ohlcv AS
SELECT 
    time_bucket('1 day', time) AS day,
    symbol,
    first(open, time) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, time) AS close,
    sum(volume) AS volume
FROM ohlcv
GROUP BY day, symbol
ORDER BY day DESC;

-- IV Rank (rolling percentile)
CREATE MATERIALIZED VIEW IF NOT EXISTS iv_rank AS
SELECT 
    time_bucket('1 day', time) AS day,
    underlying,
    avg(iv) AS avg_iv,
    percent_rank() OVER (
        PARTITION BY underlying 
        ORDER BY avg(iv)
    ) AS iv_rank
FROM iv_surface
WHERE dte BETWEEN 20 AND 50
GROUP BY day, underlying
ORDER BY day DESC;

-- ============================================================================
-- Continuous Aggregates (Auto-refreshing)
-- ============================================================================

-- Hourly price aggregates
CREATE MATERIALIZED VIEW hourly_prices
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', time) AS bucket,
    symbol,
    first(open, time) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, time) AS close,
    sum(volume) AS volume
FROM ohlcv
GROUP BY bucket, symbol;

-- Enable auto-refresh
SELECT add_continuous_aggregate_policy('hourly_prices',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- ============================================================================
-- Retention Policies
-- ============================================================================

-- Keep OHLCV for 2 years
SELECT add_retention_policy('ohlcv', INTERVAL '2 years', if_not_exists => TRUE);

-- Keep option chains for 1 year
SELECT add_retention_policy('option_chains', INTERVAL '1 year', if_not_exists => TRUE);

-- Keep signals/orders/trades for 1 year
SELECT add_retention_policy('signals', INTERVAL '1 year', if_not_exists => TRUE);
SELECT add_retention_policy('orders', INTERVAL '1 year', if_not_exists => TRUE);
SELECT add_retention_policy('trades', INTERVAL '1 year', if_not_exists => TRUE);

-- Keep alerts for 90 days
SELECT add_retention_policy('alerts', INTERVAL '90 days', if_not_exists => TRUE);

-- Keep predictions for 6 months
SELECT add_retention_policy('model_predictions', INTERVAL '6 months', if_not_exists => TRUE);

-- ============================================================================
-- Compression Policies (for older data)
-- ============================================================================

-- Enable compression on OHLCV
ALTER TABLE ohlcv SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol'
);

SELECT add_compression_policy('ohlcv', INTERVAL '7 days', if_not_exists => TRUE);

-- Enable compression on option chains
ALTER TABLE option_chains SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'underlying'
);

SELECT add_compression_policy('option_chains', INTERVAL '7 days', if_not_exists => TRUE);

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Function to get latest price
CREATE OR REPLACE FUNCTION get_latest_price(p_symbol TEXT)
RETURNS TABLE(symbol TEXT, price DOUBLE PRECISION, time TIMESTAMPTZ) AS $$
    SELECT symbol, close, time
    FROM ohlcv
    WHERE symbol = p_symbol
    ORDER BY time DESC
    LIMIT 1;
$$ LANGUAGE SQL;

-- Function to get IV percentile
CREATE OR REPLACE FUNCTION get_iv_percentile(
    p_underlying TEXT,
    p_dte INTEGER DEFAULT 30
)
RETURNS DOUBLE PRECISION AS $$
DECLARE
    current_iv DOUBLE PRECISION;
    percentile DOUBLE PRECISION;
BEGIN
    -- Get current IV
    SELECT iv INTO current_iv
    FROM iv_surface
    WHERE underlying = p_underlying AND dte = p_dte
    ORDER BY time DESC
    LIMIT 1;
    
    -- Calculate percentile over last year
    SELECT percent_rank() INTO percentile
    FROM (
        SELECT avg(iv) as avg_iv
        FROM iv_surface
        WHERE underlying = p_underlying 
          AND dte = p_dte
          AND time > NOW() - INTERVAL '1 year'
        GROUP BY time_bucket('1 day', time)
    ) daily_iv
    WHERE avg_iv <= current_iv;
    
    RETURN percentile;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Grants (for application user)
-- ============================================================================

-- Create application role if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user WITH LOGIN PASSWORD 'app_password';
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- ============================================================================
-- Schema Version
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    description TEXT
);

INSERT INTO schema_version (version, description)
VALUES (1, 'Initial schema with hypertables')
ON CONFLICT (version) DO NOTHING;

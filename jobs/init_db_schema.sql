-- Phase 14: Weekly Picks Database Schema
-- Production-ready PostgreSQL schema for market data and weekly picks

-- ============================================================================
-- TABLE 1: market_data_ohlcv (Historical OHLC + Volume)
-- ============================================================================
CREATE TABLE IF NOT EXISTS market_data_ohlcv (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open DECIMAL(12, 4) NOT NULL,
    high DECIMAL(12, 4) NOT NULL,
    low DECIMAL(12, 4) NOT NULL,
    close DECIMAL(12, 4) NOT NULL,
    volume BIGINT NOT NULL,
    source VARCHAR(50) DEFAULT 'alpaca',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_market_data_ticker ON market_data_ohlcv(ticker);
CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data_ohlcv(timestamp);
CREATE INDEX IF NOT EXISTS idx_market_data_ticker_timestamp ON market_data_ohlcv(ticker, timestamp);

-- ============================================================================
-- TABLE 2: market_data_options (Options Chains)
-- ============================================================================
CREATE TABLE IF NOT EXISTS market_data_options (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    expiration_date DATE NOT NULL,
    strike_price DECIMAL(12, 4) NOT NULL,
    option_type VARCHAR(4) NOT NULL CHECK (option_type IN ('call', 'put')),
    bid DECIMAL(12, 4),
    ask DECIMAL(12, 4),
    last_price DECIMAL(12, 4),
    volume BIGINT,
    open_interest BIGINT,
    implied_volatility DECIMAL(8, 6),
    timestamp TIMESTAMP NOT NULL,
    source VARCHAR(50) DEFAULT 'alpaca',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, expiration_date, strike_price, option_type, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_options_ticker ON market_data_options(ticker);
CREATE INDEX IF NOT EXISTS idx_options_expiration ON market_data_options(expiration_date);

-- ============================================================================
-- TABLE 3: weekly_picks_production (Generated Weekly Picks)
-- ============================================================================
CREATE TABLE IF NOT EXISTS weekly_picks_production (
    id SERIAL PRIMARY KEY,
    week_start_date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    rank INTEGER NOT NULL CHECK (rank BETWEEN 1 AND 5),
    rationale TEXT NOT NULL,
    momentum_score DECIMAL(8, 4),
    sentiment_score DECIMAL(8, 4),
    fundamental_score DECIMAL(8, 4),
    combined_score DECIMAL(8, 4) NOT NULL,
    chart_array JSONB,  -- Array of OHLCV data for mini-chart
    metadata JSONB,     -- Additional metadata (backtest results, etc.)
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    generator_version VARCHAR(20),
    UNIQUE(week_start_date, ticker)
);

CREATE INDEX IF NOT EXISTS idx_weekly_picks_date ON weekly_picks_production(week_start_date);
CREATE INDEX IF NOT EXISTS idx_weekly_picks_ticker ON weekly_picks_production(ticker);
CREATE INDEX IF NOT EXISTS idx_weekly_picks_rank ON weekly_picks_production(week_start_date, rank);

-- ============================================================================
-- TABLE 4: generator_telemetry (Execution Logs)
-- ============================================================================
CREATE TABLE IF NOT EXISTS generator_telemetry (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(50) UNIQUE NOT NULL,
    execution_start TIMESTAMP NOT NULL,
    execution_end TIMESTAMP,
    status VARCHAR(20) CHECK (status IN ('running', 'success', 'failed', 'partial')),
    stocks_processed INTEGER,
    picks_generated INTEGER,
    errors_count INTEGER DEFAULT 0,
    error_log TEXT,
    performance_metrics JSONB,  -- Execution time breakdown
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_telemetry_run_id ON generator_telemetry(run_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_status ON generator_telemetry(status);
CREATE INDEX IF NOT EXISTS idx_telemetry_start ON generator_telemetry(execution_start);

-- ============================================================================
-- TABLE 5: sentiment_scores (External Sentiment Data)
-- ============================================================================
CREATE TABLE IF NOT EXISTS sentiment_scores (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    sentiment_score DECIMAL(8, 4) NOT NULL CHECK (sentiment_score BETWEEN -1 AND 1),
    source VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, timestamp, source)
);

CREATE INDEX IF NOT EXISTS idx_sentiment_ticker ON sentiment_scores(ticker);
CREATE INDEX IF NOT EXISTS idx_sentiment_timestamp ON sentiment_scores(timestamp);

-- ============================================================================
-- TABLE 6: fundamental_metrics (Fundamental Analysis Data)
-- ============================================================================
CREATE TABLE IF NOT EXISTS fundamental_metrics (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    pe_ratio DECIMAL(10, 4),
    peg_ratio DECIMAL(10, 4),
    dividend_yield DECIMAL(8, 4),
    roe DECIMAL(8, 4),
    debt_to_equity DECIMAL(10, 4),
    market_cap BIGINT,
    revenue_growth DECIMAL(8, 4),
    eps_growth DECIMAL(8, 4),
    metadata JSONB,
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_fundamental_ticker ON fundamental_metrics(ticker);
CREATE INDEX IF NOT EXISTS idx_fundamental_timestamp ON fundamental_metrics(timestamp);

-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- View: Latest Weekly Picks
CREATE OR REPLACE VIEW latest_weekly_picks AS
SELECT 
    wp.*,
    md.close AS current_price,
    md.volume AS current_volume
FROM weekly_picks_production wp
LEFT JOIN LATERAL (
    SELECT close, volume
    FROM market_data_ohlcv
    WHERE ticker = wp.ticker
    ORDER BY timestamp DESC
    LIMIT 1
) md ON true
WHERE wp.week_start_date = (
    SELECT MAX(week_start_date) FROM weekly_picks_production
)
ORDER BY wp.rank;

-- View: Generator Performance Stats
CREATE OR REPLACE VIEW generator_performance_stats AS
SELECT 
    DATE(execution_start) AS run_date,
    COUNT(*) AS total_runs,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS successful_runs,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_runs,
    AVG(EXTRACT(EPOCH FROM (execution_end - execution_start))) AS avg_duration_seconds,
    AVG(stocks_processed) AS avg_stocks_processed,
    AVG(picks_generated) AS avg_picks_generated
FROM generator_telemetry
WHERE execution_end IS NOT NULL
GROUP BY DATE(execution_start)
ORDER BY run_date DESC;

-- ============================================================================
-- GRANTS (Adjust based on actual user permissions)
-- ============================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO dashboard_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO dashboard_user;

COMMENT ON TABLE market_data_ohlcv IS 'Historical OHLCV data from Alpaca API';
COMMENT ON TABLE market_data_options IS 'Options chain data from Alpaca API';
COMMENT ON TABLE weekly_picks_production IS 'Generated top 5 weekly stock picks';
COMMENT ON TABLE generator_telemetry IS 'Execution logs for weekly picks generator';
COMMENT ON TABLE sentiment_scores IS 'External sentiment analysis scores';
COMMENT ON TABLE fundamental_metrics IS 'Fundamental analysis metrics';

-- PHASE PRE-24 DATABASE SCHEMA
-- Created: 2025-10-31
-- Purpose: Add missing tables for Options Lab, Strategy Lab, Picks, and Observability

-- ============================================================================
-- 1. OPTIONS_FORECASTS — Store forecast results from Options Lab
-- ============================================================================
CREATE TABLE IF NOT EXISTS options_forecasts (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(50) UNIQUE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    strike DECIMAL(10,2) NOT NULL,
    expiry DATE NOT NULL,
    option_type VARCHAR(4) NOT NULL CHECK (option_type IN ('call', 'put')),
    forecast_price DECIMAL(10,4),
    current_price DECIMAL(10,4),
    confidence DECIMAL(5,4),
    outlook VARCHAR(20),
    result_json JSONB,
    mock BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_options_forecasts_symbol ON options_forecasts(symbol);
CREATE INDEX IF NOT EXISTS idx_options_forecasts_created ON options_forecasts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_options_forecasts_run_id ON options_forecasts(run_id);

-- ============================================================================
-- 2. BACKTEST_RESULTS — Store Strategy Lab backtest execution results
-- ============================================================================
CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(50) UNIQUE NOT NULL,
    tickers TEXT[] NOT NULL,
    config_json JSONB,
    result_json JSONB,
    equity_curve JSONB,
    benchmark_data JSONB,
    risk_metrics JSONB,
    factor_analysis JSONB,
    net_return_pct DECIMAL(10,4),
    sharpe_ratio DECIMAL(10,4),
    max_drawdown_pct DECIMAL(10,4),
    win_rate DECIMAL(5,4),
    completed_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backtest_results_run_id ON backtest_results(run_id);
CREATE INDEX IF NOT EXISTS idx_backtest_results_completed ON backtest_results(completed_at DESC);

-- ============================================================================
-- 3. PRICE_CACHE — Cache for Weekly/Monthly Picks price refresh
-- ============================================================================
CREATE TABLE IF NOT EXISTS price_cache (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open_price DECIMAL(10,4),
    high_price DECIMAL(10,4),
    low_price DECIMAL(10,4),
    close_price DECIMAL(10,4),
    volume BIGINT,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(symbol, date)
);

CREATE INDEX IF NOT EXISTS idx_price_cache_symbol ON price_cache(symbol);
CREATE INDEX IF NOT EXISTS idx_price_cache_updated ON price_cache(updated_at DESC);

-- ============================================================================
-- 4. AUDIT_LOG — Track system events for Command Center
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    user_id VARCHAR(50),
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(100),
    metadata JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_event_type ON audit_log(event_type);

-- ============================================================================
-- 5. JOBS_QUEUE — Track background jobs for Command Center
-- ============================================================================
CREATE TABLE IF NOT EXISTS jobs_queue (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(50) UNIQUE NOT NULL,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    priority INTEGER DEFAULT 0,
    params JSONB,
    result JSONB,
    error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_jobs_queue_status ON jobs_queue(status);
CREATE INDEX IF NOT EXISTS idx_jobs_queue_created ON jobs_queue(created_at DESC);

-- ============================================================================
-- 6. CHAT_CONVERSATIONS — Store chatbot conversations for AI Assistant
-- ============================================================================
CREATE TABLE IF NOT EXISTS chat_conversations (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    user_message TEXT NOT NULL,
    assistant_response TEXT,
    model VARCHAR(50) DEFAULT 'gpt4all-falcon',
    is_mock BOOLEAN DEFAULT false,
    tokens_used INTEGER,
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_created ON chat_conversations(created_at DESC);

-- ============================================================================
-- Insert sample data for testing
-- ============================================================================

-- Sample audit log entries
INSERT INTO audit_log (event_type, action, resource, metadata) VALUES
('system', 'dashboard_start', 'app', '{"version": "1.0.0"}'::jsonb),
('backtest', 'execution_start', 'strategy_lab', '{"tickers": ["AAPL", "MSFT"]}'::jsonb),
('forecast', 'generation_complete', 'options_lab', '{"symbol": "TSLA", "strike": 250}'::jsonb)
ON CONFLICT DO NOTHING;

-- Sample jobs queue entries
INSERT INTO jobs_queue (job_id, job_type, status, priority) VALUES
('job_001', 'price_refresh', 'completed', 1),
('job_002', 'backtest_execution', 'pending', 2),
('job_003', 'model_training', 'running', 3)
ON CONFLICT (job_id) DO NOTHING;

-- Sample price cache entries
INSERT INTO price_cache (symbol, date, close_price, updated_at) VALUES
('AAPL', CURRENT_DATE, 175.50, NOW()),
('MSFT', CURRENT_DATE, 375.25, NOW()),
('TSLA', CURRENT_DATE, 242.75, NOW())
ON CONFLICT (symbol, date) DO UPDATE SET updated_at = NOW();

COMMIT;

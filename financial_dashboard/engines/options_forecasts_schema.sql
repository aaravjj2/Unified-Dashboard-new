-- Options Forecasts Table Schema
-- Phase 20B: Options Lab Rebuild

CREATE TABLE IF NOT EXISTS options_forecasts (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expiration_days INTEGER NOT NULL,
    spot_price DECIMAL(12, 4),
    data_source VARCHAR(50),
    greeks_summary JSONB,
    oi_analysis JSONB,
    strategies JSONB,
    metrics JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, timestamp)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_options_forecasts_ticker ON options_forecasts(ticker);
CREATE INDEX IF NOT EXISTS idx_options_forecasts_timestamp ON options_forecasts(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_options_forecasts_ticker_timestamp ON options_forecasts(ticker, timestamp DESC);

-- Add comment
COMMENT ON TABLE options_forecasts IS 'Stores Options Lab forecast results with Greeks, OI analysis, and strategy recommendations';

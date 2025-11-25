-- Market Forecast Persistence - AGENT-1B Phase 4
-- PostgreSQL schema for forecast storage and retrieval

-- Forecast runs table
CREATE TABLE IF NOT EXISTS market_forecasts (
    forecast_id UUID PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    horizon INTEGER NOT NULL,
    confidence NUMERIC(3, 2) NOT NULL,
    model VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'completed',
    forecast_data JSONB NOT NULL,  -- Array of {date, yhat, yhat_lower, yhat_upper}
    metrics JSONB,                 -- {rmse, mae, mape}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast retrieval
CREATE INDEX IF NOT EXISTS idx_market_forecasts_ticker 
    ON market_forecasts(ticker);

CREATE INDEX IF NOT EXISTS idx_market_forecasts_created_at 
    ON market_forecasts(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_market_forecasts_ticker_created 
    ON market_forecasts(ticker, created_at DESC);

-- Explainability data table
CREATE TABLE IF NOT EXISTS forecast_explanations (
    forecast_id UUID PRIMARY KEY REFERENCES market_forecasts(forecast_id) ON DELETE CASCADE,
    shap_values JSONB NOT NULL,    -- Array of {feature, importance}
    base_value NUMERIC,
    features JSONB,                -- Feature values used in forecast
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Forecast performance tracking (for model monitoring)
CREATE TABLE IF NOT EXISTS forecast_performance (
    id SERIAL PRIMARY KEY,
    forecast_id UUID REFERENCES market_forecasts(forecast_id) ON DELETE CASCADE,
    ticker VARCHAR(10) NOT NULL,
    forecast_date DATE NOT NULL,
    predicted_value NUMERIC,
    actual_value NUMERIC,
    absolute_error NUMERIC,
    percentage_error NUMERIC,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_forecast_performance_ticker 
    ON forecast_performance(ticker);

CREATE INDEX IF NOT EXISTS idx_forecast_performance_date 
    ON forecast_performance(forecast_date DESC);

-- Comments
COMMENT ON TABLE market_forecasts IS 'Stores market forecast runs with predictions and metadata';
COMMENT ON TABLE forecast_explanations IS 'Stores SHAP explainability data for each forecast';
COMMENT ON TABLE forecast_performance IS 'Tracks forecast accuracy over time for model monitoring';

COMMENT ON COLUMN market_forecasts.forecast_data IS 'JSONB array of forecast points with confidence intervals';
COMMENT ON COLUMN market_forecasts.metrics IS 'JSONB object containing RMSE, MAE, MAPE';
COMMENT ON COLUMN forecast_explanations.shap_values IS 'JSONB array of feature importance scores';

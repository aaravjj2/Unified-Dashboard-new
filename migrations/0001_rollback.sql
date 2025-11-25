-- Rollback for 0001_create_market_forecasts.sql

DROP TABLE IF EXISTS forecast_performance;
DROP TABLE IF EXISTS forecast_explanations;
DROP TABLE IF EXISTS market_forecasts;

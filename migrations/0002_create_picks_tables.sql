-- Migration: Create Picks Tables
-- Created: 2025-11-21
-- Purpose: Weekly and Monthly Picks persistence with audit trail

-- Weekly Picks Table
CREATE TABLE IF NOT EXISTS weekly_picks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker VARCHAR(10) NOT NULL,
    company VARCHAR(255),
    rank INTEGER,
    score REAL,
    sector VARCHAR(100),
    market_cap VARCHAR(50),
    recommendation VARCHAR(20),
    target_price REAL,
    current_price REAL,
    price_source VARCHAR(50),
    price_fetched_at TIMESTAMP,
    pick_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, pick_date)
);

-- Monthly Picks Table  
CREATE TABLE IF NOT EXISTS monthly_picks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker VARCHAR(10) NOT NULL,
    company VARCHAR(255),
    rank INTEGER,
    score REAL,
    sector VARCHAR(100),
    market_cap VARCHAR(50),
    recommendation VARCHAR(20),
    target_price REAL,
    current_price REAL,
    price_source VARCHAR(50),
    price_fetched_at TIMESTAMP,
    pick_month VARCHAR(7) NOT NULL,  -- Format: YYYY-MM
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, pick_month)
);

-- Picks Audit Log
CREATE TABLE IF NOT EXISTS picks_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pick_type VARCHAR(10) NOT NULL,  -- 'weekly' or 'monthly'
    action VARCHAR(50) NOT NULL,     -- 'load', 'enrich', 'reload', 'delete'
    source VARCHAR(100),              -- 'csv', 'db', 'fixture', 'api'
    record_count INTEGER,
    uploader VARCHAR(100),
    details TEXT,                    -- JSON details
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_weekly_picks_date ON weekly_picks(pick_date DESC);
CREATE INDEX IF NOT EXISTS idx_monthly_picks_month ON monthly_picks(pick_month DESC);
CREATE INDEX IF NOT EXISTS idx_weekly_picks_ticker ON weekly_picks(ticker);
CREATE INDEX IF NOT EXISTS idx_monthly_picks_ticker ON monthly_picks(ticker);
CREATE INDEX IF NOT EXISTS idx_picks_audit_type_action ON picks_audit(pick_type, action);
CREATE INDEX IF NOT EXISTS idx_picks_audit_created ON picks_audit(created_at DESC);

-- Trigger to update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_weekly_picks_timestamp 
AFTER UPDATE ON weekly_picks
BEGIN
    UPDATE weekly_picks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_monthly_picks_timestamp 
AFTER UPDATE ON monthly_picks
BEGIN
    UPDATE monthly_picks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

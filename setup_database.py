#!/usr/bin/env python3
"""
Database Setup Script
Creates all required tables for the financial dashboard
"""
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging

# Load environment variables
sys.path.insert(0, 'financial_dashboard')
from dotenv import load_dotenv
load_dotenv('financial_dashboard/keys.env')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_database_schema():
    """Create all required database tables"""
    
    # Database connection
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        database=os.getenv('POSTGRES_DB', 'financial_dashboard'),
        user=os.getenv('POSTGRES_USER', 'dashboard_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'newpassword')
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    logger.info("🔧 Creating database schema...")
    
    # Weekly picks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_picks_production (
            id SERIAL PRIMARY KEY,
            week_start_date DATE NOT NULL,
            ticker VARCHAR(20) NOT NULL,
            rank INTEGER NOT NULL,
            rationale TEXT,
            momentum_score NUMERIC(5,2),
            sentiment_score NUMERIC(5,2),
            fundamental_score NUMERIC(5,2),
            combined_score NUMERIC(5,2),
            chart_array JSONB,
            metadata JSONB,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("✅ Created weekly_picks_production table")
    
    # Monthly picks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_picks (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(20) NOT NULL,
            company_name VARCHAR(255),
            current_price NUMERIC(10,2),
            target_price NUMERIC(10,2),
            recommendation VARCHAR(20),
            confidence_score NUMERIC(5,2),
            analysis_date DATE DEFAULT CURRENT_DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("✅ Created monthly_picks table")
    
    # Price cache table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_cache (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(20) NOT NULL,
            price NUMERIC(10,2),
            change_pct NUMERIC(8,4),
            volume BIGINT,
            market_cap VARCHAR(50),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker)
        );
    """)
    logger.info("✅ Created price_cache table")
    
    # Portfolio positions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_positions (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(20) NOT NULL,
            shares NUMERIC(15,6),
            avg_cost NUMERIC(10,2),
            current_price NUMERIC(10,2),
            market_value NUMERIC(15,2),
            unrealized_pl NUMERIC(15,2),
            unrealized_pl_pct NUMERIC(8,4),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("✅ Created portfolio_positions table")
    
    # Backtest runs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS backtest_runs (
            id SERIAL PRIMARY KEY,
            run_id VARCHAR(50) UNIQUE NOT NULL,
            strategy_name VARCHAR(100),
            parameters JSONB,
            start_date DATE,
            end_date DATE,
            status VARCHAR(20) DEFAULT 'running',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        );
    """)
    logger.info("✅ Created backtest_runs table")
    
    # Backtest results table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS backtest_results (
            id SERIAL PRIMARY KEY,
            run_id VARCHAR(50) REFERENCES backtest_runs(run_id),
            ticker VARCHAR(20),
            total_return NUMERIC(10,4),
            sharpe_ratio NUMERIC(8,4),
            max_drawdown NUMERIC(8,4),
            win_rate NUMERIC(5,2),
            trades_count INTEGER,
            results_data JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("✅ Created backtest_results table")
    
    # ML prediction runs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ml_prediction_runs (
            id SERIAL PRIMARY KEY,
            run_id VARCHAR(50) UNIQUE NOT NULL,
            model_type VARCHAR(50),
            input_data JSONB,
            predictions JSONB,
            confidence NUMERIC(5,4),
            status VARCHAR(20) DEFAULT 'completed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("✅ Created ml_prediction_runs table")
    
    # Options forecasts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS options_forecasts (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(20) NOT NULL,
            strike_price NUMERIC(10,2),
            expiry_date DATE,
            option_type VARCHAR(10),
            forecast_data JSONB,
            iv_forecast NUMERIC(8,4),
            price_forecast NUMERIC(10,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("✅ Created options_forecasts table")
    
    # TradingView signals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tradingview_signals (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(20) NOT NULL,
            signal VARCHAR(20) NOT NULL,
            price NUMERIC(10,2),
            strategy VARCHAR(50),
            confidence NUMERIC(5,4),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("✅ Created tradingview_signals table")
    
    # Chat conversations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_conversations (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(100),
            user_message TEXT,
            bot_response TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("✅ Created chat_conversations table")
    
    # Audit log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            action VARCHAR(100) NOT NULL,
            details JSONB,
            user_id VARCHAR(50),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("✅ Created audit_log table")
    
    # Jobs queue table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs_queue (
            id SERIAL PRIMARY KEY,
            job_type VARCHAR(50) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            parameters JSONB,
            result JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP
        );
    """)
    logger.info("✅ Created jobs_queue table")
    
    # ML models table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ml_models (
            id SERIAL PRIMARY KEY,
            model_name VARCHAR(100) NOT NULL,
            model_type VARCHAR(50),
            version VARCHAR(20),
            parameters JSONB,
            performance_metrics JSONB,
            is_active BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("✅ Created ml_models table")
    
    cursor.close()
    conn.close()
    
    logger.info("🎉 Database schema created successfully!")

def populate_sample_data():
    """Populate tables with sample financial data"""
    
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        database=os.getenv('POSTGRES_DB', 'financial_dashboard'),
        user=os.getenv('POSTGRES_USER', 'dashboard_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'newpassword')
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    logger.info("📊 Populating sample data...")
    
    # Sample weekly picks
    cursor.execute("""
        INSERT INTO weekly_picks_production (week_start_date, ticker, rank, rationale, momentum_score, sentiment_score, fundamental_score, combined_score, chart_array, metadata)
        VALUES 
        ('2025-11-01', 'AAPL', 1, 'Strong earnings momentum and AI integration', 85.5, 78.2, 92.1, 85.3, '{"chart": "bullish"}', '{"sector": "technology"}'),
        ('2025-11-01', 'NVDA', 2, 'AI chip demand continues to surge', 92.8, 88.5, 89.2, 90.2, '{"chart": "very_bullish"}', '{"sector": "semiconductors"}'),
        ('2025-11-01', 'MSFT', 3, 'Cloud growth and productivity suite expansion', 78.9, 82.1, 85.7, 82.2, '{"chart": "bullish"}', '{"sector": "technology"}'),
        ('2025-11-01', 'GOOGL', 4, 'Search dominance and AI advancements', 76.3, 79.8, 81.5, 79.2, '{"chart": "neutral_bullish"}', '{"sector": "technology"}'),
        ('2025-11-01', 'TSLA', 5, 'EV market leadership and energy storage', 82.1, 75.6, 78.9, 78.9, '{"chart": "bullish"}', '{"sector": "automotive"}')
        ON CONFLICT DO NOTHING;
    """)
    
    # Sample monthly picks
    cursor.execute("""
        INSERT INTO monthly_picks (ticker, company_name, current_price, target_price, recommendation, confidence_score)
        VALUES 
        ('AAPL', 'Apple Inc.', 175.43, 195.00, 'BUY', 0.87),
        ('NVDA', 'NVIDIA Corporation', 875.28, 950.00, 'STRONG_BUY', 0.92),
        ('MSFT', 'Microsoft Corporation', 378.85, 410.00, 'BUY', 0.84),
        ('AMZN', 'Amazon.com Inc.', 142.56, 165.00, 'BUY', 0.79),
        ('META', 'Meta Platforms Inc.', 331.05, 375.00, 'BUY', 0.81)
        ON CONFLICT DO NOTHING;
    """)
    
    # Sample price cache
    cursor.execute("""
        INSERT INTO price_cache (ticker, price, change_pct, volume, market_cap)
        VALUES 
        ('AAPL', 175.43, 1.24, 45234567, '2.7T'),
        ('NVDA', 875.28, -1.01, 12345678, '2.1T'),
        ('MSFT', 378.85, 1.52, 23456789, '2.8T'),
        ('GOOGL', 142.56, -0.53, 1234567, '1.8T'),
        ('TSLA', 248.42, 5.23, 34567890, '789B'),
        ('META', 331.05, 1.40, 18765432, '834B'),
        ('AMZN', 142.56, 0.71, 3456789, '1.5T'),
        ('SPY', 432.18, 0.85, 87654321, 'ETF'),
        ('QQQ', 378.92, 1.12, 45678901, 'ETF'),
        ('IWM', 198.76, -0.34, 23456789, 'ETF')
        ON CONFLICT (ticker) DO UPDATE SET
        price = EXCLUDED.price,
        change_pct = EXCLUDED.change_pct,
        volume = EXCLUDED.volume,
        market_cap = EXCLUDED.market_cap,
        updated_at = CURRENT_TIMESTAMP;
    """)
    
    # Sample portfolio positions
    cursor.execute("""
        INSERT INTO portfolio_positions (ticker, shares, avg_cost, current_price, market_value, unrealized_pl, unrealized_pl_pct)
        VALUES 
        ('AAPL', 100, 165.50, 175.43, 17543.00, 993.00, 6.00),
        ('NVDA', 25, 820.00, 875.28, 21882.00, 1382.00, 6.74),
        ('MSFT', 50, 350.00, 378.85, 18942.50, 1442.50, 8.24),
        ('GOOGL', 75, 135.00, 142.56, 10692.00, 567.00, 5.60),
        ('TSLA', 40, 230.00, 248.42, 9936.80, 736.80, 8.01)
        ON CONFLICT DO NOTHING;
    """)
    
    cursor.close()
    conn.close()
    
    logger.info("✅ Sample data populated successfully!")

if __name__ == "__main__":
    try:
        create_database_schema()
        populate_sample_data()
        print("\n🎉 DATABASE SETUP COMPLETE!")
        print("✅ All tables created")
        print("✅ Sample data populated")
        print("✅ Ready for dashboard connection")
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        sys.exit(1)
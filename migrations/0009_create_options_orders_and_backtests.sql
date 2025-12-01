-- Phase 31 Agent 1A - STEP 4
-- Create tables for options orders and backtests persistence

-- Options Orders Table (for manual trades & paper orders)
CREATE TABLE IF NOT EXISTS options_orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(255) UNIQUE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    option_type VARCHAR(10) CHECK (option_type IN ('call', 'put')),
    strike DECIMAL(10, 2),
    expiration DATE,
    action VARCHAR(10) CHECK (action IN ('buy', 'sell', 'buy_to_open', 'sell_to_open', 'buy_to_close', 'sell_to_close')),
    quantity INTEGER NOT NULL,
    price DECIMAL(10, 4),
    paper BOOLEAN DEFAULT TRUE NOT NULL,  -- Default to paper trading
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'filled', 'rejected', 'cancelled')),
    created_at TIMESTAMP DEFAULT NOW(),
    filled_at TIMESTAMP,
    user_id VARCHAR(100),
    notes TEXT,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_options_orders_ticker ON options_orders(ticker);
CREATE INDEX IF NOT EXISTS idx_options_orders_paper ON options_orders(paper);
CREATE INDEX IF NOT EXISTS idx_options_orders_created_at ON options_orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_options_orders_user_id ON options_orders(user_id);

-- Options Backtests Table
CREATE TABLE IF NOT EXISTS options_backtests (
    id SERIAL PRIMARY KEY,
    backtest_id VARCHAR(255) UNIQUE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    strategy VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital DECIMAL(15, 2) NOT NULL,
    final_capital DECIMAL(15, 2),
    total_return DECIMAL(10, 4),
    sharpe_ratio DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),
    win_rate DECIMAL(5, 2),
    num_trades INTEGER,
    trades JSONB,  -- Store individual trade details as JSON
    equity_curve JSONB,  -- Store daily equity values
    created_at TIMESTAMP DEFAULT NOW(),
    runtime_seconds DECIMAL(10, 3),
    user_id VARCHAR(100),
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_options_backtests_ticker ON options_backtests(ticker);
CREATE INDEX IF NOT EXISTS idx_options_backtests_strategy ON options_backtests(strategy);
CREATE INDEX IF NOT EXISTS idx_options_backtests_created_at ON options_backtests(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_options_backtests_user_id ON options_backtests(user_id);

-- Comments for documentation
COMMENT ON TABLE options_orders IS 'Stores manual options orders (paper and live)';
COMMENT ON COLUMN options_orders.paper IS 'TRUE=paper trading (simulated), FALSE=live broker order (requires LIVE_ORDER_ALLOWED=true)';
COMMENT ON TABLE options_backtests IS 'Stores options strategy backtest results';

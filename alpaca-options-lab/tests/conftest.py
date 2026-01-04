"""
Alpaca Options Lab - Test Configuration

pytest configuration with:
- Common fixtures
- Database fixtures (async and sync)
- Market data fixtures
- Options contract fixtures
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import AsyncGenerator, Generator, Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import numpy as np


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "asyncio: Async tests")


# =============================================================================
# EVENT LOOP FIXTURE
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# MOCK DATABASE FIXTURES
# =============================================================================

@pytest.fixture
def mock_db_pool():
    """Mock asyncpg database pool."""
    pool = AsyncMock()
    connection = AsyncMock()
    
    # Configure connection behavior
    connection.execute = AsyncMock(return_value="INSERT 0 1")
    connection.fetch = AsyncMock(return_value=[])
    connection.fetchrow = AsyncMock(return_value=None)
    connection.fetchval = AsyncMock(return_value=1)
    
    # Pool acquire returns connection
    pool.acquire = AsyncMock(return_value=connection)
    pool.release = AsyncMock()
    
    # Context manager support
    connection.__aenter__ = AsyncMock(return_value=connection)
    connection.__aexit__ = AsyncMock(return_value=None)
    pool.__aenter__ = AsyncMock(return_value=pool)
    pool.__aexit__ = AsyncMock(return_value=None)
    
    return pool


@pytest.fixture
def mock_sync_engine():
    """Mock SQLAlchemy sync engine."""
    engine = MagicMock()
    connection = MagicMock()
    
    engine.connect.return_value.__enter__ = MagicMock(return_value=connection)
    engine.connect.return_value.__exit__ = MagicMock(return_value=None)
    
    return engine


# =============================================================================
# MARKET DATA FIXTURES
# =============================================================================

@pytest.fixture
def sample_ohlcv_data() -> List[Dict[str, Any]]:
    """Sample OHLCV bar data."""
    base_time = datetime(2024, 1, 15, 9, 30)
    bars = []
    
    price = 150.0
    for i in range(100):
        change = np.random.normal(0, 0.5)
        price = max(price + change, 100)
        
        bars.append({
            "timestamp": base_time + timedelta(minutes=i),
            "open": price - 0.1,
            "high": price + 0.3,
            "low": price - 0.2,
            "close": price,
            "volume": int(np.random.uniform(1000, 10000)),
            "vwap": price - 0.05,
        })
    
    return bars


@pytest.fixture
def sample_quote() -> Dict[str, Any]:
    """Sample quote data."""
    return {
        "timestamp": datetime(2024, 1, 15, 10, 0),
        "symbol": "AAPL",
        "bid_price": 149.95,
        "ask_price": 150.05,
        "bid_size": 100,
        "ask_size": 150,
        "last_price": 150.00,
        "last_size": 50,
    }


@pytest.fixture
def sample_trade() -> Dict[str, Any]:
    """Sample trade data."""
    return {
        "timestamp": datetime(2024, 1, 15, 10, 0, 1),
        "symbol": "AAPL",
        "price": 150.02,
        "size": 100,
        "exchange": "NASDAQ",
        "conditions": ["@"],
    }


# =============================================================================
# OPTIONS CONTRACT FIXTURES
# =============================================================================

@pytest.fixture
def sample_option_contract() -> Dict[str, Any]:
    """Sample options contract."""
    return {
        "symbol": "AAPL240119C00150000",
        "underlying": "AAPL",
        "expiration": datetime(2024, 1, 19),
        "strike": 150.0,
        "option_type": "call",
        "multiplier": 100,
        "style": "american",
    }


@pytest.fixture
def sample_option_chain() -> List[Dict[str, Any]]:
    """Sample options chain."""
    underlying = "AAPL"
    expiration = datetime(2024, 1, 19)
    spot = 150.0
    
    chain = []
    strikes = [140, 145, 150, 155, 160]
    
    for strike in strikes:
        for opt_type in ["call", "put"]:
            moneyness = spot / strike if opt_type == "call" else strike / spot
            
            chain.append({
                "symbol": f"{underlying}240119{'C' if opt_type == 'call' else 'P'}{strike:08.0f}0",
                "underlying": underlying,
                "expiration": expiration,
                "strike": float(strike),
                "option_type": opt_type,
                "bid": max(0, (spot - strike if opt_type == "call" else strike - spot)) + np.random.uniform(0.1, 0.5),
                "ask": max(0, (spot - strike if opt_type == "call" else strike - spot)) + np.random.uniform(0.5, 1.0),
                "last": max(0, (spot - strike if opt_type == "call" else strike - spot)) + np.random.uniform(0.3, 0.7),
                "volume": int(np.random.uniform(100, 5000)),
                "open_interest": int(np.random.uniform(1000, 50000)),
                "iv": 0.25 + np.random.uniform(-0.05, 0.05),
                "delta": 0.5 * moneyness if opt_type == "call" else -0.5 * moneyness,
                "gamma": 0.05 * (1 - abs(moneyness - 1)),
                "theta": -0.02,
                "vega": 0.1,
            })
    
    return chain


# =============================================================================
# GREEKS FIXTURES
# =============================================================================

@pytest.fixture
def option_pricing_inputs() -> Dict[str, float]:
    """Standard inputs for option pricing."""
    return {
        "spot": 150.0,
        "strike": 150.0,
        "rate": 0.05,
        "time_to_expiry": 0.25,  # 3 months
        "volatility": 0.25,
    }


@pytest.fixture
def expected_greeks() -> Dict[str, Dict[str, float]]:
    """Expected Greeks for ATM option."""
    # These are approximate values for S=K=150, T=0.25, r=0.05, σ=0.25
    return {
        "call": {
            "price": 7.59,  # Approximate
            "delta": 0.55,
            "gamma": 0.024,
            "theta": -0.035,
            "vega": 0.30,
            "rho": 0.17,
        },
        "put": {
            "price": 5.73,  # Approximate
            "delta": -0.45,
            "gamma": 0.024,
            "theta": -0.020,
            "vega": 0.30,
            "rho": -0.20,
        },
    }


# =============================================================================
# POSITION FIXTURES
# =============================================================================

@pytest.fixture
def sample_position() -> Dict[str, Any]:
    """Sample options position."""
    return {
        "symbol": "AAPL240119C00150000",
        "underlying": "AAPL",
        "quantity": 10,
        "side": "long",
        "avg_cost": 3.50,
        "current_price": 4.20,
        "market_value": 4200.0,
        "unrealized_pnl": 700.0,
        "delta": 5.5,  # 10 contracts * 0.55 delta
        "gamma": 0.24,
        "theta": -3.5,
        "vega": 3.0,
    }


@pytest.fixture
def sample_portfolio() -> List[Dict[str, Any]]:
    """Sample portfolio with multiple positions."""
    return [
        {
            "symbol": "AAPL240119C00150000",
            "underlying": "AAPL",
            "quantity": 10,
            "side": "long",
            "delta": 5.5,
            "gamma": 0.24,
            "theta": -3.5,
            "vega": 3.0,
            "market_value": 4200.0,
        },
        {
            "symbol": "AAPL240119P00145000",
            "underlying": "AAPL",
            "quantity": -5,
            "side": "short",
            "delta": 1.5,  # Short put, positive delta
            "gamma": 0.10,
            "theta": 1.2,  # Collecting theta
            "vega": -1.0,
            "market_value": -1200.0,
        },
        {
            "symbol": "MSFT240119C00400000",
            "underlying": "MSFT",
            "quantity": 5,
            "side": "long",
            "delta": 2.75,
            "gamma": 0.08,
            "theta": -2.0,
            "vega": 1.5,
            "market_value": 3000.0,
        },
    ]


# =============================================================================
# BACKTEST FIXTURES
# =============================================================================

@pytest.fixture
def sample_backtest_result() -> Dict[str, Any]:
    """Sample backtest result."""
    # Generate equity curve
    initial_equity = 100000.0
    equity_curve = []
    equity = initial_equity
    
    start = datetime(2023, 1, 1)
    for i in range(252):  # One year
        daily_return = np.random.normal(0.0003, 0.01)
        equity *= (1 + daily_return)
        equity_curve.append((start + timedelta(days=i), equity))
    
    # Generate trades
    trades = []
    for i in range(50):
        pnl = np.random.normal(200, 500)
        trades.append({
            "entry_time": start + timedelta(days=i * 5),
            "exit_time": start + timedelta(days=i * 5 + 3),
            "symbol": "AAPL240119C00150000",
            "quantity": 5,
            "entry_price": 3.50,
            "exit_price": 3.50 + pnl / 500,
            "pnl": pnl,
            "fees": 2.50,
            "net_pnl": pnl - 2.50,
        })
    
    final_equity = equity_curve[-1][1]
    total_return = final_equity - initial_equity
    
    return {
        "initial_capital": initial_equity,
        "final_equity": final_equity,
        "total_return": total_return,
        "total_return_pct": total_return / initial_equity,
        "equity_curve": equity_curve,
        "trades": trades,
        "total_trades": len(trades),
        "winning_trades": len([t for t in trades if t["pnl"] > 0]),
        "losing_trades": len([t for t in trades if t["pnl"] <= 0]),
        "win_rate": len([t for t in trades if t["pnl"] > 0]) / len(trades),
        "sharpe_ratio": 1.5,
        "max_drawdown": 0.08,
        "volatility": 0.15,
        "annualized_return": 0.12,
        "profit_factor": 1.8,
    }


# =============================================================================
# RISK FIXTURES
# =============================================================================

@pytest.fixture
def sample_risk_limits() -> List[Dict[str, Any]]:
    """Sample risk limits configuration."""
    return [
        {"type": "MAX_POSITION_SIZE", "value": 100000, "hard_limit": True},
        {"type": "MAX_PORTFOLIO_DELTA", "value": 500, "hard_limit": True},
        {"type": "MAX_PORTFOLIO_GAMMA", "value": 50, "hard_limit": False},
        {"type": "MAX_PORTFOLIO_VEGA", "value": 1000, "hard_limit": False},
        {"type": "MAX_CONCENTRATION", "value": 0.25, "hard_limit": True},
        {"type": "MAX_DRAWDOWN", "value": 0.15, "hard_limit": True},
    ]


# =============================================================================
# UTILITY FIXTURES
# =============================================================================

@pytest.fixture
def mock_logger():
    """Mock logger."""
    return MagicMock()


@pytest.fixture
def freeze_time():
    """Fixture to freeze time at a specific moment."""
    from unittest.mock import patch
    
    frozen_time = datetime(2024, 1, 15, 10, 0, 0)
    
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = frozen_time
        mock_datetime.utcnow.return_value = frozen_time
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        yield frozen_time

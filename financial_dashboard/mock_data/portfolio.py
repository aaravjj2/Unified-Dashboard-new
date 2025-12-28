"""
Portfolio Mock Data
===================
Provides deterministic mock data for Portfolio Tracker analytics.
"""

import time
import numpy as np
from datetime import datetime, timedelta

def get_portfolio_mock_data():
    """Return comprehensive mock portfolio data."""
    return {
        'summary': {
            'portfolio_value': 101082.61,
            'total_invested': 92939.10,
            'unrealized_pl': 8143.51,
            'unrealized_pl_pct': 8.76,
            'buying_power': 50000.00,
            'cash': 25082.61,
            'day_pl': 1234.56,
            'day_pl_pct': 1.24,
        },
        
        'analytics': {
            'sharpe_ratio': 1.45,
            'sortino_ratio': 1.89,
            'max_drawdown': -8.2,
            'max_drawdown_duration': 23,  # days
            'beta': 1.12,
            'alpha': 3.45,
            'volatility': 18.5,
            'var_95': -2834.50,  # 95% Value at Risk
            'cvar_95': -3567.80,  # Conditional VaR
            'calmar_ratio': 1.51,
            'treynor_ratio': 12.34,
            'information_ratio': 0.67,
        },
        
        'allocation': {
            'Technology': 48.5,
            'Financials': 12.3,
            'Healthcare': 15.2,
            'Consumer': 8.9,
            'Energy': 5.1,
            'Cash': 10.0,
        },
        
        'positions': get_mock_positions(),
        'historical_returns': get_mock_returns(),
        'benchmark_comparison': get_benchmark_comparison(),
        
        'timestamp': time.time(),
    }


def get_mock_positions():
    """Return mock positions data."""
    return [
        {
            'symbol': 'AAPL',
            'qty': 50,
            'avg_cost': 228.33,
            'current_price': 238.76,
            'market_value': 11938.00,
            'unrealized_pl': 521.50,
            'unrealized_pl_pct': 4.57,
            'weight': 11.81,
            'sector': 'Technology',
        },
        {
            'symbol': 'MSFT',
            'qty': 30,
            'avg_cost': 388.14,
            'current_price': 417.89,
            'market_value': 12536.70,
            'unrealized_pl': 892.50,
            'unrealized_pl_pct': 7.67,
            'weight': 12.40,
            'sector': 'Technology',
        },
        {
            'symbol': 'NVDA',
            'qty': 20,
            'avg_cost': 148.92,
            'current_price': 142.55,
            'market_value': 2851.00,
            'unrealized_pl': -127.40,
            'unrealized_pl_pct': -4.28,
            'weight': 2.82,
            'sector': 'Technology',
        },
        {
            'symbol': 'GOOGL',
            'qty': 25,
            'avg_cost': 186.77,
            'current_price': 193.02,
            'market_value': 4825.50,
            'unrealized_pl': 156.25,
            'unrealized_pl_pct': 3.35,
            'weight': 4.77,
            'sector': 'Technology',
        },
        {
            'symbol': 'AMZN',
            'qty': 15,
            'avg_cost': 211.83,
            'current_price': 227.44,
            'market_value': 3411.60,
            'unrealized_pl': 234.15,
            'unrealized_pl_pct': 7.38,
            'weight': 3.37,
            'sector': 'Consumer',
        },
        {
            'symbol': 'META',
            'qty': 18,
            'avg_cost': 574.80,
            'current_price': 612.48,
            'market_value': 11024.64,
            'unrealized_pl': 678.24,
            'unrealized_pl_pct': 6.56,
            'weight': 10.91,
            'sector': 'Technology',
        },
        {
            'symbol': 'JPM',
            'qty': 40,
            'avg_cost': 232.49,
            'current_price': 242.18,
            'market_value': 9687.20,
            'unrealized_pl': 387.60,
            'unrealized_pl_pct': 4.17,
            'weight': 9.58,
            'sector': 'Financials',
        },
        {
            'symbol': 'UNH',
            'qty': 12,
            'avg_cost': 512.45,
            'current_price': 545.23,
            'market_value': 6542.76,
            'unrealized_pl': 393.36,
            'unrealized_pl_pct': 6.40,
            'weight': 6.47,
            'sector': 'Healthcare',
        },
    ]


def get_mock_returns():
    """Generate mock historical returns for analytics."""
    # 252 trading days (~1 year)
    np.random.seed(42)  # Deterministic
    
    # Generate returns with realistic properties
    daily_returns = np.random.normal(0.0004, 0.012, 252)  # ~10% annual return, ~19% vol
    
    # Add some autocorrelation and fat tails
    daily_returns = np.clip(daily_returns, -0.05, 0.05)
    
    # Create dates
    end_date = datetime.now()
    dates = [(end_date - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(252)][::-1]
    
    # Calculate cumulative returns
    cumulative = np.cumprod(1 + daily_returns) - 1
    
    return {
        'dates': dates,
        'daily_returns': daily_returns.tolist(),
        'cumulative_returns': cumulative.tolist(),
    }


def get_benchmark_comparison():
    """Return benchmark comparison data (SPY)."""
    np.random.seed(43)
    
    # SPY benchmark returns
    spy_returns = np.random.normal(0.0003, 0.01, 252)
    spy_cumulative = np.cumprod(1 + spy_returns) - 1
    
    return {
        'benchmark': 'SPY',
        'portfolio_return': 12.4,
        'benchmark_return': 8.2,
        'excess_return': 4.2,
        'tracking_error': 5.8,
        'correlation': 0.87,
        'benchmark_cumulative': spy_cumulative.tolist(),
    }


def calculate_sharpe_from_returns(returns, risk_free_rate=0.04):
    """
    Calculate Sharpe ratio from returns array.
    
    TODO: Plug in real historical returns here.
    """
    if len(returns) == 0:
        return 0.0
    
    excess_returns = np.array(returns) - (risk_free_rate / 252)  # Daily risk-free
    if np.std(excess_returns) == 0:
        return 0.0
    
    return (np.mean(excess_returns) / np.std(excess_returns)) * np.sqrt(252)


def calculate_max_drawdown(cumulative_returns):
    """
    Calculate maximum drawdown from cumulative returns.
    
    TODO: Plug in real cumulative returns here.
    """
    if len(cumulative_returns) == 0:
        return 0.0
    
    peak = np.maximum.accumulate(np.array(cumulative_returns) + 1)
    drawdown = (np.array(cumulative_returns) + 1) / peak - 1
    return float(np.min(drawdown) * 100)


def calculate_beta(portfolio_returns, benchmark_returns):
    """
    Calculate portfolio beta relative to benchmark.
    
    TODO: Plug in real returns series here.
    """
    if len(portfolio_returns) == 0 or len(benchmark_returns) == 0:
        return 1.0
    
    covariance = np.cov(portfolio_returns, benchmark_returns)[0, 1]
    variance = np.var(benchmark_returns)
    
    if variance == 0:
        return 1.0
    
    return covariance / variance

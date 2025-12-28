"""
Command Center Mock Data
========================
Provides deterministic mock data for the Command Center dashboard.
"""

import time
from datetime import datetime

def get_command_center_mock_data():
    """Return mock data for Command Center display."""
    return {
        'portfolio_value': 101082.61,
        'todays_pnl': 1234.56,
        'todays_pnl_pct': 1.24,
        'market_status': get_market_status(),
        'cash': 25082.61,
        'buying_power': 50000.00,
        'positions_count': 8,
        
        # Market sentiment
        'sentiment': {
            'score': 0.233,
            'label': 'Neutral',
            'sources': ['yfinance'],
        },
        
        # Picks status
        'picks': {
            'weekly_count': 20,
            'monthly_count': 10,
            'last_run': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'status': 'healthy',
        },
        
        # System status
        'services': {
            'dashboard': True,
            'api': True,
            'alpaca': True,
            'database': False,  # Postgres not running in dev
        },
        
        # Performance metrics
        'performance': {
            'cagr': '12.4%',
            'sharpe': 1.45,
            'max_drawdown': '-8.2%',
            'win_rate': '64%',
        },
        
        'timestamp': time.time(),
    }


def get_market_status():
    """Determine if market is open based on current time."""
    now = datetime.now()
    weekday = now.weekday()
    hour = now.hour
    minute = now.minute
    
    # Market hours: Mon-Fri, 9:30 AM - 4:00 PM ET
    # Simplified check (assumes local time is ET)
    if weekday >= 5:  # Weekend
        return 'Closed'
    
    market_open = (hour == 9 and minute >= 30) or (10 <= hour < 16)
    
    if market_open:
        return 'Open'
    elif hour < 9 or (hour == 9 and minute < 30):
        return 'Pre-Market'
    else:
        return 'After-Hours'


def get_demo_positions():
    """Return demo portfolio positions for display."""
    return [
        {'symbol': 'AAPL', 'qty': 50, 'current_price': 238.76, 'market_value': 11938.00, 'unrealized_pl': 523.50, 'unrealized_plpc': 4.58},
        {'symbol': 'MSFT', 'qty': 30, 'current_price': 417.89, 'market_value': 12536.70, 'unrealized_pl': 892.20, 'unrealized_plpc': 7.67},
        {'symbol': 'NVDA', 'qty': 20, 'current_price': 142.55, 'market_value': 2851.00, 'unrealized_pl': -127.40, 'unrealized_plpc': -4.27},
        {'symbol': 'GOOGL', 'qty': 25, 'current_price': 193.02, 'market_value': 4825.50, 'unrealized_pl': 156.25, 'unrealized_plpc': 3.35},
        {'symbol': 'AMZN', 'qty': 15, 'current_price': 227.44, 'market_value': 3411.60, 'unrealized_pl': 234.15, 'unrealized_plpc': 7.38},
        {'symbol': 'META', 'qty': 18, 'current_price': 612.48, 'market_value': 11024.64, 'unrealized_pl': 678.24, 'unrealized_plpc': 6.56},
        {'symbol': 'TSLA', 'qty': 22, 'current_price': 454.13, 'market_value': 9990.86, 'unrealized_pl': -445.28, 'unrealized_plpc': -4.27},
        {'symbol': 'JPM', 'qty': 40, 'current_price': 242.18, 'market_value': 9687.20, 'unrealized_pl': 387.60, 'unrealized_plpc': 4.17},
    ]

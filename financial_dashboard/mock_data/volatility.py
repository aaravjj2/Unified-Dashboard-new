"""
Volatility Lab Mock Data
========================
Provides deterministic mock data for IV Surface and volatility analysis.
"""

import time
import numpy as np
from datetime import datetime, timedelta

def get_volatility_mock_data():
    """Return comprehensive mock volatility data."""
    return {
        'ticker': 'SPY',
        'spot_price': 598.45,
        'atm_iv': 14.8,
        'iv_rank': 32,
        'iv_percentile': 28,
        
        'term_structure': {
            '7d': 13.2,
            '14d': 13.8,
            '30d': 14.8,
            '60d': 15.6,
            '90d': 16.2,
            '180d': 17.1,
        },
        
        'iv_surface': generate_iv_surface(),
        'metrics': get_surface_metrics(),
        'signals': get_volatility_signals(),
        'regime': get_regime_assessment(),
        
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'timestamp': time.time(),
    }


def generate_iv_surface():
    """
    Generate realistic IV surface data for 3D/2D visualization.
    
    Returns dict with:
    - strikes: list of strike prices
    - expiries: list of expiry dates (days to expiry)
    - iv_grid: 2D array of IV values
    """
    np.random.seed(42)  # Deterministic
    
    # Define grid parameters
    spot = 598.45
    strikes = np.linspace(spot * 0.85, spot * 1.15, 15)  # 85% to 115% of spot
    expiries = [7, 14, 21, 30, 45, 60, 90, 120, 180]  # Days to expiry
    
    # Generate IV surface with realistic smile/skew characteristics
    iv_grid = []
    for dte in expiries:
        row = []
        for strike in strikes:
            # Moneyness
            moneyness = np.log(strike / spot)
            
            # Base IV increases with time (term structure)
            base_iv = 14.5 + 2.5 * np.sqrt(dte / 365)
            
            # Add smile (higher IV for OTM options)
            smile = 3.0 * moneyness ** 2
            
            # Add skew (higher IV for puts/lower strikes)
            skew = -1.5 * moneyness if moneyness < 0 else -0.5 * moneyness
            
            # Add some noise
            noise = np.random.normal(0, 0.3)
            
            iv = base_iv + smile + skew + noise
            iv = max(8, min(50, iv))  # Clamp to reasonable range
            
            row.append(round(iv, 2))
        iv_grid.append(row)
    
    return {
        'strikes': strikes.tolist(),
        'expiries': expiries,
        'expiry_labels': [f'{d}d' for d in expiries],
        'iv_grid': iv_grid,
        'min_iv': min(min(row) for row in iv_grid),
        'max_iv': max(max(row) for row in iv_grid),
        'atm_index': len(strikes) // 2,
    }


def get_surface_metrics():
    """Return computed metrics from IV surface."""
    return {
        'atm_iv': 14.8,
        'put_skew_25d': 2.3,  # 25-delta put IV - ATM IV
        'call_skew_25d': -0.8,  # 25-delta call IV - ATM IV
        'term_spread_30_90': 1.4,  # 90d IV - 30d IV
        'butterfly_spread': 1.1,  # (25d put + 25d call) / 2 - ATM
        'risk_reversal': 3.1,  # 25d put IV - 25d call IV
        
        # Greeks at ATM 30-day
        'atm_vega': 0.42,
        'atm_gamma': 0.028,
        'vanna': 0.015,
        'volga': 0.008,
    }


def get_volatility_signals():
    """Return trading signals based on volatility analysis."""
    return [
        {
            'signal': 'SELL_PREMIUM',
            'strength': 'Medium',
            'rationale': 'IV Rank at 32 - above historical median, selling premium favorable',
            'suggested_strategy': 'Iron Condor or Short Strangle',
            'risk_level': 'Moderate',
        },
        {
            'signal': 'CALENDAR_SPREAD',
            'strength': 'Strong',
            'rationale': 'Term structure upward sloping (+1.4% 30-90d spread)',
            'suggested_strategy': 'Sell front-month, buy back-month',
            'risk_level': 'Low',
        },
        {
            'signal': 'PUT_SKEW_ELEVATED',
            'strength': 'Weak',
            'rationale': '25d put skew at 2.3%, slightly elevated',
            'suggested_strategy': 'Consider put spread vs naked puts',
            'risk_level': 'Informational',
        },
    ]


def get_regime_assessment():
    """Return current volatility regime assessment."""
    return {
        'regime': 'Normal',
        'regime_score': 45,  # 0-100 scale
        'description': 'Market in normal volatility regime, neither compressed nor elevated',
        'historical_context': {
            'current_vix': 14.8,
            'vix_percentile_1y': 32,
            'vix_percentile_5y': 28,
            'realized_vs_implied': -1.2,  # IV - RV
        },
        'regime_probabilities': {
            'low_vol': 0.25,
            'normal': 0.55,
            'high_vol': 0.15,
            'crisis': 0.05,
        },
    }


def get_backtest_mock_results():
    """Return mock backtest results for volatility strategies."""
    return {
        'strategy': 'Iron Condor',
        'ticker': 'SPY',
        'period': '2024-01-01 to 2024-12-27',
        'trades': 24,
        'win_rate': 0.71,
        'profit_factor': 1.45,
        'total_return': 12.8,
        'max_drawdown': -8.5,
        'sharpe': 1.32,
        
        'trade_history': [
            {'date': '2024-12-20', 'pnl': 245.50, 'win': True},
            {'date': '2024-12-13', 'pnl': -180.00, 'win': False},
            {'date': '2024-12-06', 'pnl': 312.00, 'win': True},
            {'date': '2024-11-29', 'pnl': 198.00, 'win': True},
            {'date': '2024-11-22', 'pnl': -420.00, 'win': False},
        ],
        
        'metrics_by_regime': {
            'low_vol': {'trades': 8, 'win_rate': 0.88, 'avg_pnl': 285},
            'normal': {'trades': 12, 'win_rate': 0.67, 'avg_pnl': 145},
            'high_vol': {'trades': 4, 'win_rate': 0.50, 'avg_pnl': -85},
        },
    }

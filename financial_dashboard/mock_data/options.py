"""
Options Lab Mock Data
=====================
Provides deterministic mock data for Options Lab.
"""

import time
import numpy as np
from datetime import datetime, timedelta
import math

def get_options_mock_data(ticker='AAPL'):
    """Return comprehensive mock options data."""
    spot_price = _get_spot_price(ticker)
    
    return {
        'ticker': ticker,
        'spot_price': spot_price,
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        
        'iv_metrics': {
            'iv_rank': 45,
            'iv_percentile': 42,
            'current_iv': 24.5,
            'hv_20': 22.1,
            'hv_50': 23.8,
            'iv_hv_spread': 2.4,
        },
        
        'chain': generate_option_chain(ticker, spot_price),
        'greeks_sample': generate_greeks_sample(ticker, spot_price),
        'ai_recommendations': generate_ai_recommendations(ticker, spot_price),
        
        'timestamp': time.time(),
    }


def _get_spot_price(ticker):
    """Return mock spot price for ticker."""
    prices = {
        'AAPL': 238.76,
        'MSFT': 417.89,
        'NVDA': 142.55,
        'GOOGL': 193.02,
        'AMZN': 227.44,
        'META': 612.48,
        'TSLA': 454.13,
        'SPY': 598.45,
        'QQQ': 524.89,
    }
    return prices.get(ticker.upper(), 100.00)


def generate_option_chain(ticker, spot_price, dte=30):
    """
    Generate mock option chain data.
    
    Returns calls and puts with realistic bid/ask spreads.
    """
    np.random.seed(hash(ticker) % 2**31)
    
    # Generate strikes around spot price
    strike_range = 0.15  # 15% above/below spot
    num_strikes = 21
    strikes = np.linspace(
        spot_price * (1 - strike_range),
        spot_price * (1 + strike_range),
        num_strikes
    )
    strikes = np.round(strikes / 2.5) * 2.5  # Round to nearest $2.50
    
    chain = []
    for strike in strikes:
        moneyness = strike / spot_price
        
        # Base IV with smile
        base_iv = 25 + 15 * (moneyness - 1) ** 2
        if moneyness < 1:  # Put skew
            base_iv += 3 * (1 - moneyness)
        
        # Calculate theoretical prices using simplified Black-Scholes
        call_price, put_price = _calculate_option_prices(spot_price, strike, dte, base_iv / 100)
        
        # Add realistic bid/ask spread
        spread_pct = max(0.02, 0.05 * abs(moneyness - 1))
        
        call_mid = max(0.01, call_price)
        put_mid = max(0.01, put_price)
        
        call_bid = round(call_mid * (1 - spread_pct), 2)
        call_ask = round(call_mid * (1 + spread_pct), 2)
        put_bid = round(put_mid * (1 - spread_pct), 2)
        put_ask = round(put_mid * (1 + spread_pct), 2)
        
        # Volume and OI
        atm_factor = np.exp(-10 * (moneyness - 1) ** 2)
        base_volume = int(1000 * atm_factor + 50)
        base_oi = int(5000 * atm_factor + 200)
        
        chain.append({
            'strike': round(strike, 2),
            
            'call_bid': max(0.01, call_bid),
            'call_ask': max(0.02, call_ask),
            'call_last': round((call_bid + call_ask) / 2, 2),
            'call_iv': round(base_iv + np.random.normal(0, 0.5), 1),
            'call_volume': int(base_volume * (1 + np.random.uniform(-0.3, 0.3))),
            'call_oi': int(base_oi * (1 + np.random.uniform(-0.2, 0.2))),
            
            'put_bid': max(0.01, put_bid),
            'put_ask': max(0.02, put_ask),
            'put_last': round((put_bid + put_ask) / 2, 2),
            'put_iv': round(base_iv + 2 + np.random.normal(0, 0.5), 1),  # Put skew
            'put_volume': int(base_volume * 0.8 * (1 + np.random.uniform(-0.3, 0.3))),
            'put_oi': int(base_oi * 0.9 * (1 + np.random.uniform(-0.2, 0.2))),
        })
    
    return chain


def _calculate_option_prices(S, K, dte, iv):
    """Simplified Black-Scholes option pricing."""
    T = dte / 365
    r = 0.045  # Risk-free rate
    
    if T <= 0 or iv <= 0:
        return max(0, S - K), max(0, K - S)
    
    d1 = (math.log(S / K) + (r + iv**2 / 2) * T) / (iv * math.sqrt(T))
    d2 = d1 - iv * math.sqrt(T)
    
    # Normal CDF approximation
    def norm_cdf(x):
        return (1 + math.erf(x / math.sqrt(2))) / 2
    
    call = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    put = K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)
    
    return max(0, call), max(0, put)


def generate_greeks_sample(ticker, spot_price, strike=None, option_type='call', dte=30):
    """
    Generate Greeks for a sample option.
    Uses simplified Black-Scholes Greeks.
    """
    if strike is None:
        strike = round(spot_price / 5) * 5  # ATM strike
    
    T = dte / 365
    iv = 0.25  # 25% IV
    r = 0.045
    
    # Calculate d1, d2
    d1 = (math.log(spot_price / strike) + (r + iv**2 / 2) * T) / (iv * math.sqrt(T))
    d2 = d1 - iv * math.sqrt(T)
    
    def norm_cdf(x):
        return (1 + math.erf(x / math.sqrt(2))) / 2
    
    def norm_pdf(x):
        return math.exp(-x**2 / 2) / math.sqrt(2 * math.pi)
    
    # Greeks
    if option_type == 'call':
        delta = norm_cdf(d1)
        theta_factor = 1
    else:
        delta = norm_cdf(d1) - 1
        theta_factor = -1
    
    gamma = norm_pdf(d1) / (spot_price * iv * math.sqrt(T))
    vega = spot_price * norm_pdf(d1) * math.sqrt(T) / 100  # Per 1% IV change
    theta = -(spot_price * norm_pdf(d1) * iv / (2 * math.sqrt(T)) + 
              theta_factor * r * strike * math.exp(-r * T) * norm_cdf(theta_factor * d2)) / 365
    rho = (theta_factor * strike * T * math.exp(-r * T) * norm_cdf(theta_factor * d2)) / 100
    
    return {
        'ticker': ticker,
        'strike': strike,
        'expiry': (datetime.now() + timedelta(days=dte)).strftime('%Y-%m-%d'),
        'option_type': option_type,
        'spot_price': spot_price,
        
        'delta': round(delta, 4),
        'gamma': round(gamma, 6),
        'vega': round(vega, 4),
        'theta': round(theta, 4),
        'rho': round(rho, 4),
        
        'iv': round(iv * 100, 1),
        'theoretical_price': round(_calculate_option_prices(spot_price, strike, dte, iv)[0 if option_type == 'call' else 1], 2),
    }


def generate_ai_recommendations(ticker, spot_price):
    """Generate AI-powered trade recommendations."""
    return [
        {
            'strategy': 'Bull Put Spread',
            'confidence': 78,
            'expected_return': 12.5,
            'max_loss': -450,
            'max_gain': 150,
            'probability_profit': 68,
            'legs': [
                {'action': 'SELL', 'strike': round(spot_price * 0.95, 2), 'type': 'PUT', 'qty': 1, 'expiry': '2025-01-17'},
                {'action': 'BUY', 'strike': round(spot_price * 0.90, 2), 'type': 'PUT', 'qty': 1, 'expiry': '2025-01-17'},
            ],
            'rationale': 'Elevated IV rank (45) favors premium selling. Bullish market bias supports put credit spread.',
        },
        {
            'strategy': 'Iron Condor',
            'confidence': 72,
            'expected_return': 8.2,
            'max_loss': -680,
            'max_gain': 220,
            'probability_profit': 62,
            'legs': [
                {'action': 'SELL', 'strike': round(spot_price * 0.95, 2), 'type': 'PUT', 'qty': 1, 'expiry': '2025-01-17'},
                {'action': 'BUY', 'strike': round(spot_price * 0.90, 2), 'type': 'PUT', 'qty': 1, 'expiry': '2025-01-17'},
                {'action': 'SELL', 'strike': round(spot_price * 1.05, 2), 'type': 'CALL', 'qty': 1, 'expiry': '2025-01-17'},
                {'action': 'BUY', 'strike': round(spot_price * 1.10, 2), 'type': 'CALL', 'qty': 1, 'expiry': '2025-01-17'},
            ],
            'rationale': 'Range-bound expectation with elevated IV. Collect premium on both sides.',
        },
        {
            'strategy': 'Calendar Spread',
            'confidence': 65,
            'expected_return': 15.0,
            'max_loss': -280,
            'max_gain': 180,
            'probability_profit': 55,
            'legs': [
                {'action': 'SELL', 'strike': round(spot_price, 2), 'type': 'CALL', 'qty': 1, 'expiry': '2025-01-10'},
                {'action': 'BUY', 'strike': round(spot_price, 2), 'type': 'CALL', 'qty': 1, 'expiry': '2025-02-21'},
            ],
            'rationale': 'Upward-sloping term structure. Profit from time decay differential.',
        },
    ]

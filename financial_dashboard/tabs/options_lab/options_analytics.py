"""
Options Analytics Module
========================
Advanced analytics for options trading including:
- IV Rank & Percentile
- Max Pain Calculator
- Expected Move
- Put/Call Ratio
- Historical Volatility Comparison
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def calculate_iv_rank(current_iv: float, iv_history: List[float]) -> float:
    """
    Calculate IV Rank (0-100).
    
    IV Rank shows where current IV falls within the 52-week range.
    - 0 = At 52-week low
    - 100 = At 52-week high
    
    Args:
        current_iv: Current implied volatility
        iv_history: List of historical IV values (ideally 252 trading days)
        
    Returns:
        IV Rank as percentage (0-100)
    """
    if not iv_history or len(iv_history) < 2:
        return 50.0
    
    min_iv = min(iv_history)
    max_iv = max(iv_history)
    
    if max_iv == min_iv:
        return 50.0
    
    return ((current_iv - min_iv) / (max_iv - min_iv)) * 100


def calculate_iv_percentile(current_iv: float, iv_history: List[float]) -> float:
    """
    Calculate IV Percentile (0-100).
    
    IV Percentile shows what percentage of days had lower IV.
    - 90% = Current IV is higher than 90% of historical readings
    
    Args:
        current_iv: Current implied volatility
        iv_history: List of historical IV values
        
    Returns:
        IV Percentile as percentage (0-100)
    """
    if not iv_history:
        return 50.0
    
    below_count = sum(1 for iv in iv_history if iv < current_iv)
    return (below_count / len(iv_history)) * 100


def calculate_max_pain(calls_df: pd.DataFrame, puts_df: pd.DataFrame) -> Dict:
    """
    Calculate max pain strike - the price at which option sellers profit most.
    
    Args:
        calls_df: DataFrame with calls (must have 'strike' and 'openInterest' columns)
        puts_df: DataFrame with puts (must have 'strike' and 'openInterest' columns)
        
    Returns:
        Dict with max_pain_strike, call_pain, put_pain, total_pain
    """
    if calls_df.empty and puts_df.empty:
        return {'max_pain_strike': 0, 'call_pain': 0, 'put_pain': 0, 'total_pain': 0}
    
    # Get all unique strikes
    all_strikes = set()
    if not calls_df.empty and 'strike' in calls_df.columns:
        all_strikes.update(calls_df['strike'].tolist())
    if not puts_df.empty and 'strike' in puts_df.columns:
        all_strikes.update(puts_df['strike'].tolist())
    
    if not all_strikes:
        return {'max_pain_strike': 0, 'call_pain': 0, 'put_pain': 0, 'total_pain': 0}
    
    strikes = sorted(all_strikes)
    min_pain = float('inf')
    max_pain_strike = strikes[len(strikes) // 2]
    best_call_pain = 0
    best_put_pain = 0
    
    # Ensure openInterest column exists
    call_oi_col = 'openInterest' if 'openInterest' in calls_df.columns else 'open_interest'
    put_oi_col = 'openInterest' if 'openInterest' in puts_df.columns else 'open_interest'
    
    for settlement_price in strikes:
        call_pain = 0
        put_pain = 0
        
        # Calculate call pain (ITM calls lose money for buyers)
        if not calls_df.empty and call_oi_col in calls_df.columns:
            for _, row in calls_df.iterrows():
                strike = row.get('strike', 0)
                oi = row.get(call_oi_col, 0) or 0
                if settlement_price > strike:  # Call is ITM
                    call_pain += oi * (settlement_price - strike) * 100
        
        # Calculate put pain (ITM puts lose money for buyers)
        if not puts_df.empty and put_oi_col in puts_df.columns:
            for _, row in puts_df.iterrows():
                strike = row.get('strike', 0)
                oi = row.get(put_oi_col, 0) or 0
                if settlement_price < strike:  # Put is ITM
                    put_pain += oi * (strike - settlement_price) * 100
        
        total_pain = call_pain + put_pain
        
        if total_pain < min_pain:
            min_pain = total_pain
            max_pain_strike = settlement_price
            best_call_pain = call_pain
            best_put_pain = put_pain
    
    return {
        'max_pain_strike': max_pain_strike,
        'call_pain': best_call_pain,
        'put_pain': best_put_pain,
        'total_pain': min_pain if min_pain != float('inf') else 0
    }


def calculate_expected_move(
    spot: float, 
    atm_call_price: float, 
    atm_put_price: float,
    days_to_expiry: int = 30
) -> Dict:
    """
    Calculate expected move based on ATM straddle price.
    
    The ATM straddle price represents roughly the 1-sigma expected move.
    
    Args:
        spot: Current underlying price
        atm_call_price: ATM call premium
        atm_put_price: ATM put premium
        days_to_expiry: Days until expiration
        
    Returns:
        Dict with expected_move_dollars, expected_move_percent, upper_bound, lower_bound
    """
    straddle_price = atm_call_price + atm_put_price
    
    # Straddle price ≈ 0.8 * expected move for ~30 DTE
    # Adjust factor based on DTE
    if days_to_expiry <= 7:
        factor = 0.95
    elif days_to_expiry <= 14:
        factor = 0.90
    elif days_to_expiry <= 30:
        factor = 0.85
    else:
        factor = 0.80
    
    expected_move = straddle_price / factor
    expected_move_pct = (expected_move / spot) * 100
    
    return {
        'expected_move_dollars': round(expected_move, 2),
        'expected_move_percent': round(expected_move_pct, 2),
        'upper_bound': round(spot + expected_move, 2),
        'lower_bound': round(spot - expected_move, 2),
        'straddle_price': round(straddle_price, 2),
        'probability_range': '68%'  # 1 sigma
    }


def calculate_put_call_ratio(calls_df: pd.DataFrame, puts_df: pd.DataFrame) -> Dict:
    """
    Calculate Put/Call ratio by volume and open interest.
    
    Args:
        calls_df: DataFrame with calls data
        puts_df: DataFrame with puts data
        
    Returns:
        Dict with volume_ratio, oi_ratio, interpretation
    """
    call_volume = 0
    put_volume = 0
    call_oi = 0
    put_oi = 0
    
    vol_col = 'volume' if 'volume' in calls_df.columns else 'Volume'
    oi_col = 'openInterest' if 'openInterest' in calls_df.columns else 'open_interest'
    
    if not calls_df.empty:
        call_volume = calls_df[vol_col].sum() if vol_col in calls_df.columns else 0
        call_oi = calls_df[oi_col].sum() if oi_col in calls_df.columns else 0
    
    if not puts_df.empty:
        put_volume = puts_df[vol_col].sum() if vol_col in puts_df.columns else 0
        put_oi = puts_df[oi_col].sum() if oi_col in puts_df.columns else 0
    
    volume_ratio = put_volume / call_volume if call_volume > 0 else 0
    oi_ratio = put_oi / call_oi if call_oi > 0 else 0
    
    # Interpretation
    if volume_ratio > 1.5:
        interpretation = "Bearish (high put activity)"
    elif volume_ratio < 0.7:
        interpretation = "Bullish (high call activity)"
    else:
        interpretation = "Neutral"
    
    return {
        'volume_ratio': round(volume_ratio, 2),
        'oi_ratio': round(oi_ratio, 2),
        'call_volume': int(call_volume),
        'put_volume': int(put_volume),
        'call_oi': int(call_oi),
        'put_oi': int(put_oi),
        'interpretation': interpretation
    }


def calculate_historical_volatility(prices: List[float], window: int = 20) -> float:
    """
    Calculate historical (realized) volatility.
    
    Args:
        prices: List of closing prices
        window: Rolling window (default 20 days)
        
    Returns:
        Annualized historical volatility
    """
    if len(prices) < window + 1:
        return 0.0
    
    returns = np.diff(np.log(prices))
    hv = np.std(returns[-window:]) * np.sqrt(252)
    return round(hv * 100, 2)  # Return as percentage


def get_iv_vs_hv_analysis(current_iv: float, hv_20: float, hv_30: float) -> Dict:
    """
    Compare IV to HV and provide analysis.
    
    Args:
        current_iv: Current implied volatility (%)
        hv_20: 20-day historical volatility (%)
        hv_30: 30-day historical volatility (%)
        
    Returns:
        Dict with comparison and recommendation
    """
    avg_hv = (hv_20 + hv_30) / 2
    iv_premium = current_iv - avg_hv
    iv_premium_pct = (iv_premium / avg_hv) * 100 if avg_hv > 0 else 0
    
    if iv_premium_pct > 20:
        recommendation = "IV is high - Consider selling premium"
        signal = "SELL"
    elif iv_premium_pct < -20:
        recommendation = "IV is low - Consider buying options"
        signal = "BUY"
    else:
        recommendation = "IV is fairly priced"
        signal = "NEUTRAL"
    
    return {
        'current_iv': round(current_iv, 2),
        'hv_20': round(hv_20, 2),
        'hv_30': round(hv_30, 2),
        'iv_premium': round(iv_premium, 2),
        'iv_premium_percent': round(iv_premium_pct, 2),
        'recommendation': recommendation,
        'signal': signal
    }


def calculate_kelly_criterion(
    win_rate: float,
    avg_win: float,
    avg_loss: float
) -> float:
    """
    Calculate Kelly Criterion for position sizing.
    
    Args:
        win_rate: Probability of winning (0-1)
        avg_win: Average win amount
        avg_loss: Average loss amount (positive number)
        
    Returns:
        Optimal position size as fraction of capital (0-1)
    """
    if avg_loss == 0 or win_rate <= 0 or win_rate >= 1:
        return 0.0
    
    win_loss_ratio = avg_win / avg_loss
    kelly = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
    
    # Half-Kelly is often recommended for safety
    return max(0, min(kelly * 0.5, 0.25))  # Cap at 25% of capital


# Export all functions
__all__ = [
    'calculate_iv_rank',
    'calculate_iv_percentile',
    'calculate_max_pain',
    'calculate_expected_move',
    'calculate_put_call_ratio',
    'calculate_historical_volatility',
    'get_iv_vs_hv_analysis',
    'calculate_kelly_criterion'
]

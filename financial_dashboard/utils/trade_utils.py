"""
utils/trade_utils.py

Trade sizing and execution utilities for monthly picks.

Functions:
- compute_position_size: Kelly criterion / volatility-based position sizing
- estimate_slippage: Market impact estimation based on ADV and spread
- generate_trade_schedule: TWAP/VWAP trade scheduling
- compute_liquidity_flag: Liquidity assessment (OK/WARN/CRITICAL)
"""

import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

# Position sizing parameters
MAX_POSITION_PCT = 0.10  # Max 10% of portfolio in single position
MIN_POSITION_PCT = 0.01  # Min 1% of portfolio in single position
KELLY_FRACTION = 0.25  # Use quarter Kelly for conservative sizing
VOL_TARGET_ANNUAL = 0.15  # 15% annual volatility target

# Liquidity thresholds
ADV_MIN_OK = 1_000_000  # $1M ADV minimum for OK liquidity
ADV_MIN_WARN = 500_000  # $500K ADV minimum for WARN
SPREAD_MAX_OK = 0.002  # 0.2% spread maximum for OK
SPREAD_MAX_WARN = 0.005  # 0.5% spread maximum for WARN

# Slippage parameters
SLIPPAGE_BASE_BPS = 5  # 5 bps base slippage
SLIPPAGE_IMPACT_FACTOR = 0.1  # Market impact factor

# Trade scheduling
TWAP_DEFAULT_DAYS = 5  # Spread trades over 5 days by default
TWAP_SESSIONS_PER_DAY = 4  # 4 trading sessions per day


# ============================================================================
# Position Sizing
# ============================================================================

def compute_position_size(
    prediction: float,
    volatility: float,
    max_notional: float,
    adv: float,
    method: str = 'volatility',
    win_rate: Optional[float] = None,
    avg_win: Optional[float] = None,
    avg_loss: Optional[float] = None
) -> Dict:
    """
    Compute position size using various methods.
    
    Args:
        prediction: Expected return (decimal, e.g., 0.05 for 5%)
        volatility: Annualized volatility (decimal, e.g., 0.30 for 30%)
        max_notional: Maximum notional value available (dollars)
        adv: Average daily volume (dollars)
        method: 'volatility', 'kelly', or 'fixed_pct'
        win_rate: Win rate for Kelly (0-1)
        avg_win: Average win size for Kelly
        avg_loss: Average loss size for Kelly
    
    Returns:
        Dict with:
            - position_size_dollars: Recommended position size
            - position_pct: Percentage of max_notional
            - method_used: Which method was applied
            - rationale: Explanation
            - constraints: Any active constraints
    """
    constraints = []
    
    # Volatility-based sizing
    if method == 'volatility' or (method == 'kelly' and not all([win_rate, avg_win, avg_loss])):
        if method == 'kelly' and not all([win_rate, avg_win, avg_loss]):
            logger.warning("Kelly method requested but parameters missing, using volatility")
            constraints.append("kelly_params_missing")
        
        # Target volatility approach: size = (target_vol / asset_vol) * portfolio_value
        if volatility <= 0:
            volatility = VOL_TARGET_ANNUAL  # Use default if missing
            constraints.append("default_volatility")
        
        raw_size = (VOL_TARGET_ANNUAL / volatility) * max_notional
        method_used = 'volatility'
        rationale = f"Sized to achieve {VOL_TARGET_ANNUAL*100:.0f}% portfolio volatility given asset vol {volatility*100:.1f}%"
    
    # Kelly criterion sizing
    elif method == 'kelly':
        # Kelly formula: f = (p*b - q) / b
        # where p = win_rate, q = 1-p, b = avg_win/avg_loss
        if avg_loss == 0:
            raw_size = max_notional * MIN_POSITION_PCT
            constraints.append("kelly_invalid_avg_loss")
        else:
            b = avg_win / abs(avg_loss)
            q = 1 - win_rate
            kelly_f = (win_rate * b - q) / b
            
            # Apply Kelly fraction for safety
            kelly_f = kelly_f * KELLY_FRACTION
            
            if kelly_f <= 0:
                raw_size = max_notional * MIN_POSITION_PCT
                constraints.append("kelly_negative")
            else:
                raw_size = kelly_f * max_notional
        
        method_used = 'kelly'
        rationale = f"Kelly criterion with {KELLY_FRACTION*100:.0f}% fraction (win_rate={win_rate:.2f}, b={avg_win/abs(avg_loss):.2f})"
    
    # Fixed percentage sizing
    else:  # method == 'fixed_pct'
        raw_size = max_notional * 0.05  # Default 5%
        method_used = 'fixed_pct'
        rationale = "Fixed 5% allocation"
    
    # Apply constraints
    # 1. Max position limit
    if raw_size > max_notional * MAX_POSITION_PCT:
        raw_size = max_notional * MAX_POSITION_PCT
        constraints.append(f"max_position_{MAX_POSITION_PCT*100:.0f}pct")
    
    # 2. Min position limit
    if raw_size < max_notional * MIN_POSITION_PCT:
        raw_size = max_notional * MIN_POSITION_PCT
        constraints.append(f"min_position_{MIN_POSITION_PCT*100:.0f}pct")
    
    # 3. Liquidity constraint (don't exceed 10% of ADV)
    max_adv_size = adv * 0.10
    if raw_size > max_adv_size:
        raw_size = max_adv_size
        constraints.append(f"liquidity_limit_10pct_adv")
    
    # 4. Adjust for prediction magnitude (scale down if low conviction)
    if abs(prediction) < 0.02:  # Less than 2% expected return
        raw_size *= 0.5
        constraints.append("low_conviction_scale")
    
    return {
        'position_size_dollars': round(raw_size, 2),
        'position_pct': round(raw_size / max_notional * 100, 2) if max_notional > 0 else 0,
        'method_used': method_used,
        'rationale': rationale,
        'constraints': constraints
    }


# ============================================================================
# Slippage Estimation
# ============================================================================

def estimate_slippage(
    position_size: float,
    adv: float,
    spread_pct: float = 0.001,
    is_buy: bool = True
) -> Dict:
    """
    Estimate slippage for a trade.
    
    Args:
        position_size: Trade size (dollars)
        adv: Average daily volume (dollars)
        spread_pct: Bid-ask spread (decimal, e.g., 0.001 for 0.1%)
        is_buy: True for buy orders, False for sell orders
    
    Returns:
        Dict with:
            - slippage_bps: Estimated slippage in basis points
            - slippage_pct: Estimated slippage as percentage
            - slippage_dollars: Estimated slippage in dollars
            - components: Breakdown of slippage sources
    """
    # Handle negative position size (take absolute value)
    position_size = abs(position_size)
    
    # Component 1: Spread cost (half-spread for limit orders, full spread for market orders)
    spread_cost_pct = spread_pct * 0.5  # Assume limit orders capture half-spread
    
    # Component 2: Market impact (proportional to trade size vs ADV)
    if adv > 0 and position_size > 0:
        participation_rate = position_size / adv
        # Square root market impact model: impact ∝ sqrt(participation_rate)
        impact_pct = SLIPPAGE_IMPACT_FACTOR * math.sqrt(participation_rate)
    else:
        participation_rate = 0.0
        impact_pct = SLIPPAGE_IMPACT_FACTOR  # Default impact if ADV unknown
    
    # Component 3: Base slippage
    base_slippage_pct = SLIPPAGE_BASE_BPS / 10000
    
    # Total slippage
    total_slippage_pct = spread_cost_pct + impact_pct + base_slippage_pct
    
    return {
        'slippage_bps': round(total_slippage_pct * 10000, 2),
        'slippage_pct': round(total_slippage_pct * 100, 4),
        'slippage_dollars': round(position_size * total_slippage_pct, 2),
        'components': {
            'spread_cost_bps': round(spread_cost_pct * 10000, 2),
            'market_impact_bps': round(impact_pct * 10000, 2),
            'base_slippage_bps': SLIPPAGE_BASE_BPS,
            'participation_rate': round(participation_rate * 100, 2) if adv > 0 else None
        }
    }


# ============================================================================
# Trade Scheduling
# ============================================================================

def generate_trade_schedule(
    position_size: float,
    price: float,
    num_days: int = TWAP_DEFAULT_DAYS,
    strategy: str = 'TWAP',
    adv: Optional[float] = None,
    volume_profile: Optional[List[float]] = None
) -> Dict:
    """
    Generate a trade execution schedule.
    
    Args:
        position_size: Total position size (dollars)
        price: Current stock price
        num_days: Number of days to spread execution
        strategy: 'TWAP' (time-weighted) or 'VWAP' (volume-weighted)
        adv: Average daily volume (for participation rate calc)
        volume_profile: Intraday volume profile (4 values for morning/mid-morning/mid-day/afternoon)
    
    Returns:
        Dict with:
            - schedule: List of execution chunks
            - total_shares: Total shares to execute
            - strategy_used: Execution strategy
            - avg_daily_participation: Average participation rate
    """
    total_shares = int(position_size / price) if price > 0 else 0
    
    if total_shares == 0:
        return {
            'schedule': [],
            'total_shares': 0,
            'strategy_used': strategy,
            'avg_daily_participation': 0
        }
    
    # Default intraday volume profile (morning, mid-morning, mid-day, afternoon)
    if volume_profile is None:
        if strategy == 'VWAP':
            # VWAP: higher volume at open and close
            volume_profile = [0.35, 0.20, 0.20, 0.25]
        else:  # TWAP
            # TWAP: equal distribution
            volume_profile = [0.25, 0.25, 0.25, 0.25]
    
    # Normalize volume profile
    total_profile = sum(volume_profile)
    volume_profile = [v / total_profile for v in volume_profile]
    
    schedule = []
    shares_remaining = total_shares
    
    for day in range(num_days):
        # Shares for this day (equal split for TWAP, can be weighted for VWAP)
        daily_shares = total_shares // num_days
        if day == num_days - 1:  # Last day gets remaining shares
            daily_shares = shares_remaining
        
        # Split into intraday sessions
        for session_idx, vol_weight in enumerate(volume_profile):
            session_shares = int(daily_shares * vol_weight)
            if session_idx == len(volume_profile) - 1:  # Last session of day
                # Calculate remaining shares for the day
                executed_today = sum(s['shares'] for s in schedule if s['day'] == day + 1)
                session_shares = daily_shares - executed_today
            
            if session_shares > 0:
                # Session times (EST)
                session_times = ['9:30-11:00', '11:00-13:00', '13:00-15:00', '15:00-16:00']
                session_name = session_times[session_idx] if session_idx < len(session_times) else f'Session {session_idx+1}'
                
                schedule.append({
                    'day': day + 1,
                    'session': session_idx + 1,
                    'time_window': session_name,
                    'shares': session_shares,
                    'notional': round(session_shares * price, 2),
                    'weight': round(vol_weight * 100, 1)
                })
        
        shares_remaining -= daily_shares
    
    # Calculate average daily participation
    avg_daily_participation = 0
    if adv and price > 0:
        avg_daily_dollars = position_size / num_days
        avg_daily_participation = round((avg_daily_dollars / adv) * 100, 2)
    
    return {
        'schedule': schedule,
        'total_shares': total_shares,
        'strategy_used': strategy,
        'num_days': num_days,
        'avg_daily_participation': avg_daily_participation
    }


# ============================================================================
# Liquidity Assessment
# ============================================================================

def compute_liquidity_flag(
    adv: float,
    spread_pct: float = 0.001,
    position_size: Optional[float] = None
) -> Dict:
    """
    Assess liquidity and return a flag (OK/WARN/CRITICAL).
    
    Args:
        adv: Average daily volume (dollars)
        spread_pct: Bid-ask spread (decimal)
        position_size: Intended position size (for participation calc)
    
    Returns:
        Dict with:
            - flag: 'OK', 'WARN', or 'CRITICAL'
            - reasons: List of reasons for the flag
            - metrics: Relevant liquidity metrics
    """
    reasons = []
    
    # Check ADV
    if adv < ADV_MIN_WARN:
        flag = 'CRITICAL'
        reasons.append(f'ADV ${adv/1e6:.1f}M below minimum ${ADV_MIN_WARN/1e6:.1f}M')
    elif adv < ADV_MIN_OK:
        flag = 'WARN'
        reasons.append(f'ADV ${adv/1e6:.1f}M below preferred ${ADV_MIN_OK/1e6:.1f}M')
    else:
        flag = 'OK'
    
    # Check spread
    if spread_pct > SPREAD_MAX_WARN:
        if flag == 'OK':
            flag = 'WARN'
        reasons.append(f'Spread {spread_pct*100:.2f}% exceeds {SPREAD_MAX_WARN*100:.2f}%')
    elif spread_pct > SPREAD_MAX_OK:
        if flag == 'OK':
            flag = 'WARN'
        reasons.append(f'Spread {spread_pct*100:.2f}% above preferred {SPREAD_MAX_OK*100:.2f}%')
    
    # Check participation rate if position size provided
    participation_rate = None
    if position_size and adv > 0:
        participation_rate = (position_size / adv) * 100
        if participation_rate > 20:  # More than 20% of ADV
            flag = 'CRITICAL'
            reasons.append(f'Position {participation_rate:.1f}% of ADV (max recommended: 10%)')
        elif participation_rate > 10:
            if flag == 'OK':
                flag = 'WARN'
            reasons.append(f'Position {participation_rate:.1f}% of ADV (preferred: <10%)')
    
    if not reasons:
        reasons.append('Sufficient liquidity for normal execution')
    
    return {
        'flag': flag,
        'reasons': reasons,
        'metrics': {
            'adv_dollars': adv,
            'spread_pct': spread_pct * 100,
            'participation_rate_pct': participation_rate
        }
    }


# ============================================================================
# Self-Test
# ============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("Testing trade_utils module...\n")
    
    # Test 1: Position sizing (volatility method)
    print("Test 1: Position sizing (volatility method)")
    result = compute_position_size(
        prediction=0.05,  # 5% expected return
        volatility=0.30,  # 30% volatility
        max_notional=1_000_000,  # $1M portfolio
        adv=5_000_000,  # $5M ADV
        method='volatility'
    )
    print(f"  Position: ${result['position_size_dollars']:,.0f} ({result['position_pct']:.1f}%)")
    print(f"  Method: {result['method_used']}")
    print(f"  Constraints: {', '.join(result['constraints']) if result['constraints'] else 'none'}")
    print()
    
    # Test 2: Position sizing (Kelly method)
    print("Test 2: Position sizing (Kelly method)")
    result = compute_position_size(
        prediction=0.08,
        volatility=0.25,
        max_notional=1_000_000,
        adv=5_000_000,
        method='kelly',
        win_rate=0.60,
        avg_win=0.12,
        avg_loss=0.08
    )
    print(f"  Position: ${result['position_size_dollars']:,.0f} ({result['position_pct']:.1f}%)")
    print(f"  Method: {result['method_used']}")
    print(f"  Rationale: {result['rationale']}")
    print()
    
    # Test 3: Slippage estimation
    print("Test 3: Slippage estimation")
    slippage = estimate_slippage(
        position_size=50_000,
        adv=5_000_000,
        spread_pct=0.001
    )
    print(f"  Total slippage: {slippage['slippage_bps']:.1f} bps (${slippage['slippage_dollars']:.2f})")
    print(f"  Components:")
    print(f"    Spread: {slippage['components']['spread_cost_bps']:.1f} bps")
    print(f"    Impact: {slippage['components']['market_impact_bps']:.1f} bps")
    print(f"    Base: {slippage['components']['base_slippage_bps']:.1f} bps")
    print()
    
    # Test 4: Trade schedule (TWAP)
    print("Test 4: Trade schedule (TWAP - 5 days)")
    schedule = generate_trade_schedule(
        position_size=100_000,
        price=150.0,
        num_days=5,
        strategy='TWAP',
        adv=5_000_000
    )
    print(f"  Total shares: {schedule['total_shares']:,}")
    print(f"  Strategy: {schedule['strategy_used']}")
    print(f"  Avg daily participation: {schedule['avg_daily_participation']:.2f}%")
    print(f"  Schedule ({len(schedule['schedule'])} chunks):")
    for chunk in schedule['schedule'][:4]:  # Show first 4
        print(f"    Day {chunk['day']}, {chunk['time_window']}: {chunk['shares']:,} shares (${chunk['notional']:,.0f})")
    print(f"    ... ({len(schedule['schedule'])-4} more chunks)")
    print()
    
    # Test 5: Liquidity flag
    print("Test 5: Liquidity assessment")
    # Good liquidity
    liq = compute_liquidity_flag(adv=5_000_000, spread_pct=0.0015, position_size=50_000)
    print(f"  Good case: {liq['flag']} - {liq['reasons'][0]}")
    
    # Warn case
    liq = compute_liquidity_flag(adv=700_000, spread_pct=0.004, position_size=80_000)
    print(f"  Warn case: {liq['flag']} - {'; '.join(liq['reasons'])}")
    
    # Critical case
    liq = compute_liquidity_flag(adv=400_000, spread_pct=0.008, position_size=100_000)
    print(f"  Critical case: {liq['flag']} - {'; '.join(liq['reasons'])}")
    print()
    
    print("✅ All tests completed!")

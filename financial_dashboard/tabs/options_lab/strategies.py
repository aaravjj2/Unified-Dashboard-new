"""
Options Strategy Templates Module

Provides pre-built multi-leg strategy templates:
- Vertical spreads (bull/bear call/put)
- Iron condor
- Iron butterfly
- Straddle/Strangle
- Calendar spreads
- Ratio spreads
- Covered calls
- Protective puts
- Collars
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
import pandas as pd

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """Available strategy types."""
    BULL_CALL_SPREAD = "bull_call_spread"
    BEAR_CALL_SPREAD = "bear_call_spread"
    BULL_PUT_SPREAD = "bull_put_spread"
    BEAR_PUT_SPREAD = "bear_put_spread"
    IRON_CONDOR = "iron_condor"
    IRON_BUTTERFLY = "iron_butterfly"
    LONG_STRADDLE = "long_straddle"
    SHORT_STRADDLE = "short_straddle"
    LONG_STRANGLE = "long_strangle"
    SHORT_STRANGLE = "short_strangle"
    CALENDAR_SPREAD = "calendar_spread"
    DIAGONAL_SPREAD = "diagonal_spread"
    COVERED_CALL = "covered_call"
    PROTECTIVE_PUT = "protective_put"
    COLLAR = "collar"
    RATIO_CALL_SPREAD = "ratio_call_spread"
    RATIO_PUT_SPREAD = "ratio_put_spread"
    JADE_LIZARD = "jade_lizard"
    BROKEN_WING_BUTTERFLY = "broken_wing_butterfly"


@dataclass
class StrategyLeg:
    """Single leg of a strategy."""
    option_type: str  # 'call' or 'put'
    strike: float
    expiration: str
    qty: int
    is_long: bool
    premium: float = 0.0
    symbol: str = ""


@dataclass
class StrategyTemplate:
    """Complete strategy template."""
    name: str
    strategy_type: StrategyType
    description: str
    max_profit: str
    max_loss: str
    breakeven: str
    ideal_conditions: str
    legs: List[StrategyLeg]
    net_premium: float = 0.0
    margin_required: float = 0.0


def get_strategy_description(strategy_type: StrategyType) -> Dict:
    """Get detailed description for a strategy type."""
    descriptions = {
        StrategyType.BULL_CALL_SPREAD: {
            "name": "Bull Call Spread",
            "description": "Buy a call and sell a higher strike call. Limited risk, limited reward bullish strategy.",
            "max_profit": "Strike width - net debit",
            "max_loss": "Net debit paid",
            "breakeven": "Lower strike + net debit",
            "ideal_conditions": "Moderately bullish outlook, lower IV preferred"
        },
        StrategyType.BEAR_CALL_SPREAD: {
            "name": "Bear Call Spread",
            "description": "Sell a call and buy a higher strike call. Credit spread for bearish outlook.",
            "max_profit": "Net credit received",
            "max_loss": "Strike width - net credit",
            "breakeven": "Lower strike + net credit",
            "ideal_conditions": "Neutral to bearish, high IV preferred"
        },
        StrategyType.BULL_PUT_SPREAD: {
            "name": "Bull Put Spread",
            "description": "Sell a put and buy a lower strike put. Credit spread for bullish outlook.",
            "max_profit": "Net credit received",
            "max_loss": "Strike width - net credit",
            "breakeven": "Higher strike - net credit",
            "ideal_conditions": "Neutral to bullish, high IV preferred"
        },
        StrategyType.BEAR_PUT_SPREAD: {
            "name": "Bear Put Spread",
            "description": "Buy a put and sell a lower strike put. Debit spread for bearish outlook.",
            "max_profit": "Strike width - net debit",
            "max_loss": "Net debit paid",
            "breakeven": "Higher strike - net debit",
            "ideal_conditions": "Moderately bearish, lower IV preferred"
        },
        StrategyType.IRON_CONDOR: {
            "name": "Iron Condor",
            "description": "Sell OTM call and put spreads. Profit from low volatility and range-bound price.",
            "max_profit": "Net credit received",
            "max_loss": "Strike width - net credit",
            "breakeven": "Upper short strike + credit, Lower short strike - credit",
            "ideal_conditions": "Low volatility expected, range-bound market"
        },
        StrategyType.IRON_BUTTERFLY: {
            "name": "Iron Butterfly",
            "description": "Sell ATM straddle, buy OTM strangle. Higher reward than condor but narrower profit zone.",
            "max_profit": "Net credit received",
            "max_loss": "Strike width - net credit",
            "breakeven": "ATM strike ± net credit",
            "ideal_conditions": "Very low volatility expected, pinning at strike"
        },
        StrategyType.LONG_STRADDLE: {
            "name": "Long Straddle",
            "description": "Buy ATM call and put same strike. Profit from big moves in either direction.",
            "max_profit": "Unlimited",
            "max_loss": "Total premium paid",
            "breakeven": "Strike ± total premium",
            "ideal_conditions": "High volatility expected, big move anticipated"
        },
        StrategyType.SHORT_STRADDLE: {
            "name": "Short Straddle",
            "description": "Sell ATM call and put. Profit from range-bound price. Unlimited risk.",
            "max_profit": "Total premium received",
            "max_loss": "Unlimited",
            "breakeven": "Strike ± total premium",
            "ideal_conditions": "Low volatility expected, price staying flat"
        },
        StrategyType.LONG_STRANGLE: {
            "name": "Long Strangle",
            "description": "Buy OTM call and OTM put. Cheaper than straddle but needs bigger move.",
            "max_profit": "Unlimited",
            "max_loss": "Total premium paid",
            "breakeven": "Put strike - premium, Call strike + premium",
            "ideal_conditions": "Very high volatility expected"
        },
        StrategyType.SHORT_STRANGLE: {
            "name": "Short Strangle",
            "description": "Sell OTM call and OTM put. Wider profit zone than short straddle.",
            "max_profit": "Total premium received",
            "max_loss": "Unlimited",
            "breakeven": "Put strike - premium, Call strike + premium",
            "ideal_conditions": "Low volatility expected"
        },
        StrategyType.COVERED_CALL: {
            "name": "Covered Call",
            "description": "Long stock + sell OTM call. Generate income on existing position.",
            "max_profit": "Call premium + (strike - stock price)",
            "max_loss": "Stock price - premium",
            "breakeven": "Stock price - premium received",
            "ideal_conditions": "Neutral to slightly bullish"
        },
        StrategyType.PROTECTIVE_PUT: {
            "name": "Protective Put",
            "description": "Long stock + buy OTM put. Insurance against downside.",
            "max_profit": "Unlimited (minus put premium)",
            "max_loss": "Stock price - strike + premium",
            "breakeven": "Stock price + premium paid",
            "ideal_conditions": "Long-term bullish, want protection"
        },
        StrategyType.COLLAR: {
            "name": "Collar",
            "description": "Long stock + protective put + covered call. Limited risk and reward.",
            "max_profit": "Call strike - stock price + net credit/debit",
            "max_loss": "Stock price - put strike - net credit/debit",
            "breakeven": "Stock price adjusted for net premium",
            "ideal_conditions": "Want to protect gains, willing to cap upside"
        },
        StrategyType.CALENDAR_SPREAD: {
            "name": "Calendar Spread",
            "description": "Sell near-term option, buy longer-term same strike. Profit from time decay.",
            "max_profit": "Varies with IV and price",
            "max_loss": "Net debit paid",
            "breakeven": "Complex - depends on IV",
            "ideal_conditions": "Expect price to stay near strike"
        },
        StrategyType.JADE_LIZARD: {
            "name": "Jade Lizard",
            "description": "Short put + short call spread. No upside risk if premium > call spread width.",
            "max_profit": "Net credit received",
            "max_loss": "Put strike - credit (downside only if properly structured)",
            "breakeven": "Put strike - net credit",
            "ideal_conditions": "Neutral to bullish, high IV"
        }
    }
    
    return descriptions.get(strategy_type, {
        "name": strategy_type.value,
        "description": "Custom strategy",
        "max_profit": "Varies",
        "max_loss": "Varies",
        "breakeven": "Varies",
        "ideal_conditions": "Varies"
    })


def build_bull_call_spread(
    chain_data: Dict,
    expiration: str,
    lower_strike: float,
    upper_strike: float,
    qty: int = 1
) -> StrategyTemplate:
    """
    Build bull call spread template.
    
    Args:
        chain_data: Options chain data
        expiration: Expiration date
        lower_strike: Long call strike (buy)
        upper_strike: Short call strike (sell)
        qty: Number of spreads
        
    Returns:
        StrategyTemplate
    """
    chains = chain_data.get('chains', {})
    chain = chains.get(expiration, {})
    calls = {c['strike']: c for c in chain.get('calls', [])}
    
    long_call = calls.get(lower_strike, {})
    short_call = calls.get(upper_strike, {})
    
    long_premium = long_call.get('ask', long_call.get('lastPrice', 0))
    short_premium = short_call.get('bid', short_call.get('lastPrice', 0))
    
    net_debit = long_premium - short_premium
    
    desc = get_strategy_description(StrategyType.BULL_CALL_SPREAD)
    
    legs = [
        StrategyLeg(
            option_type='call',
            strike=lower_strike,
            expiration=expiration,
            qty=qty,
            is_long=True,
            premium=long_premium,
            symbol=long_call.get('symbol', '')
        ),
        StrategyLeg(
            option_type='call',
            strike=upper_strike,
            expiration=expiration,
            qty=qty,
            is_long=False,
            premium=short_premium,
            symbol=short_call.get('symbol', '')
        )
    ]
    
    return StrategyTemplate(
        name=desc['name'],
        strategy_type=StrategyType.BULL_CALL_SPREAD,
        description=desc['description'],
        max_profit=f"${(upper_strike - lower_strike - net_debit) * qty * 100:,.0f}",
        max_loss=f"${net_debit * qty * 100:,.0f}",
        breakeven=f"${lower_strike + net_debit:.2f}",
        ideal_conditions=desc['ideal_conditions'],
        legs=legs,
        net_premium=-net_debit * qty * 100,
        margin_required=0  # Defined risk spread
    )


def build_bear_put_spread(
    chain_data: Dict,
    expiration: str,
    upper_strike: float,
    lower_strike: float,
    qty: int = 1
) -> StrategyTemplate:
    """Build bear put spread template."""
    chains = chain_data.get('chains', {})
    chain = chains.get(expiration, {})
    puts = {p['strike']: p for p in chain.get('puts', [])}
    
    long_put = puts.get(upper_strike, {})
    short_put = puts.get(lower_strike, {})
    
    long_premium = long_put.get('ask', long_put.get('lastPrice', 0))
    short_premium = short_put.get('bid', short_put.get('lastPrice', 0))
    
    net_debit = long_premium - short_premium
    
    desc = get_strategy_description(StrategyType.BEAR_PUT_SPREAD)
    
    legs = [
        StrategyLeg(
            option_type='put',
            strike=upper_strike,
            expiration=expiration,
            qty=qty,
            is_long=True,
            premium=long_premium,
            symbol=long_put.get('symbol', '')
        ),
        StrategyLeg(
            option_type='put',
            strike=lower_strike,
            expiration=expiration,
            qty=qty,
            is_long=False,
            premium=short_premium,
            symbol=short_put.get('symbol', '')
        )
    ]
    
    return StrategyTemplate(
        name=desc['name'],
        strategy_type=StrategyType.BEAR_PUT_SPREAD,
        description=desc['description'],
        max_profit=f"${(upper_strike - lower_strike - net_debit) * qty * 100:,.0f}",
        max_loss=f"${net_debit * qty * 100:,.0f}",
        breakeven=f"${upper_strike - net_debit:.2f}",
        ideal_conditions=desc['ideal_conditions'],
        legs=legs,
        net_premium=-net_debit * qty * 100
    )


def build_iron_condor(
    chain_data: Dict,
    expiration: str,
    put_long_strike: float,
    put_short_strike: float,
    call_short_strike: float,
    call_long_strike: float,
    qty: int = 1
) -> StrategyTemplate:
    """Build iron condor template."""
    chains = chain_data.get('chains', {})
    chain = chains.get(expiration, {})
    calls = {c['strike']: c for c in chain.get('calls', [])}
    puts = {p['strike']: p for p in chain.get('puts', [])}
    
    put_long = puts.get(put_long_strike, {})
    put_short = puts.get(put_short_strike, {})
    call_short = calls.get(call_short_strike, {})
    call_long = calls.get(call_long_strike, {})
    
    # Calculate premiums
    put_credit = put_short.get('bid', 0) - put_long.get('ask', 0)
    call_credit = call_short.get('bid', 0) - call_long.get('ask', 0)
    net_credit = put_credit + call_credit
    
    desc = get_strategy_description(StrategyType.IRON_CONDOR)
    
    legs = [
        StrategyLeg('put', put_long_strike, expiration, qty, True, put_long.get('ask', 0)),
        StrategyLeg('put', put_short_strike, expiration, qty, False, put_short.get('bid', 0)),
        StrategyLeg('call', call_short_strike, expiration, qty, False, call_short.get('bid', 0)),
        StrategyLeg('call', call_long_strike, expiration, qty, True, call_long.get('ask', 0))
    ]
    
    wing_width = max(put_short_strike - put_long_strike, call_long_strike - call_short_strike)
    
    return StrategyTemplate(
        name=desc['name'],
        strategy_type=StrategyType.IRON_CONDOR,
        description=desc['description'],
        max_profit=f"${net_credit * qty * 100:,.0f}",
        max_loss=f"${(wing_width - net_credit) * qty * 100:,.0f}",
        breakeven=f"${put_short_strike - net_credit:.2f} / ${call_short_strike + net_credit:.2f}",
        ideal_conditions=desc['ideal_conditions'],
        legs=legs,
        net_premium=net_credit * qty * 100
    )


def build_iron_butterfly(
    chain_data: Dict,
    expiration: str,
    atm_strike: float,
    wing_width: float,
    qty: int = 1
) -> StrategyTemplate:
    """Build iron butterfly template."""
    chains = chain_data.get('chains', {})
    chain = chains.get(expiration, {})
    calls = {c['strike']: c for c in chain.get('calls', [])}
    puts = {p['strike']: p for p in chain.get('puts', [])}
    
    put_long_strike = atm_strike - wing_width
    call_long_strike = atm_strike + wing_width
    
    put_long = puts.get(put_long_strike, {})
    put_short = puts.get(atm_strike, {})
    call_short = calls.get(atm_strike, {})
    call_long = calls.get(call_long_strike, {})
    
    net_credit = (
        put_short.get('bid', 0) - put_long.get('ask', 0) +
        call_short.get('bid', 0) - call_long.get('ask', 0)
    )
    
    desc = get_strategy_description(StrategyType.IRON_BUTTERFLY)
    
    legs = [
        StrategyLeg('put', put_long_strike, expiration, qty, True, put_long.get('ask', 0)),
        StrategyLeg('put', atm_strike, expiration, qty, False, put_short.get('bid', 0)),
        StrategyLeg('call', atm_strike, expiration, qty, False, call_short.get('bid', 0)),
        StrategyLeg('call', call_long_strike, expiration, qty, True, call_long.get('ask', 0))
    ]
    
    return StrategyTemplate(
        name=desc['name'],
        strategy_type=StrategyType.IRON_BUTTERFLY,
        description=desc['description'],
        max_profit=f"${net_credit * qty * 100:,.0f}",
        max_loss=f"${(wing_width - net_credit) * qty * 100:,.0f}",
        breakeven=f"${atm_strike - net_credit:.2f} / ${atm_strike + net_credit:.2f}",
        ideal_conditions=desc['ideal_conditions'],
        legs=legs,
        net_premium=net_credit * qty * 100
    )


def build_long_straddle(
    chain_data: Dict,
    expiration: str,
    strike: float,
    qty: int = 1
) -> StrategyTemplate:
    """Build long straddle template."""
    chains = chain_data.get('chains', {})
    chain = chains.get(expiration, {})
    calls = {c['strike']: c for c in chain.get('calls', [])}
    puts = {p['strike']: p for p in chain.get('puts', [])}
    
    call = calls.get(strike, {})
    put = puts.get(strike, {})
    
    call_premium = call.get('ask', call.get('lastPrice', 0))
    put_premium = put.get('ask', put.get('lastPrice', 0))
    total_premium = call_premium + put_premium
    
    desc = get_strategy_description(StrategyType.LONG_STRADDLE)
    
    legs = [
        StrategyLeg('call', strike, expiration, qty, True, call_premium),
        StrategyLeg('put', strike, expiration, qty, True, put_premium)
    ]
    
    return StrategyTemplate(
        name=desc['name'],
        strategy_type=StrategyType.LONG_STRADDLE,
        description=desc['description'],
        max_profit="Unlimited",
        max_loss=f"${total_premium * qty * 100:,.0f}",
        breakeven=f"${strike - total_premium:.2f} / ${strike + total_premium:.2f}",
        ideal_conditions=desc['ideal_conditions'],
        legs=legs,
        net_premium=-total_premium * qty * 100
    )


def build_long_strangle(
    chain_data: Dict,
    expiration: str,
    put_strike: float,
    call_strike: float,
    qty: int = 1
) -> StrategyTemplate:
    """Build long strangle template."""
    chains = chain_data.get('chains', {})
    chain = chains.get(expiration, {})
    calls = {c['strike']: c for c in chain.get('calls', [])}
    puts = {p['strike']: p for p in chain.get('puts', [])}
    
    call = calls.get(call_strike, {})
    put = puts.get(put_strike, {})
    
    call_premium = call.get('ask', call.get('lastPrice', 0))
    put_premium = put.get('ask', put.get('lastPrice', 0))
    total_premium = call_premium + put_premium
    
    desc = get_strategy_description(StrategyType.LONG_STRANGLE)
    
    legs = [
        StrategyLeg('put', put_strike, expiration, qty, True, put_premium),
        StrategyLeg('call', call_strike, expiration, qty, True, call_premium)
    ]
    
    return StrategyTemplate(
        name=desc['name'],
        strategy_type=StrategyType.LONG_STRANGLE,
        description=desc['description'],
        max_profit="Unlimited",
        max_loss=f"${total_premium * qty * 100:,.0f}",
        breakeven=f"${put_strike - total_premium:.2f} / ${call_strike + total_premium:.2f}",
        ideal_conditions=desc['ideal_conditions'],
        legs=legs,
        net_premium=-total_premium * qty * 100
    )


def suggest_strategies(
    chain_data: Dict,
    outlook: str = "neutral",
    risk_tolerance: str = "moderate",
    account_value: float = 100000
) -> List[Dict]:
    """
    Suggest appropriate strategies based on market outlook and risk tolerance.
    
    Args:
        chain_data: Options chain data
        outlook: 'bullish', 'bearish', 'neutral', 'volatile'
        risk_tolerance: 'low', 'moderate', 'high'
        account_value: Account value for position sizing
        
    Returns:
        List of strategy suggestions with reasoning
    """
    suggestions = []
    
    spot_price = chain_data.get('spot_price', 100)
    chains = chain_data.get('chains', {})
    
    if not chains:
        return []
    
    # Get first expiration for demo
    first_exp = sorted(chains.keys())[0]
    chain = chains[first_exp]
    
    calls = chain.get('calls', [])
    puts = chain.get('puts', [])
    
    if not calls or not puts:
        return []
    
    # Find ATM strike
    strikes = [c['strike'] for c in calls]
    atm_strike = min(strikes, key=lambda x: abs(x - spot_price))
    atm_idx = strikes.index(atm_strike)
    
    if outlook == "bullish":
        if risk_tolerance == "low":
            suggestions.append({
                "strategy": "Bull Call Spread",
                "type": StrategyType.BULL_CALL_SPREAD,
                "reasoning": "Limited risk bullish play with defined max loss",
                "strikes": [atm_strike, strikes[min(atm_idx + 2, len(strikes)-1)]],
                "expiration": first_exp
            })
            suggestions.append({
                "strategy": "Bull Put Spread",
                "type": StrategyType.BULL_PUT_SPREAD,
                "reasoning": "Credit spread benefits from theta decay while bullish",
                "strikes": [strikes[max(0, atm_idx - 2)], atm_strike],
                "expiration": first_exp
            })
        elif risk_tolerance == "high":
            suggestions.append({
                "strategy": "Long Call",
                "type": None,
                "reasoning": "Maximum bullish exposure with leverage",
                "strikes": [atm_strike],
                "expiration": first_exp
            })
    
    elif outlook == "bearish":
        if risk_tolerance == "low":
            suggestions.append({
                "strategy": "Bear Put Spread",
                "type": StrategyType.BEAR_PUT_SPREAD,
                "reasoning": "Limited risk bearish play with defined max loss",
                "strikes": [strikes[max(0, atm_idx - 2)], atm_strike],
                "expiration": first_exp
            })
            suggestions.append({
                "strategy": "Bear Call Spread",
                "type": StrategyType.BEAR_CALL_SPREAD,
                "reasoning": "Credit spread profits from bearish/neutral action",
                "strikes": [atm_strike, strikes[min(atm_idx + 2, len(strikes)-1)]],
                "expiration": first_exp
            })
    
    elif outlook == "neutral":
        suggestions.append({
            "strategy": "Iron Condor",
            "type": StrategyType.IRON_CONDOR,
            "reasoning": "Profit from low volatility and range-bound price",
            "strikes": [
                strikes[max(0, atm_idx - 3)],
                strikes[max(0, atm_idx - 1)],
                strikes[min(atm_idx + 1, len(strikes)-1)],
                strikes[min(atm_idx + 3, len(strikes)-1)]
            ],
            "expiration": first_exp
        })
        suggestions.append({
            "strategy": "Iron Butterfly",
            "type": StrategyType.IRON_BUTTERFLY,
            "reasoning": "Higher reward if price pins at ATM strike",
            "strikes": [atm_strike],
            "wing_width": strikes[1] - strikes[0] if len(strikes) > 1 else 5,
            "expiration": first_exp
        })
    
    elif outlook == "volatile":
        suggestions.append({
            "strategy": "Long Straddle",
            "type": StrategyType.LONG_STRADDLE,
            "reasoning": "Profit from big moves in either direction",
            "strikes": [atm_strike],
            "expiration": first_exp
        })
        suggestions.append({
            "strategy": "Long Strangle",
            "type": StrategyType.LONG_STRANGLE,
            "reasoning": "Cheaper than straddle, needs bigger move",
            "strikes": [
                strikes[max(0, atm_idx - 2)],
                strikes[min(atm_idx + 2, len(strikes)-1)]
            ],
            "expiration": first_exp
        })
    
    return suggestions


def calculate_strategy_greeks(strategy: StrategyTemplate) -> Dict[str, float]:
    """
    Calculate aggregate Greeks for a strategy.
    
    Args:
        strategy: StrategyTemplate with legs
        
    Returns:
        Dict with aggregate Greeks
    """
    total_delta = 0
    total_gamma = 0
    total_theta = 0
    total_vega = 0
    
    for leg in strategy.legs:
        multiplier = leg.qty * 100 * (1 if leg.is_long else -1)
        # These would come from the option data
        # For now return placeholder
        total_delta += 0.5 * multiplier if leg.option_type == 'call' else -0.5 * multiplier
    
    return {
        "delta": total_delta,
        "gamma": total_gamma,
        "theta": total_theta,
        "vega": total_vega
    }

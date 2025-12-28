"""
AlphaSim Options - Historical and synthetic options data.

Provides HISTORICAL_OPTIONS endpoint functionality using:
1. Cached options data (if available)
2. Synthetic options chains (fallback for unsupported tickers)
"""
import os
import hashlib
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import random

from .cache import get_cache, CacheTTL


def _black_scholes_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Calculate Black-Scholes call option price.
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate
        sigma: Volatility
    
    Returns:
        Call option price
    """
    if T <= 0:
        return max(S - K, 0)
    
    from math import log, sqrt, exp
    
    try:
        d1 = (log(S / K) + (r + sigma**2 / 2) * T) / (sigma * sqrt(T))
        d2 = d1 - sigma * sqrt(T)
        
        # Approximate normal CDF
        def norm_cdf(x):
            return (1 + math.erf(x / math.sqrt(2))) / 2
        
        call_price = S * norm_cdf(d1) - K * exp(-r * T) * norm_cdf(d2)
        return max(call_price, 0.01)
    except (ValueError, ZeroDivisionError):
        return max(S - K, 0.01)


def _black_scholes_put(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Calculate Black-Scholes put option price using put-call parity.
    """
    call = _black_scholes_call(S, K, T, r, sigma)
    put = call - S + K * math.exp(-r * T)
    return max(put, 0.01)


def _generate_synthetic_chain(
    symbol: str,
    current_price: float,
    expiration_date: datetime,
    volatility: float = 0.3,
    risk_free_rate: float = 0.05
) -> List[Dict[str, Any]]:
    """
    Generate a synthetic options chain using Black-Scholes pricing.
    
    Args:
        symbol: Ticker symbol
        current_price: Current stock price
        expiration_date: Option expiration date
        volatility: Implied volatility (default 30%)
        risk_free_rate: Risk-free interest rate (default 5%)
    
    Returns:
        List of option contract dicts
    """
    now = datetime.utcnow()
    T = max((expiration_date - now).days / 365.0, 0.001)
    
    # Generate strikes around current price
    base_strike = round(current_price / 5) * 5  # Round to nearest 5
    strikes = [base_strike + i * 5 for i in range(-5, 6)]  # 11 strikes
    
    contracts = []
    
    for strike in strikes:
        if strike <= 0:
            continue
        
        # Calculate theoretical prices
        call_price = _black_scholes_call(current_price, strike, T, risk_free_rate, volatility)
        put_price = _black_scholes_put(current_price, strike, T, risk_free_rate, volatility)
        
        # Add some bid-ask spread
        spread_pct = 0.05 + 0.02 * abs(strike - current_price) / current_price
        
        # Call contract
        contracts.append({
            "contractSymbol": f"{symbol}{expiration_date.strftime('%y%m%d')}C{int(strike*1000):08d}",
            "strike": strike,
            "type": "call",
            "expiration": expiration_date.strftime("%Y-%m-%d"),
            "bid": round(call_price * (1 - spread_pct), 2),
            "ask": round(call_price * (1 + spread_pct), 2),
            "lastPrice": round(call_price, 2),
            "volume": max(1, int(1000 * math.exp(-abs(strike - current_price) / current_price / 0.1))),
            "openInterest": max(10, int(5000 * math.exp(-abs(strike - current_price) / current_price / 0.15))),
            "impliedVolatility": round(volatility + random.uniform(-0.05, 0.05), 4),
            "inTheMoney": strike < current_price
        })
        
        # Put contract
        contracts.append({
            "contractSymbol": f"{symbol}{expiration_date.strftime('%y%m%d')}P{int(strike*1000):08d}",
            "strike": strike,
            "type": "put",
            "expiration": expiration_date.strftime("%Y-%m-%d"),
            "bid": round(put_price * (1 - spread_pct), 2),
            "ask": round(put_price * (1 + spread_pct), 2),
            "lastPrice": round(put_price, 2),
            "volume": max(1, int(800 * math.exp(-abs(strike - current_price) / current_price / 0.1))),
            "openInterest": max(10, int(4000 * math.exp(-abs(strike - current_price) / current_price / 0.15))),
            "impliedVolatility": round(volatility + random.uniform(-0.05, 0.05), 4),
            "inTheMoney": strike > current_price
        })
    
    return contracts


def _get_current_price(symbol: str) -> float:
    """
    Get current stock price for synthetic options generation.
    """
    # Try to use the engine to get real price
    try:
        from .engine import get_engine
        engine = get_engine()
        result = engine.time_series_daily(symbol, "compact")
        
        if "Time Series (Daily)" in result:
            dates = sorted(result["Time Series (Daily)"].keys(), reverse=True)
            if dates:
                latest = result["Time Series (Daily)"][dates[0]]
                return float(latest.get("4. close", 100))
    except Exception:
        pass
    
    # Fallback: generate deterministic price based on symbol hash
    symbol_hash = int(hashlib.md5(symbol.encode()).hexdigest(), 16)
    random.seed(symbol_hash)
    return round(random.uniform(50, 500), 2)


def _get_expiration_dates(base_date: Optional[datetime] = None) -> List[datetime]:
    """
    Generate standard options expiration dates (third Friday of each month).
    """
    if base_date is None:
        base_date = datetime.utcnow()
    
    expirations = []
    
    # Find next 6 monthly expirations
    current = base_date.replace(day=1)
    
    for _ in range(6):
        # Find third Friday
        first_day = current.replace(day=1)
        # Days until Friday (4)
        days_until_friday = (4 - first_day.weekday()) % 7
        first_friday = first_day + timedelta(days=days_until_friday)
        third_friday = first_friday + timedelta(weeks=2)
        
        if third_friday > base_date:
            expirations.append(third_friday)
        
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    # Add weekly expirations for the next 4 weeks
    next_friday = base_date + timedelta(days=(4 - base_date.weekday()) % 7)
    if next_friday == base_date:
        next_friday += timedelta(weeks=1)
    
    for i in range(4):
        weekly = next_friday + timedelta(weeks=i)
        if weekly not in expirations:
            expirations.append(weekly)
    
    return sorted(expirations)


def get_options_chain(
    symbol: str,
    expiration: Optional[str] = None,
    option_type: Optional[str] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Get options chain for a symbol.
    
    Args:
        symbol: Ticker symbol
        expiration: Specific expiration date (YYYY-MM-DD) or None for all
        option_type: 'call', 'put', or None for both
        use_cache: Whether to use caching
    
    Returns:
        AlphaV-compatible HISTORICAL_OPTIONS response
    """
    cache = get_cache()
    cache_key = f"options_chain:{symbol}:{expiration}:{option_type}"
    
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
    
    # Get current price
    current_price = _get_current_price(symbol)
    
    # Get expiration dates
    exp_dates = _get_expiration_dates()
    
    # If specific expiration requested, filter
    if expiration:
        try:
            target_exp = datetime.strptime(expiration, "%Y-%m-%d")
            # Find closest expiration
            exp_dates = [min(exp_dates, key=lambda x: abs((x - target_exp).days))]
        except ValueError:
            pass
    
    # Generate chains for each expiration
    all_contracts = []
    volatility = 0.25 + (hash(symbol) % 20) / 100  # 25-45% volatility
    
    for exp_date in exp_dates:
        random.seed(hash(symbol) + exp_date.toordinal())  # Deterministic
        contracts = _generate_synthetic_chain(
            symbol,
            current_price,
            exp_date,
            volatility=volatility
        )
        
        # Filter by type if specified
        if option_type:
            contracts = [c for c in contracts if c["type"] == option_type.lower()]
        
        all_contracts.extend(contracts)
    
    # Build response
    result = build_options_response(symbol, current_price, all_contracts, exp_dates)
    
    # Cache result
    if use_cache:
        cache.set(cache_key, result, ttl=CacheTTL.OPTIONS)
    
    return result


def build_options_response(
    symbol: str,
    current_price: float,
    contracts: List[Dict[str, Any]],
    expiration_dates: List[datetime]
) -> Dict[str, Any]:
    """
    Build AlphaV-compatible HISTORICAL_OPTIONS response.
    """
    from .schema import build_meta_data
    
    # Group contracts by expiration
    chains_by_expiration = {}
    for contract in contracts:
        exp = contract.get("expiration")
        if exp not in chains_by_expiration:
            chains_by_expiration[exp] = {"calls": [], "puts": []}
        
        if contract.get("type") == "call":
            chains_by_expiration[exp]["calls"].append(contract)
        else:
            chains_by_expiration[exp]["puts"].append(contract)
    
    return {
        "Meta Data": build_meta_data(
            "Historical Options (AlphaSim)",
            symbol,
            extra={
                "Underlying Price": str(current_price),
                "Data Source": "Synthetic"
            }
        ),
        "optionChain": {
            "symbol": symbol.upper(),
            "underlyingPrice": current_price,
            "expirationDates": [d.strftime("%Y-%m-%d") for d in expiration_dates],
            "options": [
                {
                    "expirationDate": exp,
                    "calls": chains_by_expiration.get(exp, {}).get("calls", []),
                    "puts": chains_by_expiration.get(exp, {}).get("puts", [])
                }
                for exp in sorted(chains_by_expiration.keys())
            ]
        }
    }


def get_option_quote(
    symbol: str,
    strike: float,
    expiration: str,
    option_type: str = "call"
) -> Dict[str, Any]:
    """
    Get quote for a specific option contract.
    
    Args:
        symbol: Underlying ticker symbol
        strike: Strike price
        expiration: Expiration date (YYYY-MM-DD)
        option_type: 'call' or 'put'
    
    Returns:
        Single option contract details
    """
    chain = get_options_chain(symbol, expiration, option_type)
    
    if "optionChain" not in chain:
        from .schema import build_error_response
        return build_error_response(f"Unable to fetch options for {symbol}")
    
    # Find matching contract
    for option_data in chain["optionChain"].get("options", []):
        contracts = option_data.get("calls" if option_type == "call" else "puts", [])
        for contract in contracts:
            if abs(contract.get("strike", 0) - strike) < 0.01:
                return {
                    "Meta Data": chain["Meta Data"],
                    "contract": contract
                }
    
    from .schema import build_error_response
    return build_error_response(
        f"Option contract not found: {symbol} {strike} {option_type} {expiration}"
    )

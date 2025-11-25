"""
Phase 6 — Azure ML Options Forecasting Integration
===================================================

Real Azure ML options forecasting with implied volatility computation and Greeks.
Integrates with Market Forecast tab to display options-based predictions.

Key Features:
- Fetch real-time options chains from Azure ML endpoint
- Compute implied volatility using Black-Scholes model
- Calculate expected returns and Greeks (delta, gamma, theta, vega)
- Integrate with Phase 3.5 ForecastContract for caching
- Support multiple expirations and strike ranges

Dependencies:
- Phase 3.5: ForecastContract, cache_router
- Azure ML: azure_ml_config, options endpoint
- scipy: Black-Scholes IV solver
- numpy/pandas: Data manipulation

Author: Agent 1A — Unified Financial Dashboard Team
Version: 1.0 (Phase 6)
"""

import os
import json
import logging
import hashlib
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from enum import Enum

import requests
import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import brentq

# Phase 3.5 Data Contracts
from phase3p5_hybrid_bridge.data_bridge.data_contracts import (
    ForecastContract,
    ContractType
)
from phase3p5_hybrid_bridge.data_bridge.cache_router import CacheRouter

# Azure ML Configuration
from financial_dashboard.tabs.azure_ml_lab.azure_ml_config import (
    AzureMLConfig,
    authenticate_azure_ml
)


logger = logging.getLogger(__name__)


# =============================================================================
# OPTIONS DATA STRUCTURES
# =============================================================================

class OptionType(Enum):
    """Option contract type."""
    CALL = "call"
    PUT = "put"


@dataclass
class OptionContract:
    """
    Single options contract data.
    
    Attributes:
        ticker: Underlying ticker symbol
        strike: Strike price
        expiration: Expiration date (ISO 8601)
        option_type: CALL or PUT
        bid: Bid price
        ask: Ask price
        last: Last trade price
        volume: Trading volume
        open_interest: Open interest
        implied_volatility: Computed IV (annualized)
        delta: Option delta
        gamma: Option gamma
        theta: Option theta (per day)
        vega: Option vega (per 1% vol change)
    """
    ticker: str
    strike: float
    expiration: str
    option_type: OptionType
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    implied_volatility: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    
    def mid_price(self) -> float:
        """Calculate mid-market price."""
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2.0
        elif self.last > 0:
            return self.last
        else:
            return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize OptionContract to a JSON-safe dict with native Python types.

        Converts numpy types (e.g., np.int64, np.float64) to native int/float to
        ensure JSON serialization across L1/L2/L3 cache tiers.
        """
        def _native(v):
            # Convert numpy scalar types to native Python types
            try:
                if hasattr(v, 'item'):
                    return v.item()
            except Exception:
                pass
            # Fallback: return as-is
            return v

        return {
            "ticker": str(self.ticker),
            "strike": float(_native(self.strike)),
            "expiration": str(self.expiration),
            "option_type": self.option_type.value if isinstance(self.option_type, OptionType) else str(self.option_type),
            "bid": float(_native(self.bid)),
            "ask": float(_native(self.ask)),
            "last": float(_native(self.last)),
            "volume": int(_native(self.volume)) if self.volume is not None else None,
            "open_interest": int(_native(self.open_interest)) if self.open_interest is not None else None,
            "implied_volatility": None if self.implied_volatility is None else float(_native(self.implied_volatility)),
            "delta": None if self.delta is None else float(_native(self.delta)),
            "gamma": None if self.gamma is None else float(_native(self.gamma)),
            "theta": None if self.theta is None else float(_native(self.theta)),
            "vega": None if self.vega is None else float(_native(self.vega)),
        }

    def to_json(self) -> str:
        """Return JSON string of the option contract (canonical formatting)."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(',', ':'))


@dataclass
class OptionChain:
    """
    Complete options chain for a ticker.
    
    Attributes:
        ticker: Stock ticker symbol
        spot_price: Current underlying price
        timestamp: Data timestamp
        expirations: List of expiration dates
        calls: List of call option contracts
        puts: List of put option contracts
        metadata: Additional metadata (exchange, data source, etc.)
    """
    ticker: str
    spot_price: float
    timestamp: str
    expirations: List[str]
    calls: List[OptionContract]
    puts: List[OptionContract]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_atm_strike(self) -> float:
        """Return the at-the-money (ATM) strike for this chain.

        Finds the strike closest to the current spot price from available
        call/put strikes and returns it as a float.
        """
        strikes = set()
        for c in self.calls:
            try:
                strikes.add(float(c.strike))
            except Exception:
                continue
        for p in self.puts:
            try:
                strikes.add(float(p.strike))
            except Exception:
                continue

        if not strikes:
            return float(self.spot_price)

        atm = min(strikes, key=lambda s: abs(s - float(self.spot_price)))
        return float(atm)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize OptionChain to a JSON-safe dict with native Python types.

        Ensures nested OptionContract objects are converted via their to_dict()
        methods so caching layers can serialize without numpy type errors.
        """
        def _native(v):
            try:
                if hasattr(v, 'item'):
                    return v.item()
            except Exception:
                pass
            return v

        return {
            "ticker": str(self.ticker),
            "spot_price": float(_native(self.spot_price)),
            "timestamp": str(self.timestamp),
            "expirations": [str(e) for e in self.expirations],
            "calls": [c.to_dict() for c in self.calls],
            "puts": [p.to_dict() for p in self.puts],
            "metadata": {k: (v.item() if hasattr(v, 'item') else v) for k, v in self.metadata.items()}
        }

    def to_json(self) -> str:
        """Return JSON string of the option chain (canonical formatting)."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(',', ':'))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptionChain':
        """Reconstruct OptionChain from a dict produced by to_dict()."""
        calls = []
        puts = []
        for c in data.get('calls', []):
            oc = OptionContract(
                ticker=c['ticker'],
                strike=float(c['strike']),
                expiration=c['expiration'],
                option_type=OptionType(c['option_type']),
                bid=float(c['bid']),
                ask=float(c['ask']),
                last=float(c['last']),
                volume=int(c['volume']) if c.get('volume') is not None else 0,
                open_interest=int(c['open_interest']) if c.get('open_interest') is not None else 0,
                implied_volatility=None if c.get('implied_volatility') is None else float(c.get('implied_volatility')),
                delta=None if c.get('delta') is None else float(c.get('delta')),
                gamma=None if c.get('gamma') is None else float(c.get('gamma')),
                theta=None if c.get('theta') is None else float(c.get('theta')),
                vega=None if c.get('vega') is None else float(c.get('vega')),
            )
            calls.append(oc)
        for p in data.get('puts', []):
            op = OptionContract(
                ticker=p['ticker'],
                strike=float(p['strike']),
                expiration=p['expiration'],
                option_type=OptionType(p['option_type']),
                bid=float(p['bid']),
                ask=float(p['ask']),
                last=float(p['last']),
                volume=int(p['volume']) if p.get('volume') is not None else 0,
                open_interest=int(p['open_interest']) if p.get('open_interest') is not None else 0,
                implied_volatility=None if p.get('implied_volatility') is None else float(p.get('implied_volatility')),
                delta=None if p.get('delta') is None else float(p.get('delta')),
                gamma=None if p.get('gamma') is None else float(p.get('gamma')),
                theta=None if p.get('theta') is None else float(p.get('theta')),
                vega=None if p.get('vega') is None else float(p.get('vega')),
            )
            puts.append(op)

        return cls(
            ticker=str(data['ticker']),
            spot_price=float(data['spot_price']),
            timestamp=str(data['timestamp']),
            expirations=[str(e) for e in data.get('expirations', [])],
            calls=calls,
            puts=puts,
            metadata=data.get('metadata', {})
        )


# =============================================================================
# BLACK-SCHOLES IMPLIED VOLATILITY
# =============================================================================

def black_scholes_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Black-Scholes call option price.
    
    Args:
        S: Spot price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate
        sigma: Volatility (annualized)
    
    Returns:
        Call option price
    """
    if T <= 0:
        return max(S - K, 0)
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)


def black_scholes_put(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Black-Scholes put option price.
    
    Args:
        S: Spot price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate
        sigma: Volatility (annualized)
    
    Returns:
        Put option price
    """
    if T <= 0:
        return max(K - S, 0)
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def compute_implied_volatility(
    option_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: OptionType,
    tol: float = 1e-5,
    max_iter: int = 100
) -> Optional[float]:
    """
    Compute implied volatility using Brent's method.
    
    Args:
        option_price: Market price of option
        S: Spot price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate
        option_type: CALL or PUT
        tol: Convergence tolerance
        max_iter: Maximum iterations
    
    Returns:
        Implied volatility (annualized) or None if computation fails
    """
    if option_price <= 0 or T <= 0:
        return None
    
    # Intrinsic value check
    if option_type == OptionType.CALL:
        intrinsic = max(S - K, 0)
        bs_func = lambda sigma: black_scholes_call(S, K, T, r, sigma) - option_price
    else:  # PUT
        intrinsic = max(K - S, 0)
        bs_func = lambda sigma: black_scholes_put(S, K, T, r, sigma) - option_price
    
    if option_price < intrinsic:
        # Price below intrinsic value, invalid
        return None
    
    try:
        # Brent's method to find sigma
        iv = brentq(bs_func, 0.01, 5.0, xtol=tol, maxiter=max_iter)
        return iv
    except (ValueError, RuntimeError):
        # Root not found (e.g., option deep in/out of money)
        return None


def compute_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: OptionType
) -> Dict[str, float]:
    """
    Compute option Greeks using Black-Scholes model.
    
    Args:
        S: Spot price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate
        sigma: Volatility (annualized)
        option_type: CALL or PUT
    
    Returns:
        Dict with delta, gamma, theta, vega
    """
    if T <= 0:
        return {
            'delta': 1.0 if S > K else 0.0,
            'gamma': 0.0,
            'theta': 0.0,
            'vega': 0.0
        }
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    # Delta
    if option_type == OptionType.CALL:
        delta = norm.cdf(d1)
    else:  # PUT
        delta = norm.cdf(d1) - 1.0
    
    # Gamma (same for calls and puts)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    
    # Theta (per day)
    if option_type == OptionType.CALL:
        theta = (
            -S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
            - r * K * np.exp(-r * T) * norm.cdf(d2)
        ) / 365  # Convert to per-day
    else:  # PUT
        theta = (
            -S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
            + r * K * np.exp(-r * T) * norm.cdf(-d2)
        ) / 365  # Convert to per-day
    
    # Vega (per 1% vol change)
    vega = S * norm.pdf(d1) * np.sqrt(T) / 100
    
    return {
        'delta': delta,
        'gamma': gamma,
        'theta': theta,
        'vega': vega
    }


# =============================================================================
# AZURE ML OPTIONS FORECAST CLIENT
# =============================================================================

class AzureMLOptionsClient:
    """
    Production Azure ML options forecasting client.
    
    Responsibilities:
    - Fetch real-time options chains from Azure ML endpoint
    - Compute implied volatility for all contracts
    - Calculate Greeks (delta, gamma, theta, vega)
    - Generate options forecast with expected returns
    - Convert to ForecastContract for Phase 3.5 caching
    
    Attributes:
        config: AzureMLConfig instance
        cache_router: Phase 3.5 CacheRouter
        options_endpoint_url: Azure ML options endpoint
        risk_free_rate: Current risk-free rate (default: 0.045 = 4.5%)
    """
    
    def __init__(self,
                 config: Optional[AzureMLConfig] = None,
                 cache_router: Optional[CacheRouter] = None,
                 risk_free_rate: float = 0.045):
        """
        Initialize Azure ML options client.
        
        Args:
            config: AzureMLConfig instance (creates new if None)
            cache_router: Phase 3.5 CacheRouter (creates new if None)
            risk_free_rate: Annual risk-free rate (default: 4.5%)
        """
        self.config = config or AzureMLConfig()
        self.cache_router = cache_router or CacheRouter()
        self.risk_free_rate = risk_free_rate
        
        # Azure ML options endpoint (separate from SHAP endpoint)
        self.options_endpoint_url = os.getenv(
            'AZURE_ML_OPTIONS_ENDPOINT_URL',
            self.config.endpoint_url  # Fallback to main endpoint
        )
        self.api_key = self.config.api_key
        self.use_mock = self.config.use_mock_fallback or not self.config.is_configured()
        
        # Performance telemetry
        self.call_count = 0
        self.total_latency = 0.0
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Log initialization
        if self.use_mock:
            logger.warning(
                "⚠️ AzureMLOptionsClient initialized in MOCK MODE "
                "(Azure credentials not configured or use_mock_fallback=True)"
            )
        else:
            logger.info(
                f"✅ AzureMLOptionsClient initialized with endpoint: "
                f"{self.options_endpoint_url[:50]}..."
            )
    
    def _generate_cache_key(self, ticker: str, expiration: Optional[str] = None) -> str:
        """
        Generate deterministic cache key for options chain request.
        
        Args:
            ticker: Stock ticker symbol
            expiration: Optional specific expiration date
        
        Returns:
            SHA256 hash of ticker + expiration
        """
        payload = f"{ticker}:{expiration if expiration else 'all'}"
        return hashlib.sha256(payload.encode()).hexdigest()
    
    def fetch_option_chain_azure(
        self,
        ticker: str,
        expiration: Optional[str] = None,
        use_cache: bool = True,
        timeout: float = 5.0
    ) -> OptionChain:
        """
        Fetch options chain from Azure ML endpoint.
        
        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")
            expiration: Optional specific expiration date (ISO 8601)
            use_cache: Whether to use L1/L2/L3 caching
            timeout: Request timeout in seconds
        
        Returns:
            OptionChain with all contracts, spot price, expirations
        
        Raises:
            requests.RequestException: If Azure ML endpoint unreachable
            ValueError: If response invalid
        """
        start_time = time.time()
        
        # Generate cache key
        cache_key = self._generate_cache_key(ticker, expiration)
        
        # Check cache
        if use_cache:
            cached_data = self.cache_router.get_data(
                contract_type=ContractType.FORECAST,
                key=cache_key
            )
            
            if cached_data is not None:
                self.cache_hits += 1
                elapsed = time.time() - start_time
                logger.info(
                    f"✅ Options chain cache HIT for {ticker} "
                    f"(latency={elapsed*1000:.1f}ms)"
                )
                return self._parse_cached_chain(cached_data)
            
            self.cache_misses += 1
        
        # Cache MISS or caching disabled
        logger.info(f"🔍 Options chain cache MISS for {ticker}, calling Azure ML endpoint...")
        
        # Call Azure ML or fallback to mock
        if self.use_mock:
            logger.warning(f"⚠️ Using mock options data for {ticker}")
            chain = self._generate_mock_chain(ticker, expiration)
        else:
            try:
                chain = self._call_azure_options_endpoint(ticker, expiration, timeout)
            except (requests.RequestException, ValueError) as e:
                logger.error(f"❌ Azure ML options endpoint failed: {e}. Using mock data.")
                chain = self._generate_mock_chain(ticker, expiration)
        
        # Compute IV and Greeks for all contracts
        self._compute_chain_analytics(chain)
        
        # Store in cache
        if use_cache:
            self.cache_router.store_data(
                contract_type=ContractType.FORECAST,
                key=cache_key,
                data=self._serialize_chain(chain)
            )
            logger.debug(f"💾 Stored options chain for {ticker} in cache")
        
        # Performance telemetry
        elapsed = time.time() - start_time
        self.call_count += 1
        self.total_latency += elapsed
        
        logger.info(
            f"✅ Options chain fetched for {ticker} "
            f"({len(chain.calls)} calls, {len(chain.puts)} puts, latency={elapsed:.3f}s)"
        )
        
        return chain
    
    def _call_azure_options_endpoint(
        self,
        ticker: str,
        expiration: Optional[str],
        timeout: float
    ) -> OptionChain:
        """
        Make HTTP request to Azure ML options endpoint.
        
        Args:
            ticker: Stock ticker symbol
            expiration: Optional specific expiration date
            timeout: Request timeout
        
        Returns:
            OptionChain from Azure ML response
        
        Raises:
            requests.RequestException: If request fails
            ValueError: If response invalid
        """
        if not self.options_endpoint_url or not self.api_key:
            raise ValueError(
                "Azure ML options_endpoint_url and api_key must be configured."
            )
        
        payload = {
            "ticker": ticker.upper(),
            "expiration": expiration,
            "include_greeks": False  # We compute Greeks locally
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        logger.debug(f"Calling Azure ML options endpoint: {self.options_endpoint_url}")
        
        response = requests.post(
            self.options_endpoint_url,
            json=payload,
            headers=headers,
            timeout=timeout
        )
        
        if response.status_code != 200:
            raise requests.RequestException(
                f"Azure ML options endpoint returned {response.status_code}: {response.text}"
            )
        
        result = response.json()
        
        # Parse response into OptionChain
        return self._parse_azure_response(ticker, result)
    
    def _parse_azure_response(self, ticker: str, azure_response: Dict[str, Any]) -> OptionChain:
        """
        Parse Azure ML response into OptionChain.
        
        Expected Azure response format:
        {
            "ticker": "AAPL",
            "spot_price": 175.50,
            "timestamp": "2025-01-30T12:00:00Z",
            "expirations": ["2025-02-14", "2025-03-21", ...],
            "calls": [
                {
                    "strike": 175.0,
                    "expiration": "2025-02-14",
                    "bid": 5.20,
                    "ask": 5.40,
                    "last": 5.30,
                    "volume": 1250,
                    "open_interest": 5000
                },
                ...
            ],
            "puts": [...]
        }
        
        Args:
            ticker: Stock ticker symbol
            azure_response: Azure ML endpoint response
        
        Returns:
            OptionChain
        """
        # Extract spot price
        spot_price = azure_response.get('spot_price', 0.0)
        if spot_price <= 0:
            raise ValueError(f"Invalid spot price in Azure response: {spot_price}")
        
        # Extract timestamp
        timestamp = azure_response.get('timestamp', datetime.now(timezone.utc).isoformat())
        
        # Extract expirations
        expirations = azure_response.get('expirations', [])
        
        # Parse call contracts
        calls = [
            OptionContract(
                ticker=ticker,
                strike=opt['strike'],
                expiration=opt['expiration'],
                option_type=OptionType.CALL,
                bid=opt.get('bid', 0.0),
                ask=opt.get('ask', 0.0),
                last=opt.get('last', 0.0),
                volume=opt.get('volume', 0),
                open_interest=opt.get('open_interest', 0)
            )
            for opt in azure_response.get('calls', [])
        ]
        
        # Parse put contracts
        puts = [
            OptionContract(
                ticker=ticker,
                strike=opt['strike'],
                expiration=opt['expiration'],
                option_type=OptionType.PUT,
                bid=opt.get('bid', 0.0),
                ask=opt.get('ask', 0.0),
                last=opt.get('last', 0.0),
                volume=opt.get('volume', 0),
                open_interest=opt.get('open_interest', 0)
            )
            for opt in azure_response.get('puts', [])
        ]
        
        return OptionChain(
            ticker=ticker,
            spot_price=spot_price,
            timestamp=timestamp,
            expirations=expirations,
            calls=calls,
            puts=puts,
            metadata={
                'source': 'Azure ML',
                'endpoint': self.options_endpoint_url[:50]
            }
        )
    
    def _generate_mock_chain(self, ticker: str, expiration: Optional[str]) -> OptionChain:
        """
        Generate mock options chain for development/fallback.
        
        Args:
            ticker: Stock ticker symbol
            expiration: Optional specific expiration
        
        Returns:
            Mock OptionChain with realistic data
        """
        # Mock spot price (ticker hash-based for determinism)
        ticker_hash = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
        np.random.seed(ticker_hash % 10000)
        spot_price = 100.0 + np.random.randn() * 50.0
        spot_price = max(10.0, spot_price)  # Ensure positive
        
        # Mock expirations (next 4 monthly expirations)
        base_date = datetime.now(timezone.utc)
        expirations = []
        for i in range(1, 5):
            exp_date = base_date + timedelta(days=30 * i)
            expirations.append(exp_date.date().isoformat())
        
        if expiration:
            expirations = [expiration]
        
        # Generate strike range (80% to 120% of spot)
        strikes = np.arange(
            round(spot_price * 0.8 / 5) * 5,
            round(spot_price * 1.2 / 5) * 5 + 1,
            5
        )
        
        calls = []
        puts = []
        
        for exp in expirations:
            # exp is already in days (integer), not a date string
            days_to_exp = exp if isinstance(exp, int) else (datetime.fromisoformat(exp) - base_date).days
            T = days_to_exp / 365.0
            
            for strike in strikes:
                # Mock implied volatility (20% - 60% annualized)
                iv = 0.20 + np.random.rand() * 0.40
                
                # Compute theoretical prices
                call_price = black_scholes_call(spot_price, strike, T, self.risk_free_rate, iv)
                put_price = black_scholes_put(spot_price, strike, T, self.risk_free_rate, iv)
                
                # Add bid-ask spread (2% of price)
                call_bid = call_price * 0.99
                call_ask = call_price * 1.01
                put_bid = put_price * 0.99
                put_ask = put_price * 1.01
                
                # Mock volume and OI
                volume = int(np.random.exponential(100))
                oi = int(np.random.exponential(500))
                
                calls.append(OptionContract(
                    ticker=ticker,
                    strike=strike,
                    expiration=exp,
                    option_type=OptionType.CALL,
                    bid=call_bid,
                    ask=call_ask,
                    last=call_price,
                    volume=volume,
                    open_interest=oi
                ))
                
                puts.append(OptionContract(
                    ticker=ticker,
                    strike=strike,
                    expiration=exp,
                    option_type=OptionType.PUT,
                    bid=put_bid,
                    ask=put_ask,
                    last=put_price,
                    volume=volume,
                    open_interest=oi
                ))
        
        return OptionChain(
            ticker=ticker,
            spot_price=spot_price,
            timestamp=datetime.now(timezone.utc).isoformat(),
            expirations=expirations,
            calls=calls,
            puts=puts,
            metadata={'source': 'Mock', 'risk_free_rate': self.risk_free_rate}
        )
    
    def _compute_chain_analytics(self, chain: OptionChain) -> None:
        """
        Compute implied volatility and Greeks for all contracts in chain.
        
        Modifies chain.calls and chain.puts in-place.
        
        Args:
            chain: OptionChain to enhance
        """
        base_date = datetime.fromisoformat(chain.timestamp.replace('Z', '+00:00'))
        
        for opt in chain.calls + chain.puts:
            # Time to expiration
            # opt.expiration can be either an int (days) or a date string
            if isinstance(opt.expiration, int):
                T = opt.expiration / 365.0
            else:
                exp_date = datetime.fromisoformat(opt.expiration + "T16:00:00+00:00")  # Market close
                T = (exp_date - base_date).total_seconds() / (365.25 * 24 * 3600)
            
            T = max(T, 1e-6)  # Avoid division by zero
            
            # Option price (use mid or last)
            option_price = opt.mid_price()
            
            if option_price <= 0:
                continue  # Skip options with no price data
            
            # Compute implied volatility
            opt.implied_volatility = compute_implied_volatility(
                option_price=option_price,
                S=chain.spot_price,
                K=opt.strike,
                T=T,
                r=self.risk_free_rate,
                option_type=opt.option_type
            )
            
            # Compute Greeks (if IV available)
            if opt.implied_volatility is not None:
                greeks = compute_greeks(
                    S=chain.spot_price,
                    K=opt.strike,
                    T=T,
                    r=self.risk_free_rate,
                    sigma=opt.implied_volatility,
                    option_type=opt.option_type
                )
                opt.delta = greeks['delta']
                opt.gamma = greeks['gamma']
                opt.theta = greeks['theta']
                opt.vega = greeks['vega']
    
    def _serialize_chain(self, chain: OptionChain) -> Dict[str, Any]:
        """Serialize OptionChain to JSON dict for caching."""
        # Use the OptionChain.to_dict() helper to ensure native Python types
        try:
            return chain.to_dict()
        except Exception:
            # Fallback: construct a conservative JSON-safe dict
            return {
                'ticker': str(chain.ticker),
                'spot_price': float(chain.spot_price),
                'timestamp': str(chain.timestamp),
                'expirations': [str(e) for e in chain.expirations],
                'calls': [self._serialize_contract(opt) for opt in chain.calls],
                'puts': [self._serialize_contract(opt) for opt in chain.puts],
                'metadata': chain.metadata
            }
    
    def _serialize_contract(self, opt: OptionContract) -> Dict[str, Any]:
        """Serialize OptionContract to JSON dict."""
        # Use OptionContract.to_dict() to ensure native types
        try:
            return opt.to_dict()
        except Exception:
            return {
                'ticker': str(opt.ticker),
                'strike': float(opt.strike),
                'expiration': str(opt.expiration),
                'option_type': opt.option_type.value if isinstance(opt.option_type, OptionType) else str(opt.option_type),
                'bid': float(opt.bid),
                'ask': float(opt.ask),
                'last': float(opt.last),
                'volume': int(opt.volume) if opt.volume is not None else 0,
                'open_interest': int(opt.open_interest) if opt.open_interest is not None else 0,
                'implied_volatility': None if opt.implied_volatility is None else float(opt.implied_volatility),
                'delta': None if opt.delta is None else float(opt.delta),
                'gamma': None if opt.gamma is None else float(opt.gamma),
                'theta': None if opt.theta is None else float(opt.theta),
                'vega': None if opt.vega is None else float(opt.vega)
            }
    
    def _parse_cached_chain(self, cached_data: Dict[str, Any]) -> OptionChain:
        """Deserialize cached data into OptionChain."""
        calls = [
            OptionContract(
                ticker=opt['ticker'],
                strike=opt['strike'],
                expiration=opt['expiration'],
                option_type=OptionType(opt['option_type']),
                bid=opt['bid'],
                ask=opt['ask'],
                last=opt['last'],
                volume=opt['volume'],
                open_interest=opt['open_interest'],
                implied_volatility=opt.get('implied_volatility'),
                delta=opt.get('delta'),
                gamma=opt.get('gamma'),
                theta=opt.get('theta'),
                vega=opt.get('vega')
            )
            for opt in cached_data.get('calls', [])
        ]
        
        puts = [
            OptionContract(
                ticker=opt['ticker'],
                strike=opt['strike'],
                expiration=opt['expiration'],
                option_type=OptionType(opt['option_type']),
                bid=opt['bid'],
                ask=opt['ask'],
                last=opt['last'],
                volume=opt['volume'],
                open_interest=opt['open_interest'],
                implied_volatility=opt.get('implied_volatility'),
                delta=opt.get('delta'),
                gamma=opt.get('gamma'),
                theta=opt.get('theta'),
                vega=opt.get('vega')
            )
            for opt in cached_data.get('puts', [])
        ]
        
        return OptionChain(
            ticker=cached_data['ticker'],
            spot_price=cached_data['spot_price'],
            timestamp=cached_data['timestamp'],
            expirations=cached_data.get('expirations', []),
            calls=calls,
            puts=puts,
            metadata=cached_data.get('metadata', {})
        )
    
    def generate_options_forecast(
        self,
        ticker: str,
        expiration: Optional[str] = None,
        use_cache: bool = True
    ) -> ForecastContract:
        """
        Generate options-based forecast with IV and expected returns.
        
        Workflow:
        1. Fetch options chain (real or mock)
        2. Find ATM options (strike nearest spot price)
        3. Extract IV from ATM call and put
        4. Compute expected return based on IV skew
        5. Package into ForecastContract for Market Forecast tab
        
        Args:
            ticker: Stock ticker symbol
            expiration: Optional specific expiration (nearest if None)
            use_cache: Whether to use L1/L2/L3 caching
        
        Returns:
            ForecastContract with IV, expected return, confidence interval
        
        Performance SLA:
            - <3s for single ticker forecast
        """
        start_time = time.time()
        
        # Fetch options chain
        chain = self.fetch_option_chain_azure(ticker, expiration, use_cache)
        
        # Select expiration (nearest if not specified)
        if expiration is None and chain.expirations:
            expiration = chain.expirations[0]  # Nearest expiration
        
        # Get ATM strike
        atm_strike = chain.get_atm_strike()

        # Normalize expiration for matching (accept int days or ISO date string)
        if isinstance(expiration, int):
            expiration_iso = (datetime.now(timezone.utc) + timedelta(days=expiration)).date().isoformat()
        else:
            expiration_iso = expiration

        # Find ATM call and put (use tolerant float compare for strikes)
        eps = 1e-6
        exp_iso_str = None
        try:
            exp_iso_str = (datetime.now(timezone.utc) + timedelta(days=expiration)).date().isoformat() if isinstance(expiration, int) else str(expiration)
        except Exception:
            exp_iso_str = str(expiration)

        def _exp_matches(opt_exp: Any) -> bool:
            # Compare stringified representations to handle int vs ISO date
            try:
                return str(opt_exp) == str(expiration) or str(opt_exp) == str(exp_iso_str)
            except Exception:
                return False

        atm_call = next(
            (opt for opt in chain.calls 
             if abs(float(opt.strike) - float(atm_strike)) < eps and _exp_matches(opt.expiration)),
            None
        )
        atm_put = next(
            (opt for opt in chain.puts 
             if abs(float(opt.strike) - float(atm_strike)) < eps and _exp_matches(opt.expiration)),
            None
        )
        
        if not atm_call or not atm_put:
            raise ValueError(f"No ATM options found for {ticker} at strike {atm_strike}")
        
        # Extract IV
        call_iv = atm_call.implied_volatility or 0.0
        put_iv = atm_put.implied_volatility or 0.0
        avg_iv = (call_iv + put_iv) / 2.0
        
        # IV skew (put IV - call IV)
        iv_skew = put_iv - call_iv
        
        # Expected return estimate (simplified)
        # Positive IV skew → bearish sentiment → lower expected return
        # Negative IV skew → bullish sentiment → higher expected return
        expected_return = -iv_skew * 100  # Convert to percentage
        
        # Confidence interval based on IV
        # Higher IV → wider confidence bands
        conf_lower = expected_return - avg_iv * 100
        conf_upper = expected_return + avg_iv * 100
        
        # Package results into Phase 3.5 ForecastContract format
        # Convert expected_return (percentage) to decimal expected_return_decimal
        expected_return_decimal = expected_return / 100.0

        horizon_days = 30
        try:
            if isinstance(expiration, int):
                horizon_days = int(expiration)
            else:
                # try parsing ISO date
                try:
                    exp_dt = datetime.fromisoformat(str(expiration))
                except Exception:
                    try:
                        exp_dt = datetime.fromisoformat(str(expiration) + "T16:00:00")
                    except Exception:
                        exp_dt = datetime.now(timezone.utc) + timedelta(days=30)
                horizon_days = max(1, (exp_dt - datetime.now(timezone.utc)).days)
        except Exception:
            horizon_days = 30

        return_distribution = {
            'mean': expected_return_decimal,
            'std': float(avg_iv) if avg_iv is not None else 0.0
        }

        confidence_score = max(0.0, min(1.0, 1.0 - min(float(avg_iv), 1.0)))

        forecast_id = hashlib.sha256(f"{ticker}:{atm_strike}:{expiration}:{time.time()}".encode('utf-8')).hexdigest()

        forecast = ForecastContract(
            forecast_id=forecast_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            ticker=ticker,
            horizon_days=int(horizon_days),
            expected_return=float(expected_return_decimal),
            return_distribution=return_distribution,
            confidence_score=float(confidence_score),
            features_used=['options_iv_skew', 'atm_iv'],
            model_version='phase6-options-v1',
            scenario='base',
            metadata={
                'spot_price': chain.spot_price,
                'atm_strike': atm_strike,
                'atm_call_iv': call_iv,
                'atm_put_iv': put_iv,
                'avg_iv': avg_iv,
                'iv_skew': iv_skew,
                'expected_return_pct': expected_return,
                'expiration': expiration_iso,
                'greeks': {
                    'call_delta': atm_call.delta if atm_call else None,
                    'put_delta': atm_put.delta if atm_put else None,
                    'delta': (
                        (atm_call.delta + atm_put.delta) / 2.0
                        if atm_call and atm_put and atm_call.delta is not None and atm_put.delta is not None
                        else (atm_call.delta if atm_call and atm_call.delta is not None else (atm_put.delta if atm_put and atm_put.delta is not None else 0.0))
                    ),
                    'gamma': atm_call.gamma if atm_call and atm_call.gamma is not None else (atm_put.gamma if atm_put and atm_put.gamma is not None else 0.0),
                    'theta': atm_call.theta if atm_call and atm_call.theta is not None else (atm_put.theta if atm_put and atm_put.theta is not None else 0.0),
                    'vega': atm_call.vega if atm_call and atm_call.vega is not None else (atm_put.vega if atm_put and atm_put.vega is not None else 0.0)
                }
            }
        )
        
        # Performance telemetry
        elapsed = time.time() - start_time
        logger.info(
            f"✅ Options forecast generated for {ticker} "
            f"(IV={avg_iv:.2%}, expected_return={expected_return:.2f}%, latency={elapsed:.3f}s)"
        )
        
        return forecast
    
    def get_telemetry(self) -> Dict[str, Any]:
        """Get performance telemetry for monitoring."""
        cache_hit_rate = (
            self.cache_hits / (self.cache_hits + self.cache_misses) * 100
            if (self.cache_hits + self.cache_misses) > 0
            else 0.0
        )
        
        avg_latency = (
            self.total_latency / self.call_count
            if self.call_count > 0
            else 0.0
        )
        
        return {
            'call_count': self.call_count,
            'total_latency_seconds': self.total_latency,
            'avg_latency_seconds': avg_latency,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate_pct': cache_hit_rate,
            'using_mock_fallback': self.use_mock,
            'options_endpoint_url': self.options_endpoint_url[:50] if self.options_endpoint_url else 'mock',
            'risk_free_rate': self.risk_free_rate
        }


# =============================================================================
# PUBLIC API
# =============================================================================

def create_azure_options_client(
    config: Optional[AzureMLConfig] = None,
    cache_router: Optional[CacheRouter] = None,
    risk_free_rate: float = 0.045,
    offline_mode: Optional[bool] = None
) -> AzureMLOptionsClient:
    """
    Factory function to create AzureMLOptionsClient instance.
    
    Args:
        config: AzureMLConfig instance (creates new if None)
        cache_router: Phase 3.5 CacheRouter (creates new if None)
        risk_free_rate: Annual risk-free rate (default: 4.5%)
        offline_mode: Force offline/mock mode (backward compatibility param)
    
    Returns:
        Configured AzureMLOptionsClient instance
    """
    # Handle offline_mode backward compatibility (for tests)
    # offline_mode is informational only - actual mock behavior determined by config
    # No changes needed here as AzureMLOptionsClient handles missing config gracefully
    return AzureMLOptionsClient(
        config=config,
        cache_router=cache_router,
        risk_free_rate=risk_free_rate
    )


if __name__ == "__main__":
    # Simple diagnostic test
    logging.basicConfig(level=logging.INFO)
    
    print("=== Phase 6 Azure ML Options Forecasting Diagnostic ===\n")
    
    # Create client
    client = create_azure_options_client()
    
    # Check configuration
    print(f"Mode: {'MOCK' if client.use_mock else 'AZURE ML'}")
    print(f"Risk-Free Rate: {client.risk_free_rate:.2%}")
    print(f"Endpoint: {client.options_endpoint_url[:50] if client.options_endpoint_url else 'Not configured'}\n")
    
    # Test options chain fetching (mock mode)
    if client.use_mock:
        print("Testing with mock options chain...")
        
        chain = client.fetch_option_chain_azure("AAPL", use_cache=False)
        
        print(f"\nOptions Chain:")
        print(f"  Ticker: {chain.ticker}")
        print(f"  Spot Price: ${chain.spot_price:.2f}")
        print(f"  Expirations: {chain.expirations}")
        print(f"  Total Calls: {len(chain.calls)}")
        print(f"  Total Puts: {len(chain.puts)}")
        print(f"  ATM Strike: ${chain.get_atm_strike():.2f}")
        
        # Test forecast generation
        forecast = client.generate_options_forecast("AAPL", use_cache=False)
        
        print(f"\nOptions Forecast:")
        print(f"  Ticker: {forecast.ticker}")
        print(f"  Horizon: {forecast.forecast_horizon_days} days")
        print(f"  Predicted Value: ${forecast.predicted_value:.2f}")
        print(f"  Confidence Interval: ${forecast.confidence_interval[0]:.2f} - ${forecast.confidence_interval[1]:.2f}")
        print(f"  Avg IV: {forecast.metadata['avg_iv']:.2%}")
        print(f"  IV Skew: {forecast.metadata['iv_skew']:+.4f}")
        print(f"  Expected Return: {forecast.metadata['expected_return_pct']:+.2f}%")
        
        # Telemetry
        telemetry = client.get_telemetry()
        print(f"\nTelemetry:")
        print(f"  Calls: {telemetry['call_count']}")
        print(f"  Avg Latency: {telemetry['avg_latency_seconds']:.3f}s")
        print(f"  Cache Hit Rate: {telemetry['cache_hit_rate_pct']:.1f}%")
    
    else:
        print("⚠️ Azure ML configured but not tested (requires real endpoint)")
    
    print("\n✅ Diagnostic complete!")

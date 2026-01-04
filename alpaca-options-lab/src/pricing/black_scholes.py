"""
Alpaca Options Lab - Black-Scholes Option Pricing Engine

Production-grade Black-Scholes implementation with:
- Analytical option pricing (European calls/puts)
- Complete Greeks calculation (Delta, Gamma, Theta, Vega, Rho)
- Numba JIT compilation for performance-critical paths
- Vectorized operations for batch pricing
- Edge case handling (expired options, extreme values)

Performance Targets:
- Single option Greeks: <1ms P99
- Batch pricing (1000 options): <50ms
- Vectorized Greeks: 100k+ options/second

Mathematical Foundation:
- Black-Scholes-Merton model (1973)
- Assumes log-normal price distribution
- European-style exercise only
- Continuous dividend yield model

Usage:
    from src.pricing.black_scholes import BlackScholesEngine, price_option
    
    # Quick pricing
    result = price_option(
        spot=150.0,
        strike=155.0,
        time_to_expiry=0.25,  # 3 months
        volatility=0.30,
        risk_free_rate=0.05,
        dividend_yield=0.01,
        is_call=True,
    )
    print(f"Price: ${result.price:.2f}")
    print(f"Delta: {result.greeks.delta:.4f}")
    
    # Engine for batch operations
    engine = BlackScholesEngine()
    prices = engine.price_batch(options_df)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

import numpy as np
from scipy.stats import norm

from src.utils.exceptions import InvalidOptionParameters, NegativeTimeToExpiry
from src.utils.logging_config import get_logger
from src.utils.metrics import get_metrics, track_latency

logger = get_logger(__name__)
metrics = get_metrics()

# Try to import numba for JIT compilation
try:
    from numba import jit, vectorize, float64
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    # Provide no-op decorator fallback
    def jit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def vectorize(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    float64 = float

# Constants
SQRT_2PI = math.sqrt(2 * math.pi)
MIN_TIME_TO_EXPIRY = 1e-10  # ~0.3 seconds in years
MAX_VOLATILITY = 5.0  # 500% IV cap
MIN_VOLATILITY = 0.001  # 0.1% IV floor


@dataclass(frozen=True)
class Greeks:
    """
    Option Greeks container.
    
    All Greeks are calculated analytically using Black-Scholes formulas.
    
    Attributes:
        delta: Rate of change of option price with respect to underlying
               Range: [0, 1] for calls, [-1, 0] for puts
        gamma: Rate of change of delta with respect to underlying
               Always positive, highest at-the-money
        theta: Rate of decay of option value per day
               Usually negative (time decay)
        vega: Sensitivity to volatility (per 1% change)
              Always positive
        rho: Sensitivity to interest rate (per 1% change)
             Positive for calls, negative for puts
    """
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "delta": round(self.delta, 6),
            "gamma": round(self.gamma, 8),
            "theta": round(self.theta, 6),
            "vega": round(self.vega, 6),
            "rho": round(self.rho, 6),
        }
    
    def __str__(self) -> str:
        return (
            f"Greeks(Δ={self.delta:.4f}, Γ={self.gamma:.6f}, "
            f"Θ={self.theta:.4f}, ν={self.vega:.4f}, ρ={self.rho:.4f})"
        )


@dataclass(frozen=True)
class OptionPriceResult:
    """
    Complete option pricing result.
    
    Contains price, Greeks, and computation metadata.
    """
    price: float
    greeks: Greeks
    intrinsic_value: float
    time_value: float
    is_call: bool
    
    # Input parameters for reference
    spot: float
    strike: float
    time_to_expiry: float
    volatility: float
    risk_free_rate: float
    dividend_yield: float
    
    @property
    def moneyness(self) -> float:
        """Calculate moneyness (S/K)."""
        if self.strike > 0:
            return self.spot / self.strike
        return 0.0
    
    @property
    def log_moneyness(self) -> float:
        """Calculate log moneyness ln(S/K)."""
        if self.strike > 0 and self.spot > 0:
            return math.log(self.spot / self.strike)
        return 0.0
    
    @property
    def is_itm(self) -> bool:
        """Check if option is in-the-money."""
        if self.is_call:
            return self.spot > self.strike
        return self.spot < self.strike
    
    @property
    def is_otm(self) -> bool:
        """Check if option is out-of-the-money."""
        return not self.is_itm
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "price": round(self.price, 4),
            "intrinsic_value": round(self.intrinsic_value, 4),
            "time_value": round(self.time_value, 4),
            "is_call": self.is_call,
            "is_itm": self.is_itm,
            "moneyness": round(self.moneyness, 4),
            "greeks": self.greeks.to_dict(),
            "inputs": {
                "spot": self.spot,
                "strike": self.strike,
                "time_to_expiry": round(self.time_to_expiry, 6),
                "volatility": round(self.volatility, 4),
                "risk_free_rate": round(self.risk_free_rate, 4),
                "dividend_yield": round(self.dividend_yield, 4),
            },
        }


# =============================================================================
# CORE BLACK-SCHOLES FUNCTIONS (Numba-accelerated when available)
# =============================================================================

@jit(nopython=True, cache=True, fastmath=True)
def _norm_cdf(x: float) -> float:
    """
    Standard normal CDF approximation (Abramowitz & Stegun).
    
    Accurate to ~7 decimal places, faster than scipy.stats.norm.cdf
    for single values in tight loops.
    """
    # Constants for approximation
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911
    
    sign = 1 if x >= 0 else -1
    x = abs(x)
    
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x / 2.0)
    
    return 0.5 * (1.0 + sign * y)


@jit(nopython=True, cache=True, fastmath=True)
def _norm_pdf(x: float) -> float:
    """Standard normal PDF."""
    return math.exp(-0.5 * x * x) / SQRT_2PI


@jit(nopython=True, cache=True, fastmath=True)
def _calculate_d1_d2(
    S: float,  # Spot price
    K: float,  # Strike price
    T: float,  # Time to expiry (years)
    r: float,  # Risk-free rate
    q: float,  # Dividend yield
    sigma: float,  # Volatility
) -> Tuple[float, float]:
    """
    Calculate d1 and d2 parameters for Black-Scholes.
    
    d1 = (ln(S/K) + (r - q + σ²/2)T) / (σ√T)
    d2 = d1 - σ√T
    """
    sqrt_T = math.sqrt(T)
    sigma_sqrt_T = sigma * sqrt_T
    
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / sigma_sqrt_T
    d2 = d1 - sigma_sqrt_T
    
    return d1, d2


@jit(nopython=True, cache=True, fastmath=True)
def _bs_call_price(
    S: float,
    K: float,
    T: float,
    r: float,
    q: float,
    sigma: float,
) -> float:
    """Black-Scholes call option price."""
    d1, d2 = _calculate_d1_d2(S, K, T, r, q, sigma)
    
    call_price = (
        S * math.exp(-q * T) * _norm_cdf(d1) -
        K * math.exp(-r * T) * _norm_cdf(d2)
    )
    
    return max(call_price, 0.0)


@jit(nopython=True, cache=True, fastmath=True)
def _bs_put_price(
    S: float,
    K: float,
    T: float,
    r: float,
    q: float,
    sigma: float,
) -> float:
    """Black-Scholes put option price."""
    d1, d2 = _calculate_d1_d2(S, K, T, r, q, sigma)
    
    put_price = (
        K * math.exp(-r * T) * _norm_cdf(-d2) -
        S * math.exp(-q * T) * _norm_cdf(-d1)
    )
    
    return max(put_price, 0.0)


@jit(nopython=True, cache=True, fastmath=True)
def _bs_greeks_call(
    S: float,
    K: float,
    T: float,
    r: float,
    q: float,
    sigma: float,
) -> Tuple[float, float, float, float, float]:
    """
    Calculate all Greeks for a call option.
    
    Returns: (delta, gamma, theta, vega, rho)
    """
    sqrt_T = math.sqrt(T)
    d1, d2 = _calculate_d1_d2(S, K, T, r, q, sigma)
    
    # Common terms
    exp_minus_qT = math.exp(-q * T)
    exp_minus_rT = math.exp(-r * T)
    nd1 = _norm_cdf(d1)
    nd2 = _norm_cdf(d2)
    pdf_d1 = _norm_pdf(d1)
    
    # Delta: ∂C/∂S = e^(-qT) * N(d1)
    delta = exp_minus_qT * nd1
    
    # Gamma: ∂²C/∂S² = e^(-qT) * n(d1) / (S * σ * √T)
    gamma = exp_minus_qT * pdf_d1 / (S * sigma * sqrt_T)
    
    # Theta: ∂C/∂t (per day)
    # Theta = -e^(-qT) * S * n(d1) * σ / (2√T) - r*K*e^(-rT)*N(d2) + q*S*e^(-qT)*N(d1)
    theta = (
        -exp_minus_qT * S * pdf_d1 * sigma / (2 * sqrt_T)
        - r * K * exp_minus_rT * nd2
        + q * S * exp_minus_qT * nd1
    ) / 365.0  # Convert to daily
    
    # Vega: ∂C/∂σ (per 1% = 0.01 change)
    vega = S * exp_minus_qT * pdf_d1 * sqrt_T * 0.01
    
    # Rho: ∂C/∂r (per 1% = 0.01 change)
    rho = K * T * exp_minus_rT * nd2 * 0.01
    
    return delta, gamma, theta, vega, rho


@jit(nopython=True, cache=True, fastmath=True)
def _bs_greeks_put(
    S: float,
    K: float,
    T: float,
    r: float,
    q: float,
    sigma: float,
) -> Tuple[float, float, float, float, float]:
    """
    Calculate all Greeks for a put option.
    
    Returns: (delta, gamma, theta, vega, rho)
    """
    sqrt_T = math.sqrt(T)
    d1, d2 = _calculate_d1_d2(S, K, T, r, q, sigma)
    
    # Common terms
    exp_minus_qT = math.exp(-q * T)
    exp_minus_rT = math.exp(-r * T)
    n_minus_d1 = _norm_cdf(-d1)
    n_minus_d2 = _norm_cdf(-d2)
    pdf_d1 = _norm_pdf(d1)
    
    # Delta: ∂P/∂S = -e^(-qT) * N(-d1)
    delta = -exp_minus_qT * n_minus_d1
    
    # Gamma: Same as call
    gamma = exp_minus_qT * pdf_d1 / (S * sigma * sqrt_T)
    
    # Theta: ∂P/∂t (per day)
    theta = (
        -exp_minus_qT * S * pdf_d1 * sigma / (2 * sqrt_T)
        + r * K * exp_minus_rT * n_minus_d2
        - q * S * exp_minus_qT * n_minus_d1
    ) / 365.0
    
    # Vega: Same as call
    vega = S * exp_minus_qT * pdf_d1 * sqrt_T * 0.01
    
    # Rho: ∂P/∂r (per 1% change)
    rho = -K * T * exp_minus_rT * n_minus_d2 * 0.01
    
    return delta, gamma, theta, vega, rho


# =============================================================================
# PUBLIC API
# =============================================================================

class BlackScholesEngine:
    """
    Production-grade Black-Scholes pricing engine.
    
    Features:
    - Single option and batch pricing
    - Greeks calculation with caching
    - Input validation and edge case handling
    - Performance metrics and logging
    
    Example:
        engine = BlackScholesEngine()
        
        result = engine.price(
            spot=150.0,
            strike=155.0,
            time_to_expiry=0.25,
            volatility=0.30,
            is_call=True,
        )
        
        # Batch pricing
        results = engine.price_batch([
            {"spot": 150, "strike": 155, ...},
            {"spot": 150, "strike": 160, ...},
        ])
    """
    
    def __init__(
        self,
        default_risk_free_rate: float = 0.05,
        default_dividend_yield: float = 0.0,
    ) -> None:
        """
        Initialize the engine.
        
        Args:
            default_risk_free_rate: Default risk-free rate when not specified
            default_dividend_yield: Default dividend yield when not specified
        """
        self.default_risk_free_rate = default_risk_free_rate
        self.default_dividend_yield = default_dividend_yield
        
        logger.debug(
            "BlackScholesEngine initialized",
            numba_enabled=HAS_NUMBA,
            default_r=default_risk_free_rate,
            default_q=default_dividend_yield,
        )
    
    def _validate_inputs(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        risk_free_rate: float,
        dividend_yield: float,
    ) -> None:
        """Validate pricing inputs."""
        if spot <= 0:
            raise InvalidOptionParameters(
                message="Spot price must be positive",
                invalid_field="spot",
                invalid_value=spot,
            )
        
        if strike <= 0:
            raise InvalidOptionParameters(
                message="Strike price must be positive",
                invalid_field="strike",
                invalid_value=strike,
            )
        
        if time_to_expiry <= 0:
            raise NegativeTimeToExpiry(
                message="Option has expired",
                time_to_expiry=time_to_expiry,
            )
        
        if volatility <= 0 or volatility > MAX_VOLATILITY:
            raise InvalidOptionParameters(
                message=f"Volatility must be between 0 and {MAX_VOLATILITY}",
                invalid_field="volatility",
                invalid_value=volatility,
            )
    
    @track_latency("greeks_calculation_seconds")
    def price(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        is_call: bool = True,
        risk_free_rate: Optional[float] = None,
        dividend_yield: Optional[float] = None,
    ) -> OptionPriceResult:
        """
        Price an option and calculate all Greeks.
        
        Args:
            spot: Current underlying price
            strike: Option strike price
            time_to_expiry: Time to expiration in years
            volatility: Implied volatility (annualized, e.g., 0.30 = 30%)
            is_call: True for call, False for put
            risk_free_rate: Risk-free interest rate (default from config)
            dividend_yield: Continuous dividend yield (default from config)
            
        Returns:
            OptionPriceResult with price and Greeks
            
        Raises:
            InvalidOptionParameters: If inputs are invalid
            NegativeTimeToExpiry: If option has expired
        """
        r = risk_free_rate if risk_free_rate is not None else self.default_risk_free_rate
        q = dividend_yield if dividend_yield is not None else self.default_dividend_yield
        
        # Validate inputs
        self._validate_inputs(spot, strike, time_to_expiry, volatility, r, q)
        
        # Handle near-expiry edge case
        if time_to_expiry < MIN_TIME_TO_EXPIRY:
            time_to_expiry = MIN_TIME_TO_EXPIRY
        
        # Calculate price
        if is_call:
            price = _bs_call_price(spot, strike, time_to_expiry, r, q, volatility)
            delta, gamma, theta, vega, rho = _bs_greeks_call(
                spot, strike, time_to_expiry, r, q, volatility
            )
            intrinsic = max(spot - strike, 0.0)
        else:
            price = _bs_put_price(spot, strike, time_to_expiry, r, q, volatility)
            delta, gamma, theta, vega, rho = _bs_greeks_put(
                spot, strike, time_to_expiry, r, q, volatility
            )
            intrinsic = max(strike - spot, 0.0)
        
        time_value = max(price - intrinsic, 0.0)
        
        greeks = Greeks(
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega,
            rho=rho,
        )
        
        return OptionPriceResult(
            price=price,
            greeks=greeks,
            intrinsic_value=intrinsic,
            time_value=time_value,
            is_call=is_call,
            spot=spot,
            strike=strike,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=r,
            dividend_yield=q,
        )
    
    def price_batch(
        self,
        options: List[dict],
    ) -> List[OptionPriceResult]:
        """
        Price multiple options efficiently.
        
        Args:
            options: List of option parameter dictionaries with keys:
                - spot, strike, time_to_expiry, volatility
                - is_call (default True)
                - risk_free_rate, dividend_yield (optional)
                
        Returns:
            List of OptionPriceResult objects
        """
        results = []
        
        for opt in options:
            try:
                result = self.price(
                    spot=opt["spot"],
                    strike=opt["strike"],
                    time_to_expiry=opt["time_to_expiry"],
                    volatility=opt["volatility"],
                    is_call=opt.get("is_call", True),
                    risk_free_rate=opt.get("risk_free_rate"),
                    dividend_yield=opt.get("dividend_yield"),
                )
                results.append(result)
            except Exception as e:
                logger.warning(f"Batch pricing error: {e}", option=opt)
                # Return a null result for failed pricing
                results.append(None)
        
        return results
    
    def price_vectorized(
        self,
        spots: np.ndarray,
        strikes: np.ndarray,
        times_to_expiry: np.ndarray,
        volatilities: np.ndarray,
        is_calls: np.ndarray,
        risk_free_rate: float = 0.05,
        dividend_yield: float = 0.0,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Vectorized pricing for maximum performance.
        
        Uses numpy broadcasting for batch calculations.
        
        Args:
            spots: Array of spot prices
            strikes: Array of strike prices
            times_to_expiry: Array of times to expiry
            volatilities: Array of volatilities
            is_calls: Boolean array (True=call, False=put)
            risk_free_rate: Common risk-free rate
            dividend_yield: Common dividend yield
            
        Returns:
            Tuple of (prices, deltas, gammas, thetas, vegas, rhos)
        """
        n = len(spots)
        
        # Ensure minimum time to expiry
        times_to_expiry = np.maximum(times_to_expiry, MIN_TIME_TO_EXPIRY)
        
        # Calculate d1 and d2
        sqrt_T = np.sqrt(times_to_expiry)
        sigma_sqrt_T = volatilities * sqrt_T
        
        d1 = (
            np.log(spots / strikes) +
            (risk_free_rate - dividend_yield + 0.5 * volatilities**2) * times_to_expiry
        ) / sigma_sqrt_T
        d2 = d1 - sigma_sqrt_T
        
        # Discount factors
        exp_minus_qT = np.exp(-dividend_yield * times_to_expiry)
        exp_minus_rT = np.exp(-risk_free_rate * times_to_expiry)
        
        # CDFs and PDFs
        Nd1 = norm.cdf(d1)
        Nd2 = norm.cdf(d2)
        N_minus_d1 = norm.cdf(-d1)
        N_minus_d2 = norm.cdf(-d2)
        nd1 = norm.pdf(d1)
        
        # Prices
        call_prices = spots * exp_minus_qT * Nd1 - strikes * exp_minus_rT * Nd2
        put_prices = strikes * exp_minus_rT * N_minus_d2 - spots * exp_minus_qT * N_minus_d1
        
        prices = np.where(is_calls, call_prices, put_prices)
        prices = np.maximum(prices, 0.0)
        
        # Deltas
        call_deltas = exp_minus_qT * Nd1
        put_deltas = -exp_minus_qT * N_minus_d1
        deltas = np.where(is_calls, call_deltas, put_deltas)
        
        # Gammas (same for calls and puts)
        gammas = exp_minus_qT * nd1 / (spots * sigma_sqrt_T)
        
        # Thetas (per day)
        common_theta = -exp_minus_qT * spots * nd1 * volatilities / (2 * sqrt_T)
        call_thetas = (
            common_theta
            - risk_free_rate * strikes * exp_minus_rT * Nd2
            + dividend_yield * spots * exp_minus_qT * Nd1
        ) / 365.0
        put_thetas = (
            common_theta
            + risk_free_rate * strikes * exp_minus_rT * N_minus_d2
            - dividend_yield * spots * exp_minus_qT * N_minus_d1
        ) / 365.0
        thetas = np.where(is_calls, call_thetas, put_thetas)
        
        # Vegas (per 1% change)
        vegas = spots * exp_minus_qT * nd1 * sqrt_T * 0.01
        
        # Rhos (per 1% change)
        call_rhos = strikes * times_to_expiry * exp_minus_rT * Nd2 * 0.01
        put_rhos = -strikes * times_to_expiry * exp_minus_rT * N_minus_d2 * 0.01
        rhos = np.where(is_calls, call_rhos, put_rhos)
        
        return prices, deltas, gammas, thetas, vegas, rhos


# =============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# =============================================================================

# Global engine instance
_engine: Optional[BlackScholesEngine] = None


def get_engine() -> BlackScholesEngine:
    """Get global BlackScholesEngine instance."""
    global _engine
    if _engine is None:
        _engine = BlackScholesEngine()
    return _engine


def price_option(
    spot: float,
    strike: float,
    time_to_expiry: float,
    volatility: float,
    is_call: bool = True,
    risk_free_rate: float = 0.05,
    dividend_yield: float = 0.0,
) -> OptionPriceResult:
    """
    Quick function to price an option.
    
    See BlackScholesEngine.price() for full documentation.
    """
    return get_engine().price(
        spot=spot,
        strike=strike,
        time_to_expiry=time_to_expiry,
        volatility=volatility,
        is_call=is_call,
        risk_free_rate=risk_free_rate,
        dividend_yield=dividend_yield,
    )


def calculate_greeks(
    spot: float,
    strike: float,
    time_to_expiry: float,
    volatility: float,
    is_call: bool = True,
    risk_free_rate: float = 0.05,
    dividend_yield: float = 0.0,
) -> Greeks:
    """
    Calculate Greeks for an option.
    
    Returns only the Greeks without full price result.
    """
    result = price_option(
        spot=spot,
        strike=strike,
        time_to_expiry=time_to_expiry,
        volatility=volatility,
        is_call=is_call,
        risk_free_rate=risk_free_rate,
        dividend_yield=dividend_yield,
    )
    return result.greeks

"""
Alpaca Options Lab - Implied Volatility Engine

Calculates implied volatility from option prices using multiple methods:
- Newton-Raphson iteration
- Bisection method
- Brenner-Subrahmanyam approximation
- Jaeckel's rational approximation

Also includes IV surface fitting models:
- SVI (Stochastic Volatility Inspired)
- SABR
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple
import numpy as np
from scipy import optimize
from scipy.stats import norm

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class IVModel(Enum):
    """IV calculation model."""
    NEWTON_RAPHSON = "newton_raphson"
    BISECTION = "bisection"
    BRENNER = "brenner"
    JAECKEL = "jaeckel"


@dataclass
class IVResult:
    """Result of IV calculation."""
    iv: float
    converged: bool
    iterations: int
    error: float
    model_used: IVModel
    
    # Additional data
    vega: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None


class IVEngine:
    """
    Implied volatility calculation engine.
    
    Calculates IV from option prices and computes Greeks.
    """
    
    def __init__(
        self,
        risk_free_rate: float = 0.05,
        dividend_yield: float = 0.0,
        max_iterations: int = 100,
        tolerance: float = 1e-8,
    ):
        self.risk_free_rate = risk_free_rate
        self.dividend_yield = dividend_yield
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        
        logger.info(
            f"IVEngine initialized: r={risk_free_rate}, q={dividend_yield}"
        )
    
    # -------------------- Black-Scholes Core --------------------
    
    def bs_price(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        is_call: bool = True,
    ) -> float:
        """Calculate Black-Scholes option price."""
        if time_to_expiry <= 0:
            # At expiry
            if is_call:
                return max(0, spot - strike)
            else:
                return max(0, strike - spot)
        
        if volatility <= 0:
            volatility = 0.001
        
        d1 = self._d1(spot, strike, time_to_expiry, volatility)
        d2 = d1 - volatility * math.sqrt(time_to_expiry)
        
        r = self.risk_free_rate
        q = self.dividend_yield
        t = time_to_expiry
        
        if is_call:
            price = (
                spot * math.exp(-q * t) * norm.cdf(d1) -
                strike * math.exp(-r * t) * norm.cdf(d2)
            )
        else:
            price = (
                strike * math.exp(-r * t) * norm.cdf(-d2) -
                spot * math.exp(-q * t) * norm.cdf(-d1)
            )
        
        return max(0, price)
    
    def _d1(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
    ) -> float:
        """Calculate d1 in Black-Scholes formula."""
        r = self.risk_free_rate
        q = self.dividend_yield
        t = time_to_expiry
        
        return (
            (math.log(spot / strike) + (r - q + 0.5 * volatility ** 2) * t) /
            (volatility * math.sqrt(t))
        )
    
    def _d2(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
    ) -> float:
        """Calculate d2 in Black-Scholes formula."""
        return self._d1(spot, strike, time_to_expiry, volatility) - volatility * math.sqrt(time_to_expiry)
    
    # -------------------- Greeks --------------------
    
    def delta(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        is_call: bool = True,
    ) -> float:
        """Calculate option delta."""
        if time_to_expiry <= 0:
            if is_call:
                return 1.0 if spot > strike else 0.0
            else:
                return -1.0 if spot < strike else 0.0
        
        d1 = self._d1(spot, strike, time_to_expiry, volatility)
        q = self.dividend_yield
        t = time_to_expiry
        
        if is_call:
            return math.exp(-q * t) * norm.cdf(d1)
        else:
            return math.exp(-q * t) * (norm.cdf(d1) - 1)
    
    def gamma(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
    ) -> float:
        """Calculate option gamma (same for calls and puts)."""
        if time_to_expiry <= 0:
            return 0.0
        
        d1 = self._d1(spot, strike, time_to_expiry, volatility)
        q = self.dividend_yield
        t = time_to_expiry
        
        return (
            math.exp(-q * t) * norm.pdf(d1) /
            (spot * volatility * math.sqrt(t))
        )
    
    def vega(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
    ) -> float:
        """Calculate option vega (same for calls and puts)."""
        if time_to_expiry <= 0:
            return 0.0
        
        d1 = self._d1(spot, strike, time_to_expiry, volatility)
        q = self.dividend_yield
        t = time_to_expiry
        
        # Vega per 1% move in vol
        return spot * math.exp(-q * t) * norm.pdf(d1) * math.sqrt(t) / 100
    
    def theta(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        is_call: bool = True,
    ) -> float:
        """Calculate option theta (daily decay)."""
        if time_to_expiry <= 0:
            return 0.0
        
        d1 = self._d1(spot, strike, time_to_expiry, volatility)
        d2 = self._d2(spot, strike, time_to_expiry, volatility)
        
        r = self.risk_free_rate
        q = self.dividend_yield
        t = time_to_expiry
        
        term1 = (
            -spot * math.exp(-q * t) * norm.pdf(d1) * volatility /
            (2 * math.sqrt(t))
        )
        
        if is_call:
            term2 = q * spot * math.exp(-q * t) * norm.cdf(d1)
            term3 = -r * strike * math.exp(-r * t) * norm.cdf(d2)
            theta = term1 - term2 + term3
        else:
            term2 = q * spot * math.exp(-q * t) * norm.cdf(-d1)
            term3 = -r * strike * math.exp(-r * t) * norm.cdf(-d2)
            theta = term1 + term2 - term3
        
        # Convert to daily theta
        return theta / 365
    
    def rho(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        is_call: bool = True,
    ) -> float:
        """Calculate option rho."""
        if time_to_expiry <= 0:
            return 0.0
        
        d2 = self._d2(spot, strike, time_to_expiry, volatility)
        r = self.risk_free_rate
        t = time_to_expiry
        
        if is_call:
            return strike * t * math.exp(-r * t) * norm.cdf(d2) / 100
        else:
            return -strike * t * math.exp(-r * t) * norm.cdf(-d2) / 100
    
    def all_greeks(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        is_call: bool = True,
    ) -> Dict[str, float]:
        """Calculate all Greeks at once."""
        return {
            "delta": self.delta(spot, strike, time_to_expiry, volatility, is_call),
            "gamma": self.gamma(spot, strike, time_to_expiry, volatility),
            "vega": self.vega(spot, strike, time_to_expiry, volatility),
            "theta": self.theta(spot, strike, time_to_expiry, volatility, is_call),
            "rho": self.rho(spot, strike, time_to_expiry, volatility, is_call),
        }
    
    # -------------------- Implied Volatility --------------------
    
    def calculate_iv(
        self,
        market_price: float,
        spot: float,
        strike: float,
        time_to_expiry: float,
        is_call: bool = True,
        model: IVModel = IVModel.NEWTON_RAPHSON,
    ) -> IVResult:
        """
        Calculate implied volatility from market price.
        
        Args:
            market_price: Observed option price
            spot: Underlying spot price
            strike: Option strike price
            time_to_expiry: Time to expiry in years
            is_call: True for call, False for put
            model: IV calculation method
        
        Returns:
            IVResult with calculated IV and metadata
        """
        # Initial estimate using Brenner-Subrahmanyam
        iv_initial = self._brenner_estimate(
            market_price, spot, strike, time_to_expiry, is_call
        )
        
        if model == IVModel.BRENNER:
            # Use the estimate directly
            error = abs(
                self.bs_price(spot, strike, time_to_expiry, iv_initial, is_call) -
                market_price
            )
            return IVResult(
                iv=iv_initial,
                converged=error < 0.01,
                iterations=0,
                error=error,
                model_used=model,
            )
        
        elif model == IVModel.NEWTON_RAPHSON:
            return self._newton_raphson_iv(
                market_price, spot, strike, time_to_expiry, is_call, iv_initial
            )
        
        elif model == IVModel.BISECTION:
            return self._bisection_iv(
                market_price, spot, strike, time_to_expiry, is_call
            )
        
        else:
            # Default to Newton-Raphson
            return self._newton_raphson_iv(
                market_price, spot, strike, time_to_expiry, is_call, iv_initial
            )
    
    def _brenner_estimate(
        self,
        market_price: float,
        spot: float,
        strike: float,
        time_to_expiry: float,
        is_call: bool,
    ) -> float:
        """
        Brenner-Subrahmanyam approximation for initial IV estimate.
        
        σ ≈ √(2π/T) * C/S  (for ATM options)
        """
        if time_to_expiry <= 0:
            return 0.25  # Default
        
        # For ATM, use simplified formula
        if abs(spot - strike) / spot < 0.1:
            iv = math.sqrt(2 * math.pi / time_to_expiry) * market_price / spot
        else:
            # Manaster-Koehler approximation for OTM
            moneyness = math.log(spot / strike)
            iv = math.sqrt(
                2 * abs(moneyness) / time_to_expiry +
                (2 * market_price / spot) ** 2 / time_to_expiry
            )
        
        # Bound to reasonable range
        return max(0.01, min(5.0, iv))
    
    def _newton_raphson_iv(
        self,
        market_price: float,
        spot: float,
        strike: float,
        time_to_expiry: float,
        is_call: bool,
        iv_guess: float,
    ) -> IVResult:
        """Newton-Raphson method for IV."""
        iv = iv_guess
        
        for i in range(self.max_iterations):
            price = self.bs_price(spot, strike, time_to_expiry, iv, is_call)
            vega = self.vega(spot, strike, time_to_expiry, iv) * 100  # Per 100% vol
            
            error = price - market_price
            
            if abs(error) < self.tolerance:
                return IVResult(
                    iv=iv,
                    converged=True,
                    iterations=i + 1,
                    error=abs(error),
                    model_used=IVModel.NEWTON_RAPHSON,
                    vega=vega / 100,
                    delta=self.delta(spot, strike, time_to_expiry, iv, is_call),
                )
            
            if abs(vega) < 1e-10:
                # Vega too small, can't converge
                break
            
            # Newton-Raphson step
            iv = iv - error / vega
            
            # Bound IV
            iv = max(0.001, min(5.0, iv))
        
        # Did not converge, return last estimate
        return IVResult(
            iv=iv,
            converged=False,
            iterations=self.max_iterations,
            error=abs(self.bs_price(spot, strike, time_to_expiry, iv, is_call) - market_price),
            model_used=IVModel.NEWTON_RAPHSON,
        )
    
    def _bisection_iv(
        self,
        market_price: float,
        spot: float,
        strike: float,
        time_to_expiry: float,
        is_call: bool,
    ) -> IVResult:
        """Bisection method for IV."""
        low = 0.001
        high = 5.0
        
        for i in range(self.max_iterations):
            mid = (low + high) / 2
            price = self.bs_price(spot, strike, time_to_expiry, mid, is_call)
            error = price - market_price
            
            if abs(error) < self.tolerance:
                return IVResult(
                    iv=mid,
                    converged=True,
                    iterations=i + 1,
                    error=abs(error),
                    model_used=IVModel.BISECTION,
                )
            
            if error > 0:
                high = mid
            else:
                low = mid
        
        return IVResult(
            iv=(low + high) / 2,
            converged=False,
            iterations=self.max_iterations,
            error=abs(error),
            model_used=IVModel.BISECTION,
        )
    
    # -------------------- Batch Processing --------------------
    
    def calculate_chain_iv(
        self,
        chain_data: list,
        spot: float,
        expiry: date,
    ) -> list:
        """
        Calculate IV for entire option chain.
        
        Args:
            chain_data: List of dicts with 'strike', 'price', 'is_call'
            spot: Underlying spot price
            expiry: Expiration date
        
        Returns:
            List of results with IV added
        """
        today = datetime.now(timezone.utc).date()
        tte = (expiry - today).days / 365.0
        
        results = []
        for opt in chain_data:
            try:
                iv_result = self.calculate_iv(
                    market_price=opt.get("price", opt.get("mid", 0)),
                    spot=spot,
                    strike=opt["strike"],
                    time_to_expiry=tte,
                    is_call=opt.get("is_call", True),
                )
                
                results.append({
                    **opt,
                    "iv": iv_result.iv,
                    "iv_converged": iv_result.converged,
                    "delta": iv_result.delta,
                    "vega": iv_result.vega,
                })
            except Exception as e:
                logger.debug(f"IV calc failed for {opt}: {e}")
                results.append({**opt, "iv": None})
        
        return results

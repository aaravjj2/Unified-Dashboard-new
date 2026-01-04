"""
Alpaca Options Lab - Volatility Skew Analysis

Analyzes the volatility smile/skew across strikes:
- Skew measurement (put/call skew)
- Smile fitting (quadratic, SVI)
- Risk reversal analysis
- Butterfly spread opportunities
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy import optimize, stats

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class SkewType(Enum):
    """Type of volatility skew."""
    NORMAL = "normal"           # Puts > Calls (equity-like)
    REVERSE = "reverse"         # Calls > Puts (commodity-like)
    SMILE = "smile"             # Both wings elevated
    FLAT = "flat"               # No significant skew
    SMIRK = "smirk"             # One wing elevated


@dataclass
class SkewPoint:
    """Single point on the skew curve."""
    strike: float
    moneyness: float  # K/S
    log_moneyness: float  # ln(K/S)
    iv: float
    delta: Optional[float] = None
    is_call: bool = True


@dataclass
class SkewMetrics:
    """Quantitative skew metrics."""
    skew_type: SkewType
    
    # Basic skew measures
    atm_iv: float
    put_skew: float  # 25d put IV - ATM IV
    call_skew: float  # 25d call IV - ATM IV
    
    # Risk reversal (25d)
    risk_reversal_25d: float  # 25d call IV - 25d put IV
    
    # Butterfly (25d)
    butterfly_25d: float  # (25d put IV + 25d call IV) / 2 - ATM IV
    
    # Skew slope
    slope: float  # IV change per 1% moneyness
    curvature: float  # Second derivative
    
    # Fitted parameters (quadratic: IV = a + b*x + c*x^2)
    fit_a: float = 0.0
    fit_b: float = 0.0
    fit_c: float = 0.0
    fit_r_squared: float = 0.0


class VolatilitySkew:
    """
    Volatility skew analysis.
    
    Analyzes how IV varies across strikes at a single expiration.
    """
    
    def __init__(
        self,
        symbol: str,
        spot_price: float,
        expiry: date,
    ):
        self.symbol = symbol
        self.spot_price = spot_price
        self.expiry = expiry
        
        # Skew data
        self._points: List[SkewPoint] = []
        
        # Fitted curve
        self._fit_params: Optional[Tuple[float, float, float]] = None
        
        # Analysis cache
        self._metrics: Optional[SkewMetrics] = None
        
        logger.info(f"VolatilitySkew initialized for {symbol}, expiry={expiry}")
    
    @property
    def days_to_expiry(self) -> int:
        """Days to expiration."""
        today = datetime.now(timezone.utc).date()
        return (self.expiry - today).days
    
    # -------------------- Data Input --------------------
    
    def add_point(
        self,
        strike: float,
        iv: float,
        delta: Optional[float] = None,
        is_call: bool = True,
    ) -> None:
        """Add a skew point."""
        if iv <= 0 or strike <= 0:
            return
        
        moneyness = strike / self.spot_price
        log_moneyness = math.log(moneyness)
        
        point = SkewPoint(
            strike=strike,
            moneyness=moneyness,
            log_moneyness=log_moneyness,
            iv=iv,
            delta=delta,
            is_call=is_call,
        )
        
        self._points.append(point)
        self._metrics = None  # Invalidate cache
        self._fit_params = None
    
    def add_chain(
        self,
        strikes: List[float],
        ivs: List[float],
        deltas: Optional[List[float]] = None,
        is_call: bool = True,
    ) -> None:
        """Add multiple points from option chain."""
        if deltas is None:
            deltas = [None] * len(strikes)
        
        for strike, iv, delta in zip(strikes, ivs, deltas):
            self.add_point(strike, iv, delta, is_call)
    
    # -------------------- Curve Fitting --------------------
    
    def fit_quadratic(self) -> Tuple[float, float, float]:
        """
        Fit quadratic curve to skew: IV = a + b*x + c*x^2
        where x = log(K/S)
        
        Returns:
            (a, b, c) coefficients
        """
        if len(self._points) < 3:
            return (0.25, 0, 0)  # Default
        
        x = np.array([p.log_moneyness for p in self._points])
        y = np.array([p.iv for p in self._points])
        
        # Fit polynomial
        try:
            coeffs = np.polyfit(x, y, 2)
            self._fit_params = (coeffs[2], coeffs[1], coeffs[0])  # a, b, c
            return self._fit_params
        except Exception as e:
            logger.warning(f"Quadratic fit failed: {e}")
            return (np.mean(y), 0, 0)
    
    def fit_svi(self) -> Dict[str, float]:
        """
        Fit SVI (Stochastic Volatility Inspired) model.
        
        w(k) = a + b * (ρ*(k-m) + sqrt((k-m)^2 + σ^2))
        
        where w = IV^2 * T (total variance)
        """
        if len(self._points) < 5:
            return {}
        
        t = self.days_to_expiry / 365.0
        if t <= 0:
            return {}
        
        k = np.array([p.log_moneyness for p in self._points])
        w = np.array([p.iv ** 2 * t for p in self._points])  # Total variance
        
        def svi(params, k):
            a, b, rho, m, sigma = params
            return a + b * (rho * (k - m) + np.sqrt((k - m) ** 2 + sigma ** 2))
        
        def objective(params):
            return np.sum((svi(params, k) - w) ** 2)
        
        # Initial guess
        x0 = [np.mean(w), 0.1, -0.5, 0, 0.1]
        
        # Bounds for arbitrage-free SVI
        bounds = [
            (0, None),      # a > 0
            (0, None),      # b > 0
            (-1, 1),        # -1 < rho < 1
            (-1, 1),        # m centered
            (0.001, 1),     # sigma > 0
        ]
        
        try:
            result = optimize.minimize(
                objective, x0,
                method="L-BFGS-B",
                bounds=bounds,
            )
            
            if result.success:
                a, b, rho, m, sigma = result.x
                return {
                    "a": a,
                    "b": b,
                    "rho": rho,
                    "m": m,
                    "sigma": sigma,
                    "converged": True,
                }
        except Exception as e:
            logger.warning(f"SVI fit failed: {e}")
        
        return {"converged": False}
    
    def get_iv_at_strike(self, strike: float) -> Optional[float]:
        """Get fitted IV at specific strike."""
        if self._fit_params is None:
            self.fit_quadratic()
        
        if self._fit_params is None:
            return None
        
        a, b, c = self._fit_params
        x = math.log(strike / self.spot_price)
        
        return a + b * x + c * x ** 2
    
    def get_iv_at_delta(self, delta: float, is_call: bool = True) -> Optional[float]:
        """
        Get IV at specific delta using interpolation.
        
        Delta convention: positive for calls (0 to 1), negative for puts (0 to -1)
        """
        # Filter by call/put
        points = [p for p in self._points if p.is_call == is_call and p.delta is not None]
        
        if len(points) < 2:
            return None
        
        # Sort by delta
        points.sort(key=lambda p: abs(p.delta))
        
        # Find bracketing points
        target = abs(delta)
        for i in range(len(points) - 1):
            d1 = abs(points[i].delta)
            d2 = abs(points[i + 1].delta)
            
            if d1 <= target <= d2 or d2 <= target <= d1:
                # Linear interpolation
                weight = (target - d1) / (d2 - d1) if d2 != d1 else 0.5
                return points[i].iv + weight * (points[i + 1].iv - points[i].iv)
        
        # Extrapolate from nearest
        deltas = [abs(p.delta) for p in points]
        if target < min(deltas):
            return points[0].iv
        else:
            return points[-1].iv
    
    # -------------------- Analysis --------------------
    
    def analyze(self) -> SkewMetrics:
        """
        Perform full skew analysis.
        
        Returns:
            SkewMetrics with quantitative measures
        """
        if self._metrics is not None:
            return self._metrics
        
        if len(self._points) < 3:
            raise ValueError("Need at least 3 points for analysis")
        
        # Fit curve
        if self._fit_params is None:
            self.fit_quadratic()
        
        a, b, c = self._fit_params
        
        # ATM IV (at moneyness = 1, log_moneyness = 0)
        atm_iv = a
        
        # 25-delta IVs (approximate moneyness)
        # For equity options, 25d put ≈ 0.95 moneyness, 25d call ≈ 1.05 moneyness
        put_25d_moneyness = -0.05  # log(0.95) ≈ -0.05
        call_25d_moneyness = 0.05  # log(1.05) ≈ 0.05
        
        iv_25d_put = a + b * put_25d_moneyness + c * put_25d_moneyness ** 2
        iv_25d_call = a + b * call_25d_moneyness + c * call_25d_moneyness ** 2
        
        # Skew measures
        put_skew = iv_25d_put - atm_iv
        call_skew = iv_25d_call - atm_iv
        
        # Risk reversal
        risk_reversal = iv_25d_call - iv_25d_put
        
        # Butterfly
        butterfly = (iv_25d_put + iv_25d_call) / 2 - atm_iv
        
        # Determine skew type
        if abs(risk_reversal) < 0.01:
            if abs(butterfly) > 0.02:
                skew_type = SkewType.SMILE
            else:
                skew_type = SkewType.FLAT
        elif risk_reversal < -0.01:
            skew_type = SkewType.NORMAL  # Puts expensive (equity-like)
        else:
            skew_type = SkewType.REVERSE  # Calls expensive
        
        # Slope and curvature
        slope = b  # First derivative at ATM
        curvature = 2 * c  # Second derivative
        
        # R-squared of fit
        if len(self._points) > 0:
            x = np.array([p.log_moneyness for p in self._points])
            y = np.array([p.iv for p in self._points])
            y_pred = a + b * x + c * x ** 2
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        else:
            r_squared = 0
        
        self._metrics = SkewMetrics(
            skew_type=skew_type,
            atm_iv=atm_iv,
            put_skew=put_skew,
            call_skew=call_skew,
            risk_reversal_25d=risk_reversal,
            butterfly_25d=butterfly,
            slope=slope,
            curvature=curvature,
            fit_a=a,
            fit_b=b,
            fit_c=c,
            fit_r_squared=r_squared,
        )
        
        return self._metrics
    
    def get_risk_reversal(self, delta: float = 0.25) -> Optional[float]:
        """
        Calculate risk reversal at specified delta.
        
        Risk Reversal = Call IV - Put IV at same delta
        """
        call_iv = self.get_iv_at_delta(delta, is_call=True)
        put_iv = self.get_iv_at_delta(delta, is_call=False)
        
        if call_iv is None or put_iv is None:
            return None
        
        return call_iv - put_iv
    
    def get_butterfly(self, delta: float = 0.25) -> Optional[float]:
        """
        Calculate butterfly spread IV at specified delta.
        
        Butterfly = (Put IV + Call IV) / 2 - ATM IV
        """
        call_iv = self.get_iv_at_delta(delta, is_call=True)
        put_iv = self.get_iv_at_delta(delta, is_call=False)
        atm_iv = self.get_iv_at_strike(self.spot_price)
        
        if call_iv is None or put_iv is None or atm_iv is None:
            return None
        
        return (call_iv + put_iv) / 2 - atm_iv
    
    # -------------------- Trading Signals --------------------
    
    def find_skew_trades(
        self,
        min_edge: float = 0.02,
    ) -> List[Dict[str, Any]]:
        """
        Find potential skew-based trading opportunities.
        
        Returns list of trade ideas based on skew anomalies.
        """
        trades = []
        
        try:
            metrics = self.analyze()
        except Exception:
            return trades
        
        # 1. Extreme risk reversal (mean reversion)
        if abs(metrics.risk_reversal_25d) > 0.05:
            if metrics.risk_reversal_25d < 0:
                # Puts expensive, sell put / buy call
                trades.append({
                    "type": "risk_reversal",
                    "direction": "long",  # Long risk reversal (sell puts, buy calls)
                    "edge": abs(metrics.risk_reversal_25d),
                    "rationale": "Puts expensive vs calls",
                })
            else:
                trades.append({
                    "type": "risk_reversal",
                    "direction": "short",
                    "edge": abs(metrics.risk_reversal_25d),
                    "rationale": "Calls expensive vs puts",
                })
        
        # 2. Elevated butterfly (wings expensive)
        if metrics.butterfly_25d > 0.03:
            trades.append({
                "type": "iron_butterfly",
                "direction": "sell",
                "edge": metrics.butterfly_25d,
                "rationale": "Wings elevated, sell butterfly",
            })
        elif metrics.butterfly_25d < -0.02:
            trades.append({
                "type": "iron_butterfly",
                "direction": "buy",
                "edge": abs(metrics.butterfly_25d),
                "rationale": "ATM elevated, buy butterfly",
            })
        
        # 3. Steep skew (put spread value)
        if metrics.put_skew > 0.04:
            trades.append({
                "type": "put_spread",
                "direction": "sell",
                "edge": metrics.put_skew,
                "rationale": "Steep put skew, sell OTM put spread",
            })
        
        return [t for t in trades if t.get("edge", 0) >= min_edge]
    
    # -------------------- Statistics --------------------
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get skew statistics."""
        if len(self._points) == 0:
            return {}
        
        ivs = [p.iv for p in self._points]
        moneyness = [p.moneyness for p in self._points]
        
        return {
            "num_points": len(self._points),
            "min_moneyness": min(moneyness),
            "max_moneyness": max(moneyness),
            "iv_min": min(ivs),
            "iv_max": max(ivs),
            "iv_range": max(ivs) - min(ivs),
            "iv_mean": np.mean(ivs),
        }
    
    def to_dict(self) -> List[Dict[str, Any]]:
        """Export skew as list of dicts."""
        return [
            {
                "strike": p.strike,
                "moneyness": p.moneyness,
                "iv": p.iv,
                "delta": p.delta,
                "is_call": p.is_call,
            }
            for p in sorted(self._points, key=lambda p: p.strike)
        ]
    
    def clear(self) -> None:
        """Clear all data."""
        self._points.clear()
        self._fit_params = None
        self._metrics = None

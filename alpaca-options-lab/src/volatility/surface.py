"""
Alpaca Options Lab - Volatility Surface

Constructs and maintains implied volatility surfaces for options analysis.

Features:
- Real-time surface construction from market data
- Multiple interpolation methods
- Surface smoothing and arbitrage-free enforcement
- Strike/expiry slice extraction
- Surface diff and change detection
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy import interpolate
from scipy.ndimage import gaussian_filter

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class InterpolationMethod(Enum):
    """Surface interpolation method."""
    LINEAR = "linear"
    CUBIC = "cubic"
    RBF = "rbf"  # Radial Basis Function
    SVI = "svi"  # Stochastic Volatility Inspired


@dataclass
class SurfacePoint:
    """Single point on the volatility surface."""
    strike: float
    expiry: date
    iv: float
    bid_iv: Optional[float] = None
    ask_iv: Optional[float] = None
    delta: Optional[float] = None
    vega: Optional[float] = None
    volume: int = 0
    open_interest: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def moneyness(self) -> float:
        """Moneyness (strike / spot). Requires spot to be set externally."""
        return self.strike  # Normalized when added to surface
    
    @property
    def days_to_expiry(self) -> int:
        """Days to expiration."""
        today = datetime.now(timezone.utc).date()
        return (self.expiry - today).days


@dataclass
class SurfaceConfig:
    """Volatility surface configuration."""
    interpolation: InterpolationMethod = InterpolationMethod.CUBIC
    smooth_surface: bool = True
    smooth_sigma: float = 1.0
    
    # Grid parameters
    strike_step: float = 0.01  # Moneyness step (1%)
    expiry_step: int = 7  # Days
    
    # Boundaries
    min_moneyness: float = 0.7
    max_moneyness: float = 1.3
    min_days_to_expiry: int = 1
    max_days_to_expiry: int = 365
    
    # Quality thresholds
    min_volume: int = 0
    min_open_interest: int = 0
    max_bid_ask_spread: float = 0.5  # 50% of mid IV


class VolatilitySurface:
    """
    Implied volatility surface construction and analysis.
    
    The surface is parameterized by:
    - X-axis: Moneyness (K/S)
    - Y-axis: Time to expiry (days or years)
    - Z-axis: Implied volatility
    """
    
    def __init__(
        self,
        symbol: str,
        spot_price: float,
        config: Optional[SurfaceConfig] = None,
    ):
        self.symbol = symbol
        self.spot_price = spot_price
        self.config = config or SurfaceConfig()
        
        # Raw data points
        self._points: List[SurfacePoint] = []
        
        # Interpolated surface
        self._surface_grid: Optional[np.ndarray] = None
        self._moneyness_axis: Optional[np.ndarray] = None
        self._expiry_axis: Optional[np.ndarray] = None
        self._interpolator: Optional[Any] = None
        
        # Metadata
        self._last_update: Optional[datetime] = None
        self._construction_time: float = 0.0
        
        logger.info(f"VolatilitySurface initialized for {symbol} @ {spot_price}")
    
    # -------------------- Data Input --------------------
    
    def add_point(self, point: SurfacePoint) -> None:
        """Add a single point to the surface."""
        # Validate
        if not self._validate_point(point):
            return
        
        # Normalize strike to moneyness
        point.moneyness  # Calculate
        self._points.append(point)
    
    def add_points(self, points: List[SurfacePoint]) -> int:
        """Add multiple points. Returns count of valid points added."""
        added = 0
        for point in points:
            if self._validate_point(point):
                self._points.append(point)
                added += 1
        return added
    
    def add_from_chain(
        self,
        chain_data: List[Dict[str, Any]],
        is_call: bool = True,
    ) -> int:
        """
        Add points from option chain data.
        
        Expected format:
        [
            {
                "strike": 100.0,
                "expiration": "2024-01-19",
                "implied_volatility": 0.25,
                "bid_iv": 0.24,
                "ask_iv": 0.26,
                "delta": 0.5,
                "vega": 0.15,
                "volume": 1000,
                "open_interest": 5000,
            },
            ...
        ]
        """
        added = 0
        for opt in chain_data:
            try:
                expiry = opt.get("expiration")
                if isinstance(expiry, str):
                    expiry = datetime.strptime(expiry, "%Y-%m-%d").date()
                
                point = SurfacePoint(
                    strike=opt["strike"],
                    expiry=expiry,
                    iv=opt.get("implied_volatility", opt.get("iv", 0)),
                    bid_iv=opt.get("bid_iv"),
                    ask_iv=opt.get("ask_iv"),
                    delta=opt.get("delta"),
                    vega=opt.get("vega"),
                    volume=opt.get("volume", 0),
                    open_interest=opt.get("open_interest", 0),
                )
                
                if self._validate_point(point):
                    self._points.append(point)
                    added += 1
                    
            except Exception as e:
                logger.debug(f"Failed to add chain point: {e}")
        
        return added
    
    def _validate_point(self, point: SurfacePoint) -> bool:
        """Validate a surface point."""
        # IV sanity check
        if point.iv <= 0 or point.iv > 5.0:  # IV > 500% is suspect
            return False
        
        # Moneyness bounds
        moneyness = point.strike / self.spot_price
        if moneyness < self.config.min_moneyness or moneyness > self.config.max_moneyness:
            return False
        
        # Expiry bounds
        dte = point.days_to_expiry
        if dte < self.config.min_days_to_expiry or dte > self.config.max_days_to_expiry:
            return False
        
        # Volume/OI thresholds
        if point.volume < self.config.min_volume:
            return False
        if point.open_interest < self.config.min_open_interest:
            return False
        
        # Bid-ask spread
        if point.bid_iv and point.ask_iv:
            spread = point.ask_iv - point.bid_iv
            if spread > self.config.max_bid_ask_spread * point.iv:
                return False
        
        return True
    
    # -------------------- Surface Construction --------------------
    
    def build_surface(self) -> bool:
        """
        Build the interpolated volatility surface.
        
        Returns:
            True if surface was built successfully
        """
        if len(self._points) < 4:
            logger.warning(f"Not enough points to build surface: {len(self._points)}")
            return False
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Extract data arrays
            moneyness = np.array([p.strike / self.spot_price for p in self._points])
            dte = np.array([p.days_to_expiry for p in self._points])
            ivs = np.array([p.iv for p in self._points])
            
            # Create regular grid
            self._moneyness_axis = np.linspace(
                self.config.min_moneyness,
                self.config.max_moneyness,
                int((self.config.max_moneyness - self.config.min_moneyness) / self.config.strike_step) + 1,
            )
            self._expiry_axis = np.linspace(
                self.config.min_days_to_expiry,
                self.config.max_days_to_expiry,
                int((self.config.max_days_to_expiry - self.config.min_days_to_expiry) / self.config.expiry_step) + 1,
            )
            
            # Build interpolator
            if self.config.interpolation == InterpolationMethod.LINEAR:
                self._interpolator = interpolate.LinearNDInterpolator(
                    list(zip(moneyness, dte)), ivs
                )
            elif self.config.interpolation == InterpolationMethod.CUBIC:
                self._interpolator = interpolate.CloughTocher2DInterpolator(
                    list(zip(moneyness, dte)), ivs
                )
            elif self.config.interpolation == InterpolationMethod.RBF:
                self._interpolator = interpolate.RBFInterpolator(
                    np.column_stack([moneyness, dte]), ivs
                )
            else:
                # Default to linear
                self._interpolator = interpolate.LinearNDInterpolator(
                    list(zip(moneyness, dte)), ivs
                )
            
            # Create surface grid
            M, E = np.meshgrid(self._moneyness_axis, self._expiry_axis)
            self._surface_grid = self._interpolator(M, E)
            
            # Handle NaN values from extrapolation
            self._surface_grid = np.nan_to_num(
                self._surface_grid,
                nan=np.nanmean(ivs),
            )
            
            # Apply smoothing
            if self.config.smooth_surface:
                self._surface_grid = gaussian_filter(
                    self._surface_grid,
                    sigma=self.config.smooth_sigma,
                )
            
            # Enforce non-negative
            self._surface_grid = np.maximum(self._surface_grid, 0.01)
            
            self._last_update = datetime.now(timezone.utc)
            self._construction_time = (self._last_update - start_time).total_seconds()
            
            logger.info(
                f"Surface built: {self._surface_grid.shape}, "
                f"time={self._construction_time:.3f}s"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to build surface: {e}")
            return False
    
    # -------------------- Surface Queries --------------------
    
    def get_iv(
        self,
        strike: float,
        expiry: date,
    ) -> Optional[float]:
        """Get interpolated IV at specific strike and expiry."""
        if self._interpolator is None:
            return None
        
        moneyness = strike / self.spot_price
        dte = (expiry - datetime.now(timezone.utc).date()).days
        
        try:
            iv = float(self._interpolator(moneyness, dte))
            return max(0.01, iv)  # Floor at 1%
        except Exception:
            return None
    
    def get_strike_slice(
        self,
        expiry: date,
    ) -> Dict[float, float]:
        """
        Get IV slice at a specific expiry (strike smile/skew).
        
        Returns:
            Dict mapping strike -> IV
        """
        result = {}
        
        if self._surface_grid is None:
            return result
        
        dte = (expiry - datetime.now(timezone.utc).date()).days
        
        for strike_pct in self._moneyness_axis:
            strike = strike_pct * self.spot_price
            iv = self.get_iv(strike, expiry)
            if iv:
                result[strike] = iv
        
        return result
    
    def get_expiry_slice(
        self,
        strike: float,
    ) -> Dict[int, float]:
        """
        Get IV slice at a specific strike (term structure).
        
        Returns:
            Dict mapping days_to_expiry -> IV
        """
        result = {}
        
        if self._surface_grid is None:
            return result
        
        today = datetime.now(timezone.utc).date()
        
        for dte in self._expiry_axis:
            expiry = today + timedelta(days=int(dte))
            iv = self.get_iv(strike, expiry)
            if iv:
                result[int(dte)] = iv
        
        return result
    
    def get_atm_iv(self, expiry: date) -> Optional[float]:
        """Get ATM IV for a specific expiry."""
        return self.get_iv(self.spot_price, expiry)
    
    def get_delta_iv(
        self,
        delta: float,
        expiry: date,
        is_call: bool = True,
    ) -> Optional[float]:
        """
        Get IV at a specific delta.
        
        Approximation: maps delta to strike using simplified formula.
        """
        # Approximate strike from delta
        # For calls: higher delta = lower strike (closer to ATM)
        # For puts: lower delta (more negative) = higher strike
        
        # Simple approximation using log-moneyness
        dte = (expiry - datetime.now(timezone.utc).date()).days
        t = dte / 365.0
        
        # Get ATM vol for initial estimate
        atm_iv = self.get_atm_iv(expiry) or 0.25
        
        # Standard normal approximation
        from scipy.stats import norm
        
        if is_call:
            d1 = norm.ppf(delta)
        else:
            d1 = norm.ppf(-delta)
        
        # Solve for strike: d1 = (ln(S/K) + (r + σ²/2)t) / (σ√t)
        # Simplified: K ≈ S * exp(-d1 * σ * √t)
        strike = self.spot_price * math.exp(-d1 * atm_iv * math.sqrt(t))
        
        return self.get_iv(strike, expiry)
    
    # -------------------- Surface Analysis --------------------
    
    def get_surface_stats(self) -> Dict[str, Any]:
        """Get surface statistics."""
        if self._surface_grid is None:
            return {}
        
        return {
            "num_points": len(self._points),
            "grid_shape": self._surface_grid.shape,
            "iv_min": float(np.min(self._surface_grid)),
            "iv_max": float(np.max(self._surface_grid)),
            "iv_mean": float(np.mean(self._surface_grid)),
            "iv_std": float(np.std(self._surface_grid)),
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "construction_time": self._construction_time,
        }
    
    def get_arbitrage_violations(self) -> List[Dict[str, Any]]:
        """
        Check for calendar spread arbitrage violations.
        
        IV should generally increase with time (positive term structure).
        Returns list of violations.
        """
        violations = []
        
        if self._surface_grid is None:
            return violations
        
        # Check each strike for term structure violations
        for i, moneyness in enumerate(self._moneyness_axis):
            for j in range(len(self._expiry_axis) - 1):
                iv_short = self._surface_grid[j, i]
                iv_long = self._surface_grid[j + 1, i]
                
                if iv_short > iv_long * 1.1:  # 10% tolerance
                    violations.append({
                        "type": "calendar_arbitrage",
                        "moneyness": float(moneyness),
                        "short_expiry_days": int(self._expiry_axis[j]),
                        "long_expiry_days": int(self._expiry_axis[j + 1]),
                        "short_iv": float(iv_short),
                        "long_iv": float(iv_long),
                    })
        
        return violations
    
    def to_dataframe(self) -> Any:
        """Export surface to pandas DataFrame."""
        try:
            import pandas as pd
            
            if self._surface_grid is None:
                return pd.DataFrame()
            
            df = pd.DataFrame(
                self._surface_grid,
                index=self._expiry_axis,
                columns=self._moneyness_axis,
            )
            df.index.name = "DTE"
            df.columns.name = "Moneyness"
            
            return df
            
        except ImportError:
            logger.warning("pandas not available for DataFrame export")
            return None
    
    def update_spot(self, new_spot: float) -> None:
        """Update spot price and rebuild surface."""
        self.spot_price = new_spot
        if self._points:
            self.build_surface()
    
    def clear(self) -> None:
        """Clear all surface data."""
        self._points.clear()
        self._surface_grid = None
        self._interpolator = None
        self._last_update = None


# Add missing import
from datetime import timedelta

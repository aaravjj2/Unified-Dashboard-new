"""
Alpaca Options Lab - Term Structure Analysis

Analyzes the term structure of implied volatility:
- Contango vs backwardation detection
- Calendar spread opportunities
- Roll cost estimation
- VIX term structure correlation
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy import interpolate, stats

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ContangoBackwardation(Enum):
    """Term structure shape."""
    CONTANGO = "contango"           # Upward sloping (normal)
    BACKWARDATION = "backwardation" # Downward sloping (inverted)
    FLAT = "flat"                   # No significant slope
    MIXED = "mixed"                 # Non-monotonic


@dataclass
class TermStructurePoint:
    """Single point on the term structure."""
    expiry: date
    days_to_expiry: int
    iv: float
    bid_iv: Optional[float] = None
    ask_iv: Optional[float] = None
    strike: Optional[float] = None
    delta: Optional[float] = None


@dataclass
class TermStructureAnalysis:
    """Analysis results for term structure."""
    structure_type: ContangoBackwardation
    slope: float  # Daily IV change per day
    slope_annualized: float  # Annualized slope
    
    # Key points
    front_month_iv: float
    back_month_iv: float
    iv_range: float
    
    # Statistical measures
    r_squared: float
    correlation: float
    
    # Actionable insights
    calendar_spread_edge: float  # Expected edge from calendar spread
    optimal_calendar_expiries: Tuple[date, date]
    
    # Risk metrics
    term_structure_risk: float  # Risk of term structure change


class TermStructure:
    """
    Term structure analysis for implied volatility.
    
    Analyzes how IV changes across expirations at a given delta
    or strike level.
    """
    
    def __init__(
        self,
        symbol: str,
        spot_price: float,
    ):
        self.symbol = symbol
        self.spot_price = spot_price
        
        # Term structure data
        self._points: List[TermStructurePoint] = []
        
        # Interpolated curve
        self._interpolator: Optional[Any] = None
        
        # Analysis cache
        self._analysis: Optional[TermStructureAnalysis] = None
        
        logger.info(f"TermStructure initialized for {symbol}")
    
    # -------------------- Data Input --------------------
    
    def add_point(
        self,
        expiry: date,
        iv: float,
        bid_iv: Optional[float] = None,
        ask_iv: Optional[float] = None,
        strike: Optional[float] = None,
        delta: Optional[float] = None,
    ) -> None:
        """Add a term structure point."""
        today = datetime.now(timezone.utc).date()
        dte = (expiry - today).days
        
        if dte <= 0:
            return
        
        point = TermStructurePoint(
            expiry=expiry,
            days_to_expiry=dte,
            iv=iv,
            bid_iv=bid_iv,
            ask_iv=ask_iv,
            strike=strike,
            delta=delta,
        )
        
        self._points.append(point)
        self._analysis = None  # Invalidate cache
    
    def add_atm_curve(
        self,
        expirations: List[date],
        ivs: List[float],
    ) -> None:
        """Add ATM term structure curve."""
        for expiry, iv in zip(expirations, ivs):
            self.add_point(expiry, iv)
    
    def add_delta_curve(
        self,
        expirations: List[date],
        ivs: List[float],
        delta: float,
    ) -> None:
        """Add constant delta term structure curve."""
        for expiry, iv in zip(expirations, ivs):
            self.add_point(expiry, iv, delta=delta)
    
    # -------------------- Curve Fitting --------------------
    
    def build_curve(self) -> bool:
        """Build interpolated term structure curve."""
        if len(self._points) < 2:
            logger.warning("Not enough points for term structure curve")
            return False
        
        # Sort by DTE
        self._points.sort(key=lambda p: p.days_to_expiry)
        
        # Extract arrays
        dte = np.array([p.days_to_expiry for p in self._points])
        ivs = np.array([p.iv for p in self._points])
        
        # Build interpolator
        try:
            self._interpolator = interpolate.interp1d(
                dte, ivs,
                kind="cubic",
                fill_value="extrapolate",
            )
            return True
        except Exception as e:
            logger.error(f"Failed to build term structure: {e}")
            return False
    
    def get_iv(self, days_to_expiry: int) -> Optional[float]:
        """Get interpolated IV at specific DTE."""
        if self._interpolator is None:
            if not self.build_curve():
                return None
        
        try:
            iv = float(self._interpolator(days_to_expiry))
            return max(0.01, iv)  # Floor at 1%
        except Exception:
            return None
    
    def get_iv_for_date(self, expiry: date) -> Optional[float]:
        """Get IV for specific expiration date."""
        today = datetime.now(timezone.utc).date()
        dte = (expiry - today).days
        return self.get_iv(dte)
    
    # -------------------- Analysis --------------------
    
    def analyze(self) -> TermStructureAnalysis:
        """
        Perform full term structure analysis.
        
        Returns:
            TermStructureAnalysis with insights
        """
        if self._analysis is not None:
            return self._analysis
        
        if len(self._points) < 2:
            raise ValueError("Need at least 2 points for analysis")
        
        # Sort by DTE
        sorted_points = sorted(self._points, key=lambda p: p.days_to_expiry)
        
        dte = np.array([p.days_to_expiry for p in sorted_points])
        ivs = np.array([p.iv for p in sorted_points])
        
        # Linear regression for slope
        slope, intercept, r_value, p_value, std_err = stats.linregress(dte, ivs)
        
        # Determine structure type
        slope_threshold = 0.0001  # 0.01% per day
        
        if slope > slope_threshold:
            structure_type = ContangoBackwardation.CONTANGO
        elif slope < -slope_threshold:
            structure_type = ContangoBackwardation.BACKWARDATION
        else:
            structure_type = ContangoBackwardation.FLAT
        
        # Check for non-monotonic
        diffs = np.diff(ivs)
        if len(diffs) > 1:
            if not (np.all(diffs >= 0) or np.all(diffs <= 0)):
                structure_type = ContangoBackwardation.MIXED
        
        # Key metrics
        front_iv = ivs[0]
        back_iv = ivs[-1]
        
        # Find optimal calendar spread
        calendar_edge, optimal_expiries = self._find_calendar_opportunity(sorted_points)
        
        # Term structure risk (std dev of changes)
        ts_risk = np.std(diffs) if len(diffs) > 0 else 0
        
        self._analysis = TermStructureAnalysis(
            structure_type=structure_type,
            slope=slope,
            slope_annualized=slope * 365,
            front_month_iv=front_iv,
            back_month_iv=back_iv,
            iv_range=back_iv - front_iv,
            r_squared=r_value ** 2,
            correlation=np.corrcoef(dte, ivs)[0, 1],
            calendar_spread_edge=calendar_edge,
            optimal_calendar_expiries=optimal_expiries,
            term_structure_risk=ts_risk,
        )
        
        return self._analysis
    
    def _find_calendar_opportunity(
        self,
        sorted_points: List[TermStructurePoint],
    ) -> Tuple[float, Tuple[date, date]]:
        """Find best calendar spread opportunity."""
        if len(sorted_points) < 2:
            today = datetime.now(timezone.utc).date()
            return 0.0, (today, today)
        
        best_edge = 0.0
        best_pair = (sorted_points[0].expiry, sorted_points[1].expiry)
        
        for i in range(len(sorted_points)):
            for j in range(i + 1, len(sorted_points)):
                short = sorted_points[i]
                long_term = sorted_points[j]
                
                # Edge = IV differential weighted by time difference
                dte_diff = long_term.days_to_expiry - short.days_to_expiry
                if dte_diff > 0:
                    iv_diff = long_term.iv - short.iv
                    edge = iv_diff / (dte_diff / 30)  # Per month
                    
                    if edge > best_edge:
                        best_edge = edge
                        best_pair = (short.expiry, long_term.expiry)
        
        return best_edge, best_pair
    
    def get_roll_cost(
        self,
        from_expiry: date,
        to_expiry: date,
    ) -> Optional[float]:
        """
        Estimate roll cost between expirations.
        
        Returns:
            IV differential (positive = cost, negative = credit)
        """
        from_iv = self.get_iv_for_date(from_expiry)
        to_iv = self.get_iv_for_date(to_expiry)
        
        if from_iv is None or to_iv is None:
            return None
        
        return to_iv - from_iv
    
    def get_calendar_spread_value(
        self,
        short_expiry: date,
        long_expiry: date,
        vega_dollars: float = 100.0,
    ) -> Dict[str, float]:
        """
        Estimate calendar spread value and risk.
        
        Args:
            short_expiry: Near-term expiration (sell)
            long_expiry: Far-term expiration (buy)
            vega_dollars: Dollar vega per contract
        
        Returns:
            Dict with edge, risk, and expected P&L
        """
        short_iv = self.get_iv_for_date(short_expiry)
        long_iv = self.get_iv_for_date(long_expiry)
        
        if short_iv is None or long_iv is None:
            return {}
        
        iv_diff = short_iv - long_iv  # Positive if in contango
        
        # Estimate theta differential
        today = datetime.now(timezone.utc).date()
        short_dte = (short_expiry - today).days
        long_dte = (long_expiry - today).days
        
        # Rough theta estimate (decays faster for short-dated)
        short_theta = -short_iv / (2 * np.sqrt(short_dte / 365)) if short_dte > 0 else 0
        long_theta = -long_iv / (2 * np.sqrt(long_dte / 365)) if long_dte > 0 else 0
        
        net_theta = short_theta - long_theta  # Positive = time decay in your favor
        
        return {
            "short_expiry": short_expiry.isoformat(),
            "long_expiry": long_expiry.isoformat(),
            "short_iv": short_iv,
            "long_iv": long_iv,
            "iv_differential": iv_diff,
            "net_vega": vega_dollars * (long_iv - short_iv) / 0.01,
            "daily_theta_edge": net_theta * vega_dollars,
            "expected_profit_to_short_expiry": net_theta * vega_dollars * short_dte,
        }
    
    # -------------------- Statistics --------------------
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get term structure statistics."""
        if len(self._points) == 0:
            return {}
        
        ivs = [p.iv for p in self._points]
        dtes = [p.days_to_expiry for p in self._points]
        
        return {
            "num_points": len(self._points),
            "min_dte": min(dtes),
            "max_dte": max(dtes),
            "iv_min": min(ivs),
            "iv_max": max(ivs),
            "iv_mean": np.mean(ivs),
            "iv_std": np.std(ivs),
        }
    
    def to_dict(self) -> List[Dict[str, Any]]:
        """Export term structure as list of dicts."""
        return [
            {
                "expiry": p.expiry.isoformat(),
                "days_to_expiry": p.days_to_expiry,
                "iv": p.iv,
                "bid_iv": p.bid_iv,
                "ask_iv": p.ask_iv,
            }
            for p in sorted(self._points, key=lambda p: p.days_to_expiry)
        ]
    
    def clear(self) -> None:
        """Clear all data."""
        self._points.clear()
        self._interpolator = None
        self._analysis = None

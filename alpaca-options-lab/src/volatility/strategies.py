"""
Alpaca Options Lab - Volatility-Based Strategies

Trading strategies that exploit volatility anomalies:
- Calendar spread arbitrage
- Volatility surface arbitrage
- Skew trading
- Term structure trades
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from src.volatility.surface import VolatilitySurface
from src.volatility.term_structure import TermStructure, ContangoBackwardation
from src.volatility.skew import VolatilitySkew, SkewType
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class VolTradeSignal:
    """Signal from volatility strategy."""
    strategy: str
    symbol: str
    direction: str  # "long_vol", "short_vol", "neutral"
    confidence: float  # 0-1
    
    # Trade structure
    legs: List[Dict[str, Any]] = field(default_factory=list)
    net_premium: float = 0.0  # Positive = credit
    
    # Risk/reward
    max_profit: Optional[float] = None
    max_loss: Optional[float] = None
    expected_value: float = 0.0
    
    # Context
    rationale: str = ""
    vol_edge: float = 0.0  # IV edge in percentage points
    
    # Timestamps
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: Optional[datetime] = None


class VolStrategy(ABC):
    """Base class for volatility strategies."""
    
    def __init__(self, symbol: str, spot_price: float):
        self.symbol = symbol
        self.spot_price = spot_price
    
    @abstractmethod
    def generate_signals(self) -> List[VolTradeSignal]:
        """Generate trading signals."""
        pass
    
    @abstractmethod
    def validate_trade(self, signal: VolTradeSignal) -> bool:
        """Validate a trade signal."""
        pass


class CalendarSpreadFinder(VolStrategy):
    """
    Find calendar spread opportunities.
    
    Looks for:
    1. Steep term structure (rich short-dated, cheap long-dated)
    2. IV differential exceeding historical norms
    3. Upcoming events that could flatten term structure
    """
    
    def __init__(
        self,
        symbol: str,
        spot_price: float,
        term_structure: TermStructure,
    ):
        super().__init__(symbol, spot_price)
        self.term_structure = term_structure
        
        # Parameters
        self.min_iv_differential = 0.02  # 2% IV difference
        self.min_dte_spread = 7  # Minimum days between legs
        self.max_dte_spread = 60  # Maximum days between legs
        self.min_confidence = 0.6
    
    def generate_signals(self) -> List[VolTradeSignal]:
        """Find calendar spread opportunities."""
        signals = []
        
        try:
            analysis = self.term_structure.analyze()
        except Exception as e:
            logger.warning(f"Term structure analysis failed: {e}")
            return signals
        
        # 1. Contango play: sell short-dated, buy long-dated
        if analysis.structure_type == ContangoBackwardation.CONTANGO:
            if analysis.iv_range >= self.min_iv_differential:
                short_exp, long_exp = analysis.optimal_calendar_expiries
                
                signals.append(VolTradeSignal(
                    strategy="calendar_spread",
                    symbol=self.symbol,
                    direction="short_vol",  # Net short front-month vol
                    confidence=min(1.0, analysis.r_squared + 0.2),
                    legs=[
                        {
                            "action": "sell",
                            "expiry": short_exp.isoformat(),
                            "strike": self.spot_price,  # ATM
                            "type": "call",
                            "quantity": 1,
                        },
                        {
                            "action": "buy",
                            "expiry": long_exp.isoformat(),
                            "strike": self.spot_price,  # ATM
                            "type": "call",
                            "quantity": 1,
                        },
                    ],
                    rationale=(
                        f"Contango term structure: {analysis.front_month_iv:.1%} front vs "
                        f"{analysis.back_month_iv:.1%} back. Edge: {analysis.calendar_spread_edge:.2%}/month"
                    ),
                    vol_edge=analysis.iv_range,
                    expected_value=analysis.calendar_spread_edge * 100,  # Rough estimate
                ))
        
        # 2. Backwardation play: opposite direction
        elif analysis.structure_type == ContangoBackwardation.BACKWARDATION:
            if abs(analysis.iv_range) >= self.min_iv_differential:
                short_exp, long_exp = analysis.optimal_calendar_expiries
                
                signals.append(VolTradeSignal(
                    strategy="reverse_calendar",
                    symbol=self.symbol,
                    direction="long_vol",  # Net long front-month vol
                    confidence=min(1.0, analysis.r_squared + 0.1),
                    legs=[
                        {
                            "action": "buy",
                            "expiry": short_exp.isoformat(),
                            "strike": self.spot_price,
                            "type": "put",
                            "quantity": 1,
                        },
                        {
                            "action": "sell",
                            "expiry": long_exp.isoformat(),
                            "strike": self.spot_price,
                            "type": "put",
                            "quantity": 1,
                        },
                    ],
                    rationale=(
                        f"Backwardation: {analysis.front_month_iv:.1%} front vs "
                        f"{analysis.back_month_iv:.1%} back. Expect normalization."
                    ),
                    vol_edge=abs(analysis.iv_range),
                ))
        
        return [s for s in signals if s.confidence >= self.min_confidence]
    
    def validate_trade(self, signal: VolTradeSignal) -> bool:
        """Validate calendar spread trade."""
        if len(signal.legs) != 2:
            return False
        
        # Check that one leg is buy, one is sell
        actions = [leg["action"] for leg in signal.legs]
        if sorted(actions) != ["buy", "sell"]:
            return False
        
        # Check IV edge
        if signal.vol_edge < self.min_iv_differential:
            return False
        
        return True


class VolArbitrage(VolStrategy):
    """
    Find volatility surface arbitrage opportunities.
    
    Detects:
    1. Calendar arbitrage (IV inversions in term structure)
    2. Butterfly arbitrage (convexity violations in skew)
    3. Box spread mispricings
    """
    
    def __init__(
        self,
        symbol: str,
        spot_price: float,
        surface: VolatilitySurface,
    ):
        super().__init__(symbol, spot_price)
        self.surface = surface
        
        # Thresholds
        self.min_arbitrage_edge = 0.01  # 1% IV
        self.calendar_tolerance = 0.02
    
    def generate_signals(self) -> List[VolTradeSignal]:
        """Find arbitrage opportunities on vol surface."""
        signals = []
        
        # Check for calendar arbitrage
        violations = self.surface.get_arbitrage_violations()
        
        for violation in violations:
            if violation["type"] == "calendar_arbitrage":
                iv_diff = violation["short_iv"] - violation["long_iv"]
                
                if iv_diff > self.min_arbitrage_edge:
                    signals.append(VolTradeSignal(
                        strategy="calendar_arbitrage",
                        symbol=self.symbol,
                        direction="neutral",
                        confidence=0.9,  # Arbitrage is high confidence
                        legs=[
                            {
                                "action": "sell",
                                "expiry_days": violation["short_expiry_days"],
                                "moneyness": violation["moneyness"],
                                "type": "straddle",
                                "quantity": 1,
                            },
                            {
                                "action": "buy",
                                "expiry_days": violation["long_expiry_days"],
                                "moneyness": violation["moneyness"],
                                "type": "straddle",
                                "quantity": 1,
                            },
                        ],
                        rationale=(
                            f"Calendar arbitrage: {violation['short_iv']:.1%} short vs "
                            f"{violation['long_iv']:.1%} long at {violation['moneyness']:.2f} moneyness"
                        ),
                        vol_edge=iv_diff,
                        expected_value=iv_diff * 100,  # Vega approximation
                    ))
        
        return signals
    
    def validate_trade(self, signal: VolTradeSignal) -> bool:
        """Validate arbitrage trade."""
        return signal.vol_edge >= self.min_arbitrage_edge


class SkewTrade(VolStrategy):
    """
    Skew-based trading strategies.
    
    Trades based on:
    1. Extreme risk reversal
    2. Elevated butterfly
    3. Skew normalization
    """
    
    def __init__(
        self,
        symbol: str,
        spot_price: float,
        skew: VolatilitySkew,
    ):
        super().__init__(symbol, spot_price)
        self.skew = skew
        
        # Thresholds
        self.risk_reversal_threshold = 0.04  # 4% RR
        self.butterfly_threshold = 0.03  # 3%
        self.min_confidence = 0.5
    
    def generate_signals(self) -> List[VolTradeSignal]:
        """Generate skew-based trade signals."""
        signals = []
        
        try:
            metrics = self.skew.analyze()
        except Exception as e:
            logger.warning(f"Skew analysis failed: {e}")
            return signals
        
        expiry = self.skew.expiry
        
        # 1. Risk Reversal Trade
        if abs(metrics.risk_reversal_25d) > self.risk_reversal_threshold:
            if metrics.risk_reversal_25d < 0:
                # Puts expensive, sell put spread / buy call spread
                signals.append(VolTradeSignal(
                    strategy="risk_reversal",
                    symbol=self.symbol,
                    direction="long_risk",
                    confidence=min(0.8, metrics.fit_r_squared + 0.3),
                    legs=[
                        {
                            "action": "sell",
                            "expiry": expiry.isoformat(),
                            "delta": -0.25,
                            "type": "put",
                            "quantity": 1,
                        },
                        {
                            "action": "buy",
                            "expiry": expiry.isoformat(),
                            "delta": 0.25,
                            "type": "call",
                            "quantity": 1,
                        },
                    ],
                    rationale=(
                        f"Puts overpriced: 25d RR = {metrics.risk_reversal_25d:.1%}. "
                        f"Sell puts, buy calls."
                    ),
                    vol_edge=abs(metrics.risk_reversal_25d),
                ))
            else:
                # Calls expensive
                signals.append(VolTradeSignal(
                    strategy="risk_reversal",
                    symbol=self.symbol,
                    direction="short_risk",
                    confidence=min(0.8, metrics.fit_r_squared + 0.3),
                    legs=[
                        {
                            "action": "buy",
                            "expiry": expiry.isoformat(),
                            "delta": -0.25,
                            "type": "put",
                            "quantity": 1,
                        },
                        {
                            "action": "sell",
                            "expiry": expiry.isoformat(),
                            "delta": 0.25,
                            "type": "call",
                            "quantity": 1,
                        },
                    ],
                    rationale=(
                        f"Calls overpriced: 25d RR = {metrics.risk_reversal_25d:.1%}. "
                        f"Sell calls, buy puts."
                    ),
                    vol_edge=abs(metrics.risk_reversal_25d),
                ))
        
        # 2. Butterfly Trade (wings vs ATM)
        if abs(metrics.butterfly_25d) > self.butterfly_threshold:
            if metrics.butterfly_25d > 0:
                # Wings expensive, sell iron butterfly
                signals.append(VolTradeSignal(
                    strategy="iron_butterfly",
                    symbol=self.symbol,
                    direction="short_wings",
                    confidence=min(0.7, metrics.fit_r_squared + 0.2),
                    legs=[
                        {
                            "action": "buy",
                            "expiry": expiry.isoformat(),
                            "strike": self.spot_price,
                            "type": "straddle",
                            "quantity": 1,
                        },
                        {
                            "action": "sell",
                            "expiry": expiry.isoformat(),
                            "delta": -0.25,
                            "type": "put",
                            "quantity": 1,
                        },
                        {
                            "action": "sell",
                            "expiry": expiry.isoformat(),
                            "delta": 0.25,
                            "type": "call",
                            "quantity": 1,
                        },
                    ],
                    rationale=(
                        f"Wings elevated: Butterfly = {metrics.butterfly_25d:.1%}. "
                        f"Buy ATM, sell wings."
                    ),
                    vol_edge=abs(metrics.butterfly_25d),
                ))
            else:
                # ATM expensive, buy iron butterfly
                signals.append(VolTradeSignal(
                    strategy="iron_butterfly",
                    symbol=self.symbol,
                    direction="long_wings",
                    confidence=min(0.7, metrics.fit_r_squared + 0.2),
                    legs=[
                        {
                            "action": "sell",
                            "expiry": expiry.isoformat(),
                            "strike": self.spot_price,
                            "type": "straddle",
                            "quantity": 1,
                        },
                        {
                            "action": "buy",
                            "expiry": expiry.isoformat(),
                            "delta": -0.25,
                            "type": "put",
                            "quantity": 1,
                        },
                        {
                            "action": "buy",
                            "expiry": expiry.isoformat(),
                            "delta": 0.25,
                            "type": "call",
                            "quantity": 1,
                        },
                    ],
                    rationale=(
                        f"ATM elevated: Butterfly = {metrics.butterfly_25d:.1%}. "
                        f"Sell ATM, buy wings."
                    ),
                    vol_edge=abs(metrics.butterfly_25d),
                ))
        
        return [s for s in signals if s.confidence >= self.min_confidence]
    
    def validate_trade(self, signal: VolTradeSignal) -> bool:
        """Validate skew trade."""
        return signal.vol_edge > 0.01  # At least 1% edge


def find_all_vol_opportunities(
    symbol: str,
    spot_price: float,
    surface: Optional[VolatilitySurface] = None,
    term_structure: Optional[TermStructure] = None,
    skew: Optional[VolatilitySkew] = None,
) -> List[VolTradeSignal]:
    """
    Find all volatility trading opportunities.
    
    Aggregates signals from all vol strategies.
    """
    signals = []
    
    if term_structure:
        finder = CalendarSpreadFinder(symbol, spot_price, term_structure)
        signals.extend(finder.generate_signals())
    
    if surface:
        arb = VolArbitrage(symbol, spot_price, surface)
        signals.extend(arb.generate_signals())
    
    if skew:
        skew_trader = SkewTrade(symbol, spot_price, skew)
        signals.extend(skew_trader.generate_signals())
    
    # Sort by confidence * edge
    signals.sort(
        key=lambda s: s.confidence * s.vol_edge,
        reverse=True,
    )
    
    return signals

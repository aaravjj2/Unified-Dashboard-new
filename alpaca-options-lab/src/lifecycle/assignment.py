"""
Alpaca Options Lab - Assignment Risk Monitor

Production-grade early assignment risk monitoring with:
- ITM detection for short options
- Dividend-based assignment risk
- Time-based risk escalation
- Real-time alerts and notifications

Early Assignment Triggers:
1. Short calls ITM near ex-dividend date
2. Short puts deep ITM near expiration
3. Hard-to-borrow situations
4. High interest rate environment

Risk Levels:
- LOW: >5% OTM or >30 DTE
- MEDIUM: 0-5% OTM or 7-30 DTE ITM
- HIGH: ITM with <7 DTE or near ex-div
- CRITICAL: Deep ITM (<1% time value) near expiry

Usage:
    from src.lifecycle.assignment import AssignmentMonitor, get_assignment_monitor
    
    monitor = get_assignment_monitor()
    
    # Check assignment risk
    risk = monitor.assess_risk(
        symbol="AAPL240119C00145000",
        spot=152.50,
        position_side="short",
    )
    
    print(f"Risk Level: {risk.level}")
    print(f"Reason: {risk.reason}")
    
    # Register alert handler
    @monitor.on_high_risk
    def handle_high_risk(symbol, risk):
        send_alert(f"High assignment risk: {symbol}")
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from src.data.symbology import OptionSymbol, OptionType, parse_osi_symbol
from src.lifecycle.fsm import Position, PositionFSM, get_position_manager
from src.pricing.black_scholes import price_option
from src.utils.config import get_config
from src.utils.logging_config import get_logger
from src.utils.metrics import get_metrics, increment_counter

logger = get_logger(__name__)
metrics = get_metrics()


class RiskLevel(Enum):
    """Assignment risk levels."""
    NONE = "none"           # Long position (no assignment risk)
    LOW = "low"             # Minimal risk
    MEDIUM = "medium"       # Monitor situation
    HIGH = "high"           # Consider action
    CRITICAL = "critical"   # Immediate action recommended


@dataclass
class DividendInfo:
    """Dividend information for a stock."""
    symbol: str
    ex_date: date
    amount: float
    frequency: str = "quarterly"  # quarterly, monthly, annual
    
    @property
    def days_to_ex(self) -> int:
        """Days until ex-dividend date."""
        return (self.ex_date - date.today()).days


@dataclass
class AssignmentRisk:
    """
    Assignment risk assessment result.
    
    Provides detailed breakdown of assignment risk factors.
    """
    symbol: str
    level: RiskLevel
    probability: float  # Estimated probability 0-1
    reason: str
    
    # Risk factors
    intrinsic_value: float = 0.0
    time_value: float = 0.0
    time_value_pct: float = 0.0  # Time value as % of intrinsic
    days_to_expiry: int = 0
    moneyness: float = 1.0  # S/K ratio
    
    # Dividend risk
    has_dividend_risk: bool = False
    days_to_ex_div: Optional[int] = None
    dividend_amount: Optional[float] = None
    
    # Market factors
    hard_to_borrow: bool = False
    high_short_interest: bool = False
    
    # Metadata
    assessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    spot_price: float = 0.0
    option_price: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "level": self.level.value,
            "probability": round(self.probability, 4),
            "reason": self.reason,
            "intrinsic_value": round(self.intrinsic_value, 4),
            "time_value": round(self.time_value, 4),
            "time_value_pct": round(self.time_value_pct, 2),
            "days_to_expiry": self.days_to_expiry,
            "moneyness": round(self.moneyness, 4),
            "has_dividend_risk": self.has_dividend_risk,
            "days_to_ex_div": self.days_to_ex_div,
            "hard_to_borrow": self.hard_to_borrow,
            "assessed_at": self.assessed_at.isoformat(),
        }


class AssignmentMonitor:
    """
    Assignment risk monitoring service.
    
    Features:
    - Real-time risk assessment for short options
    - Dividend-aware risk calculation
    - Configurable alert thresholds
    - Background monitoring with callbacks
    
    Risk Assessment Logic:
    1. Check if position is short (long has no assignment risk)
    2. Calculate moneyness and time value
    3. Check for upcoming dividends (calls only)
    4. Assess time-based risk (DTE < 7 is high risk)
    5. Factor in market conditions (HTB, short interest)
    
    Example:
        monitor = AssignmentMonitor()
        
        # Single assessment
        risk = monitor.assess_risk("AAPL240119C00145000", spot=152.50)
        
        # Start background monitoring
        await monitor.start_monitoring(check_interval=30)
        
        # Register high-risk callback
        @monitor.on_high_risk
        def handle_risk(symbol, risk):
            logger.warning(f"High assignment risk: {symbol}")
    """
    
    def __init__(
        self,
        position_manager: Optional[PositionFSM] = None,
    ) -> None:
        """
        Initialize the assignment monitor.
        
        Args:
            position_manager: Position FSM to monitor (default: global)
        """
        self._position_manager = position_manager or get_position_manager()
        self._config = get_config()
        
        # Dividend calendar (would be populated from data source)
        self._dividends: Dict[str, DividendInfo] = {}
        
        # Hard-to-borrow list
        self._htb_symbols: Set[str] = set()
        
        # Callbacks
        self._high_risk_callbacks: List[Callable[[str, AssignmentRisk], None]] = []
        self._critical_risk_callbacks: List[Callable[[str, AssignmentRisk], None]] = []
        
        # Monitoring state
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Alert cooldown to prevent spam
        self._alert_cooldown: Dict[str, datetime] = {}
        self._cooldown_seconds = 300  # 5 minutes
        
        logger.info("AssignmentMonitor initialized")
    
    def on_high_risk(
        self,
        callback: Callable[[str, AssignmentRisk], None],
    ) -> Callable:
        """Register callback for HIGH risk level."""
        self._high_risk_callbacks.append(callback)
        return callback
    
    def on_critical_risk(
        self,
        callback: Callable[[str, AssignmentRisk], None],
    ) -> Callable:
        """Register callback for CRITICAL risk level."""
        self._critical_risk_callbacks.append(callback)
        return callback
    
    def set_dividend(
        self,
        underlying: str,
        ex_date: date,
        amount: float,
    ) -> None:
        """
        Set dividend information for an underlying.
        
        Args:
            underlying: Stock ticker
            ex_date: Ex-dividend date
            amount: Dividend amount per share
        """
        self._dividends[underlying.upper()] = DividendInfo(
            symbol=underlying.upper(),
            ex_date=ex_date,
            amount=amount,
        )
    
    def set_hard_to_borrow(self, symbols: List[str]) -> None:
        """Update list of hard-to-borrow symbols."""
        self._htb_symbols = {s.upper() for s in symbols}
    
    def assess_risk(
        self,
        symbol: str,
        spot: float,
        option_price: Optional[float] = None,
        position_side: str = "short",
        volatility: float = 0.30,
    ) -> AssignmentRisk:
        """
        Assess assignment risk for an option.
        
        Args:
            symbol: OSI option symbol
            spot: Current underlying price
            option_price: Current option price (calculated if not provided)
            position_side: 'long' or 'short'
            volatility: Implied volatility for pricing
            
        Returns:
            AssignmentRisk with detailed assessment
        """
        # Parse option details
        option = parse_osi_symbol(symbol)
        
        # Long positions have no assignment risk
        if position_side == "long":
            return AssignmentRisk(
                symbol=symbol,
                level=RiskLevel.NONE,
                probability=0.0,
                reason="Long position - no assignment risk",
                days_to_expiry=option.days_to_expiry,
                spot_price=spot,
            )
        
        # Calculate pricing if needed
        if option_price is None:
            result = price_option(
                spot=spot,
                strike=option.strike,
                time_to_expiry=max(option.time_to_expiry, 0.001),
                volatility=volatility,
                is_call=option.option_type.is_call,
            )
            option_price = result.price
            intrinsic = result.intrinsic_value
            time_value = result.time_value
        else:
            # Calculate intrinsic
            if option.option_type.is_call:
                intrinsic = max(0, spot - option.strike)
            else:
                intrinsic = max(0, option.strike - spot)
            time_value = max(0, option_price - intrinsic)
        
        # Calculate moneyness
        moneyness = spot / option.strike
        
        # Time value as percentage of intrinsic
        time_value_pct = (time_value / intrinsic * 100) if intrinsic > 0 else float('inf')
        
        # Check dividend risk (calls only)
        has_div_risk = False
        days_to_ex = None
        div_amount = None
        
        if option.option_type.is_call and option.underlying in self._dividends:
            div_info = self._dividends[option.underlying]
            if div_info.ex_date > date.today() and div_info.ex_date <= option.expiry:
                days_to_ex = div_info.days_to_ex
                div_amount = div_info.amount
                # Dividend risk if time value < dividend
                if time_value < div_amount:
                    has_div_risk = True
        
        # Check hard-to-borrow
        is_htb = option.underlying in self._htb_symbols
        
        # Assess risk level
        level, probability, reason = self._calculate_risk_level(
            option=option,
            spot=spot,
            intrinsic=intrinsic,
            time_value=time_value,
            time_value_pct=time_value_pct,
            has_div_risk=has_div_risk,
            days_to_ex=days_to_ex,
            is_htb=is_htb,
        )
        
        return AssignmentRisk(
            symbol=symbol,
            level=level,
            probability=probability,
            reason=reason,
            intrinsic_value=intrinsic,
            time_value=time_value,
            time_value_pct=time_value_pct,
            days_to_expiry=option.days_to_expiry,
            moneyness=moneyness,
            has_dividend_risk=has_div_risk,
            days_to_ex_div=days_to_ex,
            dividend_amount=div_amount,
            hard_to_borrow=is_htb,
            spot_price=spot,
            option_price=option_price,
        )
    
    def _calculate_risk_level(
        self,
        option: OptionSymbol,
        spot: float,
        intrinsic: float,
        time_value: float,
        time_value_pct: float,
        has_div_risk: bool,
        days_to_ex: Optional[int],
        is_htb: bool,
    ) -> tuple[RiskLevel, float, str]:
        """Calculate risk level from factors."""
        dte = option.days_to_expiry
        is_itm = intrinsic > 0
        
        # CRITICAL: Deep ITM with minimal time value
        if is_itm and time_value_pct < 1.0 and dte <= 3:
            return (
                RiskLevel.CRITICAL,
                0.90,
                f"Deep ITM with <1% time value, {dte} DTE - assignment very likely",
            )
        
        # CRITICAL: Dividend capture scenario
        if has_div_risk and days_to_ex is not None and days_to_ex <= 2:
            return (
                RiskLevel.CRITICAL,
                0.85,
                f"ITM call {days_to_ex} days before ex-div - assignment very likely",
            )
        
        # HIGH: ITM near expiration
        if is_itm and dte <= 7:
            probability = 0.60 + (7 - dte) * 0.05
            return (
                RiskLevel.HIGH,
                min(probability, 0.80),
                f"ITM with {dte} DTE - elevated assignment risk",
            )
        
        # HIGH: Dividend risk
        if has_div_risk and days_to_ex is not None and days_to_ex <= 5:
            return (
                RiskLevel.HIGH,
                0.50,
                f"ITM call near ex-div ({days_to_ex} days) - dividend capture risk",
            )
        
        # HIGH: Deep ITM with HTB
        if is_itm and is_htb and intrinsic / spot > 0.1:
            return (
                RiskLevel.HIGH,
                0.45,
                "Deep ITM on hard-to-borrow stock - synthetic stock risk",
            )
        
        # MEDIUM: ITM with moderate DTE
        if is_itm and dte <= 30:
            return (
                RiskLevel.MEDIUM,
                0.20,
                f"ITM with {dte} DTE - monitor for early assignment",
            )
        
        # MEDIUM: Approaching dividend
        if has_div_risk:
            return (
                RiskLevel.MEDIUM,
                0.15,
                "ITM call approaching ex-dividend date",
            )
        
        # LOW: OTM or far from expiry
        if not is_itm:
            return (
                RiskLevel.LOW,
                0.01,
                "Out-of-the-money - minimal assignment risk",
            )
        
        return (
            RiskLevel.LOW,
            0.05,
            f"ITM but {dte} DTE with adequate time value",
        )
    
    def assess_portfolio_risk(
        self,
        spots: Dict[str, float],
        volatilities: Optional[Dict[str, float]] = None,
    ) -> Dict[str, AssignmentRisk]:
        """
        Assess assignment risk for all short positions.
        
        Args:
            spots: Dict mapping underlying to spot price
            volatilities: Optional dict mapping symbol to IV
            
        Returns:
            Dict mapping position ID to AssignmentRisk
        """
        results = {}
        
        for position in self._position_manager.get_active_positions():
            if position.side != "short":
                continue
            
            spot = spots.get(position.underlying)
            if spot is None:
                continue
            
            vol = 0.30
            if volatilities and position.symbol in volatilities:
                vol = volatilities[position.symbol]
            
            risk = self.assess_risk(
                symbol=position.symbol,
                spot=spot,
                option_price=position.current_price,
                position_side="short",
                volatility=vol,
            )
            
            results[position.id] = risk
        
        return results
    
    async def start_monitoring(
        self,
        spots_provider: Callable[[], Dict[str, float]],
        check_interval: int = 30,
    ) -> None:
        """
        Start background assignment risk monitoring.
        
        Args:
            spots_provider: Callback that returns current spot prices
            check_interval: Seconds between checks
        """
        if self._monitoring:
            logger.warning("Monitoring already started")
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(
            self._monitoring_loop(spots_provider, check_interval)
        )
        
        logger.info("Assignment monitoring started", interval=check_interval)
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._monitoring = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        
        logger.info("Assignment monitoring stopped")
    
    async def _monitoring_loop(
        self,
        spots_provider: Callable[[], Dict[str, float]],
        check_interval: int,
    ) -> None:
        """Background monitoring loop."""
        while self._monitoring:
            try:
                # Get current prices
                spots = spots_provider()
                
                # Assess all positions
                risks = self.assess_portfolio_risk(spots)
                
                # Check for high-risk situations
                for position_id, risk in risks.items():
                    self._check_and_alert(position_id, risk)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
            
            await asyncio.sleep(check_interval)
    
    def _check_and_alert(self, position_id: str, risk: AssignmentRisk) -> None:
        """Check risk level and send alerts if needed."""
        now = datetime.now(timezone.utc)
        
        # Check cooldown
        last_alert = self._alert_cooldown.get(position_id)
        if last_alert and (now - last_alert).total_seconds() < self._cooldown_seconds:
            return
        
        # Trigger callbacks based on level
        if risk.level == RiskLevel.CRITICAL:
            for callback in self._critical_risk_callbacks:
                try:
                    callback(risk.symbol, risk)
                except Exception as e:
                    logger.error(f"Critical risk callback error: {e}")
            
            self._alert_cooldown[position_id] = now
            increment_counter("assignment_alerts_total")
            
        elif risk.level == RiskLevel.HIGH:
            for callback in self._high_risk_callbacks:
                try:
                    callback(risk.symbol, risk)
                except Exception as e:
                    logger.error(f"High risk callback error: {e}")
            
            self._alert_cooldown[position_id] = now
            increment_counter("assignment_alerts_total")


# =============================================================================
# MODULE-LEVEL UTILITIES
# =============================================================================

_assignment_monitor: Optional[AssignmentMonitor] = None


def get_assignment_monitor() -> AssignmentMonitor:
    """Get global assignment monitor instance."""
    global _assignment_monitor
    if _assignment_monitor is None:
        _assignment_monitor = AssignmentMonitor()
    return _assignment_monitor

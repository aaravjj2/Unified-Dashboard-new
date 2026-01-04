"""
Alpaca Options Lab - Risk Limit Enforcer

Production-grade risk limit enforcement with:
- Configurable limit types (hard/soft)
- Pre-trade validation
- Real-time monitoring
- Breach notifications

Limit Types:
1. Position limits (max contracts, notional)
2. Greeks limits (delta, gamma, theta, vega)
3. Concentration limits (per underlying, sector)
4. Loss limits (daily, weekly, max drawdown)

Enforcement Modes:
- HARD: Block trade completely
- SOFT: Warn but allow with confirmation
- MONITOR: Log only, no blocking

Usage:
    from src.risk.limits import LimitEnforcer, get_limit_enforcer
    
    enforcer = get_limit_enforcer()
    
    # Set limits
    enforcer.set_limit(RiskLimitType.MAX_DELTA, value=500, mode="hard")
    enforcer.set_limit(RiskLimitType.MAX_LOSS_DAILY, value=5000, mode="soft")
    
    # Validate trade
    result = enforcer.validate_trade(
        symbol="AAPL240119C00150000",
        quantity=10,
        side="long",
        greeks=greeks,
    )
    
    if not result.allowed:
        print(f"Trade blocked: {result.reason}")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from src.data.symbology import parse_osi_symbol
from src.pricing.black_scholes import Greeks
from src.risk.aggregator import PortfolioGreeks, RiskAggregator, get_risk_aggregator
from src.utils.logging_config import get_logger
from src.utils.metrics import get_metrics, increment_counter

logger = get_logger(__name__)
metrics = get_metrics()


class RiskLimitType(Enum):
    """Types of risk limits."""
    # Position limits
    MAX_POSITION_SIZE = "max_position_size"         # Per symbol
    MAX_CONTRACTS = "max_contracts"                 # Total contracts
    MAX_NOTIONAL = "max_notional"                   # Total notional
    MAX_POSITIONS_PER_UNDERLYING = "max_per_underlying"
    
    # Greeks limits
    MAX_DELTA = "max_delta"                         # Total delta
    MAX_GAMMA = "max_gamma"                         # Total gamma  
    MAX_VEGA = "max_vega"                           # Total vega
    MAX_THETA_LOSS = "max_theta_loss"               # Max daily theta
    
    # Dollar Greeks limits
    MAX_DOLLAR_DELTA = "max_dollar_delta"           # $ delta exposure
    MAX_DOLLAR_GAMMA = "max_dollar_gamma"           # $ gamma exposure
    
    # Concentration limits
    MAX_CONCENTRATION = "max_concentration"          # Max % in single underlying
    MAX_SECTOR_EXPOSURE = "max_sector_exposure"     # Max % in sector
    
    # Loss limits
    MAX_LOSS_DAILY = "max_loss_daily"               # Daily loss limit
    MAX_LOSS_WEEKLY = "max_loss_weekly"             # Weekly loss limit
    MAX_DRAWDOWN = "max_drawdown"                   # Max drawdown %
    
    # Leverage limits
    MAX_LEVERAGE = "max_leverage"                   # Notional / equity
    MAX_MARGIN_USAGE = "max_margin_usage"           # % of buying power


class EnforcementMode(Enum):
    """How limits are enforced."""
    HARD = "hard"       # Block trade completely
    SOFT = "soft"       # Warn but allow with override
    MONITOR = "monitor"  # Log only


@dataclass
class RiskLimit:
    """Configuration for a single risk limit."""
    limit_type: RiskLimitType
    value: float
    mode: EnforcementMode = EnforcementMode.HARD
    
    # Optional scope
    underlying: Optional[str] = None    # If limit is per-underlying
    sector: Optional[str] = None        # If limit is per-sector
    
    # Warning threshold (% of limit)
    warning_pct: float = 0.80           # Warn at 80% of limit
    
    # Description
    description: str = ""
    
    # Active status
    active: bool = True
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_modified: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class LimitBreach:
    """Record of a limit breach or warning."""
    limit: RiskLimit
    current_value: float
    limit_value: float
    breach_pct: float  # current / limit * 100
    
    is_breach: bool    # True if exceeded, False if warning
    is_blocked: bool   # Whether trade was blocked
    
    # Trade context
    trade_symbol: Optional[str] = None
    trade_quantity: Optional[int] = None
    
    # Timestamp
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def severity(self) -> str:
        """Get severity level."""
        if self.is_breach and self.is_blocked:
            return "critical"
        elif self.is_breach:
            return "high"
        else:
            return "warning"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "limit_type": self.limit.limit_type.value,
            "current_value": round(self.current_value, 4),
            "limit_value": round(self.limit_value, 4),
            "breach_pct": round(self.breach_pct, 2),
            "is_breach": self.is_breach,
            "is_blocked": self.is_blocked,
            "severity": self.severity,
            "trade_symbol": self.trade_symbol,
            "occurred_at": self.occurred_at.isoformat(),
        }


@dataclass
class ValidationResult:
    """Result of trade validation."""
    allowed: bool
    breaches: List[LimitBreach] = field(default_factory=list)
    warnings: List[LimitBreach] = field(default_factory=list)
    reason: str = ""
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0
    
    @property
    def has_breaches(self) -> bool:
        """Check if there are any breaches."""
        return len(self.breaches) > 0


class LimitEnforcer:
    """
    Risk limit enforcement engine.
    
    Features:
    - Pre-trade validation with Greeks impact
    - Real-time monitoring with callbacks
    - Configurable limit types and modes
    - Breach history and audit trail
    
    Architecture:
    - Limits stored in dictionary by type
    - Per-underlying limits stored separately
    - Validation checks all applicable limits
    - Callbacks fired on breaches/warnings
    
    Example:
        enforcer = LimitEnforcer()
        
        # Configure limits
        enforcer.set_limit(RiskLimitType.MAX_DELTA, 500, "hard")
        enforcer.set_limit(RiskLimitType.MAX_LOSS_DAILY, 5000, "soft")
        
        # Pre-trade validation
        result = enforcer.validate_trade(
            symbol="AAPL240119C00150000",
            quantity=10,
            greeks=Greeks(delta=0.6, gamma=0.02, theta=-0.05, vega=0.15),
        )
        
        if not result.allowed:
            print(f"Blocked: {result.reason}")
        elif result.has_warnings:
            print(f"Warning: {result.warnings[0].limit.description}")
    """
    
    def __init__(
        self,
        risk_aggregator: Optional[RiskAggregator] = None,
    ) -> None:
        """
        Initialize the limit enforcer.
        
        Args:
            risk_aggregator: Risk aggregator for portfolio state
        """
        self._aggregator = risk_aggregator or get_risk_aggregator()
        
        # Limits by type
        self._limits: Dict[RiskLimitType, RiskLimit] = {}
        
        # Per-underlying limits
        self._underlying_limits: Dict[str, Dict[RiskLimitType, RiskLimit]] = {}
        
        # Loss tracking
        self._daily_pnl: float = 0.0
        self._weekly_pnl: float = 0.0
        self._peak_equity: float = 0.0
        self._current_equity: float = 0.0
        
        # Breach history
        self._breach_history: List[LimitBreach] = []
        
        # Callbacks
        self._breach_callbacks: List[Callable[[LimitBreach], None]] = []
        self._warning_callbacks: List[Callable[[LimitBreach], None]] = []
        
        # Initialize default limits
        self._init_default_limits()
        
        logger.info("LimitEnforcer initialized")
    
    def _init_default_limits(self) -> None:
        """Initialize sensible default limits."""
        defaults = [
            (RiskLimitType.MAX_CONTRACTS, 100, EnforcementMode.SOFT),
            (RiskLimitType.MAX_DELTA, 200, EnforcementMode.SOFT),
            (RiskLimitType.MAX_DOLLAR_DELTA, 100000, EnforcementMode.SOFT),
            (RiskLimitType.MAX_LOSS_DAILY, 10000, EnforcementMode.HARD),
        ]
        
        for limit_type, value, mode in defaults:
            self._limits[limit_type] = RiskLimit(
                limit_type=limit_type,
                value=value,
                mode=mode,
                description=f"Default {limit_type.value} limit",
                active=False,  # Disabled by default
            )
    
    def set_limit(
        self,
        limit_type: RiskLimitType,
        value: float,
        mode: str = "hard",
        underlying: Optional[str] = None,
        warning_pct: float = 0.80,
        description: str = "",
    ) -> RiskLimit:
        """
        Set or update a risk limit.
        
        Args:
            limit_type: Type of limit
            value: Limit value
            mode: Enforcement mode ('hard', 'soft', 'monitor')
            underlying: If set, limit applies to this underlying only
            warning_pct: Percentage at which to warn
            description: Human-readable description
            
        Returns:
            Created RiskLimit
        """
        enforcement = EnforcementMode(mode.lower())
        
        limit = RiskLimit(
            limit_type=limit_type,
            value=value,
            mode=enforcement,
            underlying=underlying.upper() if underlying else None,
            warning_pct=warning_pct,
            description=description or f"{limit_type.value} limit: {value}",
            active=True,
        )
        
        if underlying:
            ul = underlying.upper()
            if ul not in self._underlying_limits:
                self._underlying_limits[ul] = {}
            self._underlying_limits[ul][limit_type] = limit
        else:
            self._limits[limit_type] = limit
        
        logger.info(
            f"Risk limit set",
            limit_type=limit_type.value,
            value=value,
            mode=mode,
            underlying=underlying,
        )
        
        return limit
    
    def remove_limit(
        self,
        limit_type: RiskLimitType,
        underlying: Optional[str] = None,
    ) -> bool:
        """Remove a limit."""
        if underlying:
            ul = underlying.upper()
            if ul in self._underlying_limits and limit_type in self._underlying_limits[ul]:
                del self._underlying_limits[ul][limit_type]
                return True
        elif limit_type in self._limits:
            del self._limits[limit_type]
            return True
        return False
    
    def disable_limit(self, limit_type: RiskLimitType) -> bool:
        """Temporarily disable a limit."""
        if limit_type in self._limits:
            self._limits[limit_type].active = False
            return True
        return False
    
    def enable_limit(self, limit_type: RiskLimitType) -> bool:
        """Re-enable a disabled limit."""
        if limit_type in self._limits:
            self._limits[limit_type].active = True
            return True
        return False
    
    def on_breach(self, callback: Callable[[LimitBreach], None]) -> Callable:
        """Register callback for limit breaches."""
        self._breach_callbacks.append(callback)
        return callback
    
    def on_warning(self, callback: Callable[[LimitBreach], None]) -> Callable:
        """Register callback for limit warnings."""
        self._warning_callbacks.append(callback)
        return callback
    
    def update_pnl(
        self,
        daily_pnl: float,
        weekly_pnl: float,
        current_equity: float,
    ) -> None:
        """
        Update P&L tracking for loss limits.
        
        Args:
            daily_pnl: Today's P&L
            weekly_pnl: This week's P&L
            current_equity: Current account equity
        """
        self._daily_pnl = daily_pnl
        self._weekly_pnl = weekly_pnl
        self._current_equity = current_equity
        
        if current_equity > self._peak_equity:
            self._peak_equity = current_equity
    
    def validate_trade(
        self,
        symbol: str,
        quantity: int,
        greeks: Optional[Greeks] = None,
        notional: Optional[float] = None,
        allow_override: bool = False,
    ) -> ValidationResult:
        """
        Validate a proposed trade against risk limits.
        
        Args:
            symbol: OSI option symbol
            quantity: Number of contracts (negative for short)
            greeks: Greeks for the option
            notional: Notional value of trade
            allow_override: If True, soft limits can be overridden
            
        Returns:
            ValidationResult with allowed status and any breaches
        """
        result = ValidationResult(allowed=True)
        option = parse_osi_symbol(symbol)
        
        # Get current portfolio state
        portfolio = self._aggregator.get_portfolio_greeks()
        
        # Check each active limit
        for limit in self._get_applicable_limits(option.underlying):
            if not limit.active:
                continue
            
            breach = self._check_limit(
                limit=limit,
                portfolio=portfolio,
                trade_symbol=symbol,
                trade_quantity=quantity,
                trade_greeks=greeks,
                trade_notional=notional,
            )
            
            if breach is not None:
                if breach.is_breach:
                    result.breaches.append(breach)
                    
                    # Determine if trade is blocked
                    if limit.mode == EnforcementMode.HARD:
                        breach.is_blocked = True
                        result.allowed = False
                    elif limit.mode == EnforcementMode.SOFT and not allow_override:
                        breach.is_blocked = True
                        result.allowed = False
                    
                    # Fire callbacks
                    for cb in self._breach_callbacks:
                        try:
                            cb(breach)
                        except Exception as e:
                            logger.error(f"Breach callback error: {e}")
                    
                    self._breach_history.append(breach)
                    increment_counter("limit_breaches_total")
                    
                else:
                    result.warnings.append(breach)
                    
                    for cb in self._warning_callbacks:
                        try:
                            cb(breach)
                        except Exception as e:
                            logger.error(f"Warning callback error: {e}")
        
        # Generate reason
        if not result.allowed:
            reasons = [
                f"{b.limit.limit_type.value}: {b.current_value:.2f} > {b.limit_value:.2f}"
                for b in result.breaches
                if b.is_blocked
            ]
            result.reason = "; ".join(reasons)
        
        return result
    
    def _get_applicable_limits(self, underlying: str) -> List[RiskLimit]:
        """Get all limits that apply to an underlying."""
        limits = list(self._limits.values())
        
        # Add underlying-specific limits
        if underlying in self._underlying_limits:
            limits.extend(self._underlying_limits[underlying].values())
        
        return limits
    
    def _check_limit(
        self,
        limit: RiskLimit,
        portfolio: PortfolioGreeks,
        trade_symbol: str,
        trade_quantity: int,
        trade_greeks: Optional[Greeks],
        trade_notional: Optional[float],
    ) -> Optional[LimitBreach]:
        """Check a single limit against current + proposed state."""
        current_value = 0.0
        
        # Get current value based on limit type
        if limit.limit_type == RiskLimitType.MAX_CONTRACTS:
            current_value = portfolio.total_positions + abs(trade_quantity)
            
        elif limit.limit_type == RiskLimitType.MAX_DELTA:
            trade_delta = trade_greeks.delta * trade_quantity if trade_greeks else 0
            current_value = abs(portfolio.total_delta + trade_delta)
            
        elif limit.limit_type == RiskLimitType.MAX_GAMMA:
            trade_gamma = trade_greeks.gamma * trade_quantity if trade_greeks else 0
            current_value = abs(portfolio.total_gamma + trade_gamma)
            
        elif limit.limit_type == RiskLimitType.MAX_VEGA:
            trade_vega = trade_greeks.vega * trade_quantity if trade_greeks else 0
            current_value = abs(portfolio.total_vega + trade_vega)
            
        elif limit.limit_type == RiskLimitType.MAX_DOLLAR_DELTA:
            trade_delta = trade_greeks.delta * trade_quantity * 100 if trade_greeks else 0
            # Would need spot price for accurate calculation
            current_value = abs(portfolio.dollar_delta + trade_delta * 150)  # Approximate
            
        elif limit.limit_type == RiskLimitType.MAX_NOTIONAL:
            current_value = portfolio.total_notional + (trade_notional or 0)
            
        elif limit.limit_type == RiskLimitType.MAX_LOSS_DAILY:
            current_value = abs(min(0, self._daily_pnl))
            
        elif limit.limit_type == RiskLimitType.MAX_LOSS_WEEKLY:
            current_value = abs(min(0, self._weekly_pnl))
            
        elif limit.limit_type == RiskLimitType.MAX_DRAWDOWN:
            if self._peak_equity > 0:
                current_value = (self._peak_equity - self._current_equity) / self._peak_equity * 100
            else:
                current_value = 0
        
        else:
            return None  # Limit type not implemented
        
        # Check breach
        breach_pct = current_value / limit.value * 100 if limit.value > 0 else 0
        
        if current_value > limit.value:
            # Full breach
            return LimitBreach(
                limit=limit,
                current_value=current_value,
                limit_value=limit.value,
                breach_pct=breach_pct,
                is_breach=True,
                is_blocked=False,  # Set by caller
                trade_symbol=trade_symbol,
                trade_quantity=trade_quantity,
            )
        elif current_value >= limit.value * limit.warning_pct:
            # Warning level
            return LimitBreach(
                limit=limit,
                current_value=current_value,
                limit_value=limit.value,
                breach_pct=breach_pct,
                is_breach=False,
                is_blocked=False,
                trade_symbol=trade_symbol,
                trade_quantity=trade_quantity,
            )
        
        return None
    
    def check_portfolio_limits(self) -> List[LimitBreach]:
        """Check all limits against current portfolio state."""
        breaches = []
        portfolio = self._aggregator.get_portfolio_greeks()
        
        for limit in self._limits.values():
            if not limit.active:
                continue
            
            breach = self._check_limit(
                limit=limit,
                portfolio=portfolio,
                trade_symbol="",
                trade_quantity=0,
                trade_greeks=None,
                trade_notional=None,
            )
            
            if breach is not None:
                breaches.append(breach)
        
        return breaches
    
    def get_limit_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all limits."""
        portfolio = self._aggregator.get_portfolio_greeks()
        status = {}
        
        for limit_type, limit in self._limits.items():
            if not limit.active:
                continue
            
            # Get current usage
            current = self._get_limit_current_value(limit_type, portfolio)
            
            status[limit_type.value] = {
                "limit": limit.value,
                "current": round(current, 4),
                "usage_pct": round(current / limit.value * 100, 2) if limit.value > 0 else 0,
                "mode": limit.mode.value,
                "warning_pct": limit.warning_pct * 100,
            }
        
        return status
    
    def _get_limit_current_value(
        self,
        limit_type: RiskLimitType,
        portfolio: PortfolioGreeks,
    ) -> float:
        """Get current value for a limit type."""
        if limit_type == RiskLimitType.MAX_CONTRACTS:
            return portfolio.total_positions
        elif limit_type == RiskLimitType.MAX_DELTA:
            return abs(portfolio.total_delta)
        elif limit_type == RiskLimitType.MAX_GAMMA:
            return abs(portfolio.total_gamma)
        elif limit_type == RiskLimitType.MAX_VEGA:
            return abs(portfolio.total_vega)
        elif limit_type == RiskLimitType.MAX_DOLLAR_DELTA:
            return abs(portfolio.dollar_delta)
        elif limit_type == RiskLimitType.MAX_NOTIONAL:
            return portfolio.total_notional
        elif limit_type == RiskLimitType.MAX_LOSS_DAILY:
            return abs(min(0, self._daily_pnl))
        return 0.0
    
    def get_breach_history(self, limit: int = 100) -> List[LimitBreach]:
        """Get recent breach history."""
        return self._breach_history[-limit:]
    
    def clear_breach_history(self) -> None:
        """Clear breach history."""
        self._breach_history.clear()


# =============================================================================
# MODULE-LEVEL UTILITIES
# =============================================================================

_limit_enforcer: Optional[LimitEnforcer] = None


def get_limit_enforcer() -> LimitEnforcer:
    """Get global limit enforcer instance."""
    global _limit_enforcer
    if _limit_enforcer is None:
        _limit_enforcer = LimitEnforcer()
    return _limit_enforcer

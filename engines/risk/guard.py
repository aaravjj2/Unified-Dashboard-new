"""
Risk Guard - Phase 4 TradeOps

Implements RiskManager with hard limits for trade validation:
- MAX_DRAWDOWN_PCT: Maximum allowed portfolio drawdown
- MAX_POSITION_SIZE: Maximum position size per trade
- RESTRICTED_TICKERS: Blocked symbols

Orders violating these limits are rejected before execution.
"""

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set

logger = logging.getLogger(__name__)


class RiskViolation(Enum):
    """Types of risk violations."""
    NONE = "none"
    MAX_DRAWDOWN_EXCEEDED = "max_drawdown_exceeded"
    MAX_POSITION_SIZE_EXCEEDED = "max_position_size_exceeded"
    RESTRICTED_TICKER = "restricted_ticker"
    INSUFFICIENT_BUYING_POWER = "insufficient_buying_power"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    MAX_OPEN_POSITIONS = "max_open_positions"
    INVALID_ORDER = "invalid_order"


@dataclass
class RiskCheckResult:
    """Result of a risk check operation."""
    approved: bool
    violation: RiskViolation = RiskViolation.NONE
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "approved": self.approved,
            "violation": self.violation.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class OrderRequest:
    """Order request to be validated by RiskManager."""
    ticker: str
    side: str  # "buy" or "sell"
    quantity: int
    order_type: str  # "market", "limit", "stop"
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "day"
    order_class: str = "simple"  # "simple", "bracket", "oco", "oto"
    is_paper: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def notional_value(self) -> float:
        """Calculate notional value of the order."""
        if self.price:
            return self.quantity * self.price
        return 0.0


class RiskManager:
    """
    Risk Management Engine for TradeOps.
    
    Enforces hard limits on:
    - Maximum drawdown percentage
    - Maximum position size (shares or notional)
    - Restricted tickers
    - Daily loss limits
    - Maximum open positions
    """
    
    # Default risk limits (can be overridden via environment)
    DEFAULT_MAX_DRAWDOWN_PCT = 5.0  # 5% max drawdown
    DEFAULT_MAX_POSITION_SIZE = 100  # 100 shares max
    DEFAULT_MAX_POSITION_NOTIONAL = 50000.0  # $50k max notional
    DEFAULT_DAILY_LOSS_LIMIT = 1000.0  # $1k daily loss limit
    DEFAULT_MAX_OPEN_POSITIONS = 10  # Max 10 open positions
    
    # Restricted tickers (high-risk, illiquid, or compliance)
    DEFAULT_RESTRICTED_TICKERS = {
        "GME", "AMC", "BBBY",  # Meme stocks
        "UVXY", "SVXY",  # Leveraged volatility
        "TQQQ", "SQQQ",  # 3x leveraged ETFs
    }
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern for risk manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize risk manager with configurable limits."""
        if self._initialized:
            return
        
        # Load limits from environment or use defaults
        self.max_drawdown_pct = float(os.getenv(
            "RISK_MAX_DRAWDOWN_PCT", 
            self.DEFAULT_MAX_DRAWDOWN_PCT
        ))
        self.max_position_size = int(os.getenv(
            "RISK_MAX_POSITION_SIZE",
            self.DEFAULT_MAX_POSITION_SIZE
        ))
        self.max_position_notional = float(os.getenv(
            "RISK_MAX_POSITION_NOTIONAL",
            self.DEFAULT_MAX_POSITION_NOTIONAL
        ))
        self.daily_loss_limit = float(os.getenv(
            "RISK_DAILY_LOSS_LIMIT",
            self.DEFAULT_DAILY_LOSS_LIMIT
        ))
        self.max_open_positions = int(os.getenv(
            "RISK_MAX_OPEN_POSITIONS",
            self.DEFAULT_MAX_OPEN_POSITIONS
        ))
        
        # Parse restricted tickers from environment
        env_restricted = os.getenv("RISK_RESTRICTED_TICKERS", "")
        if env_restricted:
            self.restricted_tickers = set(env_restricted.upper().split(","))
        else:
            self.restricted_tickers = self.DEFAULT_RESTRICTED_TICKERS.copy()
        
        # Runtime state
        self.daily_pnl = 0.0
        self.current_drawdown_pct = 0.0
        self.open_positions_count = 0
        self.portfolio_value = 100000.0  # Default paper account
        self.buying_power = 100000.0
        
        # Deterministic mode for testing
        self.deterministic = os.getenv("TRADEOPS_DETERMINISTIC", "0") == "1"
        
        # Violation log
        self.violation_log: List[RiskCheckResult] = []
        
        self._initialized = True
        logger.info(f"RiskManager initialized: max_drawdown={self.max_drawdown_pct}%, "
                   f"max_position={self.max_position_size}, "
                   f"restricted={len(self.restricted_tickers)} tickers")
    
    def check(self, order: OrderRequest) -> RiskCheckResult:
        """
        Perform comprehensive risk check on an order.
        
        Args:
            order: OrderRequest to validate
            
        Returns:
            RiskCheckResult with approval status and any violations
        """
        # Check 1: Validate order structure
        if not self._validate_order_structure(order):
            result = RiskCheckResult(
                approved=False,
                violation=RiskViolation.INVALID_ORDER,
                message="Invalid order structure: missing required fields",
                details={"ticker": order.ticker, "quantity": order.quantity}
            )
            self._log_violation(result)
            return result
        
        # Check 2: Restricted tickers
        if order.ticker.upper() in self.restricted_tickers:
            result = RiskCheckResult(
                approved=False,
                violation=RiskViolation.RESTRICTED_TICKER,
                message=f"Ticker {order.ticker} is restricted",
                details={
                    "ticker": order.ticker,
                    "reason": "compliance_restricted"
                }
            )
            self._log_violation(result)
            return result
        
        # Check 3: Position size limit
        if order.quantity > self.max_position_size:
            result = RiskCheckResult(
                approved=False,
                violation=RiskViolation.MAX_POSITION_SIZE_EXCEEDED,
                message=f"Position size {order.quantity} exceeds max {self.max_position_size}",
                details={
                    "requested_size": order.quantity,
                    "max_allowed": self.max_position_size,
                    "ticker": order.ticker
                }
            )
            self._log_violation(result)
            return result
        
        # Check 4: Notional value limit
        if order.notional_value > self.max_position_notional:
            result = RiskCheckResult(
                approved=False,
                violation=RiskViolation.MAX_POSITION_SIZE_EXCEEDED,
                message=f"Notional ${order.notional_value:,.2f} exceeds max ${self.max_position_notional:,.2f}",
                details={
                    "notional_value": order.notional_value,
                    "max_notional": self.max_position_notional,
                    "ticker": order.ticker
                }
            )
            self._log_violation(result)
            return result
        
        # Check 5: Daily loss limit
        if self.daily_pnl < -self.daily_loss_limit:
            result = RiskCheckResult(
                approved=False,
                violation=RiskViolation.DAILY_LOSS_LIMIT,
                message=f"Daily loss limit reached: ${abs(self.daily_pnl):,.2f}",
                details={
                    "current_daily_pnl": self.daily_pnl,
                    "daily_limit": self.daily_loss_limit
                }
            )
            self._log_violation(result)
            return result
        
        # Check 6: Maximum drawdown
        if self.current_drawdown_pct > self.max_drawdown_pct:
            result = RiskCheckResult(
                approved=False,
                violation=RiskViolation.MAX_DRAWDOWN_EXCEEDED,
                message=f"Drawdown {self.current_drawdown_pct:.1f}% exceeds max {self.max_drawdown_pct:.1f}%",
                details={
                    "current_drawdown": self.current_drawdown_pct,
                    "max_drawdown": self.max_drawdown_pct
                }
            )
            self._log_violation(result)
            return result
        
        # Check 7: Max open positions (only for buy orders)
        if order.side.lower() == "buy" and self.open_positions_count >= self.max_open_positions:
            result = RiskCheckResult(
                approved=False,
                violation=RiskViolation.MAX_OPEN_POSITIONS,
                message=f"Max open positions ({self.max_open_positions}) reached",
                details={
                    "current_positions": self.open_positions_count,
                    "max_positions": self.max_open_positions
                }
            )
            self._log_violation(result)
            return result
        
        # Check 8: Buying power (for buy orders)
        if order.side.lower() == "buy" and order.notional_value > self.buying_power:
            result = RiskCheckResult(
                approved=False,
                violation=RiskViolation.INSUFFICIENT_BUYING_POWER,
                message=f"Insufficient buying power: need ${order.notional_value:,.2f}, have ${self.buying_power:,.2f}",
                details={
                    "required": order.notional_value,
                    "available": self.buying_power
                }
            )
            self._log_violation(result)
            return result
        
        # All checks passed
        return RiskCheckResult(
            approved=True,
            violation=RiskViolation.NONE,
            message="Order approved by risk manager",
            details={
                "ticker": order.ticker,
                "quantity": order.quantity,
                "side": order.side,
                "is_paper": order.is_paper
            }
        )
    
    def _validate_order_structure(self, order: OrderRequest) -> bool:
        """Validate order has required fields."""
        if not order.ticker or len(order.ticker) == 0:
            return False
        if order.quantity <= 0:
            return False
        if order.side.lower() not in ("buy", "sell"):
            return False
        if order.order_type.lower() not in ("market", "limit", "stop", "stop_limit"):
            return False
        return True
    
    def _log_violation(self, result: RiskCheckResult):
        """Log risk violation for audit trail."""
        self.violation_log.append(result)
        logger.warning(f"Risk violation: {result.violation.value} - {result.message}")
    
    def update_portfolio_state(
        self,
        portfolio_value: Optional[float] = None,
        buying_power: Optional[float] = None,
        daily_pnl: Optional[float] = None,
        drawdown_pct: Optional[float] = None,
        open_positions: Optional[int] = None
    ):
        """
        Update the risk manager's view of portfolio state.
        
        Called by the execution router after order fills.
        """
        if portfolio_value is not None:
            self.portfolio_value = portfolio_value
        if buying_power is not None:
            self.buying_power = buying_power
        if daily_pnl is not None:
            self.daily_pnl = daily_pnl
        if drawdown_pct is not None:
            self.current_drawdown_pct = drawdown_pct
        if open_positions is not None:
            self.open_positions_count = open_positions
    
    def add_restricted_ticker(self, ticker: str):
        """Add a ticker to the restricted list."""
        self.restricted_tickers.add(ticker.upper())
        logger.info(f"Added {ticker.upper()} to restricted tickers")
    
    def remove_restricted_ticker(self, ticker: str):
        """Remove a ticker from the restricted list."""
        self.restricted_tickers.discard(ticker.upper())
        logger.info(f"Removed {ticker.upper()} from restricted tickers")
    
    def get_risk_limits(self) -> Dict[str, Any]:
        """Get current risk limit settings."""
        return {
            "max_drawdown_pct": self.max_drawdown_pct,
            "max_position_size": self.max_position_size,
            "max_position_notional": self.max_position_notional,
            "daily_loss_limit": self.daily_loss_limit,
            "max_open_positions": self.max_open_positions,
            "restricted_tickers": list(self.restricted_tickers)
        }
    
    def get_portfolio_state(self) -> Dict[str, Any]:
        """Get current portfolio state as tracked by risk manager."""
        return {
            "portfolio_value": self.portfolio_value,
            "buying_power": self.buying_power,
            "daily_pnl": self.daily_pnl,
            "current_drawdown_pct": self.current_drawdown_pct,
            "open_positions_count": self.open_positions_count
        }
    
    def get_violation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent risk violations."""
        return [v.to_dict() for v in self.violation_log[-limit:]]
    
    def reset_daily_stats(self):
        """Reset daily statistics (call at market open)."""
        self.daily_pnl = 0.0
        logger.info("Daily risk stats reset")


def get_risk_manager() -> RiskManager:
    """Get the singleton RiskManager instance."""
    return RiskManager()

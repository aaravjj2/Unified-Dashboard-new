"""
Alpaca Options Lab - Custom Exception Hierarchy

Structured exception classes for:
- Database operations
- Market data handling
- Pricing calculations
- Risk management
- Order execution

Each exception carries structured context for logging and debugging.

Usage:
    from src.utils.exceptions import (
        DatabaseError,
        MarketDataError,
        PricingError,
        RiskLimitExceeded,
        ValidationError,
    )
    
    raise PricingError(
        message="IV solver failed to converge",
        symbol="AAPL240119C00150000",
        context={"iterations": 100, "last_error": 0.05}
    )
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class OptionsLabException(Exception):
    """
    Base exception for all Options Lab errors.
    
    Provides structured error context for observability.
    """
    message: str
    error_code: str = "OL_UNKNOWN"
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None
    
    def __post_init__(self) -> None:
        super().__init__(self.message)
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "exception_type": type(self).__name__,
        }


# =============================================================================
# DATABASE EXCEPTIONS
# =============================================================================

@dataclass
class DatabaseError(OptionsLabException):
    """Base exception for database operations."""
    error_code: str = "OL_DB_ERROR"
    query: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["query"] = self.query
        return d


@dataclass
class ConnectionPoolExhausted(DatabaseError):
    """Raised when connection pool has no available connections."""
    error_code: str = "OL_DB_POOL_EXHAUSTED"
    pool_size: int = 0
    wait_timeout: float = 0.0


@dataclass
class DatabaseTimeout(DatabaseError):
    """Raised when a database operation times out."""
    error_code: str = "OL_DB_TIMEOUT"
    timeout_seconds: float = 0.0


@dataclass
class IntegrityError(DatabaseError):
    """Raised when a database integrity constraint is violated."""
    error_code: str = "OL_DB_INTEGRITY"
    constraint_name: Optional[str] = None


# =============================================================================
# MARKET DATA EXCEPTIONS
# =============================================================================

@dataclass
class MarketDataError(OptionsLabException):
    """Base exception for market data operations."""
    error_code: str = "OL_MARKET_DATA_ERROR"
    symbol: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["symbol"] = self.symbol
        return d


@dataclass
class WebSocketDisconnected(MarketDataError):
    """Raised when WebSocket connection is lost."""
    error_code: str = "OL_WS_DISCONNECTED"
    reconnect_attempts: int = 0


@dataclass
class RateLimitExceeded(MarketDataError):
    """Raised when API rate limit is exceeded."""
    error_code: str = "OL_RATE_LIMIT"
    retry_after_seconds: float = 0.0


@dataclass
class DataNotAvailable(MarketDataError):
    """Raised when requested market data is not available."""
    error_code: str = "OL_DATA_NOT_AVAILABLE"
    requested_at: Optional[datetime] = None


@dataclass
class StaleDataError(MarketDataError):
    """Raised when market data is too old."""
    error_code: str = "OL_STALE_DATA"
    data_age_seconds: float = 0.0
    max_age_seconds: float = 0.0


# =============================================================================
# PRICING EXCEPTIONS
# =============================================================================

@dataclass
class PricingError(OptionsLabException):
    """Base exception for pricing calculations."""
    error_code: str = "OL_PRICING_ERROR"
    symbol: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["symbol"] = self.symbol
        return d


@dataclass
class IVSolverError(PricingError):
    """Raised when IV solver fails to converge."""
    error_code: str = "OL_IV_SOLVER_ERROR"
    iterations: int = 0
    last_error: float = 0.0
    bounds: tuple[float, float] = (0.0, 0.0)


@dataclass
class InvalidOptionParameters(PricingError):
    """Raised when option parameters are invalid."""
    error_code: str = "OL_INVALID_PARAMS"
    invalid_field: Optional[str] = None
    invalid_value: Any = None


@dataclass
class NegativeTimeToExpiry(PricingError):
    """Raised when option has expired."""
    error_code: str = "OL_EXPIRED_OPTION"
    expiry_date: Optional[datetime] = None
    time_to_expiry: float = 0.0


# =============================================================================
# RISK MANAGEMENT EXCEPTIONS
# =============================================================================

@dataclass
class RiskError(OptionsLabException):
    """Base exception for risk management."""
    error_code: str = "OL_RISK_ERROR"


@dataclass
class RiskLimitExceeded(RiskError):
    """Raised when a risk limit is breached."""
    error_code: str = "OL_RISK_LIMIT_EXCEEDED"
    limit_name: str = ""
    limit_value: float = 0.0
    current_value: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "limit_name": self.limit_name,
            "limit_value": self.limit_value,
            "current_value": self.current_value,
            "breach_amount": self.current_value - self.limit_value,
        })
        return d


@dataclass
class MarginExceeded(RiskError):
    """Raised when margin requirements exceed available capital."""
    error_code: str = "OL_MARGIN_EXCEEDED"
    required_margin: float = 0.0
    available_margin: float = 0.0
    utilization_ratio: float = 0.0


@dataclass
class PositionSizeExceeded(RiskError):
    """Raised when position size limit is exceeded."""
    error_code: str = "OL_POSITION_SIZE_EXCEEDED"
    symbol: str = ""
    max_size: int = 0
    requested_size: int = 0


# =============================================================================
# ORDER EXECUTION EXCEPTIONS
# =============================================================================

@dataclass
class OrderError(OptionsLabException):
    """Base exception for order execution."""
    error_code: str = "OL_ORDER_ERROR"
    order_id: Optional[str] = None
    symbol: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "order_id": self.order_id,
            "symbol": self.symbol,
        })
        return d


@dataclass
class OrderRejected(OrderError):
    """Raised when an order is rejected."""
    error_code: str = "OL_ORDER_REJECTED"
    reject_reason: str = ""


@dataclass
class InsufficientFunds(OrderError):
    """Raised when there are insufficient funds for an order."""
    error_code: str = "OL_INSUFFICIENT_FUNDS"
    required_amount: float = 0.0
    available_amount: float = 0.0


@dataclass  
class OrderNotFound(OrderError):
    """Raised when an order cannot be found."""
    error_code: str = "OL_ORDER_NOT_FOUND"


# =============================================================================
# VALIDATION EXCEPTIONS
# =============================================================================

@dataclass
class ValidationError(OptionsLabException):
    """Raised when input validation fails."""
    error_code: str = "OL_VALIDATION_ERROR"
    field_name: Optional[str] = None
    field_value: Any = None
    validation_rule: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "field_name": self.field_name,
            "field_value": str(self.field_value),
            "validation_rule": self.validation_rule,
        })
        return d


@dataclass
class ConfigurationError(OptionsLabException):
    """Raised when configuration is invalid or missing."""
    error_code: str = "OL_CONFIG_ERROR"
    config_key: Optional[str] = None


# =============================================================================
# BACKTESTING EXCEPTIONS
# =============================================================================

@dataclass
class BacktestError(OptionsLabException):
    """Base exception for backtesting operations."""
    error_code: str = "OL_BACKTEST_ERROR"
    backtest_id: Optional[str] = None


@dataclass
class InsufficientHistoricalData(BacktestError):
    """Raised when historical data is insufficient for backtest."""
    error_code: str = "OL_INSUFFICIENT_DATA"
    symbol: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    required_days: int = 0
    available_days: int = 0


@dataclass
class BacktestTimeout(BacktestError):
    """Raised when backtest execution times out."""
    error_code: str = "OL_BACKTEST_TIMEOUT"
    timeout_seconds: float = 0.0
    completed_steps: int = 0
    total_steps: int = 0


# =============================================================================
# STRATEGY EXCEPTIONS
# =============================================================================

@dataclass
class StrategyError(OptionsLabException):
    """Base exception for strategy execution."""
    error_code: str = "OL_STRATEGY_ERROR"
    strategy_name: str = ""


@dataclass
class CriticalStrategyError(StrategyError):
    """Raised for critical strategy failures that require immediate attention."""
    error_code: str = "OL_CRITICAL_STRATEGY_ERROR"
    requires_shutdown: bool = False


@dataclass
class RiskLimitError(RiskError):
    """Raised when a risk limit is breached (alias for RiskLimitExceeded)."""
    error_code: str = "OL_RISK_LIMIT_ERROR"
    limit_name: str = ""
    limit_value: float = 0.0
    current_value: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "limit_name": self.limit_name,
            "limit_value": self.limit_value,
            "current_value": self.current_value,
            "breach_amount": self.current_value - self.limit_value,
        })
        return d

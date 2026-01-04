"""
Alpaca Options Lab - Strategy Context

Provides strategies access to system components through a controlled interface.
This is the ONLY way strategies interact with the trading system.

Features:
- Portfolio access (positions, Greeks, P&L)
- Market data access (quotes, chains, Greeks)
- Order management (submit signals, check fills)
- Risk checking (validate against limits)

Usage:
    context = StrategyContext(
        portfolio=portfolio,
        risk_manager=risk_manager,
        order_manager=order_manager,
        market_data=market_data,
        greeks_engine=greeks_engine
    )
    
    # Use in strategy
    chain = context.get_option_chain("SPY")
    greeks = context.get_greeks(contract_id)
    context.submit_signal(signal)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, timezone
from typing import Any, Dict, List, Optional, Protocol, TYPE_CHECKING

from src.utils.logging_config import get_logger
from src.utils.exceptions import ValidationError

if TYPE_CHECKING:
    from src.pricing.black_scholes import Greeks, BlackScholesEngine
    from src.risk.aggregator import RiskAggregator
    from src.lifecycle.fsm import Position, PositionFSM
    from src.strategies.base import Signal

logger = get_logger(__name__)


@dataclass
class Quote:
    """Market quote for an option."""
    contract_id: int
    symbol: str
    bid: float
    ask: float
    last: float
    bid_size: int
    ask_size: int
    volume: int
    open_interest: int
    timestamp: datetime
    
    @property
    def mid(self) -> float:
        """Mid price."""
        return (self.bid + self.ask) / 2
    
    @property
    def spread(self) -> float:
        """Bid-ask spread."""
        return self.ask - self.bid


@dataclass
class OptionContract:
    """Option contract details."""
    id: int
    symbol: str
    underlying: str
    option_type: str  # 'C' or 'P'
    strike: float
    expiration: date
    multiplier: int = 100
    
    @property
    def is_call(self) -> bool:
        return self.option_type == 'C'
    
    @property
    def is_put(self) -> bool:
        return self.option_type == 'P'
    
    @property
    def days_to_expiry(self) -> int:
        """Days until expiration."""
        return (self.expiration - date.today()).days


class MarketDataProvider(Protocol):
    """Protocol for market data access."""
    
    def get_quote(self, contract_id: int) -> Optional[Quote]: ...
    def get_chain(
        self, 
        underlying: str, 
        expiration: Optional[date] = None
    ) -> List[OptionContract]: ...
    def get_underlying_price(self, symbol: str) -> float: ...


class PortfolioProvider(Protocol):
    """Protocol for portfolio access."""
    
    def get_positions(self, strategy: Optional[str] = None) -> List[Any]: ...
    def get_value(self) -> float: ...
    def get_cash(self) -> float: ...


class OrderManagerProvider(Protocol):
    """Protocol for order management."""
    
    def submit_signal(self, signal: 'Signal') -> str: ...
    def cancel_order(self, order_id: str) -> bool: ...
    def get_order_status(self, order_id: str) -> str: ...


class StrategyContext:
    """
    Context object providing strategies access to system components.
    
    This is the ONLY way strategies interact with the system.
    Ensures proper encapsulation, testing, and security.
    
    All methods are designed to be:
    - Safe: No side effects unless explicitly intended
    - Fast: Cached where appropriate
    - Isolated: Strategy errors don't affect the context
    """
    
    def __init__(
        self,
        portfolio: Optional[PortfolioProvider] = None,
        risk_manager: Optional['RiskAggregator'] = None,
        order_manager: Optional[OrderManagerProvider] = None,
        market_data: Optional[MarketDataProvider] = None,
        greeks_engine: Optional['BlackScholesEngine'] = None,
        position_manager: Optional['PositionFSM'] = None,
    ):
        """
        Initialize strategy context.
        
        Args:
            portfolio: Portfolio access provider
            risk_manager: Risk aggregation and limits
            order_manager: Order submission and management
            market_data: Market data access
            greeks_engine: Greeks calculation engine
            position_manager: Position state management
        """
        self._portfolio = portfolio
        self._risk_manager = risk_manager
        self._order_manager = order_manager
        self._market_data = market_data
        self._greeks_engine = greeks_engine
        self._position_manager = position_manager
        
        # Caches
        self._quote_cache: Dict[int, Quote] = {}
        self._chain_cache: Dict[str, List[OptionContract]] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl_seconds = 1  # 1 second cache
        
        logger.debug("strategy_context_initialized")
    
    # ================================================================
    # Market Data Methods
    # ================================================================
    
    def get_quote(self, contract_id: int) -> Optional[Quote]:
        """
        Get current quote for a contract.
        
        Args:
            contract_id: Contract identifier
            
        Returns:
            Quote object or None if not available
        """
        self._maybe_refresh_cache()
        
        if contract_id in self._quote_cache:
            return self._quote_cache[contract_id]
        
        if self._market_data:
            quote = self._market_data.get_quote(contract_id)
            if quote:
                self._quote_cache[contract_id] = quote
            return quote
        
        return None
    
    def get_option_chain(
        self,
        underlying: str,
        expiration: Optional[date] = None
    ) -> List[OptionContract]:
        """
        Get option chain for underlying.
        
        Args:
            underlying: Underlying symbol (e.g., 'SPY')
            expiration: Optional specific expiration date
            
        Returns:
            List of OptionContract objects
        """
        cache_key = f"{underlying}_{expiration or 'all'}"
        
        if cache_key in self._chain_cache:
            return self._chain_cache[cache_key]
        
        if self._market_data:
            chain = self._market_data.get_chain(underlying, expiration)
            self._chain_cache[cache_key] = chain
            return chain
        
        return []
    
    def get_underlying_price(self, symbol: str) -> float:
        """
        Get current price of underlying.
        
        Args:
            symbol: Underlying symbol
            
        Returns:
            Current price
        """
        if self._market_data:
            return self._market_data.get_underlying_price(symbol)
        return 0.0
    
    def get_greeks(self, contract_id: int) -> Optional['Greeks']:
        """
        Get Greeks for a contract.
        
        Args:
            contract_id: Contract identifier
            
        Returns:
            Greeks object or None
        """
        quote = self.get_quote(contract_id)
        if not quote or not self._greeks_engine:
            return None
        
        # Would need contract details to calculate
        # This is a simplified version
        return None
    
    # ================================================================
    # Portfolio Methods
    # ================================================================
    
    def get_positions(self, strategy: Optional[str] = None) -> List[Any]:
        """
        Get open positions.
        
        Args:
            strategy: Optional filter by strategy name
            
        Returns:
            List of Position objects
        """
        if self._portfolio:
            return self._portfolio.get_positions(strategy)
        return []
    
    def get_portfolio_value(self) -> float:
        """Get total portfolio value."""
        if self._portfolio:
            return self._portfolio.get_value()
        return 0.0
    
    def get_portfolio_cash(self) -> float:
        """Get available cash."""
        if self._portfolio:
            return self._portfolio.get_cash()
        return 0.0
    
    def get_portfolio_greeks(self) -> Dict[str, float]:
        """
        Get aggregated portfolio Greeks.
        
        Returns:
            Dictionary with delta, gamma, theta, vega, rho
        """
        if self._risk_manager:
            try:
                portfolio = self._risk_manager.get_portfolio_greeks()
                return {
                    'delta': portfolio.total_delta,
                    'gamma': portfolio.total_gamma,
                    'theta': portfolio.total_theta,
                    'vega': portfolio.total_vega,
                    'rho': portfolio.total_rho,
                    'dollar_delta': portfolio.dollar_delta,
                    'dollar_gamma': portfolio.dollar_gamma,
                }
            except Exception as e:
                logger.error("failed_to_get_portfolio_greeks", error=str(e))
        
        return {
            'delta': 0.0,
            'gamma': 0.0,
            'theta': 0.0,
            'vega': 0.0,
            'rho': 0.0,
            'dollar_delta': 0.0,
            'dollar_gamma': 0.0,
        }
    
    # ================================================================
    # Risk Methods
    # ================================================================
    
    def check_risk_limits(
        self, 
        signal: 'Signal', 
        limits: Dict[str, float]
    ) -> bool:
        """
        Check if signal would breach risk limits.
        
        Args:
            signal: Proposed signal
            limits: Risk limits to check against
            
        Returns:
            True if within limits, False otherwise
        """
        if not self._risk_manager:
            return True  # No risk manager = no limits
        
        try:
            # Get current Greeks
            current_greeks = self.get_portfolio_greeks()
            
            # Estimate signal's Greek impact
            signal_greeks = self._estimate_signal_greeks(signal)
            
            # Check delta limit
            if 'max_delta' in limits:
                projected_delta = current_greeks['delta'] + signal_greeks.get('delta', 0)
                if abs(projected_delta) > limits['max_delta']:
                    logger.warning(
                        "delta_limit_breach",
                        current=current_greeks['delta'],
                        projected=projected_delta,
                        limit=limits['max_delta']
                    )
                    return False
            
            # Check gamma limit
            if 'max_gamma' in limits:
                projected_gamma = current_greeks['gamma'] + signal_greeks.get('gamma', 0)
                if abs(projected_gamma) > limits['max_gamma']:
                    return False
            
            # Check vega limit
            if 'max_vega' in limits:
                projected_vega = current_greeks['vega'] + signal_greeks.get('vega', 0)
                if abs(projected_vega) > limits['max_vega']:
                    return False
            
            # Check max loss per trade
            if 'max_loss_per_trade' in limits and signal.max_risk:
                allocated_capital = self.get_portfolio_value() * 0.1  # Assume 10%
                max_loss = allocated_capital * limits['max_loss_per_trade']
                if signal.max_risk > max_loss:
                    logger.warning(
                        "max_loss_limit_breach",
                        signal_risk=signal.max_risk,
                        max_allowed=max_loss
                    )
                    return False
            
            return True
            
        except Exception as e:
            logger.error("risk_check_failed", error=str(e))
            return False  # Fail-safe: reject if can't verify
    
    def _estimate_signal_greeks(self, signal: 'Signal') -> Dict[str, float]:
        """Estimate Greeks impact of a signal."""
        greeks = {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}
        
        for leg in signal.legs:
            quote = self.get_quote(leg.contract_id)
            if not quote:
                continue
            
            # Simplified Greek estimation
            # In production, would calculate actual Greeks
            multiplier = 1 if leg.side.value == 'buy' else -1
            greeks['delta'] += multiplier * leg.quantity * 0.5  # Assume ATM
            greeks['gamma'] += abs(leg.quantity) * 0.02
            greeks['theta'] += multiplier * leg.quantity * -0.05
            greeks['vega'] += abs(leg.quantity) * 0.1
        
        return greeks
    
    # ================================================================
    # Order Methods
    # ================================================================
    
    def submit_signal(self, signal: 'Signal') -> str:
        """
        Submit trading signal for execution.
        
        Args:
            signal: Trading signal
            
        Returns:
            Order ID
            
        Raises:
            ValidationError: If signal is invalid
        """
        if not self._order_manager:
            raise ValidationError("No order manager available")
        
        # Validate signal
        if not signal.legs:
            raise ValidationError("Signal has no legs")
        
        return self._order_manager.submit_signal(signal)
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Order identifier
            
        Returns:
            True if cancelled, False otherwise
        """
        if not self._order_manager:
            return False
        
        return self._order_manager.cancel_order(order_id)
    
    def get_order_status(self, order_id: str) -> str:
        """
        Get order status.
        
        Args:
            order_id: Order identifier
            
        Returns:
            Status string (e.g., 'pending', 'filled', 'cancelled')
        """
        if not self._order_manager:
            return "unknown"
        
        return self._order_manager.get_order_status(order_id)
    
    # ================================================================
    # Internal Methods
    # ================================================================
    
    def _maybe_refresh_cache(self) -> None:
        """Refresh cache if TTL expired."""
        now = datetime.now(timezone.utc)
        
        if self._cache_time is None:
            self._cache_time = now
            return
        
        elapsed = (now - self._cache_time).total_seconds()
        if elapsed > self._cache_ttl_seconds:
            self._quote_cache.clear()
            self._chain_cache.clear()
            self._cache_time = now
    
    def clear_cache(self) -> None:
        """Force clear all caches."""
        self._quote_cache.clear()
        self._chain_cache.clear()
        self._cache_time = None

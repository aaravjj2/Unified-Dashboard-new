"""
Alpaca Options Lab - Options-Specific Backtesting Logic

Production-grade options backtesting with:
- Expiration handling (settlement, removal)
- Assignment risk and handling
- Exercise logic (ITM options)
- Greeks-based P&L attribution

Options Events:
1. Expiration: OTM options expire worthless, ITM options exercised
2. Assignment: Short ITM options may be assigned
3. Early Exercise: American options can be exercised early
4. Pin Risk: Options near strike at expiration

Usage:
    from src.backtesting.options_logic import OptionsBacktest
    
    backtest = OptionsBacktest(engine)
    
    # Configure handlers
    backtest.set_exercise_threshold(0.01)  # Exercise if >1% ITM
    backtest.set_assignment_probability(0.8)  # 80% assignment on ITM
    
    # Run with options handling
    result = backtest.run(market_data)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from src.data.symbology import OptionSymbol, OptionType, parse_osi_symbol
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ExpirationAction(Enum):
    """Actions at option expiration."""
    EXPIRE_WORTHLESS = "expire_worthless"
    EXERCISE = "exercise"
    ASSIGN = "assign"
    CASH_SETTLE = "cash_settle"


@dataclass
class ExpirationEvent:
    """Option expiration event."""
    symbol: str
    expiry: date
    action: ExpirationAction
    
    # Position info
    quantity: int
    entry_price: float
    
    # Settlement
    settlement_price: float
    intrinsic_value: float
    
    # P&L
    pnl: float
    
    # Stock assignment (if applicable)
    stock_quantity: int = 0
    stock_price: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "expiry": self.expiry.isoformat(),
            "action": self.action.value,
            "quantity": self.quantity,
            "settlement_price": round(self.settlement_price, 4),
            "intrinsic_value": round(self.intrinsic_value, 4),
            "pnl": round(self.pnl, 2),
            "stock_quantity": self.stock_quantity,
        }


@dataclass
class AssignmentEvent:
    """Option assignment event (for short options)."""
    symbol: str
    assigned_at: datetime
    
    # Position
    quantity: int  # Negative for short
    
    # Assignment
    strike: float
    is_call: bool
    
    # Stock effect
    stock_symbol: str
    stock_quantity: int  # Positive = buy, negative = sell
    stock_price: float
    
    # P&L
    option_pnl: float
    cash_change: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "assigned_at": self.assigned_at.isoformat(),
            "quantity": self.quantity,
            "strike": self.strike,
            "is_call": self.is_call,
            "stock_symbol": self.stock_symbol,
            "stock_quantity": self.stock_quantity,
            "option_pnl": round(self.option_pnl, 2),
            "cash_change": round(self.cash_change, 2),
        }


class ExpirationHandler:
    """
    Handles option expiration logic.
    
    Expiration Rules:
    - OTM options: Expire worthless
    - ITM options (long): Automatically exercised
    - ITM options (short): May be assigned
    - Cash-settled options: Settle to cash
    
    Example:
        handler = ExpirationHandler(
            exercise_threshold=0.01,
            cash_settle_index_options=True,
        )
        
        events = handler.process_expirations(
            positions=positions,
            spot_prices={"AAPL": 150.0},
            current_date=date(2024, 1, 19),
        )
    """
    
    def __init__(
        self,
        exercise_threshold: float = 0.01,
        cash_settle_index_options: bool = True,
        index_symbols: Optional[Set[str]] = None,
    ) -> None:
        """
        Initialize expiration handler.
        
        Args:
            exercise_threshold: Minimum % ITM to exercise (default 1%)
            cash_settle_index_options: Whether index options are cash-settled
            index_symbols: Set of index underlying symbols
        """
        self.exercise_threshold = exercise_threshold
        self.cash_settle_index_options = cash_settle_index_options
        self.index_symbols = index_symbols or {"SPX", "NDX", "RUT", "VIX"}
    
    def process_expirations(
        self,
        positions: Dict[str, Any],
        spot_prices: Dict[str, float],
        current_date: date,
        option_multiplier: int = 100,
    ) -> List[ExpirationEvent]:
        """
        Process all expiring options.
        
        Args:
            positions: Dict of symbol -> position
            spot_prices: Dict of underlying -> spot price
            current_date: Current date
            option_multiplier: Contract multiplier
            
        Returns:
            List of expiration events
        """
        events = []
        
        for symbol, position in list(positions.items()):
            # Parse option
            try:
                option = parse_osi_symbol(symbol)
            except Exception:
                continue  # Not an option
            
            # Check if expiring today
            if option.expiry != current_date:
                continue
            
            # Get spot price
            spot = spot_prices.get(option.underlying)
            if spot is None:
                logger.warning(f"No spot price for {option.underlying}")
                continue
            
            # Calculate intrinsic value
            if option.option_type.is_call:
                intrinsic = max(0, spot - option.strike)
            else:
                intrinsic = max(0, option.strike - spot)
            
            # Determine action
            quantity = position.get("quantity", 0)
            entry_price = position.get("entry_price", 0)
            
            if intrinsic == 0:
                # OTM - expire worthless
                pnl = -entry_price * abs(quantity) * option_multiplier if quantity > 0 else entry_price * abs(quantity) * option_multiplier
                
                events.append(ExpirationEvent(
                    symbol=symbol,
                    expiry=current_date,
                    action=ExpirationAction.EXPIRE_WORTHLESS,
                    quantity=quantity,
                    entry_price=entry_price,
                    settlement_price=0.0,
                    intrinsic_value=0.0,
                    pnl=pnl,
                ))
            else:
                # ITM
                itm_pct = intrinsic / option.strike
                
                if itm_pct >= self.exercise_threshold:
                    # Exercise/Assign
                    is_index = option.underlying in self.index_symbols
                    
                    if is_index and self.cash_settle_index_options:
                        # Cash settlement
                        pnl = (intrinsic - entry_price) * quantity * option_multiplier
                        
                        events.append(ExpirationEvent(
                            symbol=symbol,
                            expiry=current_date,
                            action=ExpirationAction.CASH_SETTLE,
                            quantity=quantity,
                            entry_price=entry_price,
                            settlement_price=intrinsic,
                            intrinsic_value=intrinsic,
                            pnl=pnl,
                        ))
                    else:
                        # Stock delivery
                        if quantity > 0:
                            action = ExpirationAction.EXERCISE
                        else:
                            action = ExpirationAction.ASSIGN
                        
                        # Stock quantity from exercise/assignment
                        if option.option_type.is_call:
                            stock_qty = quantity * option_multiplier
                        else:
                            stock_qty = -quantity * option_multiplier
                        
                        pnl = (intrinsic - entry_price) * quantity * option_multiplier
                        
                        events.append(ExpirationEvent(
                            symbol=symbol,
                            expiry=current_date,
                            action=action,
                            quantity=quantity,
                            entry_price=entry_price,
                            settlement_price=intrinsic,
                            intrinsic_value=intrinsic,
                            pnl=pnl,
                            stock_quantity=stock_qty,
                            stock_price=option.strike,
                        ))
                else:
                    # Slightly ITM but below threshold - expire
                    pnl = -entry_price * abs(quantity) * option_multiplier if quantity > 0 else entry_price * abs(quantity) * option_multiplier
                    
                    events.append(ExpirationEvent(
                        symbol=symbol,
                        expiry=current_date,
                        action=ExpirationAction.EXPIRE_WORTHLESS,
                        quantity=quantity,
                        entry_price=entry_price,
                        settlement_price=0.0,
                        intrinsic_value=intrinsic,
                        pnl=pnl,
                    ))
        
        return events


class AssignmentHandler:
    """
    Handles early option assignment logic.
    
    Assignment Risk Factors:
    - Deep ITM short options
    - Approaching ex-dividend (calls)
    - Near expiration with time value < dividend
    - Hard-to-borrow underlying (puts)
    
    Example:
        handler = AssignmentHandler(
            base_assignment_prob=0.05,
            dividend_assignment_prob=0.80,
        )
        
        events = handler.check_assignments(
            positions=positions,
            spot_prices=spots,
            dividends=div_calendar,
            current_date=today,
        )
    """
    
    def __init__(
        self,
        base_assignment_prob: float = 0.05,
        dividend_assignment_prob: float = 0.80,
        deep_itm_threshold: float = 0.10,
        time_value_threshold: float = 0.01,
    ) -> None:
        """
        Initialize assignment handler.
        
        Args:
            base_assignment_prob: Base daily assignment probability
            dividend_assignment_prob: Assignment prob near ex-div
            deep_itm_threshold: % ITM to be considered "deep"
            time_value_threshold: Time value % below which assignment likely
        """
        self.base_assignment_prob = base_assignment_prob
        self.dividend_assignment_prob = dividend_assignment_prob
        self.deep_itm_threshold = deep_itm_threshold
        self.time_value_threshold = time_value_threshold
        
        # Random state for reproducibility
        import random
        self._random = random.Random(42)
    
    def check_assignments(
        self,
        positions: Dict[str, Any],
        spot_prices: Dict[str, float],
        option_prices: Dict[str, float],
        dividends: Optional[Dict[str, Tuple[date, float]]] = None,
        current_date: Optional[date] = None,
        option_multiplier: int = 100,
    ) -> List[AssignmentEvent]:
        """
        Check for potential early assignments on short options.
        
        Args:
            positions: Dict of symbol -> position
            spot_prices: Dict of underlying -> spot
            option_prices: Dict of symbol -> current price
            dividends: Dict of underlying -> (ex_date, amount)
            current_date: Current date
            option_multiplier: Contract multiplier
            
        Returns:
            List of assignment events
        """
        events = []
        current_date = current_date or date.today()
        dividends = dividends or {}
        
        for symbol, position in list(positions.items()):
            quantity = position.get("quantity", 0)
            
            # Only short positions can be assigned
            if quantity >= 0:
                continue
            
            # Parse option
            try:
                option = parse_osi_symbol(symbol)
            except Exception:
                continue
            
            # Skip if expired
            if option.expiry <= current_date:
                continue
            
            spot = spot_prices.get(option.underlying)
            if spot is None:
                continue
            
            # Calculate intrinsic and time value
            if option.option_type.is_call:
                intrinsic = max(0, spot - option.strike)
            else:
                intrinsic = max(0, option.strike - spot)
            
            option_price = option_prices.get(symbol, intrinsic)
            time_value = max(0, option_price - intrinsic)
            
            # Check assignment probability
            assignment_prob = self._calculate_assignment_prob(
                option=option,
                spot=spot,
                intrinsic=intrinsic,
                time_value=time_value,
                dividends=dividends,
                current_date=current_date,
            )
            
            # Roll dice
            if self._random.random() < assignment_prob:
                # Assignment occurs
                entry_price = position.get("entry_price", 0)
                
                # Calculate stock effect
                if option.option_type.is_call:
                    # Short call assigned -> sell stock at strike
                    stock_qty = quantity * option_multiplier  # Negative
                    cash_change = -stock_qty * option.strike  # Positive (receive cash)
                else:
                    # Short put assigned -> buy stock at strike
                    stock_qty = -quantity * option_multiplier  # Positive
                    cash_change = -stock_qty * option.strike  # Negative (pay cash)
                
                # Option P&L (premium received - intrinsic at assignment)
                option_pnl = (entry_price - intrinsic) * abs(quantity) * option_multiplier
                
                events.append(AssignmentEvent(
                    symbol=symbol,
                    assigned_at=datetime.combine(current_date, time(16, 0)),
                    quantity=quantity,
                    strike=option.strike,
                    is_call=option.option_type.is_call,
                    stock_symbol=option.underlying,
                    stock_quantity=stock_qty,
                    stock_price=option.strike,
                    option_pnl=option_pnl,
                    cash_change=cash_change,
                ))
        
        return events
    
    def _calculate_assignment_prob(
        self,
        option: OptionSymbol,
        spot: float,
        intrinsic: float,
        time_value: float,
        dividends: Dict[str, Tuple[date, float]],
        current_date: date,
    ) -> float:
        """Calculate assignment probability."""
        # Must be ITM
        if intrinsic <= 0:
            return 0.0
        
        prob = self.base_assignment_prob
        
        # Deep ITM factor
        itm_pct = intrinsic / option.strike
        if itm_pct >= self.deep_itm_threshold:
            prob *= (1 + itm_pct * 5)  # Up to 2.5x for 10% ITM
        
        # Time value factor (low TV = higher assignment)
        if option.strike > 0:
            tv_pct = time_value / option.strike
            if tv_pct < self.time_value_threshold:
                prob *= 3  # 3x for very low time value
        
        # Dividend factor (calls only)
        if option.option_type.is_call and option.underlying in dividends:
            ex_date, div_amount = dividends[option.underlying]
            days_to_ex = (ex_date - current_date).days
            
            if 0 < days_to_ex <= 2:
                # Near ex-div
                if time_value < div_amount:
                    prob = self.dividend_assignment_prob
        
        # DTE factor (higher near expiration)
        dte = option.days_to_expiry
        if dte <= 7:
            prob *= (1 + (7 - dte) / 7)  # Up to 2x in final week
        
        return min(prob, 0.95)  # Cap at 95%


class OptionsBacktest:
    """
    Options-specific backtesting wrapper.
    
    Adds options-specific logic to base backtest engine:
    - Expiration processing
    - Assignment handling
    - Greeks tracking
    - P&L attribution
    
    Example:
        engine = BacktestEngine(config)
        options_bt = OptionsBacktest(engine)
        
        @options_bt.on_expiration
        def handle_expiration(event):
            logger.info(f"Expired: {event.symbol} -> {event.action}")
        
        result = options_bt.run(market_data)
    """
    
    def __init__(
        self,
        engine: Any,  # BacktestEngine
        expiration_handler: Optional[ExpirationHandler] = None,
        assignment_handler: Optional[AssignmentHandler] = None,
    ) -> None:
        """
        Initialize options backtest.
        
        Args:
            engine: Base backtest engine
            expiration_handler: Handler for expirations
            assignment_handler: Handler for assignments
        """
        self.engine = engine
        self.expiration_handler = expiration_handler or ExpirationHandler()
        self.assignment_handler = assignment_handler or AssignmentHandler()
        
        # Event history
        self._expiration_events: List[ExpirationEvent] = []
        self._assignment_events: List[AssignmentEvent] = []
        
        # Callbacks
        self._on_expiration_callbacks: List[Callable] = []
        self._on_assignment_callbacks: List[Callable] = []
        
        # Greeks tracking
        self._daily_greeks: Dict[date, Dict[str, float]] = {}
        
        # Register with engine
        self._register_hooks()
    
    def _register_hooks(self) -> None:
        """Register hooks with the base engine."""
        # Hook into end-of-day processing
        original_on_bar = self.engine._on_bar_callbacks.copy()
        
        @self.engine.on_bar
        def options_hook(timestamp: datetime, data: Dict[str, Any]):
            # Process expirations at market close
            if timestamp.time() >= time(16, 0):
                self._process_daily_expirations(timestamp.date(), data)
                self._check_daily_assignments(timestamp.date(), data)
    
    def on_expiration(self, callback: Callable) -> Callable:
        """Register callback for expiration events."""
        self._on_expiration_callbacks.append(callback)
        return callback
    
    def on_assignment(self, callback: Callable) -> Callable:
        """Register callback for assignment events."""
        self._on_assignment_callbacks.append(callback)
        return callback
    
    def _process_daily_expirations(
        self,
        current_date: date,
        market_data: Dict[str, Any],
    ) -> None:
        """Process expirations for the day."""
        # Get spot prices
        spots = {}
        for symbol, data in market_data.items():
            # Extract underlying from option symbol
            try:
                option = parse_osi_symbol(symbol)
                spots[option.underlying] = data.get("underlying_price", data.get("close", 0))
            except Exception:
                # Stock data
                spots[symbol] = data.get("close", 0)
        
        # Convert positions to dict format
        positions = {}
        for symbol, pos in self.engine.get_positions().items():
            positions[symbol] = {
                "quantity": pos.quantity,
                "entry_price": pos.entry_price,
            }
        
        # Process expirations
        events = self.expiration_handler.process_expirations(
            positions=positions,
            spot_prices=spots,
            current_date=current_date,
        )
        
        # Handle each event
        for event in events:
            self._handle_expiration_event(event)
    
    def _handle_expiration_event(self, event: ExpirationEvent) -> None:
        """Handle a single expiration event."""
        self._expiration_events.append(event)
        
        # Update engine state based on action
        if event.action == ExpirationAction.EXPIRE_WORTHLESS:
            # Remove position, realize loss
            if event.symbol in self.engine._positions:
                del self.engine._positions[event.symbol]
        
        elif event.action == ExpirationAction.CASH_SETTLE:
            # Remove position, settle cash
            if event.symbol in self.engine._positions:
                del self.engine._positions[event.symbol]
            self.engine._cash += event.pnl
        
        elif event.action in (ExpirationAction.EXERCISE, ExpirationAction.ASSIGN):
            # Remove option, add stock position
            if event.symbol in self.engine._positions:
                del self.engine._positions[event.symbol]
            
            # Add/adjust stock position
            option = parse_osi_symbol(event.symbol)
            if event.stock_quantity != 0:
                # Would add stock position here
                # Simplified: just adjust cash for value
                cash_change = event.stock_quantity * event.stock_price
                self.engine._cash -= cash_change
        
        # Fire callbacks
        for cb in self._on_expiration_callbacks:
            try:
                cb(event)
            except Exception as e:
                logger.error(f"Expiration callback error: {e}")
    
    def _check_daily_assignments(
        self,
        current_date: date,
        market_data: Dict[str, Any],
    ) -> None:
        """Check for early assignments."""
        spots = {}
        option_prices = {}
        
        for symbol, data in market_data.items():
            try:
                option = parse_osi_symbol(symbol)
                spots[option.underlying] = data.get("underlying_price", data.get("close", 0))
                option_prices[symbol] = data.get("close", 0)
            except Exception:
                spots[symbol] = data.get("close", 0)
        
        positions = {}
        for symbol, pos in self.engine.get_positions().items():
            positions[symbol] = {
                "quantity": pos.quantity,
                "entry_price": pos.entry_price,
            }
        
        events = self.assignment_handler.check_assignments(
            positions=positions,
            spot_prices=spots,
            option_prices=option_prices,
            current_date=current_date,
        )
        
        for event in events:
            self._handle_assignment_event(event)
    
    def _handle_assignment_event(self, event: AssignmentEvent) -> None:
        """Handle a single assignment event."""
        self._assignment_events.append(event)
        
        # Remove option position
        if event.symbol in self.engine._positions:
            del self.engine._positions[event.symbol]
        
        # Adjust cash
        self.engine._cash += event.cash_change + event.option_pnl
        
        # Fire callbacks
        for cb in self._on_assignment_callbacks:
            try:
                cb(event)
            except Exception as e:
                logger.error(f"Assignment callback error: {e}")
    
    def get_expiration_events(self) -> List[ExpirationEvent]:
        """Get all expiration events."""
        return self._expiration_events
    
    def get_assignment_events(self) -> List[AssignmentEvent]:
        """Get all assignment events."""
        return self._assignment_events
    
    def get_options_summary(self) -> Dict[str, Any]:
        """Get summary of options-specific events."""
        total_expiry_pnl = sum(e.pnl for e in self._expiration_events)
        total_assignment_pnl = sum(e.option_pnl for e in self._assignment_events)
        
        return {
            "total_expirations": len(self._expiration_events),
            "expired_worthless": sum(
                1 for e in self._expiration_events
                if e.action == ExpirationAction.EXPIRE_WORTHLESS
            ),
            "exercised": sum(
                1 for e in self._expiration_events
                if e.action == ExpirationAction.EXERCISE
            ),
            "assigned_at_expiry": sum(
                1 for e in self._expiration_events
                if e.action == ExpirationAction.ASSIGN
            ),
            "cash_settled": sum(
                1 for e in self._expiration_events
                if e.action == ExpirationAction.CASH_SETTLE
            ),
            "total_expiry_pnl": round(total_expiry_pnl, 2),
            "total_early_assignments": len(self._assignment_events),
            "total_assignment_pnl": round(total_assignment_pnl, 2),
        }

"""
Recipe Executor Engine - Core Automation Runtime
================================================

The heart of the No-Code Options Trading Engine.
Executes Recipe JSON configurations without any code changes.

Architecture:
------------
┌─────────────────────────────────────────────────────────────┐
│                    RecipeExecutor                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │ Scheduler │  │  Logic   │  │  Action  │  │  Position  │ │
│  │  Manager  │  │  Parser  │  │ Executor │  │  Manager   │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘ │
│        │              │              │              │       │
│        └──────────────┴──────────────┴──────────────┘       │
│                           │                                  │
│                    ┌──────┴──────┐                          │
│                    │ Event Loop  │                          │
│                    └─────────────┘                          │
└─────────────────────────────────────────────────────────────┘

Execution Flow:
--------------
1. Load Recipe JSON
2. Schedule triggers (market open, interval, etc.)
3. On trigger:
   a. Evaluate entry conditions
   b. If conditions pass, execute actions
   c. Create/manage positions
4. Monitor open positions:
   a. Evaluate exit conditions (take profit, stop loss, DTE)
   b. Execute position management

Frontend Integration:
-------------------
```javascript
// Start/stop bot execution
const [isRunning, setIsRunning] = useState(false);

const handleToggle = async () => {
    const endpoint = isRunning ? '/api/bot/stop' : '/api/bot/start';
    await fetch(endpoint, { method: 'POST', body: JSON.stringify({ recipe_id }) });
    setIsRunning(!isRunning);
};

// Real-time status via WebSocket
useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/bot');
    ws.onmessage = (e) => {
        const { type, data } = JSON.parse(e.data);
        if (type === 'position_opened') addPosition(data);
        if (type === 'condition_triggered') showNotification(data);
    };
    return () => ws.close();
}, []);
```
"""

from __future__ import annotations
import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, time as dt_time, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import uuid4
import threading

from .schema import (
    Recipe,
    Trigger,
    TriggerType,
    ConditionGroup,
    ConditionOperator,
    ActionType,
    OpenPositionAction,
    ClosePositionAction,
    CloseAllPositionsAction,
    AlertAction,
    LogAction,
    OptionStrategy,
    TakeProfitConfig,
    StopLossConfig,
    TrailingStopConfig,
    DTEExitConfig,
    PositionManagement,
    IndicatorCondition,
    PositionCondition,
)
from .data_handler import DataHandler
from .broker import (
    BrokerInterface,
    Order,
    OrderSide,
    OrderType,
    AssetType,
    OptionLegOrder,
    Position,
    PositionStatus,
)
from .logic_parser import LogicParser, EvaluationContext

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class ExecutorState(str, Enum):
    """Executor state."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ExecutionEvent:
    """Event emitted during execution."""
    type: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


@dataclass
class BotContext:
    """
    Runtime context for a bot executing a recipe.
    
    Tracks state, positions, and execution history.
    """
    bot_id: str = field(default_factory=lambda: str(uuid4()))
    recipe: Optional[Recipe] = None
    state: ExecutorState = ExecutorState.IDLE
    
    # Position tracking
    open_positions: List[str] = field(default_factory=list)  # Position IDs
    max_positions: int = 1
    
    # Execution tracking
    last_trigger_time: Optional[datetime] = None
    total_triggers: int = 0
    total_trades: int = 0
    
    # Events
    events: List[ExecutionEvent] = field(default_factory=list)
    
    def add_event(self, event_type: str, **data):
        event = ExecutionEvent(type=event_type, data=data)
        self.events.append(event)
        # Keep last 100 events
        if len(self.events) > 100:
            self.events = self.events[-100:]


# =============================================================================
# ACTION EXECUTOR
# =============================================================================

class ActionExecutor:
    """
    Executes actions defined in Recipe.
    
    Translates Recipe actions into broker orders.
    """
    
    def __init__(self, broker: BrokerInterface, data_handler: DataHandler):
        self.broker = broker
        self.data_handler = data_handler
    
    def execute_action(
        self,
        action: Union[OpenPositionAction, ClosePositionAction, AlertAction, LogAction],
        context: BotContext
    ) -> Optional[Union[Order, Position]]:
        """Execute a single action."""
        if isinstance(action, OpenPositionAction):
            return self._execute_open_position(action, context)
        elif isinstance(action, ClosePositionAction):
            return self._execute_close_position(action, context)
        elif isinstance(action, CloseAllPositionsAction):
            return self._execute_close_all_positions(action, context)
        elif isinstance(action, AlertAction):
            return self._execute_alert(action, context)
        elif isinstance(action, LogAction):
            return self._execute_log(action, context)
        else:
            logger.warning(f"Unknown action type: {type(action)}")
            return None
    
    def _execute_open_position(
        self,
        action: OpenPositionAction,
        context: BotContext
    ) -> Optional[Order]:
        """Execute open position action."""
        symbol = action.symbol
        strategy = action.strategy
        quantity = action.quantity
        
        # Get current price for order
        quote = self.data_handler.get_quote(symbol)
        current_price = quote.price
        
        # Build order based on strategy
        order = Order(
            bot_id=context.bot_id,
            recipe_id=context.recipe.id if context.recipe else None,
            symbol=symbol,
            strategy=strategy.value if isinstance(strategy, OptionStrategy) else str(strategy),
        )
        
        if strategy == OptionStrategy.LONG_EQUITY:
            order.asset_type = AssetType.EQUITY
            order.side = OrderSide.BUY
            order.quantity = quantity
            order.limit_price = current_price
        
        elif strategy == OptionStrategy.SHORT_EQUITY:
            order.asset_type = AssetType.EQUITY
            order.side = OrderSide.SELL
            order.quantity = quantity
            order.limit_price = current_price
        
        elif strategy in [
            OptionStrategy.LONG_CALL, OptionStrategy.LONG_PUT,
            OptionStrategy.SHORT_CALL, OptionStrategy.SHORT_PUT
        ]:
            order.asset_type = AssetType.OPTION
            order = self._build_single_option_order(order, action, current_price)
        
        elif strategy in [
            OptionStrategy.LONG_CALL_SPREAD, OptionStrategy.SHORT_CALL_SPREAD,
            OptionStrategy.LONG_PUT_SPREAD, OptionStrategy.SHORT_PUT_SPREAD
        ]:
            order.asset_type = AssetType.OPTION
            order = self._build_spread_order(order, action, current_price)
        
        elif strategy == OptionStrategy.IRON_CONDOR:
            order.asset_type = AssetType.OPTION
            order = self._build_iron_condor_order(order, action, current_price)
        
        elif strategy == OptionStrategy.IRON_BUTTERFLY:
            order.asset_type = AssetType.OPTION
            order = self._build_iron_butterfly_order(order, action, current_price)
        
        else:
            logger.warning(f"Unsupported strategy: {strategy}")
            return None
        
        # Submit order
        filled_order = self.broker.submit_order(order)
        
        # Track position
        positions = self.broker.get_positions(bot_id=context.bot_id, status=PositionStatus.OPEN)
        if positions:
            context.open_positions = [p.id for p in positions]
        
        context.total_trades += 1
        context.add_event("position_opened", order_id=filled_order.id, symbol=symbol, strategy=str(strategy))
        
        logger.info(f"Opened position: {symbol} {strategy}")
        return filled_order
    
    def _build_single_option_order(
        self,
        order: Order,
        action: OpenPositionAction,
        current_price: float
    ) -> Order:
        """Build single-leg option order."""
        # Determine option type
        is_call = "call" in str(action.strategy).lower()
        is_long = "long" in str(action.strategy).lower()
        
        # Calculate strike and expiration from legs
        if action.legs and len(action.legs) > 0:
            leg_config = action.legs[0]
            strike = self._calculate_strike(current_price, leg_config.strike_selection, leg_config.strike_value)
            expiration = self._calculate_expiration(leg_config.expiration_selection, leg_config.expiration_value)
        else:
            # Default: ATM, 30 DTE
            strike = round(current_price)
            expiration = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        leg = OptionLegOrder(
            option_type="call" if is_call else "put",
            side=OrderSide.BUY_TO_OPEN if is_long else OrderSide.SELL_TO_OPEN,
            strike=strike,
            expiration=expiration,
            quantity=action.quantity,
        )
        leg.generate_symbol(action.symbol)
        
        order.legs = [leg]
        order.quantity = action.quantity
        order.side = OrderSide.BUY_TO_OPEN if is_long else OrderSide.SELL_TO_OPEN
        
        # Estimate price
        chain = self.data_handler.get_option_chain(action.symbol, expiration)
        contracts = chain.calls if is_call else chain.puts
        for c in contracts:
            if c.get("strike") == strike:
                order.limit_price = (c.get("bid", 0) + c.get("ask", 0)) / 2
                break
        
        return order
    
    def _build_spread_order(
        self,
        order: Order,
        action: OpenPositionAction,
        current_price: float
    ) -> Order:
        """Build vertical spread order (call or put spread)."""
        strategy_str = str(action.strategy).lower()
        is_call = "call" in strategy_str
        is_long = "long" in strategy_str  # Long spread = debit, Short spread = credit
        
        # Get leg configurations or use defaults
        if action.legs and len(action.legs) >= 2:
            leg1_config = action.legs[0]
            leg2_config = action.legs[1]
            strike1 = self._calculate_strike(current_price, leg1_config.strike_selection, leg1_config.strike_value)
            strike2 = self._calculate_strike(current_price, leg2_config.strike_selection, leg2_config.strike_value)
            expiration = self._calculate_expiration(leg1_config.expiration_selection, leg1_config.expiration_value)
        else:
            # Default: $5 wide spread
            if is_call:
                strike1 = round(current_price) if is_long else round(current_price) + 5
                strike2 = round(current_price) + 5 if is_long else round(current_price)
            else:
                strike1 = round(current_price) if is_long else round(current_price) - 5
                strike2 = round(current_price) - 5 if is_long else round(current_price)
            expiration = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")
        
        # Build legs
        # For long spread: buy closer strike, sell further strike
        # For short spread: sell closer strike, buy further strike
        if is_long:
            buy_strike = min(strike1, strike2) if is_call else max(strike1, strike2)
            sell_strike = max(strike1, strike2) if is_call else min(strike1, strike2)
        else:
            sell_strike = min(strike1, strike2) if is_call else max(strike1, strike2)
            buy_strike = max(strike1, strike2) if is_call else min(strike1, strike2)
        
        leg1 = OptionLegOrder(
            option_type="call" if is_call else "put",
            side=OrderSide.BUY_TO_OPEN,
            strike=buy_strike,
            expiration=expiration,
            quantity=action.quantity,
        )
        leg1.generate_symbol(action.symbol)
        
        leg2 = OptionLegOrder(
            option_type="call" if is_call else "put",
            side=OrderSide.SELL_TO_OPEN,
            strike=sell_strike,
            expiration=expiration,
            quantity=action.quantity,
        )
        leg2.generate_symbol(action.symbol)
        
        order.legs = [leg1, leg2]
        order.quantity = action.quantity
        order.side = OrderSide.BUY_TO_OPEN if is_long else OrderSide.SELL_TO_OPEN
        
        # Estimate spread price
        chain = self.data_handler.get_option_chain(action.symbol, expiration)
        contracts = chain.calls if is_call else chain.puts
        
        buy_price = 0
        sell_price = 0
        for c in contracts:
            if c.get("strike") == buy_strike:
                buy_price = (c.get("bid", 0) + c.get("ask", 0)) / 2
            if c.get("strike") == sell_strike:
                sell_price = (c.get("bid", 0) + c.get("ask", 0)) / 2
        
        order.limit_price = abs(buy_price - sell_price)
        
        return order
    
    def _build_iron_condor_order(
        self,
        order: Order,
        action: OpenPositionAction,
        current_price: float
    ) -> Order:
        """Build iron condor order (4 legs)."""
        # Default: 10% OTM wings, $5 wide
        put_short_strike = round(current_price * 0.95)
        put_long_strike = put_short_strike - 5
        call_short_strike = round(current_price * 1.05)
        call_long_strike = call_short_strike + 5
        
        expiration = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")
        
        order.legs = [
            OptionLegOrder(option_type="put", side=OrderSide.BUY_TO_OPEN, strike=put_long_strike, expiration=expiration, quantity=action.quantity),
            OptionLegOrder(option_type="put", side=OrderSide.SELL_TO_OPEN, strike=put_short_strike, expiration=expiration, quantity=action.quantity),
            OptionLegOrder(option_type="call", side=OrderSide.SELL_TO_OPEN, strike=call_short_strike, expiration=expiration, quantity=action.quantity),
            OptionLegOrder(option_type="call", side=OrderSide.BUY_TO_OPEN, strike=call_long_strike, expiration=expiration, quantity=action.quantity),
        ]
        
        for leg in order.legs:
            leg.generate_symbol(action.symbol)
        
        order.quantity = action.quantity
        order.side = OrderSide.SELL_TO_OPEN  # Iron condor is a credit strategy
        order.limit_price = 1.50  # Default credit
        
        return order
    
    def _build_iron_butterfly_order(
        self,
        order: Order,
        action: OpenPositionAction,
        current_price: float
    ) -> Order:
        """Build iron butterfly order (4 legs, ATM short strikes)."""
        atm_strike = round(current_price)
        put_long_strike = atm_strike - 10
        call_long_strike = atm_strike + 10
        
        expiration = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")
        
        order.legs = [
            OptionLegOrder(option_type="put", side=OrderSide.BUY_TO_OPEN, strike=put_long_strike, expiration=expiration, quantity=action.quantity),
            OptionLegOrder(option_type="put", side=OrderSide.SELL_TO_OPEN, strike=atm_strike, expiration=expiration, quantity=action.quantity),
            OptionLegOrder(option_type="call", side=OrderSide.SELL_TO_OPEN, strike=atm_strike, expiration=expiration, quantity=action.quantity),
            OptionLegOrder(option_type="call", side=OrderSide.BUY_TO_OPEN, strike=call_long_strike, expiration=expiration, quantity=action.quantity),
        ]
        
        for leg in order.legs:
            leg.generate_symbol(action.symbol)
        
        order.quantity = action.quantity
        order.side = OrderSide.SELL_TO_OPEN
        order.limit_price = 5.00  # Default credit
        
        return order
    
    def _calculate_strike(
        self,
        current_price: float,
        selection: str,
        value: Optional[float]
    ) -> float:
        """Calculate strike price based on selection method."""
        selection = str(selection).lower()
        
        if selection == "atm" or selection == "at_the_money":
            return round(current_price)
        elif selection == "otm_percent" and value:
            return round(current_price * (1 + value / 100))
        elif selection == "itm_percent" and value:
            return round(current_price * (1 - value / 100))
        elif selection == "otm_delta" and value:
            # Simplified: use percent as proxy
            return round(current_price * (1 + value))
        elif selection == "fixed" and value:
            return value
        else:
            return round(current_price)
    
    def _calculate_expiration(
        self,
        selection: str,
        value: Optional[int]
    ) -> str:
        """Calculate expiration date based on selection method."""
        selection = str(selection).lower()
        today = datetime.now()
        
        if selection == "dte" and value:
            target = today + timedelta(days=value)
        elif selection == "weekly":
            # Next Friday
            days_until_friday = (4 - today.weekday()) % 7
            if days_until_friday == 0:
                days_until_friday = 7
            target = today + timedelta(days=days_until_friday)
        elif selection == "monthly":
            # Third Friday of next month
            if today.day < 15:
                month = today.month
                year = today.year
            else:
                month = today.month + 1 if today.month < 12 else 1
                year = today.year if today.month < 12 else today.year + 1
            
            first_day = datetime(year, month, 1)
            first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
            target = first_friday + timedelta(weeks=2)
        else:
            target = today + timedelta(days=45)
        
        return target.strftime("%Y-%m-%d")
    
    def _execute_close_position(
        self,
        action: ClosePositionAction,
        context: BotContext
    ) -> Optional[Order]:
        """Execute close position action."""
        # Get open positions for this bot
        positions = self.broker.get_positions(bot_id=context.bot_id, status=PositionStatus.OPEN)
        
        if not positions:
            logger.warning("No open positions to close")
            return None
        
        # Close first matching position (or specific one)
        position = positions[0]  # TODO: Add position selection logic
        
        order = self.broker.close_position(
            position.id,
            percent=action.percent or 100.0
        )
        
        context.open_positions = [p.id for p in positions if p.id != position.id]
        context.add_event("position_closed", position_id=position.id, pnl=position.realized_pnl)
        
        logger.info(f"Closed position: {position.symbol}")
        return order
    
    def _execute_close_all_positions(
        self,
        action: CloseAllPositionsAction,
        context: BotContext
    ) -> List[Order]:
        """Execute close all positions action."""
        positions = self.broker.get_positions(bot_id=context.bot_id, status=PositionStatus.OPEN)
        
        orders = []
        for position in positions:
            order = self.broker.close_position(position.id)
            orders.append(order)
            context.add_event("position_closed", position_id=position.id)
        
        context.open_positions = []
        logger.info(f"Closed {len(orders)} positions")
        return orders
    
    def _execute_alert(self, action: AlertAction, context: BotContext) -> None:
        """Execute alert action."""
        message = action.message
        channels = action.channels or ["log"]
        
        for channel in channels:
            if channel == "log":
                logger.info(f"ALERT: {message}")
            elif channel == "email":
                # TODO: Implement email
                logger.info(f"EMAIL ALERT: {message}")
            elif channel == "sms":
                # TODO: Implement SMS
                logger.info(f"SMS ALERT: {message}")
            elif channel == "push":
                # TODO: Implement push notification
                logger.info(f"PUSH ALERT: {message}")
        
        context.add_event("alert_sent", message=message, channels=channels)
    
    def _execute_log(self, action: LogAction, context: BotContext) -> None:
        """Execute log action."""
        logger.info(f"BOT LOG: {action.message}")
        context.add_event("log", message=action.message)


# =============================================================================
# POSITION MANAGER
# =============================================================================

class PositionManager:
    """
    Manages position lifecycle and exit conditions.
    
    Monitors positions for:
    - Take profit targets
    - Stop loss triggers
    - DTE exit rules
    - Trailing stops
    """
    
    def __init__(
        self,
        broker: BrokerInterface,
        data_handler: DataHandler,
        logic_parser: LogicParser
    ):
        self.broker = broker
        self.data_handler = data_handler
        self.logic_parser = logic_parser
    
    def check_exits(
        self,
        management: PositionManagement,
        context: BotContext
    ) -> List[str]:
        """
        Check exit conditions for all open positions.
        
        Returns list of position IDs that should be closed.
        """
        positions_to_close = []
        
        for position_id in context.open_positions:
            position = self.broker.get_position(position_id)
            if not position:
                continue
            
            should_close, reason = self._check_position_exits(position, management)
            if should_close:
                logger.info(f"Position {position_id} triggered exit: {reason}")
                positions_to_close.append((position_id, reason))
        
        return positions_to_close
    
    def _check_position_exits(
        self,
        position: Position,
        management: PositionManagement
    ) -> tuple[bool, str]:
        """Check all exit conditions for a single position."""
        # Take Profit
        if management.take_profit:
            tp = management.take_profit
            if tp.type == "percent":
                if position.unrealized_pnl_pct >= tp.value:
                    return True, f"Take profit triggered ({position.unrealized_pnl_pct:.1f}% >= {tp.value}%)"
            elif tp.type == "max_profit_pct" and position.max_profit:
                pct_of_max = (position.unrealized_pnl / position.max_profit) * 100
                if pct_of_max >= tp.value:
                    return True, f"Take profit at {tp.value}% of max profit"
            elif tp.type == "dollar":
                if position.unrealized_pnl >= tp.value:
                    return True, f"Take profit triggered (${position.unrealized_pnl:.2f} >= ${tp.value})"
        
        # Stop Loss
        if management.stop_loss:
            sl = management.stop_loss
            if sl.type == "percent":
                if position.unrealized_pnl_pct <= -sl.value:
                    return True, f"Stop loss triggered ({position.unrealized_pnl_pct:.1f}% <= -{sl.value}%)"
            elif sl.type == "max_loss_pct" and position.max_loss:
                pct_of_max = (abs(position.unrealized_pnl) / abs(position.max_loss)) * 100
                if position.unrealized_pnl < 0 and pct_of_max >= sl.value:
                    return True, f"Stop loss at {sl.value}% of max loss"
            elif sl.type == "dollar":
                if position.unrealized_pnl <= -sl.value:
                    return True, f"Stop loss triggered (${position.unrealized_pnl:.2f} <= -${sl.value})"
        
        # DTE Exit
        if management.dte_exit:
            dte = management.dte_exit
            if position.dte is not None and position.dte <= dte.days:
                return True, f"DTE exit triggered ({position.dte} days <= {dte.days})"
        
        return False, ""
    
    def close_position(
        self,
        position_id: str,
        reason: str,
        context: BotContext
    ) -> Optional[Order]:
        """Close a position and record the reason."""
        try:
            order = self.broker.close_position(position_id)
            context.open_positions = [p for p in context.open_positions if p != position_id]
            context.add_event("position_closed", position_id=position_id, reason=reason)
            return order
        except Exception as e:
            logger.error(f"Failed to close position {position_id}: {e}")
            return None


# =============================================================================
# RECIPE EXECUTOR
# =============================================================================

class RecipeExecutor:
    """
    Main engine that executes Recipe configurations.
    
    This is the core of the No-Code Options Trading Engine.
    Recipes are loaded, scheduled, and executed without any code changes.
    
    Usage:
        # Load and run a recipe
        executor = RecipeExecutor(data_handler, broker)
        executor.load_recipe(recipe_json)
        executor.start()
        
        # Or manually trigger
        executor.trigger()
        
        # Check status
        status = executor.get_status()
    """
    
    def __init__(
        self,
        data_handler: DataHandler,
        broker: BrokerInterface,
    ):
        self.data_handler = data_handler
        self.broker = broker
        self.logic_parser = LogicParser()
        self.action_executor = ActionExecutor(broker, data_handler)
        self.position_manager = PositionManager(broker, data_handler, self.logic_parser)
        
        # Contexts for running bots
        self._contexts: Dict[str, BotContext] = {}
        
        # Scheduler
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Event callbacks
        self._event_callbacks: List[Callable[[ExecutionEvent], None]] = []
    
    def load_recipe(self, recipe: Union[Recipe, Dict, str, Path]) -> BotContext:
        """
        Load a recipe and create a bot context.
        
        Args:
            recipe: Recipe object, dict, JSON string, or path to JSON file
            
        Returns:
            BotContext for the loaded recipe
        """
        # Parse recipe if needed
        if isinstance(recipe, (str, Path)):
            if Path(recipe).exists():
                with open(recipe, "r") as f:
                    recipe = json.load(f)
            else:
                recipe = json.loads(recipe)
        
        if isinstance(recipe, dict):
            recipe = Recipe(**recipe)
        
        # Create context
        context = BotContext(
            recipe=recipe,
            max_positions=recipe.max_positions or 1,
        )
        
        self._contexts[context.bot_id] = context
        recipe_name = recipe.metadata.name if recipe.metadata else recipe.symbol
        logger.info(f"Loaded recipe '{recipe_name}' as bot {context.bot_id}")
        
        return context
    
    def start(self, bot_id: Optional[str] = None) -> None:
        """Start executing a bot (or all bots)."""
        if bot_id:
            contexts = [self._contexts.get(bot_id)]
        else:
            contexts = list(self._contexts.values())
        
        for ctx in contexts:
            if ctx:
                ctx.state = ExecutorState.RUNNING
                ctx.add_event("bot_started")
                logger.info(f"Bot {ctx.bot_id} started")
        
        self._running = True
    
    def stop(self, bot_id: Optional[str] = None) -> None:
        """Stop a bot (or all bots)."""
        if bot_id:
            contexts = [self._contexts.get(bot_id)]
        else:
            contexts = list(self._contexts.values())
        
        for ctx in contexts:
            if ctx:
                ctx.state = ExecutorState.STOPPED
                ctx.add_event("bot_stopped")
                logger.info(f"Bot {ctx.bot_id} stopped")
        
        if not bot_id:
            self._running = False
    
    def pause(self, bot_id: str) -> None:
        """Pause a bot."""
        ctx = self._contexts.get(bot_id)
        if ctx:
            ctx.state = ExecutorState.PAUSED
            ctx.add_event("bot_paused")
    
    def trigger(self, bot_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Manually trigger recipe evaluation.
        
        This is the main execution entry point.
        Called by scheduler or manually.
        """
        results = {}
        
        if bot_id:
            contexts = [self._contexts.get(bot_id)]
        else:
            contexts = [ctx for ctx in self._contexts.values() if ctx.state == ExecutorState.RUNNING]
        
        for ctx in contexts:
            if not ctx or ctx.state != ExecutorState.RUNNING:
                continue
            
            try:
                result = self._execute_recipe(ctx)
                results[ctx.bot_id] = result
                ctx.last_trigger_time = datetime.now()
                ctx.total_triggers += 1
            except Exception as e:
                logger.error(f"Error executing recipe for bot {ctx.bot_id}: {e}")
                ctx.state = ExecutorState.ERROR
                ctx.add_event("error", message=str(e))
                results[ctx.bot_id] = {"error": str(e)}
        
        return results
    
    def _execute_recipe(self, context: BotContext) -> Dict[str, Any]:
        """Execute a single recipe."""
        recipe = context.recipe
        result = {
            "triggered": False,
            "conditions_met": False,
            "actions_executed": [],
            "positions_closed": [],
        }
        
        # Update position prices
        self.broker.update_positions(self.data_handler)
        
        # Check exit conditions for open positions first
        if recipe.management:
            exits = self.position_manager.check_exits(recipe.management, context)
            for position_id, reason in exits:
                order = self.position_manager.close_position(position_id, reason, context)
                result["positions_closed"].append({
                    "position_id": position_id,
                    "reason": reason,
                    "order_id": order.id if order else None
                })
        
        # Check if we can open new positions
        if len(context.open_positions) >= context.max_positions:
            logger.debug(f"Max positions reached ({context.max_positions})")
            return result
        
        # Get primary symbol from first action
        primary_symbol = None
        for action in recipe.actions:
            if hasattr(action, 'symbol') and action.symbol:
                primary_symbol = action.symbol
                break
        
        # Create evaluation context
        eval_context = EvaluationContext(
            data_handler=self.data_handler,
            broker=self.broker,
            symbol=primary_symbol,
            bot_id=context.bot_id,
        )
        
        # Evaluate entry conditions
        if recipe.entry_conditions:
            # Handle both ConditionGroup and list of conditions
            if isinstance(recipe.entry_conditions, ConditionGroup):
                conditions_met = self.logic_parser.evaluate_group(
                    recipe.entry_conditions,
                    eval_context
                )
            else:
                conditions_met = self.logic_parser.evaluate_conditions_list(
                    recipe.entry_conditions,
                    eval_context
                )
        else:
            conditions_met = True
        
        result["conditions_met"] = conditions_met
        
        if conditions_met:
            result["triggered"] = True
            context.add_event("conditions_triggered")
            
            # Execute actions
            for action in recipe.actions:
                try:
                    action_result = self.action_executor.execute_action(action, context)
                    result["actions_executed"].append({
                        "type": type(action).__name__,
                        "success": True,
                        "result": str(action_result) if action_result else None
                    })
                except Exception as e:
                    logger.error(f"Action failed: {e}")
                    result["actions_executed"].append({
                        "type": type(action).__name__,
                        "success": False,
                        "error": str(e)
                    })
        
        return result
    
    def check_trigger(self, trigger: Trigger) -> bool:
        """Check if a trigger should fire now."""
        now = datetime.now()
        
        if trigger.type == TriggerType.MARKET_OPEN:
            # Check if it's market open time (9:30 AM ET)
            market_open = dt_time(9, 30)
            return now.time() >= market_open and now.time() < dt_time(9, 35)
        
        elif trigger.type == TriggerType.MARKET_CLOSE:
            # Check if it's market close time (4:00 PM ET)
            market_close = dt_time(16, 0)
            return now.time() >= dt_time(15, 55) and now.time() <= market_close
        
        elif trigger.type == TriggerType.INTERVAL:
            # Check interval (simplified)
            interval_minutes = trigger.config.get("minutes", 5) if trigger.config else 5
            return now.minute % interval_minutes == 0
        
        elif trigger.type == TriggerType.SCHEDULE:
            # Check schedule
            schedule = trigger.config or {}
            days = schedule.get("days", [])
            time_str = schedule.get("time", "09:30")
            
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            current_day = day_names[now.weekday()]
            
            if days and current_day not in days:
                return False
            
            scheduled_time = datetime.strptime(time_str, "%H:%M").time()
            return now.time() >= scheduled_time and now.time() < (datetime.combine(now.date(), scheduled_time) + timedelta(minutes=1)).time()
        
        elif trigger.type == TriggerType.EVENT:
            # Events are triggered externally
            return False
        
        return False
    
    def get_status(self, bot_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of running bots."""
        if bot_id:
            ctx = self._contexts.get(bot_id)
            if not ctx:
                return {"error": "Bot not found"}
            return self._context_to_status(ctx)
        
        return {
            bot_id: self._context_to_status(ctx)
            for bot_id, ctx in self._contexts.items()
        }
    
    def _context_to_status(self, ctx: BotContext) -> Dict[str, Any]:
        """Convert context to status dict."""
        return {
            "bot_id": ctx.bot_id,
            "recipe_name": ctx.recipe.metadata.name if ctx.recipe and ctx.recipe.metadata else None,
            "state": ctx.state.value,
            "open_positions": len(ctx.open_positions),
            "max_positions": ctx.max_positions,
            "total_triggers": ctx.total_triggers,
            "total_trades": ctx.total_trades,
            "last_trigger": ctx.last_trigger_time.isoformat() if ctx.last_trigger_time else None,
            "recent_events": [e.to_dict() for e in ctx.events[-10:]],
        }
    
    def on_event(self, callback: Callable[[ExecutionEvent], None]) -> None:
        """Register event callback for real-time updates."""
        self._event_callbacks.append(callback)
    
    def _emit_event(self, event: ExecutionEvent) -> None:
        """Emit event to all callbacks."""
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Event callback error: {e}")


# =============================================================================
# ASYNC RUNNER (for production use)
# =============================================================================

class AsyncRecipeRunner:
    """
    Async runner for continuous recipe execution.
    
    Runs in background, checking triggers and managing positions.
    
    Usage:
        runner = AsyncRecipeRunner(executor)
        await runner.start()
        # ... later
        await runner.stop()
    """
    
    def __init__(self, executor: RecipeExecutor, interval_seconds: int = 60):
        self.executor = executor
        self.interval_seconds = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self) -> None:
        """Start the async runner."""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Async recipe runner started")
    
    async def stop(self) -> None:
        """Stop the async runner."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Async recipe runner stopped")
    
    async def _run_loop(self) -> None:
        """Main execution loop."""
        while self._running:
            try:
                # Check triggers for all running bots
                for ctx in self.executor._contexts.values():
                    if ctx.state != ExecutorState.RUNNING:
                        continue
                    
                    if ctx.recipe and ctx.recipe.triggers:
                        for trigger in ctx.recipe.triggers:
                            if self.executor.check_trigger(trigger):
                                self.executor.trigger(ctx.bot_id)
                                break
                
            except Exception as e:
                logger.error(f"Error in run loop: {e}")
            
            await asyncio.sleep(self.interval_seconds)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def run_recipe_once(
    recipe: Union[Recipe, Dict, str],
    data_handler: DataHandler,
    broker: BrokerInterface
) -> Dict[str, Any]:
    """
    Execute a recipe once and return results.
    
    Useful for testing and backtesting.
    
    Usage:
        result = run_recipe_once(recipe_json, data_handler, paper_broker)
        print(f"Positions opened: {result['actions_executed']}")
    """
    executor = RecipeExecutor(data_handler, broker)
    context = executor.load_recipe(recipe)
    executor.start(context.bot_id)
    return executor.trigger(context.bot_id).get(context.bot_id, {})


def backtest_recipe(
    recipe: Union[Recipe, Dict, str],
    data_handler: DataHandler,
    start_date: datetime,
    end_date: datetime,
    initial_capital: float = 100000.0
) -> Dict[str, Any]:
    """
    Backtest a recipe over historical data.
    
    Returns performance metrics.
    
    Usage:
        results = backtest_recipe(
            recipe,
            historical_data_handler,
            datetime(2023, 1, 1),
            datetime(2023, 12, 31)
        )
        print(f"Total return: {results['total_return']:.2f}%")
    """
    from .broker import PaperBroker
    
    broker = PaperBroker(initial_capital=initial_capital)
    executor = RecipeExecutor(data_handler, broker)
    context = executor.load_recipe(recipe)
    executor.start(context.bot_id)
    
    # Simulate daily execution
    current_date = start_date
    while current_date <= end_date:
        # Skip weekends
        if current_date.weekday() < 5:
            executor.trigger(context.bot_id)
        current_date += timedelta(days=1)
    
    # Get final results
    account = broker.get_account_info()
    
    return {
        "initial_capital": initial_capital,
        "final_equity": account["total_equity"],
        "total_return": account["total_return"],
        "total_trades": account["total_trades"],
        "win_rate": account["win_rate"],
        "total_pnl": account["total_pnl"],
        "total_commission": account["total_commission"],
        "status": executor.get_status(context.bot_id),
    }

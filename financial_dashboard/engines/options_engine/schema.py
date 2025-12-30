"""
Recipe Schema - Pydantic Models for No-Code Options Trading
===========================================================

This module defines the JSON schema for trading recipes using Pydantic.
Recipes define WHAT to trade, WHEN to trade, and HOW to manage positions.

Schema Structure (mirrors OptionsAlpha):
---------------------------------------
Recipe
├── metadata (name, description, version)
├── triggers[] (WHEN to run)
│   ├── type: "market_open" | "interval" | "event"
│   └── config: TriggerConfig
├── conditions[] (IF conditions to check)
│   ├── type: "symbol" | "indicator" | "position" | "general"
│   ├── operator: ">" | "<" | "==" | "between"
│   └── groups[] (AND/OR nesting)
├── actions[] (WHAT to do)
│   ├── type: "open_position" | "close_position" | "adjust"
│   └── strategy: OptionStrategy
└── management (HOW to manage)
    ├── take_profit: PercentConfig
    ├── stop_loss: PercentConfig
    └── trailing_stop: PercentConfig

Example Recipe JSON:
```json
{
    "name": "RSI Mean Reversion Short Put",
    "triggers": [{"type": "interval", "interval_minutes": 15}],
    "conditions": [{
        "type": "indicator",
        "indicator": "RSI",
        "symbol": "SPY",
        "period": 14,
        "operator": ">",
        "value": 70
    }],
    "actions": [{
        "type": "open_position",
        "strategy": "short_put_spread",
        "symbol": "SPY",
        "quantity": 1,
        "legs": [...]
    }],
    "management": {
        "take_profit_pct": 50,
        "stop_loss_pct": 200
    }
}
```
"""

from __future__ import annotations
from datetime import datetime, time
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# ENUMS - Define all possible values
# =============================================================================

class TriggerType(str, Enum):
    """When the recipe should be evaluated."""
    MARKET_OPEN = "market_open"
    MARKET_CLOSE = "market_close"
    INTERVAL = "interval"
    SCHEDULE = "schedule"
    EVENT = "event"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"


class ConditionType(str, Enum):
    """Types of conditions that can be evaluated."""
    SYMBOL = "symbol"          # Price-based: price > X
    INDICATOR = "indicator"    # Technical: RSI > 70
    POSITION = "position"      # Position P&L, DTE
    BOT = "bot"               # Bot metrics
    GENERAL = "general"        # Time, day of week
    OPPORTUNITY = "opportunity"  # Pre-trade filters


class ComparisonOperator(str, Enum):
    """Comparison operators for conditions."""
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    EQ = "=="
    NEQ = "!="
    BETWEEN = "between"
    NOT_BETWEEN = "not_between"
    IN = "in"
    NOT_IN = "not_in"


class ConditionOperator(str, Enum):
    """Logical operators for combining conditions."""
    AND = "and"
    OR = "or"


class ActionType(str, Enum):
    """Types of actions the bot can take."""
    OPEN_POSITION = "open_position"
    CLOSE_POSITION = "close_position"
    CLOSE_ALL_POSITIONS = "close_all_positions"
    ADJUST_POSITION = "adjust_position"
    SEND_ALERT = "send_alert"
    LOG = "log"


class OptionType(str, Enum):
    """Option contract type."""
    CALL = "call"
    PUT = "put"


class OptionStrategy(str, Enum):
    """Supported options strategies."""
    # Single Leg
    LONG_CALL = "long_call"
    LONG_PUT = "long_put"
    SHORT_CALL = "short_call"
    SHORT_PUT = "short_put"
    # Spreads
    LONG_CALL_SPREAD = "long_call_spread"
    SHORT_CALL_SPREAD = "short_call_spread"
    LONG_PUT_SPREAD = "long_put_spread"
    SHORT_PUT_SPREAD = "short_put_spread"
    # Multi-Leg
    IRON_CONDOR = "iron_condor"
    IRON_BUTTERFLY = "iron_butterfly"
    STRADDLE = "straddle"
    STRANGLE = "strangle"
    # Equity
    LONG_EQUITY = "long_equity"
    SHORT_EQUITY = "short_equity"


class Indicator(str, Enum):
    """Supported technical indicators."""
    RSI = "RSI"
    MACD = "MACD"
    MACD_SIGNAL = "MACD_SIGNAL"
    MACD_HISTOGRAM = "MACD_HISTOGRAM"
    SMA = "SMA"
    EMA = "EMA"
    BOLLINGER_UPPER = "BOLLINGER_UPPER"
    BOLLINGER_LOWER = "BOLLINGER_LOWER"
    BOLLINGER_MIDDLE = "BOLLINGER_MIDDLE"
    ATR = "ATR"
    VWAP = "VWAP"
    IV_RANK = "IV_RANK"
    IV_PERCENTILE = "IV_PERCENTILE"
    VIX = "VIX"


class StrikeSelection(str, Enum):
    """How to select strike prices."""
    ATM = "atm"                    # At the money
    OTM_DELTA = "otm_delta"        # By delta (e.g., 0.30 delta)
    OTM_PERCENT = "otm_percent"    # % out of the money
    OTM_DOLLARS = "otm_dollars"    # $ out of the money
    FIXED = "fixed"                # Exact strike price


class ExpirationSelection(str, Enum):
    """How to select expiration dates."""
    DTE = "dte"                    # Days to expiration
    WEEKLY = "weekly"              # Next weekly
    MONTHLY = "monthly"            # Next monthly
    SPECIFIC_DATE = "specific_date"


# =============================================================================
# TRIGGER MODELS
# =============================================================================

class TriggerConfig(BaseModel):
    """Configuration for different trigger types."""
    # For INTERVAL
    interval_minutes: Optional[int] = Field(None, ge=1, le=1440)
    
    # For SCHEDULE
    schedule_time: Optional[time] = None
    schedule_days: Optional[List[int]] = Field(None, description="0=Mon, 6=Sun")
    
    # For EVENT
    event_name: Optional[str] = None
    
    class Config:
        extra = "allow"


class Trigger(BaseModel):
    """
    Defines WHEN the recipe should be evaluated.
    
    Examples:
        - Market Open: Run at 9:30 AM ET
        - Interval: Run every 15 minutes
        - Event: Run when a position is opened
    """
    type: TriggerType
    config: TriggerConfig = Field(default_factory=TriggerConfig)
    enabled: bool = True
    
    @model_validator(mode='after')
    def validate_trigger_config(self) -> 'Trigger':
        """Ensure trigger has required config for its type."""
        if self.type == TriggerType.INTERVAL:
            if not self.config.interval_minutes:
                raise ValueError("INTERVAL trigger requires interval_minutes")
        elif self.type == TriggerType.SCHEDULE:
            if not self.config.schedule_time:
                raise ValueError("SCHEDULE trigger requires schedule_time")
        return self


# =============================================================================
# CONDITION MODELS
# =============================================================================

class SymbolCondition(BaseModel):
    """Condition based on symbol price."""
    type: Literal["symbol"] = "symbol"
    symbol: str
    field: str = Field(default="price", description="price, bid, ask, volume")
    operator: ComparisonOperator
    value: Union[float, List[float]]  # List for BETWEEN
    
    class Config:
        extra = "allow"


class IndicatorCondition(BaseModel):
    """Condition based on technical indicator."""
    type: Literal["indicator"] = "indicator"
    symbol: str
    indicator: Indicator
    period: int = Field(default=14, ge=1, le=200)
    operator: ComparisonOperator
    value: Union[float, List[float]]
    
    class Config:
        extra = "allow"


class PositionCondition(BaseModel):
    """Condition based on position metrics."""
    type: Literal["position"] = "position"
    field: str = Field(
        description="pnl_percent, pnl_dollars, dte, delta, theta, iv_change"
    )
    operator: ComparisonOperator
    value: Union[float, List[float]]
    position_filter: Optional[str] = None  # Filter specific positions
    
    class Config:
        extra = "allow"


class GeneralCondition(BaseModel):
    """General conditions (time, day, etc.)."""
    type: Literal["general"] = "general"
    field: str = Field(description="time_of_day, day_of_week, is_market_hours")
    operator: ComparisonOperator
    value: Union[Any, List[Any]]
    
    class Config:
        extra = "allow"


class OpportunityCondition(BaseModel):
    """Conditions for filtering trade opportunities."""
    type: Literal["opportunity"] = "opportunity"
    field: str = Field(description="iv_rank, expected_move, liquidity, spread")
    operator: ComparisonOperator
    value: Union[float, List[float]]
    
    class Config:
        extra = "allow"


# Union of all condition types
Condition = Union[
    SymbolCondition,
    IndicatorCondition,
    PositionCondition,
    GeneralCondition,
    OpportunityCondition,
]


class ConditionGroup(BaseModel):
    """
    Group of conditions with AND/OR logic.
    Supports nesting for complex conditions.
    
    Example:
        (RSI > 70 AND VIX < 20) OR (Price > SMA200)
    """
    operator: ConditionOperator = ConditionOperator.AND
    conditions: List[Union[Condition, 'ConditionGroup']] = Field(default_factory=list)
    
    class Config:
        extra = "allow"


# Enable self-referencing
ConditionGroup.model_rebuild()


# =============================================================================
# ACTION MODELS
# =============================================================================

class OptionLeg(BaseModel):
    """Single leg of an options position."""
    option_type: OptionType
    side: Literal["buy", "sell"]
    quantity: int = Field(ge=1)
    
    # Strike selection
    strike_selection: StrikeSelection = StrikeSelection.OTM_DELTA
    strike_value: Optional[float] = Field(None, description="Delta, %, $, or exact")
    strike_price: Optional[float] = None  # For FIXED selection
    
    # Expiration selection
    expiration_selection: ExpirationSelection = ExpirationSelection.DTE
    expiration_value: Optional[int] = Field(None, ge=0, le=365)
    expiration_date: Optional[str] = None  # For SPECIFIC_DATE
    
    class Config:
        extra = "allow"


class OpenPositionAction(BaseModel):
    """Action to open a new position."""
    type: Literal["open_position"] = "open_position"
    strategy: OptionStrategy
    symbol: str
    quantity: int = Field(ge=1, default=1)
    legs: List[OptionLeg] = Field(default_factory=list)
    
    # Order settings
    order_type: Literal["market", "limit", "smart"] = "smart"
    limit_price: Optional[float] = None
    smart_price_improvement: float = Field(default=0.05, ge=0, le=1)
    
    # Position sizing
    max_allocation_pct: Optional[float] = Field(None, ge=0, le=100)
    max_risk_dollars: Optional[float] = None
    
    @model_validator(mode='after')
    def validate_legs(self) -> 'OpenPositionAction':
        """Ensure strategy has correct number of legs."""
        strategy_legs = {
            OptionStrategy.LONG_CALL: 1,
            OptionStrategy.LONG_PUT: 1,
            OptionStrategy.SHORT_CALL: 1,
            OptionStrategy.SHORT_PUT: 1,
            OptionStrategy.LONG_CALL_SPREAD: 2,
            OptionStrategy.SHORT_CALL_SPREAD: 2,
            OptionStrategy.LONG_PUT_SPREAD: 2,
            OptionStrategy.SHORT_PUT_SPREAD: 2,
            OptionStrategy.IRON_CONDOR: 4,
            OptionStrategy.IRON_BUTTERFLY: 4,
            OptionStrategy.STRADDLE: 2,
            OptionStrategy.STRANGLE: 2,
        }
        expected = strategy_legs.get(self.strategy, 0)
        if expected > 0 and len(self.legs) != expected:
            # Auto-generate legs if not provided
            if len(self.legs) == 0:
                self.legs = self._generate_default_legs()
        return self
    
    def _generate_default_legs(self) -> List[OptionLeg]:
        """Generate default legs for common strategies."""
        if self.strategy == OptionStrategy.SHORT_PUT_SPREAD:
            return [
                OptionLeg(
                    option_type=OptionType.PUT,
                    side="sell",
                    quantity=self.quantity,
                    strike_selection=StrikeSelection.OTM_DELTA,
                    strike_value=0.30,
                    expiration_selection=ExpirationSelection.DTE,
                    expiration_value=30
                ),
                OptionLeg(
                    option_type=OptionType.PUT,
                    side="buy",
                    quantity=self.quantity,
                    strike_selection=StrikeSelection.OTM_DELTA,
                    strike_value=0.15,
                    expiration_selection=ExpirationSelection.DTE,
                    expiration_value=30
                ),
            ]
        elif self.strategy == OptionStrategy.IRON_CONDOR:
            return [
                # Put spread (lower)
                OptionLeg(
                    option_type=OptionType.PUT,
                    side="sell",
                    quantity=self.quantity,
                    strike_selection=StrikeSelection.OTM_DELTA,
                    strike_value=0.20,
                    expiration_selection=ExpirationSelection.DTE,
                    expiration_value=45
                ),
                OptionLeg(
                    option_type=OptionType.PUT,
                    side="buy",
                    quantity=self.quantity,
                    strike_selection=StrikeSelection.OTM_DELTA,
                    strike_value=0.10,
                    expiration_selection=ExpirationSelection.DTE,
                    expiration_value=45
                ),
                # Call spread (upper)
                OptionLeg(
                    option_type=OptionType.CALL,
                    side="sell",
                    quantity=self.quantity,
                    strike_selection=StrikeSelection.OTM_DELTA,
                    strike_value=0.20,
                    expiration_selection=ExpirationSelection.DTE,
                    expiration_value=45
                ),
                OptionLeg(
                    option_type=OptionType.CALL,
                    side="buy",
                    quantity=self.quantity,
                    strike_selection=StrikeSelection.OTM_DELTA,
                    strike_value=0.10,
                    expiration_selection=ExpirationSelection.DTE,
                    expiration_value=45
                ),
            ]
        return []
    
    class Config:
        extra = "allow"


class ClosePositionAction(BaseModel):
    """Action to close an existing position."""
    type: Literal["close_position"] = "close_position"
    position_id: Optional[str] = None  # Specific position
    position_filter: Optional[str] = None  # Filter expression
    close_percent: float = Field(default=100, ge=1, le=100)
    order_type: Literal["market", "limit", "smart"] = "smart"
    
    class Config:
        extra = "allow"


class CloseAllPositionsAction(BaseModel):
    """Action to close all positions."""
    type: Literal["close_all_positions"] = "close_all_positions"
    order_type: Literal["market", "limit", "smart"] = "market"
    
    class Config:
        extra = "allow"


class AlertAction(BaseModel):
    """Action to send an alert/notification."""
    type: Literal["send_alert"] = "send_alert"
    message: str
    channels: List[str] = Field(default_factory=lambda: ["log"])
    
    class Config:
        extra = "allow"


class LogAction(BaseModel):
    """Action to log a message."""
    type: Literal["log"] = "log"
    message: str
    level: str = "info"
    
    class Config:
        extra = "allow"


# Union of all action types
Action = Union[
    OpenPositionAction,
    ClosePositionAction,
    CloseAllPositionsAction,
    AlertAction,
    LogAction,
]


# =============================================================================
# POSITION MANAGEMENT
# =============================================================================

class TakeProfitConfig(BaseModel):
    """Take profit configuration."""
    enabled: bool = True
    percent: float = Field(ge=1, le=100, description="% of max profit")
    order_type: Literal["market", "limit", "smart"] = "smart"


class StopLossConfig(BaseModel):
    """Stop loss configuration."""
    enabled: bool = True
    percent: float = Field(ge=1, le=1000, description="% of credit received")
    order_type: Literal["market", "limit", "smart"] = "market"


class TrailingStopConfig(BaseModel):
    """Trailing stop configuration."""
    enabled: bool = False
    percent: float = Field(default=20, ge=1, le=100)
    activation_profit_pct: float = Field(default=25, ge=0, le=100)


class DTEExitConfig(BaseModel):
    """Exit based on days to expiration."""
    enabled: bool = False
    dte_threshold: int = Field(default=7, ge=0, le=365)


class PositionManagement(BaseModel):
    """
    Position management rules (mirrors OptionsAlpha monitor automations).
    
    These rules are continuously evaluated on open positions.
    """
    take_profit: Optional[TakeProfitConfig] = None
    stop_loss: Optional[StopLossConfig] = None
    trailing_stop: Optional[TrailingStopConfig] = None
    dte_exit: Optional[DTEExitConfig] = None
    
    # Time-based
    max_hold_days: Optional[int] = Field(None, ge=1, le=365)
    
    # Custom conditions for exit
    exit_conditions: Optional[ConditionGroup] = None
    
    class Config:
        extra = "allow"


# =============================================================================
# MAIN RECIPE MODEL
# =============================================================================

class RecipeMetadata(BaseModel):
    """Recipe metadata."""
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    version: str = "1.0.0"
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)


class Recipe(BaseModel):
    """
    The main Recipe model - complete trading strategy configuration.
    
    This is the root object that defines a complete trading bot strategy.
    The RecipeExecutor reads this and executes the defined logic.
    
    Frontend Integration:
    -------------------
    1. Store recipes in database with unique IDs
    2. Expose via REST API: GET/POST/PUT/DELETE /api/recipes
    3. React components render form inputs for each field
    4. JSON is validated server-side before saving
    """
    # Metadata
    id: Optional[str] = Field(default=None, description="Unique identifier")
    metadata: RecipeMetadata
    
    # Bot configuration
    enabled: bool = True
    allocation: float = Field(default=10000, ge=0, description="Capital allocation")
    max_positions: int = Field(default=5, ge=1, le=100)
    
    # Core recipe components
    triggers: List[Trigger] = Field(min_length=1)
    entry_conditions: ConditionGroup = Field(
        description="Conditions that must be true to enter a position"
    )
    actions: List[Action] = Field(min_length=1)
    management: Optional[PositionManagement] = None
    
    # Optional exit conditions (alternative to management)
    exit_conditions: Optional[ConditionGroup] = None
    exit_actions: Optional[List[Action]] = None
    
    class Config:
        extra = "allow"
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Recipe':
        """Load recipe from JSON string."""
        return cls.model_validate_json(json_str)
    
    @classmethod
    def from_file(cls, filepath: str) -> 'Recipe':
        """Load recipe from JSON file."""
        import json
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.model_validate(data)
    
    def to_json(self, indent: int = 2) -> str:
        """Export recipe to JSON string."""
        return self.model_dump_json(indent=indent)
    
    def to_file(self, filepath: str) -> None:
        """Export recipe to JSON file."""
        import json
        with open(filepath, 'w') as f:
            f.write(self.to_json())


# =============================================================================
# SAMPLE RECIPE FACTORY
# =============================================================================

def create_short_put_spread_recipe(
    symbol: str = "SPY",
    rsi_threshold: float = 70,
    take_profit_pct: float = 50,
    stop_loss_pct: float = 200,
    require_market_hours: bool = True,
) -> Recipe:
    """
    Factory function to create a standard Short Put Spread recipe.
    
    Strategy Logic:
    - WHEN: Every 15 minutes during market hours
    - IF: RSI(14) > 70 (overbought = bullish bias = sell puts)
    - THEN: Open short put spread at 0.30 delta, 30 DTE
    - MANAGE: Take profit at 50%, stop loss at 200%
    
    Args:
        symbol: Trading symbol
        rsi_threshold: RSI value to trigger trade (RSI > threshold)
        take_profit_pct: Take profit at this percent of max profit
        stop_loss_pct: Stop loss at this percent of max profit
        require_market_hours: If True, only trade during market hours
    """
    conditions = [
        IndicatorCondition(
            symbol=symbol,
            indicator=Indicator.RSI,
            period=14,
            operator=ComparisonOperator.GT,
            value=rsi_threshold
        ),
    ]
    
    if require_market_hours:
        conditions.append(
            GeneralCondition(
                field="is_market_hours",
                operator=ComparisonOperator.EQ,
                value=True
            )
        )
    
    return Recipe(
        metadata=RecipeMetadata(
            name=f"RSI Short Put Spread - {symbol}",
            description=f"Sell put spreads when {symbol} RSI > {rsi_threshold}",
            tags=["credit_spread", "bullish", "rsi", "mean_reversion"]
        ),
        allocation=10000,
        max_positions=3,
        triggers=[
            Trigger(
                type=TriggerType.INTERVAL,
                config=TriggerConfig(interval_minutes=15)
            )
        ],
        entry_conditions=ConditionGroup(
            operator=ConditionOperator.AND,
            conditions=conditions
        ),
        actions=[
            OpenPositionAction(
                strategy=OptionStrategy.SHORT_PUT_SPREAD,
                symbol=symbol,
                quantity=1,
                legs=[
                    OptionLeg(
                        option_type=OptionType.PUT,
                        side="sell",
                        quantity=1,
                        strike_selection=StrikeSelection.OTM_DELTA,
                        strike_value=0.30,
                        expiration_selection=ExpirationSelection.DTE,
                        expiration_value=30
                    ),
                    OptionLeg(
                        option_type=OptionType.PUT,
                        side="buy",
                        quantity=1,
                        strike_selection=StrikeSelection.OTM_DELTA,
                        strike_value=0.15,
                        expiration_selection=ExpirationSelection.DTE,
                        expiration_value=30
                    ),
                ]
            )
        ],
        management=PositionManagement(
            take_profit=TakeProfitConfig(
                enabled=True,
                percent=take_profit_pct
            ),
            stop_loss=StopLossConfig(
                enabled=True,
                percent=stop_loss_pct
            ),
            dte_exit=DTEExitConfig(
                enabled=True,
                dte_threshold=7
            )
        )
    )


def create_iron_condor_recipe(
    symbol: str = "SPY",
    vix_max: float = 20,
    take_profit_pct: float = 50,
) -> Recipe:
    """
    Factory function to create an Iron Condor recipe.
    
    Strategy Logic:
    - WHEN: Every 30 minutes
    - IF: VIX < 20 (low volatility)
    - THEN: Open iron condor at 0.20 delta wings
    - MANAGE: Take profit at 50%
    """
    return Recipe(
        metadata=RecipeMetadata(
            name=f"Low Vol Iron Condor - {symbol}",
            description=f"Sell iron condors when VIX < {vix_max}",
            tags=["iron_condor", "neutral", "low_vol"]
        ),
        allocation=20000,
        max_positions=2,
        triggers=[
            Trigger(
                type=TriggerType.INTERVAL,
                config=TriggerConfig(interval_minutes=30)
            )
        ],
        entry_conditions=ConditionGroup(
            operator=ConditionOperator.AND,
            conditions=[
                IndicatorCondition(
                    symbol="VIX",
                    indicator=Indicator.VIX,
                    period=1,
                    operator=ComparisonOperator.LT,
                    value=vix_max
                ),
                GeneralCondition(
                    field="is_market_hours",
                    operator=ComparisonOperator.EQ,
                    value=True
                )
            ]
        ),
        actions=[
            OpenPositionAction(
                strategy=OptionStrategy.IRON_CONDOR,
                symbol=symbol,
                quantity=1,
            )
        ],
        management=PositionManagement(
            take_profit=TakeProfitConfig(
                enabled=True,
                percent=take_profit_pct
            ),
            stop_loss=StopLossConfig(
                enabled=True,
                percent=200
            )
        )
    )

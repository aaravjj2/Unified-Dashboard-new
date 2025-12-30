"""
No-Code Options Trading Engine
==============================

A modular system that executes trading strategies defined purely by JSON 
configuration objects (Recipes), similar to OptionsAlpha's bot architecture.

Architecture Overview:
---------------------
┌─────────────────────────────────────────────────────────────────────────┐
│                         RECIPE (JSON Config)                            │
│  ┌─────────┐  ┌────────────┐  ┌──────────┐  ┌────────────────────┐     │
│  │ Trigger │→ │ Conditions │→ │ Actions  │→ │ Position Mgmt      │     │
│  │(When)   │  │ (If/Then)  │  │(Execute) │  │(Monitor/Adjust)    │     │
│  └─────────┘  └────────────┘  └──────────┘  └────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        RECIPE EXECUTOR ENGINE                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ LogicParser │  │ DataHandler │  │ BrokerIface │  │ EventLoop   │    │
│  │(Evaluate)   │  │(Market Data)│  │(Execute)    │  │(Scheduler)  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘

Key Components:
--------------
1. **Recipe Schema** (schema.py): Pydantic models for JSON validation
2. **DataHandler** (data_handler.py): Fetches price/indicator data
3. **BrokerInterface** (broker.py): Abstract broker + PaperBroker
4. **LogicParser** (logic_parser.py): Dynamic condition evaluator
5. **RecipeExecutor** (engine.py): Main orchestration engine

Frontend Integration (React):
----------------------------
This engine exposes a REST API-compatible interface. To connect from React:

1. Recipe CRUD: POST/GET/PUT/DELETE /api/recipes
2. Bot Control: POST /api/bots/{id}/start, /stop, /status
3. WebSocket: ws://host/ws/bot/{id} for real-time updates
4. Position Data: GET /api/positions (open/closed)

Example usage:
    ```python
    from financial_dashboard.engines.options_engine import (
        RecipeExecutor, Recipe, PaperBroker, MockDataHandler
    )
    
    # Load recipe from JSON
    recipe = Recipe.model_validate_json(json_string)
    
    # Create executor with paper trading
    executor = RecipeExecutor(
        recipe=recipe,
        data_handler=MockDataHandler(),
        broker=PaperBroker(initial_capital=10000)
    )
    
    # Run the bot
    executor.start()
    ```

Author: Options Engine Team
Date: December 2025
"""

__version__ = "1.0.0"

# Schema exports
from .schema import (
    Recipe,
    Trigger,
    TriggerType,
    TriggerConfig,
    ConditionGroup,
    ConditionOperator,
    ComparisonOperator,
    ConditionType,
    IndicatorCondition,
    SymbolCondition,
    PositionCondition,
    GeneralCondition,
    OpportunityCondition,
    ActionType,
    OpenPositionAction,
    ClosePositionAction,
    CloseAllPositionsAction,
    AlertAction,
    LogAction,
    OptionStrategy,
    OptionType,
    Indicator,
    OptionLeg,
    StrikeSelection,
    ExpirationSelection,
    TakeProfitConfig,
    StopLossConfig,
    TrailingStopConfig,
    DTEExitConfig,
    PositionManagement,
    create_short_put_spread_recipe,
    create_iron_condor_recipe,
)

# Data handler exports
from .data_handler import (
    DataHandler,
    MockDataHandler,
    LiveDataHandler,
    Quote,
    OHLCV,
    MarketData,
    IndicatorData,
    OptionChain,
)

# Broker exports
from .broker import (
    BrokerInterface,
    PaperBroker,
    Order,
    OrderSide,
    OrderType,
    OrderStatus,
    AssetType,
    OptionLegOrder,
    Position,
    PositionLeg,
    PositionStatus,
)

# Logic parser exports
from .logic_parser import (
    LogicParser,
    EvaluationContext,
    ConditionStringParser,
    evaluate_condition_string,
    create_condition_from_dict,
)

# Engine exports
from .engine import (
    RecipeExecutor,
    BotContext,
    ExecutorState,
    ExecutionEvent,
    ActionExecutor,
    PositionManager,
    AsyncRecipeRunner,
    run_recipe_once,
    backtest_recipe,
)

# Live data handler with Alpaca + yfinance
from .live_data import (
    AlpacaDataHandler,
    create_live_data_handler,
)

# Background scheduler for automated execution
from .scheduler import (
    OptionsScheduler,
    get_options_scheduler,
    create_gld_rsi_bot,
    BotConfig,
    BotStats,
    OptionsBotDB,
)

# Dashboard UI components
from .dashboard_ui import (
    create_options_bots_layout,
    create_options_connection_panel,
    create_options_market_panel,
    create_bot_builder_panel,
    create_active_bots_panel,
    add_options_tab_to_existing,
    get_layout,
)

# Dashboard callbacks
from .callbacks import (
    register_options_callbacks,
)

__all__ = [
    # Schema
    "Recipe",
    "Trigger",
    "TriggerType",
    "TriggerConfig",
    "ConditionGroup",
    "ConditionOperator",
    "ComparisonOperator",
    "ConditionType",
    "IndicatorCondition",
    "SymbolCondition",
    "PositionCondition",
    "GeneralCondition",
    "OpportunityCondition",
    "ActionType",
    "OpenPositionAction",
    "ClosePositionAction",
    "CloseAllPositionsAction",
    "AlertAction",
    "LogAction",
    "OptionStrategy",
    "OptionType",
    "Indicator",
    "OptionLeg",
    "StrikeSelection",
    "ExpirationSelection",
    "TakeProfitConfig",
    "StopLossConfig",
    "TrailingStopConfig",
    "DTEExitConfig",
    "PositionManagement",
    "create_short_put_spread_recipe",
    "create_iron_condor_recipe",
    # Data Handler
    "DataHandler",
    "MockDataHandler",
    "LiveDataHandler",
    "Quote",
    "OHLCV",
    "MarketData",
    "IndicatorData",
    "OptionChain",
    # Broker
    "BrokerInterface",
    "PaperBroker",
    "Order",
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "AssetType",
    "OptionLegOrder",
    "Position",
    "PositionLeg",
    "PositionStatus",
    # Logic Parser
    "LogicParser",
    "EvaluationContext",
    "ConditionStringParser",
    "evaluate_condition_string",
    "create_condition_from_dict",
    # Engine
    "RecipeExecutor",
    "BotContext",
    "ExecutorState",
    "ExecutionEvent",
    "ActionExecutor",
    "PositionManager",
    "AsyncRecipeRunner",
    "run_recipe_once",
    "backtest_recipe",
    # Live Data Handler
    "AlpacaDataHandler",
    "create_live_data_handler",
    # Scheduler
    "OptionsScheduler",
    "get_options_scheduler",
    "create_gld_rsi_bot",
    "BotConfig",
    "BotStats",
    "OptionsBotDB",
    # Dashboard UI
    "create_options_bots_layout",
    "create_options_connection_panel",
    "create_options_market_panel",
    "create_bot_builder_panel",
    "create_active_bots_panel",
    "add_options_tab_to_existing",
    "get_layout",
    # Callbacks
    "register_options_callbacks",
]

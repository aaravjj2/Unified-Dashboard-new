"""
Strategy API Routes

Endpoints for strategy management:
- GET /strategies - List all strategies
- GET /strategies/{id} - Get strategy details
- POST /strategies/{id}/enable - Enable strategy
- POST /strategies/{id}/disable - Disable strategy
- PUT /strategies/{id}/parameters - Update parameters
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class StrategyParameter(BaseModel):
    """Strategy parameter definition"""
    name: str
    value: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: str = ""


class StrategyPerformance(BaseModel):
    """Strategy performance metrics"""
    total_trades: int
    win_rate: float
    avg_profit: float
    avg_loss: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    total_pnl: float


class Strategy(BaseModel):
    """Strategy schema"""
    id: str
    name: str
    description: str
    type: str  # iron_condor, calendar, etc.
    enabled: bool
    parameters: Dict[str, Any]
    performance: Optional[StrategyPerformance] = None
    last_trade: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class StrategyCreate(BaseModel):
    """Create strategy request"""
    name: str
    type: str
    parameters: Dict[str, Any]
    description: str = ""


class StrategyUpdate(BaseModel):
    """Update strategy request"""
    name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


class ParameterUpdate(BaseModel):
    """Parameter update request"""
    parameters: Dict[str, Any]


# =============================================================================
# ROUTES
# =============================================================================

@router.get("/strategies", response_model=List[Strategy])
async def list_strategies():
    """
    List all configured strategies.
    """
    logger.info("strategies_list_requested")
    
    # Mock data
    return [
        Strategy(
            id="strat_1",
            name="Iron Condor 0DTE",
            description="0DTE iron condor on SPY",
            type="iron_condor",
            enabled=True,
            parameters={
                "underlying": "SPY",
                "target_delta": 20,
                "profit_target": 0.50,
                "stop_loss": 2.0,
                "max_positions": 3,
            },
            performance=StrategyPerformance(
                total_trades=150,
                win_rate=0.72,
                avg_profit=85.0,
                avg_loss=-120.0,
                profit_factor=1.8,
                sharpe_ratio=1.5,
                max_drawdown=0.08,
                total_pnl=5250.0,
            ),
            last_trade=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        Strategy(
            id="strat_2",
            name="Calendar Spread",
            description="Calendar spreads on high IV stocks",
            type="calendar",
            enabled=False,
            parameters={
                "underlyings": ["AAPL", "NVDA", "TSLA"],
                "min_iv_rank": 50,
                "profit_target": 0.25,
            },
            performance=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    ]


@router.get("/strategies/{strategy_id}", response_model=Strategy)
async def get_strategy(strategy_id: str):
    """
    Get strategy details by ID.
    """
    logger.info("strategy_requested", strategy_id=strategy_id)
    
    # Mock - replace with actual lookup
    return Strategy(
        id=strategy_id,
        name="Iron Condor 0DTE",
        description="0DTE iron condor on SPY",
        type="iron_condor",
        enabled=True,
        parameters={
            "underlying": "SPY",
            "target_delta": 20,
            "profit_target": 0.50,
            "stop_loss": 2.0,
        },
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@router.post("/strategies", response_model=Strategy)
async def create_strategy(request: StrategyCreate):
    """
    Create a new strategy.
    """
    logger.info("strategy_create_requested", name=request.name, type=request.type)
    
    # Mock - replace with actual creation
    return Strategy(
        id="strat_new",
        name=request.name,
        description=request.description,
        type=request.type,
        enabled=False,
        parameters=request.parameters,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@router.post("/strategies/{strategy_id}/enable")
async def enable_strategy(strategy_id: str):
    """
    Enable a strategy.
    """
    logger.info("strategy_enable_requested", strategy_id=strategy_id)
    
    # Mock - replace with actual enable
    return {"status": "enabled", "strategy_id": strategy_id}


@router.post("/strategies/{strategy_id}/disable")
async def disable_strategy(strategy_id: str):
    """
    Disable a strategy.
    """
    logger.info("strategy_disable_requested", strategy_id=strategy_id)
    
    # Mock - replace with actual disable
    return {"status": "disabled", "strategy_id": strategy_id}


@router.put("/strategies/{strategy_id}", response_model=Strategy)
async def update_strategy(strategy_id: str, request: StrategyUpdate):
    """
    Update strategy configuration.
    """
    logger.info("strategy_update_requested", strategy_id=strategy_id)
    
    # Mock - replace with actual update
    return Strategy(
        id=strategy_id,
        name=request.name or "Iron Condor 0DTE",
        description=request.description or "",
        type="iron_condor",
        enabled=True,
        parameters=request.parameters or {},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@router.put("/strategies/{strategy_id}/parameters")
async def update_strategy_parameters(strategy_id: str, request: ParameterUpdate):
    """
    Update strategy parameters.
    """
    logger.info(
        "strategy_parameters_update_requested",
        strategy_id=strategy_id,
        parameters=request.parameters,
    )
    
    return {
        "status": "updated",
        "strategy_id": strategy_id,
        "parameters": request.parameters,
    }


@router.delete("/strategies/{strategy_id}")
async def delete_strategy(strategy_id: str):
    """
    Delete a strategy.
    """
    logger.info("strategy_delete_requested", strategy_id=strategy_id)
    
    return {"status": "deleted", "strategy_id": strategy_id}


@router.get("/strategies/{strategy_id}/performance", response_model=StrategyPerformance)
async def get_strategy_performance(strategy_id: str):
    """
    Get strategy performance metrics.
    """
    logger.info("strategy_performance_requested", strategy_id=strategy_id)
    
    return StrategyPerformance(
        total_trades=150,
        win_rate=0.72,
        avg_profit=85.0,
        avg_loss=-120.0,
        profit_factor=1.8,
        sharpe_ratio=1.5,
        max_drawdown=0.08,
        total_pnl=5250.0,
    )


@router.get("/strategies/types")
async def get_strategy_types():
    """
    Get available strategy types and their parameter definitions.
    """
    return {
        "iron_condor": {
            "name": "Iron Condor",
            "description": "Sell OTM put spread and call spread",
            "parameters": [
                {"name": "target_delta", "type": "int", "min": 5, "max": 30, "default": 20},
                {"name": "profit_target", "type": "float", "min": 0.1, "max": 1.0, "default": 0.5},
                {"name": "stop_loss", "type": "float", "min": 1.0, "max": 5.0, "default": 2.0},
            ],
        },
        "calendar": {
            "name": "Calendar Spread",
            "description": "Long far month, short near month",
            "parameters": [
                {"name": "min_iv_rank", "type": "int", "min": 0, "max": 100, "default": 50},
                {"name": "profit_target", "type": "float", "min": 0.1, "max": 1.0, "default": 0.25},
            ],
        },
        "straddle": {
            "name": "Straddle",
            "description": "ATM call and put",
            "parameters": [
                {"name": "profit_target", "type": "float", "min": 0.1, "max": 2.0, "default": 0.5},
            ],
        },
    }

"""
Portfolio API Routes

Endpoints for portfolio management:
- GET /portfolio - Get current portfolio state
- GET /portfolio/positions - Get all positions
- GET /portfolio/positions/{id} - Get specific position
- GET /portfolio/greeks - Get aggregate Greeks
- GET /portfolio/history - Get portfolio value history
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class Greeks(BaseModel):
    """Greeks schema"""
    delta: float = Field(..., description="Position delta")
    gamma: float = Field(..., description="Position gamma")
    theta: float = Field(..., description="Position theta (per day)")
    vega: float = Field(..., description="Position vega")
    rho: float = Field(0, description="Position rho")


class Position(BaseModel):
    """Position schema"""
    id: str = Field(..., description="Position ID")
    contract: str = Field(..., description="Contract symbol")
    underlying: str = Field(..., description="Underlying symbol")
    quantity: int = Field(..., description="Position quantity")
    avg_entry_price: float = Field(..., description="Average entry price")
    current_price: float = Field(..., description="Current market price")
    market_value: float = Field(..., description="Current market value")
    unrealized_pnl: float = Field(..., description="Unrealized P&L")
    unrealized_pnl_pct: float = Field(..., description="Unrealized P&L percentage")
    realized_pnl: float = Field(0, description="Realized P&L")
    side: str = Field(..., description="Position side (long/short)")
    greeks: Optional[Greeks] = Field(None, description="Position Greeks")
    opened_at: datetime = Field(..., description="Position open timestamp")


class PortfolioSummary(BaseModel):
    """Portfolio summary schema"""
    total_value: float = Field(..., description="Total portfolio value")
    cash: float = Field(..., description="Cash balance")
    buying_power: float = Field(..., description="Available buying power")
    options_value: float = Field(..., description="Total options value")
    day_pnl: float = Field(..., description="Day P&L")
    day_pnl_pct: float = Field(..., description="Day P&L percentage")
    total_pnl: float = Field(..., description="Total P&L")
    total_pnl_pct: float = Field(..., description="Total P&L percentage")
    position_count: int = Field(..., description="Number of positions")


class PortfolioGreeks(BaseModel):
    """Aggregate portfolio Greeks"""
    total_delta: float = Field(..., description="Portfolio delta")
    total_gamma: float = Field(..., description="Portfolio gamma")
    total_theta: float = Field(..., description="Portfolio theta (per day)")
    total_vega: float = Field(..., description="Portfolio vega")
    dollar_delta: float = Field(..., description="Dollar delta exposure")
    dollar_gamma: float = Field(..., description="Dollar gamma exposure")
    dollar_theta: float = Field(..., description="Dollar theta (per day)")
    dollar_vega: float = Field(..., description="Dollar vega per 1% IV")
    beta_weighted_delta: float = Field(0, description="Beta-weighted delta")


class PortfolioHistoryPoint(BaseModel):
    """Single point in portfolio history"""
    timestamp: datetime
    value: float
    pnl: float
    pnl_pct: float


class PortfolioResponse(BaseModel):
    """Full portfolio response"""
    summary: PortfolioSummary
    greeks: PortfolioGreeks
    positions: List[Position]
    last_updated: datetime


# =============================================================================
# ROUTES
# =============================================================================

@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio():
    """
    Get current portfolio state.
    
    Returns complete portfolio information including:
    - Account summary (value, cash, P&L)
    - Aggregate Greeks
    - All positions with Greeks
    """
    logger.info("portfolio_requested")
    
    # Mock data for now - replace with actual implementation
    return PortfolioResponse(
        summary=PortfolioSummary(
            total_value=100000.0,
            cash=50000.0,
            buying_power=150000.0,
            options_value=50000.0,
            day_pnl=250.0,
            day_pnl_pct=0.25,
            total_pnl=5000.0,
            total_pnl_pct=5.0,
            position_count=3,
        ),
        greeks=PortfolioGreeks(
            total_delta=15.5,
            total_gamma=0.02,
            total_theta=-45.0,
            total_vega=120.0,
            dollar_delta=7750.0,
            dollar_gamma=100.0,
            dollar_theta=-45.0,
            dollar_vega=1200.0,
            beta_weighted_delta=12.5,
        ),
        positions=[
            Position(
                id="pos_1",
                contract="SPY240119C00480000",
                underlying="SPY",
                quantity=10,
                avg_entry_price=5.25,
                current_price=5.50,
                market_value=5500.0,
                unrealized_pnl=250.0,
                unrealized_pnl_pct=4.76,
                realized_pnl=0,
                side="long",
                greeks=Greeks(delta=0.45, gamma=0.02, theta=-0.05, vega=0.15, rho=0.01),
                opened_at=datetime.now(timezone.utc),
            ),
        ],
        last_updated=datetime.now(timezone.utc),
    )


@router.get("/portfolio/positions", response_model=List[Position])
async def get_positions(
    underlying: Optional[str] = Query(None, description="Filter by underlying"),
    side: Optional[str] = Query(None, description="Filter by side (long/short)"),
):
    """
    Get all positions.
    
    Optional filters:
    - underlying: Filter by underlying symbol
    - side: Filter by position side (long/short)
    """
    logger.info("positions_requested", underlying=underlying, side=side)
    
    # Mock data
    positions = [
        Position(
            id="pos_1",
            contract="SPY240119C00480000",
            underlying="SPY",
            quantity=10,
            avg_entry_price=5.25,
            current_price=5.50,
            market_value=5500.0,
            unrealized_pnl=250.0,
            unrealized_pnl_pct=4.76,
            realized_pnl=0,
            side="long",
            greeks=Greeks(delta=0.45, gamma=0.02, theta=-0.05, vega=0.15, rho=0.01),
            opened_at=datetime.now(timezone.utc),
        ),
    ]
    
    # Apply filters
    if underlying:
        positions = [p for p in positions if p.underlying == underlying]
    if side:
        positions = [p for p in positions if p.side == side]
    
    return positions


@router.get("/portfolio/positions/{position_id}", response_model=Position)
async def get_position(position_id: str):
    """
    Get specific position by ID.
    """
    logger.info("position_requested", position_id=position_id)
    
    # Mock - replace with actual lookup
    return Position(
        id=position_id,
        contract="SPY240119C00480000",
        underlying="SPY",
        quantity=10,
        avg_entry_price=5.25,
        current_price=5.50,
        market_value=5500.0,
        unrealized_pnl=250.0,
        unrealized_pnl_pct=4.76,
        realized_pnl=0,
        side="long",
        greeks=Greeks(delta=0.45, gamma=0.02, theta=-0.05, vega=0.15, rho=0.01),
        opened_at=datetime.now(timezone.utc),
    )


@router.get("/portfolio/greeks", response_model=PortfolioGreeks)
async def get_portfolio_greeks():
    """
    Get aggregate portfolio Greeks.
    """
    logger.info("portfolio_greeks_requested")
    
    return PortfolioGreeks(
        total_delta=15.5,
        total_gamma=0.02,
        total_theta=-45.0,
        total_vega=120.0,
        dollar_delta=7750.0,
        dollar_gamma=100.0,
        dollar_theta=-45.0,
        dollar_vega=1200.0,
        beta_weighted_delta=12.5,
    )


@router.get("/portfolio/history", response_model=List[PortfolioHistoryPoint])
async def get_portfolio_history(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    interval: str = Query("1d", description="Data interval (1h, 1d, 1w)"),
):
    """
    Get portfolio value history.
    """
    logger.info(
        "portfolio_history_requested",
        start_date=start_date,
        end_date=end_date,
        interval=interval,
    )
    
    # Mock data
    return [
        PortfolioHistoryPoint(
            timestamp=datetime.now(timezone.utc),
            value=100000.0,
            pnl=0,
            pnl_pct=0,
        ),
    ]

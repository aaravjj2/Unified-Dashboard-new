"""
Analytics API Routes

Endpoints for trading analytics:
- GET /analytics/performance - Trading performance metrics
- GET /analytics/pnl - P&L breakdown
- GET /analytics/attribution - P&L attribution analysis
- GET /analytics/strategies - Strategy performance comparison
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class PerformanceMetrics(BaseModel):
    """Overall performance metrics"""
    total_return: float = Field(..., description="Total return percentage")
    annualized_return: float = Field(..., description="Annualized return")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    sortino_ratio: float = Field(..., description="Sortino ratio")
    max_drawdown: float = Field(..., description="Maximum drawdown")
    win_rate: float = Field(..., description="Win rate percentage")
    profit_factor: float = Field(..., description="Gross profit / gross loss")
    avg_win: float = Field(..., description="Average winning trade")
    avg_loss: float = Field(..., description="Average losing trade")
    total_trades: int = Field(..., description="Total number of trades")
    winning_trades: int = Field(..., description="Number of winning trades")
    losing_trades: int = Field(..., description="Number of losing trades")


class DailyPnL(BaseModel):
    """Daily P&L record"""
    date: str
    pnl: float
    cumulative_pnl: float
    realized_pnl: float
    unrealized_pnl: float


class PnLBreakdown(BaseModel):
    """P&L breakdown by category"""
    total_pnl: float
    realized_pnl: float
    unrealized_pnl: float
    commissions: float
    fees: float
    net_pnl: float
    by_underlying: Dict[str, float]
    by_strategy: Dict[str, float]
    by_type: Dict[str, float]  # call/put
    daily_pnl: List[DailyPnL]


class AttributionItem(BaseModel):
    """P&L attribution item"""
    component: str
    contribution: float
    percentage: float
    description: str


class PnLAttribution(BaseModel):
    """P&L attribution analysis"""
    total_pnl: float
    delta_pnl: float
    gamma_pnl: float
    theta_pnl: float
    vega_pnl: float
    rho_pnl: float
    residual_pnl: float
    items: List[AttributionItem]


class StrategyMetrics(BaseModel):
    """Strategy performance metrics"""
    strategy_id: str
    strategy_name: str
    total_pnl: float
    return_pct: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    avg_holding_period: float  # days
    max_drawdown: float
    status: str


class DrawdownPeriod(BaseModel):
    """Drawdown period info"""
    start_date: str
    end_date: Optional[str]
    peak_value: float
    trough_value: float
    drawdown_pct: float
    recovery_date: Optional[str]


class RiskMetrics(BaseModel):
    """Risk analytics"""
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    beta: float
    correlation_spy: float
    volatility: float
    downside_volatility: float


# =============================================================================
# ROUTES
# =============================================================================

@router.get("/analytics/performance", response_model=PerformanceMetrics)
async def get_performance_metrics(
    period: str = Query("30d", description="Period (7d, 30d, 90d, ytd, all)"),
):
    """
    Get overall trading performance metrics.
    """
    logger.info("performance_metrics_requested", period=period)
    
    return PerformanceMetrics(
        total_return=15.8,
        annualized_return=42.5,
        sharpe_ratio=1.85,
        sortino_ratio=2.45,
        max_drawdown=-8.2,
        win_rate=68.5,
        profit_factor=2.15,
        avg_win=125.0,
        avg_loss=-58.0,
        total_trades=127,
        winning_trades=87,
        losing_trades=40,
    )


@router.get("/analytics/pnl", response_model=PnLBreakdown)
async def get_pnl_breakdown(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
):
    """
    Get P&L breakdown by category.
    """
    logger.info("pnl_breakdown_requested", start_date=start_date, end_date=end_date)
    
    # Generate mock daily P&L
    daily = []
    cumulative = 0
    base_date = datetime.now(timezone.utc) - timedelta(days=30)
    for i in range(30):
        day_pnl = (i % 5 - 2) * 50 + 25
        cumulative += day_pnl
        daily.append(DailyPnL(
            date=(base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
            pnl=day_pnl,
            cumulative_pnl=cumulative,
            realized_pnl=day_pnl * 0.7,
            unrealized_pnl=day_pnl * 0.3,
        ))
    
    return PnLBreakdown(
        total_pnl=15250.0,
        realized_pnl=12800.0,
        unrealized_pnl=2450.0,
        commissions=425.0,
        fees=38.50,
        net_pnl=14786.50,
        by_underlying={
            "SPY": 8500.0,
            "QQQ": 4200.0,
            "IWM": 2550.0,
        },
        by_strategy={
            "iron_condor": 5200.0,
            "put_credit_spread": 4800.0,
            "covered_call": 3500.0,
            "wheel": 1750.0,
        },
        by_type={
            "call": 6800.0,
            "put": 8450.0,
        },
        daily_pnl=daily,
    )


@router.get("/analytics/attribution", response_model=PnLAttribution)
async def get_pnl_attribution(
    period: str = Query("30d", description="Period for attribution"),
):
    """
    Get P&L attribution by Greeks.
    """
    logger.info("pnl_attribution_requested", period=period)
    
    total_pnl = 15250.0
    
    return PnLAttribution(
        total_pnl=total_pnl,
        delta_pnl=3200.0,
        gamma_pnl=850.0,
        theta_pnl=9500.0,
        vega_pnl=1200.0,
        rho_pnl=-150.0,
        residual_pnl=650.0,
        items=[
            AttributionItem(
                component="Theta",
                contribution=9500.0,
                percentage=62.3,
                description="Time decay income from premium selling",
            ),
            AttributionItem(
                component="Delta",
                contribution=3200.0,
                percentage=21.0,
                description="Directional gains from price movement",
            ),
            AttributionItem(
                component="Vega",
                contribution=1200.0,
                percentage=7.9,
                description="Volatility contraction gains",
            ),
            AttributionItem(
                component="Gamma",
                contribution=850.0,
                percentage=5.6,
                description="Convexity gains",
            ),
            AttributionItem(
                component="Residual",
                contribution=650.0,
                percentage=4.3,
                description="Unexplained / other factors",
            ),
            AttributionItem(
                component="Rho",
                contribution=-150.0,
                percentage=-1.0,
                description="Interest rate impact",
            ),
        ],
    )


@router.get("/analytics/strategies", response_model=List[StrategyMetrics])
async def get_strategy_performance():
    """
    Get performance comparison across strategies.
    """
    logger.info("strategy_performance_requested")
    
    return [
        StrategyMetrics(
            strategy_id="strat_1",
            strategy_name="Iron Condor - SPY",
            total_pnl=5200.0,
            return_pct=18.5,
            sharpe_ratio=2.1,
            win_rate=72.0,
            total_trades=45,
            avg_holding_period=12.5,
            max_drawdown=-4.2,
            status="active",
        ),
        StrategyMetrics(
            strategy_id="strat_2",
            strategy_name="Put Credit Spread - QQQ",
            total_pnl=4800.0,
            return_pct=22.3,
            sharpe_ratio=1.9,
            win_rate=68.0,
            total_trades=38,
            avg_holding_period=8.2,
            max_drawdown=-5.8,
            status="active",
        ),
        StrategyMetrics(
            strategy_id="strat_3",
            strategy_name="Covered Call - IWM",
            total_pnl=3500.0,
            return_pct=12.8,
            sharpe_ratio=1.5,
            win_rate=82.0,
            total_trades=24,
            avg_holding_period=21.0,
            max_drawdown=-3.5,
            status="active",
        ),
        StrategyMetrics(
            strategy_id="strat_4",
            strategy_name="Wheel - SPY",
            total_pnl=1750.0,
            return_pct=8.5,
            sharpe_ratio=1.2,
            win_rate=65.0,
            total_trades=20,
            avg_holding_period=28.0,
            max_drawdown=-6.2,
            status="paused",
        ),
    ]


@router.get("/analytics/drawdowns", response_model=List[DrawdownPeriod])
async def get_drawdown_analysis():
    """
    Get drawdown periods analysis.
    """
    logger.info("drawdown_analysis_requested")
    
    return [
        DrawdownPeriod(
            start_date="2024-01-15",
            end_date="2024-01-22",
            peak_value=105000.0,
            trough_value=96400.0,
            drawdown_pct=-8.2,
            recovery_date="2024-01-29",
        ),
        DrawdownPeriod(
            start_date="2024-02-05",
            end_date="2024-02-08",
            peak_value=112000.0,
            trough_value=107500.0,
            drawdown_pct=-4.0,
            recovery_date="2024-02-12",
        ),
    ]


@router.get("/analytics/risk", response_model=RiskMetrics)
async def get_risk_analytics(
    period: str = Query("30d", description="Period for risk calculation"),
):
    """
    Get risk analytics.
    """
    logger.info("risk_analytics_requested", period=period)
    
    return RiskMetrics(
        var_95=2500.0,
        var_99=4200.0,
        cvar_95=3100.0,
        cvar_99=5500.0,
        beta=0.35,
        correlation_spy=0.42,
        volatility=12.5,
        downside_volatility=8.2,
    )


@router.get("/analytics/trade-analysis")
async def get_trade_analysis(
    strategy_id: Optional[str] = Query(None, description="Filter by strategy"),
):
    """
    Get detailed trade analysis.
    """
    logger.info("trade_analysis_requested", strategy_id=strategy_id)
    
    return {
        "total_trades": 127,
        "avg_holding_period_days": 14.2,
        "avg_contracts_per_trade": 5.8,
        "avg_premium_collected": 285.0,
        "avg_premium_paid": 125.0,
        "by_day_of_week": {
            "Monday": {"trades": 24, "win_rate": 71.0},
            "Tuesday": {"trades": 28, "win_rate": 68.0},
            "Wednesday": {"trades": 32, "win_rate": 72.0},
            "Thursday": {"trades": 25, "win_rate": 64.0},
            "Friday": {"trades": 18, "win_rate": 67.0},
        },
        "by_month": {
            "January": {"trades": 35, "pnl": 4200.0},
            "February": {"trades": 42, "pnl": 5800.0},
            "March": {"trades": 50, "pnl": 5250.0},
        },
        "exit_reasons": {
            "profit_target": 52,
            "stop_loss": 28,
            "expiration": 35,
            "manual": 12,
        },
    }


@router.get("/analytics/greeks-history")
async def get_greeks_history(
    days: int = Query(30, description="Number of days"),
):
    """
    Get historical portfolio Greeks.
    """
    logger.info("greeks_history_requested", days=days)
    
    history = []
    base_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    for i in range(days):
        history.append({
            "date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
            "delta": -0.12 + (i % 10) * 0.01,
            "gamma": 0.03 - (i % 5) * 0.002,
            "theta": 125.0 + (i % 7) * 5,
            "vega": -450.0 + (i % 8) * 20,
        })
    
    return {"history": history}

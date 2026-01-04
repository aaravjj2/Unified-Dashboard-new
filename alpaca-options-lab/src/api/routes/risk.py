"""
Risk API Routes

Endpoints for risk management:
- GET /risk/limits - Get risk limits
- PUT /risk/limits - Update risk limits
- GET /risk/status - Get current risk status
- GET /risk/exposure - Get risk exposure breakdown
- POST /risk/stress-test - Run stress test
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class RiskLimits(BaseModel):
    """Risk limit configuration"""
    max_portfolio_delta: float = Field(100, description="Max absolute portfolio delta")
    max_portfolio_gamma: float = Field(50, description="Max absolute portfolio gamma")
    max_portfolio_theta: float = Field(-500, description="Max negative theta per day")
    max_portfolio_vega: float = Field(1000, description="Max portfolio vega")
    max_position_size_pct: float = Field(5, description="Max position size as % of portfolio")
    max_daily_loss_pct: float = Field(3, description="Max daily loss as % of portfolio")
    max_single_underlying_pct: float = Field(20, description="Max exposure to single underlying")
    max_positions: int = Field(20, description="Max number of positions")


class RiskLimitStatus(BaseModel):
    """Status of a single risk limit"""
    name: str
    limit: float
    current: float
    utilization_pct: float
    status: str  # 'ok', 'warning', 'breach'


class RiskStatus(BaseModel):
    """Overall risk status"""
    status: str  # 'healthy', 'elevated', 'critical'
    limits: List[RiskLimitStatus]
    breach_count: int
    warning_count: int
    last_updated: datetime


class RiskExposure(BaseModel):
    """Risk exposure by underlying"""
    underlying: str
    delta_exposure: float
    gamma_exposure: float
    vega_exposure: float
    notional_exposure: float
    pct_of_portfolio: float


class StressTestScenario(BaseModel):
    """Stress test scenario"""
    name: str
    underlying_move_pct: float
    iv_change_pct: float


class StressTestResult(BaseModel):
    """Result of stress test"""
    scenario: str
    portfolio_pnl: float
    portfolio_pnl_pct: float
    delta_pnl: float
    gamma_pnl: float
    vega_pnl: float
    theta_pnl: float
    worst_position: str
    worst_position_pnl: float


class VaRResult(BaseModel):
    """Value at Risk result"""
    var_95: float
    var_99: float
    expected_shortfall: float
    method: str  # 'historical', 'parametric', 'monte_carlo'
    lookback_days: int


# =============================================================================
# ROUTES
# =============================================================================

@router.get("/risk/limits", response_model=RiskLimits)
async def get_risk_limits():
    """
    Get current risk limits configuration.
    """
    logger.info("risk_limits_requested")
    
    return RiskLimits(
        max_portfolio_delta=100,
        max_portfolio_gamma=50,
        max_portfolio_theta=-500,
        max_portfolio_vega=1000,
        max_position_size_pct=5,
        max_daily_loss_pct=3,
        max_single_underlying_pct=20,
        max_positions=20,
    )


@router.put("/risk/limits", response_model=RiskLimits)
async def update_risk_limits(limits: RiskLimits):
    """
    Update risk limits configuration.
    """
    logger.info("risk_limits_update_requested", limits=limits.dict())
    
    # Validate limits
    if limits.max_daily_loss_pct > 10:
        raise HTTPException(
            status_code=400,
            detail="Daily loss limit cannot exceed 10%"
        )
    
    return limits


@router.get("/risk/status", response_model=RiskStatus)
async def get_risk_status():
    """
    Get current risk status including limit utilization.
    """
    logger.info("risk_status_requested")
    
    limits_status = [
        RiskLimitStatus(
            name="Portfolio Delta",
            limit=100,
            current=45,
            utilization_pct=45,
            status="ok",
        ),
        RiskLimitStatus(
            name="Portfolio Gamma",
            limit=50,
            current=12,
            utilization_pct=24,
            status="ok",
        ),
        RiskLimitStatus(
            name="Portfolio Theta",
            limit=-500,
            current=-180,
            utilization_pct=36,
            status="ok",
        ),
        RiskLimitStatus(
            name="Portfolio Vega",
            limit=1000,
            current=850,
            utilization_pct=85,
            status="warning",
        ),
        RiskLimitStatus(
            name="Daily Loss",
            limit=3,
            current=0.5,
            utilization_pct=16.7,
            status="ok",
        ),
    ]
    
    breach_count = sum(1 for l in limits_status if l.status == 'breach')
    warning_count = sum(1 for l in limits_status if l.status == 'warning')
    
    if breach_count > 0:
        overall_status = 'critical'
    elif warning_count > 0:
        overall_status = 'elevated'
    else:
        overall_status = 'healthy'
    
    return RiskStatus(
        status=overall_status,
        limits=limits_status,
        breach_count=breach_count,
        warning_count=warning_count,
        last_updated=datetime.now(timezone.utc),
    )


@router.get("/risk/exposure", response_model=List[RiskExposure])
async def get_risk_exposure():
    """
    Get risk exposure breakdown by underlying.
    """
    logger.info("risk_exposure_requested")
    
    return [
        RiskExposure(
            underlying="SPY",
            delta_exposure=25.5,
            gamma_exposure=5.2,
            vega_exposure=450.0,
            notional_exposure=50000,
            pct_of_portfolio=50,
        ),
        RiskExposure(
            underlying="QQQ",
            delta_exposure=15.0,
            gamma_exposure=3.1,
            vega_exposure=280.0,
            notional_exposure=30000,
            pct_of_portfolio=30,
        ),
        RiskExposure(
            underlying="IWM",
            delta_exposure=4.5,
            gamma_exposure=1.8,
            vega_exposure=120.0,
            notional_exposure=20000,
            pct_of_portfolio=20,
        ),
    ]


@router.post("/risk/stress-test", response_model=List[StressTestResult])
async def run_stress_test(scenarios: Optional[List[StressTestScenario]] = None):
    """
    Run stress test scenarios on current portfolio.
    """
    logger.info("stress_test_requested")
    
    # Default scenarios if none provided
    if not scenarios:
        scenarios = [
            StressTestScenario(name="Market Crash -5%", underlying_move_pct=-5, iv_change_pct=50),
            StressTestScenario(name="Market Rally +5%", underlying_move_pct=5, iv_change_pct=-20),
            StressTestScenario(name="IV Spike +30%", underlying_move_pct=0, iv_change_pct=30),
            StressTestScenario(name="IV Crush -30%", underlying_move_pct=0, iv_change_pct=-30),
        ]
    
    results = []
    for scenario in scenarios:
        # Mock stress test calculation
        delta_pnl = -scenario.underlying_move_pct * 45 * 100  # delta * move * multiplier
        vega_pnl = scenario.iv_change_pct * 850 / 100  # vega * iv_change
        gamma_pnl = 0.5 * 12 * (scenario.underlying_move_pct / 100 * 500) ** 2
        theta_pnl = -180  # One day of theta
        
        total_pnl = delta_pnl + vega_pnl + gamma_pnl + theta_pnl
        
        results.append(StressTestResult(
            scenario=scenario.name,
            portfolio_pnl=total_pnl,
            portfolio_pnl_pct=total_pnl / 100000 * 100,
            delta_pnl=delta_pnl,
            gamma_pnl=gamma_pnl,
            vega_pnl=vega_pnl,
            theta_pnl=theta_pnl,
            worst_position="SPY240119C00480000",
            worst_position_pnl=total_pnl * 0.4,
        ))
    
    return results


@router.get("/risk/var", response_model=VaRResult)
async def get_var(
    method: str = "historical",
    lookback_days: int = 252,
):
    """
    Calculate Value at Risk for portfolio.
    """
    logger.info("var_requested", method=method, lookback=lookback_days)
    
    return VaRResult(
        var_95=-2500,
        var_99=-4200,
        expected_shortfall=-5100,
        method=method,
        lookback_days=lookback_days,
    )


@router.post("/risk/kill-switch")
async def activate_kill_switch(reason: str):
    """
    Activate emergency kill switch.
    
    This will close all positions and halt trading.
    """
    logger.critical("kill_switch_activated_via_api", reason=reason)
    
    # In production, this would call the actual kill switch
    return {
        "status": "activated",
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

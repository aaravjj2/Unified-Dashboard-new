"""
Portfolio Dashboard Service - Independent Backend
==================================================
FastAPI service that encapsulates all Portfolio tab logic and data serving.
Exposes REST endpoints for the main dashboard to consume.

Endpoints:
- GET /portfolio/summary - Portfolio summary metrics
- GET /portfolio/positions - Current positions with details
- GET /portfolio/analytics - Advanced analytics data
- GET /portfolio/orders - Order history
- POST /portfolio/refresh - Force data refresh
- GET /health - Service health check

Port: 8057
"""

import os
try:
    # Use central config helper when available
    from config import get_cfg as get_env
except Exception:
    # fallback to os.getenv
    import os as _os
    def get_env(k, d=None):
        return _os.getenv(k, d)
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import Alpaca client
ALPACA_AVAILABLE = False
try:
    from alpaca.trading.client import TradingClient
    from alpaca.data.historical import StockHistoricalDataClient
    ALPACA_AVAILABLE = True
    logger.info("✓ Alpaca SDK available")
except Exception as e:
    logger.warning(f"Alpaca not available: {e}")

# Initialize FastAPI app
app = FastAPI(
    title="Portfolio Dashboard Service",
    description="Backend service for Portfolio tab data and analytics",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response models
class PortfolioSummary(BaseModel):
    """Portfolio summary metrics."""
    portfolio_value: float
    equity: float
    cash: float
    buying_power: float
    total_positions: int
    total_cost_basis: float
    total_unrealized_pl: float
    total_unrealized_pl_pct: float
    timestamp: str

class Position(BaseModel):
    """Individual position details."""
    symbol: str
    qty: float
    avg_entry_price: float
    current_price: float
    cost_basis: float
    market_value: float
    unrealized_pl: float
    unrealized_plpc: float
    side: str

class PortfolioPositions(BaseModel):
    """All portfolio positions."""
    positions: List[Position]
    summary: PortfolioSummary
    timestamp: str

class OrderHistory(BaseModel):
    """Order history response."""
    orders: List[Dict[str, Any]]
    total_count: int
    timestamp: str

class AnalyticsData(BaseModel):
    """Portfolio analytics data."""
    metrics: Dict[str, Any]
    charts: Dict[str, Any]
    timestamp: str


def get_alpaca_client():
    """Get Alpaca trading client from environment."""
    if not ALPACA_AVAILABLE:
        return None
    
    key = get_env('ALPACA_API_KEY') or get_env('APCA_API_KEY_ID') or get_env('APCA_API_KEY')
    secret = get_env('ALPACA_API_SECRET') or get_env('APCA_API_SECRET_KEY') or get_env('APCA_API_SECRET')
    if not key or not secret:
        logger.warning("Alpaca credentials not found in environment")
        return None
    
    # Default to paper trading
    paper = True
    return TradingClient(key, secret, paper=paper)


@app.get("/portfolio/summary", response_model=PortfolioSummary)
async def get_portfolio_summary():
    """
    Get portfolio summary metrics.
    Returns current account value, P/L, positions count, etc.
    """
    try:
        client = get_alpaca_client()
        if not client:
            raise HTTPException(
                status_code=503,
                detail="Alpaca client not available. Check API credentials."
            )
        
        account = client.get_account()
        positions = client.get_all_positions()
        
        # Calculate totals
        total_cost_basis = sum(float(pos.cost_basis) for pos in positions)
        total_unrealized_pl = sum(float(pos.unrealized_pl) for pos in positions)
        total_unrealized_pl_pct = (
            (total_unrealized_pl / total_cost_basis * 100) 
            if total_cost_basis > 0 else 0
        )
        
        return PortfolioSummary(
            portfolio_value=float(account.portfolio_value),
            equity=float(account.equity),
            cash=float(account.cash),
            buying_power=float(account.buying_power),
            total_positions=len(positions),
            total_cost_basis=round(total_cost_basis, 2),
            total_unrealized_pl=round(total_unrealized_pl, 2),
            total_unrealized_pl_pct=round(total_unrealized_pl_pct, 2),
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching portfolio summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/portfolio/positions", response_model=PortfolioPositions)
async def get_portfolio_positions():
    """
    Get all portfolio positions with details.
    """
    try:
        client = get_alpaca_client()
        if not client:
            raise HTTPException(
                status_code=503,
                detail="Alpaca client not available. Check API credentials."
            )
        
        account = client.get_account()
        positions = client.get_all_positions()
        
        # Build positions list
        positions_list = []
        total_cost_basis = 0.0
        total_unrealized_pl = 0.0
        
        for pos in positions:
            cost_basis = float(pos.cost_basis)
            market_value = float(pos.market_value)
            unrealized_pl = market_value - cost_basis
            
            total_cost_basis += cost_basis
            total_unrealized_pl += unrealized_pl
            
            positions_list.append(Position(
                symbol=pos.symbol,
                qty=float(pos.qty),
                avg_entry_price=float(pos.avg_entry_price),
                current_price=float(pos.current_price),
                cost_basis=cost_basis,
                market_value=market_value,
                unrealized_pl=unrealized_pl,
                unrealized_plpc=float(pos.unrealized_plpc) * 100,
                side=pos.side
            ))
        
        summary = PortfolioSummary(
            portfolio_value=float(account.portfolio_value),
            equity=float(account.equity),
            cash=float(account.cash),
            buying_power=float(account.buying_power),
            total_positions=len(positions),
            total_cost_basis=round(total_cost_basis, 2),
            total_unrealized_pl=round(total_unrealized_pl, 2),
            total_unrealized_pl_pct=round(
                (total_unrealized_pl / total_cost_basis * 100) if total_cost_basis > 0 else 0,
                2
            ),
            timestamp=datetime.now().isoformat()
        )
        
        return PortfolioPositions(
            positions=positions_list,
            summary=summary,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching positions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/portfolio/orders", response_model=OrderHistory)
async def get_order_history(
    limit: int = Query(default=50, ge=1, le=500),
    status: Optional[str] = Query(default=None)
):
    """
    Get order history.
    
    Args:
        limit: Maximum number of orders to return
        status: Filter by order status (filled, canceled, etc.)
    """
    try:
        client = get_alpaca_client()
        if not client:
            raise HTTPException(
                status_code=503,
                detail="Alpaca client not available. Check API credentials."
            )
        
        # Get orders
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus
        
        # Build request
        request_params = {"limit": limit}
        if status:
            request_params["status"] = QueryOrderStatus[status.upper()]
        
        request = GetOrdersRequest(**request_params)
        orders = client.get_orders(filter=request)
        
        # Convert to dict
        orders_list = []
        for order in orders:
            orders_list.append({
                "id": str(order.id),
                "symbol": order.symbol,
                "qty": float(order.qty) if order.qty else None,
                "side": order.side.value if order.side else None,
                "type": order.type.value if order.type else None,
                "status": order.status.value if order.status else None,
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None,
            })
        
        return OrderHistory(
            orders=orders_list,
            total_count=len(orders_list),
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching order history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/portfolio/analytics", response_model=AnalyticsData)
async def get_portfolio_analytics():
    """
    Get advanced portfolio analytics.
    Returns risk metrics, performance data, etc.
    """
    try:
        client = get_alpaca_client()
        if not client:
            raise HTTPException(
                status_code=503,
                detail="Alpaca client not available. Check API credentials."
            )
        
        account = client.get_account()
        positions = client.get_all_positions()
        
        # Calculate basic analytics
        total_market_value = sum(float(pos.market_value) for pos in positions)
        
        # Position allocation
        allocations = {}
        for pos in positions:
            allocations[pos.symbol] = {
                "value": float(pos.market_value),
                "percentage": (float(pos.market_value) / total_market_value * 100) 
                              if total_market_value > 0 else 0
            }
        
        # Sort by allocation
        top_allocations = dict(
            sorted(allocations.items(), key=lambda x: x[1]['percentage'], reverse=True)[:10]
        )
        
        metrics = {
            "total_value": float(account.portfolio_value),
            "equity": float(account.equity),
            "cash": float(account.cash),
            "total_positions": len(positions),
            "largest_position": max(
                (pos.symbol for pos in positions),
                key=lambda s: next(pos.market_value for pos in positions if pos.symbol == s),
                default=None
            ) if positions else None,
            "allocations": top_allocations
        }
        
        charts = {
            "allocation_chart": {
                "labels": list(top_allocations.keys()),
                "values": [v['value'] for v in top_allocations.values()],
                "percentages": [v['percentage'] for v in top_allocations.values()]
            }
        }
        
        return AnalyticsData(
            metrics=metrics,
            charts=charts,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/portfolio/refresh")
async def refresh_portfolio():
    """
    Force a portfolio data refresh.
    Returns updated summary.
    """
    return await get_portfolio_summary()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    alpaca_status = "available" if ALPACA_AVAILABLE else "unavailable"
    
    # Check credentials using centralized loader
    has_credentials = False
    if ALPACA_AVAILABLE:
        key = get_env('ALPACA_API_KEY') or get_env('APCA_API_KEY_ID') or get_env('APCA_API_KEY')
        secret = get_env('ALPACA_API_SECRET') or get_env('APCA_API_SECRET_KEY') or get_env('APCA_API_SECRET')
        has_credentials = bool(key and secret)
    
    return {
        "service": "portfolio_dashboard_service",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "alpaca_sdk": alpaca_status,
        "alpaca_credentials": "configured" if has_credentials else "missing"
    }


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting Portfolio Dashboard Service on http://0.0.0.0:8057")
    logger.info("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8057,
        log_level="info"
    )

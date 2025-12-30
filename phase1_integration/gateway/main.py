"""
FastAPI Gateway for Alpaca Options Lab

Central API gateway providing:
- REST endpoints for all services
- WebSocket for real-time updates
- Health aggregation
- Request routing to gRPC/BentoML services
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx

logger = logging.getLogger(__name__)

# Configuration from environment
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
SIGNAL_SERVICE_HOST = os.getenv("SIGNAL_SERVICE_HOST", "localhost")
SIGNAL_SERVICE_PORT = os.getenv("SIGNAL_SERVICE_PORT", "50051")
ORDER_SERVICE_HOST = os.getenv("ORDER_SERVICE_HOST", "localhost")
ORDER_SERVICE_PORT = os.getenv("ORDER_SERVICE_PORT", "50052")
BENTO_PRICE_URL = os.getenv("BENTO_PRICE_URL", "http://localhost:3000")
BENTO_IV_URL = os.getenv("BENTO_IV_URL", "http://localhost:3001")
BENTO_SENTIMENT_URL = os.getenv("BENTO_SENTIMENT_URL", "http://localhost:3002")
TRITON_URL = os.getenv("TRITON_URL", "http://localhost:8100")


# -----------------------------------------------------------------------------
# Request/Response Models
# -----------------------------------------------------------------------------

class SignalRequest(BaseModel):
    """Signal request model"""
    type: str = Field(..., description="Signal type: buy, sell, hold")
    symbol: str = Field(..., description="Stock symbol")
    strategy: str = Field(default="", description="Strategy name")
    confidence: float = Field(default=0.5, ge=0, le=1)
    source: str = Field(default="manual", description="Signal source")
    data: Dict[str, Any] = Field(default_factory=dict)


class OrderRequest(BaseModel):
    """Order request model"""
    symbol: str = Field(..., description="Stock symbol")
    side: str = Field(..., description="buy or sell")
    order_type: str = Field(default="limit")
    quantity: int = Field(..., gt=0)
    limit_price: float = Field(default=0.0)
    strategy: str = Field(default="")


class PredictionRequest(BaseModel):
    """ML prediction request"""
    symbol: str
    horizon_days: int = Field(default=5, ge=1, le=30)


class SentimentRequest(BaseModel):
    """Sentiment analysis request"""
    text: str
    symbol: Optional[str] = None


class IVForecastRequest(BaseModel):
    """IV forecast request"""
    symbol: str
    dte: int = Field(default=30, ge=1, le=365)


# -----------------------------------------------------------------------------
# Service Clients
# -----------------------------------------------------------------------------

class ServiceClient:
    """HTTP client for service calls"""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.http_client.aclose()
    
    async def get(self, url: str) -> Dict:
        try:
            resp = await self.http_client.get(url)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"GET {url} failed: {e}")
            return {"error": str(e)}
    
    async def post(self, url: str, data: Dict) -> Dict:
        try:
            resp = await self.http_client.post(url, json=data)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"POST {url} failed: {e}")
            return {"error": str(e)}


# Global client
client = ServiceClient()


# -----------------------------------------------------------------------------
# Application Lifecycle
# -----------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    logger.info("Gateway starting up...")
    
    # Initialize services
    try:
        from ..redis import get_pubsub, get_streams
        app.state.pubsub = get_pubsub()
        app.state.streams = get_streams()
        logger.info("Redis connections initialized")
    except Exception as e:
        logger.warning(f"Redis not available: {e}")
        app.state.pubsub = None
        app.state.streams = None
    
    yield
    
    # Cleanup
    logger.info("Gateway shutting down...")
    await client.close()


# -----------------------------------------------------------------------------
# FastAPI Application
# -----------------------------------------------------------------------------

app = FastAPI(
    title="Alpaca Options Lab Gateway",
    description="Central API gateway for all services",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Health Endpoints
# -----------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    """Aggregated health check"""
    checks = {
        "gateway": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    # Check BentoML services
    for name, url in [
        ("bento_price", BENTO_PRICE_URL),
        ("bento_iv", BENTO_IV_URL),
        ("bento_sentiment", BENTO_SENTIMENT_URL),
    ]:
        try:
            result = await client.get(f"{url}/healthz")
            checks[name] = result.get("status", "unknown")
        except Exception:
            checks[name] = "unavailable"
    
    # Check Triton
    try:
        result = await client.get(f"{TRITON_URL}/v2/health/ready")
        checks["triton"] = "healthy" if result else "unhealthy"
    except Exception:
        checks["triton"] = "unavailable"
    
    # Overall status
    all_healthy = all(v in ["healthy", "ok"] for k, v in checks.items() 
                      if k not in ["gateway", "timestamp"])
    checks["overall"] = "healthy" if all_healthy else "degraded"
    
    return checks


@app.get("/health/services")
async def service_health():
    """Detailed service health"""
    return {
        "redis": {
            "host": REDIS_HOST,
            "status": "connected" if app.state.pubsub else "disconnected"
        },
        "signal_service": {
            "host": SIGNAL_SERVICE_HOST,
            "port": SIGNAL_SERVICE_PORT,
        },
        "order_service": {
            "host": ORDER_SERVICE_HOST,
            "port": ORDER_SERVICE_PORT,
        },
        "bento_services": {
            "price": BENTO_PRICE_URL,
            "iv": BENTO_IV_URL,
            "sentiment": BENTO_SENTIMENT_URL,
        },
        "triton": TRITON_URL,
    }


# -----------------------------------------------------------------------------
# Signal Endpoints
# -----------------------------------------------------------------------------

@app.post("/api/signals")
async def create_signal(request: SignalRequest):
    """Create and publish a trading signal"""
    try:
        from ..grpc.services import SignalServiceImpl, Signal
        
        service = SignalServiceImpl()
        signal = Signal(
            type=request.type,
            symbol=request.symbol,
            strategy=request.strategy,
            confidence=request.confidence,
            source=request.source,
            data=request.data,
        )
        
        success, signal_id, error = await service.publish_signal(signal)
        
        if success:
            return {"success": True, "signal_id": signal_id}
        else:
            raise HTTPException(status_code=400, detail=error)
    except ImportError:
        # Fallback without gRPC
        return {
            "success": True,
            "signal_id": f"mock_{datetime.utcnow().timestamp()}",
            "note": "Signal service not available",
        }


@app.get("/api/signals")
async def get_signals(
    symbol: str = None,
    strategy: str = None,
    count: int = Query(default=50, le=500),
):
    """Get recent signals"""
    try:
        from ..grpc.services import SignalServiceImpl
        
        service = SignalServiceImpl()
        signals = await service.get_recent_signals(
            count=count,
            symbol=symbol,
            strategy=strategy,
        )
        
        return {"signals": [s.to_dict() for s in signals]}
    except ImportError:
        return {"signals": [], "note": "Signal service not available"}


# -----------------------------------------------------------------------------
# Order Endpoints
# -----------------------------------------------------------------------------

@app.post("/api/orders")
async def create_order(request: OrderRequest):
    """Submit a new order"""
    try:
        from ..grpc.services import OrderServiceImpl
        
        service = OrderServiceImpl(paper_mode=True)
        success, order_id, client_order_id, order, error = await service.submit_order(
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            limit_price=request.limit_price,
            strategy=request.strategy,
        )
        
        if success:
            return {
                "success": True,
                "order_id": order_id,
                "client_order_id": client_order_id,
                "order": order.to_dict(),
            }
        else:
            raise HTTPException(status_code=400, detail=error)
    except ImportError:
        return {
            "success": True,
            "order_id": f"mock_{datetime.utcnow().timestamp()}",
            "note": "Order service not available",
        }


@app.get("/api/orders")
async def get_orders(
    symbol: str = None,
    status: str = None,
    count: int = Query(default=50, le=500),
):
    """Get order history"""
    try:
        from ..grpc.services import OrderServiceImpl
        
        service = OrderServiceImpl(paper_mode=True)
        orders = await service.get_order_history(
            count=count,
            symbol=symbol,
            statuses=[status] if status else None,
        )
        
        return {"orders": [o.to_dict() for o in orders]}
    except ImportError:
        return {"orders": [], "note": "Order service not available"}


@app.delete("/api/orders/{order_id}")
async def cancel_order(order_id: str):
    """Cancel an order"""
    try:
        from ..grpc.services import OrderServiceImpl
        
        service = OrderServiceImpl(paper_mode=True)
        success, _, error = await service.cancel_order(order_id)
        
        if success:
            return {"success": True, "order_id": order_id}
        else:
            raise HTTPException(status_code=400, detail=error)
    except ImportError:
        raise HTTPException(status_code=503, detail="Order service not available")


# -----------------------------------------------------------------------------
# ML Prediction Endpoints
# -----------------------------------------------------------------------------

@app.post("/api/predict/direction")
async def predict_direction(request: PredictionRequest):
    """Price direction prediction"""
    result = await client.post(
        f"{BENTO_PRICE_URL}/predict",
        {
            "symbol": request.symbol,
            "horizon_days": request.horizon_days,
        }
    )
    return result


@app.post("/api/predict/iv")
async def predict_iv(request: IVForecastRequest):
    """IV forecast"""
    result = await client.post(
        f"{BENTO_IV_URL}/predict",
        {
            "symbol": request.symbol,
            "dte": request.dte,
        }
    )
    return result


@app.post("/api/predict/sentiment")
async def analyze_sentiment(request: SentimentRequest):
    """Sentiment analysis"""
    result = await client.post(
        f"{BENTO_SENTIMENT_URL}/analyze",
        {
            "text": request.text,
            "symbol": request.symbol,
        }
    )
    return result


@app.post("/api/predict/ensemble")
async def ensemble_predict(request: PredictionRequest):
    """Ensemble prediction combining all models"""
    # Gather predictions from all models in parallel
    direction_task = client.post(
        f"{BENTO_PRICE_URL}/predict",
        {"symbol": request.symbol, "horizon_days": request.horizon_days}
    )
    iv_task = client.post(
        f"{BENTO_IV_URL}/predict",
        {"symbol": request.symbol, "dte": 30}
    )
    
    direction_result, iv_result = await asyncio.gather(
        direction_task, iv_task,
        return_exceptions=True
    )
    
    # Combine results
    return {
        "symbol": request.symbol,
        "direction": direction_result if not isinstance(direction_result, Exception) else {"error": str(direction_result)},
        "iv_forecast": iv_result if not isinstance(iv_result, Exception) else {"error": str(iv_result)},
        "timestamp": datetime.utcnow().isoformat(),
    }


# -----------------------------------------------------------------------------
# WebSocket for Real-time Updates
# -----------------------------------------------------------------------------

class ConnectionManager:
    """WebSocket connection manager"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: Dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


@app.websocket("/ws/signals")
async def websocket_signals(websocket: WebSocket):
    """WebSocket endpoint for real-time signal updates"""
    await manager.connect(websocket)
    
    try:
        if app.state.pubsub:
            # Stream from Redis pub/sub
            async for signal in app.state.pubsub.subscribe_signals():
                await websocket.send_json(signal.to_dict())
        else:
            # Mock updates
            while True:
                await asyncio.sleep(5)
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat(),
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.websocket("/ws/orders")
async def websocket_orders(websocket: WebSocket):
    """WebSocket endpoint for real-time order updates"""
    await manager.connect(websocket)
    
    try:
        while True:
            await asyncio.sleep(5)
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat(),
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------

def main():
    """Run the gateway server"""
    import uvicorn
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    port = int(os.getenv("GATEWAY_PORT", "8090"))
    
    uvicorn.run(
        "phase1.gateway.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()

"""
FastAPI Main Application

Production-grade REST API for Alpaca Options Lab.

Features:
- JWT authentication
- Rate limiting
- CORS support
- WebSocket real-time updates
- Comprehensive logging
- Health checks

Usage:
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Try to import optional dependencies
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    RATE_LIMITING_AVAILABLE = True
except ImportError:
    RATE_LIMITING_AVAILABLE = False
    Limiter = None


# =============================================================================
# CONFIGURATION
# =============================================================================

class APIConfig:
    """API configuration"""
    
    # Server
    HOST: str = os.getenv("API_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("API_DEBUG", "false").lower() == "true"
    
    # CORS
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:3000,http://localhost:8053"
    ).split(",")
    
    # Rate Limiting
    RATE_LIMIT: str = os.getenv("RATE_LIMIT", "100/minute")
    
    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30
    
    # API Version
    VERSION: str = "3.0.0"
    TITLE: str = "Alpaca Options Lab API"
    DESCRIPTION: str = "Production-grade options trading platform API"


config = APIConfig()


# =============================================================================
# LIFESPAN MANAGER
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        "api_starting",
        version=config.VERSION,
        host=config.HOST,
        port=config.PORT,
    )
    
    # Initialize services
    # await initialize_database()
    # await initialize_broker()
    # await initialize_websocket()
    
    yield
    
    # Shutdown
    logger.info("api_shutting_down")
    
    # Cleanup
    # await close_database()
    # await close_broker()


# =============================================================================
# CREATE APP
# =============================================================================

def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=config.TITLE,
        description=config.DESCRIPTION,
        version=config.VERSION,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add rate limiting if available
    if RATE_LIMITING_AVAILABLE:
        limiter = Limiter(key_func=get_remote_address)
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = datetime.now(timezone.utc)
        
        response = await call_next(request)
        
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        logger.debug(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        
        return response
    
    # Register routes
    register_routes(app)
    
    return app


def register_routes(app: FastAPI) -> None:
    """Register all API routes"""
    
    # Health check
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": config.VERSION,
        }
    
    @app.get("/health/live")
    async def liveness_check():
        """Kubernetes liveness probe"""
        return {"status": "live"}
    
    @app.get("/health/ready")
    async def readiness_check():
        """Kubernetes readiness probe"""
        # Add actual readiness checks here
        # e.g., database connection, broker connection
        return {"status": "ready"}
    
    # API info
    @app.get("/api/v1")
    async def api_info():
        """API information"""
        return {
            "name": config.TITLE,
            "version": config.VERSION,
            "description": config.DESCRIPTION,
            "endpoints": {
                "portfolio": "/api/v1/portfolio",
                "strategies": "/api/v1/strategies",
                "risk": "/api/v1/risk",
                "orders": "/api/v1/orders",
                "analytics": "/api/v1/analytics",
                "websocket": "/ws",
            },
        }
    
    # Include route modules
    from src.api.routes import portfolio, strategies, risk, orders, analytics
    
    app.include_router(portfolio.router, prefix="/api/v1", tags=["Portfolio"])
    app.include_router(strategies.router, prefix="/api/v1", tags=["Strategies"])
    app.include_router(risk.router, prefix="/api/v1", tags=["Risk"])
    app.include_router(orders.router, prefix="/api/v1", tags=["Orders"])
    app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])
    
    # WebSocket
    from src.api.websocket import websocket_manager
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket):
        """WebSocket endpoint for real-time updates"""
        # For native WebSocket support (Socket.IO is separate)
        await websocket.accept()
        sid = f"ws_{id(websocket)}"
        await websocket_manager.connect(sid, "anonymous")
        try:
            while True:
                data = await websocket.receive_text()
                # Handle incoming messages
        except Exception:
            await websocket_manager.disconnect(sid)


# Create app instance
app = create_app()


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.exception(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if config.DEBUG else "An unexpected error occurred",
        },
    )


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level="debug" if config.DEBUG else "info",
    )

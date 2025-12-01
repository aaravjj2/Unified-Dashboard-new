"""
API Gateway
===========
Central reverse proxy that routes all frontend API requests to appropriate
backend microservices. This creates a single entry point for the UI.

Architecture:
- Single unified API endpoint for all services
- Request routing based on path prefixes
- Health aggregation from all backend services
- CORS handling
- Request/response logging
- API key authentication for production endpoints

Routes:
- /api/trends/* → market_trends_service (port 8050)
- /api/forecast/* → market_forecast_service (port 8051) [Future]
- /api/portfolio/* → portfolio_service (port 8056) [Future]
- /health → Aggregate health check

Port: 8049
"""

import logging
import os
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request, Response, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown events."""
    # Startup
    logger.info("API Gateway starting up...")
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=5.0),
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
    )
    yield
    # Shutdown
    logger.info("API Gateway shutting down...")
    await app.state.http_client.aclose()

# Initialize FastAPI with lifespan
app = FastAPI(
    title="API Gateway",
    description="Central API gateway for financial dashboard services",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service registry - maps path prefixes to backend service URLs
# Use Docker service names for container-to-container communication
SERVICES = {
    "dashboard": os.getenv("DASHBOARD_URL", "http://dashboard:8050"),
    "trends": os.getenv("MARKET_TRENDS_URL", "http://market_trends:8050"),
    "forecast": os.getenv("MARKET_FORECAST_URL", "http://market_forecast:8051"),
    "analysis": os.getenv("ANALYSIS_URL", "http://analysis:8054"),
    "portfolio": os.getenv("PORTFOLIO_URL", "http://portfolio:8056"),
    "research": os.getenv("RESEARCH_URL", "http://research:8058"),
    "options": os.getenv("OPTIONS_URL", "http://options_service:8060"),
    "chatbot": os.getenv("CHATBOT_URL", "http://chatbot:8062"),
    "backtester": os.getenv("BACKTESTER_URL", "http://backtester:8064"),
}

# API Key authentication (Sprint 5)
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Load valid API keys from environment (comma-separated)
VALID_API_KEYS = set(os.getenv("API_GATEWAY_KEYS", "").split(","))
# Add default key for development if no keys configured
if not VALID_API_KEYS or VALID_API_KEYS == {''}:
    VALID_API_KEYS = {"dev-key-12345"}
    logger.warning("No API_GATEWAY_KEYS configured, using default development key")

# Paths that don't require authentication
PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}

async def verify_api_key(request: Request, api_key: Optional[str] = Security(api_key_header)):
    """
    Verify API key from request header.
    
    Args:
        api_key: API key from X-API-Key header
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    # Allow local calls (from localhost) to bypass API key during development/tests
    try:
        client_host = request.client.host if request and request.client else None
    except Exception:
        client_host = None

    if client_host in ("127.0.0.1", "::1", "localhost"):
        return api_key or "local"

    if api_key and api_key in VALID_API_KEYS:
        return api_key

    logger.warning(f"Invalid API key attempt: {api_key[:10] if api_key else 'None'}...")
    raise HTTPException(
        status_code=401,
        detail="Invalid or missing API key",
        headers={"WWW-Authenticate": "ApiKey"}
    )

def requires_auth(request: Request) -> bool:
    """
    Check if a request path requires authentication.
    
    Args:
        request: The incoming request
        
    Returns:
        True if authentication is required, False otherwise
    """
    # Check if path is in public paths
    if request.url.path in PUBLIC_PATHS:
        return False
    
    # Check if path starts with any public path
    for public_path in PUBLIC_PATHS:
        if request.url.path.startswith(public_path):
            return False
    
    return True

async def proxy_request(
    service_url: str,
    path: str,
    request: Request
) -> Response:
    """
    Proxy a request to a backend service.
    
    Args:
        service_url: Base URL of the backend service
        path: Path to append to service URL
        request: Original FastAPI request
        
    Returns:
        Response from backend service
    """
    # Build target URL
    target_url = f"{service_url}{path}"
    
    # Get request body if present
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()
    
    # Forward headers (excluding host)
    headers = dict(request.headers)
    headers.pop('host', None)
    
    try:
        logger.info(f"Proxying {request.method} {path} → {target_url}")
        
        # Make request to backend service
        response = await request.app.state.http_client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=dict(request.query_params),
            content=body,
            follow_redirects=False
        )
        
        # Build response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get('content-type')
        )
        
    except httpx.ConnectError as e:
        logger.error(f"Connection failed to {service_url}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {service_url}"
        )
    except httpx.TimeoutException as e:
        logger.error(f"Timeout connecting to {service_url}: {e}")
        raise HTTPException(
            status_code=504,
            detail=f"Service timeout: {service_url}"
        )
    except Exception as e:
        logger.error(f"Error proxying request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Gateway error: {str(e)}"
        )

# Health check endpoint
@app.get("/health")
async def health_check(request: Request):
    """
    Aggregate health check for all backend services.
    Returns overall health and individual service statuses.
    """
    health_status = {
        "gateway": "healthy",
        "timestamp": None,
        "services": {}
    }
    
    from datetime import datetime
    health_status["timestamp"] = datetime.utcnow().isoformat()
    
    # Check each service
    for service_name, service_url in SERVICES.items():
        try:
            response = await request.app.state.http_client.get(
                f"{service_url}/health",
                timeout=5.0
            )
            if response.status_code == 200:
                health_status["services"][service_name] = {
                    "status": "healthy",
                    "url": service_url,
                    "response": response.json()
                }
            else:
                health_status["services"][service_name] = {
                    "status": "unhealthy",
                    "url": service_url,
                    "status_code": response.status_code
                }
        except Exception as e:
            health_status["services"][service_name] = {
                "status": "unavailable",
                "url": service_url,
                "error": str(e)
            }
    
    # Determine overall health
    unhealthy = [s for s, d in health_status["services"].items()
                 if d["status"] != "healthy"]
    
    if unhealthy:
        health_status["gateway"] = "degraded"
        health_status["unhealthy_services"] = unhealthy
    
    return health_status

# Market Trends service routes
@app.api_route("/api/trends/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def trends_proxy(path: str, request: Request, api_key: str = Depends(verify_api_key)):
    """Proxy requests to Market Trends service (requires API key)."""
    # The backend services expect paths under /api/* (for example: /api/jobs).
    # Clients call the gateway at /api/trends/<path>. When <path> is "jobs",
    # we need to forward to /api/jobs on the backend. If the incoming <path>
    # already includes the api/ prefix (e.g. api/jobs) avoid doubling it.
    if path.startswith("api/"):
        target_path = f"/{path}"
    else:
        target_path = f"/api/{path}"

    return await proxy_request(SERVICES["trends"], target_path, request)

# Market Forecast service routes (future)
@app.api_route("/api/forecast/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def forecast_proxy(path: str, request: Request, api_key: str = Depends(verify_api_key)):
    """Proxy requests to Market Forecast service (requires API key)."""
    if path.startswith("api/"):
        target_path = f"/{path}"
    else:
        target_path = f"/api/{path}"
    return await proxy_request(SERVICES["forecast"], target_path, request)

# Analysis Hub service routes (future)
@app.api_route("/api/analysis/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def analysis_proxy(path: str, request: Request, api_key: str = Depends(verify_api_key)):
    """Proxy requests to Analysis Hub service (requires API key)."""
    if path.startswith("api/"):
        target_path = f"/{path}"
    else:
        target_path = f"/api/{path}"
    return await proxy_request(SERVICES["analysis"], target_path, request)

# Portfolio service routes (future)
@app.api_route("/api/portfolio/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def portfolio_proxy(path: str, request: Request, api_key: str = Depends(verify_api_key)):
    """Proxy requests to Portfolio service (requires API key)."""
    if path.startswith("api/"):
        target_path = f"/{path}"
    else:
        target_path = f"/api/{path}"
    return await proxy_request(SERVICES["portfolio"], target_path, request)

# Research Lab service routes (future)
@app.api_route("/api/research/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def research_proxy(path: str, request: Request, api_key: str = Depends(verify_api_key)):
    """Proxy requests to Research Lab service (requires API key)."""
    if path.startswith("api/"):
        target_path = f"/{path}"
    else:
        target_path = f"/api/{path}"
    return await proxy_request(SERVICES["research"], target_path, request)

# Options Trading service routes (future)
@app.api_route("/api/options/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def options_proxy(path: str, request: Request, api_key: str = Depends(verify_api_key)):
    """Proxy requests to Options Trading service (requires API key)."""
    if path.startswith("api/"):
        target_path = f"/{path}"
    else:
        target_path = f"/api/{path}"
    return await proxy_request(SERVICES["options"], target_path, request)

# AI Chatbot service routes (Sprint 7)
@app.api_route("/api/chat/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def chatbot_proxy(path: str, request: Request):
    """Proxy requests to AI Chatbot service (public access for chat)."""
    if path.startswith("api/"):
        target_path = f"/{path}"
    else:
        target_path = f"/api/{path}"
    return await proxy_request(SERVICES["chatbot"], target_path, request)

# Backtesting service routes (Sprint 8)
@app.api_route("/api/backtest/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def backtest_proxy(path: str, request: Request):
    """Proxy requests to Backtesting service (public access)."""
    if path.startswith("api/"):
        target_path = f"/{path}"
    else:
        target_path = f"/api/{path}"
    return await proxy_request(SERVICES["backtester"], target_path, request)

# Dashboard UI proxy - Catch-all route for the main Dash application
# This should be LAST to avoid conflicting with API routes
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def dashboard_proxy(path: str, request: Request):
    """
    Proxy all non-API requests to the main Dash dashboard.
    This allows the gateway to serve as the single entry point.
    """
    # Preserve the original path
    target_path = f"/{path}" if path else "/"
    return await proxy_request(SERVICES["dashboard"], target_path, request)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,  # Changed from 8049 to 8000 as main entry point
        log_level="info"
    )

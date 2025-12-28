"""
AlphaSim FastAPI Application - Main entry point for the AlphaSim API.
"""
import os
import time
from typing import Optional
from fastapi import FastAPI, Query, HTTPException, Header, Response
from fastapi.responses import JSONResponse, PlainTextResponse

from .engine import get_engine
from .rate_limiter import get_rate_limiter
from .cache import get_cache
from .schema import build_rate_limit_response, build_error_response
from .metrics import (
    track_request, track_latency, track_rate_limit_rejection,
    get_metrics_text, get_metrics_dict, PROMETHEUS_AVAILABLE
)

# Create FastAPI app
app = FastAPI(
    title="AlphaSim API",
    description="Internal Alpha Vantage-compatible API service",
    version="0.1.0"
)


# ---------- Health Endpoints ----------

@app.get("/health")
async def health():
    """Health check endpoint for readiness/liveness probes."""
    return {"status": "ok", "service": "alpha_sim"}


@app.get("/metrics")
async def metrics(format: str = Query("json", description="Response format: json or prometheus")):
    """Metrics endpoint - supports JSON and Prometheus formats."""
    if format == "prometheus" and PROMETHEUS_AVAILABLE:
        return PlainTextResponse(
            content=get_metrics_text(),
            media_type="text/plain; version=0.0.4"
        )
    
    cache = get_cache()
    rate_limiter = get_rate_limiter()
    
    return {
        "cache": cache.stats(),
        "rate_limiter": {
            "active_keys": len(rate_limiter._buckets)
        },
        "prometheus": get_metrics_dict()
    }


# ---------- Main Query Endpoint ----------

@app.get("/query")
async def query(
    function: str = Query(..., description="Alpha Vantage function name"),
    symbol: Optional[str] = Query(None, description="Ticker symbol"),
    apikey: str = Query(..., description="API key for rate limiting"),
    outputsize: str = Query("compact", description="Output size: compact or full"),
    interval: Optional[str] = Query(None, description="Time interval for intraday"),
    time_period: Optional[int] = Query(None, description="Time period for indicators"),
    series_type: str = Query("close", description="Series type for indicators"),
    datatype: str = Query("json", description="Response format: json or csv"),
):
    """
    Main query endpoint - mimics Alpha Vantage API surface.
    
    Supported functions:
    - TIME_SERIES_DAILY
    - TIME_SERIES_INTRADAY
    - SMA
    - EMA
    - RSI
    - NEWS_SENTIMENT
    - HISTORICAL_OPTIONS
    """
    start_time = time.time()
    func_upper = function.upper()
    
    # Rate limiting check
    rate_limiter = get_rate_limiter()
    allowed, retry_after = rate_limiter.allow_request(apikey)
    
    if not allowed:
        track_rate_limit_rejection()
        track_request(func_upper, "429")
        track_latency(func_upper, time.time() - start_time)
        return JSONResponse(
            status_code=429,
            content=build_rate_limit_response(retry_after or 3600),
            headers={"Retry-After": str(retry_after or 3600)}
        )
    
    # Get engine
    engine = get_engine()
    
    # Route to appropriate handler
    try:
        result = None
        
        if func_upper == "TIME_SERIES_DAILY":
            if not symbol:
                track_request(func_upper, "400")
                track_latency(func_upper, time.time() - start_time)
                return JSONResponse(
                    status_code=400,
                    content=build_error_response("Missing required parameter: symbol")
                )
            result = engine.time_series_daily(symbol, outputsize)
        
        elif func_upper == "TIME_SERIES_INTRADAY":
            if not symbol:
                track_request(func_upper, "400")
                track_latency(func_upper, time.time() - start_time)
                return JSONResponse(
                    status_code=400,
                    content=build_error_response("Missing required parameter: symbol")
                )
            result = engine.time_series_intraday(symbol, interval or "5min", outputsize)
        
        elif func_upper == "SMA":
            if not symbol:
                track_request(func_upper, "400")
                track_latency(func_upper, time.time() - start_time)
                return JSONResponse(
                    status_code=400,
                    content=build_error_response("Missing required parameter: symbol")
                )
            result = engine.calculate_sma(
                symbol,
                time_period=time_period or 10,
                series_type=series_type,
                interval=interval or "daily"
            )
        
        elif func_upper == "EMA":
            if not symbol:
                track_request(func_upper, "400")
                track_latency(func_upper, time.time() - start_time)
                return JSONResponse(
                    status_code=400,
                    content=build_error_response("Missing required parameter: symbol")
                )
            result = engine.calculate_ema(
                symbol,
                time_period=time_period or 10,
                series_type=series_type
            )
        
        elif func_upper == "RSI":
            if not symbol:
                track_request(func_upper, "400")
                track_latency(func_upper, time.time() - start_time)
                return JSONResponse(
                    status_code=400,
                    content=build_error_response("Missing required parameter: symbol")
                )
            result = engine.calculate_rsi(
                symbol,
                time_period=time_period or 14,
                series_type=series_type
            )
        
        elif func_upper == "NEWS_SENTIMENT":
            if not symbol:
                track_request(func_upper, "400")
                track_latency(func_upper, time.time() - start_time)
                return JSONResponse(
                    status_code=400,
                    content=build_error_response("Missing required parameter: symbol")
                )
            from .news import fetch_and_score
            result = fetch_and_score(symbol, limit=20, use_cache=True)
        
        elif func_upper == "HISTORICAL_OPTIONS":
            if not symbol:
                track_request(func_upper, "400")
                track_latency(func_upper, time.time() - start_time)
                return JSONResponse(
                    status_code=400,
                    content=build_error_response("Missing required parameter: symbol")
                )
            from .options import get_options_chain
            result = get_options_chain(
                symbol,
                expiration=None,  # Get all expirations
                option_type=None,  # Get both calls and puts
                use_cache=True
            )
        
        else:
            track_request(func_upper, "400")
            track_latency(func_upper, time.time() - start_time)
            return JSONResponse(
                status_code=400,
                content=build_error_response(
                    f"Unknown function: {function}",
                    note="Supported functions: TIME_SERIES_DAILY, TIME_SERIES_INTRADAY, SMA, EMA, RSI, NEWS_SENTIMENT, HISTORICAL_OPTIONS"
                )
            )
        
        # Track successful request
        track_request(func_upper, "200")
        track_latency(func_upper, time.time() - start_time)
        return result
        
    except Exception as e:
        # Track error
        track_request(func_upper, "500")
        track_latency(func_upper, time.time() - start_time)
        from .metrics import track_error
        track_error(func_upper, type(e).__name__)
        return JSONResponse(
            status_code=500,
            content=build_error_response(f"Internal error: {str(e)}")
        )


# ---------- Admin Endpoints ----------

@app.get("/admin/quota/{key}")
async def admin_get_quota(
    key: str,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")
):
    """Get quota info for an API key (admin only)."""
    rate_limiter = get_rate_limiter()
    
    # Check admin access
    admin_key = x_admin_key or os.getenv("ALPHA_SIM_ADMIN_KEY", "admin")
    if not rate_limiter.is_admin(admin_key):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return rate_limiter.get_quota(key)


@app.post("/admin/reset/{key}")
async def admin_reset_quota(
    key: str,
    tokens: Optional[float] = None,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")
):
    """Reset quota for an API key (admin only)."""
    rate_limiter = get_rate_limiter()
    
    # Check admin access
    admin_key = x_admin_key or os.getenv("ALPHA_SIM_ADMIN_KEY", "admin")
    if not rate_limiter.is_admin(admin_key):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return rate_limiter.reset_quota(key, tokens)


# ---------- Root Endpoint ----------

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "service": "AlphaSim",
        "version": "0.1.0",
        "description": "Internal Alpha Vantage-compatible API",
        "endpoints": {
            "query": "/query?function=...&symbol=...&apikey=...",
            "health": "/health",
            "metrics": "/metrics",
            "admin_quota": "/admin/quota/{key}",
            "admin_reset": "/admin/reset/{key}"
        },
        "supported_functions": [
            "TIME_SERIES_DAILY",
            "TIME_SERIES_INTRADAY",
            "SMA",
            "EMA",
            "RSI",
            "NEWS_SENTIMENT",
            "HISTORICAL_OPTIONS"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8065)

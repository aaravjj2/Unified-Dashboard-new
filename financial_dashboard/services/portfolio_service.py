#!/usr/bin/env python3
"""
Portfolio Service - Headless Backend
====================================
FastAPI service for portfolio management and analysis.
Decouples business logic from UI, enabling reusability and scaling.

Architecture:
- Job-based async execution model
- Thread-safe job tracking
- Health monitoring endpoint
- Alpaca integration for live positions

Endpoints:
- POST /api/jobs - Create portfolio analysis job
- GET /api/jobs/{job_id} - Check job status
- GET /health - Service health check

Port: 8056
"""

import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
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
    title="Portfolio Service",
    description="Headless backend for portfolio management and analysis",
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

# Job storage and executor
jobs: Dict[str, Dict[str, Any]] = {}
jobs_lock = Lock()
executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="portfolio_worker")


# Request/Response models
class PortfolioJobRequest(BaseModel):
    """Request to create a portfolio analysis job."""
    analysis_type: str = Field(
        default="positions",
        description="Type of analysis: positions, analytics, optimization, factors, orders"
    )
    date_range_days: Optional[int] = Field(
        default=30,
        description="Number of days for historical analysis"
    )
    include_history: bool = Field(
        default=True,
        description="Include historical price data"
    )


class JobStatusResponse(BaseModel):
    """Response containing job status and results."""
    job_id: str
    status: str  # pending, running, completed, failed
    progress: Optional[float] = None
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


def get_alpaca_client():
    """Get Alpaca trading client from environment."""
    if not ALPACA_AVAILABLE:
        return None
    
    try:
        from config import get_cfg
        # Support multiple key naming conventions including ALPACA2_KEY
        key = (get_cfg('ALPACA2_KEY') or get_cfg('APCA_API_KEY_ID') or 
               get_cfg('APCA_API_KEY') or get_cfg('ALPACA_API_KEY'))
        secret = (get_cfg('ALPACA2_SECRET') or get_cfg('APCA_API_SECRET_KEY') or 
                  get_cfg('APCA_API_SECRET') or get_cfg('ALPACA_API_SECRET'))
    except Exception:
        try:
            from config import get_cfg
            key = (get_cfg('ALPACA2_KEY') or get_cfg('APCA_API_KEY_ID') or 
                   get_cfg('APCA_API_KEY') or get_cfg('ALPACA_API_KEY'))
            secret = (get_cfg('ALPACA2_SECRET') or get_cfg('APCA_API_SECRET_KEY') or 
                      get_cfg('APCA_API_SECRET') or get_cfg('ALPACA_API_SECRET'))
        except Exception:
            key = (os.getenv("ALPACA2_KEY") or os.getenv("APCA_API_KEY_ID") or 
                   os.getenv('APCA_API_KEY') or os.getenv('ALPACA_API_KEY'))
            secret = (os.getenv("ALPACA2_SECRET") or os.getenv("APCA_API_SECRET_KEY") or 
                      os.getenv('APCA_API_SECRET') or os.getenv('ALPACA_API_SECRET'))
    if not key or not secret:
        logger.warning("Alpaca credentials not found in environment")
        return None
    
    # Default to paper trading
    paper = True
    logger.info(f"✅ Alpaca client initialized (paper={paper}, key_prefix={key[:4]}...)")
    return TradingClient(key, secret, paper=paper)


def run_portfolio_job(job_id: str, request: PortfolioJobRequest):
    """
    Worker function to execute portfolio analysis.
    Runs in background thread pool.
    """
    try:
        # Update job status
        with jobs_lock:
            jobs[job_id]["status"] = "running"
            jobs[job_id]["progress"] = 0.1
            jobs[job_id]["message"] = "Connecting to Alpaca..."
        
        # Get Alpaca client
        client = get_alpaca_client()
        if not client:
            raise Exception("Alpaca client not available. Check API credentials.")
        
        # Update progress
        with jobs_lock:
            jobs[job_id]["progress"] = 0.3
            jobs[job_id]["message"] = "Fetching portfolio data..."
        
        # Get account info
        account = client.get_account()
        
        # Get positions
        positions = client.get_all_positions()
        
        # Update progress
        with jobs_lock:
            jobs[job_id]["progress"] = 0.6
            jobs[job_id]["message"] = f"Processing {len(positions)} positions..."
        
        # Build result based on analysis type
        result = {
            "analysis_type": request.analysis_type,
            "timestamp": datetime.now().isoformat(),
            "account": {
                "equity": float(account.equity),
                "cash": float(account.cash),
                "buying_power": float(account.buying_power),
                "portfolio_value": float(account.portfolio_value),
                "currency": account.currency,
                "status": account.status,
            },
            "positions": []
        }
        
        # Process positions
        for pos in positions:
            position_data = {
                "symbol": pos.symbol,
                "qty": float(pos.qty),
                "side": pos.side,
                "market_value": float(pos.market_value),
                "cost_basis": float(pos.cost_basis),
                "unrealized_pl": float(pos.unrealized_pl),
                "unrealized_plpc": float(pos.unrealized_plpc),
                "current_price": float(pos.current_price),
                "avg_entry_price": float(pos.avg_entry_price),
            }
            result["positions"].append(position_data)
        
        # Calculate summary statistics
        total_unrealized_pl = sum(p["unrealized_pl"] for p in result["positions"])
        result["summary"] = {
            "total_positions": len(result["positions"]),
            "total_unrealized_pl": total_unrealized_pl,
            "total_market_value": sum(p["market_value"] for p in result["positions"]),
            "total_cost_basis": sum(p["cost_basis"] for p in result["positions"]),
        }
        
        # Update progress
        with jobs_lock:
            jobs[job_id]["progress"] = 0.9
            jobs[job_id]["message"] = "Finalizing results..."
        
        time.sleep(0.5)  # Brief pause for UI feedback
        
        # Mark job as completed
        with jobs_lock:
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["progress"] = 1.0
            jobs[job_id]["message"] = "Portfolio analysis complete"
            jobs[job_id]["result"] = result
            jobs[job_id]["completed_at"] = datetime.now().isoformat()
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        with jobs_lock:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)
            jobs[job_id]["completed_at"] = datetime.now().isoformat()


@app.post("/api/jobs", response_model=JobStatusResponse)
async def create_job(request: PortfolioJobRequest):
    """
    Create a new portfolio analysis job.
    Returns job_id for status polling.
    """
    job_id = str(uuid.uuid4())
    
    # Initialize job record
    job_record = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0.0,
        "message": "Job queued",
        "result": None,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "error": None,
        "request": request.dict()
    }
    
    with jobs_lock:
        jobs[job_id] = job_record
    
    # Submit job to executor
    executor.submit(run_portfolio_job, job_id, request)
    
    logger.info(f"Created job {job_id} for analysis type: {request.analysis_type}")
    
    return JobStatusResponse(**job_record)


@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get status of a portfolio analysis job.
    """
    with jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        job = jobs[job_id].copy()
    
    return JobStatusResponse(**job)


@app.get("/api/account")
async def get_account():
    """
    Get current account summary and positions from Alpaca.
    Synchronous endpoint for quick portfolio data retrieval.
    """
    try:
        client = get_alpaca_client()
        if not client:
            return {
                "error": "Alpaca client not available",
                "message": "Ensure APCA_API_KEY_ID and APCA_API_SECRET_KEY are set",
                "timestamp": datetime.now().isoformat()
            }
        
        # Get account and positions
        account = client.get_account()
        positions = client.get_all_positions()
        
        # Calculate totals
        total_cost_basis = sum(float(pos.cost_basis) for pos in positions)
        total_unrealized_pl = sum(float(pos.unrealized_pl) for pos in positions)
        
        # Format response
        return {
            "account": {
                "portfolio_value": float(account.portfolio_value),
                "equity": float(account.equity),
                "cash": float(account.cash),
                "buying_power": float(account.buying_power),
                "currency": account.currency,
                "status": account.status
            },
            "summary": {
                "total_positions": len(positions),
                "total_cost_basis": round(total_cost_basis, 2),
                "total_unrealized_pl": round(total_unrealized_pl, 2),
                "total_unrealized_pl_pct": round((total_unrealized_pl / total_cost_basis * 100) if total_cost_basis > 0 else 0, 2)
            },
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error fetching account data: {e}", exc_info=True)
        return {
            "error": str(e),
            "message": "Failed to fetch account data from Alpaca",
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    alpaca_status = "available" if ALPACA_AVAILABLE else "unavailable"
    
    # Check credentials
    has_credentials = False
    if ALPACA_AVAILABLE:
        key = os.getenv("APCA_API_KEY_ID") or os.getenv('APCA_API_KEY') or os.getenv('ALPACA_API_KEY')
        secret = os.getenv("APCA_API_SECRET_KEY") or os.getenv('APCA_API_SECRET') or os.getenv('ALPACA_API_SECRET')
        has_credentials = bool(key and secret)
    
    return {
        "service": "portfolio_service",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "alpaca_sdk": alpaca_status,
        "alpaca_credentials": "configured" if has_credentials else "missing",
        "active_jobs": len([j for j in jobs.values() if j["status"] in ["pending", "running"]]),
        "total_jobs": len(jobs)
    }


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting Portfolio Service on http://0.0.0.0:8056")
    logger.info("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8056,
        log_level="info"
    )

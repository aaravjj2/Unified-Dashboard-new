"""
Market Forecast Service - Headless Backend
===========================================
FastAPI service providing forecast analysis capabilities.

Endpoints:
- POST /api/jobs - Create new forecast job
- GET /api/jobs/{job_id} - Get job status and results
- GET /health - Health check

Port: 8051
"""

import os
import sys
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from threading import Lock
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Setup paths
SERVICE_DIR = Path(__file__).parent
APP_DIR = SERVICE_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state
JOBS: Dict[str, Dict] = {}
JOBS_LOCK = Lock()
executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="forecast-worker")

# FastAPI app
app = FastAPI(
    title="Market Forecast Service",
    description="Backend service for market forecasting",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ForecastJobRequest(BaseModel):
    """Request to create a forecast job."""
    tickers: List[str] = Field(..., description="List of stock tickers")
    horizon: str = Field(default="30d", description="Forecast horizon")
    model_type: str = Field(default="auto", description="Model type: auto, arima, lstm")


class JobStatus(BaseModel):
    """Job status response."""
    job_id: str
    status: str  # pending, running, completed, failed
    progress: float = 0.0
    message: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


# ============================================================================
# JOB EXECUTION
# ============================================================================

def run_forecast_job(job_id: str, params: Dict[str, Any]):
    """Execute forecast in background thread."""
    logger.info(f"Job {job_id}: Starting forecast with params: {params}")
    
    with JOBS_LOCK:
        if job_id not in JOBS:
            logger.error(f"Job {job_id} not found")
            return
        JOBS[job_id]['status'] = 'running'
        JOBS[job_id]['started_at'] = datetime.utcnow().isoformat()
        JOBS[job_id]['progress'] = 0.1
    
    try:
        tickers = params.get('tickers', [])
        horizon = params.get('horizon', '30d')
        model_type = params.get('model_type', 'auto')
        
        logger.info(f"Job {job_id}: Forecasting {len(tickers)} tickers")
        
        with JOBS_LOCK:
            JOBS[job_id]['progress'] = 0.5
            JOBS[job_id]['message'] = "Generating forecasts..."
        
        # Simulate forecast (in real implementation, call actual forecast logic)
        import time
        time.sleep(2)
        
        results = {
            'tickers': tickers,
            'horizon': horizon,
            'model_type': model_type,
            'forecasts': [
                {
                    'ticker': t,
                    'forecast_price': 100.0 + hash(t) % 50,
                    'confidence': 0.85
                }
                for t in tickers
            ],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        with JOBS_LOCK:
            JOBS[job_id]['status'] = 'completed'
            JOBS[job_id]['progress'] = 1.0
            JOBS[job_id]['completed_at'] = datetime.utcnow().isoformat()
            JOBS[job_id]['result'] = results
            JOBS[job_id]['message'] = "Forecast completed"
        
        logger.info(f"Job {job_id}: Completed successfully")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        with JOBS_LOCK:
            JOBS[job_id]['status'] = 'failed'
            JOBS[job_id]['error'] = str(e)
            JOBS[job_id]['completed_at'] = datetime.utcnow().isoformat()


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "market_forecast",
        "timestamp": datetime.utcnow().isoformat(),
        "active_jobs": len([j for j in JOBS.values() if j['status'] == 'running'])
    }


@app.post("/api/jobs")
async def create_job(request: ForecastJobRequest):
    """Create a new forecast job."""
    job_id = str(uuid.uuid4())
    
    job_data = {
        'job_id': job_id,
        'status': 'pending',
        'progress': 0.0,
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'params': request.dict()
    }
    
    with JOBS_LOCK:
        JOBS[job_id] = job_data
    
    # Submit to executor
    executor.submit(run_forecast_job, job_id, request.dict())
    
    logger.info(f"Created job {job_id}")
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": f"Forecast job created for {len(request.tickers)} tickers"
    }


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a specific job."""
    with JOBS_LOCK:
        if job_id not in JOBS:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        job_data = JOBS[job_id].copy()
    
    return JobStatus(**job_data)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8053,  # Changed from 8051 to avoid conflict with main dashboard
        log_level="info"
    )


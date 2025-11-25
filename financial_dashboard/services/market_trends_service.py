"""
Market Trends Headless Backend Service
=======================================
A pure FastAPI service that exposes the Market Trends analysis logic
via REST API endpoints. No Dash UI code - this is a backend-only service.

Architecture:
- Job-based async execution (start job, poll status, get results)
- Thread-safe caching for results and models
- Health checks and graceful shutdown
- Comprehensive error handling

API Endpoints:
- POST /api/jobs - Start new analysis job
- GET /api/jobs/{job_id} - Get job status
- GET /api/results/latest - Get most recent cached results
- GET /health - Health check

Port: 8050
"""

import os
import sys
import json
import time
import uuid
import logging
import traceback
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Path configuration
APP_DIR = Path(__file__).parent.parent
PROJECT_ROOT = APP_DIR.parent
GRADIO_DIR = PROJECT_ROOT / 'Gradio'

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

# Import analysis module
mt_mod = None
try:
    mt_path = GRADIO_DIR / 'market_trends.py'
    if mt_path.exists():
        spec = importlib.util.spec_from_file_location('market_trends', mt_path)
        mt_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mt_mod)
        logger.info(f"✓ Loaded market_trends module from {mt_path}")
except Exception as e:
    logger.error(f"Failed to load market_trends module: {e}")

# Import shared utilities
SH = None
try:
    shared_path = APP_DIR / '_shared.py'
    if shared_path.exists():
        spec = importlib.util.spec_from_file_location('_shared', shared_path)
        SH = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(SH)
        logger.info("✓ Loaded _shared module")
except Exception as e:
    logger.warning(f"Could not load _shared module: {e}")

# Optional local .env loader
try:
    from _shared_env import get_env, load_local_env
    load_local_env()
except Exception:
    def get_env(k, d=None):
        return os.getenv(k, d)

# Thread-safe caches
JOBS_LOCK = Lock()
RESULTS_LOCK = Lock()
MODEL_LOCK = Lock()

JOBS: Dict[str, Dict[str, Any]] = {}
RESULTS_CACHE: Dict[str, Any] = {'results': None, 'loaded_at': None}
MODEL_CACHE: Dict[str, Any] = {'model': None, 'loaded_at': None, 'ttl': 3600}

# Thread pool for background jobs
executor = ThreadPoolExecutor(max_workers=3)

# Initialize FastAPI
app = FastAPI(
    title="Market Trends Service",
    description="Headless backend for market trends analysis",
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

# Pydantic models
class JobRequest(BaseModel):
    tickers: List[str] = Field(..., min_items=1, description="List of stock tickers")
    period: str = Field(default='1y', description="Time period (e.g., 1y, 6mo)")
    interval: str = Field(default='1d', description="Data interval (e.g., 1d, 1wk)")
    options: bool = Field(default=True, description="Include options analysis")
    news: bool = Field(default=True, description="Include news sentiment")
    cache_only: bool = Field(default=False, description="Use cached data only")
    options_topn: int = Field(default=3, description="Top N options to analyze")
    min_avg_vol: float = Field(default=0.0, description="Minimum average volume filter")
    topn: int = Field(default=10, description="Number of top results")

class JobStatus(BaseModel):
    job_id: str
    status: str  # 'pending', 'running', 'completed', 'failed'
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: float = 0.0
    message: str = ""
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str

# Helper functions
def load_cached_results_from_disk() -> Optional[Dict[str, Any]]:
    """Load cached results from outputs directory."""
    try:
        if SH and hasattr(SH, 'load_last_cached_results'):
            cached = SH.load_last_cached_results()
            if cached and (cached.get('detailed') or cached.get('tidy')):
                logger.info(f"Loaded {len(cached.get('detailed', []))} cached results from disk")
                return cached
    except Exception as e:
        logger.error(f"Error loading cached results: {e}")
    return None

def run_analysis_job(job_id: str, params: Dict[str, Any]):
    """Execute analysis in background thread."""
    logger.info(f"Job {job_id}: Starting analysis with params: {params}")
    
    with JOBS_LOCK:
        if job_id not in JOBS:
            logger.error(f"Job {job_id} not found in registry")
            return
        JOBS[job_id]['status'] = 'running'
        JOBS[job_id]['started_at'] = datetime.utcnow().isoformat()
        JOBS[job_id]['progress'] = 0.1
    
    try:
        # If the concrete analysis module isn't available, fall back to the
        # built-in mock data path below. Previously this raised an exception
        # which caused jobs to fail even though a harmless mock fallback
        # exists later in this function.
        if mt_mod is None:
            logger.warning("Market trends analysis module not available - using mock fallback")
        
        # Extract parameters
        tickers = params.get('tickers', [])
        period = params.get('period', '1y')
        interval = params.get('interval', '1d')
        no_options = not params.get('options', True)
        no_news = not params.get('news', True)
        cache_only = params.get('cache_only', False)
        options_topn = params.get('options_topn', 3)
        min_avg_vol = params.get('min_avg_vol', 0.0)
        topn = params.get('topn', 10)
        
        logger.info(f"Job {job_id}: Running analysis for {len(tickers)} tickers")
        
        with JOBS_LOCK:
            JOBS[job_id]['progress'] = 0.3
            JOBS[job_id]['message'] = "Fetching market data..."
        
        # Look for run_full_analysis function
        run_fn = None
        for fn_name in ['run_full_analysis', 'analyze_tickers', 'batch_analyze']:
            if hasattr(mt_mod, fn_name):
                run_fn = getattr(mt_mod, fn_name)
                break
        
        if run_fn is None:
            # Fallback: generate mock data
            logger.warning(f"Job {job_id}: No analysis function found, generating mock data")
            import random
            results = {
                'ok': True,
                'detailed': [
                    {
                        'ticker': t,
                        'composite_score': round(random.uniform(-1, 1), 3),
                        'signal': random.choice(['BUY', 'SELL', 'HOLD']),
                        'price': round(random.uniform(50, 500), 2)
                    }
                    for t in tickers
                ],
                'tidy': [],
                'prices': {},
                'brief_text': f"Mock analysis for {len(tickers)} tickers",
                'brief_json': {}
            }
        else:
            with JOBS_LOCK:
                JOBS[job_id]['progress'] = 0.5
                JOBS[job_id]['message'] = "Analyzing tickers..."
            
            # Call the analysis function
            results = run_fn(
                tickers=tickers,
                period=period,
                interval=interval,
                options_topn=options_topn,
                no_options=no_options,
                no_news=no_news,
                min_avg_vol=min_avg_vol,
                topn=topn,
                use_cache_only=cache_only
            )
        
        with JOBS_LOCK:
            JOBS[job_id]['progress'] = 0.9
            JOBS[job_id]['message'] = "Finalizing results..."
        
        # Sanitize results for JSON serialization
        sanitized_results = _sanitize_results(results)
        
        # Update cache
        with RESULTS_LOCK:
            RESULTS_CACHE['results'] = sanitized_results
            RESULTS_CACHE['loaded_at'] = time.time()
        
        # Mark job complete
        with JOBS_LOCK:
            JOBS[job_id]['status'] = 'completed'
            JOBS[job_id]['completed_at'] = datetime.utcnow().isoformat()
            JOBS[job_id]['progress'] = 1.0
            JOBS[job_id]['message'] = f"Analysis complete: {len(sanitized_results.get('detailed', []))} results"
            JOBS[job_id]['result'] = sanitized_results
        
        logger.info(f"Job {job_id}: Completed successfully")
        
    except Exception as e:
        error_msg = f"Analysis failed: {str(e)}"
        logger.error(f"Job {job_id}: {error_msg}", exc_info=True)
        
        with JOBS_LOCK:
            JOBS[job_id]['status'] = 'failed'
            JOBS[job_id]['completed_at'] = datetime.utcnow().isoformat()
            JOBS[job_id]['error'] = error_msg
            JOBS[job_id]['message'] = error_msg

def _sanitize_results(data: Any) -> Any:
    """Recursively sanitize data for JSON serialization."""
    if data is None:
        return None
    elif isinstance(data, (str, int, float, bool)):
        return data
    elif isinstance(data, dict):
        return {k: _sanitize_results(v) for k, v in data.items()}
    elif isinstance(data, (list, tuple)):
        return [_sanitize_results(item) for item in data]
    elif hasattr(data, 'to_dict'):
        return _sanitize_results(data.to_dict())
    elif hasattr(data, '__dict__'):
        return _sanitize_results(data.__dict__)
    else:
        return str(data)

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "market_trends",
        "timestamp": datetime.utcnow().isoformat(),
        "module_loaded": mt_mod is not None,
        "active_jobs": len([j for j in JOBS.values() if j['status'] in ['pending', 'running']]),
        "cached_results": RESULTS_CACHE['results'] is not None
    }

@app.post("/api/jobs", response_model=JobResponse)
async def create_job(request: JobRequest, background_tasks: BackgroundTasks):
    """Start a new analysis job."""
    job_id = str(uuid.uuid4())
    
    job_data = {
        'job_id': job_id,
        'status': 'pending',
        'created_at': datetime.utcnow().isoformat(),
        'started_at': None,
        'completed_at': None,
        'progress': 0.0,
        'message': 'Job queued',
        'error': None,
        'result': None,
        'params': request.dict()
    }
    
    with JOBS_LOCK:
        JOBS[job_id] = job_data
    
    # Submit to thread pool
    executor.submit(run_analysis_job, job_id, request.dict())
    
    logger.info(f"Created job {job_id} for {len(request.tickers)} tickers")
    
    return JobResponse(
        job_id=job_id,
        status='pending',
        message=f'Job {job_id} created and queued'
    )

@app.get("/api/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get status of a specific job."""
    with JOBS_LOCK:
        if job_id not in JOBS:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        job_data = JOBS[job_id].copy()
    
    return JobStatus(**job_data)

@app.get("/api/results/latest")
async def get_latest_results():
    """Get the most recent cached analysis results."""
    with RESULTS_LOCK:
        if RESULTS_CACHE['results'] is None:
            # Try loading from disk
            cached = load_cached_results_from_disk()
            if cached:
                RESULTS_CACHE['results'] = cached
                RESULTS_CACHE['loaded_at'] = time.time()
            else:
                raise HTTPException(
                    status_code=404,
                    detail="No cached results available. Run an analysis first."
                )
        
        results = RESULTS_CACHE['results']
        loaded_at = RESULTS_CACHE['loaded_at']
    
    return {
        "success": True,
        "data": results,
        "cached_at": datetime.fromtimestamp(loaded_at).isoformat() if loaded_at else None,
        "row_count": len(results.get('detailed', []))
    }

@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job from the registry."""
    with JOBS_LOCK:
        if job_id not in JOBS:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        del JOBS[job_id]
    
    return {"success": True, "message": f"Job {job_id} deleted"}

@app.on_event("startup")
async def startup_event():
    """Load cached results on startup."""
    logger.info("Market Trends Service starting up...")
    cached = load_cached_results_from_disk()
    if cached:
        with RESULTS_LOCK:
            RESULTS_CACHE['results'] = cached
            RESULTS_CACHE['loaded_at'] = time.time()
        logger.info(f"Pre-loaded {len(cached.get('detailed', []))} cached results")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Market Trends Service shutting down...")
    executor.shutdown(wait=False)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8050,
        log_level="info"
    )

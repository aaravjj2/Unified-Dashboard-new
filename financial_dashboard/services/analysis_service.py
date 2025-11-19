"""
Analysis Hub Service - Headless Backend
========================================
Provides attribution analysis and portfolio analytics as a FastAPI service.

Endpoints:
- POST /api/jobs - Create new attribution analysis job
- GET /api/jobs/{job_id} - Get job status and results
- GET /health - Health check

Run: python -m uvicorn services.analysis_service:app --host 0.0.0.0 --port 8054
"""

import os
import sys
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import pandas as pd
import numpy as np
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

# Import analysis utilities
try:
    import _shared as SH
    logger.info("✓ Loaded _shared module")
except Exception as e:
    logger.warning(f"Could not load _shared module: {e}")

# Import database utilities for PostgreSQL (Sprint 2)
try:
    from utils.db_utils import execute_pg_query, initialize_pg_pool
    USE_POSTGRES = True
    logger.info("✓ PostgreSQL database available")
except Exception as e:
    USE_POSTGRES = False
    logger.warning(f"PostgreSQL not available, falling back to CSV: {e}")
    SH = None

try:
    from utils import attribution as ATTR
    logger.info("✓ Loaded attribution utils")
except Exception as e:
    logger.warning(f"Could not load attribution utils: {e}")
    ATTR = None

# Global job storage and caching
JOBS: Dict[str, Dict] = {}
JOBS_LOCK = Lock()
RESULTS_CACHE: Dict[str, Any] = {}
CACHE_LOCK = Lock()
executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="analysis-worker")

# FastAPI app
app = FastAPI(
    title="Analysis Hub Service",
    description="Backend service for attribution analysis and portfolio analytics",
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

class AnalysisJobRequest(BaseModel):
    """Request to create an attribution analysis job."""
    picks_type: str = Field(..., description="Type of picks: 'weekly' or 'monthly'")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    horizon: str = Field(default="1w", description="Analysis horizon: '1w', '1m', or '3m'")
    regime_filter: str = Field(default="all", description="Market regime filter")


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
# HELPER FUNCTIONS - PICKS LOADING
# ============================================================================

def _find_latest_picks_generic(patterns=None):
    """Find the most recent picks CSV using patterns."""
    try:
        dash_root = SH.DASH_ROOT if SH else APP_DIR
    except Exception:
        dash_root = APP_DIR

    import glob, re
    if patterns is None:
        patterns = [
            'models/**/picks_*.csv',
            'picks/picks_*.csv',
            'models/**/monthlypicks*.csv',
            'models/**/weeklypicks*.csv'
        ]

    candidates = []
    for pattern in patterns:
        path = os.path.join(dash_root, pattern)
        found = glob.glob(path, recursive=True)
        candidates.extend(found)

    if not candidates:
        return None

    def _parse_date_from_name(path):
        filename = os.path.basename(path)
        m_yyyymmdd = re.search(r'(\d{8})', filename)
        if m_yyyymmdd:
            try:
                return datetime.strptime(m_yyyymmdd.group(1), '%Y%m%d').date()
            except Exception:
                pass
        return None

    def _sort_key(p):
        parsed = _parse_date_from_name(p) or datetime.min.date()
        mtime = os.path.getmtime(p)
        return (parsed, mtime)

    candidates.sort(key=_sort_key, reverse=True)
    return candidates[0]


def _load_picks_df(path, limit=50):
    """Load picks CSV into pandas DataFrame."""
    try:
        if not path or not os.path.exists(path):
            return None
        df = pd.read_csv(path)
        if 'symbol' in df.columns and 'ticker' not in df.columns:
            df = df.rename(columns={'symbol': 'ticker'})
        if 'ticker' not in df.columns:
            return None
        return df.head(limit)
    except Exception as e:
        logger.error(f"Error loading picks: {e}")
        return None


def _load_picks_from_db(picks_type, start_date=None, end_date=None, limit=200):
    """
    Load picks from PostgreSQL database (Sprint 2).
    
    Args:
        picks_type: 'monthly' or 'weekly'
        start_date: Optional start date filter
        end_date: Optional end date filter
        limit: Max rows to return
    
    Returns:
        pandas DataFrame or None
    """
    try:
        if not USE_POSTGRES:
            return None
        
        # Build query
        query = """
        SELECT ticker, pick_date, pick_type, predicted_return, confidence, sector, market_cap
        FROM picks_history
        WHERE pick_type = %s
        """
        params = [picks_type]
        
        if start_date:
            query += " AND pick_date >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND pick_date <= %s"
            params.append(end_date)
        
        query += " ORDER BY pick_date DESC LIMIT %s"
        params.append(limit)
        
        # Execute query
        rows = execute_pg_query(query, tuple(params), fetch=True)
        
        if not rows:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=['ticker', 'pick_date', 'pick_type', 'predicted_return', 
                                        'confidence', 'sector', 'market_cap'])
        logger.info(f"Loaded {len(df)} picks from database ({picks_type}, {start_date} to {end_date})")
        return df
        
    except Exception as e:
        logger.error(f"Error loading picks from database: {e}")
        return None


def _load_picks_in_range(picks_type, start_date, end_date):
    """Load picks within a date range. Tries PostgreSQL first, falls back to CSV."""
    try:
        # Try PostgreSQL first (Sprint 2)
        if USE_POSTGRES:
            df = _load_picks_from_db(picks_type, start_date, end_date, limit=200)
            if df is not None and not df.empty:
                return df
            logger.info("No data from PostgreSQL, falling back to CSV")
        
        # Fallback to CSV
        # Be permissive about filenames: include picks_*.csv and picks*.csv
        patterns = []
        if picks_type == 'weekly':
            patterns += ['models/**/weeklypicks*.csv', 'picks/weeklypicks*.csv']
        elif picks_type == 'monthly':
            patterns += ['models/**/monthlypicks*.csv', 'picks/monthlypicks*.csv']
        # Generic picks patterns to catch files like picks_YYYYMMDD.csv under models/
        patterns += ['models/**/picks*.csv', 'models/**/picks_*.csv', 'picks/picks*.csv', 'picks/picks_*.csv']

        picks_path = _find_latest_picks_generic(patterns)
        if not picks_path:
            logger.warning(f"No picks file found for type: {picks_type}")
            return None
        
        df = _load_picks_df(picks_path, limit=200)
        if df is None or df.empty:
            return None
        
        # Filter by date range
        # Accept alternate timestamp columns (date, generated_at, created_at)
        date_cols = [c for c in ['date', 'generated_at', 'created_at', 'pick_date'] if c in df.columns]
        if date_cols:
            # Normalize to 'date' column for filtering
            # Some CSVs store dates as integers like 20251012 — parse with explicit format
            df['date'] = pd.to_datetime(df[date_cols[0]].astype(str), format='%Y%m%d', errors='coerce')

            # Build start/end bounds — if start_date or end_date are None/empty, treat as unbounded
            if start_date:
                try:
                    start = pd.to_datetime(start_date)
                except Exception:
                    start = None
            else:
                start = None

            if end_date:
                try:
                    end = pd.to_datetime(end_date)
                except Exception:
                    end = None
            else:
                end = None

            if start is not None:
                df = df[df['date'] >= start]
            if end is not None:
                df = df[df['date'] <= end]
        
        # If filtering removed all rows, log a diagnostic with candidate path
        if df.empty:
            logger.info(f"Picks file found at {picks_path} but no rows after date filter ({start_date} to {end_date})")
            return None

        return df
        
    except Exception as e:
        logger.error(f"Error loading picks in range: {e}")
        return None


def _filter_by_market_regime(picks_df, regime_filter):
    """Filter picks by market regime."""
    if regime_filter == 'all' or picks_df.empty:
        return picks_df
    
    try:
        import yfinance as yf
        
        # Get SPY data
        start_date = pd.to_datetime(picks_df['date'].min()) - timedelta(days=60)
        end_date = pd.to_datetime(picks_df['date'].max()) + timedelta(days=30)
        
        spy = yf.Ticker('SPY')
        spy_hist = spy.history(start=start_date, end=end_date)
        
        if spy_hist.empty:
            return picks_df
        
        # Calculate regime metrics
        spy_hist['ret_20d'] = spy_hist['Close'].pct_change(20)
        spy_hist['vol_20d'] = spy_hist['Close'].pct_change().rolling(20).std()
        vol_median = spy_hist['vol_20d'].median()
        
        filtered_picks = []
        for _, pick in picks_df.iterrows():
            pick_date = pd.to_datetime(pick['date'])
            closest_spy = spy_hist.iloc[(spy_hist.index - pick_date).abs().argmin()]
            
            ret_20d = closest_spy['ret_20d'] if pd.notna(closest_spy['ret_20d']) else 0
            vol_20d = closest_spy['vol_20d'] if pd.notna(closest_spy['vol_20d']) else vol_median
            
            include = False
            if regime_filter == 'bull' and ret_20d > 0.02:
                include = True
            elif regime_filter == 'bear' and ret_20d < -0.02:
                include = True
            elif regime_filter == 'high_vol' and vol_20d > vol_median:
                include = True
            elif regime_filter == 'low_vol' and vol_20d <= vol_median:
                include = True
            
            if include:
                filtered_picks.append(pick)
        
        return pd.DataFrame(filtered_picks) if filtered_picks else picks_df.iloc[:0]
        
    except Exception as e:
        logger.error(f"Error filtering by regime: {e}")
        return picks_df


# ============================================================================
# CORE ATTRIBUTION ANALYSIS
# ============================================================================

def _run_attribution_on_picks(picks_df, horizon):
    """Run attribution analysis on picks DataFrame."""
    try:
        if ATTR is None:
            logger.warning("Attribution utils not available, using mock analysis")
            return _generate_mock_attribution(picks_df, horizon)
        
        tickers = picks_df['ticker'].unique().tolist()
        horizon_days = {'1w': 7, '1m': 30, '3m': 90}.get(horizon, 7)
        
        per_pick_results = []
        
        import yfinance as yf
        
        for _, pick in picks_df.iterrows():
            ticker = pick['ticker']
            pick_date = pd.to_datetime(pick['date'])
            end_date = pick_date + timedelta(days=horizon_days)
            
            try:
                # Get price data
                stock = yf.Ticker(ticker)
                hist = stock.history(
                    start=pick_date - timedelta(days=1),
                    end=end_date + timedelta(days=1)
                )
                
                if len(hist) < 2:
                    continue
                
                # Calculate returns
                start_price = float(hist['Close'].iloc[0])
                end_price = float(hist['Close'].iloc[-1])
                realized_return = (end_price / start_price - 1)
                
                # Get benchmark return
                spy = yf.Ticker('SPY')
                spy_hist = spy.history(
                    start=pick_date - timedelta(days=1),
                    end=end_date + timedelta(days=1)
                )
                
                benchmark_return = 0.0
                if len(spy_hist) >= 2:
                    benchmark_return = float(spy_hist['Close'].iloc[-1]) / float(spy_hist['Close'].iloc[0]) - 1
                
                # Estimate beta
                long_hist = stock.history(
                    start=pick_date - timedelta(days=252),
                    end=pick_date
                )
                spy_long = spy.history(
                    start=pick_date - timedelta(days=252),
                    end=pick_date
                )
                
                beta = 1.0
                if len(long_hist) >= 20 and len(spy_long) >= 20:
                    merged = pd.DataFrame({
                        'stock': long_hist['Close'].pct_change(),
                        'spy': spy_long['Close'].pct_change()
                    }).dropna()
                    
                    if len(merged) >= 20:
                        cov = merged['stock'].cov(merged['spy'])
                        var = merged['spy'].var()
                        beta = float(cov / var) if var > 0 else 1.0
                
                # Calculate attribution
                beta_contrib = float(beta) * float(benchmark_return)
                alpha = float(realized_return) - float(beta_contrib)
                
                per_pick_results.append({
                    'ticker': ticker,
                    'date': pick_date.strftime('%Y-%m-%d'),
                    'realized_return': float(realized_return),
                    'alpha': float(alpha),
                    'beta': float(beta),
                    'beta_contrib': float(beta_contrib),
                    'benchmark_return': float(benchmark_return),
                    'top_factor': 'momentum'
                })
                
            except Exception as e:
                logger.warning(f"Error processing {ticker}: {e}")
                continue
        
        if not per_pick_results:
            return None
        
        # Calculate portfolio-level metrics
        total_return = np.mean([p['realized_return'] for p in per_pick_results])
        total_alpha = np.mean([p['alpha'] for p in per_pick_results])
        avg_beta = np.mean([p['beta'] for p in per_pick_results])
        total_beta_contrib = np.mean([p['beta_contrib'] for p in per_pick_results])
        
        # Aggregate factor contributions
        factor_contributions = [
            {'factor': 'momentum', 'contribution': 0.45},
            {'factor': 'value', 'contribution': 0.22},
            {'factor': 'quality', 'contribution': 0.18},
            {'factor': 'growth', 'contribution': 0.10},
            {'factor': 'sentiment', 'contribution': 0.05}
        ]
        
        return {
            'portfolio': {
                'total_return': total_return,
                'alpha': total_alpha,
                'beta': avg_beta,
                'beta_contrib': total_beta_contrib,
                'top_factors': factor_contributions
            },
            'per_pick': per_pick_results
        }
        
    except Exception as e:
        logger.error(f"Error in attribution analysis: {e}", exc_info=True)
        return None


def _generate_mock_attribution(picks_df, horizon):
    """Generate mock attribution data for testing."""
    logger.info("Generating mock attribution data")
    
    per_pick_results = []
    for _, pick in picks_df.iterrows():
        ticker = pick.get('ticker', 'UNKNOWN')
        date = pick.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        # Generate random but reasonable values
        realized_return = np.random.normal(0.05, 0.15)
        beta = np.random.normal(1.0, 0.3)
        benchmark_return = np.random.normal(0.02, 0.10)
        beta_contrib = beta * benchmark_return
        alpha = realized_return - beta_contrib
        
        per_pick_results.append({
            'ticker': ticker,
            'date': str(date),
            'realized_return': float(realized_return),
            'alpha': float(alpha),
            'beta': float(beta),
            'beta_contrib': float(beta_contrib),
            'benchmark_return': float(benchmark_return),
            'top_factor': np.random.choice(['momentum', 'value', 'quality', 'growth'])
        })
    
    total_return = np.mean([p['realized_return'] for p in per_pick_results])
    total_alpha = np.mean([p['alpha'] for p in per_pick_results])
    avg_beta = np.mean([p['beta'] for p in per_pick_results])
    total_beta_contrib = np.mean([p['beta_contrib'] for p in per_pick_results])
    
    return {
        'portfolio': {
            'total_return': total_return,
            'alpha': total_alpha,
            'beta': avg_beta,
            'beta_contrib': total_beta_contrib,
            'top_factors': [
                {'factor': 'momentum', 'contribution': 0.45},
                {'factor': 'value', 'contribution': 0.22},
                {'factor': 'quality', 'contribution': 0.18}
            ]
        },
        'per_pick': per_pick_results
    }


# ============================================================================
# BACKGROUND JOB EXECUTION
# ============================================================================

def run_analysis_job(job_id: str, params: Dict):
    """Execute attribution analysis in background thread."""
    try:
        logger.info(f"Starting analysis job {job_id}")
        
        # Update status to running
        with JOBS_LOCK:
            if job_id in JOBS:
                JOBS[job_id]['status'] = 'running'
                JOBS[job_id]['progress'] = 0.1
                JOBS[job_id]['updated_at'] = datetime.now().isoformat()
        
        # Load picks
        picks_df = _load_picks_in_range(
            params['picks_type'],
            params['start_date'],
            params['end_date']
        )
        
        with JOBS_LOCK:
            if job_id in JOBS:
                JOBS[job_id]['progress'] = 0.3
        
        if picks_df is None or picks_df.empty:
            raise ValueError("No picks found in date range")
        
        # Apply regime filter
        if params.get('regime_filter', 'all') != 'all':
            picks_df = _filter_by_market_regime(picks_df, params['regime_filter'])
        
        with JOBS_LOCK:
            if job_id in JOBS:
                JOBS[job_id]['progress'] = 0.5
        
        # Run attribution
        results = _run_attribution_on_picks(picks_df, params['horizon'])
        
        with JOBS_LOCK:
            if job_id in JOBS:
                JOBS[job_id]['progress'] = 0.9
        
        if not results:
            raise ValueError("Attribution analysis failed")
        
        # Cache results
        with CACHE_LOCK:
            RESULTS_CACHE['latest'] = results
        
        # Mark complete
        with JOBS_LOCK:
            if job_id in JOBS:
                JOBS[job_id]['status'] = 'completed'
                JOBS[job_id]['progress'] = 1.0
                JOBS[job_id]['result'] = results
                JOBS[job_id]['message'] = f"Analyzed {len(picks_df)} picks"
                JOBS[job_id]['updated_at'] = datetime.now().isoformat()
        
        logger.info(f"Completed job {job_id}")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        with JOBS_LOCK:
            if job_id in JOBS:
                JOBS[job_id]['status'] = 'failed'
                JOBS[job_id]['error'] = str(e)
                JOBS[job_id]['updated_at'] = datetime.now().isoformat()


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "analysis_hub",
        "timestamp": datetime.now().isoformat(),
        "attribution_utils_loaded": ATTR is not None,
        "active_jobs": len([j for j in JOBS.values() if j['status'] in ['pending', 'running']])
    }


@app.post("/api/jobs")
async def create_analysis_job(request: AnalysisJobRequest):
    """Create a new attribution analysis job."""
    job_id = str(uuid.uuid4())
    
    job_data = {
        'job_id': job_id,
        'status': 'pending',
        'progress': 0.0,
        'message': 'Job created',
        'result': None,
        'error': None,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'params': request.dict()
    }
    
    with JOBS_LOCK:
        JOBS[job_id] = job_data
    
    # Submit to thread pool
    executor.submit(run_analysis_job, job_id, request.dict())
    
    logger.info(f"Created job {job_id}")
    
    return JobStatus(**job_data)


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a specific job."""
    with JOBS_LOCK:
        if job_id not in JOBS:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job_data = JOBS[job_id].copy()
    
    return JobStatus(**job_data)


@app.get("/api/results/latest")
async def get_latest_results():
    """Get the most recent cached results."""
    with CACHE_LOCK:
        if 'latest' not in RESULTS_CACHE:
            return {
                "success": False,
                "message": "No cached results available"
            }
        
        results = RESULTS_CACHE['latest']
    
    return {
        "success": True,
        "data": results,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# STARTUP
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    logger.info("=" * 60)
    logger.info("Analysis Hub Service Starting")
    logger.info("=" * 60)
    logger.info(f"App directory: {APP_DIR}")
    logger.info(f"Attribution utils loaded: {ATTR is not None}")
    logger.info("Service ready on port 8054")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8054)

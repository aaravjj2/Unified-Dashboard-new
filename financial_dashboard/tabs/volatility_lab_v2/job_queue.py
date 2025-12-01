"""
Volatility Lab - Job Queue System
=================================

Agent-1A: File-backed job queue for async IV surface computation.

Architecture:
- File-backed queue using jobs.json (atomic writes)
- Job states: pending, running, completed, failed
- Job metadata: id, ticker, expiry, strike_range, created_at, status, result
- Thread-safe operations (fcntl file locking on Linux)

Queue Operations:
- enqueue_job(params): Add new job to queue
- get_job_status(job_id): Check job state and result
- process_next_job(): Worker function to process pending jobs
- cleanup_old_jobs(max_age_hours=24): Remove completed/failed jobs

Storage:
- Path: reports/vol_lab_rebuild_v2/diagnostics/jobs.json
- Format: JSON array of job objects
- Backup: jobs.json.bak created on each write

Design Principles:
- Fail-safe: Always backup before write
- Atomic: Use temp file + rename pattern
- Observable: Each job includes full audit trail
- Deterministic: Job IDs are timestamp-based (sortable)
"""

import logging
import os
import json
import fcntl
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Queue configuration
QUEUE_FILE = os.path.join(
    os.path.dirname(__file__),
    '../../../reports/vol_lab_rebuild_v2/diagnostics/jobs.json'
)
QUEUE_BACKUP = QUEUE_FILE + '.bak'

# Job states
JOB_STATE_PENDING = 'pending'
JOB_STATE_RUNNING = 'running'
JOB_STATE_COMPLETED = 'completed'
JOB_STATE_FAILED = 'failed'


class JobQueueError(Exception):
    """Custom exception for job queue operations"""
    pass


def _ensure_queue_file():
    """Create queue file and parent directories if not exist"""
    queue_path = Path(QUEUE_FILE)
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not queue_path.exists():
        with open(QUEUE_FILE, 'w') as f:
            json.dump([], f)
        logger.info(f"✓ Initialized job queue: {QUEUE_FILE}")


def _read_queue_locked(lock_timeout=5) -> List[Dict]:
    """
    Read queue with file lock (thread-safe)
    
    Args:
        lock_timeout: Maximum seconds to wait for lock
    
    Returns:
        List of job dictionaries
    
    Raises:
        JobQueueError: If lock timeout or file read fails
    """
    _ensure_queue_file()
    
    start_time = time.time()
    while time.time() - start_time < lock_timeout:
        try:
            with open(QUEUE_FILE, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for read
                try:
                    jobs = json.load(f)
                    return jobs
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Release lock
        except IOError:
            time.sleep(0.1)
            continue
    
    raise JobQueueError(f"Lock timeout after {lock_timeout}s")


def _write_queue_locked(jobs: List[Dict], lock_timeout=5):
    """
    Write queue with file lock and backup (thread-safe, atomic)
    
    Args:
        jobs: List of job dictionaries to write
        lock_timeout: Maximum seconds to wait for lock
    
    Raises:
        JobQueueError: If lock timeout or file write fails
    """
    _ensure_queue_file()
    
    # Backup existing queue
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, 'r') as src:
            with open(QUEUE_BACKUP, 'w') as dst:
                dst.write(src.read())
    
    # Atomic write using temp file + rename
    temp_file = QUEUE_FILE + '.tmp'
    start_time = time.time()
    
    while time.time() - start_time < lock_timeout:
        try:
            with open(temp_file, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock for write
                try:
                    json.dump(jobs, f, indent=2)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Release lock
            
            # Atomic rename
            os.rename(temp_file, QUEUE_FILE)
            return
            
        except IOError:
            time.sleep(0.1)
            continue
    
    raise JobQueueError(f"Lock timeout after {lock_timeout}s")


def enqueue_job(ticker: str, expiry: str = 'auto', strike_range: str = '±10%', 
                priority: int = 0, metadata: Optional[Dict] = None) -> str:
    """
    Add new IV surface computation job to queue
    
    Args:
        ticker: Stock ticker symbol
        expiry: Expiry date or 'auto'
        strike_range: Strike range specification (e.g., '±10%')
        priority: Job priority (higher = processed first)
        metadata: Optional additional metadata
    
    Returns:
        Job ID (timestamp-based UUID)
    
    Example:
        >>> job_id = enqueue_job('SPY', '2024-12-20', '±5%', priority=1)
        >>> print(job_id)
        '20241127_143022_a7f3c8d4'
    """
    job_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    job = {
        'id': job_id,
        'ticker': ticker.upper(),
        'expiry': expiry,
        'strike_range': strike_range,
        'priority': priority,
        'created_at': datetime.now().isoformat(),
        'status': JOB_STATE_PENDING,
        'result': None,
        'error': None,
        'metadata': metadata or {}
    }
    
    jobs = _read_queue_locked()
    jobs.append(job)
    
    # Sort by priority (descending), then created_at (ascending)
    jobs.sort(key=lambda x: (-x['priority'], x['created_at']))
    
    _write_queue_locked(jobs)
    
    logger.info(f"✓ Enqueued job {job_id}: {ticker} {expiry} {strike_range} (priority={priority})")
    return job_id


def get_job_status(job_id: str) -> Optional[Dict]:
    """
    Get current status and result of a job
    
    Args:
        job_id: Job ID returned by enqueue_job()
    
    Returns:
        Job dictionary with status, result, error fields, or None if not found
    
    Example:
        >>> status = get_job_status('20241127_143022_a7f3c8d4')
        >>> print(status['status'])  # 'completed'
        >>> print(status['result'])  # {iv_grid: [...], diagnostics: {...}}
    """
    jobs = _read_queue_locked()
    
    for job in jobs:
        if job['id'] == job_id:
            return job
    
    logger.warning(f"Job {job_id} not found in queue")
    return None


def get_queue_summary() -> Dict[str, Any]:
    """
    Get queue statistics and summary
    
    Returns:
        Dictionary with total, pending, running, completed, failed counts
    
    Example:
        >>> summary = get_queue_summary()
        >>> print(summary)
        {'total': 10, 'pending': 2, 'running': 1, 'completed': 6, 'failed': 1}
    """
    jobs = _read_queue_locked()
    
    summary = {
        'total': len(jobs),
        'pending': sum(1 for j in jobs if j['status'] == JOB_STATE_PENDING),
        'running': sum(1 for j in jobs if j['status'] == JOB_STATE_RUNNING),
        'completed': sum(1 for j in jobs if j['status'] == JOB_STATE_COMPLETED),
        'failed': sum(1 for j in jobs if j['status'] == JOB_STATE_FAILED),
    }
    
    return summary


def process_next_job() -> Optional[str]:
    """
    Worker function to process next pending job
    
    Workflow:
    1. Lock queue and find first pending job
    2. Mark job as running
    3. Release lock and execute job (POST /api/volsurface/compute)
    4. Lock queue again and update job with result/error
    5. Return job ID
    
    Returns:
        Job ID if job was processed, None if queue empty
    
    Note:
        This is a synchronous worker function. For production, use celery or rq.
    """
    jobs = _read_queue_locked()
    
    # Find first pending job
    pending_job = next((j for j in jobs if j['status'] == JOB_STATE_PENDING), None)
    if not pending_job:
        logger.debug("No pending jobs in queue")
        return None
    
    job_id = pending_job['id']
    
    # Mark as running
    for job in jobs:
        if job['id'] == job_id:
            job['status'] = JOB_STATE_RUNNING
            job['started_at'] = datetime.now().isoformat()
            break
    
    _write_queue_locked(jobs)
    logger.info(f"Processing job {job_id}: {pending_job['ticker']} {pending_job['expiry']}")
    
    # Execute job (call volsurface API)
    try:
        import requests
        api_base = os.getenv('VOLLAB_API_BASE', 'http://localhost:8090/api/volsurface')
        
        payload = {
            'ticker': pending_job['ticker'],
            'expiry': pending_job['expiry'],
            'strike_range': pending_job['strike_range'],
            'mode': 'deterministic' if os.getenv('VOLLAB_DETERMINISTIC', '0') == '1' else 'live'
        }
        
        response = requests.post(f"{api_base}/compute", json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        
        # Update job as completed
        jobs = _read_queue_locked()
        for job in jobs:
            if job['id'] == job_id:
                job['status'] = JOB_STATE_COMPLETED
                job['completed_at'] = datetime.now().isoformat()
                job['result'] = result
                break
        
        _write_queue_locked(jobs)
        logger.info(f"✓ Job {job_id} completed successfully")
        return job_id
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        
        # Update job as failed
        jobs = _read_queue_locked()
        for job in jobs:
            if job['id'] == job_id:
                job['status'] = JOB_STATE_FAILED
                job['completed_at'] = datetime.now().isoformat()
                job['error'] = str(e)
                break
        
        _write_queue_locked(jobs)
        return job_id


def cleanup_old_jobs(max_age_hours: int = 24) -> int:
    """
    Remove completed and failed jobs older than max_age_hours
    
    Args:
        max_age_hours: Maximum age in hours for completed/failed jobs
    
    Returns:
        Number of jobs removed
    
    Example:
        >>> removed_count = cleanup_old_jobs(max_age_hours=48)
        >>> print(f"Removed {removed_count} old jobs")
    """
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    
    jobs = _read_queue_locked()
    original_count = len(jobs)
    
    # Filter out old completed/failed jobs
    jobs = [
        j for j in jobs
        if not (
            (j['status'] in [JOB_STATE_COMPLETED, JOB_STATE_FAILED]) and
            (datetime.fromisoformat(j.get('completed_at', datetime.now().isoformat())) < cutoff_time)
        )
    ]
    
    removed_count = original_count - len(jobs)
    
    if removed_count > 0:
        _write_queue_locked(jobs)
        logger.info(f"✓ Cleaned up {removed_count} old jobs (max_age={max_age_hours}h)")
    
    return removed_count


# Export public API
__all__ = [
    'enqueue_job',
    'get_job_status',
    'get_queue_summary',
    'process_next_job',
    'cleanup_old_jobs',
    'JOB_STATE_PENDING',
    'JOB_STATE_RUNNING',
    'JOB_STATE_COMPLETED',
    'JOB_STATE_FAILED',
]

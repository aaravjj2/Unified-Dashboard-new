"""
Job locking and status tracking for dashboard pipelines.

Provides atomic file-based locks to prevent concurrent execution of resource-intensive
jobs (monthly picks generation, weekly picks, market trends analysis).

Status tracking uses diskcache for persistent state across restarts.
"""

import os
import time
import json
import fcntl
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import logging

try:
    from diskcache import Cache
except ImportError:
    Cache = None  # Fallback if diskcache not installed

logger = logging.getLogger(__name__)

# Global cache directory
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cache')
LOCKS_DIR = os.path.join(CACHE_DIR, 'locks')

# Ensure directories exist
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(LOCKS_DIR, exist_ok=True)

# Status cache (persistent)
_status_cache = None

def get_status_cache():
    """Get or create the status cache."""
    global _status_cache
    if _status_cache is None and Cache is not None:
        _status_cache = Cache(os.path.join(CACHE_DIR, 'job_status'))
    return _status_cache


class LockAcquisitionError(Exception):
    """Raised when a lock cannot be acquired."""
    pass


class JobLock:
    """
    Context manager for atomic job locking using file-based locks.
    
    Uses fcntl for POSIX file locking (atomic and process-safe).
    Stores lock metadata as JSON for debugging.
    
    Example:
        with JobLock('monthly_picks'):
            # Do work that shouldn't run concurrently
            generate_monthly_picks()
    """
    
    def __init__(
        self, 
        name: str, 
        timeout: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize job lock.
        
        Args:
            name: Unique lock name (e.g. 'monthly_picks', 'weekly_picks', 'market_trends')
            timeout: Seconds to wait for lock (0 = fail immediately if locked)
            metadata: Optional dict to store with lock (e.g. job_id, start_time, params)
        """
        self.name = name
        self.timeout = timeout
        self.metadata = metadata or {}
        self.lock_file = os.path.join(LOCKS_DIR, f'{name}.lock')
        self.lock_fd = None
        self.acquired = False
        
    def __enter__(self):
        """Acquire the lock."""
        return self.acquire()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release the lock."""
        self.release()
        return False  # Don't suppress exceptions
    
    def acquire(self) -> 'JobLock':
        """
        Acquire the lock with optional timeout.
        
        Returns:
            self
            
        Raises:
            LockAcquisitionError: If lock cannot be acquired within timeout
        """
        start_time = time.time()
        
        while True:
            try:
                # Open/create lock file
                self.lock_fd = open(self.lock_file, 'w')
                
                # Try to acquire exclusive lock
                if self.timeout == 0:
                    # Non-blocking
                    fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                else:
                    # Blocking with timeout
                    elapsed = time.time() - start_time
                    if elapsed >= self.timeout:
                        raise LockAcquisitionError(f"Could not acquire lock '{self.name}' within {self.timeout}s")
                    
                    try:
                        fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except (IOError, OSError):
                        # Lock held by another process, wait and retry
                        time.sleep(0.1)
                        continue
                
                # Lock acquired! Write metadata
                lock_data = {
                    'name': self.name,
                    'acquired_at': datetime.utcnow().isoformat(),
                    'pid': os.getpid(),
                    **self.metadata
                }
                
                self.lock_fd.write(json.dumps(lock_data, indent=2))
                self.lock_fd.flush()
                
                self.acquired = True
                logger.info(f"Acquired lock: {self.name}")
                
                # Update status cache
                self._update_status('running', lock_data)
                
                return self
                
            except (IOError, OSError) as e:
                if self.timeout == 0:
                    # Non-blocking mode, fail immediately
                    raise LockAcquisitionError(f"Lock '{self.name}' is already held") from e
                
                # Check timeout
                if time.time() - start_time >= self.timeout:
                    raise LockAcquisitionError(f"Could not acquire lock '{self.name}' within {self.timeout}s") from e
                
                # Wait and retry
                time.sleep(0.1)
    
    def release(self):
        """Release the lock and clean up."""
        if not self.acquired:
            return
        
        try:
            if self.lock_fd:
                # Release file lock
                fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
                self.lock_fd.close()
                self.lock_fd = None
            
            # Remove lock file
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
            
            logger.info(f"Released lock: {self.name}")
            
            # Update status cache
            self._update_status('completed', {'completed_at': datetime.utcnow().isoformat()})
            
        except Exception as e:
            logger.error(f"Error releasing lock {self.name}: {e}")
        finally:
            self.acquired = False
    
    def _update_status(self, status: str, data: Dict[str, Any]):
        """Update job status in cache."""
        cache = get_status_cache()
        if cache is not None:
            status_key = f'job_status:{self.name}'
            status_data = {
                'status': status,
                'updated_at': datetime.utcnow().isoformat(),
                **data
            }
            cache.set(status_key, status_data, expire=86400)  # Keep for 24h
    
    def is_locked(self) -> bool:
        """Check if lock file exists (doesn't guarantee lock is held)."""
        return os.path.exists(self.lock_file)


def acquire_lock(name: str, timeout: float = 0.0, metadata: Optional[Dict[str, Any]] = None) -> JobLock:
    """
    Convenience function to acquire a lock.
    
    Args:
        name: Lock name
        timeout: Seconds to wait (0 = fail immediately)
        metadata: Optional metadata dict
        
    Returns:
        JobLock instance (acquired)
        
    Raises:
        LockAcquisitionError: If lock cannot be acquired
    """
    lock = JobLock(name, timeout=timeout, metadata=metadata)
    return lock.acquire()


def release_lock(lock: JobLock):
    """
    Convenience function to release a lock.
    
    Args:
        lock: JobLock instance to release
    """
    if lock:
        lock.release()


def is_job_running(name: str) -> bool:
    """
    Check if a job is currently running (lock file exists).
    
    Args:
        name: Job name
        
    Returns:
        True if job is running
    """
    lock_file = os.path.join(LOCKS_DIR, f'{name}.lock')
    return os.path.exists(lock_file)


def get_job_status(name: str) -> Optional[Dict[str, Any]]:
    """
    Get job status from cache.
    
    Args:
        name: Job name
        
    Returns:
        Status dict or None if not found
    """
    cache = get_status_cache()
    if cache is not None:
        return cache.get(f'job_status:{name}')
    return None


def get_all_job_statuses() -> Dict[str, Dict[str, Any]]:
    """
    Get all job statuses from cache.
    
    Returns:
        Dict mapping job names to status dicts
    """
    cache = get_status_cache()
    if cache is None:
        return {}
    
    result = {}
    for key in cache:
        if isinstance(key, str) and key.startswith('job_status:'):
            job_name = key.replace('job_status:', '')
            result[job_name] = cache.get(key)
    
    return result


def clear_stale_locks(max_age_seconds: int = 3600):
    """
    Clear lock files older than max_age_seconds.
    
    Useful for cleaning up after crashes or unexpected terminations.
    
    Args:
        max_age_seconds: Maximum age in seconds (default 1 hour)
    """
    now = time.time()
    cleared = []
    
    for filename in os.listdir(LOCKS_DIR):
        if not filename.endswith('.lock'):
            continue
        
        lock_path = os.path.join(LOCKS_DIR, filename)
        try:
            # Check file age
            file_age = now - os.path.getmtime(lock_path)
            
            if file_age > max_age_seconds:
                # Try to read lock data for logging
                try:
                    with open(lock_path, 'r') as f:
                        lock_data = json.load(f)
                        job_name = lock_data.get('name', filename.replace('.lock', ''))
                except:
                    job_name = filename.replace('.lock', '')
                
                # Remove stale lock
                os.remove(lock_path)
                cleared.append(job_name)
                logger.warning(f"Cleared stale lock: {job_name} (age: {file_age:.0f}s)")
        
        except Exception as e:
            logger.error(f"Error checking lock file {filename}: {e}")
    
    return cleared


if __name__ == '__main__':
    # Self-test
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    print("Testing JobLock...")
    
    # Test 1: Acquire and release
    print("\nTest 1: Basic acquire/release")
    with JobLock('test_job', metadata={'test': True}):
        print(f"  Lock acquired. Running job...")
        print(f"  Lock file exists: {is_job_running('test_job')}")
        time.sleep(0.5)
    
    print(f"  Lock released. File exists: {is_job_running('test_job')}")
    
    # Test 2: Lock conflict
    print("\nTest 2: Lock conflict detection")
    lock1 = acquire_lock('test_job2')
    print(f"  Lock1 acquired")
    
    try:
        lock2 = acquire_lock('test_job2', timeout=0.5)
        print(f"  ERROR: Lock2 should have failed!")
        sys.exit(1)
    except LockAcquisitionError as e:
        print(f"  ✓ Lock2 failed as expected: {e}")
    
    release_lock(lock1)
    print(f"  Lock1 released")
    
    # Test 3: Status tracking
    print("\nTest 3: Status tracking")
    with JobLock('test_job3', metadata={'run_id': '12345'}):
        status = get_job_status('test_job3')
        print(f"  Job status during run: {status}")
    
    status = get_job_status('test_job3')
    print(f"  Job status after completion: {status}")
    
    # Test 4: Clear stale locks
    print("\nTest 4: Clear stale locks")
    # Create a fake old lock
    old_lock_path = os.path.join(LOCKS_DIR, 'stale_job.lock')
    with open(old_lock_path, 'w') as f:
        json.dump({'name': 'stale_job', 'created': 'long_ago'}, f)
    
    # Make it old
    old_time = time.time() - 7200  # 2 hours ago
    os.utime(old_lock_path, (old_time, old_time))
    
    cleared = clear_stale_locks(max_age_seconds=3600)
    print(f"  Cleared stale locks: {cleared}")
    
    print("\n✓ All tests passed!")

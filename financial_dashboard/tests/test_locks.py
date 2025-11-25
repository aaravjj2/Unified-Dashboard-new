"""
Unit tests for utils/locks.py

Tests file locking mechanisms for concurrent pipeline execution.
"""
import pytest
import os
import time
from pathlib import Path
from utils import locks


class TestFileLocks:
    """Test file locking utilities."""
    
    def test_acquire_lock_creates_file(self, tmp_path):
        """Test that acquiring a lock creates a lock file."""
        # Use unique lock name instead of full path
        lock_name = f'test_lock_{os.getpid()}'
        
        lock = locks.acquire_lock(lock_name)
        
        assert lock is not None
        assert isinstance(lock, locks.JobLock)
        assert lock.acquired is True
        
        # Cleanup
        locks.release_lock(lock)
    
    def test_cannot_acquire_locked_file(self, tmp_path):
        """Test that a locked file cannot be acquired again."""
        lock_name = f'test_lock2_{os.getpid()}'
        
        # First acquisition should succeed
        lock1 = locks.acquire_lock(lock_name)
        assert lock1 is not None
        assert lock1.acquired is True
        
        # Second acquisition should fail with timeout 0
        with pytest.raises(locks.LockAcquisitionError):
            lock2 = locks.acquire_lock(lock_name, timeout=0)
        
        # Cleanup
        locks.release_lock(lock1)
    
    def test_release_lock_removes_file(self, tmp_path):
        """Test that releasing a lock removes the lock file."""
        lock_name = f'test_lock3_{os.getpid()}'
        
        lock = locks.acquire_lock(lock_name)
        assert locks.is_job_running(lock_name)
        
        locks.release_lock(lock)
        assert not locks.is_job_running(lock_name)
    
    def test_lock_context_manager(self, tmp_path):
        """Test lock as context manager."""
        lock_name = f'test_lock4_{os.getpid()}'
        
        with locks.JobLock(lock_name):
            assert locks.is_job_running(lock_name)
        
        # Lock should be released after context
        assert not locks.is_job_running(lock_name)
    
    def test_stale_lock_handling(self, tmp_path):
        """Test handling of stale locks using clear_stale_locks."""
        lock_name = f'test_stale_{os.getpid()}'
        lock_file = os.path.join(locks.LOCKS_DIR, f'{lock_name}.lock')
        
        # Create a stale lock file
        os.makedirs(locks.LOCKS_DIR, exist_ok=True)
        with open(lock_file, 'w') as f:
            f.write(f'{{"name": "{lock_name}", "pid": {os.getpid()}}}')
        
        # Modify timestamp to make it old
        old_time = time.time() - 7200  # 2 hours ago
        os.utime(lock_file, (old_time, old_time))
        
        # Clear stale locks
        cleared = locks.clear_stale_locks(max_age_seconds=3600)
        assert lock_name in cleared or not os.path.exists(lock_file)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

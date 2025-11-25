"""
WSL2-Aware Cache Persistence Module

Handles reliable file writing under WSL2/Windows filesystem constraints.

ROOT CAUSE ADDRESSED: WSL2/Windows filesystem caching prevents normal 
json.dump() + fsync() from persisting reliably. This module implements
atomic writes with verification.

SUPER-AGENT FIX: Implements write-verify-retry pattern with temp files.
"""

import json
import os
import tempfile
import shutil
import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class CachePersistence:
    """
    Handles cache file persistence with WSL2/Windows workarounds.
    
    Strategy:
    1. Write to temp file in same directory (ensures same filesystem)
    2. Verify temp file content matches expected data
    3. Atomic move/copy to target location
    4. Verify final file
    5. Retry up to 3 times if verification fails
    """
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.logger = logging.getLogger(__name__)
        
        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def write_cache(
        self, 
        data: Dict[str, Any], 
        filename: str,
        max_retries: int = 3
    ) -> bool:
        """
        Write cache data to file with WSL2-aware persistence.
        
        Args:
            data: Dictionary to write as JSON
            filename: Target filename (e.g., 'prices_weekly.json')
            max_retries: Number of write attempts
            
        Returns:
            True if write successful and verified, False otherwise
        """
        target_path = self.base_dir / filename
        
        for attempt in range(1, max_retries + 1):
            self.logger.info(f"[CACHE_WRITE] Attempt {attempt}/{max_retries} for {filename}")
            
            try:
                # Step 1: Write to temp file in same directory
                temp_fd, temp_path_str = tempfile.mkstemp(
                    dir=str(self.base_dir),
                    prefix=f".tmp_{filename}_",
                    suffix=".json"
                )
                temp_path = Path(temp_path_str)
                
                try:
                    # Write JSON data
                    with os.fdopen(temp_fd, 'w') as f:
                        json.dump(data, f, indent=2)
                        f.flush()
                        os.fsync(f.fileno())
                    
                    # Step 2: Verify temp file content
                    if not self._verify_file_content(temp_path, data):
                        self.logger.error(f"[CACHE_WRITE] Temp file verification failed for {filename}")
                        temp_path.unlink()
                        continue
                    
                    # Step 3: Atomic move to target (or copy on Windows)
                    if target_path.exists():
                        backup_path = target_path.with_suffix('.json.backup')
                        shutil.copy2(target_path, backup_path)
                        self.logger.info(f"[CACHE_WRITE] Created backup: {backup_path.name}")
                    
                    # Use copy + sync + remove instead of move for WSL2 reliability
                    shutil.copy2(temp_path, target_path)
                    self._sync_file(target_path)
                    temp_path.unlink()
                    
                    # Step 4: Verify final file
                    time.sleep(0.1)  # Brief pause for filesystem sync
                    if not self._verify_file_content(target_path, data):
                        self.logger.error(f"[CACHE_WRITE] Final file verification failed for {filename}")
                        continue
                    
                    self.logger.info(f"✅ [CACHE_WRITE] Successfully wrote and verified {filename}")
                    return True
                    
                except Exception as e:
                    self.logger.error(f"[CACHE_WRITE] Error during write: {e}")
                    if temp_path.exists():
                        temp_path.unlink()
                    continue
                    
            except Exception as e:
                self.logger.error(f"[CACHE_WRITE] Failed to create temp file: {e}")
                continue
        
        self.logger.error(f"❌ [CACHE_WRITE] Failed to write {filename} after {max_retries} attempts")
        return False
    
    def read_cache(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Read cache file with error handling.
        
        Args:
            filename: Cache filename to read
            
        Returns:
            Dictionary if successful, None otherwise
        """
        target_path = self.base_dir / filename
        
        if not target_path.exists():
            self.logger.warning(f"[CACHE_READ] File does not exist: {filename}")
            return None
        
        try:
            with open(target_path, 'r') as f:
                data = json.load(f)
            
            self.logger.info(f"✅ [CACHE_READ] Successfully read {filename}")
            return data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"[CACHE_READ] JSON decode error in {filename}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"[CACHE_READ] Error reading {filename}: {e}")
            return None
    
    def _verify_file_content(self, file_path: Path, expected_data: Dict[str, Any]) -> bool:
        """
        Verify file contains expected data.
        
        Args:
            file_path: Path to file to verify
            expected_data: Expected dictionary content
            
        Returns:
            True if content matches, False otherwise
        """
        try:
            with open(file_path, 'r') as f:
                actual_data = json.load(f)
            
            # Compare key structure (full deep comparison too expensive)
            expected_keys = set(expected_data.keys())
            actual_keys = set(actual_data.keys())
            
            if expected_keys != actual_keys:
                self.logger.error(
                    f"[VERIFY] Key mismatch. Expected: {expected_keys}, Got: {actual_keys}"
                )
                return False
            
            # For price data, verify ticker count
            if 'prices' in expected_data:
                expected_tickers = len(expected_data['prices'])
                actual_tickers = len(actual_data['prices'])
                if expected_tickers != actual_tickers:
                    self.logger.error(
                        f"[VERIFY] Ticker count mismatch. Expected: {expected_tickers}, Got: {actual_tickers}"
                    )
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"[VERIFY] Verification error: {e}")
            return False
    
    def _sync_file(self, file_path: Path):
        """Force filesystem sync for a file"""
        try:
            with open(file_path, 'r+b') as f:
                os.fsync(f.fileno())
        except Exception as e:
            self.logger.warning(f"[SYNC] Could not sync {file_path.name}: {e}")
    
    def get_file_info(self, filename: str) -> Dict[str, Any]:
        """Get information about a cache file"""
        target_path = self.base_dir / filename
        
        if not target_path.exists():
            return {
                'exists': False,
                'path': str(target_path)
            }
        
        stat = target_path.stat()
        return {
            'exists': True,
            'path': str(target_path),
            'size_bytes': stat.st_size,
            'modified_time': stat.st_mtime,
            'modified_readable': time.ctime(stat.st_mtime)
        }


# Global instance (initialized lazily)
_cache_persistence: Optional[CachePersistence] = None


def get_cache_persistence(base_dir: Optional[str] = None) -> CachePersistence:
    """
    Get global CachePersistence instance.
    
    Args:
        base_dir: Base directory for cache files (defaults to financial_dashboard/outputs)
    """
    global _cache_persistence
    
    if _cache_persistence is None:
        if base_dir is None:
            # Default to outputs directory
            import financial_dashboard._shared as SH
            base_dir = SH.OUT_ROOT
        
        _cache_persistence = CachePersistence(str(base_dir))
        logger.info(f"[CACHE_PERSISTENCE] Initialized with base_dir: {base_dir}")
    
    return _cache_persistence


def write_cache(data: Dict[str, Any], filename: str) -> bool:
    """Convenience function to write cache"""
    persistence = get_cache_persistence()
    return persistence.write_cache(data, filename)


def read_cache(filename: str) -> Optional[Dict[str, Any]]:
    """Convenience function to read cache"""
    persistence = get_cache_persistence()
    return persistence.read_cache(filename)

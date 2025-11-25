"""
Sync Manifest Utility for Cross-Tab Data Synchronization.

This module provides lightweight timestamp tracking for cross-tab analytics coordination.
Used by Portfolio and Market Trends tabs to detect stale data and trigger refreshes.

Schema:
{
    "market_trends": {
        "last_updated": "2025-10-23T20:30:00.123456",
        "job_id": "job_1761249972035",
        "tickers": ["AAPL", "MSFT", "GOOGL"],
        "status": "completed"
    },
    "portfolio": {
        "last_synced_with_trends": "2025-10-23T20:31:00.456789",
        "dependent_on_job": "job_1761249972035",
        "ticker_count": 15
    }
}
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Manifest file location in cache directory
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cache')
MANIFEST_PATH = os.path.join(CACHE_DIR, 'sync_manifest.json')

# Ensure cache directory exists
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)


def read_sync_manifest() -> Dict[str, Any]:
    """
    Read the sync manifest file.
    
    Returns:
        Dict with tab names as keys, metadata dicts as values.
        Empty dict if file doesn't exist or is corrupted.
    """
    try:
        if os.path.exists(MANIFEST_PATH):
            with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
                logger.debug(f"Loaded sync manifest: {len(manifest)} tabs tracked")
                return manifest
        else:
            logger.debug("Sync manifest file does not exist, returning empty manifest")
            return {}
    except json.JSONDecodeError as e:
        logger.error(f"Sync manifest JSON corrupted: {e}")
        return {}
    except Exception as e:
        logger.exception(f"Error reading sync manifest: {e}")
        return {}


def write_sync_timestamp(
    tab_name: str,
    job_id: Optional[str] = None,
    status: str = "completed",
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Update sync manifest with latest timestamp for a tab.
    
    Args:
        tab_name: Name of the tab ("market_trends", "portfolio", etc.)
        job_id: Background job ID that produced the data
        status: Job status ("running", "completed", "failed")
        metadata: Additional metadata (tickers, row count, etc.)
        
    Returns:
        True if write succeeded, False otherwise
        
    Example:
        write_sync_timestamp("market_trends", "job_123", metadata={"tickers": ["AAPL", "MSFT"]})
    """
    try:
        # Load existing manifest
        manifest = read_sync_manifest()
        
        # Create/update entry for this tab
        tab_data = manifest.get(tab_name, {})
        tab_data['last_updated'] = datetime.now(timezone.utc).isoformat()
        
        if job_id:
            tab_data['job_id'] = job_id
        
        tab_data['status'] = status
        
        # Merge additional metadata
        if metadata:
            tab_data.update(metadata)
        
        manifest[tab_name] = tab_data
        
        # Write atomically using temp file
        temp_path = MANIFEST_PATH + '.tmp'
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        
        # Atomic replace
        try:
            os.replace(temp_path, MANIFEST_PATH)
        except Exception:
            # Fallback for systems without atomic replace
            import shutil
            shutil.copy2(temp_path, MANIFEST_PATH)
            os.remove(temp_path)
        
        logger.info(f"✅ Sync manifest updated: {tab_name} @ {tab_data['last_updated'][:19]}")
        return True
        
    except Exception as e:
        logger.exception(f"Failed to write sync manifest for {tab_name}: {e}")
        return False


def get_tab_metadata(tab_name: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata for a specific tab from sync manifest.
    
    Args:
        tab_name: Name of the tab to query
        
    Returns:
        Dict with tab metadata or None if not found
        
    Example:
        metadata = get_tab_metadata("market_trends")
        if metadata:
            job_id = metadata.get('job_id')
            last_updated = metadata.get('last_updated')
    """
    manifest = read_sync_manifest()
    return manifest.get(tab_name)


def is_data_stale(
    tab_name: str,
    max_age_seconds: int = 14400  # 4 hours default
) -> bool:
    """
    Check if a tab's data is stale based on last_updated timestamp.
    
    Args:
        tab_name: Name of the tab to check
        max_age_seconds: Maximum age in seconds before considered stale
        
    Returns:
        True if data is stale (older than max_age_seconds) or missing
        False if data is fresh
        
    Example:
        if is_data_stale("market_trends", max_age_seconds=3600):  # 1 hour
            # Trigger refresh
            pass
    """
    try:
        metadata = get_tab_metadata(tab_name)
        
        if not metadata:
            logger.info(f"⚠️  {tab_name} has no sync metadata - considered stale")
            return True
        
        last_updated_str = metadata.get('last_updated')
        if not last_updated_str:
            logger.warning(f"⚠️  {tab_name} metadata missing last_updated field")
            return True
        
        # Parse timestamp
        try:
            last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
        except ValueError:
            # Try legacy format without timezone
            last_updated = datetime.fromisoformat(last_updated_str)
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)
        
        # Calculate age
        now = datetime.now(timezone.utc)
        age_seconds = (now - last_updated).total_seconds()
        
        is_stale = age_seconds > max_age_seconds
        
        if is_stale:
            logger.info(f"⏰ {tab_name} data is STALE (age: {int(age_seconds)}s > max: {max_age_seconds}s)")
        else:
            logger.debug(f"✅ {tab_name} data is FRESH (age: {int(age_seconds)}s)")
        
        return is_stale
        
    except Exception as e:
        logger.exception(f"Error checking staleness for {tab_name}: {e}")
        # Fail safe: consider stale if error occurs
        return True


def mark_dependency(
    dependent_tab: str,
    source_tab: str,
    source_job_id: Optional[str] = None
) -> bool:
    """
    Mark that one tab has synchronized with data from another tab.
    
    Args:
        dependent_tab: Tab that consumed the data (e.g., "portfolio")
        source_tab: Tab that produced the data (e.g., "market_trends")
        source_job_id: Optional job ID from source tab
        
    Returns:
        True if successfully marked, False otherwise
        
    Example:
        # Portfolio just loaded Market Trends signals
        mark_dependency("portfolio", "market_trends", source_job_id="job_123")
    """
    try:
        manifest = read_sync_manifest()
        
        # Update dependent tab's metadata
        dep_data = manifest.get(dependent_tab, {})
        dep_data[f'last_synced_with_{source_tab}'] = datetime.now(timezone.utc).isoformat()
        
        if source_job_id:
            dep_data['dependent_on_job'] = source_job_id
        
        manifest[dependent_tab] = dep_data
        
        # Write back
        temp_path = MANIFEST_PATH + '.tmp'
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        
        os.replace(temp_path, MANIFEST_PATH)
        
        logger.info(f"✅ Dependency marked: {dependent_tab} synced with {source_tab}")
        return True
        
    except Exception as e:
        logger.exception(f"Failed to mark dependency {dependent_tab} → {source_tab}: {e}")
        return False


def get_time_since_update(tab_name: str) -> Optional[timedelta]:
    """
    Get time elapsed since tab was last updated.
    
    Args:
        tab_name: Name of the tab to check
        
    Returns:
        timedelta object or None if no update timestamp found
        
    Example:
        age = get_time_since_update("market_trends")
        if age and age.total_seconds() > 3600:
            print("Data is over 1 hour old")
    """
    try:
        metadata = get_tab_metadata(tab_name)
        if not metadata:
            return None
        
        last_updated_str = metadata.get('last_updated')
        if not last_updated_str:
            return None
        
        last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        return now - last_updated
        
    except Exception as e:
        logger.error(f"Error calculating time since update for {tab_name}: {e}")
        return None

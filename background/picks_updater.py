"""
Background Picks Updater - Scheduled price enrichment job

Features:
- Idempotent execution (prevents duplicate runs)
- Concurrency-safe with file locks
- Audit logging
- Configurable schedule
- Manual trigger via admin endpoint

Author: Agent-1B
Date: 2025-11-21
"""

import os
import sys
import json
import logging
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from financial_dashboard.utils.picks_fetcher import PicksFetcher
from financial_dashboard.utils.cache_manager import CacheManager

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _make_plain(obj):
    """Recursively convert numpy/pandas types to native Python types for JSON."""
    try:
        # Local imports to keep module-level dependencies minimal
        import numpy as _np
        import pandas as _pd
    except Exception:
        _np = None
        _pd = None

    if isinstance(obj, dict):
        return {k: _make_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_plain(v) for v in obj]

    # numpy scalar
    if _np is not None and isinstance(obj, _np.generic):
        return obj.item()

    # numpy arrays
    if _np is not None and isinstance(obj, _np.ndarray):
        return obj.tolist()

    # pandas timestamps
    if _pd is not None and isinstance(obj, _pd.Timestamp):
        try:
            return obj.isoformat()
        except Exception:
            return str(obj)

    # datetime objects
    if isinstance(obj, datetime):
        return obj.isoformat()

    return obj

# Lock file to prevent concurrent runs
LOCK_FILE = PROJECT_ROOT / 'data' / 'picks' / '.picks_updater.lock'
LOG_FILE = PROJECT_ROOT / 'reports' / 'picks' / 'logs' / 'picks_updater.log'

# Ensure directories exist
LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Configure file logging
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)


class PicksUpdater:
    """Background job to update picks with fresh prices."""
    
    def __init__(self):
        """Initialize updater."""
        self.lock_file = LOCK_FILE
        self.is_running = False
        self._lock = threading.Lock()
    
    def acquire_lock(self) -> bool:
        """
        Acquire exclusive lock to prevent concurrent runs.
        
        Returns:
            True if lock acquired, False if already running
        """
        try:
            if self.lock_file.exists():
                # Check if lock is stale (older than 1 hour)
                lock_age = time.time() - self.lock_file.stat().st_mtime
                if lock_age < 3600:  # 1 hour
                    logger.warning(f"Lock file exists (age: {int(lock_age)}s), another job may be running")
                    return False
                else:
                    logger.warning(f"Removing stale lock file (age: {int(lock_age)}s)")
                    self.lock_file.unlink()
            
            # Create lock file
            with open(self.lock_file, 'w') as f:
                f.write(json.dumps({
                    'pid': os.getpid(),
                    'started_at': datetime.now().isoformat(),
                    'hostname': os.uname().nodename if hasattr(os, 'uname') else 'unknown'
                }))
            
            logger.info("Lock acquired")
            return True
            
        except Exception as e:
            logger.error(f"Failed to acquire lock: {e}")
            return False
    
    def release_lock(self):
        """Release lock file."""
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
                logger.info("Lock released")
        except Exception as e:
            logger.error(f"Failed to release lock: {e}")
    
    def update_weekly_picks(self) -> Dict[str, Any]:
        """
        Update weekly picks with fresh prices.
        
        Returns:
            Dict with status and stats
        """
        try:
            logger.info("=== Starting weekly picks update ===")
            
            # Load picks from JSON fallback or DB
            json_path = PROJECT_ROOT / 'data' / 'picks' / 'weekly_picks.json'
            
            if json_path.exists():
                with open(json_path, 'r') as f:
                    data = json.load(f)
                
                import pandas as pd
                picks_df = pd.DataFrame(data.get('data', []))
                logger.info(f"Loaded {len(picks_df)} weekly picks from JSON")
            else:
                fetcher = PicksFetcher()
                picks_df = fetcher.load_from_db('weekly_picks')
                logger.info(f"Loaded {len(picks_df)} weekly picks from DB")
            
            if picks_df.empty:
                logger.warning("No weekly picks to update")
                return {'status': 'skipped', 'reason': 'no_data', 'count': 0}
            
            # Enrich with fresh prices
            fetcher = PicksFetcher()
            enriched_df = fetcher.enrich_with_prices(picks_df, provenance=True)
            
            # Count successful enrichments
            if 'current_price' in enriched_df.columns:
                price_count = enriched_df['current_price'].notna().sum()
            else:
                price_count = 0
            
            # Update cache
            cache_path = PROJECT_ROOT / 'data' / 'picks' / 'weekly_cache.json'
            cache_manager = CacheManager(
                cache_file_path=str(cache_path),
                memory_cache={},
                ttl_seconds=300
            )
            
            # Convert DataFrame records to native Python types for JSON
            records = enriched_df.where(pd.notnull(enriched_df), None).to_dict('records')
            cache_data = {
                'picks': _make_plain(records),
                'count': int(len(enriched_df)),
                'empty': False,
                'generated_at': datetime.now().isoformat(),
                'prices_updated': int(price_count)
            }
            
            cache_manager.save_to_disk(cache_data)
            
            logger.info(f"✅ Weekly picks updated: {price_count}/{len(enriched_df)} prices fetched")
            
            return {
                'status': 'success',
                'pick_type': 'weekly',
                'total_picks': len(enriched_df),
                'prices_updated': price_count,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to update weekly picks: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def update_monthly_picks(self) -> Dict[str, Any]:
        """
        Update monthly picks with fresh prices.
        
        Returns:
            Dict with status and stats
        """
        try:
            logger.info("=== Starting monthly picks update ===")
            
            # Load picks
            json_path = PROJECT_ROOT / 'data' / 'picks' / 'monthly_picks.json'
            
            if json_path.exists():
                with open(json_path, 'r') as f:
                    data = json.load(f)
                
                import pandas as pd
                picks_df = pd.DataFrame(data.get('data', []))
                logger.info(f"Loaded {len(picks_df)} monthly picks from JSON")
            else:
                fetcher = PicksFetcher()
                picks_df = fetcher.load_from_db('monthly_picks')
                logger.info(f"Loaded {len(picks_df)} monthly picks from DB")
            
            if picks_df.empty:
                logger.warning("No monthly picks to update")
                return {'status': 'skipped', 'reason': 'no_data', 'count': 0}
            
            # Enrich with fresh prices
            fetcher = PicksFetcher()
            enriched_df = fetcher.enrich_with_prices(picks_df, provenance=True)
            
            if 'current_price' in enriched_df.columns:
                price_count = enriched_df['current_price'].notna().sum()
            else:
                price_count = 0
            
            # Update cache
            cache_path = PROJECT_ROOT / 'data' / 'picks' / 'monthly_cache.json'
            cache_manager = CacheManager(
                cache_file_path=str(cache_path),
                memory_cache={},
                ttl_seconds=300
            )
            
            # Convert DataFrame records to native Python types for JSON
            records = enriched_df.where(pd.notnull(enriched_df), None).to_dict('records')
            cache_data = {
                'picks': _make_plain(records),
                'count': int(len(enriched_df)),
                'empty': False,
                'generated_at': datetime.now().isoformat(),
                'prices_updated': int(price_count)
            }
            
            cache_manager.save_to_disk(cache_data)
            
            logger.info(f"✅ Monthly picks updated: {price_count}/{len(enriched_df)} prices fetched")
            
            return {
                'status': 'success',
                'pick_type': 'monthly',
                'total_picks': len(enriched_df),
                'prices_updated': price_count,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to update monthly picks: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def run(self) -> Dict[str, Any]:
        """
        Run the update job.
        
        Returns:
            Dict with job results
        """
        with self._lock:
            if self.is_running:
                logger.warning("Job already running, skipping")
                return {'status': 'skipped', 'reason': 'already_running'}
            
            self.is_running = True
        
        if not self.acquire_lock():
            self.is_running = False
            return {'status': 'error', 'reason': 'could_not_acquire_lock'}
        
        try:
            start_time = time.time()
            logger.info("🚀 Picks updater job started")
            
            # Update both weekly and monthly
            weekly_result = self.update_weekly_picks()
            monthly_result = self.update_monthly_picks()
            
            duration = time.time() - start_time
            
            result = {
                'status': 'completed',
                'duration_seconds': round(duration, 2),
                'weekly': weekly_result,
                'monthly': monthly_result,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Job completed in {duration:.2f}s")
            
            # Save run summary (normalize types first)
            summary_file = PROJECT_ROOT / 'reports' / 'picks' / 'logs' / 'last_run.json'
            result_plain = _make_plain(result)
            with open(summary_file, 'w') as f:
                json.dump(result_plain, f, indent=2)
            
            return result
            
        except Exception as e:
            logger.error(f"Job failed: {e}")
            return {'status': 'error', 'error': str(e)}
        
        finally:
            self.release_lock()
            self.is_running = False


# Singleton instance
_updater = PicksUpdater()


def run_picks_update() -> Dict[str, Any]:
    """
    Run picks update job (can be called from admin endpoint).
    
    Returns:
        Dict with job status and results
    """
    return _updater.run()


def start_scheduled_updates(interval_minutes: int = 60):
    """
    Start background thread that runs updates on schedule.
    
    Args:
        interval_minutes: Minutes between update runs
    """
    def scheduler_loop():
        logger.info(f"Scheduler started (interval: {interval_minutes} minutes)")
        
        while True:
            try:
                # Wait for interval
                time.sleep(interval_minutes * 60)
                
                # Run update
                logger.info("Scheduled update triggered")
                result = run_picks_update()
                logger.info(f"Scheduled update completed: {result.get('status')}")
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
    
    # Start background thread
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()
    
    logger.info("✅ Background scheduler started")


if __name__ == '__main__':
    # CLI entry point
    import argparse
    
    parser = argparse.ArgumentParser(description='Run picks price update job')
    parser.add_argument('--schedule', type=int, help='Run on schedule (minutes)')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    
    args = parser.parse_args()
    
    if args.schedule:
        print(f"Starting scheduled updates every {args.schedule} minutes...")
        start_scheduled_updates(args.schedule)
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nShutting down scheduler...")
            sys.exit(0)
    
    else:
        # Run once
        print("Running picks update job...")
        result = run_picks_update()
        # Normalize result for CLI output (convert numpy/pandas types)
        try:
            print(json.dumps(_make_plain(result), indent=2))
        except Exception:
            # Fallback to safe print
            print(str(_make_plain(result)))
        
        if result.get('status') == 'completed':
            sys.exit(0)
        else:
            sys.exit(1)

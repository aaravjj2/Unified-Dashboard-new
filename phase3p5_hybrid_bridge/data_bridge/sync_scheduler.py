"""
Sync Scheduler
==============

Async orchestrator for local → cloud stub synchronization.

Features:
- Manual and auto sync modes
- Batch processing with configurable batch size
- Telemetry logging to JSONL
- Error handling and retry logic
"""

import asyncio
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from .cache_router import get_global_router
from .data_contracts import ContractType


# Configuration
SYNC_LOG_DIR = Path(__file__).parent.parent.parent / "data" / "hybrid_logs"
SYNC_LOG_FILE = SYNC_LOG_DIR / "sync_log.jsonl"
DEFAULT_BATCH_SIZE = 10
DEFAULT_AUTO_INTERVAL_MINUTES = 15
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


class SyncMode(Enum):
    """Sync operation mode."""
    MANUAL = "manual"
    AUTO = "auto"


class SyncStatus(Enum):
    """Status of sync operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class SyncTask:
    """Represents a single sync task."""
    task_id: str
    contract_type: str
    key: str
    status: str = SyncStatus.PENDING.value
    created_at: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()
    
    def to_json(self) -> dict:
        """Convert to JSON dict."""
        return asdict(self)


@dataclass
class SyncEvent:
    """Telemetry event for sync operation."""
    event_id: str
    timestamp: str
    event_type: str  # sync_start, sync_complete, sync_error, batch_start, batch_complete
    mode: str
    batch_size: int
    tasks_successful: int
    tasks_failed: int
    duration_ms: float
    metadata: Dict[str, Any]
    
    def to_json(self) -> dict:
        """Convert to JSON dict."""
        return asdict(self)


class SyncScheduler:
    """
    Orchestrator for cache synchronization to cloud stubs.
    
    Supports manual trigger and automatic periodic syncs with batch processing.
    """
    
    def __init__(
        self,
        batch_size: int = DEFAULT_BATCH_SIZE,
        auto_interval_minutes: int = DEFAULT_AUTO_INTERVAL_MINUTES,
        log_file: Optional[Path] = None
    ):
        """
        Initialize sync scheduler.
        
        Args:
            batch_size: Number of tasks to process in parallel
            auto_interval_minutes: Interval for auto sync in minutes
            log_file: Path to telemetry log file
        """
        self.batch_size = batch_size
        self.auto_interval_minutes = auto_interval_minutes
        self.log_file = log_file or SYNC_LOG_FILE
        
        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Task queue
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.active_tasks: List[SyncTask] = []
        
        # Auto sync control
        self.auto_sync_enabled = False
        self.auto_sync_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.total_syncs = 0
        self.successful_syncs = 0
        self.failed_syncs = 0
    
    async def enqueue_sync(self, contract_type: ContractType, key: str) -> str:
        """
        Add sync task to queue.
        
        Args:
            contract_type: Contract type to sync
            key: Cache key
        
        Returns:
            Task ID
        """
        task_id = f"{contract_type.value}:{key}:{int(time.time() * 1000)}"
        
        task = SyncTask(
            task_id=task_id,
            contract_type=contract_type.value,
            key=key
        )
        
        await self.task_queue.put(task)
        return task_id
    
    async def sync_manual(self, contract_type: ContractType, key: str) -> bool:
        """
        Manually trigger sync for single item.
        
        Args:
            contract_type: Contract type to sync
            key: Cache key
        
        Returns:
            True if successful
        """
        start_time = time.time()
        
        # Log event
        self._log_event(SyncEvent(
            event_id=f"manual_{int(start_time * 1000)}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            event_type="sync_start",
            mode=SyncMode.MANUAL.value,
            batch_size=1,
            tasks_successful=0,
            tasks_failed=0,
            duration_ms=0.0,
            metadata={"contract_type": contract_type.value, "key": key}
        ))
        
        # Perform sync
        router = get_global_router()
        success = router.sync_to_cloud(contract_type, key)
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Update stats
        self.total_syncs += 1
        if success:
            self.successful_syncs += 1
        else:
            self.failed_syncs += 1
        
        # Log completion
        self._log_event(SyncEvent(
            event_id=f"manual_{int(time.time() * 1000)}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            event_type="sync_complete" if success else "sync_error",
            mode=SyncMode.MANUAL.value,
            batch_size=1,
            tasks_successful=1 if success else 0,
            tasks_failed=0 if success else 1,
            duration_ms=duration_ms,
            metadata={"contract_type": contract_type.value, "key": key}
        ))
        
        return success
    
    async def sync_batch(self, tasks: List[SyncTask]) -> Dict[str, int]:
        """
        Sync batch of tasks in parallel.
        
        Args:
            tasks: List of sync tasks
        
        Returns:
            Dict with successful and failed counts
        """
        batch_start = time.time()
        
        # Log batch start
        self._log_event(SyncEvent(
            event_id=f"batch_{int(batch_start * 1000)}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            event_type="batch_start",
            mode=SyncMode.AUTO.value,
            batch_size=len(tasks),
            tasks_successful=0,
            tasks_failed=0,
            duration_ms=0.0,
            metadata={}
        ))
        
        # Process tasks in parallel
        results = await asyncio.gather(
            *[self._sync_single_task(task) for task in tasks],
            return_exceptions=True
        )
        
        # Count successes and failures
        successful = sum(1 for r in results if r is True)
        failed = len(results) - successful
        
        duration_ms = (time.time() - batch_start) * 1000
        
        # Update stats
        self.total_syncs += len(tasks)
        self.successful_syncs += successful
        self.failed_syncs += failed
        
        # Log batch completion
        self._log_event(SyncEvent(
            event_id=f"batch_{int(time.time() * 1000)}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            event_type="batch_complete",
            mode=SyncMode.AUTO.value,
            batch_size=len(tasks),
            tasks_successful=successful,
            tasks_failed=failed,
            duration_ms=duration_ms,
            metadata={}
        ))
        
        return {"successful": successful, "failed": failed}
    
    async def _sync_single_task(self, task: SyncTask) -> bool:
        """
        Sync single task with retry logic.
        
        Args:
            task: Sync task
        
        Returns:
            True if successful
        """
        task.status = SyncStatus.IN_PROGRESS.value
        task.started_at = time.time()
        
        router = get_global_router()
        contract_type = ContractType(task.contract_type)
        
        for attempt in range(MAX_RETRIES):
            try:
                success = router.sync_to_cloud(contract_type, task.key)
                
                if success:
                    task.status = SyncStatus.SUCCESS.value
                    task.completed_at = time.time()
                    return True
                else:
                    # Retry if not last attempt
                    if attempt < MAX_RETRIES - 1:
                        task.status = SyncStatus.RETRYING.value
                        task.retry_count += 1
                        await asyncio.sleep(RETRY_DELAY_SECONDS)
                    else:
                        task.status = SyncStatus.FAILED.value
                        task.error = "Sync returned False after max retries"
                        task.completed_at = time.time()
                        return False
            
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    task.status = SyncStatus.RETRYING.value
                    task.retry_count += 1
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                else:
                    task.status = SyncStatus.FAILED.value
                    task.error = str(e)
                    task.completed_at = time.time()
                    return False
        
        return False
    
    async def start_auto_sync(self) -> None:
        """Start automatic periodic sync."""
        if self.auto_sync_enabled:
            return
        
        self.auto_sync_enabled = True
        self.auto_sync_task = asyncio.create_task(self._auto_sync_loop())
    
    async def stop_auto_sync(self) -> None:
        """Stop automatic periodic sync."""
        self.auto_sync_enabled = False
        
        if self.auto_sync_task:
            self.auto_sync_task.cancel()
            try:
                await self.auto_sync_task
            except asyncio.CancelledError:
                pass
            self.auto_sync_task = None
    
    async def _auto_sync_loop(self) -> None:
        """Background loop for auto sync."""
        while self.auto_sync_enabled:
            try:
                # Wait for interval
                await asyncio.sleep(self.auto_interval_minutes * 60)
                
                # Process queued tasks in batches
                await self._process_queue()
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue
                print(f"Auto sync error: {e}")
    
    async def _process_queue(self) -> None:
        """Process all queued tasks in batches."""
        if self.task_queue.empty():
            return
        
        # Collect batch
        batch = []
        while not self.task_queue.empty() and len(batch) < self.batch_size:
            try:
                task = await asyncio.wait_for(self.task_queue.get(), timeout=0.1)
                batch.append(task)
            except asyncio.TimeoutError:
                break
        
        if batch:
            await self.sync_batch(batch)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get scheduler statistics.
        
        Returns:
            Dict with sync stats
        """
        success_rate = self.successful_syncs / self.total_syncs if self.total_syncs > 0 else 0.0
        
        return {
            "total_syncs": self.total_syncs,
            "successful_syncs": self.successful_syncs,
            "failed_syncs": self.failed_syncs,
            "success_rate": success_rate,
            "queue_size": self.task_queue.qsize(),
            "auto_sync_enabled": self.auto_sync_enabled,
            "auto_interval_minutes": self.auto_interval_minutes,
            "batch_size": self.batch_size
        }
    
    def _log_event(self, event: SyncEvent) -> None:
        """
        Write telemetry event to JSONL log.
        
        Args:
            event: Sync event to log
        """
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(event.to_json()) + '\n')
        except IOError as e:
            print(f"Warning: Failed to write sync log: {e}")
    
    def read_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Read recent sync events from log.
        
        Args:
            limit: Maximum number of events to return
        
        Returns:
            List of event dicts (most recent first)
        """
        if not self.log_file.exists():
            return []
        
        events = []
        
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    try:
                        events.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        except IOError:
            return []
        
        # Return most recent first
        return list(reversed(events[-limit:]))


# Singleton instance
_global_scheduler: Optional[SyncScheduler] = None


def get_global_scheduler() -> SyncScheduler:
    """Get or create global sync scheduler instance."""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = SyncScheduler()
    return _global_scheduler


# Convenience functions

async def sync_manual(contract_type: ContractType, key: str) -> bool:
    """Convenience wrapper for global scheduler sync_manual."""
    return await get_global_scheduler().sync_manual(contract_type, key)


async def start_auto_sync() -> None:
    """Convenience wrapper for global scheduler start_auto_sync."""
    await get_global_scheduler().start_auto_sync()


async def stop_auto_sync() -> None:
    """Convenience wrapper for global scheduler stop_auto_sync."""
    await get_global_scheduler().stop_auto_sync()


def get_sync_stats() -> Dict[str, Any]:
    """Convenience wrapper for global scheduler get_stats."""
    return get_global_scheduler().get_stats()

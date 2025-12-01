"""
Compute Router (Phase 4 - Hybrid Readiness)

Dispatches compute tasks (risk calc, forecast, optimization) to the correct backend.
Acts as the middle layer between Dash callbacks and Azure stubs/real clients.

This module provides intelligent routing logic that can:
- Route lightweight tasks to local compute
- Route heavy tasks to Azure ML
- Balance load across multiple backends
- Cache frequent computations

Usage:
    >>> router = ComputeRouter()
    >>> result = router.dispatch('forecast', task_data)
"""

import logging
import time
from typing import Dict, Any, Optional, Literal, List
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

from phase4_hybrid_stubs.local_hybrid_bridge.hybrid_interface import (
    run_analytics,
    is_offline
)

logger = logging.getLogger(__name__)

# ============================================================================
# TASK CONFIGURATION
# ============================================================================

@dataclass
class TaskConfig:
    """Configuration for compute task routing."""
    
    task_type: str
    priority: int = 1  # 1-5, higher = more important
    max_latency_ms: float = 5000.0  # Maximum acceptable latency
    prefer_local: bool = False  # Prefer local compute if available
    requires_gpu: bool = False  # Whether task needs GPU
    cache_ttl_seconds: int = 300  # Cache time-to-live
    retry_on_failure: bool = True  # Whether to retry on failure
    max_retries: int = 3  # Maximum retry attempts


# Task type configurations
TASK_CONFIGS = {
    'forecast': TaskConfig(
        task_type='forecast',
        priority=3,
        max_latency_ms=2000.0,
        prefer_local=False,
        cache_ttl_seconds=600
    ),
    'backtest': TaskConfig(
        task_type='backtest',
        priority=2,
        max_latency_ms=5000.0,
        prefer_local=False,
        cache_ttl_seconds=1800
    ),
    'risk': TaskConfig(
        task_type='risk',
        priority=4,
        max_latency_ms=1000.0,
        prefer_local=True,
        cache_ttl_seconds=300
    ),
    'optimization': TaskConfig(
        task_type='optimization',
        priority=2,
        max_latency_ms=10000.0,
        prefer_local=False,
        requires_gpu=True,
        cache_ttl_seconds=900
    ),
    'shap': TaskConfig(
        task_type='shap',
        priority=3,
        max_latency_ms=3000.0,
        prefer_local=False,
        cache_ttl_seconds=1200
    ),
    'batch': TaskConfig(
        task_type='batch',
        priority=1,
        max_latency_ms=30000.0,
        prefer_local=False,
        cache_ttl_seconds=3600
    )
}


# ============================================================================
# COMPUTE ROUTER
# ============================================================================

class ComputeRouter:
    """
    Intelligent compute task router.
    
    Routes tasks to appropriate backend based on:
    - Task type and complexity
    - Available resources
    - Latency requirements
    - Cache availability
    
    Example:
        >>> router = ComputeRouter()
        >>> result = router.dispatch(
        ...     task_type='forecast',
        ...     payload={'ticker': 'AAPL', ...}
        ... )
    """
    
    def __init__(self):
        """Initialize compute router."""
        self.task_queue: List[Dict[str, Any]] = []
        self.task_history: List[Dict[str, Any]] = []
        self.cache: Dict[str, Any] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        
        logger.info("🔀 ComputeRouter initialized")
    
    def dispatch(
        self,
        task_type: Literal['forecast', 'backtest', 'risk', 'optimization', 'shap', 'batch'],
        payload: Dict[str, Any],
        force_backend: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Dispatch compute task to appropriate backend.
        
        Args:
            task_type: Type of task to execute
            payload: Task payload (see run_analytics for schema)
            force_backend: Force specific backend ('local' or 'azure'), None = auto-select
            use_cache: Whether to use cached results if available
        
        Returns:
            Task result dictionary
        
        Example:
            >>> result = router.dispatch('forecast', {'ticker': 'AAPL', ...})
        """
        start_time = time.perf_counter()
        
        # Get task configuration
        config = TASK_CONFIGS.get(task_type)
        if not config:
            raise ValueError(f"Unknown task type: {task_type}")
        
        # Generate cache key
        cache_key = self._generate_cache_key(task_type, payload)
        
        # Check cache
        if use_cache and cache_key in self.cache:
            if self._is_cache_valid(cache_key, config.cache_ttl_seconds):
                logger.info(f"🎯 Cache HIT for {task_type} (key={cache_key[:16]}...)")
                cached_result = self.cache[cache_key]
                cached_result['_from_cache'] = True
                cached_result['_cache_age_seconds'] = (
                    datetime.now() - self.cache_timestamps[cache_key]
                ).total_seconds()
                return cached_result
        
        # Select backend
        if force_backend:
            backend = force_backend
        else:
            backend = self._select_backend(config)
        
        logger.info(f"🚀 Dispatching {task_type} to {backend} backend")
        
        # Execute task with retry logic
        result = None
        last_error = None
        
        for attempt in range(1, config.max_retries + 1):
            try:
                if backend == 'local':
                    result = self._execute_local(task_type, payload)
                elif backend == 'azure':
                    result = self._execute_azure(task_type, payload)
                else:
                    raise ValueError(f"Unknown backend: {backend}")
                
                # Success - break retry loop
                break
                
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️  Task failed (attempt {attempt}/{config.max_retries}): {e}")
                
                if not config.retry_on_failure or attempt >= config.max_retries:
                    # No more retries
                    raise
                
                # Wait before retry (exponential backoff)
                wait_time = 2 ** (attempt - 1)  # 1s, 2s, 4s, ...
                time.sleep(wait_time)
        
        if result is None:
            raise RuntimeError(f"Task failed after {config.max_retries} retries: {last_error}")
        
        # Calculate latency
        latency_ms = (time.perf_counter() - start_time) * 1000
        result['_dispatch_latency_ms'] = latency_ms
        result['_backend'] = backend
        result['_from_cache'] = False
        
        # Store in cache
        if use_cache:
            self.cache[cache_key] = result
            self.cache_timestamps[cache_key] = datetime.now()
            logger.debug(f"💾 Cached result for {task_type} (key={cache_key[:16]}...)")
        
        # Record in history
        self.task_history.append({
            'task_type': task_type,
            'ticker': payload.get('ticker'),
            'backend': backend,
            'latency_ms': latency_ms,
            'timestamp': datetime.now().isoformat(),
            'success': True
        })
        
        # Check if latency exceeded threshold
        if latency_ms > config.max_latency_ms:
            logger.warning(
                f"⏱️  Task latency {latency_ms:.0f}ms exceeded threshold {config.max_latency_ms:.0f}ms"
            )
        
        logger.info(f"✅ Task completed: {task_type} ({latency_ms:.0f}ms)")
        return result
    
    def _select_backend(self, config: TaskConfig) -> str:
        """
        Select backend for task based on configuration and availability.
        
        Args:
            config: Task configuration
        
        Returns:
            Backend name ('local' or 'azure')
        """
        # If in offline mode, always use local
        if is_offline():
            return 'local'
        
        # If task prefers local and local is available, use local
        if config.prefer_local:
            return 'local'
        
        # If task requires GPU and azure is available, use azure
        if config.requires_gpu:
            return 'azure'
        
        # For high-priority tasks, use azure for better performance
        if config.priority >= 4:
            return 'azure'
        
        # Default: use azure
        return 'azure'
    
    def _execute_local(
        self,
        task_type: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute task on local backend (stub).
        
        Args:
            task_type: Task type
            payload: Task payload
        
        Returns:
            Task result
        """
        # For local execution, use stub clients via hybrid interface
        # Force offline mode temporarily
        from phase4_hybrid_stubs.local_hybrid_bridge.hybrid_interface import set_offline_mode
        original_mode = is_offline()
        
        try:
            set_offline_mode(True)
            result = run_analytics(job_type=task_type, payload=payload)
            return result
        finally:
            set_offline_mode(original_mode)
    
    def _execute_azure(
        self,
        task_type: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute task on Azure backend (stub or real).
        
        Args:
            task_type: Task type
            payload: Task payload
        
        Returns:
            Task result
        """
        # Execute via hybrid interface (will use stub if offline, real Azure if online)
        result = run_analytics(job_type=task_type, payload=payload)
        return result
    
    def _generate_cache_key(
        self,
        task_type: str,
        payload: Dict[str, Any]
    ) -> str:
        """
        Generate cache key for task.
        
        Args:
            task_type: Task type
            payload: Task payload
        
        Returns:
            Cache key string
        """
        import hashlib
        import json
        
        # Create deterministic key from task type and payload
        cache_data = {
            'task_type': task_type,
            'ticker': payload.get('ticker'),
            'features': payload.get('features'),
            'date_range': payload.get('date_range'),
            'model_type': payload.get('model_type'),
            'forecast_horizon': payload.get('forecast_horizon')
        }
        
        # Sort keys for deterministic hashing
        json_str = json.dumps(cache_data, sort_keys=True)
        hash_obj = hashlib.sha256(json_str.encode())
        
        return hash_obj.hexdigest()
    
    def _is_cache_valid(
        self,
        cache_key: str,
        ttl_seconds: int
    ) -> bool:
        """
        Check if cached result is still valid.
        
        Args:
            cache_key: Cache key
            ttl_seconds: Time-to-live in seconds
        
        Returns:
            True if cache is valid, False otherwise
        """
        if cache_key not in self.cache_timestamps:
            return False
        
        age_seconds = (datetime.now() - self.cache_timestamps[cache_key]).total_seconds()
        
        return age_seconds < ttl_seconds
    
    def clear_cache(self, task_type: Optional[str] = None):
        """
        Clear cache (all or specific task type).
        
        Args:
            task_type: Task type to clear (None = clear all)
        """
        if task_type is None:
            self.cache.clear()
            self.cache_timestamps.clear()
            logger.info("🗑️  Cleared entire cache")
        else:
            # Clear cache entries for specific task type
            keys_to_remove = [
                key for key in self.cache.keys()
                if key.startswith(task_type)
            ]
            for key in keys_to_remove:
                del self.cache[key]
                del self.cache_timestamps[key]
            logger.info(f"🗑️  Cleared {len(keys_to_remove)} cache entries for {task_type}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Cache stats dictionary
        """
        total_cached = len(self.cache)
        
        # Calculate cache age distribution
        if total_cached > 0:
            ages = [
                (datetime.now() - ts).total_seconds()
                for ts in self.cache_timestamps.values()
            ]
            avg_age = sum(ages) / len(ages)
            max_age = max(ages)
        else:
            avg_age = 0.0
            max_age = 0.0
        
        return {
            'total_cached_items': total_cached,
            'average_age_seconds': avg_age,
            'max_age_seconds': max_age,
            'cache_size_bytes': sum(
                len(str(v)) for v in self.cache.values()
            )
        }
    
    def get_task_history(
        self,
        limit: int = 100,
        task_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get task execution history.
        
        Args:
            limit: Maximum number of history entries to return
            task_type: Filter by task type (None = all types)
        
        Returns:
            List of task history dictionaries
        """
        history = self.task_history
        
        # Filter by task type if specified
        if task_type:
            history = [h for h in history if h['task_type'] == task_type]
        
        # Return most recent entries
        return history[-limit:]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics across all tasks.
        
        Returns:
            Performance stats dictionary
        """
        if not self.task_history:
            return {
                'total_tasks': 0,
                'average_latency_ms': 0.0,
                'success_rate': 0.0
            }
        
        latencies = [h['latency_ms'] for h in self.task_history]
        successes = [h['success'] for h in self.task_history]
        
        return {
            'total_tasks': len(self.task_history),
            'average_latency_ms': sum(latencies) / len(latencies),
            'min_latency_ms': min(latencies),
            'max_latency_ms': max(latencies),
            'success_rate': sum(successes) / len(successes),
            'task_type_breakdown': self._get_task_type_breakdown()
        }
    
    def _get_task_type_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Get per-task-type performance breakdown."""
        breakdown = {}
        
        for task_type in TASK_CONFIGS.keys():
            type_history = [h for h in self.task_history if h['task_type'] == task_type]
            
            if type_history:
                latencies = [h['latency_ms'] for h in type_history]
                breakdown[task_type] = {
                    'count': len(type_history),
                    'avg_latency_ms': sum(latencies) / len(latencies),
                    'min_latency_ms': min(latencies),
                    'max_latency_ms': max(latencies)
                }
        
        return breakdown


# ============================================================================
# GLOBAL ROUTER INSTANCE
# ============================================================================

# Singleton router instance for dashboard use
_global_router: Optional[ComputeRouter] = None


def get_router() -> ComputeRouter:
    """
    Get global ComputeRouter instance.
    
    Returns:
        Shared ComputeRouter instance
    """
    global _global_router
    
    if _global_router is None:
        _global_router = ComputeRouter()
    
    return _global_router


logger.info("✓ Compute Router loaded (Phase 4 - Hybrid Readiness)")

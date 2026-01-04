"""
Alpaca Options Lab - Health Check

System health monitoring:
- Component health tracking
- Dependency checking
- Automatic recovery
- Health endpoints
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status of a component."""
    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    message: str = ""
    
    # Timing
    last_check: Optional[datetime] = None
    latency_ms: float = 0.0
    
    # Details
    details: Dict[str, Any] = field(default_factory=dict)
    
    # History
    consecutive_failures: int = 0
    last_healthy: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "latency_ms": self.latency_ms,
            "consecutive_failures": self.consecutive_failures,
            "details": self.details,
        }


@dataclass
class HealthCheckConfig:
    """Health check configuration."""
    check_interval_seconds: int = 30
    timeout_seconds: float = 10.0
    
    # Thresholds
    unhealthy_threshold: int = 3  # Failures before unhealthy
    degraded_threshold: int = 1  # Failures before degraded
    
    # Recovery
    auto_recovery_enabled: bool = True
    recovery_cooldown_seconds: int = 60


class HealthCheck:
    """
    Health check for a single component.
    
    Performs periodic health checks and tracks status.
    """
    
    def __init__(
        self,
        name: str,
        check_fn: Callable[[], Any],
        config: Optional[HealthCheckConfig] = None,
    ):
        self.name = name
        self.check_fn = check_fn
        self.config = config or HealthCheckConfig()
        
        # State
        self._health = ComponentHealth(name=name)
        
        # Recovery
        self._recovery_fn: Optional[Callable] = None
        self._last_recovery: Optional[datetime] = None
        
        logger.debug(f"HealthCheck '{name}' initialized")
    
    async def check(self) -> ComponentHealth:
        """
        Perform health check.
        
        Returns:
            ComponentHealth with current status
        """
        import time
        
        start = time.monotonic()
        
        try:
            # Execute check function
            if asyncio.iscoroutinefunction(self.check_fn):
                result = await asyncio.wait_for(
                    self.check_fn(),
                    timeout=self.config.timeout_seconds,
                )
            else:
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, self.check_fn),
                    timeout=self.config.timeout_seconds,
                )
            
            # Success
            self._health.status = HealthStatus.HEALTHY
            self._health.message = "OK"
            self._health.consecutive_failures = 0
            self._health.last_healthy = datetime.now(timezone.utc)
            
            if isinstance(result, dict):
                self._health.details = result
            
        except asyncio.TimeoutError:
            self._record_failure("Check timed out")
            
        except Exception as e:
            self._record_failure(str(e))
        
        # Record timing
        elapsed_ms = (time.monotonic() - start) * 1000
        self._health.latency_ms = elapsed_ms
        self._health.last_check = datetime.now(timezone.utc)
        
        # Attempt recovery if needed
        if self._health.status == HealthStatus.UNHEALTHY:
            await self._attempt_recovery()
        
        return self._health
    
    def _record_failure(self, message: str) -> None:
        """Record a health check failure."""
        self._health.consecutive_failures += 1
        self._health.message = message
        
        if self._health.consecutive_failures >= self.config.unhealthy_threshold:
            self._health.status = HealthStatus.UNHEALTHY
        elif self._health.consecutive_failures >= self.config.degraded_threshold:
            self._health.status = HealthStatus.DEGRADED
        else:
            self._health.status = HealthStatus.DEGRADED
        
        logger.warning(
            f"Health check '{self.name}' failed: {message} "
            f"(failures: {self._health.consecutive_failures})"
        )
    
    async def _attempt_recovery(self) -> None:
        """Attempt automatic recovery."""
        if not self.config.auto_recovery_enabled:
            return
        
        if not self._recovery_fn:
            return
        
        # Check cooldown
        if self._last_recovery:
            elapsed = (datetime.now(timezone.utc) - self._last_recovery).total_seconds()
            if elapsed < self.config.recovery_cooldown_seconds:
                return
        
        logger.info(f"Attempting recovery for '{self.name}'...")
        
        try:
            if asyncio.iscoroutinefunction(self._recovery_fn):
                await self._recovery_fn()
            else:
                self._recovery_fn()
            
            self._last_recovery = datetime.now(timezone.utc)
            logger.info(f"Recovery attempted for '{self.name}'")
            
        except Exception as e:
            logger.error(f"Recovery failed for '{self.name}': {e}")
    
    def set_recovery(self, recovery_fn: Callable) -> None:
        """Set recovery function."""
        self._recovery_fn = recovery_fn
    
    @property
    def health(self) -> ComponentHealth:
        """Get current health status."""
        return self._health
    
    @property
    def is_healthy(self) -> bool:
        """Check if component is healthy."""
        return self._health.status == HealthStatus.HEALTHY


class HealthMonitor:
    """
    Monitors health of multiple components.
    
    Features:
    - Periodic health checks
    - Aggregate status
    - Health endpoint support
    - Alerting integration
    """
    
    def __init__(self, config: Optional[HealthCheckConfig] = None):
        self.config = config or HealthCheckConfig()
        
        # Health checks
        self._checks: Dict[str, HealthCheck] = {}
        
        # Monitoring
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Callbacks
        self._on_status_change: List[Callable] = []
        
        logger.info("HealthMonitor initialized")
    
    # -------------------- Registration --------------------
    
    def register(
        self,
        name: str,
        check_fn: Callable,
        recovery_fn: Optional[Callable] = None,
    ) -> HealthCheck:
        """
        Register a health check.
        
        Args:
            name: Component name
            check_fn: Function to check health
            recovery_fn: Optional recovery function
        
        Returns:
            Created HealthCheck
        """
        check = HealthCheck(name, check_fn, self.config)
        
        if recovery_fn:
            check.set_recovery(recovery_fn)
        
        self._checks[name] = check
        logger.info(f"Health check registered: {name}")
        
        return check
    
    def unregister(self, name: str) -> bool:
        """Unregister a health check."""
        if name in self._checks:
            del self._checks[name]
            return True
        return False
    
    # -------------------- Checking --------------------
    
    async def check_all(self) -> Dict[str, ComponentHealth]:
        """
        Run all health checks.
        
        Returns:
            Dictionary of component name -> health status
        """
        results = {}
        
        # Run checks in parallel
        tasks = [
            self._run_check(name, check)
            for name, check in self._checks.items()
        ]
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        for name, check in self._checks.items():
            results[name] = check.health
        
        return results
    
    async def _run_check(self, name: str, check: HealthCheck) -> None:
        """Run a single health check with status change detection."""
        old_status = check.health.status
        
        await check.check()
        
        new_status = check.health.status
        
        # Notify on status change
        if old_status != new_status:
            await self._notify_status_change(name, old_status, new_status)
    
    async def check_one(self, name: str) -> Optional[ComponentHealth]:
        """Run health check for specific component."""
        check = self._checks.get(name)
        if check:
            return await check.check()
        return None
    
    # -------------------- Aggregate Status --------------------
    
    def get_aggregate_status(self) -> HealthStatus:
        """
        Get aggregate status across all components.
        
        Returns:
            Worst status across all components
        """
        if not self._checks:
            return HealthStatus.UNKNOWN
        
        statuses = [check.health.status for check in self._checks.values()]
        
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        if HealthStatus.UNKNOWN in statuses:
            return HealthStatus.UNKNOWN
        
        return HealthStatus.HEALTHY
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get full health report."""
        components = {
            name: check.health.to_dict()
            for name, check in self._checks.items()
        }
        
        aggregate = self.get_aggregate_status()
        healthy_count = len([c for c in self._checks.values() if c.is_healthy])
        
        return {
            "status": aggregate.value,
            "healthy_components": healthy_count,
            "total_components": len(self._checks),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": components,
        }
    
    # -------------------- Monitoring --------------------
    
    async def start_monitoring(self, interval: Optional[int] = None) -> None:
        """Start periodic health monitoring."""
        if self._running:
            return
        
        self._running = True
        check_interval = interval or self.config.check_interval_seconds
        
        self._monitor_task = asyncio.create_task(
            self._monitor_loop(check_interval)
        )
        
        logger.info(f"Health monitoring started (interval: {check_interval}s)")
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Health monitoring stopped")
    
    async def _monitor_loop(self, interval: int) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                await self.check_all()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(interval)
    
    # -------------------- Callbacks --------------------
    
    def on_status_change(self, callback: Callable) -> None:
        """Register status change callback."""
        self._on_status_change.append(callback)
    
    async def _notify_status_change(
        self,
        component: str,
        old_status: HealthStatus,
        new_status: HealthStatus,
    ) -> None:
        """Notify status change callbacks."""
        for callback in self._on_status_change:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(component, old_status, new_status)
                else:
                    callback(component, old_status, new_status)
            except Exception as e:
                logger.error(f"Status change callback error: {e}")


# -------------------- Common Health Checks --------------------

async def check_database_connection(conn_string: str) -> Dict[str, Any]:
    """Health check for database connection."""
    # Placeholder - implement based on your database
    return {"connected": True, "latency_ms": 5}


async def check_api_connection(url: str) -> Dict[str, Any]:
    """Health check for API connection."""
    import aiohttp
    
    async with aiohttp.ClientSession() as session:
        start = asyncio.get_event_loop().time()
        async with session.get(url, timeout=5) as response:
            latency = (asyncio.get_event_loop().time() - start) * 1000
            return {
                "status_code": response.status,
                "latency_ms": latency,
                "connected": response.status == 200,
            }


def check_disk_space(path: str = "/", min_free_gb: float = 1.0) -> Dict[str, Any]:
    """Health check for disk space."""
    import shutil
    
    total, used, free = shutil.disk_usage(path)
    free_gb = free / (1024 ** 3)
    
    return {
        "total_gb": total / (1024 ** 3),
        "used_gb": used / (1024 ** 3),
        "free_gb": free_gb,
        "healthy": free_gb >= min_free_gb,
    }


def check_memory_usage(max_percent: float = 90.0) -> Dict[str, Any]:
    """Health check for memory usage."""
    try:
        import psutil
        
        mem = psutil.virtual_memory()
        return {
            "total_gb": mem.total / (1024 ** 3),
            "used_percent": mem.percent,
            "available_gb": mem.available / (1024 ** 3),
            "healthy": mem.percent < max_percent,
        }
    except ImportError:
        return {"error": "psutil not installed"}

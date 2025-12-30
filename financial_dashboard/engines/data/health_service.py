"""
Health Service - Redis and TimescaleDB health check infrastructure.
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    service_name: str
    status: ServiceStatus
    latency_ms: float
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "service_name": self.service_name,
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 2),
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class HealthService:
    """
    Centralized health check service for data fabric components.
    
    Monitors:
    - Redis cache connectivity and latency
    - TimescaleDB connection pool health
    - Data feed freshness
    """
    
    # Latency thresholds in milliseconds
    REDIS_LATENCY_WARN = 50.0  # ms
    REDIS_LATENCY_CRIT = 200.0  # ms
    TIMESCALE_LATENCY_WARN = 100.0  # ms
    TIMESCALE_LATENCY_CRIT = 500.0  # ms
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        timescale_dsn: Optional[str] = None
    ):
        """
        Initialize health service.
        
        Args:
            redis_url: Redis connection URL (default from env)
            timescale_dsn: TimescaleDB DSN (default from env)
        """
        import os
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.timescale_dsn = timescale_dsn or os.getenv(
            "TIMESCALE_DSN", 
            "postgresql://postgres:postgres@localhost:5432/options_data"
        )
        self._redis_client = None
        self._pg_pool = None
        self._last_checks: Dict[str, HealthCheckResult] = {}
        
    async def _get_redis_client(self):
        """Lazy initialization of Redis client."""
        if self._redis_client is None:
            try:
                import redis.asyncio as redis
                self._redis_client = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
            except ImportError:
                logger.warning("redis package not installed")
                return None
        return self._redis_client
    
    async def _get_pg_pool(self):
        """Lazy initialization of PostgreSQL connection pool."""
        if self._pg_pool is None:
            try:
                import asyncpg
                self._pg_pool = await asyncpg.create_pool(
                    self.timescale_dsn,
                    min_size=1,
                    max_size=5,
                    command_timeout=5.0
                )
            except ImportError:
                logger.warning("asyncpg package not installed")
                return None
            except Exception as e:
                logger.error(f"Failed to create PG pool: {e}")
                return None
        return self._pg_pool
    
    async def check_redis(self) -> HealthCheckResult:
        """
        Check Redis connectivity and latency.
        
        Returns:
            HealthCheckResult with status and latency
        """
        service_name = "redis"
        start_time = time.perf_counter()
        
        try:
            client = await self._get_redis_client()
            if client is None:
                return HealthCheckResult(
                    service_name=service_name,
                    status=ServiceStatus.UNKNOWN,
                    latency_ms=0.0,
                    message="Redis client not available (package not installed)",
                    metadata={"error": "import_error"}
                )
            
            # Ping test
            pong = await asyncio.wait_for(client.ping(), timeout=2.0)
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            if not pong:
                return HealthCheckResult(
                    service_name=service_name,
                    status=ServiceStatus.UNHEALTHY,
                    latency_ms=latency_ms,
                    message="Redis PING failed",
                    metadata={"response": str(pong)}
                )
            
            # Get additional info
            info = await client.info(section="server")
            
            # Determine status based on latency
            if latency_ms > self.REDIS_LATENCY_CRIT:
                status = ServiceStatus.UNHEALTHY
                message = f"Redis latency critical: {latency_ms:.1f}ms"
            elif latency_ms > self.REDIS_LATENCY_WARN:
                status = ServiceStatus.DEGRADED
                message = f"Redis latency elevated: {latency_ms:.1f}ms"
            else:
                status = ServiceStatus.HEALTHY
                message = f"Redis OK ({latency_ms:.1f}ms)"
            
            result = HealthCheckResult(
                service_name=service_name,
                status=status,
                latency_ms=latency_ms,
                message=message,
                metadata={
                    "redis_version": info.get("redis_version", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_human": info.get("used_memory_human", "unknown")
                }
            )
            
        except asyncio.TimeoutError:
            latency_ms = (time.perf_counter() - start_time) * 1000
            result = HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                latency_ms=latency_ms,
                message="Redis connection timeout",
                metadata={"error": "timeout"}
            )
            
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            result = HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                latency_ms=latency_ms,
                message=f"Redis error: {str(e)[:100]}",
                metadata={"error": type(e).__name__}
            )
        
        self._last_checks["redis"] = result
        return result
    
    async def check_timescaledb(self) -> HealthCheckResult:
        """
        Check TimescaleDB connectivity and latency.
        
        Returns:
            HealthCheckResult with status and latency
        """
        service_name = "timescaledb"
        start_time = time.perf_counter()
        
        try:
            pool = await self._get_pg_pool()
            if pool is None:
                return HealthCheckResult(
                    service_name=service_name,
                    status=ServiceStatus.UNKNOWN,
                    latency_ms=0.0,
                    message="PostgreSQL pool not available",
                    metadata={"error": "pool_unavailable"}
                )
            
            async with pool.acquire() as conn:
                # Simple query test
                result = await asyncio.wait_for(
                    conn.fetchval("SELECT 1"),
                    timeout=5.0
                )
                latency_ms = (time.perf_counter() - start_time) * 1000
                
                if result != 1:
                    return HealthCheckResult(
                        service_name=service_name,
                        status=ServiceStatus.UNHEALTHY,
                        latency_ms=latency_ms,
                        message="TimescaleDB query returned unexpected result",
                        metadata={"result": str(result)}
                    )
                
                # Get additional diagnostics
                version = await conn.fetchval("SELECT version()")
                pool_size = pool.get_size()
                
                # Check TimescaleDB extension
                ts_version = await conn.fetchval(
                    "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'"
                )
            
            # Determine status based on latency
            if latency_ms > self.TIMESCALE_LATENCY_CRIT:
                status = ServiceStatus.UNHEALTHY
                message = f"TimescaleDB latency critical: {latency_ms:.1f}ms"
            elif latency_ms > self.TIMESCALE_LATENCY_WARN:
                status = ServiceStatus.DEGRADED
                message = f"TimescaleDB latency elevated: {latency_ms:.1f}ms"
            else:
                status = ServiceStatus.HEALTHY
                message = f"TimescaleDB OK ({latency_ms:.1f}ms)"
            
            result = HealthCheckResult(
                service_name=service_name,
                status=status,
                latency_ms=latency_ms,
                message=message,
                metadata={
                    "pg_version": version[:50] if version else "unknown",
                    "timescaledb_version": ts_version or "not installed",
                    "pool_size": pool_size
                }
            )
            
        except asyncio.TimeoutError:
            latency_ms = (time.perf_counter() - start_time) * 1000
            result = HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                latency_ms=latency_ms,
                message="TimescaleDB connection timeout",
                metadata={"error": "timeout"}
            )
            
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            result = HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                latency_ms=latency_ms,
                message=f"TimescaleDB error: {str(e)[:100]}",
                metadata={"error": type(e).__name__}
            )
        
        self._last_checks["timescaledb"] = result
        return result
    
    async def check_all(self) -> Dict[str, HealthCheckResult]:
        """
        Run all health checks in parallel.
        
        Returns:
            Dictionary of service names to health check results
        """
        results = await asyncio.gather(
            self.check_redis(),
            self.check_timescaledb(),
            return_exceptions=True
        )
        
        output = {}
        for i, (name, result) in enumerate(zip(["redis", "timescaledb"], results)):
            if isinstance(result, Exception):
                output[name] = HealthCheckResult(
                    service_name=name,
                    status=ServiceStatus.UNHEALTHY,
                    latency_ms=0.0,
                    message=f"Check failed: {str(result)[:100]}",
                    metadata={"error": type(result).__name__}
                )
            else:
                output[name] = result
        
        return output
    
    def get_overall_status(self) -> ServiceStatus:
        """
        Compute overall system status from last checks.
        
        Returns:
            ServiceStatus representing worst-case status
        """
        if not self._last_checks:
            return ServiceStatus.UNKNOWN
        
        statuses = [r.status for r in self._last_checks.values()]
        
        if any(s == ServiceStatus.UNHEALTHY for s in statuses):
            return ServiceStatus.UNHEALTHY
        if any(s == ServiceStatus.DEGRADED for s in statuses):
            return ServiceStatus.DEGRADED
        if any(s == ServiceStatus.UNKNOWN for s in statuses):
            return ServiceStatus.UNKNOWN
        return ServiceStatus.HEALTHY
    
    def get_last_checks(self) -> Dict[str, Dict[str, Any]]:
        """Get dictionary of last check results for JSON serialization."""
        return {
            name: result.to_dict() 
            for name, result in self._last_checks.items()
        }
    
    async def close(self):
        """Clean up connections."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
        if self._pg_pool:
            await self._pg_pool.close()
            self._pg_pool = None


# Global instance for singleton pattern
_health_service: Optional[HealthService] = None


def get_health_service() -> HealthService:
    """Get or create the global health service instance."""
    global _health_service
    if _health_service is None:
        _health_service = HealthService()
    return _health_service

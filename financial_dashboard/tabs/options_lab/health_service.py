"""
Health Service for Alpaca Options Dashboard (Port 8053)

Provides health checks for:
- Redis cache connectivity
- TimescaleDB connection pool
- Data feed latency monitoring
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from collections import deque
import os

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class FeedStatus(Enum):
    """Data feed status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    STALE = "stale"
    ERROR = "error"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    service_name: str
    status: ServiceStatus
    latency_ms: float
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 2),
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class HealthService:
    """Centralized health check service for Alpaca Options Dashboard."""
    
    REDIS_LATENCY_WARN = 50.0
    REDIS_LATENCY_CRIT = 200.0
    TIMESCALE_LATENCY_WARN = 100.0
    TIMESCALE_LATENCY_CRIT = 500.0
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.timescale_dsn = os.getenv("TIMESCALE_DSN", "postgresql://postgres:postgres@localhost:5432/options_data")
        self._redis_client = None
        self._pg_pool = None
        self._last_checks: Dict[str, HealthCheckResult] = {}
        
    async def _get_redis_client(self):
        if self._redis_client is None:
            try:
                import redis.asyncio as redis
                self._redis_client = redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
            except ImportError:
                return None
        return self._redis_client
    
    async def _get_pg_pool(self):
        if self._pg_pool is None:
            try:
                import asyncpg
                self._pg_pool = await asyncpg.create_pool(self.timescale_dsn, min_size=1, max_size=5, command_timeout=5.0)
            except (ImportError, Exception):
                return None
        return self._pg_pool
    
    async def check_redis(self) -> HealthCheckResult:
        """Check Redis connectivity."""
        start = time.perf_counter()
        try:
            client = await self._get_redis_client()
            if client is None:
                return HealthCheckResult("redis", ServiceStatus.UNKNOWN, 0.0, "Redis not available", metadata={"error": "import"})
            
            pong = await asyncio.wait_for(client.ping(), timeout=2.0)
            latency_ms = (time.perf_counter() - start) * 1000
            
            if not pong:
                return HealthCheckResult("redis", ServiceStatus.UNHEALTHY, latency_ms, "PING failed")
            
            info = await client.info(section="server")
            status = ServiceStatus.UNHEALTHY if latency_ms > self.REDIS_LATENCY_CRIT else ServiceStatus.DEGRADED if latency_ms > self.REDIS_LATENCY_WARN else ServiceStatus.HEALTHY
            
            result = HealthCheckResult("redis", status, latency_ms, f"OK ({latency_ms:.1f}ms)",
                metadata={"redis_version": info.get("redis_version", "?"), "connected_clients": info.get("connected_clients", 0)})
        except asyncio.TimeoutError:
            result = HealthCheckResult("redis", ServiceStatus.UNHEALTHY, (time.perf_counter() - start) * 1000, "Timeout")
        except Exception as e:
            result = HealthCheckResult("redis", ServiceStatus.UNHEALTHY, (time.perf_counter() - start) * 1000, f"Error: {str(e)[:30]}")
        
        self._last_checks["redis"] = result
        return result
    
    async def check_timescaledb(self) -> HealthCheckResult:
        """Check TimescaleDB connectivity."""
        start = time.perf_counter()
        try:
            pool = await self._get_pg_pool()
            if pool is None:
                return HealthCheckResult("timescaledb", ServiceStatus.UNKNOWN, 0.0, "Pool not available")
            
            async with pool.acquire() as conn:
                val = await asyncio.wait_for(conn.fetchval("SELECT 1"), timeout=5.0)
                latency_ms = (time.perf_counter() - start) * 1000
                
                if val != 1:
                    return HealthCheckResult("timescaledb", ServiceStatus.UNHEALTHY, latency_ms, "Query failed")
                
                version = await conn.fetchval("SELECT version()")
                ts_ver = await conn.fetchval("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'")
            
            status = ServiceStatus.UNHEALTHY if latency_ms > self.TIMESCALE_LATENCY_CRIT else ServiceStatus.DEGRADED if latency_ms > self.TIMESCALE_LATENCY_WARN else ServiceStatus.HEALTHY
            result = HealthCheckResult("timescaledb", status, latency_ms, f"OK ({latency_ms:.1f}ms)",
                metadata={"pg_version": version[:40] if version else "?", "timescaledb_version": ts_ver or "N/A"})
        except asyncio.TimeoutError:
            result = HealthCheckResult("timescaledb", ServiceStatus.UNHEALTHY, (time.perf_counter() - start) * 1000, "Timeout")
        except Exception as e:
            result = HealthCheckResult("timescaledb", ServiceStatus.UNHEALTHY, (time.perf_counter() - start) * 1000, f"Error: {str(e)[:30]}")
        
        self._last_checks["timescaledb"] = result
        return result
    
    async def check_all(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks."""
        results = await asyncio.gather(self.check_redis(), self.check_timescaledb(), return_exceptions=True)
        output = {}
        for name, result in zip(["redis", "timescaledb"], results):
            if isinstance(result, Exception):
                output[name] = HealthCheckResult(name, ServiceStatus.UNHEALTHY, 0.0, f"Check failed: {str(result)[:30]}")
            else:
                output[name] = result
        return output
    
    def check_all_sync(self) -> Dict[str, Dict[str, Any]]:
        """Synchronous health check fallback for when async isn't possible."""
        results = {}
        
        # Check Redis synchronously
        try:
            import redis
            start = time.perf_counter()
            client = redis.from_url(self.redis_url, socket_timeout=2.0)
            pong = client.ping()
            latency_ms = (time.perf_counter() - start) * 1000
            
            if pong:
                status = "unhealthy" if latency_ms > self.REDIS_LATENCY_CRIT else "degraded" if latency_ms > self.REDIS_LATENCY_WARN else "healthy"
                info = client.info(section="server")
                results["redis"] = {
                    "service_name": "redis",
                    "status": status,
                    "latency_ms": round(latency_ms, 2),
                    "message": f"OK ({latency_ms:.1f}ms)",
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": {"redis_version": info.get("redis_version", "?"), "connected_clients": info.get("connected_clients", 0)}
                }
            else:
                results["redis"] = {"service_name": "redis", "status": "unhealthy", "latency_ms": latency_ms, "message": "PING failed"}
            client.close()
        except ImportError:
            results["redis"] = {"service_name": "redis", "status": "unavailable", "latency_ms": 0, "message": "Not Installed"}
        except Exception as e:
            # Clean up error messages for common cases
            err_str = str(e).lower()
            if "connection refused" in err_str or "111" in err_str:
                msg = "Service Not Running"
            elif "timeout" in err_str:
                msg = "Connection Timeout"
            elif "auth" in err_str or "password" in err_str:
                msg = "Auth Failed"
            else:
                msg = "Unavailable"
            results["redis"] = {"service_name": "redis", "status": "unavailable", "latency_ms": 0, "message": msg}
        
        # Check TimescaleDB synchronously
        try:
            import psycopg2
            start = time.perf_counter()
            conn = psycopg2.connect(self.timescale_dsn, connect_timeout=5)
            cur = conn.cursor()
            cur.execute("SELECT 1")
            val = cur.fetchone()[0]
            latency_ms = (time.perf_counter() - start) * 1000
            
            if val == 1:
                status = "unhealthy" if latency_ms > self.TIMESCALE_LATENCY_CRIT else "degraded" if latency_ms > self.TIMESCALE_LATENCY_WARN else "healthy"
                cur.execute("SELECT version()")
                pg_ver = cur.fetchone()[0][:40] if cur.rowcount else "?"
                results["timescaledb"] = {
                    "service_name": "timescaledb",
                    "status": status,
                    "latency_ms": round(latency_ms, 2),
                    "message": f"OK ({latency_ms:.1f}ms)",
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": {"pg_version": pg_ver}
                }
            else:
                results["timescaledb"] = {"service_name": "timescaledb", "status": "unhealthy", "latency_ms": latency_ms, "message": "Query failed"}
            cur.close()
            conn.close()
        except ImportError:
            results["timescaledb"] = {"service_name": "timescaledb", "status": "unavailable", "latency_ms": 0, "message": "Not Installed"}
        except Exception as e:
            # Clean up error messages for common cases
            err_str = str(e).lower()
            if "connection refused" in err_str or "111" in err_str:
                msg = "Service Not Running"
            elif "timeout" in err_str:
                msg = "Connection Timeout"
            elif "could not connect" in err_str or "no route" in err_str:
                msg = "Service Unavailable"
            elif "auth" in err_str or "password" in err_str:
                msg = "Auth Failed"
            else:
                msg = "Unavailable"
            results["timescaledb"] = {"service_name": "timescaledb", "status": "unavailable", "latency_ms": 0, "message": msg}
        
        return results
    
    def get_last_checks(self) -> Dict[str, Dict[str, Any]]:
        return {n: r.to_dict() for n, r in self._last_checks.items()}


class LatencyTracker:
    """Tracks latency samples with rolling window."""
    
    def __init__(self, window_size: int = 100, stale_seconds: float = 30.0):
        self.window_size = window_size
        self.stale_threshold = timedelta(seconds=stale_seconds)
        self._samples: deque = deque(maxlen=window_size)
        self._last_update: Optional[datetime] = None
        self._error_count: int = 0
        self._last_error: Optional[str] = None
    
    def record_sample(self, latency_ms: float):
        self._samples.append(latency_ms)
        self._last_update = datetime.utcnow()
    
    def record_error(self, msg: str):
        self._error_count += 1
        self._last_error = msg[:200]
    
    def get_status(self) -> FeedStatus:
        if self._last_update is None:
            return FeedStatus.DISCONNECTED
        if datetime.utcnow() - self._last_update > self.stale_threshold:
            return FeedStatus.STALE
        if self._error_count > 5:
            return FeedStatus.ERROR
        return FeedStatus.CONNECTED
    
    def get_stats(self) -> Dict[str, float]:
        if not self._samples:
            return {"avg": 0.0, "min": 0.0, "max": 0.0, "p95": 0.0}
        s = list(self._samples)
        ss = sorted(s)
        return {"avg": sum(s)/len(s), "min": min(s), "max": max(s), "p95": ss[int(len(ss)*0.95)] if len(ss) >= 20 else max(s)}
    
    def get_metrics(self, name: str) -> Dict[str, Any]:
        stats = self.get_stats()
        return {
            "feed_name": name,
            "status": self.get_status().value,
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "latency": {"avg_ms": round(stats["avg"], 2), "min_ms": round(stats["min"], 2), "max_ms": round(stats["max"], 2), "p95_ms": round(stats["p95"], 2)},
            "samples_count": len(self._samples),
            "error_count": self._error_count,
        }


class DataFetcher:
    """Manages data feed latency monitoring."""
    
    FEED_NAMES = ["market_quotes", "options_chain", "historical_bars", "news_feed", "volatility_surface"]
    
    def __init__(self):
        self._trackers: Dict[str, LatencyTracker] = {n: LatencyTracker() for n in self.FEED_NAMES}
        self._running = False
    
    async def record_latency(self, feed_name: str, latency_ms: float):
        if feed_name not in self._trackers:
            self._trackers[feed_name] = LatencyTracker()
        self._trackers[feed_name].record_sample(latency_ms)
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        return {n: t.get_metrics(n) for n, t in self._trackers.items()}
    
    def get_overall_status(self) -> str:
        statuses = [t.get_status() for t in self._trackers.values()]
        if FeedStatus.ERROR in statuses:
            return "error"
        if FeedStatus.DISCONNECTED in statuses:
            return "disconnected"
        if FeedStatus.STALE in statuses:
            return "stale"
        return "connected"
    
    async def simulate_activity(self, duration: float = 60.0):
        """Simulate feed activity for testing."""
        import random
        self._running = True
        start = time.time()
        while self._running and (time.time() - start) < duration:
            for feed in self.FEED_NAMES:
                base = {"market_quotes": 5, "options_chain": 15, "historical_bars": 25, "news_feed": 50, "volatility_surface": 100}.get(feed, 20)
                lat = base * (0.5 + random.random())
                if random.random() < 0.05:
                    lat *= 3
                await self.record_latency(feed, lat)
            await asyncio.sleep(1.0)
        self._running = False
    
    def stop_simulation(self):
        self._running = False


# Global instances
_health_service: Optional[HealthService] = None
_data_fetcher: Optional[DataFetcher] = None


def get_health_service() -> HealthService:
    global _health_service
    if _health_service is None:
        _health_service = HealthService()
    return _health_service


def get_data_fetcher() -> DataFetcher:
    global _data_fetcher
    if _data_fetcher is None:
        _data_fetcher = DataFetcher()
    return _data_fetcher

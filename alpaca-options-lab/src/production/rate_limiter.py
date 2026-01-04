"""
Alpaca Options Lab - Rate Limiter

API rate limiting implementations:
- Token bucket algorithm
- Sliding window
- Per-endpoint limits
- Distributed rate limiting
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class RateLimitExceeded(Exception):
    """Rate limit exceeded."""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        limit_name: str = "",
    ):
        super().__init__(message)
        self.retry_after = retry_after
        self.limit_name = limit_name


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    # Requests
    requests_per_second: float = 10.0
    requests_per_minute: float = 200.0
    requests_per_hour: float = 5000.0
    
    # Burst
    burst_size: int = 20
    
    # Behavior
    wait_for_token: bool = True  # Wait or raise exception
    max_wait_seconds: float = 30.0


@dataclass
class RateLimitStats:
    """Rate limit statistics."""
    total_requests: int = 0
    allowed_requests: int = 0
    throttled_requests: int = 0
    total_wait_time: float = 0.0
    
    current_rate: float = 0.0
    peak_rate: float = 0.0


class TokenBucket:
    """
    Token bucket rate limiter.
    
    - Allows bursts up to bucket capacity
    - Refills at constant rate
    - Simple and efficient
    """
    
    def __init__(
        self,
        rate: float = 10.0,  # Tokens per second
        capacity: int = 20,  # Maximum tokens
    ):
        self.rate = rate
        self.capacity = capacity
        
        # State
        self._tokens = float(capacity)
        self._last_update = time.monotonic()
        
        # Lock
        self._lock = asyncio.Lock()
        
        # Stats
        self._stats = RateLimitStats()
    
    async def acquire(
        self,
        tokens: int = 1,
        wait: bool = True,
        max_wait: float = 30.0,
    ) -> bool:
        """
        Acquire tokens.
        
        Args:
            tokens: Number of tokens to acquire
            wait: Wait for tokens if not available
            max_wait: Maximum wait time
        
        Returns:
            True if tokens acquired
        
        Raises:
            RateLimitExceeded: If wait=False and no tokens
        """
        async with self._lock:
            self._refill()
            
            if self._tokens >= tokens:
                self._tokens -= tokens
                self._stats.allowed_requests += 1
                self._stats.total_requests += 1
                return True
            
            if not wait:
                self._stats.throttled_requests += 1
                self._stats.total_requests += 1
                
                # Calculate retry_after
                needed = tokens - self._tokens
                retry_after = needed / self.rate
                
                raise RateLimitExceeded(
                    f"Rate limit exceeded, retry after {retry_after:.2f}s",
                    retry_after=retry_after,
                )
        
        # Wait for tokens
        start_wait = time.monotonic()
        
        while True:
            async with self._lock:
                self._refill()
                
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    wait_time = time.monotonic() - start_wait
                    self._stats.total_wait_time += wait_time
                    self._stats.allowed_requests += 1
                    self._stats.total_requests += 1
                    return True
            
            elapsed = time.monotonic() - start_wait
            if elapsed >= max_wait:
                self._stats.throttled_requests += 1
                self._stats.total_requests += 1
                raise RateLimitExceeded(
                    f"Rate limit exceeded after waiting {elapsed:.2f}s",
                    retry_after=0,
                )
            
            # Sleep until next token
            sleep_time = min(1.0 / self.rate, max_wait - elapsed)
            await asyncio.sleep(sleep_time)
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_update
        self._last_update = now
        
        # Add tokens based on rate
        new_tokens = elapsed * self.rate
        self._tokens = min(self.capacity, self._tokens + new_tokens)
    
    @property
    def available(self) -> float:
        """Available tokens (approximate)."""
        elapsed = time.monotonic() - self._last_update
        return min(self.capacity, self._tokens + elapsed * self.rate)
    
    @property
    def stats(self) -> RateLimitStats:
        """Get statistics."""
        return self._stats


class SlidingWindow:
    """
    Sliding window rate limiter.
    
    - Tracks exact request times
    - More accurate than token bucket
    - Higher memory usage
    """
    
    def __init__(
        self,
        limit: int = 100,  # Requests per window
        window_seconds: float = 60.0,  # Window size
    ):
        self.limit = limit
        self.window_seconds = window_seconds
        
        # Request timestamps
        self._requests: List[float] = []
        
        # Lock
        self._lock = asyncio.Lock()
        
        # Stats
        self._stats = RateLimitStats()
    
    async def acquire(
        self,
        wait: bool = True,
        max_wait: float = 30.0,
    ) -> bool:
        """
        Acquire permission for request.
        
        Args:
            wait: Wait if limit exceeded
            max_wait: Maximum wait time
        
        Returns:
            True if request allowed
        
        Raises:
            RateLimitExceeded: If wait=False and limit exceeded
        """
        async with self._lock:
            self._cleanup()
            
            if len(self._requests) < self.limit:
                self._requests.append(time.monotonic())
                self._stats.allowed_requests += 1
                self._stats.total_requests += 1
                self._update_rate()
                return True
            
            if not wait:
                self._stats.throttled_requests += 1
                self._stats.total_requests += 1
                
                # Calculate retry_after
                oldest = self._requests[0]
                retry_after = self.window_seconds - (time.monotonic() - oldest)
                
                raise RateLimitExceeded(
                    f"Rate limit exceeded ({len(self._requests)}/{self.limit})",
                    retry_after=max(0, retry_after),
                )
        
        # Wait for slot
        start_wait = time.monotonic()
        
        while True:
            async with self._lock:
                self._cleanup()
                
                if len(self._requests) < self.limit:
                    self._requests.append(time.monotonic())
                    wait_time = time.monotonic() - start_wait
                    self._stats.total_wait_time += wait_time
                    self._stats.allowed_requests += 1
                    self._stats.total_requests += 1
                    self._update_rate()
                    return True
                
                # Calculate wait time
                oldest = self._requests[0]
                wait_needed = self.window_seconds - (time.monotonic() - oldest)
            
            elapsed = time.monotonic() - start_wait
            if elapsed >= max_wait:
                self._stats.throttled_requests += 1
                self._stats.total_requests += 1
                raise RateLimitExceeded(
                    f"Rate limit exceeded after waiting {elapsed:.2f}s",
                    retry_after=0,
                )
            
            sleep_time = min(wait_needed + 0.01, max_wait - elapsed)
            await asyncio.sleep(max(0.01, sleep_time))
    
    def _cleanup(self) -> None:
        """Remove expired requests."""
        cutoff = time.monotonic() - self.window_seconds
        self._requests = [r for r in self._requests if r > cutoff]
    
    def _update_rate(self) -> None:
        """Update rate statistics."""
        if len(self._requests) >= 2:
            duration = self._requests[-1] - self._requests[0]
            if duration > 0:
                rate = len(self._requests) / duration
                self._stats.current_rate = rate
                self._stats.peak_rate = max(self._stats.peak_rate, rate)
    
    @property
    def current_count(self) -> int:
        """Current request count in window."""
        cutoff = time.monotonic() - self.window_seconds
        return len([r for r in self._requests if r > cutoff])
    
    @property
    def stats(self) -> RateLimitStats:
        """Get statistics."""
        return self._stats


class RateLimiter:
    """
    Composite rate limiter.
    
    Combines multiple limits:
    - Per-second
    - Per-minute
    - Per-hour
    - Burst handling
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        
        # Create limiters
        self._per_second = TokenBucket(
            rate=self.config.requests_per_second,
            capacity=self.config.burst_size,
        )
        
        self._per_minute = SlidingWindow(
            limit=int(self.config.requests_per_minute),
            window_seconds=60.0,
        )
        
        self._per_hour = SlidingWindow(
            limit=int(self.config.requests_per_hour),
            window_seconds=3600.0,
        )
        
        # Endpoint-specific limiters
        self._endpoint_limiters: Dict[str, TokenBucket] = {}
        
        logger.info("RateLimiter initialized")
    
    async def acquire(
        self,
        endpoint: Optional[str] = None,
        tokens: int = 1,
    ) -> bool:
        """
        Acquire permission for request.
        
        Args:
            endpoint: Optional endpoint for specific limits
            tokens: Number of tokens to consume
        
        Returns:
            True if request allowed
        
        Raises:
            RateLimitExceeded: If any limit exceeded
        """
        wait = self.config.wait_for_token
        max_wait = self.config.max_wait_seconds
        
        # Check all limits
        await self._per_second.acquire(tokens=tokens, wait=wait, max_wait=max_wait)
        await self._per_minute.acquire(wait=wait, max_wait=max_wait)
        await self._per_hour.acquire(wait=wait, max_wait=max_wait)
        
        # Check endpoint-specific limit
        if endpoint and endpoint in self._endpoint_limiters:
            await self._endpoint_limiters[endpoint].acquire(
                tokens=tokens, wait=wait, max_wait=max_wait
            )
        
        return True
    
    def set_endpoint_limit(
        self,
        endpoint: str,
        rate: float,
        capacity: int = 10,
    ) -> None:
        """Set rate limit for specific endpoint."""
        self._endpoint_limiters[endpoint] = TokenBucket(
            rate=rate,
            capacity=capacity,
        )
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator for rate-limited functions."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            await self.acquire()
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)
        
        return wrapper
    
    def get_status(self) -> Dict[str, Any]:
        """Get rate limiter status."""
        return {
            "per_second": {
                "available": self._per_second.available,
                "stats": {
                    "total": self._per_second.stats.total_requests,
                    "allowed": self._per_second.stats.allowed_requests,
                    "throttled": self._per_second.stats.throttled_requests,
                },
            },
            "per_minute": {
                "current_count": self._per_minute.current_count,
                "limit": self._per_minute.limit,
                "stats": {
                    "total": self._per_minute.stats.total_requests,
                    "throttled": self._per_minute.stats.throttled_requests,
                },
            },
            "per_hour": {
                "current_count": self._per_hour.current_count,
                "limit": self._per_hour.limit,
            },
            "endpoint_limits": list(self._endpoint_limiters.keys()),
        }


class AlpacaRateLimiter(RateLimiter):
    """
    Rate limiter configured for Alpaca API limits.
    
    Default limits:
    - Trading: 200 requests/minute
    - Data: 200 requests/minute per symbol
    - Account: 200 requests/minute
    """
    
    def __init__(self):
        config = RateLimitConfig(
            requests_per_second=3.33,  # ~200/min
            requests_per_minute=200,
            requests_per_hour=10000,
            burst_size=10,
            wait_for_token=True,
            max_wait_seconds=60.0,
        )
        super().__init__(config)
        
        # Set endpoint-specific limits
        self.set_endpoint_limit("orders", rate=3.33, capacity=10)
        self.set_endpoint_limit("positions", rate=3.33, capacity=10)
        self.set_endpoint_limit("account", rate=3.33, capacity=10)
        self.set_endpoint_limit("market_data", rate=10.0, capacity=20)

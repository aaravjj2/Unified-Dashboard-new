"""
Alpaca Options Lab - Circuit Breaker

Fault tolerance pattern implementation:
- Automatic failure detection
- State transitions (closed -> open -> half-open)
- Configurable thresholds
- Async support
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic
import time

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker state."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreakerError(Exception):
    """Circuit breaker is open."""
    
    def __init__(self, message: str, circuit_name: str = ""):
        super().__init__(message)
        self.circuit_name = circuit_name


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    # Failure threshold
    failure_threshold: int = 5  # Opens after this many failures
    failure_window_seconds: int = 60  # Window for counting failures
    
    # Recovery
    reset_timeout_seconds: int = 30  # Time in open state before half-open
    half_open_max_calls: int = 3  # Max calls in half-open state
    success_threshold: int = 2  # Successes needed to close
    
    # Timeout
    call_timeout_seconds: Optional[float] = None  # Timeout for calls
    
    # Exceptions
    excluded_exceptions: List[type] = field(default_factory=list)  # Don't count these


@dataclass
class CircuitStats:
    """Circuit breaker statistics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    
    # Recent failures
    failures_in_window: int = 0
    last_failure_time: Optional[datetime] = None
    
    # State tracking
    state_changes: int = 0
    last_state_change: Optional[datetime] = None
    time_in_current_state: float = 0.0


class CircuitBreaker:
    """
    Circuit breaker for fault tolerance.
    
    Prevents cascading failures by:
    - Tracking failure rate
    - Opening circuit on threshold breach
    - Allowing gradual recovery
    """
    
    def __init__(
        self,
        name: str = "default",
        config: Optional[CircuitBreakerConfig] = None,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # State
        self._state = CircuitState.CLOSED
        self._state_changed_at = datetime.now(timezone.utc)
        
        # Failure tracking
        self._failures: List[datetime] = []
        self._half_open_calls = 0
        self._half_open_successes = 0
        
        # Statistics
        self._stats = CircuitStats()
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        logger.info(f"CircuitBreaker '{name}' initialized")
    
    # -------------------- Properties --------------------
    
    @property
    def state(self) -> CircuitState:
        """Current state."""
        return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (rejecting calls)."""
        return self._state == CircuitState.OPEN
    
    @property
    def stats(self) -> CircuitStats:
        """Get statistics."""
        self._update_stats()
        return self._stats
    
    # -------------------- State Management --------------------
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to new state."""
        old_state = self._state
        
        if old_state == new_state:
            return
        
        self._state = new_state
        self._state_changed_at = datetime.now(timezone.utc)
        self._stats.state_changes += 1
        self._stats.last_state_change = self._state_changed_at
        
        # Reset half-open counters
        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._half_open_successes = 0
        
        logger.info(
            f"CircuitBreaker '{self.name}': {old_state.value} -> {new_state.value}"
        )
    
    def _should_open(self) -> bool:
        """Check if circuit should open."""
        # Count recent failures
        now = datetime.now(timezone.utc)
        window_start = now.timestamp() - self.config.failure_window_seconds
        
        recent_failures = [
            f for f in self._failures
            if f.timestamp() > window_start
        ]
        
        self._stats.failures_in_window = len(recent_failures)
        
        return len(recent_failures) >= self.config.failure_threshold
    
    def _should_attempt_reset(self) -> bool:
        """Check if should attempt reset (open -> half-open)."""
        if self._state != CircuitState.OPEN:
            return False
        
        elapsed = (datetime.now(timezone.utc) - self._state_changed_at).total_seconds()
        return elapsed >= self.config.reset_timeout_seconds
    
    def _record_success(self) -> None:
        """Record successful call."""
        self._stats.successful_calls += 1
        
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_successes += 1
            
            # Check if recovered
            if self._half_open_successes >= self.config.success_threshold:
                self._transition_to(CircuitState.CLOSED)
                self._failures.clear()
    
    def _record_failure(self, error: Exception) -> None:
        """Record failed call."""
        # Check if exception should be excluded
        if type(error) in self.config.excluded_exceptions:
            return
        
        self._failures.append(datetime.now(timezone.utc))
        self._stats.failed_calls += 1
        self._stats.last_failure_time = datetime.now(timezone.utc)
        
        if self._state == CircuitState.CLOSED:
            if self._should_open():
                self._transition_to(CircuitState.OPEN)
        
        elif self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open goes back to open
            self._transition_to(CircuitState.OPEN)
    
    def _update_stats(self) -> None:
        """Update statistics."""
        if self._state_changed_at:
            self._stats.time_in_current_state = (
                datetime.now(timezone.utc) - self._state_changed_at
            ).total_seconds()
    
    # -------------------- Call Execution --------------------
    
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to call (sync or async)
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Function result
        
        Raises:
            CircuitBreakerError: If circuit is open
        """
        async with self._lock:
            # Check state
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to(CircuitState.HALF_OPEN)
                else:
                    self._stats.rejected_calls += 1
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is open",
                        circuit_name=self.name,
                    )
            
            # Check half-open call limit
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    self._stats.rejected_calls += 1
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' half-open limit reached",
                        circuit_name=self.name,
                    )
                self._half_open_calls += 1
        
        # Execute call
        self._stats.total_calls += 1
        
        try:
            # Handle timeout
            if self.config.call_timeout_seconds:
                if asyncio.iscoroutinefunction(func):
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=self.config.call_timeout_seconds,
                    )
                else:
                    # Run sync function with timeout in executor
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: func(*args, **kwargs)),
                        timeout=self.config.call_timeout_seconds,
                    )
            else:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
            
            async with self._lock:
                self._record_success()
            
            return result
            
        except Exception as e:
            async with self._lock:
                self._record_failure(e)
            raise
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator for protecting functions."""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.get_event_loop().run_until_complete(
                self.call(func, *args, **kwargs)
            )
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    # -------------------- Manual Control --------------------
    
    def reset(self) -> None:
        """Manually reset circuit to closed state."""
        self._transition_to(CircuitState.CLOSED)
        self._failures.clear()
        self._half_open_calls = 0
        self._half_open_successes = 0
        logger.info(f"CircuitBreaker '{self.name}' manually reset")
    
    def trip(self) -> None:
        """Manually open circuit."""
        self._transition_to(CircuitState.OPEN)
        logger.info(f"CircuitBreaker '{self.name}' manually tripped")
    
    # -------------------- Status --------------------
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        self._update_stats()
        
        return {
            "name": self.name,
            "state": self._state.value,
            "total_calls": self._stats.total_calls,
            "successful_calls": self._stats.successful_calls,
            "failed_calls": self._stats.failed_calls,
            "rejected_calls": self._stats.rejected_calls,
            "failures_in_window": self._stats.failures_in_window,
            "state_changes": self._stats.state_changes,
            "time_in_current_state": self._stats.time_in_current_state,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "failure_window_seconds": self.config.failure_window_seconds,
                "reset_timeout_seconds": self.config.reset_timeout_seconds,
            },
        }


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    _instance: Optional['CircuitBreakerRegistry'] = None
    _breakers: Dict[str, CircuitBreaker] = {}
    
    @classmethod
    def get_instance(cls) -> 'CircuitBreakerRegistry':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def get_breaker(
        cls,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Get or create circuit breaker."""
        if name not in cls._breakers:
            cls._breakers[name] = CircuitBreaker(name, config)
        return cls._breakers[name]
    
    @classmethod
    def get_all_status(cls) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {
            name: breaker.get_status()
            for name, breaker in cls._breakers.items()
        }
    
    @classmethod
    def reset_all(cls) -> None:
        """Reset all circuit breakers."""
        for breaker in cls._breakers.values():
            breaker.reset()

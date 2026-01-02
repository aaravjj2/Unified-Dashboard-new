"""
Circuit Breaker Pattern for API calls

Prevents cascade failures when external APIs are down.
"""

import time
import logging
import threading
from enum import Enum
from typing import Callable, Any, Optional
from dataclasses import dataclass
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitStats:
    """Circuit breaker statistics."""
    state: CircuitState
    failures: int
    successes: int
    last_failure_time: Optional[float]
    last_success_time: Optional[float]
    total_calls: int
    rejected_calls: int
    
    def to_dict(self):
        return {
            'state': self.state.value,
            'failures': self.failures,
            'successes': self.successes,
            'total_calls': self.total_calls,
            'rejected_calls': self.rejected_calls,
            'last_failure': self.last_failure_time,
            'last_success': self.last_success_time
        }


class CircuitBreaker:
    """
    Circuit breaker implementation for external API calls.
    
    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Too many failures, calls are rejected immediately
    - HALF_OPEN: Testing if service recovered
    
    Usage:
        breaker = CircuitBreaker(
            name="alpaca_api",
            failure_threshold=5,
            recovery_timeout=60,
            success_threshold=2
        )
        
        @breaker
        def call_api():
            return requests.get(url)
        
        # Or manually:
        result = breaker.call(call_api)
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
        excluded_exceptions: tuple = ()
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Identifier for this breaker
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before trying again
            success_threshold: Successes needed to close circuit
            excluded_exceptions: Exceptions that don't count as failures
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.excluded_exceptions = excluded_exceptions
        
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._successes = 0
        self._last_failure_time: Optional[float] = None
        self._last_success_time: Optional[float] = None
        self._total_calls = 0
        self._rejected_calls = 0
        self._lock = threading.RLock()
        
        logger.info(f"⚡ Circuit breaker '{name}' initialized "
                   f"(threshold={failure_threshold}, timeout={recovery_timeout}s)")
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    logger.info(f"⚡ Circuit '{self.name}' transitioning to HALF_OPEN")
            return self._state
    
    @property
    def stats(self) -> CircuitStats:
        """Get circuit statistics."""
        with self._lock:
            return CircuitStats(
                state=self._state,
                failures=self._failures,
                successes=self._successes,
                last_failure_time=self._last_failure_time,
                last_success_time=self._last_success_time,
                total_calls=self._total_calls,
                rejected_calls=self._rejected_calls
            )
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try recovery."""
        if self._last_failure_time is None:
            return True
        return time.time() - self._last_failure_time >= self.recovery_timeout
    
    def _record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            self._successes += 1
            self._last_success_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                if self._successes >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failures = 0
                    self._successes = 0
                    logger.info(f"⚡ Circuit '{self.name}' CLOSED (service recovered)")
    
    def _record_failure(self, exc: Exception) -> None:
        """Record a failed call."""
        with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                # Immediate transition back to OPEN
                self._state = CircuitState.OPEN
                logger.warning(f"⚡ Circuit '{self.name}' OPEN (recovery failed: {exc})")
            elif self._failures >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(f"⚡ Circuit '{self.name}' OPEN "
                             f"(threshold={self.failure_threshold} reached)")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitOpenError: If circuit is open
            Original exception: If call fails
        """
        with self._lock:
            self._total_calls += 1
            
            current_state = self.state  # This may transition OPEN -> HALF_OPEN
            
            if current_state == CircuitState.OPEN:
                self._rejected_calls += 1
                raise CircuitOpenError(
                    f"Circuit '{self.name}' is OPEN. "
                    f"Try again in {self.recovery_timeout}s"
                )
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except self.excluded_exceptions:
            # These exceptions don't count as failures
            raise
        except Exception as e:
            self._record_failure(e)
            raise
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator usage."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper
    
    def reset(self) -> None:
        """Manually reset circuit to CLOSED state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failures = 0
            self._successes = 0
            logger.info(f"⚡ Circuit '{self.name}' manually reset")
    
    def force_open(self) -> None:
        """Manually open circuit (for testing/maintenance)."""
        with self._lock:
            self._state = CircuitState.OPEN
            self._last_failure_time = time.time()
            logger.info(f"⚡ Circuit '{self.name}' manually opened")


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# Global circuit breakers for different services
_breakers: dict = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    success_threshold: int = 2
) -> CircuitBreaker:
    """
    Get or create a named circuit breaker.
    
    Args:
        name: Unique name for the breaker
        failure_threshold: Failures before opening
        recovery_timeout: Seconds before retry
        success_threshold: Successes to close
        
    Returns:
        CircuitBreaker instance
    """
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold
        )
    return _breakers[name]


def get_all_breaker_stats() -> dict:
    """Get stats for all circuit breakers."""
    return {name: breaker.stats.to_dict() for name, breaker in _breakers.items()}


# Convenience decorators
def with_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60
):
    """
    Decorator to wrap function with circuit breaker.
    
    Usage:
        @with_circuit_breaker("my_api", failure_threshold=3)
        def call_external_api():
            return requests.get(url)
    """
    def decorator(func: Callable) -> Callable:
        breaker = get_circuit_breaker(name, failure_threshold, recovery_timeout)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        # Attach breaker reference for inspection
        wrapper.circuit_breaker = breaker
        return wrapper
    
    return decorator

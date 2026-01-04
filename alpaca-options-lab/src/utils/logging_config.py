"""
Alpaca Options Lab - Structured Logging Module

Production-grade logging with:
- JSON structured output for log aggregation
- Correlation ID propagation for request tracing
- Context binding for rich log metadata
- Performance-optimized lazy evaluation
- Automatic fallback to standard logging when structlog unavailable

Usage:
    from src.utils.logging_config import get_logger, bind_context
    
    logger = get_logger(__name__)
    logger.info("Processing order", order_id="12345", symbol="AAPL")
"""
from __future__ import annotations

import logging
import logging.handlers
import sys
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Generator, Optional, TypeVar, cast

# Try to import structlog, fallback to standard logging
try:
    import structlog
    from structlog.types import FilteringBoundLogger, Processor
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False
    FilteringBoundLogger = Any  # type: ignore
    Processor = Any  # type: ignore

# Type variable for decorator
F = TypeVar("F", bound=Callable[..., Any])

# Context variables for request tracing
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
_request_context: ContextVar[Dict[str, Any]] = ContextVar("request_context", default={})

# Track if logging has been configured
_logging_configured = False


def get_correlation_id() -> str:
    """Get or create a correlation ID for the current context."""
    cid = _correlation_id.get()
    if cid is None:
        cid = str(uuid.uuid4())[:8]
        _correlation_id.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Set the correlation ID for the current context."""
    _correlation_id.set(cid)


@contextmanager
def correlation_context(cid: Optional[str] = None) -> Generator[str, None, None]:
    """Context manager for correlation ID scope."""
    old_cid = _correlation_id.get()
    new_cid = cid or str(uuid.uuid4())[:8]
    _correlation_id.set(new_cid)
    try:
        yield new_cid
    finally:
        _correlation_id.set(old_cid)


def bind_context(**kwargs: Any) -> None:
    """Bind additional context to the current request scope."""
    ctx = _request_context.get().copy()
    ctx.update(kwargs)
    _request_context.set(ctx)


def clear_context() -> None:
    """Clear the request context."""
    _request_context.set({})


# ================== Standard Library Logger Wrapper ==================

class StandardLogger:
    """
    Wrapper around standard library logger that provides
    structlog-like interface with keyword arguments.
    """
    
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
        self._context: Dict[str, Any] = {}
    
    def bind(self, **kwargs: Any) -> "StandardLogger":
        """Bind context to logger."""
        new_logger = StandardLogger(self._logger.name)
        new_logger._context = {**self._context, **kwargs}
        return new_logger
    
    def _format_message(self, event: str, **kwargs: Any) -> str:
        """Format log message with context."""
        all_context = {**self._context, **_request_context.get(), **kwargs}
        if all_context:
            context_str = " ".join(f"{k}={v}" for k, v in all_context.items())
            return f"{event} | {context_str}"
        return event
    
    def debug(self, event: str = "", **kwargs: Any) -> None:
        self._logger.debug(self._format_message(event, **kwargs))
    
    def info(self, event: str = "", **kwargs: Any) -> None:
        self._logger.info(self._format_message(event, **kwargs))
    
    def warning(self, event: str = "", **kwargs: Any) -> None:
        self._logger.warning(self._format_message(event, **kwargs))
    
    def error(self, event: str = "", **kwargs: Any) -> None:
        self._logger.error(self._format_message(event, **kwargs))
    
    def critical(self, event: str = "", **kwargs: Any) -> None:
        self._logger.critical(self._format_message(event, **kwargs))
    
    def exception(self, event: str = "", **kwargs: Any) -> None:
        self._logger.exception(self._format_message(event, **kwargs))


# ================== Structlog Processors (conditional) ==================

if STRUCTLOG_AVAILABLE:
    def _add_correlation_id(
        logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Processor to add correlation ID to log events."""
        event_dict["correlation_id"] = get_correlation_id()
        return event_dict

    def _add_request_context(
        logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Processor to add request context to log events."""
        ctx = _request_context.get()
        if ctx:
            event_dict.update(ctx)
        return event_dict

    def _add_timestamp(
        logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Processor to add ISO timestamp."""
        event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
        return event_dict


def configure_logging(
    log_level: str = "INFO",
    json_format: bool = False,
    log_file: Optional[str] = None,
    add_correlation_id: bool = True,
) -> None:
    """
    Configure the logging system for the application.
    
    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON format (True) or console format (False)
        log_file: Optional path to log file
        add_correlation_id: Whether to add correlation IDs to log entries
    """
    global _logging_configured
    
    if _logging_configured:
        return
    
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    if STRUCTLOG_AVAILABLE:
        # Use structlog
        processors: list[Processor] = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            _add_timestamp,
        ]
        
        if add_correlation_id:
            processors.append(_add_correlation_id)
            processors.append(_add_request_context)
        
        processors.extend([
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
        ])
        
        if json_format:
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer(colors=True))
        
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    # Configure standard library logging
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10_485_760,  # 10MB
            backupCount=5,
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    _logging_configured = True


def get_logger(name: str) -> Any:
    """
    Get a structured logger for the given module name.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Configured logger (structlog or standard library wrapper)
    """
    # Ensure logging is configured
    if not _logging_configured:
        configure_logging()
    
    if STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    else:
        return StandardLogger(name)


def log_execution_time(logger: Optional[Any] = None) -> Callable[[F], F]:
    """
    Decorator to log function execution time.
    
    Usage:
        @log_execution_time()
        def my_function():
            ...
    """
    def decorator(func: F) -> F:
        _logger = logger or get_logger(func.__module__)
        
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = datetime.now(timezone.utc)
            try:
                result = func(*args, **kwargs)
                elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                _logger.debug(
                    "Function executed",
                    function=func.__name__,
                    elapsed_ms=round(elapsed_ms, 2),
                    status="success",
                )
                return result
            except Exception as e:
                elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                _logger.error(
                    "Function failed",
                    function=func.__name__,
                    elapsed_ms=round(elapsed_ms, 2),
                    status="error",
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                raise
        
        return cast(F, wrapper)
    
    return decorator


class LogContext:
    """
    Context manager for scoped logging context.
    
    Usage:
        with LogContext(operation="order_processing", order_id="12345"):
            logger.info("Processing started")
            # ... do work ...
            logger.info("Processing complete")
    """
    
    def __init__(self, **kwargs: Any) -> None:
        self._context = kwargs
        self._token: Optional[Any] = None
    
    def __enter__(self) -> "LogContext":
        bind_context(**self._context)
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        # Context is automatically cleared when the coroutine/thread completes
        pass

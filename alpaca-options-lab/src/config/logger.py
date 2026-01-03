"""
System Logger - Phase 4: Reliability Layer
==========================================
Centralized logging with colored console + file output.

Format: [TIME] [LEVEL] [MODULE] Message

Features:
- Colored console output (production terminals)
- File logging to reports/logs/system.log
- Rotation to prevent unbounded growth
- API call tracing support
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional
from pathlib import Path

# =============================================================================
# COLOR CODES (ANSI)
# =============================================================================

class LogColors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Level colors
    DEBUG = "\033[36m"      # Cyan
    INFO = "\033[32m"       # Green
    WARNING = "\033[33m"    # Yellow
    ERROR = "\033[31m"      # Red
    CRITICAL = "\033[35m"   # Magenta (bold)
    
    # Component colors
    TIME = "\033[90m"       # Gray
    MODULE = "\033[34m"     # Blue
    
    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """Apply color to text."""
        return f"{color}{text}{cls.RESET}"


# =============================================================================
# CUSTOM FORMATTERS
# =============================================================================

class ColoredConsoleFormatter(logging.Formatter):
    """
    Custom formatter with colored output for console.
    
    Format: [TIME] [LEVEL] [MODULE] Message
    """
    
    LEVEL_COLORS = {
        logging.DEBUG: LogColors.DEBUG,
        logging.INFO: LogColors.INFO,
        logging.WARNING: LogColors.WARNING,
        logging.ERROR: LogColors.ERROR,
        logging.CRITICAL: LogColors.CRITICAL,
    }
    
    LEVEL_ICONS = {
        logging.DEBUG: "🔍",
        logging.INFO: "ℹ️ ",
        logging.WARNING: "⚠️ ",
        logging.ERROR: "❌",
        logging.CRITICAL: "🔥",
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # Get level color
        level_color = self.LEVEL_COLORS.get(record.levelno, LogColors.RESET)
        level_icon = self.LEVEL_ICONS.get(record.levelno, "")
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]
        colored_time = LogColors.colorize(f"[{timestamp}]", LogColors.TIME)
        
        # Format level
        level_name = f"[{record.levelname:8}]"
        colored_level = LogColors.colorize(level_name, level_color)
        
        # Format module
        module_name = f"[{record.name[:20]:20}]"
        colored_module = LogColors.colorize(module_name, LogColors.MODULE)
        
        # Format message
        message = record.getMessage()
        if record.levelno >= logging.ERROR:
            message = LogColors.colorize(message, level_color)
        
        # Combine with icon
        return f"{level_icon} {colored_time} {colored_level} {colored_module} {message}"


class FileFormatter(logging.Formatter):
    """
    Plain text formatter for file output.
    
    Format: [TIME] [LEVEL] [MODULE] Message
    """
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        level_name = f"[{record.levelname:8}]"
        module_name = f"[{record.name[:25]:25}]"
        message = record.getMessage()
        
        # Include exception info if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"
        
        return f"[{timestamp}] {level_name} {module_name} {message}"


# =============================================================================
# LOGGER CONFIGURATION
# =============================================================================

def get_log_file_path() -> Path:
    """Get the path to the system log file."""
    # Find project root (contains reports/ directory)
    current = Path(__file__).resolve()
    
    for parent in [current] + list(current.parents):
        if (parent / "reports").exists():
            log_dir = parent / "reports" / "logs"
            break
    else:
        # Fallback to current directory
        log_dir = Path.cwd() / "reports" / "logs"
    
    # Ensure directory exists
    log_dir.mkdir(parents=True, exist_ok=True)
    
    return log_dir / "system.log"


def setup_system_logger(
    level: int = logging.INFO,
    console_level: Optional[int] = None,
    file_level: Optional[int] = None,
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Setup the centralized system logger.
    
    Args:
        level: Base logging level
        console_level: Console handler level (defaults to level)
        file_level: File handler level (defaults to level)
        log_file: Custom log file path
        max_file_size: Max log file size before rotation (bytes)
        backup_count: Number of backup files to keep
        
    Returns:
        Configured root logger
    """
    console_level = console_level or level
    file_level = file_level or level
    log_path = Path(log_file) if log_file else get_log_file_path()
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(min(console_level, file_level))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(ColoredConsoleFormatter())
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    try:
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(FileFormatter())
        root_logger.addHandler(file_handler)
        
        # Log initialization
        root_logger.info(f"📋 System logger initialized: {log_path}")
        
    except Exception as e:
        root_logger.warning(f"Could not setup file logging: {e}")
    
    return root_logger


def get_module_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Usage:
        from financial_dashboard.config.logger import get_module_logger
        logger = get_module_logger(__name__)
        logger.info("Module initialized")
    """
    return logging.getLogger(name)


# =============================================================================
# API CALL TRACING
# =============================================================================

class APICallTracer:
    """
    Context manager for tracing API calls.
    
    Usage:
        with APICallTracer("Finnhub", "sentiment", symbol="NVDA"):
            response = finnhub_client.get_sentiment("NVDA")
    """
    
    def __init__(self, api_name: str, endpoint: str, **kwargs):
        self.api_name = api_name
        self.endpoint = endpoint
        self.kwargs = kwargs
        self.logger = logging.getLogger("api.trace")
        self.start_time: Optional[float] = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        
        params = ", ".join(f"{k}={v}" for k, v in self.kwargs.items())
        self.logger.debug(f"📡 API CALL: {self.api_name}.{self.endpoint}({params})")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        elapsed = (time.time() - self.start_time) * 1000  # ms
        
        if exc_type:
            self.logger.error(
                f"❌ API FAIL: {self.api_name}.{self.endpoint} "
                f"({elapsed:.1f}ms) - {exc_type.__name__}: {exc_val}"
            )
        else:
            status = "OK" if elapsed < 1000 else "SLOW"
            icon = "✅" if status == "OK" else "🐢"
            self.logger.debug(
                f"{icon} API {status}: {self.api_name}.{self.endpoint} "
                f"({elapsed:.1f}ms)"
            )
        
        return False  # Don't suppress exceptions


def log_api_call(api_name: str, endpoint: str, **kwargs) -> APICallTracer:
    """Helper function to create API call tracer."""
    return APICallTracer(api_name, endpoint, **kwargs)


# =============================================================================
# STARTUP LOG BANNER
# =============================================================================

def log_startup_banner(version: str = "1.0.0", phase: str = "Phase 4"):
    """Log a startup banner with system info."""
    logger = logging.getLogger("system.startup")
    
    banner = f"""
╔══════════════════════════════════════════════════════════════╗
║                   ALPACA OPTIONS LAB                         ║
║                   {phase} - Reliability Layer                ║
║                   Version {version:10}                       ║
╠══════════════════════════════════════════════════════════════╣
║  Port: 8053                                                  ║
║  Theme: Alpaca Dark                                          ║
║  Status: Starting...                                         ║
╚══════════════════════════════════════════════════════════════╝
"""
    
    for line in banner.strip().split('\n'):
        logger.info(line)


# =============================================================================
# SYSTEM HEALTH LOGGING
# =============================================================================

def log_health_status(
    api_statuses: dict,
    math_integrity: bool,
    error_count: int = 0
):
    """Log system health status."""
    logger = logging.getLogger("system.health")
    
    status_icons = {True: "🟢", False: "🔴", None: "🟡"}
    
    logger.info("═══════════════ HEALTH CHECK ═══════════════")
    
    # API Statuses
    for api, status in api_statuses.items():
        icon = status_icons.get(status, "⚪")
        state = "Online" if status else "Offline" if status is False else "Unknown"
        logger.info(f"  {icon} {api:15} : {state}")
    
    # Math Integrity
    math_icon = status_icons[math_integrity]
    logger.info(f"  {math_icon} {'Math Integrity':15} : {'PASS' if math_integrity else 'FAIL'}")
    
    # Error Count
    error_icon = "🟢" if error_count == 0 else "🟡" if error_count < 10 else "🔴"
    logger.info(f"  {error_icon} {'Recent Errors':15} : {error_count}")
    
    logger.info("═════════════════════════════════════════════")


# =============================================================================
# AUTO-INITIALIZE ON IMPORT
# =============================================================================

# Initialize logger on first import
_initialized = False

def ensure_initialized():
    """Ensure logger is initialized."""
    global _initialized
    if not _initialized:
        setup_system_logger(level=logging.INFO)
        _initialized = True


# Initialize on import
ensure_initialized()


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Test the logger
    setup_system_logger(level=logging.DEBUG)
    
    log_startup_banner()
    
    logger = get_module_logger("test.module")
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Test API tracing
    with log_api_call("Finnhub", "sentiment", symbol="NVDA"):
        import time
        time.sleep(0.1)  # Simulate API call
    
    # Test health logging
    log_health_status(
        api_statuses={"Alpaca": True, "Finnhub": True, "Tiingo": None},
        math_integrity=True,
        error_count=0
    )
    
    print("\n✅ Logger test completed! Check reports/logs/system.log")


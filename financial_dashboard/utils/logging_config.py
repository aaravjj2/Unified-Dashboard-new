"""Logging Configuration Module"""
import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 5
LOG_LEVELS = {'DEBUG': logging.DEBUG, 'INFO': logging.INFO, 'WARNING': logging.WARNING, 'ERROR': logging.ERROR, 'CRITICAL': logging.CRITICAL}

def setup_logging(service_name, log_level="INFO", log_to_file=True, log_to_console=True, max_bytes=DEFAULT_MAX_BYTES, backup_count=DEFAULT_BACKUP_COUNT):
    LOG_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger(service_name)
    logger.setLevel(LOG_LEVELS.get(log_level.upper(), logging.INFO))
    logger.handlers.clear()
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    if log_to_file:
        log_file = LOG_DIR / f"{service_name}.log"
        file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
        file_handler.setLevel(LOG_LEVELS.get(log_level.upper(), logging.INFO))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(LOG_LEVELS.get(log_level.upper(), logging.INFO))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    logger.propagate = False
    return logger

def log_performance(logger, operation, duration):
    logger.info(f"Performance: {operation} completed in {duration:.3f}s")

def log_api_request(logger, method, path, status_code, duration):
    status_emoji = "OK" if 200 <= status_code < 300 else "ERR"
    logger.info(f"{status_emoji} {method} {path} -> {status_code} ({duration:.3f}s)")

def log_error_with_context(logger, error, context=None):
    context_str = ""
    if context:
        context_items = [f"{k}={v}" for k, v in context.items()]
        context_str = f" | Context: {', '.join(context_items)}"
    logger.error(f"Error: {type(error).__name__}: {str(error)}{context_str}", exc_info=True)

def get_log_level_from_env(default="INFO"):
    level_name = os.getenv('LOG_LEVEL', default).upper()
    return LOG_LEVELS.get(level_name, logging.INFO)

LOG_DIR.mkdir(exist_ok=True)

"""
Monitoring Module - Phase 5 TradeOps

Provides market monitoring, alert generation, and watchdog services.
"""

from .watchdog import (
    MarketWatchdog,
    Alert,
    AlertType,
    AlertSeverity,
    get_watchdog
)

__all__ = [
    'MarketWatchdog',
    'Alert',
    'AlertType',
    'AlertSeverity',
    'get_watchdog'
]

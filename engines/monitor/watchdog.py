"""
Market Watchdog - Phase 5 TradeOps

Monitors market conditions and generates alerts:
- IV_SPIKE: Implied volatility increase >50%
- PRICE_GAP: Price gap >2% from previous close
- VOLUME_SURGE: Unusual volume activity
- POSITION_ALERT: Position-specific warnings

Alerts are logged locally and published to UI feed.
"""

import os
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set
from collections import deque

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Types of market alerts."""
    IV_SPIKE = "iv_spike"
    PRICE_GAP = "price_gap"
    VOLUME_SURGE = "volume_surge"
    POSITION_ALERT = "position_alert"
    RISK_WARNING = "risk_warning"
    ORDER_FILL = "order_fill"
    ORDER_REJECT = "order_reject"
    SYSTEM_INFO = "system_info"
    MARKET_CLOSE = "market_close"
    EARNINGS_WARNING = "earnings_warning"


class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "critical"  # Immediate action required
    WARNING = "warning"    # Attention needed
    INFO = "info"          # Informational


@dataclass
class Alert:
    """Alert record."""
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    ticker: Optional[str]
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "ticker": self.ticker,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "acknowledged": self.acknowledged
        }
    
    @property
    def color(self) -> str:
        """Get display color based on severity."""
        colors = {
            AlertSeverity.CRITICAL: "#dc3545",  # Red
            AlertSeverity.WARNING: "#ffc107",   # Yellow
            AlertSeverity.INFO: "#17a2b8"       # Blue
        }
        return colors.get(self.severity, "#6c757d")


@dataclass
class MarketSnapshot:
    """Point-in-time market data for a ticker."""
    ticker: str
    price: float
    prev_close: float
    volume: int
    avg_volume: int
    iv: float  # Implied volatility
    prev_iv: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def price_gap_pct(self) -> float:
        """Calculate price gap from previous close."""
        if self.prev_close == 0:
            return 0.0
        return ((self.price - self.prev_close) / self.prev_close) * 100
    
    @property
    def iv_change_pct(self) -> float:
        """Calculate IV change percentage."""
        if self.prev_iv == 0:
            return 0.0
        return ((self.iv - self.prev_iv) / self.prev_iv) * 100
    
    @property
    def volume_ratio(self) -> float:
        """Calculate volume relative to average."""
        if self.avg_volume == 0:
            return 1.0
        return self.volume / self.avg_volume


class MarketWatchdog:
    """
    Market Monitoring Watchdog.
    
    Scans market conditions and triggers alerts:
    - IV_SPIKE: IV increase > threshold (default 50%)
    - PRICE_GAP: Gap from prev close > threshold (default 2%)
    - VOLUME_SURGE: Volume > threshold x average
    
    Alerts are stored in a rolling log and published to callbacks.
    """
    
    # Default thresholds
    DEFAULT_IV_SPIKE_PCT = 50.0    # 50% IV increase
    DEFAULT_PRICE_GAP_PCT = 2.0    # 2% price gap
    DEFAULT_VOLUME_SURGE_RATIO = 3.0  # 3x average volume
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern for watchdog."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize market watchdog."""
        if self._initialized:
            return
        
        # Thresholds (configurable via environment)
        self.iv_spike_threshold = float(os.getenv(
            "WATCHDOG_IV_SPIKE_PCT",
            self.DEFAULT_IV_SPIKE_PCT
        ))
        self.price_gap_threshold = float(os.getenv(
            "WATCHDOG_PRICE_GAP_PCT",
            self.DEFAULT_PRICE_GAP_PCT
        ))
        self.volume_surge_ratio = float(os.getenv(
            "WATCHDOG_VOLUME_SURGE_RATIO",
            self.DEFAULT_VOLUME_SURGE_RATIO
        ))
        
        # Deterministic mode
        self.deterministic = os.getenv("TRADEOPS_DETERMINISTIC", "0") == "1"
        
        # Alert storage (rolling buffer)
        self.max_alerts = 500
        self.alerts: deque = deque(maxlen=self.max_alerts)
        self.alert_counter = 0
        
        # Watched tickers and their last snapshots
        self.watched_tickers: Set[str] = {"SPY", "QQQ"}
        self.last_snapshots: Dict[str, MarketSnapshot] = {}
        
        # Callbacks for real-time alert publishing
        self.on_alert: Optional[Callable[[Alert], None]] = None
        
        # Background monitoring (disabled by default)
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        
        # Simulated market data for testing
        self._sim_data: Dict[str, Dict[str, float]] = {
            "SPY": {"price": 450.0, "prev_close": 448.0, "iv": 0.15, "prev_iv": 0.14, "volume": 50000000, "avg_volume": 45000000},
            "QQQ": {"price": 380.0, "prev_close": 378.0, "iv": 0.18, "prev_iv": 0.17, "volume": 30000000, "avg_volume": 28000000},
            "AAPL": {"price": 175.0, "prev_close": 174.0, "iv": 0.22, "prev_iv": 0.20, "volume": 60000000, "avg_volume": 55000000},
            "NVDA": {"price": 480.0, "prev_close": 475.0, "iv": 0.45, "prev_iv": 0.40, "volume": 40000000, "avg_volume": 35000000},
        }
        
        self._initialized = True
        logger.info(f"MarketWatchdog initialized: iv_spike={self.iv_spike_threshold}%, "
                   f"price_gap={self.price_gap_threshold}%, volume_surge={self.volume_surge_ratio}x")
    
    def scan_ticker(self, snapshot: MarketSnapshot) -> List[Alert]:
        """
        Scan a ticker for alert conditions.
        
        Args:
            snapshot: Current market data snapshot
            
        Returns:
            List of triggered alerts
        """
        alerts = []
        ticker = snapshot.ticker.upper()
        
        # Store snapshot
        self.last_snapshots[ticker] = snapshot
        
        # Check IV spike
        if abs(snapshot.iv_change_pct) >= self.iv_spike_threshold:
            direction = "increased" if snapshot.iv_change_pct > 0 else "decreased"
            alert = self._create_alert(
                alert_type=AlertType.IV_SPIKE,
                severity=AlertSeverity.WARNING if snapshot.iv_change_pct > 0 else AlertSeverity.INFO,
                ticker=ticker,
                title=f"🔥 High Volatility: {ticker}",
                message=f"IV {direction} {abs(snapshot.iv_change_pct):.1f}% "
                       f"(from {snapshot.prev_iv*100:.1f}% to {snapshot.iv*100:.1f}%)",
                details={
                    "iv_current": snapshot.iv,
                    "iv_previous": snapshot.prev_iv,
                    "iv_change_pct": snapshot.iv_change_pct
                }
            )
            alerts.append(alert)
        
        # Check price gap
        if abs(snapshot.price_gap_pct) >= self.price_gap_threshold:
            direction = "up" if snapshot.price_gap_pct > 0 else "down"
            severity = AlertSeverity.WARNING if abs(snapshot.price_gap_pct) > 5 else AlertSeverity.INFO
            alert = self._create_alert(
                alert_type=AlertType.PRICE_GAP,
                severity=severity,
                ticker=ticker,
                title=f"📊 Price Gap: {ticker}",
                message=f"Gapped {direction} {abs(snapshot.price_gap_pct):.2f}% "
                       f"(${snapshot.prev_close:.2f} → ${snapshot.price:.2f})",
                details={
                    "price_current": snapshot.price,
                    "price_prev_close": snapshot.prev_close,
                    "gap_pct": snapshot.price_gap_pct
                }
            )
            alerts.append(alert)
        
        # Check volume surge
        if snapshot.volume_ratio >= self.volume_surge_ratio:
            alert = self._create_alert(
                alert_type=AlertType.VOLUME_SURGE,
                severity=AlertSeverity.INFO,
                ticker=ticker,
                title=f"📈 Volume Surge: {ticker}",
                message=f"Volume {snapshot.volume_ratio:.1f}x average "
                       f"({snapshot.volume:,} vs avg {snapshot.avg_volume:,})",
                details={
                    "volume_current": snapshot.volume,
                    "volume_average": snapshot.avg_volume,
                    "volume_ratio": snapshot.volume_ratio
                }
            )
            alerts.append(alert)
        
        return alerts
    
    def scan_all_watched(self) -> List[Alert]:
        """Scan all watched tickers using simulated data."""
        all_alerts = []
        
        for ticker in self.watched_tickers:
            if ticker in self._sim_data:
                data = self._sim_data[ticker]
                snapshot = MarketSnapshot(
                    ticker=ticker,
                    price=data["price"],
                    prev_close=data["prev_close"],
                    volume=int(data["volume"]),
                    avg_volume=int(data["avg_volume"]),
                    iv=data["iv"],
                    prev_iv=data["prev_iv"]
                )
                alerts = self.scan_ticker(snapshot)
                all_alerts.extend(alerts)
        
        return all_alerts
    
    def simulate_iv_spike(self, ticker: str, iv_increase_pct: float = 60.0):
        """
        Simulate an IV spike for testing.
        
        Args:
            ticker: Symbol to spike
            iv_increase_pct: Percentage increase in IV
        """
        ticker = ticker.upper()
        
        if ticker not in self._sim_data:
            self._sim_data[ticker] = {
                "price": 100.0,
                "prev_close": 100.0,
                "iv": 0.20,
                "prev_iv": 0.20,
                "volume": 1000000,
                "avg_volume": 1000000
            }
        
        data = self._sim_data[ticker]
        new_iv = data["prev_iv"] * (1 + iv_increase_pct / 100)
        data["iv"] = new_iv
        
        logger.info(f"Simulated IV spike for {ticker}: {iv_increase_pct}% increase")
        
        # Trigger scan
        snapshot = MarketSnapshot(
            ticker=ticker,
            price=data["price"],
            prev_close=data["prev_close"],
            volume=int(data["volume"]),
            avg_volume=int(data["avg_volume"]),
            iv=new_iv,
            prev_iv=data["prev_iv"]
        )
        
        return self.scan_ticker(snapshot)
    
    def simulate_price_gap(self, ticker: str, gap_pct: float = 3.0):
        """
        Simulate a price gap for testing.
        
        Args:
            ticker: Symbol to gap
            gap_pct: Gap percentage (positive=up, negative=down)
        """
        ticker = ticker.upper()
        
        if ticker not in self._sim_data:
            self._sim_data[ticker] = {
                "price": 100.0,
                "prev_close": 100.0,
                "iv": 0.20,
                "prev_iv": 0.20,
                "volume": 1000000,
                "avg_volume": 1000000
            }
        
        data = self._sim_data[ticker]
        new_price = data["prev_close"] * (1 + gap_pct / 100)
        data["price"] = new_price
        
        logger.info(f"Simulated price gap for {ticker}: {gap_pct}%")
        
        # Trigger scan
        snapshot = MarketSnapshot(
            ticker=ticker,
            price=new_price,
            prev_close=data["prev_close"],
            volume=int(data["volume"]),
            avg_volume=int(data["avg_volume"]),
            iv=data["iv"],
            prev_iv=data["prev_iv"]
        )
        
        return self.scan_ticker(snapshot)
    
    def add_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        ticker: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """
        Manually add an alert to the feed.
        
        Args:
            alert_type: Type of alert
            severity: Severity level
            title: Alert title
            message: Alert message
            ticker: Related ticker (optional)
            details: Additional details (optional)
            
        Returns:
            Created alert
        """
        return self._create_alert(
            alert_type=alert_type,
            severity=severity,
            ticker=ticker,
            title=title,
            message=message,
            details=details or {}
        )
    
    def _create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        ticker: Optional[str],
        title: str,
        message: str,
        details: Dict[str, Any]
    ) -> Alert:
        """Create and store an alert."""
        self.alert_counter += 1
        
        if self.deterministic:
            alert_id = f"ALERT-{self.alert_counter:06d}"
        else:
            import uuid
            alert_id = f"ALERT-{uuid.uuid4().hex[:8].upper()}"
        
        alert = Alert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            ticker=ticker,
            title=title,
            message=message,
            details=details
        )
        
        self.alerts.append(alert)
        
        logger.info(f"Alert created: [{severity.value}] {title}")
        
        # Publish to callback
        if self.on_alert:
            self.on_alert(alert)
        
        return alert
    
    def get_alerts(
        self,
        limit: int = 50,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[AlertType] = None,
        ticker: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get alerts with optional filtering.
        
        Args:
            limit: Maximum number of alerts to return
            severity: Filter by severity
            alert_type: Filter by alert type
            ticker: Filter by ticker
            
        Returns:
            List of alert dictionaries
        """
        result = []
        
        for alert in reversed(self.alerts):
            if len(result) >= limit:
                break
            
            if severity and alert.severity != severity:
                continue
            if alert_type and alert.alert_type != alert_type:
                continue
            if ticker and alert.ticker != ticker.upper():
                continue
            
            result.append(alert.to_dict())
        
        return result
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark an alert as acknowledged."""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False
    
    def clear_alerts(self):
        """Clear all alerts."""
        self.alerts.clear()
        logger.info("All alerts cleared")
    
    def add_watched_ticker(self, ticker: str):
        """Add a ticker to watch list."""
        self.watched_tickers.add(ticker.upper())
    
    def remove_watched_ticker(self, ticker: str):
        """Remove a ticker from watch list."""
        self.watched_tickers.discard(ticker.upper())
    
    def get_watched_tickers(self) -> List[str]:
        """Get list of watched tickers."""
        return list(self.watched_tickers)
    
    def get_thresholds(self) -> Dict[str, float]:
        """Get current alert thresholds."""
        return {
            "iv_spike_pct": self.iv_spike_threshold,
            "price_gap_pct": self.price_gap_threshold,
            "volume_surge_ratio": self.volume_surge_ratio
        }


def get_watchdog() -> MarketWatchdog:
    """Get the singleton MarketWatchdog instance."""
    return MarketWatchdog()

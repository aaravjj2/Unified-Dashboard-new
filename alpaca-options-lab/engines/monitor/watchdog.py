from enum import Enum
import time


class AlertType(Enum):
    ORDER_FILL = "ORDER_FILL"
    ORDER_REJECT = "ORDER_REJECT"
    RISK_WARNING = "RISK_WARNING"


class AlertSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class _Watchdog:
    def __init__(self):
        self._alerts = []

    def add_alert(self, alert_type: AlertType, severity: AlertSeverity, title: str, message: str, ticker: str = None, details: dict = None):
        alert = {
            "id": int(time.time()*1000),
            "type": alert_type.value,
            "severity": severity.value,
            "title": title,
            "message": message,
            "ticker": ticker,
            "details": details or {},
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self._alerts.insert(0, alert)
        return alert

    def simulate_iv_spike(self, ticker: str, iv_increase_pct: float = 50.0):
        alert = self.add_alert(AlertType.RISK_WARNING, AlertSeverity.CRITICAL, f"IV Spike: {ticker}", f"IV increased by {iv_increase_pct}%", ticker=ticker)
        return [alert]

    def get_alerts(self, limit: int = 50):
        return self._alerts[:limit]


_SINGLETON = None


def get_watchdog():
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = _Watchdog()
    return _SINGLETON

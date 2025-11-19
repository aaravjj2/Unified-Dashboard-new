"""
Generic Alerter Module
Handles alerts and notifications for important system events.
"""

import logging
from typing import Optional
from datetime import datetime
from pathlib import Path
from enum import Enum


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertCategory(Enum):
    """Alert categories."""
    TRADE_EXECUTION = "trade_execution"
    TRADE_FAILURE = "trade_failure"
    RISK_BREACH = "risk_breach"
    API_ERROR = "api_error"
    STRATEGY_STATUS = "strategy_status"
    SYSTEM = "system"


class Alerter:
    """Manages alerts and notifications."""
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize alerter.
        
        Args:
            config: Alert configuration dict
        """
        self.config = config or {}
        
        # Configuration
        self.log_to_file = self.config.get('log_to_file', True)
        self.log_file = self.config.get('log_file', 'logs/alerts.log')
        self.email_enabled = self.config.get('email_enabled', False)
        self.slack_enabled = self.config.get('slack_enabled', False)
        self.telegram_enabled = self.config.get('telegram_enabled', False)
        
        # Event filters
        self.on_trade_execution = self.config.get('on_trade_execution', True)
        self.on_trade_failure = self.config.get('on_trade_failure', True)
        self.on_risk_limit_breach = self.config.get('on_risk_limit_breach', True)
        self.on_api_error = self.config.get('on_api_error', True)
        self.on_strategy_start = self.config.get('on_strategy_start', True)
        self.on_strategy_stop = self.config.get('on_strategy_stop', True)
        
        # Setup file logging
        if self.log_to_file:
            self._setup_file_logging()
        
        # Alert history (in-memory, last 100 alerts)
        self.alert_history = []
        self.max_history = 100
    
    def _setup_file_logging(self):
        """Setup file logging for alerts."""
        log_path = Path(self.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger('alerter')
        self.logger.setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def send_alert(self, message: str, severity: AlertSeverity = AlertSeverity.INFO, 
                   category: AlertCategory = AlertCategory.SYSTEM, metadata: Optional[dict] = None):
        """
        Send an alert through configured channels.
        
        Args:
            message: Alert message
            severity: Alert severity level
            category: Alert category
            metadata: Optional additional data
        """
        # Create alert record
        alert = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'severity': severity.value,
            'category': category.value,
            'metadata': metadata or {}
        }
        
        # Add to history
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_history:
            self.alert_history.pop(0)
        
        # Check if this category should trigger alerts
        if not self._should_alert(category):
            return
        
        # Log to console
        severity_color = {
            AlertSeverity.INFO: '\033[94m',  # Blue
            AlertSeverity.WARNING: '\033[93m',  # Yellow
            AlertSeverity.ERROR: '\033[91m',  # Red
            AlertSeverity.CRITICAL: '\033[95m'  # Magenta
        }
        reset_color = '\033[0m'
        
        console_msg = f"{severity_color.get(severity, '')}{severity.value}{reset_color} [{category.value}] {message}"
        print(console_msg)
        
        # Log to file
        if self.log_to_file and hasattr(self, 'logger'):
            log_level = {
                AlertSeverity.INFO: logging.INFO,
                AlertSeverity.WARNING: logging.WARNING,
                AlertSeverity.ERROR: logging.ERROR,
                AlertSeverity.CRITICAL: logging.CRITICAL
            }
            self.logger.log(
                log_level.get(severity, logging.INFO),
                f"[{category.value}] {message} {metadata or ''}"
            )
        
        # Send to external channels (email, Slack, Telegram)
        # These would be implemented when needed
        if self.email_enabled:
            self._send_email_alert(alert)
        
        if self.slack_enabled:
            self._send_slack_alert(alert)
        
        if self.telegram_enabled:
            self._send_telegram_alert(alert)
    
    def _should_alert(self, category: AlertCategory) -> bool:
        """Check if alerts should be sent for this category."""
        category_map = {
            AlertCategory.TRADE_EXECUTION: self.on_trade_execution,
            AlertCategory.TRADE_FAILURE: self.on_trade_failure,
            AlertCategory.RISK_BREACH: self.on_risk_limit_breach,
            AlertCategory.API_ERROR: self.on_api_error,
            AlertCategory.STRATEGY_STATUS: self.on_strategy_start or self.on_strategy_stop,
        }
        return category_map.get(category, True)
    
    def _send_email_alert(self, alert: dict):
        """Send alert via email. To be implemented."""
        # TODO: Implement SMTP email sending
        pass
    
    def _send_slack_alert(self, alert: dict):
        """Send alert to Slack. To be implemented."""
        # TODO: Implement Slack webhook
        pass
    
    def _send_telegram_alert(self, alert: dict):
        """Send alert to Telegram. To be implemented."""
        # TODO: Implement Telegram bot API
        pass
    
    def get_recent_alerts(self, limit: int = 50, category: Optional[AlertCategory] = None,
                         severity: Optional[AlertSeverity] = None) -> list:
        """
        Get recent alerts, optionally filtered.
        
        Args:
            limit: Maximum number of alerts to return
            category: Optional category filter
            severity: Optional severity filter
        
        Returns:
            List of alert dicts
        """
        alerts = self.alert_history.copy()
        
        # Apply filters
        if category:
            alerts = [a for a in alerts if a['category'] == category.value]
        
        if severity:
            alerts = [a for a in alerts if a['severity'] == severity.value]
        
        # Return most recent first
        return list(reversed(alerts[-limit:]))
    
    def clear_history(self):
        """Clear alert history."""
        self.alert_history = []
    
    # Convenience methods for common alerts
    
    def alert_trade_executed(self, trade_details: dict):
        """Alert that a trade was executed."""
        message = f"Trade executed: {trade_details.get('side', '').upper()} {trade_details.get('quantity')} x {trade_details.get('symbol')}"
        self.send_alert(message, AlertSeverity.INFO, AlertCategory.TRADE_EXECUTION, trade_details)
    
    def alert_trade_failed(self, trade_details: dict, error: str):
        """Alert that a trade failed."""
        message = f"Trade failed: {trade_details.get('symbol')} - {error}"
        metadata = {**trade_details, 'error': error}
        self.send_alert(message, AlertSeverity.ERROR, AlertCategory.TRADE_FAILURE, metadata)
    
    def alert_risk_breach(self, breach_type: str, details: dict):
        """Alert that a risk limit was breached."""
        message = f"Risk limit breached: {breach_type}"
        self.send_alert(message, AlertSeverity.WARNING, AlertCategory.RISK_BREACH, details)
    
    def alert_api_error(self, api_name: str, error: str):
        """Alert about an API error."""
        message = f"API error ({api_name}): {error}"
        metadata = {'api': api_name, 'error': error}
        self.send_alert(message, AlertSeverity.ERROR, AlertCategory.API_ERROR, metadata)
    
    def alert_strategy_started(self, strategy_name: str):
        """Alert that a strategy was started."""
        message = f"Strategy started: {strategy_name}"
        self.send_alert(message, AlertSeverity.INFO, AlertCategory.STRATEGY_STATUS, {'strategy': strategy_name})
    
    def alert_strategy_stopped(self, strategy_name: str):
        """Alert that a strategy was stopped."""
        message = f"Strategy stopped: {strategy_name}"
        self.send_alert(message, AlertSeverity.INFO, AlertCategory.STRATEGY_STATUS, {'strategy': strategy_name})

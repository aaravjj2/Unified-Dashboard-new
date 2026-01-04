"""
Alpaca Options Lab - Alert Manager

Alert and notification system:
- Multi-channel alerts
- Alert severity levels
- Rate limiting
- Alert history
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class AlertLevel(Enum):
    """Alert severity level."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    
    def __lt__(self, other: 'AlertLevel') -> bool:
        order = [AlertLevel.DEBUG, AlertLevel.INFO, AlertLevel.WARNING, 
                 AlertLevel.ERROR, AlertLevel.CRITICAL]
        return order.index(self) < order.index(other)


class AlertChannel(Enum):
    """Alert delivery channel."""
    LOG = "log"
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"
    WEBHOOK = "webhook"
    CONSOLE = "console"


@dataclass
class Alert:
    """Alert message."""
    alert_id: str
    title: str
    message: str
    level: AlertLevel = AlertLevel.INFO
    
    # Source
    source: str = ""
    component: str = ""
    
    # Timing
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    
    # Delivery
    channels: List[AlertChannel] = field(default_factory=list)
    delivered: bool = False
    delivery_attempts: int = 0
    delivered_at: Optional[datetime] = None
    
    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # Tracking
    acknowledged: bool = False
    acknowledged_by: str = ""
    acknowledged_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "title": self.title,
            "message": self.message,
            "level": self.level.value,
            "source": self.source,
            "component": self.component,
            "timestamp": self.timestamp.isoformat(),
            "delivered": self.delivered,
            "acknowledged": self.acknowledged,
            "context": self.context,
            "tags": self.tags,
        }


@dataclass
class AlertRule:
    """Rule for automatic alert generation."""
    name: str
    condition: Callable[..., bool]
    level: AlertLevel
    title_template: str
    message_template: str
    
    # Targeting
    channels: List[AlertChannel] = field(default_factory=list)
    
    # Rate limiting
    cooldown_seconds: int = 300  # 5 minutes
    last_triggered: Optional[datetime] = None
    
    # Metadata
    enabled: bool = True
    tags: List[str] = field(default_factory=list)


class AlertChannelHandler:
    """Base class for alert channel handlers."""
    
    async def send(self, alert: Alert) -> bool:
        """Send alert through this channel."""
        raise NotImplementedError


class LogAlertHandler(AlertChannelHandler):
    """Send alerts to log."""
    
    async def send(self, alert: Alert) -> bool:
        level_map = {
            AlertLevel.DEBUG: logger.debug,
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical,
        }
        
        log_fn = level_map.get(alert.level, logger.info)
        log_fn(f"[ALERT] {alert.title}: {alert.message}")
        
        return True


class ConsoleAlertHandler(AlertChannelHandler):
    """Print alerts to console."""
    
    async def send(self, alert: Alert) -> bool:
        level_emoji = {
            AlertLevel.DEBUG: "🔍",
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.ERROR: "❌",
            AlertLevel.CRITICAL: "🚨",
        }
        
        emoji = level_emoji.get(alert.level, "📢")
        print(f"{emoji} [{alert.level.value.upper()}] {alert.title}")
        print(f"   {alert.message}")
        
        return True


class WebhookAlertHandler(AlertChannelHandler):
    """Send alerts to webhook."""
    
    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        self.url = url
        self.headers = headers or {}
    
    async def send(self, alert: Alert) -> bool:
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.url,
                    json=alert.to_dict(),
                    headers=self.headers,
                    timeout=10,
                ) as response:
                    return response.status < 400
                    
        except Exception as e:
            logger.error(f"Webhook alert failed: {e}")
            return False


class SlackAlertHandler(AlertChannelHandler):
    """Send alerts to Slack."""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    async def send(self, alert: Alert) -> bool:
        try:
            import aiohttp
            
            # Format for Slack
            color_map = {
                AlertLevel.DEBUG: "#808080",
                AlertLevel.INFO: "#36a64f",
                AlertLevel.WARNING: "#daa038",
                AlertLevel.ERROR: "#cc0000",
                AlertLevel.CRITICAL: "#ff0000",
            }
            
            payload = {
                "attachments": [{
                    "color": color_map.get(alert.level, "#808080"),
                    "title": alert.title,
                    "text": alert.message,
                    "footer": f"{alert.source} | {alert.component}",
                    "ts": alert.timestamp.timestamp(),
                    "fields": [
                        {"title": "Level", "value": alert.level.value, "short": True},
                        {"title": "Component", "value": alert.component, "short": True},
                    ],
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10,
                ) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"Slack alert failed: {e}")
            return False


class AlertManager:
    """
    Alert management system.
    
    Features:
    - Multi-channel delivery
    - Alert rules
    - Rate limiting
    - History tracking
    """
    
    def __init__(self, min_level: AlertLevel = AlertLevel.INFO):
        self.min_level = min_level
        
        # Channel handlers
        self._handlers: Dict[AlertChannel, AlertChannelHandler] = {
            AlertChannel.LOG: LogAlertHandler(),
            AlertChannel.CONSOLE: ConsoleAlertHandler(),
        }
        
        # Default channels
        self._default_channels = [AlertChannel.LOG]
        
        # Alert rules
        self._rules: Dict[str, AlertRule] = {}
        
        # History
        self._alerts: List[Alert] = []
        self._max_history = 1000
        
        # Rate limiting
        self._alert_counts: Dict[str, int] = {}
        self._rate_limit_window = 60  # 1 minute
        self._rate_limit_max = 10  # Max alerts per type per minute
        
        # Counter for IDs
        self._counter = 0
        
        logger.info("AlertManager initialized")
    
    # -------------------- Configuration --------------------
    
    def register_handler(
        self,
        channel: AlertChannel,
        handler: AlertChannelHandler,
    ) -> None:
        """Register a channel handler."""
        self._handlers[channel] = handler
        logger.info(f"Alert handler registered: {channel.value}")
    
    def set_default_channels(self, channels: List[AlertChannel]) -> None:
        """Set default delivery channels."""
        self._default_channels = channels
    
    def set_min_level(self, level: AlertLevel) -> None:
        """Set minimum alert level."""
        self.min_level = level
    
    # -------------------- Alert Creation --------------------
    
    async def alert(
        self,
        title: str,
        message: str,
        level: AlertLevel = AlertLevel.INFO,
        source: str = "",
        component: str = "",
        channels: Optional[List[AlertChannel]] = None,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Alert:
        """
        Create and send an alert.
        
        Args:
            title: Alert title
            message: Alert message
            level: Severity level
            source: Alert source
            component: Component name
            channels: Delivery channels
            context: Additional context
            tags: Alert tags
        
        Returns:
            Created Alert
        """
        # Check minimum level
        if level < self.min_level:
            return Alert(
                alert_id="",
                title=title,
                message=message,
                level=level,
                delivered=False,
            )
        
        # Check rate limit
        rate_key = f"{source}:{component}:{title}"
        if not self._check_rate_limit(rate_key):
            logger.debug(f"Alert rate limited: {rate_key}")
            return Alert(
                alert_id="",
                title=title,
                message=message,
                level=level,
                delivered=False,
            )
        
        # Create alert
        self._counter += 1
        alert = Alert(
            alert_id=f"alert_{self._counter:06d}",
            title=title,
            message=message,
            level=level,
            source=source,
            component=component,
            channels=channels or self._default_channels,
            context=context or {},
            tags=tags or [],
        )
        
        # Send through channels
        await self._deliver_alert(alert)
        
        # Store in history
        self._store_alert(alert)
        
        return alert
    
    async def _deliver_alert(self, alert: Alert) -> None:
        """Deliver alert through configured channels."""
        for channel in alert.channels:
            handler = self._handlers.get(channel)
            
            if not handler:
                logger.warning(f"No handler for channel: {channel.value}")
                continue
            
            try:
                alert.delivery_attempts += 1
                success = await handler.send(alert)
                
                if success:
                    alert.delivered = True
                    alert.delivered_at = datetime.now(timezone.utc)
                    
            except Exception as e:
                logger.error(f"Alert delivery failed ({channel.value}): {e}")
    
    def _store_alert(self, alert: Alert) -> None:
        """Store alert in history."""
        self._alerts.append(alert)
        
        # Trim history
        if len(self._alerts) > self._max_history:
            self._alerts = self._alerts[-self._max_history:]
    
    def _check_rate_limit(self, key: str) -> bool:
        """Check if alert is rate limited."""
        count = self._alert_counts.get(key, 0)
        
        if count >= self._rate_limit_max:
            return False
        
        self._alert_counts[key] = count + 1
        
        # Schedule reset (simple implementation)
        asyncio.get_event_loop().call_later(
            self._rate_limit_window,
            lambda: self._alert_counts.update({key: max(0, self._alert_counts.get(key, 0) - 1)}),
        )
        
        return True
    
    # -------------------- Convenience Methods --------------------
    
    async def info(
        self,
        title: str,
        message: str,
        **kwargs,
    ) -> Alert:
        """Send INFO level alert."""
        return await self.alert(title, message, level=AlertLevel.INFO, **kwargs)
    
    async def warning(
        self,
        title: str,
        message: str,
        **kwargs,
    ) -> Alert:
        """Send WARNING level alert."""
        return await self.alert(title, message, level=AlertLevel.WARNING, **kwargs)
    
    async def error(
        self,
        title: str,
        message: str,
        **kwargs,
    ) -> Alert:
        """Send ERROR level alert."""
        return await self.alert(title, message, level=AlertLevel.ERROR, **kwargs)
    
    async def critical(
        self,
        title: str,
        message: str,
        **kwargs,
    ) -> Alert:
        """Send CRITICAL level alert."""
        return await self.alert(title, message, level=AlertLevel.CRITICAL, **kwargs)
    
    # -------------------- Alert Rules --------------------
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self._rules[rule.name] = rule
        logger.info(f"Alert rule added: {rule.name}")
    
    def remove_rule(self, name: str) -> bool:
        """Remove an alert rule."""
        if name in self._rules:
            del self._rules[name]
            return True
        return False
    
    async def evaluate_rules(self, context: Dict[str, Any]) -> List[Alert]:
        """Evaluate all rules against context."""
        triggered = []
        
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            
            # Check cooldown
            if rule.last_triggered:
                elapsed = (datetime.now(timezone.utc) - rule.last_triggered).total_seconds()
                if elapsed < rule.cooldown_seconds:
                    continue
            
            try:
                if rule.condition(context):
                    # Render templates
                    title = rule.title_template.format(**context)
                    message = rule.message_template.format(**context)
                    
                    alert = await self.alert(
                        title=title,
                        message=message,
                        level=rule.level,
                        channels=rule.channels or self._default_channels,
                        tags=rule.tags,
                        context=context,
                    )
                    
                    rule.last_triggered = datetime.now(timezone.utc)
                    triggered.append(alert)
                    
            except Exception as e:
                logger.error(f"Rule evaluation error ({rule.name}): {e}")
        
        return triggered
    
    # -------------------- History --------------------
    
    def get_alerts(
        self,
        level: Optional[AlertLevel] = None,
        component: Optional[str] = None,
        limit: int = 100,
        acknowledged: Optional[bool] = None,
    ) -> List[Alert]:
        """
        Get alert history.
        
        Args:
            level: Filter by level
            component: Filter by component
            limit: Maximum alerts to return
            acknowledged: Filter by acknowledged status
        
        Returns:
            List of alerts
        """
        alerts = self._alerts
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        if component:
            alerts = [a for a in alerts if a.component == component]
        
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        return alerts[-limit:]
    
    def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str = "",
    ) -> bool:
        """Acknowledge an alert."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.now(timezone.utc)
                return True
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        by_level = {}
        by_component = {}
        
        for alert in self._alerts:
            level_key = alert.level.value
            by_level[level_key] = by_level.get(level_key, 0) + 1
            
            if alert.component:
                by_component[alert.component] = by_component.get(alert.component, 0) + 1
        
        return {
            "total_alerts": len(self._alerts),
            "unacknowledged": len([a for a in self._alerts if not a.acknowledged]),
            "by_level": by_level,
            "by_component": by_component,
            "rules_count": len(self._rules),
        }

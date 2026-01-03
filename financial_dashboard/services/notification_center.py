"""
Notification Center Service
Implements #260 from ROADMAP_ULTIMATE.md

Centralized notification system for alerts, signals, and updates
"""
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import asyncio
import logging
import uuid

logger = logging.getLogger(__name__)


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class NotificationCategory(Enum):
    """Notification categories"""
    TRADE_SIGNAL = "trade_signal"
    PRICE_ALERT = "price_alert"
    RISK_WARNING = "risk_warning"
    NEWS = "news"
    EARNINGS = "earnings"
    DIVIDEND = "dividend"
    UNUSUAL_ACTIVITY = "unusual_activity"
    SYSTEM = "system"
    PORTFOLIO = "portfolio"
    ORDER = "order"
    MARKET_EVENT = "market_event"


class NotificationStatus(Enum):
    """Notification status"""
    UNREAD = "unread"
    READ = "read"
    DISMISSED = "dismissed"
    ACTIONED = "actioned"


@dataclass
class NotificationAction:
    """Action that can be taken on a notification"""
    action_id: str
    label: str
    callback: Optional[str] = None  # JavaScript callback or route
    style: str = "default"  # default, primary, danger


@dataclass
class Notification:
    """Notification data structure"""
    id: str
    title: str
    message: str
    category: NotificationCategory
    priority: NotificationPriority
    timestamp: datetime
    status: NotificationStatus = NotificationStatus.UNREAD
    icon: str = ""
    symbol: Optional[str] = None
    data: Dict = field(default_factory=dict)
    actions: List[NotificationAction] = field(default_factory=list)
    expires_at: Optional[datetime] = None
    sound: bool = False
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'category': self.category.value,
            'priority': self.priority.value,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status.value,
            'icon': self.icon,
            'symbol': self.symbol,
            'data': self.data,
            'actions': [
                {'action_id': a.action_id, 'label': a.label, 'callback': a.callback, 'style': a.style}
                for a in self.actions
            ],
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'sound': self.sound
        }


@dataclass
class NotificationFilter:
    """Filter for querying notifications"""
    categories: Optional[List[NotificationCategory]] = None
    priorities: Optional[List[NotificationPriority]] = None
    status: Optional[List[NotificationStatus]] = None
    symbols: Optional[List[str]] = None
    since: Optional[datetime] = None
    limit: int = 50


class NotificationCenter:
    """
    Centralized notification management system
    Handles alerts, signals, and all types of notifications
    """
    
    def __init__(self, max_notifications: int = 1000):
        self.max_notifications = max_notifications
        self.notifications: Dict[str, Notification] = {}
        self.notification_queue: deque = deque(maxlen=max_notifications)
        self.subscribers: Dict[NotificationCategory, List[Callable]] = {}
        self.global_subscribers: List[Callable] = []
        self.muted_categories: set = set()
        self.muted_symbols: set = set()
        
        # Initialize category icons
        self.category_icons = {
            NotificationCategory.TRADE_SIGNAL: "📊",
            NotificationCategory.PRICE_ALERT: "🔔",
            NotificationCategory.RISK_WARNING: "⚠️",
            NotificationCategory.NEWS: "📰",
            NotificationCategory.EARNINGS: "💰",
            NotificationCategory.DIVIDEND: "💵",
            NotificationCategory.UNUSUAL_ACTIVITY: "🔥",
            NotificationCategory.SYSTEM: "⚙️",
            NotificationCategory.PORTFOLIO: "📁",
            NotificationCategory.ORDER: "📋",
            NotificationCategory.MARKET_EVENT: "🌍"
        }
        
        # Priority sounds
        self.priority_sounds = {
            NotificationPriority.URGENT: True,
            NotificationPriority.CRITICAL: True
        }
    
    def create_notification(self,
                          title: str,
                          message: str,
                          category: NotificationCategory,
                          priority: NotificationPriority = NotificationPriority.NORMAL,
                          symbol: Optional[str] = None,
                          data: Dict = None,
                          actions: List[NotificationAction] = None,
                          expires_in_minutes: Optional[int] = None) -> Notification:
        """Create and store a new notification"""
        
        # Check muting
        if category in self.muted_categories:
            return None
        if symbol and symbol in self.muted_symbols:
            return None
        
        notification_id = str(uuid.uuid4())[:8]
        
        expires_at = None
        if expires_in_minutes:
            expires_at = datetime.now() + timedelta(minutes=expires_in_minutes)
        
        notification = Notification(
            id=notification_id,
            title=title,
            message=message,
            category=category,
            priority=priority,
            timestamp=datetime.now(),
            icon=self.category_icons.get(category, "📌"),
            symbol=symbol,
            data=data or {},
            actions=actions or [],
            expires_at=expires_at,
            sound=priority in self.priority_sounds
        )
        
        self.notifications[notification_id] = notification
        self.notification_queue.append(notification_id)
        
        # Cleanup expired
        self._cleanup_expired()
        
        # Notify subscribers
        self._notify_subscribers(notification)
        
        logger.info(f"Notification created: {notification_id} - {title}")
        
        return notification
    
    def _cleanup_expired(self):
        """Remove expired notifications"""
        now = datetime.now()
        expired = [
            nid for nid, n in self.notifications.items()
            if n.expires_at and n.expires_at < now
        ]
        
        for nid in expired:
            del self.notifications[nid]
    
    def _notify_subscribers(self, notification: Notification):
        """Notify all relevant subscribers"""
        # Category subscribers
        if notification.category in self.subscribers:
            for callback in self.subscribers[notification.category]:
                try:
                    callback(notification)
                except Exception as e:
                    logger.error(f"Subscriber callback error: {e}")
        
        # Global subscribers
        for callback in self.global_subscribers:
            try:
                callback(notification)
            except Exception as e:
                logger.error(f"Global subscriber error: {e}")
    
    def subscribe(self, category: NotificationCategory, callback: Callable):
        """Subscribe to a category"""
        if category not in self.subscribers:
            self.subscribers[category] = []
        self.subscribers[category].append(callback)
    
    def subscribe_all(self, callback: Callable):
        """Subscribe to all notifications"""
        self.global_subscribers.append(callback)
    
    def unsubscribe(self, category: NotificationCategory, callback: Callable):
        """Unsubscribe from a category"""
        if category in self.subscribers and callback in self.subscribers[category]:
            self.subscribers[category].remove(callback)
    
    def mark_as_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        if notification_id in self.notifications:
            self.notifications[notification_id].status = NotificationStatus.READ
            return True
        return False
    
    def mark_all_read(self, category: Optional[NotificationCategory] = None):
        """Mark all notifications as read"""
        for notification in self.notifications.values():
            if category is None or notification.category == category:
                notification.status = NotificationStatus.READ
    
    def dismiss(self, notification_id: str) -> bool:
        """Dismiss a notification"""
        if notification_id in self.notifications:
            self.notifications[notification_id].status = NotificationStatus.DISMISSED
            return True
        return False
    
    def action_taken(self, notification_id: str, action_id: str) -> bool:
        """Record that an action was taken"""
        if notification_id in self.notifications:
            self.notifications[notification_id].status = NotificationStatus.ACTIONED
            self.notifications[notification_id].data['actioned'] = action_id
            return True
        return False
    
    def get_notifications(self, 
                         filter: Optional[NotificationFilter] = None) -> List[Notification]:
        """Get filtered notifications"""
        if filter is None:
            filter = NotificationFilter()
        
        result = []
        
        for notification in self.notifications.values():
            # Apply filters
            if filter.categories and notification.category not in filter.categories:
                continue
            if filter.priorities and notification.priority not in filter.priorities:
                continue
            if filter.status and notification.status not in filter.status:
                continue
            if filter.symbols and notification.symbol not in filter.symbols:
                continue
            if filter.since and notification.timestamp < filter.since:
                continue
            
            result.append(notification)
        
        # Sort by priority and timestamp
        priority_order = {
            NotificationPriority.CRITICAL: 0,
            NotificationPriority.URGENT: 1,
            NotificationPriority.HIGH: 2,
            NotificationPriority.NORMAL: 3,
            NotificationPriority.LOW: 4
        }
        
        result.sort(key=lambda n: (priority_order[n.priority], -n.timestamp.timestamp()))
        
        return result[:filter.limit]
    
    def get_unread_count(self, category: Optional[NotificationCategory] = None) -> int:
        """Get count of unread notifications"""
        count = 0
        for notification in self.notifications.values():
            if notification.status == NotificationStatus.UNREAD:
                if category is None or notification.category == category:
                    count += 1
        return count
    
    def get_summary(self) -> Dict:
        """Get notification summary"""
        summary = {
            'total': len(self.notifications),
            'unread': 0,
            'by_category': {},
            'by_priority': {},
            'recent': []
        }
        
        for notification in self.notifications.values():
            if notification.status == NotificationStatus.UNREAD:
                summary['unread'] += 1
            
            cat = notification.category.value
            if cat not in summary['by_category']:
                summary['by_category'][cat] = 0
            summary['by_category'][cat] += 1
            
            pri = notification.priority.value
            if pri not in summary['by_priority']:
                summary['by_priority'][pri] = 0
            summary['by_priority'][pri] += 1
        
        # Get 5 most recent
        recent = sorted(
            self.notifications.values(),
            key=lambda n: n.timestamp,
            reverse=True
        )[:5]
        
        summary['recent'] = [n.to_dict() for n in recent]
        
        return summary
    
    def mute_category(self, category: NotificationCategory):
        """Mute a category"""
        self.muted_categories.add(category)
    
    def unmute_category(self, category: NotificationCategory):
        """Unmute a category"""
        self.muted_categories.discard(category)
    
    def mute_symbol(self, symbol: str):
        """Mute notifications for a symbol"""
        self.muted_symbols.add(symbol)
    
    def unmute_symbol(self, symbol: str):
        """Unmute a symbol"""
        self.muted_symbols.discard(symbol)
    
    def clear_all(self, category: Optional[NotificationCategory] = None):
        """Clear all notifications"""
        if category is None:
            self.notifications.clear()
        else:
            to_remove = [
                nid for nid, n in self.notifications.items()
                if n.category == category
            ]
            for nid in to_remove:
                del self.notifications[nid]
    
    # Convenience methods for common notification types
    def trade_signal(self, 
                    symbol: str,
                    signal_type: str,  # BUY, SELL, etc.
                    price: float,
                    confidence: float,
                    strategy: str = "") -> Notification:
        """Create a trade signal notification"""
        return self.create_notification(
            title=f"{signal_type} Signal: {symbol}",
            message=f"{strategy} suggests {signal_type} at ${price:.2f} ({confidence:.0%} confidence)",
            category=NotificationCategory.TRADE_SIGNAL,
            priority=NotificationPriority.HIGH if confidence > 0.8 else NotificationPriority.NORMAL,
            symbol=symbol,
            data={
                'signal_type': signal_type,
                'price': price,
                'confidence': confidence,
                'strategy': strategy
            },
            actions=[
                NotificationAction("execute", "Execute Trade", "/api/execute", "primary"),
                NotificationAction("dismiss", "Dismiss", None, "default")
            ]
        )
    
    def price_alert(self,
                   symbol: str,
                   current_price: float,
                   target_price: float,
                   alert_type: str) -> Notification:
        """Create a price alert notification"""
        direction = "above" if current_price >= target_price else "below"
        return self.create_notification(
            title=f"Price Alert: {symbol}",
            message=f"{symbol} is now ${current_price:.2f}, {direction} your ${target_price:.2f} target",
            category=NotificationCategory.PRICE_ALERT,
            priority=NotificationPriority.HIGH,
            symbol=symbol,
            data={
                'current_price': current_price,
                'target_price': target_price,
                'alert_type': alert_type
            }
        )
    
    def risk_warning(self,
                    title: str,
                    message: str,
                    risk_type: str,
                    severity: str = "warning",
                    symbol: Optional[str] = None) -> Notification:
        """Create a risk warning notification"""
        priority = NotificationPriority.CRITICAL if severity == "critical" else NotificationPriority.HIGH
        return self.create_notification(
            title=title,
            message=message,
            category=NotificationCategory.RISK_WARNING,
            priority=priority,
            symbol=symbol,
            data={'risk_type': risk_type, 'severity': severity}
        )
    
    def unusual_activity(self,
                        symbol: str,
                        activity_type: str,
                        volume: int,
                        description: str) -> Notification:
        """Create an unusual activity notification"""
        return self.create_notification(
            title=f"Unusual Activity: {symbol}",
            message=description,
            category=NotificationCategory.UNUSUAL_ACTIVITY,
            priority=NotificationPriority.HIGH,
            symbol=symbol,
            data={
                'activity_type': activity_type,
                'volume': volume
            }
        )
    
    def to_json(self, notifications: List[Notification]) -> str:
        """Convert notifications to JSON"""
        return json.dumps([n.to_dict() for n in notifications])


# JavaScript/Dash integration
NOTIFICATION_CENTER_JS = '''
// Notification Center for Dash integration
window.NotificationCenter = {
    notifications: [],
    unreadCount: 0,
    
    init: function() {
        console.log('Notification Center initialized');
        this.requestPermission();
    },
    
    requestPermission: function() {
        if ('Notification' in window) {
            Notification.requestPermission();
        }
    },
    
    add: function(notification) {
        this.notifications.unshift(notification);
        this.unreadCount++;
        this.updateBadge();
        
        if (notification.priority === 'urgent' || notification.priority === 'critical') {
            this.showBrowserNotification(notification);
        }
        
        this.showToast(notification);
    },
    
    showBrowserNotification: function(notification) {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(notification.title, {
                body: notification.message,
                icon: notification.icon
            });
        }
    },
    
    showToast: function(notification) {
        const toast = document.createElement('div');
        toast.className = 'notification-toast ' + notification.priority;
        toast.innerHTML = `
            <div class="toast-icon">${notification.icon}</div>
            <div class="toast-content">
                <div class="toast-title">${notification.title}</div>
                <div class="toast-message">${notification.message}</div>
            </div>
            <button class="toast-close" onclick="NotificationCenter.dismissToast(this)">×</button>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);
        
        setTimeout(() => {
            this.dismissToast(toast.querySelector('.toast-close'));
        }, 5000);
    },
    
    dismissToast: function(closeBtn) {
        const toast = closeBtn.closest('.notification-toast');
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    },
    
    markAsRead: function(id) {
        const notification = this.notifications.find(n => n.id === id);
        if (notification && notification.status === 'unread') {
            notification.status = 'read';
            this.unreadCount--;
            this.updateBadge();
        }
    },
    
    markAllRead: function() {
        this.notifications.forEach(n => n.status = 'read');
        this.unreadCount = 0;
        this.updateBadge();
    },
    
    updateBadge: function() {
        const badge = document.querySelector('.notification-badge');
        if (badge) {
            badge.textContent = this.unreadCount > 99 ? '99+' : this.unreadCount;
            badge.style.display = this.unreadCount > 0 ? 'block' : 'none';
        }
    },
    
    getUnread: function() {
        return this.notifications.filter(n => n.status === 'unread');
    }
};

// CSS for toast notifications
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
.notification-toast {
    position: fixed;
    top: 20px;
    right: -400px;
    width: 350px;
    padding: 16px;
    background: #1e1e1e;
    border: 1px solid #333;
    border-radius: 8px;
    display: flex;
    align-items: flex-start;
    gap: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    transition: right 0.3s ease;
    z-index: 10000;
}
.notification-toast.show {
    right: 20px;
}
.notification-toast.urgent,
.notification-toast.critical {
    border-color: #ef5350;
}
.notification-toast.high {
    border-color: #ffa726;
}
.toast-icon {
    font-size: 24px;
}
.toast-content {
    flex: 1;
}
.toast-title {
    font-weight: bold;
    color: #fff;
    margin-bottom: 4px;
}
.toast-message {
    color: #888;
    font-size: 14px;
}
.toast-close {
    background: none;
    border: none;
    color: #666;
    font-size: 20px;
    cursor: pointer;
}
.toast-close:hover {
    color: #fff;
}
.notification-badge {
    position: absolute;
    top: -5px;
    right: -5px;
    background: #ef5350;
    color: white;
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 10px;
    display: none;
}
`;
document.head.appendChild(notificationStyles);

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    NotificationCenter.init();
});
'''


# Singleton instance
_notification_center = None

def get_notification_center() -> NotificationCenter:
    global _notification_center
    if _notification_center is None:
        _notification_center = NotificationCenter()
    return _notification_center

"""
Autonomous Position Monitor & Alert System
==========================================
AI-driven position monitoring that automatically:
- Monitors open positions health
- Generates alerts without user input
- Suggests optimal roll/adjustment timing
- Predicts risk events
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading
import time

logger = logging.getLogger(__name__)


class AlertPriority(Enum):
    """Alert priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AlertType(Enum):
    """Types of auto-generated alerts."""
    PRICE_TARGET = "price_target"
    IV_SPIKE = "iv_spike"
    IV_CRUSH = "iv_crush"
    THETA_DECAY = "theta_decay"
    DELTA_SHIFT = "delta_shift"
    ROLL_OPPORTUNITY = "roll_opportunity"
    EARNINGS_WARNING = "earnings_warning"
    STOP_LOSS = "stop_loss"
    PROFIT_TARGET = "profit_target"
    EXPIRATION_WARNING = "expiration_warning"
    ASSIGNMENT_RISK = "assignment_risk"
    MARGIN_WARNING = "margin_warning"


class PositionHealth(Enum):
    """Position health status."""
    EXCELLENT = "excellent"  # > 50% profit potential remaining
    GOOD = "good"           # 25-50% profit potential
    FAIR = "fair"           # 0-25% profit potential
    AT_RISK = "at_risk"     # Near breakeven
    DANGER = "danger"       # In loss territory


@dataclass
class Alert:
    """Individual alert."""
    alert_id: str
    alert_type: AlertType
    priority: AlertPriority
    ticker: str
    title: str
    message: str
    action_suggested: str
    timestamp: datetime
    is_read: bool = False
    is_dismissed: bool = False
    metadata: Dict = field(default_factory=dict)


@dataclass
class PositionStatus:
    """Status of a single position."""
    position_id: str
    ticker: str
    strategy: str
    health: PositionHealth
    health_score: float  # 0-100
    current_pnl: float
    max_profit: float
    max_loss: float
    days_to_expiry: int
    current_delta: float
    current_theta: float
    iv_rank: float
    risks: List[str]
    recommendations: List[str]
    last_updated: datetime


class PositionMonitor:
    """
    Autonomous position monitoring system.
    Continuously monitors positions and generates alerts.
    """
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.positions: Dict[str, PositionStatus] = {}
        self._alert_counter = 0
        self._monitoring = False
        self._monitor_thread = None
        
        # Alert thresholds (can be customized)
        self.thresholds = {
            'iv_spike_pct': 20,        # Alert if IV spikes 20%
            'iv_crush_pct': -15,       # Alert if IV drops 15%
            'delta_shift': 0.2,        # Alert if delta changes by 0.2
            'days_to_expiry_warning': 7,
            'profit_target_pct': 50,   # Alert at 50% of max profit
            'stop_loss_pct': -100,     # Alert at 100% of credit received
            'assignment_delta': 0.9,   # Warn when delta > 0.9 for short options
        }
    
    def analyze_position(self, position_data: Dict) -> PositionStatus:
        """
        Analyze a position and determine its health status.
        """
        ticker = position_data.get('ticker', 'UNKNOWN')
        strategy = position_data.get('strategy', 'Unknown')
        
        # Calculate P&L
        entry_cost = position_data.get('entry_cost', 0)
        current_value = position_data.get('current_value', 0)
        current_pnl = current_value - entry_cost
        
        # Get max profit/loss
        max_profit = position_data.get('max_profit', 100)
        max_loss = position_data.get('max_loss', -100)
        
        # Calculate profit potential remaining
        if max_profit > 0:
            profit_captured_pct = (current_pnl / max_profit) * 100 if max_profit != 0 else 0
        else:
            profit_captured_pct = 0
        
        # Determine health
        if profit_captured_pct >= 50:
            health = PositionHealth.EXCELLENT
            health_score = 90 + (profit_captured_pct - 50) * 0.2
        elif profit_captured_pct >= 25:
            health = PositionHealth.GOOD
            health_score = 70 + (profit_captured_pct - 25) * 0.8
        elif profit_captured_pct >= 0:
            health = PositionHealth.FAIR
            health_score = 50 + profit_captured_pct * 0.8
        elif profit_captured_pct >= -50:
            health = PositionHealth.AT_RISK
            health_score = 25 + (profit_captured_pct + 50) * 0.5
        else:
            health = PositionHealth.DANGER
            health_score = max(0, 25 + (profit_captured_pct + 50) * 0.5)
        
        # Get Greeks
        delta = position_data.get('delta', 0)
        theta = position_data.get('theta', 0)
        iv_rank = position_data.get('iv_rank', 50)
        dte = position_data.get('days_to_expiry', 30)
        
        # Identify risks
        risks = []
        recommendations = []
        
        if dte <= 7:
            risks.append(f"Only {dte} days to expiry")
            recommendations.append("Consider closing or rolling position")
        
        if abs(delta) > 0.7:
            risks.append(f"High delta exposure ({delta:.2f})")
            recommendations.append("Consider hedging or adjusting strikes")
        
        if iv_rank > 80:
            risks.append(f"High IV rank ({iv_rank:.0f}%)")
            recommendations.append("Good for premium selling, watch for IV crush")
        elif iv_rank < 20:
            risks.append(f"Low IV rank ({iv_rank:.0f}%)")
            recommendations.append("Consider long premium strategies")
        
        if health == PositionHealth.DANGER:
            risks.append("Position at significant loss")
            recommendations.append("Review stop-loss or consider adjustment")
        
        if profit_captured_pct >= 50:
            recommendations.append("Consider taking profits (50% target reached)")
        
        return PositionStatus(
            position_id=position_data.get('id', f"pos_{ticker}"),
            ticker=ticker,
            strategy=strategy,
            health=health,
            health_score=min(100, max(0, health_score)),
            current_pnl=current_pnl,
            max_profit=max_profit,
            max_loss=max_loss,
            days_to_expiry=dte,
            current_delta=delta,
            current_theta=theta,
            iv_rank=iv_rank,
            risks=risks,
            recommendations=recommendations,
            last_updated=datetime.now()
        )
    
    def check_for_alerts(self, position: PositionStatus, previous: Optional[PositionStatus] = None) -> List[Alert]:
        """
        Check a position for any conditions that should trigger alerts.
        """
        new_alerts = []
        
        # 1. Expiration warning
        if position.days_to_expiry <= self.thresholds['days_to_expiry_warning']:
            new_alerts.append(self._create_alert(
                AlertType.EXPIRATION_WARNING,
                AlertPriority.HIGH if position.days_to_expiry <= 3 else AlertPriority.MEDIUM,
                position.ticker,
                f"Expiration Warning: {position.ticker}",
                f"Position expires in {position.days_to_expiry} days",
                "Consider closing or rolling before expiration"
            ))
        
        # 2. Profit target
        if position.max_profit > 0:
            profit_pct = (position.current_pnl / position.max_profit) * 100
            if profit_pct >= self.thresholds['profit_target_pct']:
                new_alerts.append(self._create_alert(
                    AlertType.PROFIT_TARGET,
                    AlertPriority.MEDIUM,
                    position.ticker,
                    f"Profit Target Reached: {position.ticker}",
                    f"Position has captured {profit_pct:.0f}% of max profit (${position.current_pnl:.0f})",
                    "Consider taking profits and closing position"
                ))
        
        # 3. Stop loss
        if position.max_profit > 0 and position.current_pnl < 0:
            loss_pct = (position.current_pnl / position.max_profit) * 100
            if loss_pct <= self.thresholds['stop_loss_pct']:
                new_alerts.append(self._create_alert(
                    AlertType.STOP_LOSS,
                    AlertPriority.CRITICAL,
                    position.ticker,
                    f"Stop Loss Alert: {position.ticker}",
                    f"Position has lost {abs(loss_pct):.0f}% of credit received (${position.current_pnl:.0f})",
                    "Consider closing to limit further losses"
                ))
        
        # 4. Assignment risk
        if abs(position.current_delta) >= self.thresholds['assignment_delta']:
            new_alerts.append(self._create_alert(
                AlertType.ASSIGNMENT_RISK,
                AlertPriority.HIGH,
                position.ticker,
                f"Assignment Risk: {position.ticker}",
                f"Delta is {position.current_delta:.2f} - high assignment probability",
                "Monitor closely, consider rolling out or closing"
            ))
        
        # 5. Delta shift (if we have previous data)
        if previous:
            delta_change = abs(position.current_delta - previous.current_delta)
            if delta_change >= self.thresholds['delta_shift']:
                new_alerts.append(self._create_alert(
                    AlertType.DELTA_SHIFT,
                    AlertPriority.MEDIUM,
                    position.ticker,
                    f"Delta Shift: {position.ticker}",
                    f"Position delta changed from {previous.current_delta:.2f} to {position.current_delta:.2f}",
                    "Review position risk profile"
                ))
        
        # 6. Position health degradation
        if position.health == PositionHealth.DANGER:
            new_alerts.append(self._create_alert(
                AlertType.STOP_LOSS,
                AlertPriority.CRITICAL,
                position.ticker,
                f"Position Health Critical: {position.ticker}",
                f"Position health score: {position.health_score:.0f}/100",
                "Immediate review recommended"
            ))
        
        return new_alerts
    
    def _create_alert(self, alert_type: AlertType, priority: AlertPriority,
                     ticker: str, title: str, message: str, action: str) -> Alert:
        """Create a new alert."""
        self._alert_counter += 1
        return Alert(
            alert_id=f"alert_{self._alert_counter}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            alert_type=alert_type,
            priority=priority,
            ticker=ticker,
            title=title,
            message=message,
            action_suggested=action,
            timestamp=datetime.now()
        )
    
    def get_roll_suggestion(self, position: PositionStatus) -> Optional[Dict]:
        """
        AI-powered roll timing suggestion.
        Analyzes position to determine optimal roll timing.
        """
        suggestions = {
            'should_roll': False,
            'urgency': 'low',
            'reason': '',
            'suggested_action': '',
            'optimal_dte': 0,
            'price_target_met': False
        }
        
        # Check if roll is needed
        profit_pct = (position.current_pnl / position.max_profit * 100) if position.max_profit > 0 else 0
        
        # Time-based roll trigger
        if position.days_to_expiry <= 21 and profit_pct >= 50:
            suggestions['should_roll'] = True
            suggestions['urgency'] = 'medium'
            suggestions['reason'] = f"50% profit captured with {position.days_to_expiry} DTE - optimal roll window"
            suggestions['suggested_action'] = f"Roll to 45 DTE for additional premium capture"
            suggestions['optimal_dte'] = 45
            suggestions['price_target_met'] = True
        
        elif position.days_to_expiry <= 7:
            suggestions['should_roll'] = True
            suggestions['urgency'] = 'high'
            suggestions['reason'] = f"Only {position.days_to_expiry} days to expiry - gamma risk elevated"
            suggestions['suggested_action'] = "Roll out to reduce gamma exposure"
            suggestions['optimal_dte'] = 30
        
        # IV-based roll trigger
        elif position.iv_rank < 25 and profit_pct >= 75:
            suggestions['should_roll'] = True
            suggestions['urgency'] = 'low'
            suggestions['reason'] = "IV rank low and most profit captured"
            suggestions['suggested_action'] = "Consider closing or rolling to higher IV underlying"
        
        # Delta-based adjustment
        elif abs(position.current_delta) > 0.6:
            suggestions['should_roll'] = True
            suggestions['urgency'] = 'medium'
            suggestions['reason'] = f"Delta exposure too high ({position.current_delta:.2f})"
            suggestions['suggested_action'] = "Roll to adjust delta exposure"
        
        return suggestions
    
    def get_alerts(self, ticker: Optional[str] = None, unread_only: bool = False,
                   priority: Optional[AlertPriority] = None) -> List[Alert]:
        """Get alerts with optional filtering."""
        alerts = self.alerts.copy()
        
        if ticker:
            alerts = [a for a in alerts if a.ticker == ticker]
        
        if unread_only:
            alerts = [a for a in alerts if not a.is_read]
        
        if priority:
            alerts = [a for a in alerts if a.priority.value >= priority.value]
        
        # Sort by priority (highest first) then by time (newest first)
        alerts.sort(key=lambda a: (-a.priority.value, -a.timestamp.timestamp()))
        
        return alerts
    
    def mark_alert_read(self, alert_id: str):
        """Mark an alert as read."""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.is_read = True
                break
    
    def dismiss_alert(self, alert_id: str):
        """Dismiss an alert."""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.is_dismissed = True
                break
    
    def get_portfolio_health(self, positions: List[Dict]) -> Dict:
        """
        Analyze overall portfolio health.
        """
        if not positions:
            return {
                'overall_health': 'N/A',
                'health_score': 0,
                'total_pnl': 0,
                'positions_count': 0,
                'at_risk_count': 0,
                'recommendations': ['No open positions to analyze']
            }
        
        total_pnl = 0
        health_scores = []
        at_risk = 0
        all_risks = []
        
        for pos_data in positions:
            status = self.analyze_position(pos_data)
            total_pnl += status.current_pnl
            health_scores.append(status.health_score)
            
            if status.health in [PositionHealth.AT_RISK, PositionHealth.DANGER]:
                at_risk += 1
            
            all_risks.extend(status.risks)
        
        avg_health = sum(health_scores) / len(health_scores)
        
        # Determine overall health
        if avg_health >= 80:
            overall_health = 'Excellent'
        elif avg_health >= 60:
            overall_health = 'Good'
        elif avg_health >= 40:
            overall_health = 'Fair'
        elif avg_health >= 20:
            overall_health = 'At Risk'
        else:
            overall_health = 'Danger'
        
        # Generate portfolio recommendations
        recommendations = []
        
        if at_risk > 0:
            recommendations.append(f"{at_risk} position(s) need attention")
        
        if total_pnl > 0:
            recommendations.append(f"Portfolio profitable: +${total_pnl:.0f}")
        elif total_pnl < 0:
            recommendations.append(f"Portfolio at loss: ${total_pnl:.0f}")
        
        # Unique risks
        unique_risks = list(set(all_risks))
        if unique_risks:
            recommendations.append(f"Key risks: {', '.join(unique_risks[:3])}")
        
        return {
            'overall_health': overall_health,
            'health_score': round(avg_health, 1),
            'total_pnl': total_pnl,
            'positions_count': len(positions),
            'at_risk_count': at_risk,
            'recommendations': recommendations
        }


# Singleton instance
_position_monitor = None

def get_position_monitor() -> PositionMonitor:
    """Get singleton position monitor."""
    global _position_monitor
    if _position_monitor is None:
        _position_monitor = PositionMonitor()
    return _position_monitor


def quick_health_check(position_data: Dict) -> Dict:
    """
    Quick health check for a position.
    Returns simplified status for UI display.
    """
    monitor = get_position_monitor()
    status = monitor.analyze_position(position_data)
    
    health_colors = {
        PositionHealth.EXCELLENT: '#22c55e',
        PositionHealth.GOOD: '#84cc16',
        PositionHealth.FAIR: '#eab308',
        PositionHealth.AT_RISK: '#f97316',
        PositionHealth.DANGER: '#ef4444'
    }
    
    health_icons = {
        PositionHealth.EXCELLENT: '🟢',
        PositionHealth.GOOD: '🟢',
        PositionHealth.FAIR: '🟡',
        PositionHealth.AT_RISK: '🟠',
        PositionHealth.DANGER: '🔴'
    }
    
    return {
        'ticker': status.ticker,
        'strategy': status.strategy,
        'health': status.health.value,
        'health_score': round(status.health_score, 1),
        'health_color': health_colors[status.health],
        'health_icon': health_icons[status.health],
        'pnl': round(status.current_pnl, 2),
        'days_to_expiry': status.days_to_expiry,
        'delta': round(status.current_delta, 2),
        'theta': round(status.current_theta, 2),
        'iv_rank': round(status.iv_rank, 1),
        'risks': status.risks,
        'recommendations': status.recommendations
    }


def get_active_alerts(ticker: Optional[str] = None, count: int = 10) -> List[Dict]:
    """
    Get active alerts formatted for UI.
    """
    monitor = get_position_monitor()
    alerts = monitor.get_alerts(ticker=ticker, unread_only=False)[:count]
    
    priority_colors = {
        AlertPriority.LOW: '#6b7280',
        AlertPriority.MEDIUM: '#eab308',
        AlertPriority.HIGH: '#f97316',
        AlertPriority.CRITICAL: '#ef4444'
    }
    
    priority_icons = {
        AlertPriority.LOW: 'ℹ️',
        AlertPriority.MEDIUM: '⚠️',
        AlertPriority.HIGH: '🔔',
        AlertPriority.CRITICAL: '🚨'
    }
    
    return [
        {
            'id': a.alert_id,
            'type': a.alert_type.value,
            'priority': a.priority.name,
            'priority_color': priority_colors[a.priority],
            'priority_icon': priority_icons[a.priority],
            'ticker': a.ticker,
            'title': a.title,
            'message': a.message,
            'action': a.action_suggested,
            'timestamp': a.timestamp.isoformat(),
            'is_read': a.is_read
        }
        for a in alerts
        if not a.is_dismissed
    ]

#!/usr/bin/env python3
"""
Monitoring & Alerts Engine for Enhanced Alpaca Options Lab
==========================================================

Improvements 76-100: Real-time Monitoring & Alerting
Focus: GLD, SLV, SPY + Tech Stocks

Fully autonomous monitoring - zero user interaction.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio
from collections import deque

logger = logging.getLogger(__name__)

# Import focus tickers
try:
    from .ai_automation_engine import ALL_FOCUS_TICKERS, FOCUS_TICKERS
except ImportError:
    ALL_FOCUS_TICKERS = ['GLD', 'SLV', 'SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'GOOGL']
    FOCUS_TICKERS = {}


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = 'info'
    WARNING = 'warning'
    CRITICAL = 'critical'
    URGENT = 'urgent'


class AlertType(Enum):
    """Types of alerts."""
    PRICE_MOVE = 'price_move'
    IV_CHANGE = 'iv_change'
    POSITION_PNL = 'position_pnl'
    GREEKS_LIMIT = 'greeks_limit'
    FLOW_UNUSUAL = 'flow_unusual'
    EARNINGS = 'earnings'
    MARKET_OPEN = 'market_open'
    MARKET_CLOSE = 'market_close'


@dataclass
class Alert:
    """Alert data structure."""
    id: str
    type: AlertType
    severity: AlertSeverity
    ticker: str
    message: str
    data: Dict
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False


# =============================================================================
# IMPROVEMENT 76-80: Real-time Price Monitor
# =============================================================================

class PriceMonitor:
    """
    Improvement #76-80: Real-time price monitoring.
    Monitors all focus tickers automatically.
    """
    
    def __init__(self):
        self.price_cache = {}
        self.price_history = {ticker: deque(maxlen=1000) for ticker in ALL_FOCUS_TICKERS}
        self.alerts = []
    
    # Improvement #76: Price change alerts
    def check_price_alerts(self, ticker: str, current_price: float,
                          threshold_pct: float = 0.02) -> Optional[Alert]:
        """Alert on significant price moves."""
        history = self.price_history.get(ticker, deque())
        
        if len(history) < 2:
            return None
        
        # Compare to recent prices
        prev_price = history[-1]
        change_pct = (current_price - prev_price) / prev_price
        
        if abs(change_pct) >= threshold_pct:
            severity = AlertSeverity.WARNING if abs(change_pct) < 0.05 else AlertSeverity.CRITICAL
            direction = 'UP' if change_pct > 0 else 'DOWN'
            
            return Alert(
                id=f'price_{ticker}_{datetime.now().timestamp()}',
                type=AlertType.PRICE_MOVE,
                severity=severity,
                ticker=ticker,
                message=f'{ticker} moved {direction} {abs(change_pct):.1%}',
                data={'change_pct': change_pct, 'price': current_price}
            )
        
        return None
    
    # Improvement #77: Support/resistance breach alerts
    def check_sr_breach(self, ticker: str, price: float,
                       support: float, resistance: float) -> Optional[Alert]:
        """Alert when price breaches support/resistance."""
        if price < support:
            return Alert(
                id=f'support_{ticker}_{datetime.now().timestamp()}',
                type=AlertType.PRICE_MOVE,
                severity=AlertSeverity.WARNING,
                ticker=ticker,
                message=f'{ticker} broke below support ${support:.2f}',
                data={'price': price, 'support': support}
            )
        
        if price > resistance:
            return Alert(
                id=f'resistance_{ticker}_{datetime.now().timestamp()}',
                type=AlertType.PRICE_MOVE,
                severity=AlertSeverity.WARNING,
                ticker=ticker,
                message=f'{ticker} broke above resistance ${resistance:.2f}',
                data={'price': price, 'resistance': resistance}
            )
        
        return None
    
    # Improvement #78: Gap detection
    def detect_gap(self, ticker: str, open_price: float, prev_close: float) -> Optional[Alert]:
        """Detect opening gaps."""
        gap_pct = (open_price - prev_close) / prev_close
        
        if abs(gap_pct) >= 0.02:  # 2% gap
            direction = 'UP' if gap_pct > 0 else 'DOWN'
            severity = AlertSeverity.WARNING if abs(gap_pct) < 0.05 else AlertSeverity.CRITICAL
            
            return Alert(
                id=f'gap_{ticker}_{datetime.now().timestamp()}',
                type=AlertType.PRICE_MOVE,
                severity=severity,
                ticker=ticker,
                message=f'{ticker} gapped {direction} {abs(gap_pct):.1%}',
                data={'gap_pct': gap_pct, 'open': open_price, 'prev_close': prev_close}
            )
        
        return None
    
    # Improvement #79: Intraday high/low alerts
    def check_intraday_extremes(self, ticker: str, price: float,
                               daily_high: float, daily_low: float) -> Optional[Alert]:
        """Alert on new intraday highs/lows."""
        if price >= daily_high:
            return Alert(
                id=f'high_{ticker}_{datetime.now().timestamp()}',
                type=AlertType.PRICE_MOVE,
                severity=AlertSeverity.INFO,
                ticker=ticker,
                message=f'{ticker} new intraday HIGH: ${price:.2f}',
                data={'price': price, 'type': 'high'}
            )
        
        if price <= daily_low:
            return Alert(
                id=f'low_{ticker}_{datetime.now().timestamp()}',
                type=AlertType.PRICE_MOVE,
                severity=AlertSeverity.INFO,
                ticker=ticker,
                message=f'{ticker} new intraday LOW: ${price:.2f}',
                data={'price': price, 'type': 'low'}
            )
        
        return None
    
    # Improvement #80: Moving average cross alerts
    def check_ma_cross(self, ticker: str, prices: pd.Series) -> Optional[Alert]:
        """Alert on moving average crossovers."""
        if len(prices) < 50:
            return None
        
        ma20 = prices.rolling(20).mean()
        ma50 = prices.rolling(50).mean()
        
        # Check for cross in last 2 periods
        cross_up = ma20.iloc[-1] > ma50.iloc[-1] and ma20.iloc[-2] <= ma50.iloc[-2]
        cross_down = ma20.iloc[-1] < ma50.iloc[-1] and ma20.iloc[-2] >= ma50.iloc[-2]
        
        if cross_up:
            return Alert(
                id=f'ma_cross_{ticker}_{datetime.now().timestamp()}',
                type=AlertType.PRICE_MOVE,
                severity=AlertSeverity.INFO,
                ticker=ticker,
                message=f'{ticker} BULLISH MA cross (20 > 50)',
                data={'signal': 'bullish', 'ma20': ma20.iloc[-1], 'ma50': ma50.iloc[-1]}
            )
        
        if cross_down:
            return Alert(
                id=f'ma_cross_{ticker}_{datetime.now().timestamp()}',
                type=AlertType.PRICE_MOVE,
                severity=AlertSeverity.INFO,
                ticker=ticker,
                message=f'{ticker} BEARISH MA cross (20 < 50)',
                data={'signal': 'bearish', 'ma20': ma20.iloc[-1], 'ma50': ma50.iloc[-1]}
            )
        
        return None
    
    def update_price(self, ticker: str, price: float):
        """Update price cache and history."""
        self.price_cache[ticker] = price
        self.price_history[ticker].append(price)


# =============================================================================
# IMPROVEMENT 81-85: IV & Greeks Monitor
# =============================================================================

class IVGreeksMonitor:
    """
    Improvement #81-85: IV and Greeks monitoring.
    Alerts on significant IV and Greeks changes.
    """
    
    def __init__(self):
        self.iv_cache = {}
        self.greeks_limits = {
            'delta': 500,
            'gamma': 100,
            'theta': -300,
            'vega': 500
        }
    
    # Improvement #81: IV spike alerts
    def check_iv_spike(self, ticker: str, current_iv: float,
                      historical_iv: float) -> Optional[Alert]:
        """Alert on IV spikes."""
        iv_change = (current_iv - historical_iv) / historical_iv
        
        if abs(iv_change) >= 0.15:  # 15% IV change
            direction = 'SPIKE' if iv_change > 0 else 'CRUSH'
            severity = AlertSeverity.WARNING if abs(iv_change) < 0.25 else AlertSeverity.CRITICAL
            
            return Alert(
                id=f'iv_{ticker}_{datetime.now().timestamp()}',
                type=AlertType.IV_CHANGE,
                severity=severity,
                ticker=ticker,
                message=f'{ticker} IV {direction}: {current_iv:.1%} ({iv_change:+.1%})',
                data={'current_iv': current_iv, 'change': iv_change}
            )
        
        return None
    
    # Improvement #82: IV rank alerts
    def check_iv_rank_extremes(self, ticker: str, iv_rank: float) -> Optional[Alert]:
        """Alert on extreme IV rank readings."""
        if iv_rank > 80:
            return Alert(
                id=f'ivr_high_{ticker}_{datetime.now().timestamp()}',
                type=AlertType.IV_CHANGE,
                severity=AlertSeverity.INFO,
                ticker=ticker,
                message=f'{ticker} HIGH IV Rank: {iv_rank:.0f}% - Good for selling premium',
                data={'iv_rank': iv_rank, 'action': 'sell_premium'}
            )
        
        if iv_rank < 20:
            return Alert(
                id=f'ivr_low_{ticker}_{datetime.now().timestamp()}',
                type=AlertType.IV_CHANGE,
                severity=AlertSeverity.INFO,
                ticker=ticker,
                message=f'{ticker} LOW IV Rank: {iv_rank:.0f}% - Good for buying premium',
                data={'iv_rank': iv_rank, 'action': 'buy_premium'}
            )
        
        return None
    
    # Improvement #83: Portfolio Greeks alerts
    def check_portfolio_greeks(self, portfolio_greeks: Dict) -> List[Alert]:
        """Alert when portfolio Greeks exceed limits."""
        alerts = []
        
        for greek, value in portfolio_greeks.items():
            limit = self.greeks_limits.get(greek, float('inf'))
            
            if greek == 'theta':
                if value < limit:  # Theta is negative
                    alerts.append(Alert(
                        id=f'greek_{greek}_{datetime.now().timestamp()}',
                        type=AlertType.GREEKS_LIMIT,
                        severity=AlertSeverity.WARNING,
                        ticker='PORTFOLIO',
                        message=f'Portfolio {greek.upper()} exceeds limit: {value:.0f}',
                        data={'greek': greek, 'value': value, 'limit': limit}
                    ))
            else:
                if abs(value) > limit:
                    alerts.append(Alert(
                        id=f'greek_{greek}_{datetime.now().timestamp()}',
                        type=AlertType.GREEKS_LIMIT,
                        severity=AlertSeverity.WARNING,
                        ticker='PORTFOLIO',
                        message=f'Portfolio {greek.upper()} exceeds limit: {value:.0f}',
                        data={'greek': greek, 'value': value, 'limit': limit}
                    ))
        
        return alerts
    
    # Improvement #84: Gamma risk alerts
    def check_gamma_risk(self, positions: List[Dict]) -> List[Alert]:
        """Alert on high gamma risk positions."""
        alerts = []
        
        for pos in positions:
            dte = pos.get('dte', 30)
            gamma = pos.get('gamma', 0)
            
            # High gamma near expiry
            if dte < 7 and abs(gamma) > 0.1:
                alerts.append(Alert(
                    id=f'gamma_{pos.get("id")}_{datetime.now().timestamp()}',
                    type=AlertType.GREEKS_LIMIT,
                    severity=AlertSeverity.CRITICAL,
                    ticker=pos.get('underlying', ''),
                    message=f'HIGH GAMMA RISK: {pos.get("symbol")} ({dte} DTE)',
                    data={'position': pos, 'gamma': gamma, 'dte': dte}
                ))
        
        return alerts
    
    # Improvement #85: Vega exposure alerts
    def check_vega_exposure(self, positions: List[Dict], vix: float) -> List[Alert]:
        """Alert on significant vega exposure."""
        alerts = []
        total_vega = sum(p.get('vega', 0) * p.get('quantity', 1) for p in positions)
        
        # High vega in volatile market
        if abs(total_vega) > 300 and vix > 20:
            alerts.append(Alert(
                id=f'vega_{datetime.now().timestamp()}',
                type=AlertType.GREEKS_LIMIT,
                severity=AlertSeverity.WARNING,
                ticker='PORTFOLIO',
                message=f'High vega ({total_vega:.0f}) with elevated VIX ({vix:.1f})',
                data={'vega': total_vega, 'vix': vix}
            ))
        
        return alerts


# =============================================================================
# IMPROVEMENT 86-90: Position Monitor
# =============================================================================

class PositionMonitor:
    """
    Improvement #86-90: Position P&L monitoring.
    Tracks all positions and alerts on significant changes.
    """
    
    def __init__(self):
        self.profit_target = 0.50
        self.stop_loss = -1.00  # 100% of credit received
    
    # Improvement #86: P&L alerts
    def check_pnl_alerts(self, positions: List[Dict]) -> List[Alert]:
        """Alert on significant P&L changes."""
        alerts = []
        
        for pos in positions:
            pnl_pct = pos.get('pnl_pct', 0)
            
            # Profit target
            if pnl_pct >= self.profit_target:
                alerts.append(Alert(
                    id=f'profit_{pos.get("id")}_{datetime.now().timestamp()}',
                    type=AlertType.POSITION_PNL,
                    severity=AlertSeverity.INFO,
                    ticker=pos.get('underlying', ''),
                    message=f'PROFIT TARGET: {pos.get("symbol")} at {pnl_pct:.0%}',
                    data={'position': pos, 'action': 'consider_closing'}
                ))
            
            # Stop loss
            if pnl_pct <= self.stop_loss:
                alerts.append(Alert(
                    id=f'stop_{pos.get("id")}_{datetime.now().timestamp()}',
                    type=AlertType.POSITION_PNL,
                    severity=AlertSeverity.CRITICAL,
                    ticker=pos.get('underlying', ''),
                    message=f'STOP LOSS: {pos.get("symbol")} at {pnl_pct:.0%}',
                    data={'position': pos, 'action': 'close_immediately'}
                ))
        
        return alerts
    
    # Improvement #87: Expiration alerts
    def check_expiration_alerts(self, positions: List[Dict]) -> List[Alert]:
        """Alert on upcoming expirations."""
        alerts = []
        
        for pos in positions:
            dte = pos.get('dte', 30)
            
            if dte <= 1:
                alerts.append(Alert(
                    id=f'exp_{pos.get("id")}_{datetime.now().timestamp()}',
                    type=AlertType.POSITION_PNL,
                    severity=AlertSeverity.URGENT,
                    ticker=pos.get('underlying', ''),
                    message=f'EXPIRING TODAY: {pos.get("symbol")}',
                    data={'position': pos, 'action': 'close_or_roll'}
                ))
            elif dte <= 7:
                alerts.append(Alert(
                    id=f'exp_{pos.get("id")}_{datetime.now().timestamp()}',
                    type=AlertType.POSITION_PNL,
                    severity=AlertSeverity.WARNING,
                    ticker=pos.get('underlying', ''),
                    message=f'EXPIRING SOON ({dte} DTE): {pos.get("symbol")}',
                    data={'position': pos, 'action': 'review'}
                ))
        
        return alerts
    
    # Improvement #88: Assignment risk alerts
    def check_assignment_risk(self, positions: List[Dict]) -> List[Alert]:
        """Alert on positions with assignment risk."""
        alerts = []
        
        for pos in positions:
            if pos.get('strategy') in ['short_put', 'credit_spread']:
                delta = abs(pos.get('delta', 0))
                dte = pos.get('dte', 30)
                
                if delta > 0.7 and dte < 7:
                    alerts.append(Alert(
                        id=f'assign_{pos.get("id")}_{datetime.now().timestamp()}',
                        type=AlertType.POSITION_PNL,
                        severity=AlertSeverity.CRITICAL,
                        ticker=pos.get('underlying', ''),
                        message=f'ASSIGNMENT RISK: {pos.get("symbol")} (Delta: {delta:.2f})',
                        data={'position': pos, 'delta': delta}
                    ))
        
        return alerts
    
    # Improvement #89: Tested position alerts
    def check_tested_positions(self, positions: List[Dict]) -> List[Alert]:
        """Alert when position is being tested."""
        alerts = []
        
        for pos in positions:
            # Check if price approaching short strike
            short_strike = pos.get('short_strike')
            current_price = pos.get('underlying_price')
            
            if short_strike and current_price:
                distance = abs(current_price - short_strike) / short_strike
                
                if distance < 0.02:  # Within 2%
                    alerts.append(Alert(
                        id=f'tested_{pos.get("id")}_{datetime.now().timestamp()}',
                        type=AlertType.POSITION_PNL,
                        severity=AlertSeverity.WARNING,
                        ticker=pos.get('underlying', ''),
                        message=f'POSITION TESTED: {pos.get("symbol")} near ${short_strike}',
                        data={'position': pos, 'distance': distance}
                    ))
        
        return alerts
    
    # Improvement #90: Daily P&L summary
    def generate_daily_summary(self, positions: List[Dict]) -> Dict:
        """Generate daily P&L summary."""
        total_pnl = sum(p.get('daily_pnl', 0) for p in positions)
        winners = [p for p in positions if p.get('daily_pnl', 0) > 0]
        losers = [p for p in positions if p.get('daily_pnl', 0) < 0]
        
        return {
            'total_pnl': total_pnl,
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': len(winners) / len(positions) if positions else 0,
            'biggest_winner': max(positions, key=lambda x: x.get('daily_pnl', 0)) if positions else None,
            'biggest_loser': min(positions, key=lambda x: x.get('daily_pnl', 0)) if positions else None,
            'timestamp': datetime.now().isoformat()
        }


# =============================================================================
# IMPROVEMENT 91-95: Market Events Monitor
# =============================================================================

class MarketEventsMonitor:
    """
    Improvement #91-95: Market events monitoring.
    Tracks earnings, dividends, and market hours.
    """
    
    def __init__(self):
        self.earnings_calendar = {}
        self.market_hours = {
            'pre_market': ('04:00', '09:30'),
            'regular': ('09:30', '16:00'),
            'after_hours': ('16:00', '20:00')
        }
    
    # Improvement #91: Earnings alerts
    def check_earnings_alerts(self, ticker: str, days_until: int) -> Optional[Alert]:
        """Alert on upcoming earnings."""
        if days_until <= 7:
            severity = AlertSeverity.CRITICAL if days_until <= 1 else AlertSeverity.WARNING
            
            return Alert(
                id=f'earnings_{ticker}_{datetime.now().timestamp()}',
                type=AlertType.EARNINGS,
                severity=severity,
                ticker=ticker,
                message=f'{ticker} EARNINGS in {days_until} days - IV expansion expected',
                data={'days_until': days_until, 'action': 'review_positions'}
            )
        
        return None
    
    # Improvement #92: Market open/close alerts
    def check_market_hours(self) -> Optional[Alert]:
        """Alert at market open/close."""
        now = datetime.now()
        current_time = now.strftime('%H:%M')
        
        if current_time == '09:30':
            return Alert(
                id=f'market_open_{now.date()}',
                type=AlertType.MARKET_OPEN,
                severity=AlertSeverity.INFO,
                ticker='MARKET',
                message='🔔 Market is NOW OPEN',
                data={'time': current_time}
            )
        
        if current_time == '15:45':
            return Alert(
                id=f'market_close_warning_{now.date()}',
                type=AlertType.MARKET_CLOSE,
                severity=AlertSeverity.WARNING,
                ticker='MARKET',
                message='⚠️ Market closes in 15 minutes',
                data={'time': current_time}
            )
        
        return None
    
    # Improvement #93: FOMC/Fed alerts
    def check_fed_events(self, event_date: str, event_type: str) -> Optional[Alert]:
        """Alert on Federal Reserve events."""
        event_dt = datetime.strptime(event_date, '%Y-%m-%d')
        days_until = (event_dt - datetime.now()).days
        
        if days_until <= 3:
            return Alert(
                id=f'fed_{event_type}_{datetime.now().timestamp()}',
                type=AlertType.EARNINGS,  # Using earnings type for events
                severity=AlertSeverity.WARNING,
                ticker='MARKET',
                message=f'🏛️ {event_type} in {days_until} days - Expect volatility',
                data={'event': event_type, 'date': event_date}
            )
        
        return None
    
    # Improvement #94: Dividend alerts
    def check_dividend_alert(self, ticker: str, ex_date: str) -> Optional[Alert]:
        """Alert on ex-dividend dates."""
        ex_dt = datetime.strptime(ex_date, '%Y-%m-%d')
        days_until = (ex_dt - datetime.now()).days
        
        if days_until <= 3:
            return Alert(
                id=f'div_{ticker}_{datetime.now().timestamp()}',
                type=AlertType.EARNINGS,
                severity=AlertSeverity.INFO,
                ticker=ticker,
                message=f'{ticker} goes ex-dividend in {days_until} days',
                data={'ex_date': ex_date, 'action': 'consider_early_assignment'}
            )
        
        return None
    
    # Improvement #95: VIX spike alerts
    def check_vix_alert(self, vix: float, prev_vix: float) -> Optional[Alert]:
        """Alert on VIX spikes."""
        change = (vix - prev_vix) / prev_vix
        
        if vix > 25 or change > 0.15:
            severity = AlertSeverity.CRITICAL if vix > 30 else AlertSeverity.WARNING
            
            return Alert(
                id=f'vix_{datetime.now().timestamp()}',
                type=AlertType.IV_CHANGE,
                severity=severity,
                ticker='VIX',
                message=f'⚠️ VIX at {vix:.1f} ({change:+.1%}) - High volatility',
                data={'vix': vix, 'change': change}
            )
        
        return None


# =============================================================================
# IMPROVEMENT 96-100: Alert Manager & Dashboard
# =============================================================================

class AlertManager:
    """
    Improvement #96-100: Centralized alert management.
    Manages all alerts and notifications.
    """
    
    def __init__(self):
        self.alerts = deque(maxlen=500)  # Keep last 500 alerts
        self.callbacks = []
        self.muted_types = set()
    
    # Improvement #96: Alert aggregation
    def add_alert(self, alert: Alert):
        """Add alert and trigger callbacks."""
        if alert.type in self.muted_types:
            return
        
        self.alerts.append(alert)
        
        # Trigger callbacks
        for callback in self.callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    # Improvement #97: Alert filtering
    def get_alerts(self, severity: Optional[AlertSeverity] = None,
                  alert_type: Optional[AlertType] = None,
                  ticker: Optional[str] = None,
                  since: Optional[datetime] = None) -> List[Alert]:
        """Get filtered alerts."""
        filtered = list(self.alerts)
        
        if severity:
            filtered = [a for a in filtered if a.severity == severity]
        
        if alert_type:
            filtered = [a for a in filtered if a.type == alert_type]
        
        if ticker:
            filtered = [a for a in filtered if a.ticker == ticker]
        
        if since:
            filtered = [a for a in filtered if a.timestamp >= since]
        
        return filtered
    
    # Improvement #98: Alert statistics
    def get_statistics(self) -> Dict:
        """Get alert statistics."""
        if not self.alerts:
            return {'total': 0}
        
        by_severity = {}
        by_type = {}
        
        for alert in self.alerts:
            by_severity[alert.severity.value] = by_severity.get(alert.severity.value, 0) + 1
            by_type[alert.type.value] = by_type.get(alert.type.value, 0) + 1
        
        return {
            'total': len(self.alerts),
            'by_severity': by_severity,
            'by_type': by_type,
            'unacknowledged': sum(1 for a in self.alerts if not a.acknowledged),
            'critical_count': by_severity.get('critical', 0) + by_severity.get('urgent', 0)
        }
    
    # Improvement #99: Alert acknowledgment
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False
    
    # Improvement #100: Alert summary dashboard
    def get_dashboard_summary(self) -> Dict:
        """Get summary for dashboard display."""
        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        recent = self.get_alerts(since=last_hour)
        today_alerts = self.get_alerts(since=today)
        
        critical = [a for a in recent if a.severity in [AlertSeverity.CRITICAL, AlertSeverity.URGENT]]
        
        return {
            'total_today': len(today_alerts),
            'last_hour': len(recent),
            'critical_unack': len([a for a in critical if not a.acknowledged]),
            'latest_alerts': list(self.alerts)[-10:],
            'statistics': self.get_statistics(),
            'status': 'ATTENTION_NEEDED' if critical else 'NORMAL'
        }
    
    def register_callback(self, callback: Callable[[Alert], None]):
        """Register callback for new alerts."""
        self.callbacks.append(callback)
    
    def mute_type(self, alert_type: AlertType):
        """Mute a specific alert type."""
        self.muted_types.add(alert_type)
    
    def unmute_type(self, alert_type: AlertType):
        """Unmute a specific alert type."""
        self.muted_types.discard(alert_type)


# =============================================================================
# Master Monitor - Combines all monitors
# =============================================================================

class MasterMonitor:
    """Combines all monitoring systems into one autonomous system."""
    
    def __init__(self):
        self.price_monitor = PriceMonitor()
        self.iv_greeks_monitor = IVGreeksMonitor()
        self.position_monitor = PositionMonitor()
        self.events_monitor = MarketEventsMonitor()
        self.alert_manager = AlertManager()
        
        self.running = False
    
    def run_all_checks(self, market_data: Dict, positions: List[Dict]) -> List[Alert]:
        """Run all monitoring checks."""
        all_alerts = []
        
        # Price checks
        for ticker in ALL_FOCUS_TICKERS:
            if ticker in market_data:
                price = market_data[ticker].get('price', 0)
                self.price_monitor.update_price(ticker, price)
                
                alert = self.price_monitor.check_price_alerts(ticker, price)
                if alert:
                    all_alerts.append(alert)
        
        # IV checks
        for ticker in ALL_FOCUS_TICKERS:
            if ticker in market_data:
                iv = market_data[ticker].get('iv', 0)
                iv_rank = market_data[ticker].get('iv_rank', 50)
                
                alert = self.iv_greeks_monitor.check_iv_rank_extremes(ticker, iv_rank)
                if alert:
                    all_alerts.append(alert)
        
        # Position checks
        all_alerts.extend(self.position_monitor.check_pnl_alerts(positions))
        all_alerts.extend(self.position_monitor.check_expiration_alerts(positions))
        
        # Add to alert manager
        for alert in all_alerts:
            self.alert_manager.add_alert(alert)
        
        return all_alerts
    
    def get_status(self) -> Dict:
        """Get overall monitoring status."""
        return {
            'monitors_active': True,
            'focus_tickers': ALL_FOCUS_TICKERS,
            'alert_summary': self.alert_manager.get_dashboard_summary(),
            'last_check': datetime.now().isoformat()
        }


# =============================================================================
# Singleton instances
# =============================================================================

price_monitor = PriceMonitor()
iv_greeks_monitor = IVGreeksMonitor()
position_monitor = PositionMonitor()
events_monitor = MarketEventsMonitor()
alert_manager = AlertManager()
master_monitor = MasterMonitor()

__all__ = [
    'AlertSeverity', 'AlertType', 'Alert',
    'PriceMonitor', 'IVGreeksMonitor', 'PositionMonitor',
    'MarketEventsMonitor', 'AlertManager', 'MasterMonitor',
    'price_monitor', 'iv_greeks_monitor', 'position_monitor',
    'events_monitor', 'alert_manager', 'master_monitor'
]

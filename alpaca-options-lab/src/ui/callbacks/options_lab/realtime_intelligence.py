"""
Real-Time Intelligence Module
=============================
Live monitoring and intelligence features:
- Live P&L tracker
- Alert engine
- Webhook integration
- Market scanner
- News impact analyzer

Author: AI/ML Options Lab
"""

import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import threading
import queue
import json

logger = logging.getLogger(__name__)


# ============================================================
# DATA CLASSES
# ============================================================

class AlertPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AlertType(Enum):
    PRICE = "price"
    PNL = "pnl"
    RISK = "risk"
    NEWS = "news"
    VOLUME = "volume"
    GREEK = "greek"


@dataclass
class PnLSnapshot:
    """Point-in-time P&L snapshot."""
    timestamp: datetime
    position_id: str
    ticker: str
    
    # P&L metrics
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    pnl_pct: float
    
    # Greeks contribution
    delta_pnl: float
    gamma_pnl: float
    theta_pnl: float
    vega_pnl: float


@dataclass
class Alert:
    """Trading alert."""
    alert_id: str
    timestamp: datetime
    alert_type: AlertType
    priority: AlertPriority
    ticker: str
    message: str
    value: float
    threshold: float
    acknowledged: bool = False


@dataclass
class AlertRule:
    """Alert rule configuration."""
    rule_id: str
    name: str
    alert_type: AlertType
    condition: str  # 'above', 'below', 'change_pct'
    threshold: float
    ticker: Optional[str]  # None = all
    priority: AlertPriority
    enabled: bool = True


@dataclass
class ScanResult:
    """Market scanner result."""
    ticker: str
    pattern: str
    signal_strength: float
    current_price: float
    change_pct: float
    volume_ratio: float
    iv_percentile: float
    recommendation: str


@dataclass
class NewsItem:
    """News item with impact analysis."""
    headline: str
    timestamp: datetime
    source: str
    tickers: List[str]
    sentiment: float  # -1 to 1
    impact_score: float  # 0 to 100
    category: str


# ============================================================
# LIVE P&L TRACKER
# ============================================================

class LivePnLTracker:
    """
    Real-time P&L tracking with Greeks attribution.
    """
    
    def __init__(self):
        self.positions: Dict[str, Dict] = {}
        self.pnl_history: List[PnLSnapshot] = []
        self.last_prices: Dict[str, float] = {}
    
    def add_position(self, position_id: str, ticker: str,
                     entry_price: float, contracts: int,
                     greeks: Dict = None):
        """Add position to tracker."""
        self.positions[position_id] = {
            'ticker': ticker,
            'entry_price': entry_price,
            'contracts': contracts,
            'greeks': greeks or {'delta': 0.5, 'gamma': 0.01, 'theta': -0.05, 'vega': 0.1},
            'entry_time': datetime.now()
        }
    
    def update_prices(self, prices: Dict[str, float]):
        """Update current prices."""
        self.last_prices.update(prices)
        self._calculate_all_pnl()
    
    def _calculate_all_pnl(self):
        """Calculate P&L for all positions."""
        for pos_id, pos in self.positions.items():
            ticker = pos['ticker']
            if ticker not in self.last_prices:
                continue
            
            current_price = self.last_prices[ticker]
            entry_price = pos['entry_price']
            contracts = pos['contracts']
            greeks = pos['greeks']
            
            # Price change
            price_change = current_price - entry_price
            pct_change = price_change / entry_price
            
            # Unrealized P&L (simplified option P&L)
            unrealized = price_change * contracts * 100
            
            # Greeks-attributed P&L
            days_held = (datetime.now() - pos['entry_time']).days
            
            delta_pnl = greeks['delta'] * price_change * contracts * 100
            gamma_pnl = 0.5 * greeks['gamma'] * (price_change ** 2) * contracts * 100
            theta_pnl = greeks['theta'] * days_held * contracts * 100
            vega_pnl = greeks['vega'] * (pct_change * 10) * contracts * 100  # IV proxy
            
            snapshot = PnLSnapshot(
                timestamp=datetime.now(),
                position_id=pos_id,
                ticker=ticker,
                unrealized_pnl=round(unrealized, 2),
                realized_pnl=0,
                total_pnl=round(unrealized, 2),
                pnl_pct=round(pct_change * 100, 2),
                delta_pnl=round(delta_pnl, 2),
                gamma_pnl=round(gamma_pnl, 2),
                theta_pnl=round(theta_pnl, 2),
                vega_pnl=round(vega_pnl, 2)
            )
            
            self.pnl_history.append(snapshot)
    
    def get_portfolio_pnl(self) -> Dict:
        """Get aggregate portfolio P&L."""
        if not self.pnl_history:
            return {'total_pnl': 0, 'unrealized': 0, 'realized': 0}
        
        # Get latest for each position
        latest = {}
        for snapshot in self.pnl_history:
            latest[snapshot.position_id] = snapshot
        
        total_unrealized = sum(s.unrealized_pnl for s in latest.values())
        total_realized = sum(s.realized_pnl for s in latest.values())
        
        return {
            'total_pnl': round(total_unrealized + total_realized, 2),
            'unrealized': round(total_unrealized, 2),
            'realized': round(total_realized, 2),
            'delta_contribution': round(sum(s.delta_pnl for s in latest.values()), 2),
            'gamma_contribution': round(sum(s.gamma_pnl for s in latest.values()), 2),
            'theta_contribution': round(sum(s.theta_pnl for s in latest.values()), 2),
            'vega_contribution': round(sum(s.vega_pnl for s in latest.values()), 2),
            'positions': len(latest)
        }
    
    def get_position_details(self) -> List[Dict]:
        """Get details for all positions."""
        latest = {}
        for snapshot in self.pnl_history:
            latest[snapshot.position_id] = snapshot
        
        return [
            {
                'position_id': s.position_id,
                'ticker': s.ticker,
                'pnl': s.total_pnl,
                'pnl_pct': s.pnl_pct,
                'greeks_breakdown': {
                    'delta': s.delta_pnl,
                    'gamma': s.gamma_pnl,
                    'theta': s.theta_pnl,
                    'vega': s.vega_pnl
                }
            }
            for s in latest.values()
        ]


# ============================================================
# ALERT ENGINE
# ============================================================

class AlertEngine:
    """
    Configurable alert system.
    """
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: List[Alert] = []
        self.alert_counter = 0
        self.callbacks: List[Callable] = []
    
    def add_rule(self, name: str, alert_type: AlertType,
                 condition: str, threshold: float,
                 ticker: str = None,
                 priority: AlertPriority = AlertPriority.MEDIUM) -> str:
        """Add alert rule."""
        rule_id = f"RULE_{len(self.rules):03d}"
        
        self.rules[rule_id] = AlertRule(
            rule_id=rule_id,
            name=name,
            alert_type=alert_type,
            condition=condition,
            threshold=threshold,
            ticker=ticker,
            priority=priority,
            enabled=True
        )
        
        return rule_id
    
    def check_conditions(self, data: Dict):
        """Check all rules against current data."""
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            triggered = self._evaluate_rule(rule, data)
            if triggered:
                self._create_alert(rule, data)
    
    def _evaluate_rule(self, rule: AlertRule, data: Dict) -> bool:
        """Evaluate a single rule."""
        if rule.alert_type == AlertType.PRICE:
            value = data.get('price', 0)
        elif rule.alert_type == AlertType.PNL:
            value = data.get('pnl', 0)
        elif rule.alert_type == AlertType.VOLUME:
            value = data.get('volume_ratio', 1)
        elif rule.alert_type == AlertType.GREEK:
            value = data.get(rule.condition.split('_')[0], 0)
        else:
            value = 0
        
        if rule.ticker and data.get('ticker') != rule.ticker:
            return False
        
        if rule.condition == 'above':
            return value > rule.threshold
        elif rule.condition == 'below':
            return value < rule.threshold
        elif rule.condition == 'change_pct':
            return abs(data.get('change_pct', 0)) > rule.threshold
        
        return False
    
    def _create_alert(self, rule: AlertRule, data: Dict):
        """Create alert from triggered rule."""
        self.alert_counter += 1
        
        alert = Alert(
            alert_id=f"ALT_{self.alert_counter:05d}",
            timestamp=datetime.now(),
            alert_type=rule.alert_type,
            priority=rule.priority,
            ticker=data.get('ticker', 'UNKNOWN'),
            message=f"{rule.name}: {rule.condition} {rule.threshold}",
            value=data.get('price', 0),
            threshold=rule.threshold
        )
        
        self.alerts.append(alert)
        
        # Trigger callbacks
        for callback in self.callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert."""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                break
    
    def get_active_alerts(self, priority_min: AlertPriority = None) -> List[Alert]:
        """Get unacknowledged alerts."""
        active = [a for a in self.alerts if not a.acknowledged]
        
        if priority_min:
            active = [a for a in active if a.priority.value >= priority_min.value]
        
        return sorted(active, key=lambda x: x.priority.value, reverse=True)
    
    def register_callback(self, callback: Callable):
        """Register alert callback."""
        self.callbacks.append(callback)


# ============================================================
# WEBHOOK INTEGRATION
# ============================================================

class WebhookIntegration:
    """
    Webhook integration for external notifications.
    """
    
    def __init__(self):
        self.webhooks: Dict[str, Dict] = {}
        self.send_queue: queue.Queue = queue.Queue()
        self.enabled = True
    
    def add_webhook(self, name: str, url: str,
                    events: List[str] = None,
                    headers: Dict = None) -> str:
        """Register webhook endpoint."""
        webhook_id = f"WH_{len(self.webhooks):03d}"
        
        self.webhooks[webhook_id] = {
            'name': name,
            'url': url,
            'events': events or ['all'],
            'headers': headers or {'Content-Type': 'application/json'},
            'enabled': True
        }
        
        return webhook_id
    
    def send(self, event: str, data: Dict):
        """Queue webhook payload."""
        if not self.enabled:
            return
        
        payload = {
            'event': event,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        for wh_id, webhook in self.webhooks.items():
            if not webhook['enabled']:
                continue
            
            if 'all' in webhook['events'] or event in webhook['events']:
                self.send_queue.put({
                    'webhook_id': wh_id,
                    'url': webhook['url'],
                    'headers': webhook['headers'],
                    'payload': payload
                })
    
    def _send_webhook(self, url: str, headers: Dict, payload: Dict) -> bool:
        """Actually send webhook (mock for now)."""
        try:
            # In production, would use requests.post
            logger.info(f"Webhook sent to {url}: {json.dumps(payload)[:100]}...")
            return True
        except Exception as e:
            logger.error(f"Webhook failed: {e}")
            return False
    
    def process_queue(self):
        """Process pending webhooks."""
        sent = 0
        while not self.send_queue.empty():
            try:
                item = self.send_queue.get_nowait()
                self._send_webhook(item['url'], item['headers'], item['payload'])
                sent += 1
            except queue.Empty:
                break
        return sent
    
    def format_tradingview_alert(self, alert: Alert) -> Dict:
        """Format alert for TradingView webhook."""
        return {
            'symbol': alert.ticker,
            'action': 'alert',
            'message': alert.message,
            'price': alert.value,
            'timestamp': alert.timestamp.isoformat()
        }
    
    def format_discord_message(self, alert: Alert) -> Dict:
        """Format alert for Discord webhook."""
        emoji = {'CRITICAL': '🚨', 'HIGH': '⚠️', 'MEDIUM': '📊', 'LOW': 'ℹ️'}
        
        return {
            'content': f"{emoji.get(alert.priority.name, '📊')} **{alert.ticker}** - {alert.message}",
            'embeds': [{
                'title': f'Trading Alert - {alert.priority.name}',
                'fields': [
                    {'name': 'Ticker', 'value': alert.ticker, 'inline': True},
                    {'name': 'Value', 'value': str(alert.value), 'inline': True},
                    {'name': 'Threshold', 'value': str(alert.threshold), 'inline': True}
                ],
                'timestamp': alert.timestamp.isoformat()
            }]
        }


# ============================================================
# MARKET SCANNER
# ============================================================

class MarketScanner:
    """
    Real-time market opportunity scanner.
    """
    
    def __init__(self):
        self.scan_patterns = [
            'high_iv_rank',
            'unusual_volume',
            'earnings_play',
            'momentum_breakout',
            'mean_reversion',
            'dividend_capture'
        ]
        self.watchlist: List[str] = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMD', 'GOOGL']
    
    def scan(self, pattern: str = None) -> List[ScanResult]:
        """Run market scan."""
        results = []
        patterns = [pattern] if pattern else self.scan_patterns[:3]
        
        for ticker in self.watchlist:
            for pat in patterns:
                score = self._calculate_signal(ticker, pat)
                
                if score > 0.6:  # Threshold for inclusion
                    results.append(ScanResult(
                        ticker=ticker,
                        pattern=pat,
                        signal_strength=round(score, 3),
                        current_price=round(100 + np.random.uniform(-20, 50), 2),
                        change_pct=round(np.random.uniform(-5, 5), 2),
                        volume_ratio=round(1 + np.random.exponential(0.5), 2),
                        iv_percentile=round(np.random.uniform(0, 100), 1),
                        recommendation=self._get_recommendation(pat, score)
                    ))
        
        return sorted(results, key=lambda x: x.signal_strength, reverse=True)
    
    def _calculate_signal(self, ticker: str, pattern: str) -> float:
        """Calculate signal strength for pattern."""
        # Simulated signal calculation
        base_score = np.random.uniform(0.3, 0.9)
        
        # Add some realism - certain patterns better for certain tickers
        pattern_affinity = {
            'high_iv_rank': ['TSLA', 'NVDA', 'AMD'],
            'momentum_breakout': ['QQQ', 'SPY', 'NVDA'],
            'mean_reversion': ['SPY', 'AAPL', 'MSFT']
        }
        
        if ticker in pattern_affinity.get(pattern, []):
            base_score *= 1.2
        
        return min(base_score, 1.0)
    
    def _get_recommendation(self, pattern: str, score: float) -> str:
        """Generate strategy recommendation."""
        recommendations = {
            'high_iv_rank': 'Sell premium - Iron Condor or Credit Spread',
            'unusual_volume': 'Investigate for directional play',
            'earnings_play': 'Consider straddle or iron butterfly',
            'momentum_breakout': 'Debit spread in trend direction',
            'mean_reversion': 'Short-term reversal play',
            'dividend_capture': 'Covered call or cash-secured put'
        }
        
        rec = recommendations.get(pattern, 'Monitor for entry')
        
        if score > 0.8:
            return f"STRONG: {rec}"
        elif score > 0.7:
            return rec
        else:
            return f"Wait for confirmation: {rec}"
    
    def add_to_watchlist(self, ticker: str):
        """Add ticker to watchlist."""
        if ticker not in self.watchlist:
            self.watchlist.append(ticker)
    
    def remove_from_watchlist(self, ticker: str):
        """Remove ticker from watchlist."""
        if ticker in self.watchlist:
            self.watchlist.remove(ticker)


# ============================================================
# NEWS IMPACT ANALYZER
# ============================================================

class NewsImpactAnalyzer:
    """
    Analyze news impact on options strategies.
    """
    
    def __init__(self):
        self.news_cache: List[NewsItem] = []
        self.sentiment_keywords = {
            'positive': ['surge', 'beats', 'record', 'breakthrough', 'upgrade', 'growth'],
            'negative': ['plunge', 'miss', 'lawsuit', 'downgrade', 'decline', 'warning']
        }
    
    def analyze_headline(self, headline: str, tickers: List[str]) -> NewsItem:
        """Analyze news headline impact."""
        headline_lower = headline.lower()
        
        # Calculate sentiment
        positive_count = sum(1 for w in self.sentiment_keywords['positive'] if w in headline_lower)
        negative_count = sum(1 for w in self.sentiment_keywords['negative'] if w in headline_lower)
        
        if positive_count > negative_count:
            sentiment = 0.5 + (positive_count * 0.2)
        elif negative_count > positive_count:
            sentiment = -0.5 - (negative_count * 0.2)
        else:
            sentiment = 0
        
        sentiment = max(min(sentiment, 1), -1)
        
        # Calculate impact score
        impact = abs(sentiment) * 50
        
        # Category detection
        if any(w in headline_lower for w in ['earnings', 'revenue', 'profit']):
            category = 'earnings'
            impact *= 1.5
        elif any(w in headline_lower for w in ['fda', 'trial', 'drug']):
            category = 'regulatory'
            impact *= 2
        elif any(w in headline_lower for w in ['merger', 'acquisition', 'deal']):
            category = 'ma'
            impact *= 1.8
        else:
            category = 'general'
        
        impact = min(impact, 100)
        
        news_item = NewsItem(
            headline=headline,
            timestamp=datetime.now(),
            source='analyzed',
            tickers=tickers,
            sentiment=round(sentiment, 3),
            impact_score=round(impact, 1),
            category=category
        )
        
        self.news_cache.append(news_item)
        return news_item
    
    def get_strategy_impact(self, news_item: NewsItem) -> Dict:
        """Get impact on different strategies."""
        sentiment = news_item.sentiment
        impact = news_item.impact_score
        
        # High impact = high IV expected
        expected_iv_change = impact * 0.3
        
        strategies = {}
        
        if impact > 60:
            # High impact - avoid premium selling
            strategies['iron_condor'] = {
                'recommendation': 'AVOID',
                'reason': 'High impact event - IV crush risk after news settles'
            }
            strategies['straddle'] = {
                'recommendation': 'CONSIDER' if impact > 80 else 'WAIT',
                'reason': 'Potential large move expected'
            }
        else:
            strategies['iron_condor'] = {
                'recommendation': 'PROCEED',
                'reason': 'Low impact - favorable for premium collection'
            }
        
        if sentiment > 0.5:
            strategies['bull_call_spread'] = {
                'recommendation': 'FAVORABLE',
                'reason': 'Positive sentiment supports bullish bias'
            }
        elif sentiment < -0.5:
            strategies['bear_put_spread'] = {
                'recommendation': 'FAVORABLE',
                'reason': 'Negative sentiment supports bearish bias'
            }
        
        return {
            'news': news_item.headline,
            'sentiment': news_item.sentiment,
            'impact': news_item.impact_score,
            'expected_iv_change': f"+{expected_iv_change:.1f}%" if expected_iv_change > 0 else f"{expected_iv_change:.1f}%",
            'strategy_recommendations': strategies
        }
    
    def get_recent_news(self, ticker: str = None, hours: int = 24) -> List[NewsItem]:
        """Get recent news items."""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        recent = [n for n in self.news_cache if n.timestamp > cutoff]
        
        if ticker:
            recent = [n for n in recent if ticker in n.tickers]
        
        return sorted(recent, key=lambda x: x.timestamp, reverse=True)


# ============================================================
# UNIFIED REALTIME ENGINE
# ============================================================

class RealtimeIntelligenceEngine:
    """Unified real-time intelligence engine."""
    
    def __init__(self):
        self.pnl_tracker = LivePnLTracker()
        self.alert_engine = AlertEngine()
        self.webhooks = WebhookIntegration()
        self.scanner = MarketScanner()
        self.news_analyzer = NewsImpactAnalyzer()
        
        # Connect alert engine to webhooks
        self.alert_engine.register_callback(self._on_alert)
    
    def _on_alert(self, alert: Alert):
        """Handle alert and send to webhooks."""
        self.webhooks.send('alert', {
            'alert_id': alert.alert_id,
            'ticker': alert.ticker,
            'message': alert.message,
            'priority': alert.priority.name
        })
    
    def setup_default_alerts(self):
        """Setup default alert rules."""
        # P&L alerts
        self.alert_engine.add_rule(
            'Large Loss',
            AlertType.PNL,
            'below',
            -500,
            priority=AlertPriority.HIGH
        )
        
        self.alert_engine.add_rule(
            'Profit Target',
            AlertType.PNL,
            'above',
            1000,
            priority=AlertPriority.MEDIUM
        )
        
        # Volume alert
        self.alert_engine.add_rule(
            'Unusual Volume',
            AlertType.VOLUME,
            'above',
            3.0,
            priority=AlertPriority.HIGH
        )
    
    def get_dashboard_data(self) -> Dict:
        """Get data for real-time dashboard."""
        return {
            'pnl': self.pnl_tracker.get_portfolio_pnl(),
            'positions': self.pnl_tracker.get_position_details(),
            'active_alerts': [
                {
                    'id': a.alert_id,
                    'ticker': a.ticker,
                    'message': a.message,
                    'priority': a.priority.name
                }
                for a in self.alert_engine.get_active_alerts()[:5]
            ],
            'scan_results': [
                {
                    'ticker': s.ticker,
                    'pattern': s.pattern,
                    'signal': s.signal_strength,
                    'recommendation': s.recommendation
                }
                for s in self.scanner.scan()[:5]
            ],
            'recent_news': [
                {
                    'headline': n.headline[:50] + '...',
                    'sentiment': n.sentiment,
                    'impact': n.impact_score
                }
                for n in self.news_analyzer.get_recent_news()[:3]
            ],
            'timestamp': datetime.now().isoformat()
        }


# ============================================================
# SINGLETON GETTER
# ============================================================

_realtime_engine = None

def get_realtime_engine() -> RealtimeIntelligenceEngine:
    """Get singleton instance."""
    global _realtime_engine
    if _realtime_engine is None:
        _realtime_engine = RealtimeIntelligenceEngine()
        _realtime_engine.setup_default_alerts()
    return _realtime_engine

"""
Autonomous Monitoring System
============================
Continuous autonomous monitoring that requires zero user input:
- Auto-alert generation
- Position health monitoring
- Roll timing optimization
- Earnings calendar integration
- Volatility regime tracking
- Real-time risk assessment

Author: AI/ML Options Lab
"""

import os
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


# ============================================================
# ENUMS & DATA CLASSES
# ============================================================

class AlertPriority(Enum):
    """Alert priority levels."""
    INFO = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5


class AlertCategory(Enum):
    """Categories of auto-generated alerts."""
    PRICE = "price"
    VOLATILITY = "volatility"
    POSITION = "position"
    EARNINGS = "earnings"
    RISK = "risk"
    OPPORTUNITY = "opportunity"
    SYSTEM = "system"


class MonitorStatus(Enum):
    """Monitor status."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class AutoAlert:
    """Auto-generated alert."""
    alert_id: str
    category: AlertCategory
    priority: AlertPriority
    ticker: str
    title: str
    message: str
    action_required: str
    timestamp: datetime
    expires_at: datetime
    metadata: Dict = field(default_factory=dict)
    is_acknowledged: bool = False


@dataclass
class VolatilityRegime:
    """Current volatility regime."""
    regime: str  # 'low', 'normal', 'elevated', 'high', 'extreme'
    vix_level: float
    vix_percentile: float
    regime_change: bool
    previous_regime: str
    regime_duration_days: int
    forecast: str
    trading_implications: List[str]
    timestamp: datetime


@dataclass
class EarningsEvent:
    """Upcoming earnings event."""
    ticker: str
    earnings_date: str
    days_until: int
    time_of_day: str  # 'before_open', 'after_close'
    expected_move: float
    historical_moves: List[float]
    has_position: bool
    action_needed: str


@dataclass
class RollOpportunity:
    """Roll opportunity for a position."""
    ticker: str
    current_expiry: str
    current_dte: int
    recommended_expiry: str
    recommended_dte: int
    
    current_value: float
    roll_credit_debit: float
    new_theta: float
    
    urgency: str
    rationale: str


@dataclass
class PositionHealthCheck:
    """Position health check result."""
    ticker: str
    position_type: str
    health_score: float  # 0-100
    
    # Components
    pnl_status: str
    theta_status: str
    delta_status: str
    time_status: str
    
    # Issues found
    issues: List[str]
    recommendations: List[str]
    
    timestamp: datetime


# ============================================================
# AUTO-ALERT GENERATOR
# ============================================================

class AutoAlertGenerator:
    """
    Generates alerts automatically without user input.
    Monitors multiple conditions and creates actionable alerts.
    """
    
    def __init__(self):
        self._alert_counter = 0
        self._recent_alerts: List[AutoAlert] = []
        self._alert_rules: List[Dict] = []
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default alert rules."""
        self._alert_rules = [
            {
                'name': 'price_move_5pct',
                'condition': lambda data: abs(data.get('price_change_pct', 0)) > 5,
                'priority': AlertPriority.HIGH,
                'category': AlertCategory.PRICE,
                'message_template': "{ticker} moved {change:.1f}% - Review positions"
            },
            {
                'name': 'iv_spike',
                'condition': lambda data: data.get('iv_change_pct', 0) > 20,
                'priority': AlertPriority.MEDIUM,
                'category': AlertCategory.VOLATILITY,
                'message_template': "{ticker} IV spiked {iv_change:.1f}% - Consider adjustments"
            },
            {
                'name': 'earnings_warning',
                'condition': lambda data: 0 < data.get('days_to_earnings', 999) <= 5,
                'priority': AlertPriority.HIGH,
                'category': AlertCategory.EARNINGS,
                'message_template': "{ticker} earnings in {days} days - Check exposure"
            },
            {
                'name': 'stop_loss_near',
                'condition': lambda data: data.get('pct_to_stop', 100) < 5,
                'priority': AlertPriority.CRITICAL,
                'category': AlertCategory.RISK,
                'message_template': "{ticker} approaching stop loss - Action needed"
            },
            {
                'name': 'profit_target',
                'condition': lambda data: data.get('pct_of_max_profit', 0) > 75,
                'priority': AlertPriority.MEDIUM,
                'category': AlertCategory.POSITION,
                'message_template': "{ticker} reached {pct:.0f}% of max profit - Consider closing"
            },
            {
                'name': 'expiration_warning',
                'condition': lambda data: 0 < data.get('dte', 999) <= 7,
                'priority': AlertPriority.HIGH,
                'category': AlertCategory.POSITION,
                'message_template': "{ticker} expires in {dte} days - Decide on exit or roll"
            }
        ]
    
    def check_and_generate_alerts(self, market_data: Dict, 
                                   positions: List[Dict]) -> List[AutoAlert]:
        """Check all rules and generate relevant alerts."""
        new_alerts = []
        
        # Check market-wide conditions
        market_alerts = self._check_market_conditions(market_data)
        new_alerts.extend(market_alerts)
        
        # Check position-specific conditions
        for position in positions:
            pos_alerts = self._check_position_conditions(position)
            new_alerts.extend(pos_alerts)
        
        # Deduplicate and store
        new_alerts = self._deduplicate_alerts(new_alerts)
        self._recent_alerts.extend(new_alerts)
        
        # Keep only last 100 alerts
        self._recent_alerts = self._recent_alerts[-100:]
        
        return new_alerts
    
    def _check_market_conditions(self, data: Dict) -> List[AutoAlert]:
        """Check market-wide conditions."""
        alerts = []
        
        # VIX spike check
        vix = data.get('vix', 20)
        if vix > 30:
            alerts.append(self._create_alert(
                category=AlertCategory.VOLATILITY,
                priority=AlertPriority.HIGH,
                ticker='VIX',
                title='Elevated Volatility Warning',
                message=f'VIX at {vix:.1f} - Market stress elevated',
                action='Review portfolio risk exposure'
            ))
        
        # Market drop check
        spy_change = data.get('spy_change_pct', 0)
        if spy_change < -2:
            alerts.append(self._create_alert(
                category=AlertCategory.PRICE,
                priority=AlertPriority.HIGH,
                ticker='SPY',
                title='Significant Market Decline',
                message=f'S&P 500 down {abs(spy_change):.1f}% today',
                action='Check downside protection'
            ))
        
        return alerts
    
    def _check_position_conditions(self, position: Dict) -> List[AutoAlert]:
        """Check position-specific conditions."""
        alerts = []
        ticker = position.get('ticker', 'UNKNOWN')
        
        for rule in self._alert_rules:
            try:
                if rule['condition'](position):
                    message = rule['message_template'].format(
                        ticker=ticker,
                        **position
                    )
                    alerts.append(self._create_alert(
                        category=rule['category'],
                        priority=rule['priority'],
                        ticker=ticker,
                        title=rule['name'].replace('_', ' ').title(),
                        message=message,
                        action=f"Review {ticker} position"
                    ))
            except Exception as e:
                logger.debug(f"Rule {rule['name']} check failed: {e}")
        
        return alerts
    
    def _create_alert(self, category: AlertCategory, priority: AlertPriority,
                      ticker: str, title: str, message: str, 
                      action: str) -> AutoAlert:
        """Create a new alert."""
        self._alert_counter += 1
        
        # Set expiration based on priority
        expire_hours = {
            AlertPriority.CRITICAL: 2,
            AlertPriority.HIGH: 8,
            AlertPriority.MEDIUM: 24,
            AlertPriority.LOW: 48,
            AlertPriority.INFO: 72
        }
        
        return AutoAlert(
            alert_id=f"alert_{self._alert_counter}_{int(time.time())}",
            category=category,
            priority=priority,
            ticker=ticker,
            title=title,
            message=message,
            action_required=action,
            timestamp=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=expire_hours[priority])
        )
    
    def _deduplicate_alerts(self, alerts: List[AutoAlert]) -> List[AutoAlert]:
        """Remove duplicate alerts."""
        seen = set()
        unique = []
        
        for alert in alerts:
            key = (alert.ticker, alert.category, alert.title)
            if key not in seen:
                seen.add(key)
                unique.append(alert)
        
        return unique
    
    def get_active_alerts(self) -> List[AutoAlert]:
        """Get all non-expired, unacknowledged alerts."""
        now = datetime.now()
        return [
            a for a in self._recent_alerts 
            if a.expires_at > now and not a.is_acknowledged
        ]
    
    def acknowledge_alert(self, alert_id: str):
        """Mark an alert as acknowledged."""
        for alert in self._recent_alerts:
            if alert.alert_id == alert_id:
                alert.is_acknowledged = True
                break


# ============================================================
# VOLATILITY REGIME TRACKER
# ============================================================

class VolatilityRegimeTracker:
    """
    Tracks and classifies the current volatility regime.
    Provides trading implications for each regime.
    """
    
    def __init__(self):
        self._regime_history: List[VolatilityRegime] = []
        self._current_regime: Optional[VolatilityRegime] = None
        
        # Regime thresholds (based on VIX)
        self.thresholds = {
            'low': (0, 12),
            'normal': (12, 20),
            'elevated': (20, 25),
            'high': (25, 35),
            'extreme': (35, 100)
        }
        
        # Trading implications for each regime
        self.implications = {
            'low': [
                "Buying options is cheap - favor long strategies",
                "Iron condors have tight ranges - wider may work better",
                "Consider buying straddles for volatility expansion plays"
            ],
            'normal': [
                "Standard premium selling strategies work well",
                "Balance between buying and selling premium",
                "Focus on high-probability trades"
            ],
            'elevated': [
                "Premium selling becomes more attractive",
                "Consider wider strike spreads",
                "Watch for mean reversion in volatility"
            ],
            'high': [
                "Excellent for premium selling - high credits",
                "Use defined risk strategies",
                "Avoid naked short options",
                "Expect increased whipsaw"
            ],
            'extreme': [
                "Maximum caution - reduce position sizes",
                "Cash is a position",
                "If selling premium, use very wide wings",
                "Crisis alpha strategies may work"
            ]
        }
    
    def update_regime(self, vix: float) -> VolatilityRegime:
        """Update and return current regime."""
        # Determine regime
        regime = 'normal'
        for name, (low, high) in self.thresholds.items():
            if low <= vix < high:
                regime = name
                break
        
        # Calculate percentile (simplified)
        # In production, use actual VIX historical distribution
        vix_percentile = min(99, (vix / 80) * 100)
        
        # Check for regime change
        previous = self._current_regime.regime if self._current_regime else 'normal'
        regime_change = regime != previous
        
        # Calculate duration
        if regime_change or not self._regime_history:
            duration = 0
        else:
            last_change = next(
                (r for r in reversed(self._regime_history) if r.regime_change),
                self._regime_history[0] if self._regime_history else None
            )
            duration = (datetime.now() - last_change.timestamp).days if last_change else 0
        
        # Forecast
        if regime in ['high', 'extreme']:
            forecast = 'Volatility likely to mean-revert lower'
        elif regime == 'low':
            forecast = 'Volatility may expand from current lows'
        else:
            forecast = 'Volatility stable in normal range'
        
        new_regime = VolatilityRegime(
            regime=regime,
            vix_level=vix,
            vix_percentile=round(vix_percentile, 1),
            regime_change=regime_change,
            previous_regime=previous,
            regime_duration_days=duration,
            forecast=forecast,
            trading_implications=self.implications[regime],
            timestamp=datetime.now()
        )
        
        self._current_regime = new_regime
        self._regime_history.append(new_regime)
        
        # Keep last 100 readings
        self._regime_history = self._regime_history[-100:]
        
        return new_regime
    
    def get_current_regime(self) -> Optional[VolatilityRegime]:
        """Get current regime."""
        return self._current_regime
    
    def get_regime_history(self, days: int = 30) -> List[VolatilityRegime]:
        """Get regime history."""
        cutoff = datetime.now() - timedelta(days=days)
        return [r for r in self._regime_history if r.timestamp > cutoff]


# ============================================================
# EARNINGS CALENDAR MONITOR
# ============================================================

class EarningsCalendarMonitor:
    """
    Monitors earnings calendar and generates alerts.
    Auto-adjusts positions for earnings events.
    """
    
    def __init__(self):
        # Simulated earnings calendar
        self._earnings_calendar: Dict[str, Dict] = {}
        self._populate_calendar()
    
    def _populate_calendar(self):
        """Populate earnings calendar with sample data."""
        # In production, fetch from API
        major_stocks = [
            ('AAPL', 5), ('NVDA', 12), ('TSLA', 8), ('AMZN', 15),
            ('GOOGL', 10), ('META', 7), ('MSFT', 3), ('AMD', 20)
        ]
        
        base_date = datetime.now()
        for ticker, days_offset in major_stocks:
            self._earnings_calendar[ticker] = {
                'date': (base_date + timedelta(days=days_offset)).strftime('%Y-%m-%d'),
                'time': 'after_close' if hash(ticker) % 2 else 'before_open',
                'expected_move': 5 + hash(ticker) % 10,
                'historical_moves': [float(3 + (hash(ticker + str(i)) % 15)) for i in range(8)]
            }
    
    def check_upcoming_earnings(self, watchlist: List[str], 
                                positions: List[Dict],
                                days_ahead: int = 14) -> List[EarningsEvent]:
        """Check for upcoming earnings on watchlist/positions."""
        events = []
        
        all_tickers = set(watchlist)
        all_tickers.update(p.get('ticker') for p in positions)
        
        today = datetime.now()
        
        for ticker in all_tickers:
            if ticker in self._earnings_calendar:
                earnings = self._earnings_calendar[ticker]
                earnings_date = datetime.strptime(earnings['date'], '%Y-%m-%d')
                days_until = (earnings_date - today).days
                
                if 0 <= days_until <= days_ahead:
                    has_position = any(p.get('ticker') == ticker for p in positions)
                    
                    # Determine action
                    if has_position and days_until <= 3:
                        action = "URGENT: Close or hedge before earnings"
                    elif has_position and days_until <= 7:
                        action = "Consider closing position or adding protection"
                    elif not has_position and days_until <= 5:
                        action = "Opportunity: Consider earnings play"
                    else:
                        action = "Monitor - earnings approaching"
                    
                    events.append(EarningsEvent(
                        ticker=ticker,
                        earnings_date=earnings['date'],
                        days_until=days_until,
                        time_of_day=earnings['time'],
                        expected_move=earnings['expected_move'],
                        historical_moves=earnings['historical_moves'],
                        has_position=has_position,
                        action_needed=action
                    ))
        
        # Sort by days until earnings
        events.sort(key=lambda e: e.days_until)
        return events


# ============================================================
# ROLL TIMING OPTIMIZER
# ============================================================

class RollTimingOptimizer:
    """
    Optimizes timing for rolling options positions.
    Determines best time to roll based on theta, IV, and time.
    """
    
    def __init__(self):
        self.min_dte_threshold = 14  # Start considering roll at 14 DTE
        self.optimal_roll_dte = 21   # Optimal new expiry is 21-45 DTE
    
    def analyze_roll_opportunities(self, positions: List[Dict]) -> List[RollOpportunity]:
        """Analyze positions for roll opportunities."""
        opportunities = []
        
        for pos in positions:
            opp = self._analyze_position(pos)
            if opp:
                opportunities.append(opp)
        
        # Sort by urgency
        urgency_order = {'immediate': 0, 'soon': 1, 'consider': 2}
        opportunities.sort(key=lambda x: urgency_order.get(x.urgency, 3))
        
        return opportunities
    
    def _analyze_position(self, position: Dict) -> Optional[RollOpportunity]:
        """Analyze single position for roll opportunity."""
        dte = position.get('dte', 999)
        ticker = position.get('ticker', 'UNKNOWN')
        
        if dte > self.min_dte_threshold:
            return None
        
        # Determine urgency
        if dte <= 5:
            urgency = 'immediate'
            rationale = f"Only {dte} DTE remaining - roll urgently to avoid gamma risk"
        elif dte <= 10:
            urgency = 'soon'
            rationale = f"Position at {dte} DTE - optimal roll window opening"
        else:
            urgency = 'consider'
            rationale = f"Position approaching roll zone at {dte} DTE"
        
        # Calculate recommended expiry (45 DTE is common target)
        current_expiry = position.get('expiration', 
                                      (datetime.now() + timedelta(days=dte)).strftime('%Y-%m-%d'))
        new_dte = 45
        recommended_expiry = (datetime.now() + timedelta(days=new_dte)).strftime('%Y-%m-%d')
        
        # Estimate roll credit/debit (simplified)
        current_value = position.get('current_value', 100)
        new_theta = current_value * 0.02  # Rough estimate
        roll_credit = current_value * 0.3 if dte < 10 else current_value * 0.5
        
        return RollOpportunity(
            ticker=ticker,
            current_expiry=current_expiry,
            current_dte=dte,
            recommended_expiry=recommended_expiry,
            recommended_dte=new_dte,
            current_value=round(current_value, 2),
            roll_credit_debit=round(roll_credit, 2),
            new_theta=round(new_theta, 2),
            urgency=urgency,
            rationale=rationale
        )


# ============================================================
# POSITION HEALTH MONITOR
# ============================================================

class PositionHealthMonitor:
    """
    Continuously monitors position health.
    Scores each position and identifies issues.
    """
    
    def check_all_positions(self, positions: List[Dict]) -> List[PositionHealthCheck]:
        """Check health of all positions."""
        return [self._check_position(pos) for pos in positions]
    
    def _check_position(self, position: Dict) -> PositionHealthCheck:
        """Check health of a single position."""
        ticker = position.get('ticker', 'UNKNOWN')
        pos_type = position.get('strategy', 'unknown')
        
        issues = []
        recommendations = []
        
        # PNL Status
        pnl_pct = position.get('pnl_pct', 0)
        if pnl_pct < -50:
            pnl_status = 'critical'
            issues.append(f"Position down {abs(pnl_pct):.0f}%")
        elif pnl_pct < -25:
            pnl_status = 'poor'
            issues.append(f"Significant unrealized loss")
        elif pnl_pct > 50:
            pnl_status = 'excellent'
            recommendations.append("Consider taking profits")
        elif pnl_pct > 25:
            pnl_status = 'good'
        else:
            pnl_status = 'normal'
        
        # Theta Status
        theta = position.get('theta', 0)
        if theta < -5:
            theta_status = 'poor'
            issues.append("High negative theta decay")
        elif theta > 0:
            theta_status = 'good'
        else:
            theta_status = 'normal'
        
        # Delta Status
        delta = position.get('delta', 0)
        if abs(delta) > 0.7:
            delta_status = 'high_risk'
            issues.append(f"High delta exposure ({delta:.2f})")
            recommendations.append("Consider delta hedging")
        else:
            delta_status = 'normal'
        
        # Time Status
        dte = position.get('dte', 999)
        if dte <= 5:
            time_status = 'critical'
            issues.append("Expiration imminent")
            recommendations.append("Roll or close immediately")
        elif dte <= 14:
            time_status = 'warning'
            recommendations.append("Plan exit strategy")
        else:
            time_status = 'normal'
        
        # Calculate overall health score
        score = 100
        
        # PNL impact
        if pnl_pct < -50:
            score -= 40
        elif pnl_pct < -25:
            score -= 20
        elif pnl_pct > 50:
            score += 10
        
        # Time impact
        if dte <= 5:
            score -= 30
        elif dte <= 14:
            score -= 10
        
        # Delta impact
        if abs(delta) > 0.7:
            score -= 15
        
        score = max(0, min(100, score))
        
        return PositionHealthCheck(
            ticker=ticker,
            position_type=pos_type,
            health_score=score,
            pnl_status=pnl_status,
            theta_status=theta_status,
            delta_status=delta_status,
            time_status=time_status,
            issues=issues,
            recommendations=recommendations,
            timestamp=datetime.now()
        )


# ============================================================
# UNIFIED AUTONOMOUS MONITOR
# ============================================================

class AutonomousMonitor:
    """
    Main autonomous monitoring system.
    Runs continuously in background and generates alerts.
    """
    
    def __init__(self):
        self.alert_generator = AutoAlertGenerator()
        self.vol_tracker = VolatilityRegimeTracker()
        self.earnings_monitor = EarningsCalendarMonitor()
        self.roll_optimizer = RollTimingOptimizer()
        self.health_monitor = PositionHealthMonitor()
        
        self._status = MonitorStatus.IDLE
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Monitoring state
        self._last_scan = None
        self._scan_interval = 60  # seconds
        
        # Callbacks for notifications
        self._alert_callbacks: List[Callable] = []
    
    def start(self):
        """Start autonomous monitoring."""
        if self._status == MonitorStatus.RUNNING:
            return
        
        self._status = MonitorStatus.RUNNING
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Autonomous monitor started")
    
    def stop(self):
        """Stop autonomous monitoring."""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self._status = MonitorStatus.IDLE
        logger.info("Autonomous monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while not self._stop_event.is_set():
            try:
                self._run_scan()
            except Exception as e:
                logger.error(f"Monitor scan error: {e}")
                self._status = MonitorStatus.ERROR
            
            self._stop_event.wait(self._scan_interval)
    
    def _run_scan(self):
        """Run a monitoring scan."""
        self._last_scan = datetime.now()
        
        # Get current market data
        market_data = self._get_market_data()
        
        # Get current positions (placeholder - integrate with real portfolio)
        positions = self._get_positions()
        
        # Run all monitors
        # 1. Update volatility regime
        vix = market_data.get('vix', 20)
        regime = self.vol_tracker.update_regime(vix)
        
        # 2. Check earnings - includes precious metals and major tech
        earnings = self.earnings_monitor.check_upcoming_earnings(
            watchlist=['GLD', 'SLV', 'SPY', 'QQQ', 'AAPL', 'NVDA', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'AMD'],
            positions=positions
        )
        
        # 3. Check roll opportunities
        rolls = self.roll_optimizer.analyze_roll_opportunities(positions)
        
        # 4. Position health
        health = self.health_monitor.check_all_positions(positions)
        
        # 5. Generate alerts
        alerts = self.alert_generator.check_and_generate_alerts(
            market_data, positions
        )
        
        # Add regime change alert
        if regime.regime_change:
            alerts.append(self.alert_generator._create_alert(
                category=AlertCategory.VOLATILITY,
                priority=AlertPriority.MEDIUM,
                ticker='VIX',
                title='Volatility Regime Change',
                message=f'Regime changed from {regime.previous_regime} to {regime.regime}',
                action='Adjust strategy for new regime'
            ))
        
        # Add earnings alerts
        for e in earnings:
            if e.days_until <= 3 and e.has_position:
                alerts.append(self.alert_generator._create_alert(
                    category=AlertCategory.EARNINGS,
                    priority=AlertPriority.CRITICAL,
                    ticker=e.ticker,
                    title='Earnings Alert',
                    message=f'{e.ticker} earnings in {e.days_until} days',
                    action=e.action_needed
                ))
        
        # Add roll alerts
        for r in rolls:
            if r.urgency == 'immediate':
                alerts.append(self.alert_generator._create_alert(
                    category=AlertCategory.POSITION,
                    priority=AlertPriority.HIGH,
                    ticker=r.ticker,
                    title='Roll Required',
                    message=r.rationale,
                    action=f'Roll to {r.recommended_expiry}'
                ))
        
        # Notify callbacks
        if alerts:
            self._notify_alerts(alerts)
    
    def _get_market_data(self) -> Dict:
        """Get current market data."""
        try:
            from .alpaca_data_loader import get_alpaca_client
            client = get_alpaca_client()
            
            spy_price = client.get_stock_quote('SPY') or 500
            
            # Get VIX proxy from SPY options IV
            return {
                'spy_price': spy_price,
                'spy_change_pct': 0.5,  # Placeholder
                'vix': 18.5,  # Placeholder - in production use real VIX
            }
        except:
            return {'spy_price': 500, 'spy_change_pct': 0, 'vix': 20}
    
    def _get_positions(self) -> List[Dict]:
        """Get current positions."""
        # Placeholder - in production, fetch from portfolio manager
        return [
            {'ticker': 'SPY', 'dte': 25, 'pnl_pct': 15, 'delta': 0.3, 'theta': 5},
            {'ticker': 'AAPL', 'dte': 10, 'pnl_pct': -5, 'delta': 0.5, 'theta': 3},
        ]
    
    def add_alert_callback(self, callback: Callable):
        """Add callback for alert notifications."""
        self._alert_callbacks.append(callback)
    
    def _notify_alerts(self, alerts: List[AutoAlert]):
        """Notify all registered callbacks."""
        for callback in self._alert_callbacks:
            try:
                callback(alerts)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    def get_status(self) -> Dict:
        """Get monitor status."""
        return {
            'status': self._status.value,
            'last_scan': self._last_scan.isoformat() if self._last_scan else None,
            'active_alerts': len(self.alert_generator.get_active_alerts()),
            'current_regime': self.vol_tracker.get_current_regime()
        }
    
    # Manual scan methods for on-demand analysis
    def scan_now(self) -> Dict:
        """Run scan immediately and return results."""
        market_data = self._get_market_data()
        positions = self._get_positions()
        
        return {
            'regime': self.vol_tracker.update_regime(market_data.get('vix', 20)),
            'alerts': self.alert_generator.check_and_generate_alerts(market_data, positions),
            'earnings': self.earnings_monitor.check_upcoming_earnings(
                ['SPY', 'QQQ', 'AAPL', 'NVDA'], positions
            ),
            'rolls': self.roll_optimizer.analyze_roll_opportunities(positions),
            'health': self.health_monitor.check_all_positions(positions),
            'timestamp': datetime.now().isoformat()
        }


# ============================================================
# SINGLETON
# ============================================================

_monitor = None

def get_autonomous_monitor() -> AutonomousMonitor:
    """Get singleton autonomous monitor."""
    global _monitor
    if _monitor is None:
        _monitor = AutonomousMonitor()
    return _monitor

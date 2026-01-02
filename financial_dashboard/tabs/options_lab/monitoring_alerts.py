"""
Alpaca Options Lab - Monitoring, Alerts & Additional Features
Implements Items 176-220 from the 220 NEW IDEAS roadmap
"""

import dash_bootstrap_components as dbc
from dash import html, dcc
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import hashlib


# ============================================================
# ITEM 176-185: Alert System
# ============================================================
class AlertType(Enum):
    PRICE = "price"
    IV = "iv"
    GREEKS = "greeks"
    VOLUME = "volume"
    EXPIRATION = "expiration"
    PNL = "pnl"
    CUSTOM = "custom"


class AlertPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Trading alert."""
    alert_id: str
    alert_type: AlertType
    symbol: str
    condition: str  # e.g., "iv_rank > 80"
    threshold: float
    current_value: float
    priority: AlertPriority
    message: str
    triggered: bool = False
    triggered_at: Optional[datetime] = None
    acknowledged: bool = False
    created_at: datetime = field(default_factory=datetime.now)


class AlertManager:
    """Manage trading alerts."""
    
    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
    
    def create_alert(
        self,
        alert_type: AlertType,
        symbol: str,
        condition: str,
        threshold: float,
        priority: AlertPriority = AlertPriority.MEDIUM,
        message: str = ""
    ) -> Alert:
        """Create a new alert."""
        alert_id = hashlib.md5(f"{symbol}_{condition}_{datetime.now()}".encode()).hexdigest()[:8]
        
        alert = Alert(
            alert_id=alert_id,
            alert_type=alert_type,
            symbol=symbol,
            condition=condition,
            threshold=threshold,
            current_value=0,
            priority=priority,
            message=message or f"{symbol}: {condition} @ {threshold}"
        )
        
        self.alerts[alert_id] = alert
        return alert
    
    def check_alerts(self, market_data: Dict) -> List[Alert]:
        """Check all alerts against current market data."""
        triggered = []
        
        for alert in self.alerts.values():
            if alert.triggered:
                continue
            
            current = market_data.get(alert.symbol, {})
            
            # Evaluate condition (simplified)
            if alert.alert_type == AlertType.PRICE:
                value = current.get('price', 0)
            elif alert.alert_type == AlertType.IV:
                value = current.get('iv', 0)
            else:
                value = 0
            
            alert.current_value = value
            
            # Check threshold
            if 'above' in alert.condition and value > alert.threshold:
                alert.triggered = True
                alert.triggered_at = datetime.now()
                triggered.append(alert)
            elif 'below' in alert.condition and value < alert.threshold:
                alert.triggered = True
                alert.triggered_at = datetime.now()
                triggered.append(alert)
        
        return triggered
    
    def acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert."""
        if alert_id in self.alerts:
            self.alerts[alert_id].acknowledged = True
            self.alert_history.append(self.alerts[alert_id])
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active (triggered, unacknowledged) alerts."""
        return [a for a in self.alerts.values() if a.triggered and not a.acknowledged]


def create_alert_card(alert: Alert) -> dbc.Card:
    """Create alert display card."""
    priority_colors = {
        AlertPriority.LOW: 'info',
        AlertPriority.MEDIUM: 'warning',
        AlertPriority.HIGH: 'danger',
        AlertPriority.CRITICAL: 'danger'
    }
    
    color = priority_colors.get(alert.priority, 'secondary')
    
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.I(className=f"fas fa-bell me-2 text-{color}"),
                    html.Strong(alert.symbol),
                    html.Br(),
                    html.Small(alert.message, className="text-muted")
                ], width=8),
                dbc.Col([
                    dbc.Badge(alert.priority.value.upper(), color=color),
                    html.Br(),
                    html.Small(
                        alert.triggered_at.strftime("%H:%M") if alert.triggered_at else "",
                        className="text-muted"
                    )
                ], width=4, className="text-end")
            ])
        ])
    ], color=color, outline=True, className="mb-2")


def create_alerts_panel(alerts: List[Alert]) -> html.Div:
    """Create alerts management panel."""
    return html.Div([
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-bell me-2"),
                "Active Alerts",
                dbc.Badge(str(len(alerts)), color="danger", className="ms-2")
            ]),
            dbc.CardBody([
                html.Div([create_alert_card(a) for a in alerts]) if alerts else
                html.P("No active alerts", className="text-muted text-center")
            ])
        ])
    ])


# ============================================================
# ITEM 186-195: Position Monitoring
# ============================================================
@dataclass
class PortfolioGreeks:
    """Aggregated portfolio Greeks."""
    total_delta: float
    total_gamma: float
    total_theta: float
    total_vega: float
    delta_dollars: float
    gamma_dollars: float
    theta_daily: float
    vega_1pct: float


def calculate_portfolio_greeks(positions: List[Dict]) -> PortfolioGreeks:
    """Calculate aggregated portfolio Greeks."""
    total_delta = sum(p.get('delta', 0) * p.get('quantity', 0) for p in positions)
    total_gamma = sum(p.get('gamma', 0) * p.get('quantity', 0) for p in positions)
    total_theta = sum(p.get('theta', 0) * p.get('quantity', 0) for p in positions)
    total_vega = sum(p.get('vega', 0) * p.get('quantity', 0) for p in positions)
    
    # Dollar exposures (assuming 100 multiplier)
    delta_dollars = total_delta * 100
    gamma_dollars = total_gamma * 100 * 100  # Per 1% move
    theta_daily = total_theta * 100
    vega_1pct = total_vega * 100
    
    return PortfolioGreeks(
        total_delta=total_delta,
        total_gamma=total_gamma,
        total_theta=total_theta,
        total_vega=total_vega,
        delta_dollars=delta_dollars,
        gamma_dollars=gamma_dollars,
        theta_daily=theta_daily,
        vega_1pct=vega_1pct
    )


def create_portfolio_greeks_card(greeks: PortfolioGreeks) -> dbc.Card:
    """Create portfolio Greeks summary card."""
    def greek_item(name: str, value: float, dollar_value: float, unit: str = "") -> dbc.Col:
        color = 'success' if value >= 0 else 'danger'
        return dbc.Col([
            html.Div([
                html.H5(f"{value:+.2f}", className=f"text-{color} mb-0"),
                html.Small(name, className="text-muted d-block"),
                html.Small(f"${dollar_value:+,.0f}{unit}", className="text-muted")
            ], className="text-center")
        ], width=3)
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-chart-pie me-2"),
            "Portfolio Greeks"
        ]),
        dbc.CardBody([
            dbc.Row([
                greek_item("Delta", greeks.total_delta, greeks.delta_dollars),
                greek_item("Gamma", greeks.total_gamma, greeks.gamma_dollars, "/1%"),
                greek_item("Theta", greeks.total_theta, greeks.theta_daily, "/day"),
                greek_item("Vega", greeks.total_vega, greeks.vega_1pct, "/1% IV"),
            ])
        ])
    ])


# ============================================================
# ITEM 196-200: Dashboard Customization
# ============================================================
@dataclass
class DashboardLayout:
    """User dashboard layout configuration."""
    user_id: str
    layout_name: str
    widgets: List[Dict]  # Widget configurations
    theme: str = 'dark'
    refresh_rate: int = 5  # seconds
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)


class DashboardManager:
    """Manage dashboard layouts and customization."""
    
    def __init__(self):
        self.layouts: Dict[str, DashboardLayout] = {}
        self._create_default_layouts()
    
    def _create_default_layouts(self):
        """Create default dashboard layouts."""
        # Trading layout
        self.layouts['trading'] = DashboardLayout(
            user_id='default',
            layout_name='Trading',
            widgets=[
                {'type': 'chain_viewer', 'position': [0, 0], 'size': [8, 4]},
                {'type': 'greeks_summary', 'position': [8, 0], 'size': [4, 2]},
                {'type': 'positions', 'position': [8, 2], 'size': [4, 2]},
                {'type': 'order_entry', 'position': [0, 4], 'size': [6, 2]},
                {'type': 'alerts', 'position': [6, 4], 'size': [6, 2]},
            ]
        )
        
        # Analysis layout
        self.layouts['analysis'] = DashboardLayout(
            user_id='default',
            layout_name='Analysis',
            widgets=[
                {'type': 'vol_surface', 'position': [0, 0], 'size': [6, 4]},
                {'type': 'term_structure', 'position': [6, 0], 'size': [6, 2]},
                {'type': 'skew_chart', 'position': [6, 2], 'size': [6, 2]},
                {'type': 'regime_indicator', 'position': [0, 4], 'size': [4, 2]},
                {'type': 'flow_summary', 'position': [4, 4], 'size': [4, 2]},
                {'type': 'recommendations', 'position': [8, 4], 'size': [4, 2]},
            ]
        )
        
        # Strategy builder layout
        self.layouts['strategy'] = DashboardLayout(
            user_id='default',
            layout_name='Strategy Builder',
            widgets=[
                {'type': 'strategy_builder', 'position': [0, 0], 'size': [8, 3]},
                {'type': 'payoff_diagram', 'position': [0, 3], 'size': [8, 3]},
                {'type': 'risk_reward', 'position': [8, 0], 'size': [4, 3]},
                {'type': 'what_if', 'position': [8, 3], 'size': [4, 3]},
            ]
        )
    
    def get_layout(self, layout_name: str) -> Optional[DashboardLayout]:
        """Get a dashboard layout."""
        return self.layouts.get(layout_name)
    
    def save_layout(self, layout: DashboardLayout):
        """Save a dashboard layout."""
        layout.modified_at = datetime.now()
        self.layouts[layout.layout_name.lower()] = layout


# ============================================================
# ITEM 201-210: Advanced Features
# ============================================================

# Earnings Calendar Integration
def get_earnings_calendar(symbols: List[str], days_ahead: int = 30) -> List[Dict]:
    """Get upcoming earnings dates for symbols."""
    # Placeholder - would fetch from actual source
    earnings = []
    for symbol in symbols:
        # Random future date
        date = datetime.now() + timedelta(days=np.random.randint(1, days_ahead))
        earnings.append({
            'symbol': symbol,
            'date': date,
            'timing': np.random.choice(['BMO', 'AMC']),  # Before/After market
            'estimated_move': np.random.uniform(3, 10),
            'iv_crush_expected': np.random.uniform(20, 40)
        })
    
    return sorted(earnings, key=lambda x: x['date'])


def create_earnings_calendar_card(earnings: List[Dict]) -> dbc.Card:
    """Create earnings calendar card."""
    rows = []
    for e in earnings[:10]:
        rows.append(html.Tr([
            html.Td(e['symbol']),
            html.Td(e['date'].strftime('%b %d')),
            html.Td(e['timing']),
            html.Td(f"±{e['estimated_move']:.1f}%"),
            html.Td(f"-{e['iv_crush_expected']:.0f}%", className="text-danger")
        ]))
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-calendar me-2"),
            "Upcoming Earnings"
        ]),
        dbc.CardBody([
            dbc.Table([
                html.Thead([
                    html.Tr([
                        html.Th("Symbol"),
                        html.Th("Date"),
                        html.Th("Time"),
                        html.Th("Est. Move"),
                        html.Th("IV Crush")
                    ])
                ]),
                html.Tbody(rows)
            ], bordered=True, hover=True, size="sm", striped=True)
        ])
    ])


# Dividend Calendar
def get_dividend_calendar(symbols: List[str]) -> List[Dict]:
    """Get upcoming dividend dates."""
    dividends = []
    for symbol in symbols:
        ex_date = datetime.now() + timedelta(days=np.random.randint(1, 60))
        dividends.append({
            'symbol': symbol,
            'ex_date': ex_date,
            'pay_date': ex_date + timedelta(days=14),
            'amount': np.random.uniform(0.5, 2.5),
            'yield': np.random.uniform(1, 4)
        })
    
    return sorted(dividends, key=lambda x: x['ex_date'])


# Sector Rotation Analysis
def analyze_sector_rotation(sector_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Analyze sector rotation patterns."""
    results = {}
    
    for sector, data in sector_data.items():
        if data.empty:
            continue
        
        # Calculate momentum
        returns = data['close'].pct_change()
        momentum_1m = returns.iloc[-21:].sum() if len(returns) >= 21 else 0
        momentum_3m = returns.iloc[-63:].sum() if len(returns) >= 63 else 0
        
        results[sector] = {
            'momentum_1m': momentum_1m,
            'momentum_3m': momentum_3m,
            'trend': 'strong' if momentum_1m > 0.05 else ('weak' if momentum_1m < -0.05 else 'neutral'),
            'rotation_score': momentum_1m - momentum_3m  # Improving or deteriorating
        }
    
    return results


# ============================================================
# ITEM 211-220: Watchlist & Screening
# ============================================================
@dataclass
class WatchlistItem:
    """Watchlist item."""
    symbol: str
    notes: str = ""
    target_entry: Optional[float] = None
    target_exit: Optional[float] = None
    iv_alert: Optional[float] = None
    added_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)


class WatchlistManager:
    """Manage watchlists."""
    
    def __init__(self):
        self.watchlists: Dict[str, List[WatchlistItem]] = {
            'default': []
        }
    
    def add_symbol(self, symbol: str, watchlist: str = 'default', **kwargs) -> WatchlistItem:
        """Add symbol to watchlist."""
        if watchlist not in self.watchlists:
            self.watchlists[watchlist] = []
        
        item = WatchlistItem(symbol=symbol, **kwargs)
        self.watchlists[watchlist].append(item)
        return item
    
    def remove_symbol(self, symbol: str, watchlist: str = 'default'):
        """Remove symbol from watchlist."""
        if watchlist in self.watchlists:
            self.watchlists[watchlist] = [
                i for i in self.watchlists[watchlist] if i.symbol != symbol
            ]
    
    def get_watchlist(self, watchlist: str = 'default') -> List[WatchlistItem]:
        """Get watchlist items."""
        return self.watchlists.get(watchlist, [])


# Options Screener
def screen_options(
    universe: List[str],
    filters: Dict[str, Any]
) -> List[Dict]:
    """Screen options based on criteria."""
    results = []
    
    for symbol in universe:
        # Placeholder - would fetch actual data
        option_data = {
            'symbol': symbol,
            'iv_rank': np.random.uniform(0, 100),
            'iv_percentile': np.random.uniform(0, 100),
            'atm_iv': np.random.uniform(0.15, 0.60),
            'volume': np.random.randint(1000, 100000),
            'pcr': np.random.uniform(0.5, 2.0),
            'expected_move': np.random.uniform(2, 15)
        }
        
        # Apply filters
        passes = True
        
        if 'iv_rank_min' in filters:
            passes = passes and option_data['iv_rank'] >= filters['iv_rank_min']
        if 'iv_rank_max' in filters:
            passes = passes and option_data['iv_rank'] <= filters['iv_rank_max']
        if 'volume_min' in filters:
            passes = passes and option_data['volume'] >= filters['volume_min']
        
        if passes:
            results.append(option_data)
    
    return sorted(results, key=lambda x: x['iv_rank'], reverse=True)


def create_screener_results_table(results: List[Dict]) -> dbc.Card:
    """Create screener results table."""
    rows = []
    for r in results[:20]:
        iv_color = 'danger' if r['iv_rank'] > 70 else ('success' if r['iv_rank'] < 30 else 'warning')
        
        rows.append(html.Tr([
            html.Td(r['symbol']),
            html.Td(dbc.Badge(f"{r['iv_rank']:.0f}%", color=iv_color)),
            html.Td(f"{r['atm_iv']*100:.1f}%"),
            html.Td(f"{r['volume']:,}"),
            html.Td(f"{r['pcr']:.2f}"),
            html.Td(f"±{r['expected_move']:.1f}%"),
            html.Td(dbc.Button([html.I(className="fas fa-plus")], size="sm", color="primary", outline=True))
        ]))
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-filter me-2"),
            "Screener Results",
            dbc.Badge(str(len(results)), color="info", className="ms-2")
        ]),
        dbc.CardBody([
            dbc.Table([
                html.Thead([
                    html.Tr([
                        html.Th("Symbol"),
                        html.Th("IV Rank"),
                        html.Th("ATM IV"),
                        html.Th("Volume"),
                        html.Th("P/C"),
                        html.Th("Move"),
                        html.Th("")
                    ])
                ]),
                html.Tbody(rows)
            ], bordered=True, hover=True, size="sm", striped=True)
        ])
    ])


def create_screener_panel() -> html.Div:
    """Create options screener panel."""
    return html.Div([
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-search me-2"),
                "Options Screener"
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("IV Rank"),
                        dcc.RangeSlider(
                            id="screener-iv-rank",
                            min=0, max=100, step=5,
                            value=[50, 100],
                            marks={0: '0', 50: '50', 100: '100'}
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Label("Min Volume"),
                        dbc.Input(id="screener-min-vol", type="number", value=5000)
                    ], width=2),
                    dbc.Col([
                        dbc.Label("Expected Move"),
                        dcc.RangeSlider(
                            id="screener-exp-move",
                            min=0, max=20, step=1,
                            value=[3, 15],
                            marks={0: '0%', 10: '10%', 20: '20%'}
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Label(" "),
                        dbc.Button([
                            html.I(className="fas fa-search me-2"),
                            "Screen"
                        ], id="run-screener-btn", color="primary", className="w-100 d-block mt-1")
                    ], width=2)
                ])
            ])
        ], className="mb-3"),
        
        html.Div(id="screener-results-area")
    ])


# ============================================================
# Main Monitoring Dashboard
# ============================================================
def create_monitoring_dashboard() -> html.Div:
    """Create the monitoring and alerts dashboard."""
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Div(id="portfolio-greeks-card")
            ], width=6),
            dbc.Col([
                html.Div(id="alerts-panel")
            ], width=6)
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                html.Div(id="earnings-calendar-card")
            ], width=6),
            dbc.Col([
                html.Div(id="watchlist-panel")
            ], width=6)
        ], className="mb-3"),
        
        create_screener_panel()
    ])


__all__ = [
    'AlertType',
    'AlertPriority',
    'Alert',
    'AlertManager',
    'create_alert_card',
    'create_alerts_panel',
    'PortfolioGreeks',
    'calculate_portfolio_greeks',
    'create_portfolio_greeks_card',
    'DashboardLayout',
    'DashboardManager',
    'get_earnings_calendar',
    'create_earnings_calendar_card',
    'get_dividend_calendar',
    'analyze_sector_rotation',
    'WatchlistItem',
    'WatchlistManager',
    'screen_options',
    'create_screener_results_table',
    'create_screener_panel',
    'create_monitoring_dashboard',
]

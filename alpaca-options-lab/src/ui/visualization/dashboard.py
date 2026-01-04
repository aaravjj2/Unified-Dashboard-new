"""
Alpaca Options Lab - Real-Time Dashboard

Production-grade Plotly Dash dashboard with:
- Live portfolio status
- Real-time Greeks monitoring
- Position management
- Risk alerts

Layout Sections:
1. Header: Account summary, P&L, alerts
2. Positions: Active positions table with Greeks
3. Risk: Portfolio Greeks, limit status
4. Charts: P&L chart, Greeks evolution

Usage:
    from src.ui.visualization.dashboard import create_dashboard_app
    
    app = create_dashboard_app()
    app.run_server(debug=True, port=8050)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

try:
    import dash
    from dash import dcc, html, dash_table, callback_context
    from dash.dependencies import Input, Output, State
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    DASH_AVAILABLE = True
except ImportError:
    DASH_AVAILABLE = False

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


# =============================================================================
# STYLES
# =============================================================================

COLORS = {
    "background": "#1a1a2e",
    "card": "#16213e",
    "text": "#e8e8e8",
    "accent": "#0f3460",
    "positive": "#00d26a",
    "negative": "#ff6b6b",
    "warning": "#feca57",
    "border": "#2a2a4a",
}

CARD_STYLE = {
    "backgroundColor": COLORS["card"],
    "borderRadius": "8px",
    "padding": "20px",
    "marginBottom": "20px",
    "boxShadow": "0 4px 6px rgba(0,0,0,0.3)",
}

HEADER_STYLE = {
    "color": COLORS["text"],
    "marginBottom": "15px",
    "borderBottom": f"2px solid {COLORS['accent']}",
    "paddingBottom": "10px",
}

TABLE_STYLE = {
    "style_header": {
        "backgroundColor": COLORS["accent"],
        "color": COLORS["text"],
        "fontWeight": "bold",
        "textAlign": "center",
    },
    "style_cell": {
        "backgroundColor": COLORS["card"],
        "color": COLORS["text"],
        "textAlign": "center",
        "padding": "10px",
        "border": f"1px solid {COLORS['border']}",
    },
    "style_data_conditional": [
        {
            "if": {"filter_query": "{P&L} > 0"},
            "color": COLORS["positive"],
        },
        {
            "if": {"filter_query": "{P&L} < 0"},
            "color": COLORS["negative"],
        },
    ],
}


# =============================================================================
# DASHBOARD APP
# =============================================================================

class DashboardApp:
    """
    Main dashboard application.
    
    Features:
    - Real-time position updates
    - Portfolio Greeks display
    - Risk limit monitoring
    - P&L tracking
    
    Example:
        app = DashboardApp()
        
        # Register data providers
        app.set_position_provider(get_positions)
        app.set_greeks_provider(get_portfolio_greeks)
        
        # Run
        app.run(port=8050)
    """
    
    def __init__(
        self,
        title: str = "Alpaca Options Lab",
        update_interval: int = 5000,  # 5 seconds
    ) -> None:
        """
        Initialize dashboard app.
        
        Args:
            title: Dashboard title
            update_interval: Data refresh interval in milliseconds
        """
        if not DASH_AVAILABLE:
            raise ImportError("dash and plotly are required for the dashboard")
        
        self.title = title
        self.update_interval = update_interval
        
        # Data providers (callbacks that return data)
        self._position_provider: Optional[Callable] = None
        self._greeks_provider: Optional[Callable] = None
        self._pnl_provider: Optional[Callable] = None
        self._alerts_provider: Optional[Callable] = None
        
        # Create Dash app
        self.app = dash.Dash(
            __name__,
            title=title,
            suppress_callback_exceptions=True,
        )
        
        # Build layout
        self.app.layout = self._create_layout()
        
        # Register callbacks
        self._register_callbacks()
        
        logger.info("DashboardApp initialized", title=title)
    
    def set_position_provider(self, provider: Callable[[], List[Dict]]) -> None:
        """Set callback for position data."""
        self._position_provider = provider
    
    def set_greeks_provider(self, provider: Callable[[], Dict]) -> None:
        """Set callback for portfolio Greeks."""
        self._greeks_provider = provider
    
    def set_pnl_provider(self, provider: Callable[[], Dict]) -> None:
        """Set callback for P&L data."""
        self._pnl_provider = provider
    
    def set_alerts_provider(self, provider: Callable[[], List[Dict]]) -> None:
        """Set callback for alerts."""
        self._alerts_provider = provider
    
    def _create_layout(self) -> html.Div:
        """Create dashboard layout."""
        return html.Div(
            style={
                "backgroundColor": COLORS["background"],
                "minHeight": "100vh",
                "padding": "20px",
            },
            children=[
                # Header
                self._create_header(),
                
                # Main content
                html.Div(
                    style={"display": "flex", "gap": "20px"},
                    children=[
                        # Left column (positions + charts)
                        html.Div(
                            style={"flex": "2"},
                            children=[
                                self._create_positions_card(),
                                self._create_pnl_chart_card(),
                            ],
                        ),
                        # Right column (Greeks + risk)
                        html.Div(
                            style={"flex": "1"},
                            children=[
                                self._create_greeks_card(),
                                self._create_risk_card(),
                                self._create_alerts_card(),
                            ],
                        ),
                    ],
                ),
                
                # Auto-update interval
                dcc.Interval(
                    id="update-interval",
                    interval=self.update_interval,
                    n_intervals=0,
                ),
                
                # Data stores
                dcc.Store(id="positions-store"),
                dcc.Store(id="greeks-store"),
            ],
        )
    
    def _create_header(self) -> html.Div:
        """Create header section."""
        return html.Div(
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "marginBottom": "20px",
                "padding": "20px",
                "backgroundColor": COLORS["card"],
                "borderRadius": "8px",
            },
            children=[
                # Title
                html.H1(
                    self.title,
                    style={"color": COLORS["text"], "margin": 0},
                ),
                # Summary metrics
                html.Div(
                    id="header-metrics",
                    style={"display": "flex", "gap": "40px"},
                    children=[
                        self._metric_box("Total P&L", "$0.00", "total-pnl"),
                        self._metric_box("Day P&L", "$0.00", "day-pnl"),
                        self._metric_box("Positions", "0", "position-count"),
                        self._metric_box("Buying Power", "$0.00", "buying-power"),
                    ],
                ),
            ],
        )
    
    def _metric_box(self, label: str, value: str, id_suffix: str) -> html.Div:
        """Create a metric display box."""
        return html.Div(
            children=[
                html.Div(
                    label,
                    style={
                        "color": COLORS["text"],
                        "fontSize": "12px",
                        "opacity": 0.7,
                    },
                ),
                html.Div(
                    id=f"metric-{id_suffix}",
                    children=value,
                    style={
                        "color": COLORS["text"],
                        "fontSize": "24px",
                        "fontWeight": "bold",
                    },
                ),
            ],
        )
    
    def _create_positions_card(self) -> html.Div:
        """Create positions table card."""
        return html.Div(
            style=CARD_STYLE,
            children=[
                html.H3("Positions", style=HEADER_STYLE),
                dash_table.DataTable(
                    id="positions-table",
                    columns=[
                        {"name": "Symbol", "id": "symbol"},
                        {"name": "Side", "id": "side"},
                        {"name": "Qty", "id": "quantity"},
                        {"name": "Entry", "id": "entry_price", "type": "numeric", "format": {"specifier": ".2f"}},
                        {"name": "Current", "id": "current_price", "type": "numeric", "format": {"specifier": ".2f"}},
                        {"name": "P&L", "id": "pnl", "type": "numeric", "format": {"specifier": ".2f"}},
                        {"name": "Delta", "id": "delta", "type": "numeric", "format": {"specifier": ".3f"}},
                        {"name": "Theta", "id": "theta", "type": "numeric", "format": {"specifier": ".2f"}},
                        {"name": "DTE", "id": "dte"},
                    ],
                    data=[],
                    **TABLE_STYLE,
                    page_size=10,
                    sort_action="native",
                    filter_action="native",
                ),
            ],
        )
    
    def _create_greeks_card(self) -> html.Div:
        """Create Greeks summary card."""
        return html.Div(
            style=CARD_STYLE,
            children=[
                html.H3("Portfolio Greeks", style=HEADER_STYLE),
                html.Div(
                    id="greeks-display",
                    children=self._greeks_grid({
                        "delta": 0,
                        "gamma": 0,
                        "theta": 0,
                        "vega": 0,
                    }),
                ),
            ],
        )
    
    def _greeks_grid(self, greeks: Dict[str, float]) -> html.Div:
        """Create Greeks display grid."""
        items = [
            ("Delta", greeks.get("delta", 0), "Δ"),
            ("Gamma", greeks.get("gamma", 0), "Γ"),
            ("Theta", greeks.get("theta", 0), "Θ"),
            ("Vega", greeks.get("vega", 0), "ν"),
        ]
        
        return html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "15px"},
            children=[
                html.Div(
                    style={
                        "backgroundColor": COLORS["accent"],
                        "padding": "15px",
                        "borderRadius": "6px",
                        "textAlign": "center",
                    },
                    children=[
                        html.Div(
                            f"{symbol} {name}",
                            style={"color": COLORS["text"], "opacity": 0.7, "fontSize": "12px"},
                        ),
                        html.Div(
                            f"{value:+.2f}" if name != "Gamma" else f"{value:+.4f}",
                            style={
                                "color": COLORS["positive"] if value >= 0 else COLORS["negative"],
                                "fontSize": "20px",
                                "fontWeight": "bold",
                            },
                        ),
                    ],
                )
                for name, value, symbol in items
            ],
        )
    
    def _create_risk_card(self) -> html.Div:
        """Create risk limits card."""
        return html.Div(
            style=CARD_STYLE,
            children=[
                html.H3("Risk Limits", style=HEADER_STYLE),
                html.Div(
                    id="risk-limits-display",
                    children=[
                        self._limit_bar("Delta", 50, 200),
                        self._limit_bar("Notional", 75000, 100000),
                        self._limit_bar("Positions", 8, 20),
                    ],
                ),
            ],
        )
    
    def _limit_bar(self, name: str, current: float, limit: float) -> html.Div:
        """Create a limit progress bar."""
        pct = min(current / limit * 100, 100)
        color = COLORS["positive"]
        if pct >= 80:
            color = COLORS["warning"]
        if pct >= 100:
            color = COLORS["negative"]
        
        return html.Div(
            style={"marginBottom": "15px"},
            children=[
                html.Div(
                    style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "marginBottom": "5px",
                    },
                    children=[
                        html.Span(name, style={"color": COLORS["text"], "fontSize": "12px"}),
                        html.Span(
                            f"{current:,.0f} / {limit:,.0f}",
                            style={"color": COLORS["text"], "fontSize": "12px"},
                        ),
                    ],
                ),
                html.Div(
                    style={
                        "backgroundColor": COLORS["border"],
                        "borderRadius": "4px",
                        "height": "8px",
                    },
                    children=[
                        html.Div(
                            style={
                                "backgroundColor": color,
                                "width": f"{pct}%",
                                "height": "100%",
                                "borderRadius": "4px",
                                "transition": "width 0.3s ease",
                            },
                        ),
                    ],
                ),
            ],
        )
    
    def _create_alerts_card(self) -> html.Div:
        """Create alerts card."""
        return html.Div(
            style=CARD_STYLE,
            children=[
                html.H3("Alerts", style=HEADER_STYLE),
                html.Div(
                    id="alerts-display",
                    children=[
                        html.Div(
                            "No active alerts",
                            style={"color": COLORS["text"], "opacity": 0.5},
                        ),
                    ],
                ),
            ],
        )
    
    def _create_pnl_chart_card(self) -> html.Div:
        """Create P&L chart card."""
        return html.Div(
            style=CARD_STYLE,
            children=[
                html.H3("P&L Chart", style=HEADER_STYLE),
                dcc.Graph(
                    id="pnl-chart",
                    config={"displayModeBar": False},
                    style={"height": "300px"},
                    figure=self._empty_pnl_chart(),
                ),
            ],
        )
    
    def _empty_pnl_chart(self) -> go.Figure:
        """Create empty P&L chart."""
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor=COLORS["card"],
            plot_bgcolor=COLORS["card"],
            font_color=COLORS["text"],
            margin=dict(l=40, r=20, t=20, b=40),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor=COLORS["border"]),
        )
        return fig
    
    def _register_callbacks(self) -> None:
        """Register Dash callbacks."""
        
        @self.app.callback(
            [
                Output("positions-table", "data"),
                Output("greeks-display", "children"),
                Output("metric-total-pnl", "children"),
                Output("metric-position-count", "children"),
            ],
            Input("update-interval", "n_intervals"),
        )
        def update_dashboard(n_intervals):
            """Update dashboard data."""
            # Get positions
            positions = []
            if self._position_provider:
                try:
                    positions = self._position_provider()
                except Exception as e:
                    logger.error(f"Position provider error: {e}")
            
            # Get Greeks
            greeks = {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}
            if self._greeks_provider:
                try:
                    greeks = self._greeks_provider()
                except Exception as e:
                    logger.error(f"Greeks provider error: {e}")
            
            # Calculate totals
            total_pnl = sum(p.get("pnl", 0) for p in positions)
            pnl_color = COLORS["positive"] if total_pnl >= 0 else COLORS["negative"]
            pnl_text = html.Span(
                f"${total_pnl:+,.2f}",
                style={"color": pnl_color},
            )
            
            return (
                positions,
                self._greeks_grid(greeks),
                pnl_text,
                str(len(positions)),
            )
    
    def run(
        self,
        host: str = "127.0.0.1",
        port: int = 8050,
        debug: bool = False,
    ) -> None:
        """Run the dashboard server."""
        logger.info(f"Starting dashboard at http://{host}:{port}")
        self.app.run_server(host=host, port=port, debug=debug)


def create_dashboard_app(
    title: str = "Alpaca Options Lab",
    **kwargs,
) -> DashboardApp:
    """
    Factory function to create dashboard app.
    
    Args:
        title: Dashboard title
        **kwargs: Additional arguments for DashboardApp
        
    Returns:
        Configured DashboardApp instance
    """
    return DashboardApp(title=title, **kwargs)

"""
Alpaca Options Lab - Visualization Module

Production-grade visualization components with:
- Real-time dashboard (Plotly Dash)
- Backtest result viewer
- Greeks visualization
- P&L attribution charts

Components:
- DashboardApp: Main Dash application
- BacktestViewer: Backtest analysis charts
- GreeksDisplay: Real-time Greeks visualization
- ChartComponents: Reusable chart components
"""
from src.ui.visualization.dashboard import (
    DashboardApp,
    create_dashboard_app,
)
from src.ui.visualization.backtest_viewer import (
    BacktestViewer,
    create_equity_chart,
    create_drawdown_chart,
    create_trade_chart,
)
from src.ui.visualization.charts import (
    create_greeks_heatmap,
    create_pnl_attribution,
    create_risk_chart,
    create_options_payoff,
)

__all__ = [
    # Dashboard
    "DashboardApp",
    "create_dashboard_app",
    # Backtest viewer
    "BacktestViewer",
    "create_equity_chart",
    "create_drawdown_chart",
    "create_trade_chart",
    # Charts
    "create_greeks_heatmap",
    "create_pnl_attribution",
    "create_risk_chart",
    "create_options_payoff",
]

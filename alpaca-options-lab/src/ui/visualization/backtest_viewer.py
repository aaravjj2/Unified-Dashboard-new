"""
Alpaca Options Lab - Backtest Result Viewer

Production-grade backtest visualization with:
- Equity curve with drawdown overlay
- Trade analysis charts
- Performance metrics display
- Rolling statistics

Charts:
1. Equity Curve: Portfolio value over time
2. Drawdown Chart: Drawdown periods
3. Trade Distribution: P&L histogram
4. Monthly Returns: Heatmap of monthly performance
5. Rolling Metrics: Rolling Sharpe, volatility

Usage:
    from src.ui.visualization.backtest_viewer import BacktestViewer
    
    viewer = BacktestViewer(backtest_result)
    
    # Get individual charts
    equity_fig = viewer.equity_chart()
    drawdown_fig = viewer.drawdown_chart()
    
    # Full report
    viewer.generate_report("backtest_report.html")
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

import numpy as np

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


# =============================================================================
# CHART STYLES
# =============================================================================

CHART_COLORS = {
    "primary": "#3498db",
    "secondary": "#2ecc71",
    "negative": "#e74c3c",
    "neutral": "#95a5a6",
    "background": "#1a1a2e",
    "grid": "#2a2a4a",
    "text": "#e8e8e8",
}

CHART_TEMPLATE = {
    "paper_bgcolor": CHART_COLORS["background"],
    "plot_bgcolor": CHART_COLORS["background"],
    "font": {"color": CHART_COLORS["text"]},
    "xaxis": {
        "gridcolor": CHART_COLORS["grid"],
        "zerolinecolor": CHART_COLORS["grid"],
    },
    "yaxis": {
        "gridcolor": CHART_COLORS["grid"],
        "zerolinecolor": CHART_COLORS["grid"],
    },
}


# =============================================================================
# CHART FACTORY FUNCTIONS
# =============================================================================

def create_equity_chart(
    equity_curve: List[Tuple[datetime, float]],
    benchmark_curve: Optional[List[Tuple[datetime, float]]] = None,
    title: str = "Portfolio Equity Curve",
) -> "go.Figure":
    """
    Create equity curve chart.
    
    Args:
        equity_curve: List of (timestamp, equity) tuples
        benchmark_curve: Optional benchmark equity curve
        title: Chart title
        
    Returns:
        Plotly Figure
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("plotly is required for charting")
    
    fig = go.Figure()
    
    if equity_curve:
        timestamps, equities = zip(*equity_curve)
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=equities,
            mode="lines",
            name="Portfolio",
            line=dict(color=CHART_COLORS["primary"], width=2),
            fill="tozeroy",
            fillcolor=f"rgba(52, 152, 219, 0.2)",
        ))
    
    if benchmark_curve:
        bm_timestamps, bm_equities = zip(*benchmark_curve)
        
        # Normalize benchmark to same starting point
        if equity_curve and bm_equities:
            initial = equity_curve[0][1]
            bm_initial = bm_equities[0]
            bm_normalized = [initial * (e / bm_initial) for e in bm_equities]
            
            fig.add_trace(go.Scatter(
                x=bm_timestamps,
                y=bm_normalized,
                mode="lines",
                name="Benchmark",
                line=dict(color=CHART_COLORS["neutral"], width=1, dash="dash"),
            ))
    
    fig.update_layout(
        title=title,
        **CHART_TEMPLATE,
        xaxis_title="Date",
        yaxis_title="Equity ($)",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )
    
    return fig


def create_drawdown_chart(
    equity_curve: List[Tuple[datetime, float]],
    title: str = "Drawdown",
) -> "go.Figure":
    """
    Create drawdown chart.
    
    Args:
        equity_curve: List of (timestamp, equity) tuples
        title: Chart title
        
    Returns:
        Plotly Figure
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("plotly is required for charting")
    
    if not equity_curve:
        return go.Figure()
    
    timestamps, equities = zip(*equity_curve)
    equities = np.array(equities)
    
    # Calculate drawdown
    peak = np.maximum.accumulate(equities)
    drawdown = (peak - equities) / peak * 100  # Percentage
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=-drawdown,
        mode="lines",
        name="Drawdown",
        line=dict(color=CHART_COLORS["negative"], width=1),
        fill="tozeroy",
        fillcolor=f"rgba(231, 76, 60, 0.3)",
    ))
    
    fig.update_layout(
        title=title,
        **CHART_TEMPLATE,
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        hovermode="x unified",
    )
    
    return fig


def create_trade_chart(
    trades: List[Dict[str, Any]],
    chart_type: str = "histogram",
    title: str = "Trade P&L Distribution",
) -> "go.Figure":
    """
    Create trade analysis chart.
    
    Args:
        trades: List of trade dictionaries with 'pnl' field
        chart_type: 'histogram', 'scatter', or 'cumulative'
        title: Chart title
        
    Returns:
        Plotly Figure
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("plotly is required for charting")
    
    if not trades:
        return go.Figure()
    
    pnls = [t.get("pnl", t.get("net_pnl", 0)) for t in trades]
    
    fig = go.Figure()
    
    if chart_type == "histogram":
        # Color bins by positive/negative
        colors = [CHART_COLORS["secondary"] if p > 0 else CHART_COLORS["negative"] for p in pnls]
        
        fig.add_trace(go.Histogram(
            x=pnls,
            nbinsx=30,
            name="Trade P&L",
            marker_color=CHART_COLORS["primary"],
        ))
        
        # Add vertical line at zero
        fig.add_vline(
            x=0,
            line_dash="dash",
            line_color=CHART_COLORS["text"],
            opacity=0.5,
        )
        
        fig.update_layout(
            xaxis_title="P&L ($)",
            yaxis_title="Count",
        )
        
    elif chart_type == "scatter":
        timestamps = [t.get("timestamp", t.get("exit_time")) for t in trades]
        colors = [CHART_COLORS["secondary"] if p > 0 else CHART_COLORS["negative"] for p in pnls]
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=pnls,
            mode="markers",
            name="Trade P&L",
            marker=dict(
                color=colors,
                size=8,
                opacity=0.7,
            ),
        ))
        
        fig.add_hline(
            y=0,
            line_dash="dash",
            line_color=CHART_COLORS["text"],
            opacity=0.5,
        )
        
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="P&L ($)",
        )
        
    elif chart_type == "cumulative":
        cumulative_pnl = np.cumsum(pnls)
        
        fig.add_trace(go.Scatter(
            x=list(range(1, len(pnls) + 1)),
            y=cumulative_pnl,
            mode="lines",
            name="Cumulative P&L",
            line=dict(color=CHART_COLORS["primary"], width=2),
        ))
        
        fig.update_layout(
            xaxis_title="Trade #",
            yaxis_title="Cumulative P&L ($)",
        )
    
    fig.update_layout(
        title=title,
        **CHART_TEMPLATE,
    )
    
    return fig


def create_monthly_returns_heatmap(
    equity_curve: List[Tuple[datetime, float]],
    title: str = "Monthly Returns",
) -> "go.Figure":
    """
    Create monthly returns heatmap.
    
    Args:
        equity_curve: List of (timestamp, equity) tuples
        title: Chart title
        
    Returns:
        Plotly Figure
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("plotly is required for charting")
    
    if not equity_curve:
        return go.Figure()
    
    # Group by month
    monthly_data: Dict[str, Dict[str, float]] = {}
    
    for i in range(1, len(equity_curve)):
        prev_time, prev_eq = equity_curve[i-1]
        curr_time, curr_eq = equity_curve[i]
        
        year = str(curr_time.year) if hasattr(curr_time, 'year') else str(curr_time)[:4]
        month = curr_time.strftime("%b") if hasattr(curr_time, 'strftime') else str(curr_time)[5:7]
        
        if year not in monthly_data:
            monthly_data[year] = {}
        
        # Accumulate returns within month
        if month not in monthly_data[year]:
            monthly_data[year][month] = 1.0
        
        daily_return = curr_eq / prev_eq
        monthly_data[year][month] *= daily_return
    
    # Convert to percentage returns
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    years = sorted(monthly_data.keys())
    
    z_values = []
    for year in years:
        row = []
        for month in months:
            if month in monthly_data.get(year, {}):
                ret = (monthly_data[year][month] - 1) * 100
                row.append(ret)
            else:
                row.append(None)
        z_values.append(row)
    
    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=months,
        y=years,
        colorscale=[
            [0, CHART_COLORS["negative"]],
            [0.5, CHART_COLORS["neutral"]],
            [1, CHART_COLORS["secondary"]],
        ],
        text=[[f"{v:.1f}%" if v is not None else "" for v in row] for row in z_values],
        texttemplate="%{text}",
        textfont={"size": 10},
        hoverongaps=False,
    ))
    
    fig.update_layout(
        title=title,
        **CHART_TEMPLATE,
        xaxis_title="Month",
        yaxis_title="Year",
    )
    
    return fig


# =============================================================================
# BACKTEST VIEWER CLASS
# =============================================================================

class BacktestViewer:
    """
    Comprehensive backtest result visualization.
    
    Generates all standard backtest charts and reports.
    
    Example:
        from src.backtesting.engine import BacktestResult
        
        viewer = BacktestViewer(result)
        
        # Individual charts
        fig1 = viewer.equity_chart()
        fig2 = viewer.drawdown_chart()
        
        # Full HTML report
        viewer.generate_report("report.html")
    """
    
    def __init__(
        self,
        result: Any,  # BacktestResult
        benchmark_curve: Optional[List[Tuple[datetime, float]]] = None,
    ) -> None:
        """
        Initialize backtest viewer.
        
        Args:
            result: BacktestResult from backtest engine
            benchmark_curve: Optional benchmark equity curve
        """
        if not PLOTLY_AVAILABLE:
            raise ImportError("plotly is required for BacktestViewer")
        
        self.result = result
        self.benchmark_curve = benchmark_curve
        
        # Extract data from result
        self.equity_curve = getattr(result, "equity_curve", [])
        self.trades = getattr(result, "trades", [])
        self.daily_returns = getattr(result, "daily_returns", [])
    
    def equity_chart(self, **kwargs) -> "go.Figure":
        """Generate equity curve chart."""
        return create_equity_chart(
            equity_curve=self.equity_curve,
            benchmark_curve=self.benchmark_curve,
            **kwargs,
        )
    
    def drawdown_chart(self, **kwargs) -> "go.Figure":
        """Generate drawdown chart."""
        return create_drawdown_chart(
            equity_curve=self.equity_curve,
            **kwargs,
        )
    
    def trade_histogram(self, **kwargs) -> "go.Figure":
        """Generate trade P&L histogram."""
        return create_trade_chart(
            trades=self.trades,
            chart_type="histogram",
            **kwargs,
        )
    
    def trade_scatter(self, **kwargs) -> "go.Figure":
        """Generate trade scatter plot."""
        return create_trade_chart(
            trades=self.trades,
            chart_type="scatter",
            **kwargs,
        )
    
    def cumulative_trades(self, **kwargs) -> "go.Figure":
        """Generate cumulative trade P&L chart."""
        return create_trade_chart(
            trades=self.trades,
            chart_type="cumulative",
            **kwargs,
        )
    
    def monthly_heatmap(self, **kwargs) -> "go.Figure":
        """Generate monthly returns heatmap."""
        return create_monthly_returns_heatmap(
            equity_curve=self.equity_curve,
            **kwargs,
        )
    
    def combined_chart(self) -> "go.Figure":
        """Generate combined multi-panel chart."""
        fig = make_subplots(
            rows=3,
            cols=2,
            subplot_titles=(
                "Equity Curve",
                "Drawdown",
                "Trade P&L Distribution",
                "Cumulative Trade P&L",
                "Monthly Returns",
                "Daily Returns Distribution",
            ),
            vertical_spacing=0.1,
            horizontal_spacing=0.08,
        )
        
        # Equity curve
        if self.equity_curve:
            timestamps, equities = zip(*self.equity_curve)
            fig.add_trace(
                go.Scatter(
                    x=timestamps, y=equities,
                    mode="lines", name="Equity",
                    line=dict(color=CHART_COLORS["primary"]),
                ),
                row=1, col=1,
            )
        
        # Drawdown
        if self.equity_curve:
            timestamps, equities = zip(*self.equity_curve)
            equities = np.array(equities)
            peak = np.maximum.accumulate(equities)
            drawdown = (peak - equities) / peak * 100
            
            fig.add_trace(
                go.Scatter(
                    x=timestamps, y=-drawdown,
                    mode="lines", name="Drawdown",
                    line=dict(color=CHART_COLORS["negative"]),
                    fill="tozeroy",
                ),
                row=1, col=2,
            )
        
        # Trade histogram
        if self.trades:
            pnls = [t.get("pnl", 0) for t in self.trades]
            fig.add_trace(
                go.Histogram(
                    x=pnls, nbinsx=20, name="Trade P&L",
                    marker_color=CHART_COLORS["primary"],
                ),
                row=2, col=1,
            )
        
        # Cumulative trades
        if self.trades:
            pnls = [t.get("pnl", 0) for t in self.trades]
            cumulative = np.cumsum(pnls)
            fig.add_trace(
                go.Scatter(
                    x=list(range(len(cumulative))), y=cumulative,
                    mode="lines", name="Cumulative P&L",
                    line=dict(color=CHART_COLORS["secondary"]),
                ),
                row=2, col=2,
            )
        
        # Daily returns histogram
        if self.daily_returns:
            fig.add_trace(
                go.Histogram(
                    x=self.daily_returns, nbinsx=30, name="Daily Returns",
                    marker_color=CHART_COLORS["primary"],
                ),
                row=3, col=2,
            )
        
        fig.update_layout(
            height=900,
            showlegend=False,
            **CHART_TEMPLATE,
        )
        
        return fig
    
    def metrics_summary(self) -> str:
        """Generate metrics summary HTML."""
        r = self.result
        
        html = f"""
        <div style="font-family: Arial; color: {CHART_COLORS['text']}; 
                    background: {CHART_COLORS['background']}; padding: 20px;">
            <h2>Performance Summary</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background: {CHART_COLORS['grid']}">
                    <td style="padding: 10px;">Total Return</td>
                    <td style="padding: 10px; text-align: right;">
                        ${getattr(r, 'total_return', 0):,.2f} 
                        ({getattr(r, 'total_return_pct', 0):.2%})
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px;">Annualized Return</td>
                    <td style="padding: 10px; text-align: right;">
                        {getattr(r, 'annualized_return', 0):.2%}
                    </td>
                </tr>
                <tr style="background: {CHART_COLORS['grid']}">
                    <td style="padding: 10px;">Volatility</td>
                    <td style="padding: 10px; text-align: right;">
                        {getattr(r, 'volatility', 0):.2%}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px;">Sharpe Ratio</td>
                    <td style="padding: 10px; text-align: right;">
                        {getattr(r, 'sharpe_ratio', 0):.3f}
                    </td>
                </tr>
                <tr style="background: {CHART_COLORS['grid']}">
                    <td style="padding: 10px;">Max Drawdown</td>
                    <td style="padding: 10px; text-align: right;">
                        {getattr(r, 'max_drawdown', 0):.2%}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px;">Total Trades</td>
                    <td style="padding: 10px; text-align: right;">
                        {getattr(r, 'total_trades', 0)}
                    </td>
                </tr>
                <tr style="background: {CHART_COLORS['grid']}">
                    <td style="padding: 10px;">Win Rate</td>
                    <td style="padding: 10px; text-align: right;">
                        {getattr(r, 'win_rate', 0):.2%}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px;">Profit Factor</td>
                    <td style="padding: 10px; text-align: right;">
                        {getattr(r, 'profit_factor', 0):.3f}
                    </td>
                </tr>
            </table>
        </div>
        """
        
        return html
    
    def generate_report(
        self,
        filepath: str,
        include_trades: bool = True,
    ) -> None:
        """
        Generate complete HTML report.
        
        Args:
            filepath: Output file path
            include_trades: Whether to include trade table
        """
        combined_fig = self.combined_chart()
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Backtest Report</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: {CHART_COLORS['background']};
                    color: {CHART_COLORS['text']};
                    margin: 0;
                    padding: 20px;
                }}
                .container {{ max-width: 1400px; margin: 0 auto; }}
                h1 {{ border-bottom: 2px solid {CHART_COLORS['primary']}; padding-bottom: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Backtest Report</h1>
                {self.metrics_summary()}
                <div id="chart">{combined_fig.to_html(full_html=False)}</div>
            </div>
        </body>
        </html>
        """
        
        with open(filepath, "w") as f:
            f.write(html_content)
        
        logger.info(f"Report generated: {filepath}")

"""
Volatility Lab - Reusable UI Components
=======================================

Agent-1A: Building blocks for panels and visualizations.

Component Categories:
1. Cards: Themed containers for panels
2. Charts: Plotly chart builders (heatmap, line, scatter)
3. Tables: Bootstrap tables for metrics and signals
4. Controls: Input groups and buttons

Design Principles:
- All components return html/dcc objects
- No side effects (pure functions)
- Bootstrap 5 compatible
- Plotly chart configuration follows UX spec
"""

import logging
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

logger = logging.getLogger(__name__)

# Stable component IDs (exported for callbacks)
COMPONENT_IDS = {
    # Overview panel
    'overview_last_surface': 'vl-overview-last-surface',
    'overview_atm_iv': 'vl-overview-atm-iv',
    'overview_term_30': 'vl-overview-term-30',
    'overview_term_60': 'vl-overview-term-60',
    'overview_term_90': 'vl-overview-term-90',
    'compute_quick_btn': 'vl-compute-quick-btn',
    'overview_refresh_btn': 'vl-overview-refresh-btn',
    
    # IV Surface panel
    'calc_ticker': 'vl-calc-ticker',
    'calc_expiry': 'vl-calc-expiry',
    'calc_strike_range': 'vl-calc-strike-range',
    'calc_run_btn': 'vl-calc-run-btn',
    'heatmap': 'vl-heatmap',
    'iv_metrics_table': 'vl-iv-metrics-table',
    'iv_export_btn': 'vl-iv-export-btn',
    'explorer_date_slider': 'vl-explorer-date-slider',
    
    # Signals + Backtest panel
    'signal_run_btn': 'vl-signal-run-btn',
    'signal_table': 'vl-signal-table',
    'signal_paper_order_btn': 'vl-signal-paper-order-btn',
    'backtest_run_btn': 'vl-backtest-run-btn',
    'backtest_results': 'vl-backtest-results',
    'backtest_export_btn': 'vl-backtest-export-btn',
    
    # Diagnostics panel
    'diag_solver_log': 'vl-diag-solver-log',
    'diag_iterations': 'vl-diag-iterations',
    'diag_last_payload': 'vl-diag-last-payload',
    'diag_export_log': 'vl-diag-export-log',
    'diag_collapse': 'vl-diag-collapse',
    
    # Stores and intervals
    'surface_store': 'vl-surface-store',
    'job_store': 'vl-job-store',
    'health_interval': 'vl-health-interval',
}


def create_panel_card(header, body, card_id=None, collapsible=False, open_by_default=True):
    """
    Create themed Bootstrap card for panels
    
    Args:
        header: Card header content (string or html component)
        body: Card body content (list of html components)
        card_id: Optional ID for collapse functionality
        collapsible: If True, body is wrapped in Collapse component
        open_by_default: Initial state for collapsible cards
    
    Returns:
        dbc.Card component
    """
    card_header = dbc.CardHeader(header if isinstance(header, list) else html.H5(header, className="mb-0"))
    
    if collapsible and card_id:
        card_body = dbc.Collapse(
            dbc.CardBody(body),
            id=card_id,
            is_open=open_by_default
        )
    else:
        card_body = dbc.CardBody(body)
    
    return dbc.Card([card_header, card_body], className="h-100")


def create_heatmap(z_data, x_labels, y_labels, title="IV Heatmap", height=300):
    """
    Create Plotly heatmap for IV surface visualization
    
    Args:
        z_data: 2D array of IV values
        x_labels: X-axis labels (tenors)
        y_labels: Y-axis labels (strikes)
        title: Chart title
        height: Chart height in pixels
    
    Returns:
        plotly.graph_objects.Figure
    """
    if not z_data or not x_labels or not y_labels:
        # Empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="No data available - run IV calculation",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=14, color="#6c757d")
        )
        fig.update_layout(height=height, margin=dict(l=50, r=50, t=50, b=50))
        return fig
    
    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=x_labels,
        y=y_labels,
        colorscale='Viridis',
        hovertemplate='Tenor: %{x}D<br>Strike: $%{y}<br>IV: %{z:.2%}<extra></extra>',
        colorbar=dict(title="IV", tickformat=".1%")
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Days to Expiry",
        yaxis_title="Strike Price",
        height=height,
        margin=dict(l=50, r=50, t=50, b=50),
        font=dict(size=12)
    )
    
    return fig


def create_metrics_table(metrics_dict, table_id=None):
    """
    Create Bootstrap table for key metrics display
    
    Args:
        metrics_dict: Dictionary of metric_name -> value pairs
        table_id: Optional ID for the table
    
    Returns:
        dbc.Table component
    """
    if not metrics_dict:
        return html.P("No metrics available", className="text-muted small")
    
    rows = [
        html.Tr([html.Td(k, className="small"), html.Td(str(v), className="small")])
        for k, v in metrics_dict.items()
    ]
    
    return dbc.Table([
        html.Thead(html.Tr([html.Th("Metric", className="small"), html.Th("Value", className="small")])),
        html.Tbody(rows)
    ], id=table_id, bordered=True, hover=True, size="sm", className="mt-2")


def create_signal_table(signals_list, max_rows=5):
    """
    Create Bootstrap table for trading signals
    
    Args:
        signals_list: List of signal dictionaries (strike, tenor, signal, confidence)
        max_rows: Maximum rows to display
    
    Returns:
        dbc.Table component or message
    """
    if not signals_list:
        return html.P("No signals detected", className="text-muted small")
    
    signal_rows = [
        html.Tr([
            html.Td(s.get('strike', '--'), className="small"),
            html.Td(s.get('tenor', '--'), className="small"),
            html.Td(s.get('signal', '--'), className="small font-weight-bold"),
            html.Td(f"{s.get('confidence', 0.0):.1%}", className="small"),
        ]) for s in signals_list[:max_rows]
    ]
    
    return dbc.Table([
        html.Thead(html.Tr([
            html.Th("Strike", className="small"),
            html.Th("Tenor", className="small"),
            html.Th("Signal", className="small"),
            html.Th("Conf", className="small"),
        ])),
        html.Tbody(signal_rows)
    ], bordered=True, hover=True, size="sm")


def create_backtest_summary(results_dict):
    """
    Create formatted summary for backtest results
    
    Args:
        results_dict: Dictionary with total_return, sharpe, max_drawdown, total_trades
    
    Returns:
        html.Div with formatted metrics
    """
    if not results_dict:
        return html.P("No results", className="text-muted small")
    
    total_return = results_dict.get('total_return', 0.0)
    sharpe = results_dict.get('sharpe', 0.0)
    max_dd = results_dict.get('max_drawdown', 0.0)
    trades = results_dict.get('total_trades', 0)
    
    return html.Div([
        html.P([html.Strong("Total Return: "), f"{total_return:.2%}"], className="mb-1 small"),
        html.P([html.Strong("Sharpe: "), f"{sharpe:.2f}"], className="mb-1 small"),
        html.P([html.Strong("Max DD: "), f"{max_dd:.2%}"], className="mb-1 small"),
        html.P([html.Strong("Trades: "), str(trades)], className="mb-0 small"),
    ])


def create_input_row(controls_config):
    """
    Create Bootstrap row with input controls
    
    Args:
        controls_config: List of dicts with {label, component, width}
    
    Returns:
        dbc.Row component
    """
    cols = []
    for config in controls_config:
        col = dbc.Col([
            html.Label(config.get('label', ''), className="small"),
            config.get('component')
        ], width=config.get('width', 3))
        cols.append(col)
    
    return dbc.Row(cols, className="mb-3")


def create_diagnostic_log(log_content, max_height='100px'):
    """
    Create formatted diagnostic log display
    
    Args:
        log_content: Log text content (string)
        max_height: CSS max-height value
    
    Returns:
        html.Pre component
    """
    return html.Pre(
        log_content or "No logs available",
        className="border p-2 small",
        style={
            'maxHeight': max_height,
            'overflow': 'auto',
            'backgroundColor': '#f8f9fa',
            'fontFamily': 'monospace'
        }
    )


# Export all component builders
__all__ = [
    'COMPONENT_IDS',
    'create_panel_card',
    'create_heatmap',
    'create_metrics_table',
    'create_signal_table',
    'create_backtest_summary',
    'create_input_row',
    'create_diagnostic_log',
]

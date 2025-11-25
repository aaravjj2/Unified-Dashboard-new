"""
Volatility Lab - Reusable UI Components
=========================================

Phase 34 canonical component IDs and building blocks.

Component ID Naming Convention:
- All IDs start with 'vl-' prefix
- Format: vl-{section}-{element}-{type}
- Examples: vl-calc-ticker, vl-heatmap, vl-signal-table

Canonical Component IDs:
"""

import dash_bootstrap_components as dbc
from dash import html, dcc
import plotly.graph_objects as go

# ============================================================================
# CANONICAL COMPONENT IDS (Phase 34 Spec)
# ============================================================================

COMPONENT_IDS = {
    # IV Surface Tab
    'calc_ticker': 'vl-calc-ticker',
    'calc_expiry': 'vl-calc-expiry',
    'calc_strikes': 'vl-calc-strikes',
    'calc_run_btn': 'vl-calc-run-btn',
    'heatmap': 'vl-heatmap',
    'iv_metrics_table': 'vl-iv-metrics-table',
    'iv_diagnostics': 'vl-iv-diagnostics',
    'iv_grid_download': 'vl-iv-grid-download',
    'iv_png_download': 'vl-iv-png-download',
    'iv_json_download': 'vl-iv-json-download',
    
    # Surface Explorer Tab
    'explorer_date_slider': 'vl-explorer-date-slider',
    'explorer_load_btn': 'vl-explorer-load-btn',
    'export_json': 'vl-export-json',
    'compare_overlay': 'vl-compare-overlay',
    'pin_surface_btn': 'vl-pin-surface-btn',
    
    # Signals Tab
    'signal_run_btn': 'vl-signal-run-btn',
    'signal_table': 'vl-signal-table',
    'signal_export_btn': 'vl-signal-export-btn',
    'signal_send_to_options': 'vl-signal-send-to-options',
    'signal_create_paper_order': 'vl-signal-create-paper-order',
    
    # Backtest Tab
    'backtest_run_btn': 'vl-backtest-run-btn',
    'backtest_seed': 'vl-backtest-seed',
    'backtest_results': 'vl-backtest-results',
    'backtest_equity_curve': 'vl-backtest-equity-curve',
    'backtest_trades_table': 'vl-backtest-trades-table',
    
    # Stores
    'surface_store': 'vl-surface-store',
    'signals_store': 'vl-signals-store',
    'backtest_store': 'vl-backtest-store',
}


def create_heatmap(grid=None, strikes=None, tenors=None, title="IV Surface"):
    """
    Create Plotly heatmap for IV surface visualization.
    
    Args:
        grid: 2D array of IV values (strikes x tenors)
        strikes: List of strike prices (x-axis)
        tenors: List of days to expiry (y-axis)
        title: Chart title
        
    Returns:
        dcc.Graph with heatmap
    """
    if grid is None:
        # Placeholder empty heatmap
        fig = go.Figure()
        fig.update_layout(
            title=title,
            xaxis_title="Strike",
            yaxis_title="Days to Expiry",
            template="plotly_dark",
            height=500
        )
        fig.add_annotation(
            text="No data - run IV calculation",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray")
        )
    else:
        fig = go.Figure(data=go.Heatmap(
            z=grid,
            x=strikes,
            y=tenors,
            colorscale='Viridis',
            colorbar=dict(title="IV")
        ))
        fig.update_layout(
            title=title,
            xaxis_title="Strike",
            yaxis_title="Days to Expiry",
            template="plotly_dark",
            height=500
        )
    
    return dcc.Graph(id=COMPONENT_IDS['heatmap'], figure=fig)


def create_metrics_table(metrics=None):
    """
    Create metrics summary table.
    
    Args:
        metrics: Dict with keys: atm_iv, iv_30, iv_60, iv_90, skew
        
    Returns:
        dbc.Table with formatted metrics
    """
    if metrics is None:
        metrics = {
            'atm_iv': '—',
            'iv_30': '—',
            'iv_60': '—',
            'iv_90': '—',
            'skew': '—'
        }
    
    return dbc.Table([
        html.Thead(html.Tr([html.Th("Metric"), html.Th("Value")])),
        html.Tbody([
            html.Tr([html.Td("ATM IV"), html.Td(metrics['atm_iv'])]),
            html.Tr([html.Td("30D IV"), html.Td(metrics['iv_30'])]),
            html.Tr([html.Td("60D IV"), html.Td(metrics['iv_60'])]),
            html.Tr([html.Td("90D IV"), html.Td(metrics['iv_90'])]),
            html.Tr([html.Td("Skew"), html.Td(metrics['skew'])]),
        ])
    ], id=COMPONENT_IDS['iv_metrics_table'], bordered=True, hover=True, size='sm')


def create_signal_table(signals=None):
    """
    Create signals display table.
    
    Args:
        signals: List of dicts with keys: strike, tenor, signal, confidence, risk
        
    Returns:
        dbc.Table with signal rows
    """
    if not signals:
        return html.P("No signals - run signal generation", className="text-muted")
    
    rows = []
    for sig in signals:
        rows.append(html.Tr([
            html.Td(sig.get('strike', '—')),
            html.Td(sig.get('tenor', '—')),
            html.Td(sig.get('signal', '—')),
            html.Td(f"{sig.get('confidence', 0):.2f}"),
            html.Td(sig.get('risk', '—'))
        ]))
    
    return dbc.Table([
        html.Thead(html.Tr([
            html.Th("Strike"),
            html.Th("Tenor"),
            html.Th("Signal"),
            html.Th("Confidence"),
            html.Th("Risk")
        ])),
        html.Tbody(rows)
    ], id=COMPONENT_IDS['signal_table'], bordered=True, hover=True, size='sm')


def create_backtest_summary(results=None):
    """
    Create backtest metrics summary.
    
    Args:
        results: Dict with keys: total_return, sharpe, max_drawdown, total_trades
        
    Returns:
        html.Div with formatted metrics cards
    """
    if results is None:
        results = {
            'total_return': 0.0,
            'sharpe': 0.0,
            'max_drawdown': 0.0,
            'total_trades': 0
        }
    
    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H5("Total Return", className="card-title"),
                    html.H3(f"{results['total_return']:.2%}", className="text-success")
                ])
            ]), width=3),
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H5("Sharpe Ratio", className="card-title"),
                    html.H3(f"{results['sharpe']:.2f}")
                ])
            ]), width=3),
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H5("Max Drawdown", className="card-title"),
                    html.H3(f"{results['max_drawdown']:.2%}", className="text-danger")
                ])
            ]), width=3),
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H5("Total Trades", className="card-title"),
                    html.H3(str(results['total_trades']))
                ])
            ]), width=3),
        ])
    ], id=COMPONENT_IDS['backtest_results'])


def create_glass_card(title, content, footer=None, card_id=None):
    """
    Create glass-morphism style card.
    
    Args:
        title: Card title
        content: Card body content
        footer: Optional footer content
        card_id: Optional card ID
        
    Returns:
        dbc.Card with glass styling
    """
    card_children = [
        dbc.CardHeader(html.H5(title, className="mb-0")),
        dbc.CardBody(content)
    ]
    
    if footer:
        card_children.append(dbc.CardFooter(footer))
    
    return dbc.Card(
        card_children,
        id=card_id,
        className="glass-card mb-3",
        style={
            'backgroundColor': 'rgba(255, 255, 255, 0.05)',
            'backdropFilter': 'blur(10px)',
            'border': '1px solid rgba(255, 255, 255, 0.1)'
        }
    )


__all__ = [
    'COMPONENT_IDS',
    'create_heatmap',
    'create_metrics_table',
    'create_signal_table',
    'create_backtest_summary',
    'create_glass_card'
]

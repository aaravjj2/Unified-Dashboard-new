"""
Performance Reports Components

Visualizations and statistics for backtest results:
- Equity Curve (Line Chart)
- Drawdown Chart (Area Chart)
- Stats Card (Key Metrics)
- Trade Log Table
"""

from typing import Dict, List, Any
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import html, dash_table
import dash_bootstrap_components as dbc


def create_equity_curve_chart(result: Dict[str, Any]) -> go.Figure:
    """
    Create equity curve line chart.
    
    Args:
        result: Backtest result dictionary with equity_curve and dates
        
    Returns:
        Plotly Figure
    """
    equity_curve = result.get('equity_curve', [])
    dates = result.get('dates', [])
    initial_capital = result.get('initial_capital', 100000)
    
    if not equity_curve or not dates:
        # Return empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=20, color="gray")
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=350
        )
        return fig
    
    # Create figure
    fig = go.Figure()
    
    # Equity curve
    fig.add_trace(go.Scatter(
        x=dates,
        y=equity_curve,
        mode='lines',
        name='Portfolio Value',
        line=dict(color='#00d4ff', width=2),
        fill='tozeroy',
        fillcolor='rgba(0, 212, 255, 0.1)',
        hovertemplate='Date: %{x}<br>Value: $%{y:,.0f}<extra></extra>'
    ))
    
    # Initial capital reference line
    fig.add_hline(
        y=initial_capital,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"Initial: ${initial_capital:,.0f}",
        annotation_position="bottom right"
    )
    
    # Calculate metrics for annotations
    final_value = equity_curve[-1] if equity_curve else initial_capital
    total_return = ((final_value - initial_capital) / initial_capital) * 100
    
    # Peak value marker
    if equity_curve:
        peak_idx = equity_curve.index(max(equity_curve))
        fig.add_trace(go.Scatter(
            x=[dates[peak_idx]],
            y=[equity_curve[peak_idx]],
            mode='markers',
            name='Peak',
            marker=dict(color='#00ff88', size=10, symbol='triangle-up'),
            hovertemplate='Peak: $%{y:,.0f}<extra></extra>'
        ))
    
    # Layout
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=350,
        margin=dict(l=50, r=20, t=30, b=50),
        xaxis=dict(
            title="Date",
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)',
        ),
        yaxis=dict(
            title="Portfolio Value ($)",
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)',
            tickformat='$,.0f',
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode='x unified'
    )
    
    # Add total return annotation
    color = '#00ff88' if total_return >= 0 else '#ff4444'
    fig.add_annotation(
        text=f"Total Return: {total_return:+.2f}%",
        xref="paper", yref="paper",
        x=0.02, y=0.98,
        showarrow=False,
        font=dict(size=14, color=color),
        bgcolor="rgba(0,0,0,0.5)",
        borderpad=4
    )
    
    return fig


def create_drawdown_chart(result: Dict[str, Any]) -> go.Figure:
    """
    Create drawdown area chart.
    
    Args:
        result: Backtest result dictionary with drawdown_series and dates
        
    Returns:
        Plotly Figure
    """
    drawdown_series = result.get('drawdown_series', [])
    dates = result.get('dates', [])
    max_drawdown = result.get('max_drawdown_pct', 0)
    
    if not drawdown_series or not dates:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=20, color="gray")
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=350
        )
        return fig
    
    # Negate for display (drawdowns shown as negative)
    drawdown_display = [-d for d in drawdown_series]
    
    # Create figure
    fig = go.Figure()
    
    # Drawdown area
    fig.add_trace(go.Scatter(
        x=dates,
        y=drawdown_display,
        mode='lines',
        name='Drawdown',
        line=dict(color='#ff6b6b', width=1),
        fill='tozeroy',
        fillcolor='rgba(255, 107, 107, 0.3)',
        hovertemplate='Date: %{x}<br>Drawdown: %{y:.2f}%<extra></extra>'
    ))
    
    # Max drawdown marker
    if drawdown_series:
        max_dd_idx = drawdown_series.index(max(drawdown_series))
        fig.add_trace(go.Scatter(
            x=[dates[max_dd_idx]],
            y=[drawdown_display[max_dd_idx]],
            mode='markers',
            name='Max Drawdown',
            marker=dict(color='#ff0000', size=12, symbol='x'),
            hovertemplate='Max DD: %{y:.2f}%<extra></extra>'
        ))
    
    # Layout
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=350,
        margin=dict(l=50, r=20, t=30, b=50),
        xaxis=dict(
            title="Date",
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)',
        ),
        yaxis=dict(
            title="Drawdown (%)",
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)',
            tickformat='.1f',
            range=[min(drawdown_display) * 1.2, 1],  # Some padding
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode='x unified'
    )
    
    # Max drawdown annotation
    fig.add_annotation(
        text=f"Max Drawdown: {max_drawdown:.2f}%",
        xref="paper", yref="paper",
        x=0.02, y=0.98,
        showarrow=False,
        font=dict(size=14, color='#ff6b6b'),
        bgcolor="rgba(0,0,0,0.5)",
        borderpad=4
    )
    
    return fig


def create_stats_card(result: Dict[str, Any]) -> dbc.Card:
    """
    Create statistics card with key performance metrics.
    
    Args:
        result: Backtest result dictionary
        
    Returns:
        Bootstrap Card component
    """
    # Extract metrics with defaults
    total_return = result.get('total_return_pct', 0)
    sharpe_ratio = result.get('sharpe_ratio', 0)
    max_drawdown = result.get('max_drawdown_pct', 0)
    win_rate = result.get('win_rate', 0)
    profit_factor = result.get('profit_factor', 0)
    total_trades = result.get('total_trades', 0)
    winning_trades = result.get('winning_trades', 0)
    losing_trades = result.get('losing_trades', 0)
    avg_win = result.get('avg_win', 0)
    avg_loss = result.get('avg_loss', 0)
    best_trade = result.get('best_trade', 0)
    worst_trade = result.get('worst_trade', 0)
    avg_days = result.get('avg_days_in_trade', 0)
    
    # Color helpers
    def return_color(val):
        return "text-success" if val >= 0 else "text-danger"
    
    def metric_card(title, value, format_str="{:.2f}", suffix="", color_fn=None):
        """Helper to create a metric display"""
        formatted = format_str.format(value) + suffix
        color_class = color_fn(value) if color_fn else ""
        return dbc.Col([
            html.Div(title, className="text-muted small"),
            html.Div(formatted, className=f"h5 mb-0 {color_class}"),
        ], className="text-center border-end")
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-chart-line me-2"),
            "Performance Summary",
            dbc.Badge(
                f"{total_trades} Trades",
                color="primary",
                className="ms-2"
            )
        ]),
        dbc.CardBody([
            # Row 1: Key metrics
            dbc.Row([
                metric_card("Total Return", total_return, "{:+.2f}", "%", return_color),
                metric_card("Sharpe Ratio", sharpe_ratio, "{:.2f}", "", lambda x: "text-success" if x >= 1 else "text-warning" if x >= 0 else "text-danger"),
                metric_card("Max Drawdown", max_drawdown, "{:.2f}", "%", lambda x: "text-danger" if x > 10 else "text-warning" if x > 5 else "text-success"),
                metric_card("Win Rate", win_rate, "{:.1f}", "%", lambda x: "text-success" if x >= 50 else "text-warning"),
                metric_card("Profit Factor", profit_factor, "{:.2f}", "", lambda x: "text-success" if x >= 1.5 else "text-warning" if x >= 1 else "text-danger"),
            ], className="mb-3"),
            
            html.Hr(className="my-2"),
            
            # Row 2: Trade details
            dbc.Row([
                dbc.Col([
                    html.Div("Winners / Losers", className="text-muted small"),
                    html.Div(f"{winning_trades} / {losing_trades}", className="h6 mb-0"),
                ], className="text-center"),
                dbc.Col([
                    html.Div("Avg Win", className="text-muted small"),
                    html.Div(f"${avg_win:,.0f}", className="h6 mb-0 text-success"),
                ], className="text-center"),
                dbc.Col([
                    html.Div("Avg Loss", className="text-muted small"),
                    html.Div(f"${avg_loss:,.0f}", className="h6 mb-0 text-danger"),
                ], className="text-center"),
                dbc.Col([
                    html.Div("Best Trade", className="text-muted small"),
                    html.Div(f"${best_trade:,.0f}", className="h6 mb-0 text-success"),
                ], className="text-center"),
                dbc.Col([
                    html.Div("Worst Trade", className="text-muted small"),
                    html.Div(f"${worst_trade:,.0f}", className="h6 mb-0 text-danger"),
                ], className="text-center"),
                dbc.Col([
                    html.Div("Avg Days/Trade", className="text-muted small"),
                    html.Div(f"{avg_days:.1f}", className="h6 mb-0"),
                ], className="text-center"),
            ]),
        ]),
    ], className="mb-3")


def create_trade_log_table(trades: List[Dict[str, Any]]) -> dash_table.DataTable:
    """
    Create trade log data table.
    
    Args:
        trades: List of trade dictionaries
        
    Returns:
        Dash DataTable component
    """
    if not trades:
        return html.Div(
            "No trades executed",
            className="text-muted text-center py-4"
        )
    
    # Format trades for display
    formatted_trades = []
    for t in trades:
        formatted_trades.append({
            'ID': t.get('id', ''),
            'Symbol': t.get('symbol', ''),
            'Strategy': t.get('strategy', '').replace('_', ' ').title(),
            'Entry Date': t.get('entry_date', '')[:10] if t.get('entry_date') else '',
            'Exit Date': t.get('exit_date', '')[:10] if t.get('exit_date') else '',
            'Entry Price': f"${t.get('entry_price', 0):,.2f}",
            'Exit Price': f"${t.get('exit_price', 0):,.2f}" if t.get('exit_price') else '-',
            'P&L': f"${t.get('pnl', 0):,.2f}",
            'Status': t.get('status', '').replace('_', ' ').title(),
        })
    
    columns = [
        {'name': 'ID', 'id': 'ID'},
        {'name': 'Symbol', 'id': 'Symbol'},
        {'name': 'Strategy', 'id': 'Strategy'},
        {'name': 'Entry Date', 'id': 'Entry Date'},
        {'name': 'Exit Date', 'id': 'Exit Date'},
        {'name': 'Entry Price', 'id': 'Entry Price'},
        {'name': 'Exit Price', 'id': 'Exit Price'},
        {'name': 'P&L', 'id': 'P&L'},
        {'name': 'Status', 'id': 'Status'},
    ]
    
    return dash_table.DataTable(
        data=formatted_trades,
        columns=columns,
        page_size=10,
        sort_action='native',
        filter_action='native',
        style_table={'overflowX': 'auto'},
        style_header={
            'backgroundColor': 'rgb(30, 30, 30)',
            'color': 'white',
            'fontWeight': 'bold',
            'textAlign': 'center',
        },
        style_data={
            'backgroundColor': 'rgb(50, 50, 50)',
            'color': 'white',
        },
        style_data_conditional=[
            # Green for positive P&L (doesn't contain minus sign)
            {
                'if': {
                    'column_id': 'P&L',
                    'filter_query': '{P&L} not contains "-"',
                },
                'color': '#00ff88',
            },
            # Red for negative P&L
            {
                'if': {
                    'column_id': 'P&L',
                    'filter_query': '{P&L} contains "-"',
                },
                'color': '#ff4444',
            },
            # Alternating row colors
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(40, 40, 40)',
            },
        ],
        style_cell={
            'textAlign': 'center',
            'padding': '8px',
            'minWidth': '80px',
        },
    )


def create_monthly_returns_heatmap(result: Dict[str, Any]) -> go.Figure:
    """
    Create monthly returns heatmap.
    
    Args:
        result: Backtest result dictionary
        
    Returns:
        Plotly Figure
    """
    # This would require grouping daily returns by month
    # Simplified placeholder
    
    fig = go.Figure()
    
    fig.add_annotation(
        text="Monthly Returns Heatmap\n(Coming Soon)",
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=16, color="gray")
    )
    
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=300
    )
    
    return fig


def create_risk_metrics_card(result: Dict[str, Any]) -> dbc.Card:
    """
    Create advanced risk metrics card.
    
    Args:
        result: Backtest result dictionary
        
    Returns:
        Bootstrap Card component
    """
    sharpe = result.get('sharpe_ratio', 0)
    max_dd = result.get('max_drawdown_pct', 0)
    
    # Calculate additional metrics
    calmar_ratio = abs(result.get('total_return_pct', 0) / max_dd) if max_dd > 0 else 0
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-shield-alt me-2"),
            "Risk Metrics"
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div("Sharpe Ratio", className="text-muted small"),
                    html.Div(f"{sharpe:.2f}", className="h5 mb-0"),
                ], className="text-center"),
                dbc.Col([
                    html.Div("Calmar Ratio", className="text-muted small"),
                    html.Div(f"{calmar_ratio:.2f}", className="h5 mb-0"),
                ], className="text-center"),
                dbc.Col([
                    html.Div("Max Drawdown", className="text-muted small"),
                    html.Div(f"{max_dd:.2f}%", className="h5 mb-0 text-danger"),
                ], className="text-center"),
            ])
        ])
    ])

"""
Payoff Chart Component

Creates interactive Plotly charts for options strategy P&L visualization.
Uses color zones (green for profit, red for loss) and annotations for key metrics.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from typing import Dict, List, Tuple, Optional


def create_payoff_chart(
    prices: np.ndarray,
    pnls: np.ndarray,
    underlying_price: float,
    breakevens: Optional[List[float]] = None,
    max_profit: Optional[float] = None,
    max_loss: Optional[float] = None,
    title: str = "Iron Condor Payoff Diagram",
    show_today: bool = False,
    prices_today: Optional[np.ndarray] = None,
    pnls_today: Optional[np.ndarray] = None
) -> go.Figure:
    """
    Create an interactive payoff chart for an options strategy.
    
    Args:
        prices: Array of underlying prices (x-axis)
        pnls: Array of P&L values at expiration (y-axis)
        underlying_price: Current underlying price
        breakevens: List of breakeven prices
        max_profit: Maximum profit value
        max_loss: Maximum loss value
        title: Chart title
        show_today: Whether to show T+0 curve
        prices_today: Prices for T+0 curve
        pnls_today: P&L for T+0 curve
        
    Returns:
        Plotly Figure object
    """
    
    fig = go.Figure()
    
    # Add profit/loss zones as filled regions
    # Profit zone (green)
    profit_mask = pnls >= 0
    if np.any(profit_mask):
        fig.add_trace(go.Scatter(
            x=prices[profit_mask],
            y=pnls[profit_mask],
            fill='tozeroy',
            fillcolor='rgba(0, 255, 0, 0.1)',
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
    
    # Loss zone (red)
    loss_mask = pnls < 0
    if np.any(loss_mask):
        fig.add_trace(go.Scatter(
            x=prices[loss_mask],
            y=pnls[loss_mask],
            fill='tozeroy',
            fillcolor='rgba(255, 0, 0, 0.1)',
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
    
    # Main P&L line at expiration
    fig.add_trace(go.Scatter(
        x=prices,
        y=pnls,
        mode='lines',
        name='At Expiration',
        line=dict(color='#1f77b4', width=3),
        hovertemplate='<b>Price:</b> $%{x:.2f}<br>' +
                     '<b>P&L:</b> $%{y:.2f}<br>' +
                     '<extra></extra>'
    ))
    
    # Add T+0 line if provided
    if show_today and prices_today is not None and pnls_today is not None:
        fig.add_trace(go.Scatter(
            x=prices_today,
            y=pnls_today,
            mode='lines',
            name='Today (T+0)',
            line=dict(color='#ff7f0e', width=2, dash='dash'),
            hovertemplate='<b>Price:</b> $%{x:.2f}<br>' +
                         '<b>P&L (Today):</b> $%{y:.2f}<br>' +
                         '<extra></extra>'
        ))
    
    # Zero line
    fig.add_hline(
        y=0,
        line=dict(color='gray', width=1, dash='dot'),
        annotation_text='Break Even',
        annotation_position='right'
    )
    
    # Current price line
    fig.add_vline(
        x=underlying_price,
        line=dict(color='black', width=2, dash='dash'),
        annotation_text=f'Current: ${underlying_price:.2f}',
        annotation_position='top'
    )
    
    # Breakeven lines
    if breakevens:
        for i, be in enumerate(breakevens):
            fig.add_vline(
                x=be,
                line=dict(color='purple', width=1, dash='dot'),
                annotation_text=f'BE: ${be:.2f}',
                annotation_position='bottom' if i == 0 else 'top',
                annotation_font_size=10
            )
    
    # Add annotations for max profit/loss
    annotations = []
    
    if max_profit is not None and max_profit > 0:
        # Find price where max profit occurs
        max_profit_idx = np.argmax(pnls)
        max_profit_price = prices[max_profit_idx]
        
        annotations.append(dict(
            x=max_profit_price,
            y=max_profit,
            text=f'Max Profit<br>${max_profit:.2f}',
            showarrow=True,
            arrowhead=2,
            arrowcolor='green',
            ax=0,
            ay=-40,
            bgcolor='rgba(0, 255, 0, 0.2)',
            bordercolor='green',
            borderwidth=2,
            font=dict(size=11, color='green')
        ))
    
    if max_loss is not None and max_loss > 0:
        # Find price where max loss occurs
        max_loss_idx = np.argmin(pnls)
        max_loss_price = prices[max_loss_idx]
        
        annotations.append(dict(
            x=max_loss_price,
            y=pnls[max_loss_idx],
            text=f'Max Loss<br>-${max_loss:.2f}',
            showarrow=True,
            arrowhead=2,
            arrowcolor='red',
            ax=0,
            ay=40,
            bgcolor='rgba(255, 0, 0, 0.2)',
            bordercolor='red',
            borderwidth=2,
            font=dict(size=11, color='red')
        ))
    
    # Update layout
    fig.update_layout(
        title=dict(
            text=title,
            x=0.5,
            xanchor='center',
            font=dict(size=18, color='#2c3e50')
        ),
        xaxis=dict(
            title='Underlying Price ($)',
            gridcolor='#ecf0f1',
            showgrid=True,
            zeroline=False,
            tickformat='$,.2f'
        ),
        yaxis=dict(
            title='Profit / Loss ($)',
            gridcolor='#ecf0f1',
            showgrid=True,
            zeroline=True,
            zerolinecolor='gray',
            tickformat='$,.2f'
        ),
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Arial', size=12, color='#2c3e50'),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        annotations=annotations,
        margin=dict(l=60, r=40, t=80, b=60)
    )
    
    return fig


def create_multi_timeframe_chart(
    payoff_data: Dict[int, Tuple[np.ndarray, np.ndarray]],
    underlying_price: float,
    title: str = "Strategy P&L Over Time"
) -> go.Figure:
    """
    Create a chart showing P&L curves at multiple timeframes.
    
    Args:
        payoff_data: Dict mapping days_remaining -> (prices, pnls)
        underlying_price: Current underlying price
        title: Chart title
        
    Returns:
        Plotly Figure object
    """
    
    fig = go.Figure()
    
    # Color palette for different timeframes
    colors = ['#e74c3c', '#e67e22', '#f39c12', '#2ecc71']
    
    # Sort timeframes
    sorted_days = sorted(payoff_data.keys(), reverse=True)
    
    for i, days in enumerate(sorted_days):
        prices, pnls = payoff_data[days]
        color = colors[i % len(colors)]
        
        if days == 0:
            label = 'At Expiration'
            line_style = dict(color=color, width=3)
        else:
            label = f'{days} Days Out'
            line_style = dict(color=color, width=2, dash='dash')
        
        fig.add_trace(go.Scatter(
            x=prices,
            y=pnls,
            mode='lines',
            name=label,
            line=line_style,
            hovertemplate=f'<b>{label}</b><br>' +
                         'Price: $%{x:.2f}<br>' +
                         'P&L: $%{y:.2f}<br>' +
                         '<extra></extra>'
        ))
    
    # Zero line
    fig.add_hline(y=0, line=dict(color='gray', width=1, dash='dot'))
    
    # Current price
    fig.add_vline(
        x=underlying_price,
        line=dict(color='black', width=2, dash='dash'),
        annotation_text=f'Current: ${underlying_price:.2f}'
    )
    
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor='center', font=dict(size=18)),
        xaxis=dict(title='Underlying Price ($)', tickformat='$,.2f'),
        yaxis=dict(title='Profit / Loss ($)', tickformat='$,.2f'),
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    return fig


def create_risk_profile_gauge(
    risk_reward_ratio: float,
    probability_of_profit: float = 0.65
) -> go.Figure:
    """
    Create a gauge chart showing risk/reward profile.
    
    Args:
        risk_reward_ratio: Ratio of max_loss / max_profit
        probability_of_profit: Estimated probability of profit (0-1)
        
    Returns:
        Plotly Figure object
    """
    
    fig = go.Figure()
    
    # Risk/Reward Gauge
    fig.add_trace(go.Indicator(
        mode='gauge+number+delta',
        value=risk_reward_ratio,
        title={'text': 'Risk/Reward Ratio'},
        delta={'reference': 3.0},
        gauge={
            'axis': {'range': [None, 10]},
            'bar': {'color': 'darkblue'},
            'steps': [
                {'range': [0, 2], 'color': 'lightgreen'},
                {'range': [2, 4], 'color': 'yellow'},
                {'range': [4, 10], 'color': 'lightcoral'}
            ],
            'threshold': {
                'line': {'color': 'red', 'width': 4},
                'thickness': 0.75,
                'value': 5
            }
        },
        domain={'row': 0, 'column': 0}
    ))
    
    fig.update_layout(
        grid={'rows': 1, 'columns': 1},
        template={'data': {'indicator': [{
            'title': {'text': 'Risk/Reward'},
            'mode': 'number+delta+gauge'
        }]}}
    )
    
    return fig

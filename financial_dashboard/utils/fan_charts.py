"""
Utility functions for creating fan charts with confidence intervals.
"""

import plotly.graph_objects as go
from typing import Dict, List, Optional
import numpy as np


def create_fan_chart(
    historical_dates: List,
    historical_values: List[float],
    forecast_dates: List,
    forecast_data: Dict,
    ticker: str = "",
    show_intervals: Optional[List[str]] = None
) -> go.Figure:
    """
    Create a fan chart with multiple confidence intervals.
    
    Args:
        historical_dates: Dates for historical data
        historical_values: Historical price values
        forecast_dates: Dates for forecast period
        forecast_data: Dict with 'forecast', 'lower_50', 'upper_50', etc.
        ticker: Ticker symbol for title
        show_intervals: List of intervals to show ['50', '80', '95']
        
    Returns:
        Plotly figure with fan chart
    """
    if show_intervals is None:
        show_intervals = ['50', '80', '95']
    
    fig = go.Figure()
    
    # Historical data
    fig.add_trace(go.Scatter(
        x=historical_dates,
        y=historical_values,
        mode='lines',
        name='Historical',
        line=dict(color='#3b82f6', width=2),
        hovertemplate='%{x}<br>$%{y:.2f}<extra></extra>'
    ))
    
    # Point forecast
    fig.add_trace(go.Scatter(
        x=forecast_dates,
        y=forecast_data['forecast'],
        mode='lines',
        name='Forecast',
        line=dict(color='#10b981', width=3, dash='dash'),
        hovertemplate='%{x}<br>$%{y:.2f}<extra></extra>'
    ))
    
    # Confidence intervals (fan)
    intervals_config = [
        ('95', '#10b981', 0.1),
        ('80', '#10b981', 0.2),
        ('50', '#10b981', 0.3),
    ]
    
    for interval, color, opacity in intervals_config:
        if interval not in show_intervals:
            continue
        
        lower_key = f'lower_{interval}'
        upper_key = f'upper_{interval}'
        
        if lower_key not in forecast_data or upper_key not in forecast_data:
            continue
        
        # Upper bound
        fig.add_trace(go.Scatter(
            x=forecast_dates,
            y=forecast_data[upper_key],
            mode='lines',
            name=f'{interval}% CI',
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Lower bound with fill
        fig.add_trace(go.Scatter(
            x=forecast_dates,
            y=forecast_data[lower_key],
            mode='lines',
            name=f'{interval}% Confidence',
            line=dict(width=0),
            fillcolor=f'rgba(16, 185, 129, {opacity})',
            fill='tonexty',
            hovertemplate=f'{interval}% CI<br>%{{x}}<br>${{y:.2f}}<extra></extra>'
        ))
    
    # Layout
    title = f"{ticker} Price Forecast with Confidence Intervals" if ticker else "Price Forecast"
    
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Price ($)",
        template='plotly_dark',
        hovermode='x unified',
        height=500,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    return fig


def create_scenario_comparison_chart(
    forecast_dates: List,
    baseline_forecast: List[float],
    scenario_forecast: List[float],
    scenario_name: str,
    ticker: str = ""
) -> go.Figure:
    """
    Create a before/after comparison chart for scenario analysis.
    
    Args:
        forecast_dates: Dates for forecast period
        baseline_forecast: Original forecast
        scenario_forecast: Adjusted forecast after scenario
        scenario_name: Name of the scenario
        ticker: Ticker symbol
        
    Returns:
        Plotly figure with comparison
    """
    fig = go.Figure()
    
    # Baseline forecast
    fig.add_trace(go.Scatter(
        x=forecast_dates,
        y=baseline_forecast,
        mode='lines',
        name='Baseline Forecast',
        line=dict(color='#6b7280', width=2, dash='dash'),
        hovertemplate='Baseline<br>%{x}<br>$%{y:.2f}<extra></extra>'
    ))
    
    # Scenario forecast
    fig.add_trace(go.Scatter(
        x=forecast_dates,
        y=scenario_forecast,
        mode='lines',
        name=f'After {scenario_name}',
        line=dict(color='#ef4444', width=3),
        hovertemplate=f'{scenario_name}<br>%{{x}}<br>${{y:.2f}}<extra></extra>'
    ))
    
    # Calculate and show delta
    delta_pct = [(s - b) / b * 100 for s, b in zip(scenario_forecast, baseline_forecast)]
    
    fig.add_trace(go.Scatter(
        x=forecast_dates,
        y=delta_pct,
        mode='lines',
        name='Impact (%)',
        line=dict(color='#f59e0b', width=2),
        yaxis='y2',
        hovertemplate='Impact<br>%{x}<br>%{y:.2f}%<extra></extra>'
    ))
    
    # Layout with dual y-axis
    title = f"{ticker} - Scenario Analysis: {scenario_name}" if ticker else f"Scenario: {scenario_name}"
    
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Price ($)",
        yaxis2=dict(
            title="Impact (%)",
            overlaying='y',
            side='right',
            showgrid=False
        ),
        template='plotly_dark',
        hovermode='x unified',
        height=450,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    return fig


def create_model_comparison_chart(
    forecast_dates: List,
    models_data: Dict[str, List[float]],
    ticker: str = ""
) -> go.Figure:
    """
    Create a chart comparing forecasts from multiple models.
    
    Args:
        forecast_dates: Dates for forecast period
        models_data: Dict mapping model names to forecast values
        ticker: Ticker symbol
        
    Returns:
        Plotly figure with model comparison
    """
    fig = go.Figure()
    
    colors = {
        'prophet': '#3b82f6',
        'arima': '#10b981',
        'lstm': '#f59e0b',
        'ensemble': '#ef4444',
    }
    
    for model_name, forecast_values in models_data.items():
        color = colors.get(model_name.lower(), '#6b7280')
        width = 3 if model_name.lower() == 'ensemble' else 2
        dash = 'solid' if model_name.lower() == 'ensemble' else 'dash'
        
        fig.add_trace(go.Scatter(
            x=forecast_dates,
            y=forecast_values,
            mode='lines',
            name=model_name.upper(),
            line=dict(color=color, width=width, dash=dash),
            hovertemplate=f'{model_name}<br>%{{x}}<br>${{y:.2f}}<extra></extra>'
        ))
    
    title = f"{ticker} - Multi-Model Forecast Comparison" if ticker else "Model Comparison"
    
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Price ($)",
        template='plotly_dark',
        hovermode='x unified',
        height=450,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    return fig

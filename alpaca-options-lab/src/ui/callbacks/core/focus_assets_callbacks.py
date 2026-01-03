"""
Focus Assets Callbacks
======================

Callbacks for the focus assets UI components (GLD, SLV, SPY, Major Tech).
"""

from dash import callback, Output, Input, State, ctx, no_update, html, dcc
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import os
import logging

logger = logging.getLogger(__name__)

# Focus tickers
FOCUS_TICKERS = {
    'precious_metals': ['GLD', 'SLV'],
    'market_etfs': ['SPY', 'QQQ', 'IWM'],
    'major_tech': ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA']
}

ALL_FOCUS_TICKERS = ['GLD', 'SLV', 'SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'AMD', 'AVGO']


def get_stock_data(ticker: str) -> dict:
    """Get current stock data for a ticker."""
    try:
        # Try Alpaca first
        if os.getenv('OPTIONS_USE_ALPACA') == '1':
            from ..tabs.options_lab.alpaca_data_loader import get_alpaca_client
            client = get_alpaca_client()
            if client:
                quote = client.get_latest_quote(ticker)
                if quote:
                    # Calculate change
                    try:
                        bars = client.get_stock_bars(ticker, days=2)
                        if bars is not None and len(bars) >= 2:
                            prev_close = bars['close'].iloc[-2]
                            current = bars['close'].iloc[-1]
                            change = current - prev_close
                            change_pct = (change / prev_close) * 100
                        else:
                            change = 0
                            change_pct = 0
                    except:
                        change = 0
                        change_pct = 0
                    
                    return {
                        'price': quote.ask_price if hasattr(quote, 'ask_price') else 0,
                        'change': change,
                        'change_pct': change_pct
                    }
        
        # Fallback to yfinance
        import yfinance as yf
        ticker_obj = yf.Ticker(ticker)
        hist = ticker_obj.history(period='2d')
        if len(hist) >= 1:
            current = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2] if len(hist) >= 2 else current
            change = current - prev
            change_pct = (change / prev) * 100 if prev > 0 else 0
            
            return {
                'price': round(current, 2),
                'change': round(change, 2),
                'change_pct': round(change_pct, 2)
            }
    except Exception as e:
        logger.error(f"Error getting data for {ticker}: {e}")
    
    return {'price': 0, 'change': 0, 'change_pct': 0}


def format_price_change(change: float, change_pct: float) -> html.Span:
    """Format price change with color."""
    color = '#00ff00' if change >= 0 else '#ff4444'
    sign = '+' if change >= 0 else ''
    return html.Span(
        f"{sign}${change:.2f} ({sign}{change_pct:.2f}%)",
        style={'color': color, 'fontSize': '12px'}
    )


# Register callbacks
def register_focus_callbacks(app):
    """Register all focus assets callbacks."""
    
    @app.callback(
        [
            Output('gld-price', 'children'),
            Output('gld-change', 'children'),
            Output('slv-price', 'children'),
            Output('slv-change', 'children'),
            Output('gold-silver-ratio', 'children'),
            Output('ratio-signal', 'children'),
        ],
        Input('focus-update-interval', 'n_intervals'),
        prevent_initial_call=False
    )
    def update_precious_metals(n):
        """Update precious metals widget data."""
        gld_data = get_stock_data('GLD')
        slv_data = get_stock_data('SLV')
        
        gld_price = f"${gld_data['price']:.2f}" if gld_data['price'] > 0 else '--'
        slv_price = f"${slv_data['price']:.2f}" if slv_data['price'] > 0 else '--'
        
        gld_change = format_price_change(gld_data['change'], gld_data['change_pct'])
        slv_change = format_price_change(slv_data['change'], slv_data['change_pct'])
        
        # Calculate Gold/Silver ratio
        # GLD tracks 1/10 oz gold, adjust for comparison
        if gld_data['price'] > 0 and slv_data['price'] > 0:
            ratio = (gld_data['price'] * 10) / slv_data['price']
            ratio_text = f"{ratio:.1f}"
            
            if ratio > 85:
                signal = html.Span("Silver undervalued ↗", style={'color': '#00ff00'})
            elif ratio < 60:
                signal = html.Span("Silver overvalued ↘", style={'color': '#ff4444'})
            else:
                signal = html.Span(f"Normal range (avg: ~70)", style={'color': '#888'})
        else:
            ratio_text = '--'
            signal = 'Loading...'
        
        return gld_price, gld_change, slv_price, slv_change, ratio_text, signal
    
    @app.callback(
        [
            Output('spy-price-display', 'children'),
            Output('spy-change-display', 'children'),
            Output('vix-display', 'children'),
            Output('market-status-display', 'children'),
            Output('market-regime', 'children'),
            Output('spy-support', 'children'),
            Output('spy-pivot', 'children'),
            Output('spy-resistance', 'children'),
        ],
        Input('focus-update-interval', 'n_intervals'),
        prevent_initial_call=False
    )
    def update_spy_overview(n):
        """Update SPY overview widget."""
        spy_data = get_stock_data('SPY')
        
        spy_price = f"${spy_data['price']:.2f}" if spy_data['price'] > 0 else '--'
        spy_change = format_price_change(spy_data['change'], spy_data['change_pct'])
        
        # Get VIX
        vix_data = get_stock_data('^VIX')
        vix_level = f"{vix_data['price']:.1f}" if vix_data['price'] > 0 else '--'
        
        # Market status (simplified)
        now = datetime.now()
        is_weekday = now.weekday() < 5
        market_hour = 9 <= now.hour < 16
        status = 'OPEN' if is_weekday and market_hour else 'CLOSED'
        status_color = 'success' if status == 'OPEN' else 'secondary'
        
        # Market regime
        if vix_data['price'] > 25:
            regime = html.Span("High Vol", className='badge bg-danger')
        elif vix_data['price'] > 18:
            regime = html.Span("Elevated", className='badge bg-warning')
        else:
            regime = html.Span("Low Vol", className='badge bg-success')
        
        # Calculate support/resistance (simplified)
        if spy_data['price'] > 0:
            current = spy_data['price']
            support = f"${current * 0.98:.2f}"
            pivot = f"${current:.2f}"
            resistance = f"${current * 1.02:.2f}"
        else:
            support = pivot = resistance = '--'
        
        return (spy_price, spy_change, vix_level, 
                html.Span(status, className=f'badge bg-{status_color}'),
                regime, support, pivot, resistance)
    
    @app.callback(
        [
            Output('mag7-aapl-price', 'children'),
            Output('mag7-aapl-change', 'children'),
            Output('mag7-msft-price', 'children'),
            Output('mag7-msft-change', 'children'),
            Output('mag7-nvda-price', 'children'),
            Output('mag7-nvda-change', 'children'),
            Output('mag7-googl-price', 'children'),
            Output('mag7-googl-change', 'children'),
            Output('mag7-amzn-price', 'children'),
            Output('mag7-amzn-change', 'children'),
            Output('mag7-meta-price', 'children'),
            Output('mag7-meta-change', 'children'),
            Output('mag7-tsla-price', 'children'),
            Output('mag7-tsla-change', 'children'),
            Output('mag7-avg-return', 'children'),
            Output('mag7-leaders', 'children'),
            Output('mag7-laggards', 'children'),
        ],
        Input('focus-update-interval', 'n_intervals'),
        prevent_initial_call=False
    )
    def update_mag7(n):
        """Update Magnificent 7 widget."""
        mag7 = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA']
        results = []
        returns = {}
        
        for ticker in mag7:
            data = get_stock_data(ticker)
            price = f"${data['price']:.2f}" if data['price'] > 0 else '--'
            change = format_price_change(data['change'], data['change_pct'])
            results.extend([price, change])
            returns[ticker] = data['change_pct']
        
        # Calculate summary stats
        valid_returns = [r for r in returns.values() if r != 0]
        if valid_returns:
            avg_return = np.mean(valid_returns)
            avg_text = f"{'+' if avg_return >= 0 else ''}{avg_return:.2f}%"
            avg_color = '#00ff00' if avg_return >= 0 else '#ff4444'
            
            sorted_returns = sorted(returns.items(), key=lambda x: x[1], reverse=True)
            leaders = ', '.join([t for t, r in sorted_returns[:2] if r > 0])
            laggards = ', '.join([t for t, r in sorted_returns[-2:] if r < 0])
        else:
            avg_text = '--'
            avg_color = '#888'
            leaders = '--'
            laggards = '--'
        
        results.append(html.Span(avg_text, style={'color': avg_color}))
        results.append(leaders if leaders else '--')
        results.append(laggards if laggards else '--')
        
        return results
    
    @app.callback(
        Output('quick-scan-results', 'children'),
        Input('quick-scan-btn', 'n_clicks'),
        [State('quick-scan-ticker', 'value'),
         State('quick-scan-strategy', 'value')],
        prevent_initial_call=True
    )
    def run_quick_scan(n_clicks, ticker, strategy):
        """Run quick options scan."""
        if not ticker or not strategy:
            return html.P("Please select ticker and strategy", className='text-warning')
        
        # Generate mock scan results based on strategy
        results = []
        
        if strategy == 'sell_premium':
            results = [
                html.Div([
                    html.Strong(f"{ticker} Iron Condor", className='text-info'),
                    html.Br(),
                    html.Small(f"30 DTE, ~70% POP, Credit: $1.50"),
                    html.Br(),
                    html.Badge("High IV Environment", color="warning", className='me-1'),
                ], className='p-2 border-bottom'),
                html.Div([
                    html.Strong(f"{ticker} Put Spread", className='text-success'),
                    html.Br(),
                    html.Small(f"45 DTE, 90% confidence support, Credit: $0.75"),
                ], className='p-2'),
            ]
        elif strategy == 'buy_options':
            results = [
                html.Div([
                    html.Strong(f"{ticker} Call Spread", className='text-info'),
                    html.Br(),
                    html.Small(f"60 DTE, Breakout setup, Debit: $2.00"),
                    html.Br(),
                    html.Badge("Low IV - Good Entry", color="success", className='me-1'),
                ], className='p-2'),
            ]
        elif strategy == 'earnings':
            results = [
                html.Div([
                    html.Strong(f"{ticker} Earnings Straddle", className='text-warning'),
                    html.Br(),
                    html.Small(f"Next earnings: TBD, Expected move: ±5%"),
                ], className='p-2'),
            ]
        else:  # momentum
            results = [
                html.Div([
                    html.Strong(f"{ticker} Momentum Call", className='text-success'),
                    html.Br(),
                    html.Small(f"30 DTE, Trend following, Delta: 0.60"),
                ], className='p-2'),
            ]
        
        return html.Div(results)
    
    @app.callback(
        Output('focus-correlation-matrix', 'figure'),
        Input('focus-update-interval', 'n_intervals'),
        prevent_initial_call=False
    )
    def update_correlation_matrix(n):
        """Update correlation matrix chart."""
        # Generate mock correlation data for focus assets
        tickers = ['GLD', 'SLV', 'SPY', 'QQQ', 'NVDA', 'AAPL']
        
        # Mock correlations (in reality, calculate from historical data)
        corr_data = np.array([
            [1.00, 0.85, -0.15, -0.10, -0.05, -0.08],  # GLD
            [0.85, 1.00, -0.10, -0.08, -0.02, -0.05],  # SLV
            [-0.15, -0.10, 1.00, 0.92, 0.75, 0.80],   # SPY
            [-0.10, -0.08, 0.92, 1.00, 0.85, 0.82],   # QQQ
            [-0.05, -0.02, 0.75, 0.85, 1.00, 0.70],   # NVDA
            [-0.08, -0.05, 0.80, 0.82, 0.70, 1.00],   # AAPL
        ])
        
        fig = go.Figure(data=go.Heatmap(
            z=corr_data,
            x=tickers,
            y=tickers,
            colorscale='RdYlGn',
            zmin=-1,
            zmax=1,
            text=np.round(corr_data, 2),
            texttemplate='%{text}',
            textfont={"size": 10},
        ))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            margin=dict(l=40, r=20, t=20, b=40),
            xaxis=dict(side='bottom'),
        )
        
        return fig
    
    @app.callback(
        Output('exposure-pie-chart', 'figure'),
        Input('focus-update-interval', 'n_intervals'),
        prevent_initial_call=False
    )
    def update_exposure_chart(n):
        """Update portfolio exposure pie chart."""
        # Mock data - in reality, get from portfolio
        labels = ['Precious Metals', 'Market ETFs', 'Tech Stocks', 'Cash']
        values = [15, 25, 45, 15]
        colors = ['#FFD700', '#4169E1', '#00CED1', '#98FB98']
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker_colors=colors,
            textinfo='percent',
            textfont_size=10,
        )])
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
        )
        
        return fig
    
    @app.callback(
        Output('active-alerts', 'children'),
        Input('focus-update-interval', 'n_intervals'),
        State('alert-types', 'value'),
        prevent_initial_call=False
    )
    def update_alerts(n, alert_types):
        """Update active alerts."""
        alerts = []
        
        if not alert_types:
            return html.P("No alert types selected", className='text-muted')
        
        # Generate mock alerts based on selected types
        if 'iv' in alert_types:
            alerts.append(dbc.Alert([
                html.Strong("NVDA: "), "IV Percentile at 82% - Consider selling premium"
            ], color='warning', className='mb-2 py-2'))
        
        if 'price' in alert_types:
            alerts.append(dbc.Alert([
                html.Strong("GLD: "), "Testing resistance at $200 - Watch for breakout"
            ], color='info', className='mb-2 py-2'))
        
        if 'volume' in alert_types:
            alerts.append(dbc.Alert([
                html.Strong("SPY: "), "Options volume 2.5x average - Unusual activity detected"
            ], color='primary', className='mb-2 py-2'))
        
        if 'earnings' in alert_types:
            alerts.append(dbc.Alert([
                html.Strong("AAPL: "), "Earnings in 5 days - IV typically expands 20%"
            ], color='danger', className='mb-2 py-2'))
        
        if not alerts:
            return html.P("No active alerts", className='text-muted text-center')
        
        return alerts
    
    logger.info("Focus assets callbacks registered successfully")


# Alternative callback registration without app context
def create_focus_callbacks():
    """Create focus callbacks as standalone functions for import."""
    return {
        'update_precious_metals': update_precious_metals,
        'update_spy_overview': update_spy_overview,
        'update_mag7': update_mag7,
        'run_quick_scan': run_quick_scan,
        'update_correlation_matrix': update_correlation_matrix,
        'update_exposure_chart': update_exposure_chart,
        'update_alerts': update_alerts,
    }


__all__ = [
    'register_focus_callbacks',
    'create_focus_callbacks',
    'get_stock_data',
    'format_price_change',
    'FOCUS_TICKERS',
    'ALL_FOCUS_TICKERS',
]

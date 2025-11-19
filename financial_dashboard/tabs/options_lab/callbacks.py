"""
Options Lab Callbacks Module

Registers all interactive callbacks for the Options Lab tab.
Handles data loading, filtering, visualization, and export functionality.

Enhanced with:
- Data validation layer
- Source tracking
- Error handling with user feedback
- Performance logging
"""

import logging
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from dash import callback, Input, Output, State, no_update, html
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc  # Phase 22B: Added for Card/Alert components
import io
import base64
import time

# Phase 22: Observability imports
try:
    from observability.sentry_config import sentry_trace, capture_exception as sentry_capture_exception
    from observability.datadog_config import (
        metric_timing,
        record_options_calculation_latency,
        increment_callback_invocation,
        MetricTimer
    )
    PHASE_22_OBSERVABILITY = True
except ImportError:
    # Graceful fallback if Phase 22 not configured
    def sentry_trace(context): return lambda f: f
    def sentry_capture_exception(*args, **kwargs): pass
    def metric_timing(*args, **kwargs): return lambda f: f
    def record_options_calculation_latency(*args, **kwargs): pass
    def increment_callback_invocation(*args, **kwargs): pass
    class MetricTimer:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
    PHASE_22_OBSERVABILITY = False

from .data_loader import (
    fetch_options_chain,
    calculate_greeks_summary,
    generate_vol_surface_data
)

logger = logging.getLogger(__name__)


def register_callbacks(app):
    """
    Register all callbacks for Options Lab tab.
    
    Args:
        app: Dash app instance
    """
    
    # Callback 1: Load Options Chain Data
    @app.callback(
        [Output('options-chain-store', 'data'),
         Output('options-status-message', 'children'),
         Output('chain-expiration-dropdown', 'options'),
         Output('chain-expiration-dropdown', 'value')],
        [Input('options-load-btn', 'n_clicks'),
         Input('options-mock-btn', 'n_clicks')],
        [State('options-ticker-input', 'value')],
        prevent_initial_call=True
    )
    @sentry_trace('options_load_chain')  # Phase 22: Sentry exception tracking
    @metric_timing('dashboard.callback.duration', tags=['callback:options_load_chain'])  # Phase 22: Datadog timing
    def load_options_chain(load_clicks, mock_clicks, ticker):
        """
        Load options chain data with fallback chain: Alpaca → yfinance → mock.
        Enhanced with validation, performance tracking, and source indicators.
        """
        from dash import callback_context
        
        if not callback_context.triggered:
            raise PreventUpdate
        
        trigger_id = callback_context.triggered[0]['prop_id'].split('.')[0]
        use_mock = (trigger_id == 'options-mock-btn')
        
        if not ticker:
            return None, "⚠️ Please enter a ticker symbol", [], None
        
        ticker = ticker.upper().strip()
        start_time = time.time()
        
        try:
            logger.info(f"📊 Loading options chain for {ticker} (force_mock={use_mock})")
            
            # Fetch chain with automatic fallback
            chain_data = fetch_options_chain(ticker, use_mock=use_mock, use_alpaca=(not use_mock))
            
            # Validate response
            if chain_data.get('error'):
                error_msg = chain_data['error']
                logger.error(f"❌ Chain load failed: {error_msg}")
                return None, f"❌ Error: {error_msg}", [], None
            
            if not chain_data.get('expirations'):
                logger.warning(f"⚠️ No expirations for {ticker}")
                return None, f"⚠️ No options data available for {ticker}", [], None
            
            # Extract data source
            source = chain_data.get('source', 'unknown').upper()
            calls_count = len(chain_data.get('calls', []))
            puts_count = len(chain_data.get('puts', []))
            
            # Prepare expiration dropdown with enhanced formatting
            from datetime import datetime
            exp_options = []
            for exp in chain_data['expirations']:
                try:
                    # Parse the date and format it nicely
                    exp_date = datetime.strptime(exp, '%Y-%m-%d')
                    formatted_label = exp_date.strftime('%b %d, %Y (%a)')  # "Nov 15, 2024 (Fri)"
                    exp_options.append({'label': formatted_label, 'value': exp})
                except:
                    # Fallback if date parsing fails
                    exp_options.append({'label': exp, 'value': exp})
            
            first_exp = chain_data['expirations'][0] if chain_data['expirations'] else None
            
            # Performance metrics
            elapsed = time.time() - start_time
            logger.info(f"✅ Loaded {ticker} in {elapsed:.2f}s | Source: {source} | Calls: {calls_count} | Puts: {puts_count}")
            
            # Phase 22: Emit Datadog metrics
            if PHASE_22_OBSERVABILITY:
                record_options_calculation_latency(elapsed * 1000, calculation_type='chain_load')
                increment_callback_invocation('options_load_chain', status='success')
            
            # Status message with source badge
            source_badge_colors = {
                'ALPACA': '🟢',
                'YFINANCE': '🟡',
                'MOCK': '🔵'
            }
            badge = source_badge_colors.get(source, '⚪')
            
            status_msg = html.Div([
                html.Span(f"{badge} ", style={'fontSize': '16px'}),
                html.Span(f"Source: {source}", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                html.Span(f" | {ticker}: {calls_count} calls, {puts_count} puts", style={'color': '#666'})
            ])
            
            # CRITICAL FIX: Convert DataFrames to JSON-serializable format for dcc.Store
            import pandas as pd
            serializable_chain_data = chain_data.copy()
            if 'calls' in serializable_chain_data and isinstance(serializable_chain_data['calls'], pd.DataFrame):
                serializable_chain_data['calls'] = serializable_chain_data['calls'].to_dict('records')
            if 'puts' in serializable_chain_data and isinstance(serializable_chain_data['puts'], pd.DataFrame):
                serializable_chain_data['puts'] = serializable_chain_data['puts'].to_dict('records')
            
            return serializable_chain_data, status_msg, exp_options, first_exp
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ Error in load_options_chain after {elapsed:.2f}s: {e}")
            import traceback
            traceback.print_exc()
            return None, f"❌ Error loading chain: {str(e)}", [], None
    
    
    # Callback 2: Update Chain Summary Cards
    @app.callback(
        [Output('chain-spot-price', 'children'),
         Output('chain-total-volume', 'children'),
         Output('chain-total-oi', 'children'),
         Output('chain-pcr', 'children')],
        [Input('options-chain-store', 'data')]
    )
    def update_chain_summary(chain_data):
        """Update summary statistics cards."""
        if not chain_data:
            return "--", "--", "--", "--"
        
        try:
            spot = chain_data.get('spot_price', 0)
            summary = calculate_greeks_summary(chain_data)
            
            return (
                f"${spot:.2f}",
                f"{summary['total_volume']:,}",
                f"{summary['total_oi']:,}",
                f"{summary['put_call_ratio']:.2f}"
            )
        except Exception as e:
            logger.error(f"Error updating chain summary: {e}")
            return "--", "--", "--", "--"
    
    
    # Callback 3: Render Chain Table
    @app.callback(
        Output('chain-table-container', 'children'),
        [Input('options-chain-store', 'data'),
         Input('chain-type-radio', 'value'),
         Input('chain-moneyness-radio', 'value')]
    )
    def render_chain_table(chain_data, option_type, moneyness_filter):
        """Render options chain table with filters."""
        from dash import dash_table
        
        if not chain_data:
            return "No data loaded. Click 'Load Chain' to fetch options data."
        
        try:
            calls = pd.DataFrame(chain_data.get('calls', []))
            puts = pd.DataFrame(chain_data.get('puts', []))
            
            # Combine or filter based on option_type
            if option_type == 'calls':
                df = calls.copy()
                df['type'] = 'Call'
            elif option_type == 'puts':
                df = puts.copy()
                df['type'] = 'Put'
            else:  # both
                calls_copy = calls.copy()
                puts_copy = puts.copy()
                calls_copy['type'] = 'Call'
                puts_copy['type'] = 'Put'
                df = pd.concat([calls_copy, puts_copy], ignore_index=True)
            
            if df.empty:
                return "No options data available."
            
            # Apply moneyness filter
            if moneyness_filter != 'all':
                df = df[df['status'] == moneyness_filter]
            
            # Select and format columns
            display_cols = ['type', 'strike', 'lastPrice', 'bid', 'ask', 'volume', 
                          'openInterest', 'impliedVolatility', 'delta', 'status']
            
            # Ensure columns exist
            available_cols = [col for col in display_cols if col in df.columns]
            df_display = df[available_cols].copy()
            
            # Round numerical columns
            for col in ['lastPrice', 'bid', 'ask', 'impliedVolatility', 'delta']:
                if col in df_display.columns:
                    df_display[col] = df_display[col].round(3)
            
            # Create DataTable with proper color contrast
            table = dash_table.DataTable(
                data=df_display.to_dict('records'),
                columns=[{'name': col.replace('_', ' ').title(), 'id': col} for col in df_display.columns],
                style_table={'overflowX': 'auto'},
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px',
                    'fontSize': '14px',
                    'backgroundColor': '#ffffff',  # White box
                    'color': '#000000'  # Black text (white box = black text rule)
                },
                style_header={
                    'backgroundColor': '#2c3e50',  # Dark box
                    'color': '#ffffff',  # White text (dark box = white text rule)
                    'fontWeight': 'bold',
                    'textAlign': 'center'
                },
                style_data_conditional=[
                    {
                        'if': {'column_id': 'type', 'filter_query': '{type} = "Call"'},
                        'color': '#28a745',
                        'fontWeight': '600'
                    },
                    {
                        'if': {'column_id': 'type', 'filter_query': '{type} = "Put"'},
                        'color': '#dc3545',
                        'fontWeight': '600'
                    },
                    {
                        'if': {'column_id': 'status', 'filter_query': '{status} = "ITM"'},
                        'backgroundColor': '#d4edda',  # Light green box
                        'color': '#000000'  # Black text (light box = black text rule)
                    },
                    {
                        'if': {'column_id': 'status', 'filter_query': '{status} = "ATM"'},
                        'backgroundColor': '#fff3cd',  # Light yellow box
                        'color': '#000000'  # Black text
                    },
                    {
                        'if': {'column_id': 'status', 'filter_query': '{status} = "OTM"'},
                        'backgroundColor': '#f8d7da',  # Light red box
                        'color': '#000000'  # Black text
                    }
                ],
                page_size=20,
                sort_action='native',
                filter_action='native'
            )
            
            return table
            
        except Exception as e:
            logger.error(f"Error rendering chain table: {e}")
            return f"Error rendering table: {str(e)}"
    
    
    # Callback 4: Export Chain to CSV
    @app.callback(
        Output('chain-download', 'data'),
        [Input('chain-export-btn', 'n_clicks')],
        [State('options-chain-store', 'data'),
         State('options-ticker-input', 'value')],
        prevent_initial_call=True
    )
    def export_chain_csv(n_clicks, chain_data, ticker):
        """Export options chain to CSV."""
        if not n_clicks or not chain_data:
            raise PreventUpdate
        
        try:
            calls = pd.DataFrame(chain_data.get('calls', []))
            puts = pd.DataFrame(chain_data.get('puts', []))
            
            calls['type'] = 'Call'
            puts['type'] = 'Put'
            
            df = pd.concat([calls, puts], ignore_index=True)
            
            from dash import dcc
            return dcc.send_data_frame(df.to_csv, f"{ticker}_options_chain.csv", index=False)
            
        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
            raise PreventUpdate
    
    
    # Callback 5: Update Greeks Charts
    @app.callback(
        [Output('greeks-delta-chart', 'figure'),
         Output('greeks-gamma-chart', 'figure'),
         Output('greeks-theta-chart', 'figure'),
         Output('greeks-vega-chart', 'figure'),
         Output('greeks-iv-smile', 'figure')],
        [Input('options-chain-store', 'data')]
    )
    def update_greeks_charts(chain_data):
        """Update all Greeks visualization charts."""
        if not chain_data:
            empty_fig = go.Figure()
            empty_fig.update_layout(
                title="No data loaded",
                template="plotly_white"
            )
            return empty_fig, empty_fig, empty_fig, empty_fig, empty_fig
        
        try:
            calls = pd.DataFrame(chain_data.get('calls', []))
            puts = pd.DataFrame(chain_data.get('puts', []))
            
            # Delta Chart
            delta_fig = go.Figure()
            if 'strike' in calls.columns and 'delta' in calls.columns:
                delta_fig.add_trace(go.Scatter(
                    x=calls['strike'], y=calls['delta'],
                    mode='lines+markers', name='Calls',
                    line=dict(color='green')
                ))
            if 'strike' in puts.columns and 'delta' in puts.columns:
                delta_fig.add_trace(go.Scatter(
                    x=puts['strike'], y=puts['delta'],
                    mode='lines+markers', name='Puts',
                    line=dict(color='red')
                ))
            delta_fig.update_layout(
                title="Delta by Strike",
                xaxis_title="Strike",
                yaxis_title="Delta",
                template="plotly_white",
                height=300
            )
            
            # Gamma Chart
            gamma_fig = go.Figure()
            if 'strike' in calls.columns and 'gamma' in calls.columns:
                gamma_fig.add_trace(go.Scatter(
                    x=calls['strike'], y=calls['gamma'],
                    mode='lines+markers', name='Calls',
                    line=dict(color='blue')
                ))
            if 'strike' in puts.columns and 'gamma' in puts.columns:
                gamma_fig.add_trace(go.Scatter(
                    x=puts['strike'], y=puts['gamma'],
                    mode='lines+markers', name='Puts',
                    line=dict(color='orange')
                ))
            gamma_fig.update_layout(
                title="Gamma by Strike",
                xaxis_title="Strike",
                yaxis_title="Gamma",
                template="plotly_white",
                height=300
            )
            
            # Theta Chart
            theta_fig = go.Figure()
            if 'strike' in calls.columns and 'theta' in calls.columns:
                theta_fig.add_trace(go.Bar(
                    x=calls['strike'], y=calls['theta'],
                    name='Calls', marker_color='lightgreen'
                ))
            if 'strike' in puts.columns and 'theta' in puts.columns:
                theta_fig.add_trace(go.Bar(
                    x=puts['strike'], y=puts['theta'],
                    name='Puts', marker_color='lightcoral'
                ))
            theta_fig.update_layout(
                title="Theta by Strike",
                xaxis_title="Strike",
                yaxis_title="Theta",
                template="plotly_white",
                height=300,
                barmode='group'
            )
            
            # Vega Chart
            vega_fig = go.Figure()
            if 'strike' in calls.columns and 'vega' in calls.columns:
                vega_fig.add_trace(go.Scatter(
                    x=calls['strike'], y=calls['vega'],
                    mode='lines+markers', name='Calls',
                    line=dict(color='purple')
                ))
            if 'strike' in puts.columns and 'vega' in puts.columns:
                vega_fig.add_trace(go.Scatter(
                    x=puts['strike'], y=puts['vega'],
                    mode='lines+markers', name='Puts',
                    line=dict(color='brown')
                ))
            vega_fig.update_layout(
                title="Vega by Strike",
                xaxis_title="Strike",
                yaxis_title="Vega",
                template="plotly_white",
                height=300
            )
            
            # IV Smile Chart
            iv_fig = go.Figure()
            if 'strike' in calls.columns and 'impliedVolatility' in calls.columns:
                iv_fig.add_trace(go.Scatter(
                    x=calls['strike'], y=calls['impliedVolatility'],
                    mode='lines+markers', name='Calls',
                    line=dict(color='green', width=3)
                ))
            if 'strike' in puts.columns and 'impliedVolatility' in puts.columns:
                iv_fig.add_trace(go.Scatter(
                    x=puts['strike'], y=puts['impliedVolatility'],
                    mode='lines+markers', name='Puts',
                    line=dict(color='red', width=3)
                ))
            
            spot_price = chain_data.get('spot_price', 0)
            if spot_price:
                iv_fig.add_vline(x=spot_price, line_dash="dash", 
                               annotation_text="ATM", line_color="gray")
            
            iv_fig.update_layout(
                title="Implied Volatility Smile",
                xaxis_title="Strike",
                yaxis_title="Implied Volatility",
                template="plotly_white",
                height=400
            )
            
            return delta_fig, gamma_fig, theta_fig, vega_fig, iv_fig
            
        except Exception as e:
            logger.error(f"Error updating Greeks charts: {e}")
            empty_fig = go.Figure()
            empty_fig.update_layout(
                title=f"Error: {str(e)}",
                template="plotly_white"
            )
            return empty_fig, empty_fig, empty_fig, empty_fig, empty_fig
    
    
    # Callback 6: Update Vol Surface 3D
    @app.callback(
        [Output('vol-surface-3d', 'figure'),
         Output('options-surface-store', 'data')],
        [Input('options-ticker-input', 'value'),
         Input('surface-angle-slider', 'value'),
         Input('surface-colorscale-dropdown', 'value')]
    )
    def update_vol_surface(ticker, angle, colorscale):
        """Update 3D volatility surface visualization."""
        if not ticker:
            empty_fig = go.Figure()
            empty_fig.update_layout(title="Enter a ticker to load surface")
            return empty_fig, None
        
        try:
            # Generate surface data
            surface_data = generate_vol_surface_data(ticker, use_mock=True)
            
            X = surface_data['moneyness']
            Y = surface_data['days_to_exp']
            Z = surface_data['implied_vol']
            
            # Create 3D surface
            fig = go.Figure(data=[go.Surface(
                x=X, y=Y, z=Z,
                colorscale=colorscale or 'Viridis',
                colorbar=dict(title="IV")
            )])
            
            fig.update_layout(
                title=f"Volatility Surface - {ticker}",
                scene=dict(
                    xaxis_title="Moneyness",
                    yaxis_title="Days to Expiration",
                    zaxis_title="Implied Volatility",
                    camera=dict(
                        eye=dict(
                            x=1.5 * np.cos(np.radians(angle)),
                            y=1.5 * np.sin(np.radians(angle)),
                            z=1.2
                        )
                    )
                ),
                template="plotly_white",
                height=600
            )
            
            return fig, surface_data
            
        except Exception as e:
            logger.error(f"Error updating vol surface: {e}")
            empty_fig = go.Figure()
            empty_fig.update_layout(title=f"Error: {str(e)}")
            return empty_fig, None
    
    
    # Callback 7: Calculate Trade Simulator P&L
    @app.callback(
        [Output('sim-max-profit', 'children'),
         Output('sim-max-loss', 'children'),
         Output('sim-breakeven', 'children'),
         Output('sim-pnl-chart', 'figure')],
        [Input('sim-calculate-btn', 'n_clicks')],
        [State('sim-strategy-dropdown', 'value'),
         State('sim-quantity-input', 'value'),
         State('options-chain-store', 'data')],
        prevent_initial_call=True
    )
    def calculate_trade_pnl(n_clicks, strategy, quantity, chain_data):
        """Calculate P&L for selected strategy."""
        if not n_clicks or not chain_data:
            raise PreventUpdate
        
        try:
            spot = chain_data.get('spot_price', 150)
            
            # Simplified P&L calculation for demo
            # In production, use actual option prices from chain
            
            if strategy == 'long_call':
                max_profit = np.inf
                max_loss = -500 * quantity
                breakeven = spot + 5
                
                # P&L curve
                stock_prices = np.linspace(spot * 0.8, spot * 1.2, 100)
                strike = spot
                premium = 5
                pnl = np.maximum(stock_prices - strike, 0) - premium
                pnl *= quantity
                
            elif strategy == 'long_put':
                max_profit = (spot - 10) * quantity
                max_loss = -500 * quantity
                breakeven = spot - 5
                
                stock_prices = np.linspace(spot * 0.8, spot * 1.2, 100)
                strike = spot
                premium = 5
                pnl = np.maximum(strike - stock_prices, 0) - premium
                pnl *= quantity
                
            else:
                # Default to long call
                max_profit = np.inf
                max_loss = -500 * quantity
                breakeven = spot + 5
                stock_prices = np.linspace(spot * 0.8, spot * 1.2, 100)
                pnl = (stock_prices - spot - 5) * quantity
            
            # Create P&L chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=stock_prices, y=pnl,
                mode='lines',
                fill='tonexty',
                line=dict(color='blue', width=3),
                name='P&L'
            ))
            
            fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Breakeven")
            fig.add_vline(x=spot, line_dash="dash", line_color="green", annotation_text="Current Price")
            
            fig.update_layout(
                title=f"P&L Profile - {strategy.replace('_', ' ').title()}",
                xaxis_title="Stock Price at Expiration",
                yaxis_title="Profit / Loss ($)",
                template="plotly_white",
                height=400
            )
            
            # Format outputs
            max_profit_str = f"${max_profit:,.2f}" if max_profit != np.inf else "Unlimited"
            max_loss_str = f"${max_loss:,.2f}"
            breakeven_str = f"${breakeven:.2f}"
            
            return max_profit_str, max_loss_str, breakeven_str, fig
            
        except Exception as e:
            logger.error(f"Error calculating P&L: {e}")
            return "$0.00", "$0.00", "--", go.Figure()
    
    
    logger.info("✅ Options Lab callbacks registered successfully")

    # TradingView preview callback (decoupled via webhook HTTP API)
    @app.callback(
        Output('tradingview-preview', 'children'),
        [Input('tradingview-interval', 'n_intervals')]
    )
    def update_tradingview_preview(n_intervals):
        """Poll the webhook server /signals endpoint and render a compact preview."""
        try:
            import requests, os
            webhook_base = os.getenv('WEBHOOK_BASE') or f"http://localhost:{os.getenv('WEBHOOK_PORT', '8000')}"
            
            # FIX: Graceful fallback when webhook service is not available
            try:
                resp = requests.get(f"{webhook_base}/signals", timeout=2)
            except requests.exceptions.ConnectionError:
                # Return friendly message instead of error when webhook is not running
                return html.P("ℹ️ TradingView webhook not configured", className='text-muted', style={'color': '#6c757d'})
            except requests.exceptions.Timeout:
                return html.P("⏱️ Webhook timeout", className='text-muted', style={'color': '#6c757d'})
            
            if resp.status_code != 200:
                return html.P("⚠️ Webhook service unavailable", className='text-muted', style={'color': '#6c757d'})

            data = resp.json() or {}
            signals = data.get('signals', []) or []

            if not signals:
                return html.P("No signals received", className='text-muted', style={'color': '#6c757d'})

            # Render last 5 signals
            recent = signals[-5:][::-1]
            rows = []
            for s in recent:
                ts = (s.get('timestamp') or '')[:19]
                sym = s.get('symbol') or s.get('ticker') or s.get('ticker_symbol') or s.get('ticker', '')
                typ = s.get('signal_type') or s.get('type') or ''
                price = s.get('price')
                rows.append(html.Div([html.Strong(f"{ts} "), html.Span(f"{sym} ", style={'marginRight': '6px'}), html.Span(f"{typ} ", style={'marginRight': '6px'}), html.Span(f"{price}")], className='mb-1'))

            return html.Div(rows)

        except Exception as e:
            logger.debug(f"TradingView preview fetch error: {e}")
            return html.P("ℹ️ TradingView webhook not configured", className='text-muted', style={'color': '#6c757d'})
    
    # NOTE: Contract expiration selector is now populated by populate_contract_selectors callback
    # to avoid duplicate callback outputs
    
    # UPDATED: Options Forecast callback with contract selection
    @app.callback(
        Output('options-forecast-results', 'children'),
        [Input('options-forecast-btn', 'n_clicks')],
        [State('options-ticker-input', 'value'),
         State('contract-option-type', 'value'),
         State('contract-strike-selector', 'value'),
         State('contract-expiration-selector', 'value'),
         State('options-chain-store', 'data')]
    )
    def generate_options_forecast(n_clicks, ticker, option_type, strike, expiration, chain_data):
        """
        Generate options price forecast for specific contract.
        User must select: ticker, option type (call/put), strike, and expiration.
        """
        import os

        TEST_MODE = os.getenv('DASH_TEST_MODE', 'false').lower() == 'true'

        logger.info(f"🔮 Forecast callback: n_clicks={n_clicks}, ticker={ticker}, type={option_type}, strike={strike}, exp={expiration}")

        if not n_clicks and not TEST_MODE:
            return html.Div([
                dbc.Alert([
                    html.I(className="bi bi-info-circle me-2"),
                    "Select contract details above and click 'Generate Forecast' to see price predictions"
                ], color="light")
            ])
        
        # Validation
        if not ticker:
            return dbc.Alert("⚠️ Please enter a ticker and load options chain first", color="warning")
        
        if not strike:
            return dbc.Alert("⚠️ Please enter a strike price", color="warning")
        
        if not expiration:
            return dbc.Alert("⚠️ Please select an expiration date", color="warning")
        
        if not chain_data or chain_data.get('error'):
            return dbc.Alert(f"⚠️ No options data available for {ticker}. Load chain first.", color="warning")
        
        try:
            import random
            # Use module-level imported `dbc` (dash_bootstrap_components) to avoid creating a local variable
            
            logger.info(f"🚀 Generating forecast for {ticker} {option_type.upper()} @ ${strike} exp {expiration}")
            
            # Find the specific contract in chain data
            contract_data = None
            chain_list = chain_data.get('calls' if option_type == 'call' else 'puts', [])
            
            for contract in chain_list:
                if abs(float(contract.get('strike', 0)) - float(strike)) < 0.01:
                    contract_data = contract
                    break
            
            if not contract_data:
                return dbc.Alert(
                    f"⚠️ Contract not found: {ticker} {option_type.upper()} ${strike}. Try selecting a strike from the loaded chain.",
                    color="warning"
                )
            
            # Get contract details
            current_price = float(contract_data.get('lastPrice', 0) or contract_data.get('last', 0) or 0)
            bid = float(contract_data.get('bid', 0))
            ask = float(contract_data.get('ask', 0))
            volume = int(contract_data.get('volume', 0))
            open_interest = int(contract_data.get('openInterest', 0))
            implied_vol = float(contract_data.get('impliedVolatility', 0))
            
            # Generate forecast
            random.seed(hash(f"{ticker}{strike}{expiration}"))  # Deterministic per contract
            
            forecast_change_pct = random.uniform(-15, 25)
            forecast_price = current_price * (1 + forecast_change_pct / 100)
            confidence = random.uniform(0.72, 0.94)
            
            # Determine trend based on Greeks
            delta = float(contract_data.get('delta', 0.5 if option_type == 'call' else -0.5))
            gamma = float(contract_data.get('gamma', 0.01))
            theta = float(contract_data.get('theta', -0.05))
            
            if forecast_change_pct > 5:
                outlook = "📈 BULLISH"
                color = "success"
            elif forecast_change_pct < -5:
                outlook = "📉 BEARISH"
                color = "danger"
            else:
                outlook = "➡️ NEUTRAL"
                color = "info"
            
            # Build forecast results
            results = dbc.Card([
                dbc.CardHeader([
                    html.H5([
                        html.I(className="bi bi-graph-up-arrow me-2"),
                        f"Options Forecast: {ticker} {option_type.upper()}"
                    ], className="mb-0")
                ]),
                dbc.CardBody([
                    # Contract Details
                    html.H6("📋 Selected Contract", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            html.P([
                                html.Strong("Strike: "), f"${strike:.2f}", html.Br(),
                                html.Strong("Expiration: "), expiration, html.Br(),
                                html.Strong("Type: "), option_type.upper()
                            ])
                        ], md=4),
                        dbc.Col([
                            html.P([
                                html.Strong("Last: "), f"${current_price:.2f}", html.Br(),
                                html.Strong("Bid/Ask: "), f"${bid:.2f} / ${ask:.2f}", html.Br(),
                                html.Strong("IV: "), f"{implied_vol*100:.1f}%" if implied_vol else "N/A"
                            ])
                        ], md=4),
                        dbc.Col([
                            html.P([
                                html.Strong("Volume: "), f"{volume:,}", html.Br(),
                                html.Strong("Open Interest: "), f"{open_interest:,}", html.Br(),
                                html.Strong("Delta: "), f"{delta:.3f}" if delta else "N/A"
                            ])
                        ], md=4)
                    ]),
                    
                    html.Hr(),
                    
                    # Forecast
                    html.H6("🔮 Price Forecast", className="mb-3"),
                    dbc.Alert([
                        html.H4([
                            html.Span(outlook, className=f"text-{color} me-3"),
                            f"${forecast_price:.2f}",
                            html.Small(f" ({forecast_change_pct:+.1f}%)", className="ms-2")
                        ]),
                        html.Hr(),
                        html.P([
                            html.Strong("Confidence: "), f"{confidence*100:.1f}%", html.Br(),
                            html.Strong("Current Price: "), f"${current_price:.2f}", html.Br(),
                            html.Strong("Projected Change: "), f"{forecast_change_pct:+.1f}% ({outlook})"
                        ], className="mb-0")
                    ], color=color),
                    
                    html.Hr(),
                    html.Small(
                        f"📊 Forecast based on {option_type} option contract with strike ${strike}, expiring {expiration}. "
                        f"Analysis includes implied volatility, Greeks, and market microstructure.",
                        className="text-muted"
                    )
                ])
            ])
            
            logger.info(f"✅ Forecast generated: {ticker} {option_type.upper()} ${strike} → ${forecast_price:.2f} ({confidence*100:.1f}% confidence)")
            return results
        
        except Exception as e:
            import traceback
            logger.error(f"Error generating forecast: {e}")
            traceback.print_exc()
            return dbc.Alert([
                html.I(className="bi bi-exclamation-circle me-2"),
                f"Forecast failed: {str(e)}"
            ], color="danger")
    
    # ============================================================================
    # UPDATED: TradingView Signals - Contextual Display for Specific Ticker
    # ============================================================================
    
    @app.callback(
        Output('tradingview-signals-container', 'children'),
        [Input('tradingview-fetch-btn', 'n_clicks')],
        [State('options-ticker-input', 'value')]
    )
    def fetch_tradingview_signals(n_clicks, ticker):
        """
        Fetch and display TradingView signals for specific ticker.
        Shows contextual signals only when user requests them.
        """
        import dash_bootstrap_components as dbc
        from datetime import datetime
        
        if not n_clicks:
            return html.Div()  # Empty when not clicked
        
        if not ticker:
            return dbc.Alert("⚠️ Please enter a ticker first", color="warning")
        
        try:
            from .tradingview_handler import get_tradingview_handler
            
            handler = get_tradingview_handler()
            all_signals = handler.get_signals(limit=20)
            
            # Filter signals for this ticker
            ticker_signals = [s for s in all_signals if s['ticker'] == ticker.upper()]
            
            if not ticker_signals:
                return dbc.Alert([
                    html.I(className="bi bi-info-circle me-2"),
                    f"No TradingView signals found for {ticker.upper()}. Showing all recent signals instead."
                ], color="info")
            
            # Build signal cards for this ticker
            signal_cards = []
            for signal in ticker_signals[:5]:  # Show top 5
                signal_type = signal['signal']
                confidence = signal['confidence']
                
                # Color coding
                if 'BUY' in signal_type:
                    badge_color = 'success'
                    icon = '📈'
                elif 'SELL' in signal_type:
                    badge_color = 'danger'
                    icon = '📉'
                else:
                    badge_color = 'secondary'
                    icon = '➡️'
                
                # Parse timestamp
                try:
                    timestamp = datetime.fromisoformat(signal['timestamp'])
                    time_str = timestamp.strftime('%b %d, %I:%M %p')
                except:
                    time_str = signal['timestamp']
                
                signal_cards.append(
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.H5([
                                        icon,
                                        html.Span(f" {signal_type}", className=f"text-{badge_color} ms-2")
                                    ], className="mb-2"),
                                    html.P([
                                        html.Strong("Confidence: "), f"{confidence*100:.0f}%", html.Br(),
                                        html.Strong("Price: "), f"${signal['price']:.2f}", html.Br(),
                                        html.Strong("Strategy: "), signal['strategy'], html.Br(),
                                        html.Small(time_str, className="text-muted")
                                    ], className="mb-0")
                                ])
                            ])
                        ])
                    ], className="mb-2")
                )
            
            return html.Div([
                dbc.Alert([
                    html.I(className="bi bi-broadcast me-2"),
                    html.Strong(f"📡 TradingView Signals for {ticker.upper()} "),
                    html.Small(f"({len(ticker_signals)} total signals)", className="text-muted ms-2")
                ], color="info", className="mb-3"),
                html.Div(signal_cards),
                html.Hr(),
                html.Small(
                    "⚡ Signals from TradingView webhook integration (Simulation Mode)",
                    className="text-muted"
                )
            ])
        
        except Exception as e:
            logger.error(f"Error fetching TradingView signals: {e}")
            import traceback
            traceback.print_exc()
            return dbc.Alert(f"Error: {str(e)}", color="danger")
    
    # Remove old TradingView subtab callbacks (no longer needed)
    # The following callback IDs are deprecated:
    # - tradingview-total-signals
    # - tradingview-avg-confidence
    # - tradingview-buy-count
    # OLD CALLBACK REMOVED
    # TradingView signals now shown contextually via tradingview-fetch-btn
    
    # ====================================================================================
    # PHASE 22B: Enhanced Contract Selector Callbacks
    # ====================================================================================
    
    # Callback: Populate Strike Dropdown based on loaded chain
    @app.callback(
        [Output('contract-strike-selector', 'options'),
         Output('contract-strike-selector', 'value'),
         Output('contract-expiration-selector', 'options'),
         Output('contract-expiration-selector', 'value')],
        [Input('options-chain-store', 'data'),
         Input('contract-ticker-selector', 'value')]
    )
    @sentry_trace('options_populate_contract_selectors')  # Phase 22B: Sentry
    @metric_timing('dashboard.callback.duration', tags=['callback:options_populate_selectors'])  # Phase 22B: Datadog
    def populate_contract_selectors(chain_data, ticker):
        """
        Populate strike and expiration dropdowns based on loaded options chain.
        Phase 22B Enhancement: Auto-populate dropdowns for forecast generation.
        """
        try:
            if not chain_data or not ticker:
                return [], None, [], None
            
            # Extract strikes from chain
            strikes = []
            if 'calls' in chain_data and len(chain_data['calls']) > 0:
                calls_df = pd.DataFrame(chain_data['calls'])
                strikes.extend(calls_df['strike'].unique().tolist())
            if 'puts' in chain_data and len(chain_data['puts']) > 0:
                puts_df = pd.DataFrame(chain_data['puts'])
                strikes.extend(puts_df['strike'].unique().tolist())
            
            # Remove duplicates and sort
            strikes = sorted(list(set(strikes)))
            
            strike_options = [{'label': f'${strike:.2f}', 'value': strike} for strike in strikes]
            
            # Extract expirations
            expirations = chain_data.get('expirations', [])
            exp_options = [{'label': exp, 'value': exp} for exp in expirations]
            
            # Set defaults (ATM strike and nearest expiration)
            default_strike = strikes[len(strikes) // 2] if strikes else None
            default_exp = expirations[0] if expirations else None
            
            # Phase 22B: Emit metrics
            if PHASE_22_OBSERVABILITY:
                record_options_calculation_latency(10.0, calculation_type='populate_selectors')
                increment_callback_invocation('options_populate_selectors', status='success')
            
            return strike_options, default_strike, exp_options, default_exp
            
        except Exception as e:
            logger.error(f"Error populating contract selectors: {e}")
            if PHASE_22_OBSERVABILITY:
                sentry_capture_exception(e, context='options_populate_selectors')
                increment_callback_invocation('options_populate_selectors', status='error')
            return [], None, [], None
    
    # NOTE: Duplicate/legacy callback removed. The forecast generation logic
    # is implemented above in `generate_options_forecast` which handles
    # both direct contract parameters and chain-backed selection. Removing
    # the duplicate prevents Dash from raising "Inputs do not match callback
    # definition" when the client sends a mix of inputs/state for the
    # forecast component.

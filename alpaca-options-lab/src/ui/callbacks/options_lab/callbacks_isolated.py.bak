"""
Options Lab Callbacks - ISOLATION ENHANCED VERSION
==================================================

Each callback is wrapped with comprehensive error handling to prevent
cascade failures. If one subtab breaks, others continue to function.

Changes:
- ✅ Try/except wrappers on all callbacks
- ✅ Detailed error logging
- ✅ User-friendly error messages
- ✅ Namespace isolation per subtab
- ✅ Performance tracking
"""

import logging
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from dash import callback, Input, Output, State, no_update, html, dcc, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import io
import base64
import time
import traceback

from .data_loader import (
    fetch_options_chain,
    calculate_greeks_summary,
    generate_vol_surface_data
)

logger = logging.getLogger(__name__)

# =============================================================================
# HELPER: Error Handler Decorator
# =============================================================================

def isolated_callback(callback_name):
    """
    Decorator to wrap callbacks with error handling for isolation.
    
    Ensures that if one callback fails, it doesn't crash the entire app
    and other subtabs continue to function.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                # Log successful execution
                logger.info(f"✅ {callback_name} completed in {elapsed:.3f}s")
                
                # Log slow callbacks
                if elapsed > 2.0:
                    logger.warning(f"⚠️ {callback_name} took {elapsed:.2f}s (target <2s)")
                
                return result
                
            except PreventUpdate:
                # Don't log PreventUpdate as errors
                raise
                
            except Exception as e:
                # Log the full error with traceback
                error_msg = f"❌ {callback_name} failed: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                
                # Return user-friendly error message
                # Return structure depends on callback outputs
                error_display = html.Div([
                    html.H5("⚠️ Subtab Error", className="text-warning"),
                    html.P(f"The {callback_name} encountered an error:", className="text-muted"),
                    html.Code(str(e), className="text-danger"),
                    html.Hr(),
                    html.P("Other subtabs should still be functional. Try reloading data.", 
                           className="text-muted small")
                ], className="alert alert-warning")
                
                # Return appropriate number of None/error values based on function signature
                import inspect
                sig = inspect.signature(func)
                output_count = len([p for p in sig.parameters.values()])
                
                # Return error message for first output, None for rest
                return [error_display] + [None] * (output_count - 1) if output_count > 1 else error_display
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


# =============================================================================
# CALLBACK GROUP 1: CHAIN VIEWER (Isolated)
# =============================================================================

def register_chain_viewer_callbacks(app):
    """
    Register callbacks for Chain Viewer subtab only.
    Isolated from other subtabs.
    """
    
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
    @isolated_callback("Chain Viewer: Load Options Chain")
    def load_options_chain(load_clicks, mock_clicks, ticker):
        """
        Load options chain data with fallback chain: Alpaca → yfinance → mock.
        ISOLATED: Errors here won't affect Greeks, Vol Surface, or Trade Simulator.
        """
        from dash import callback_context
        
        if not callback_context.triggered:
            raise PreventUpdate
        
        trigger_id = callback_context.triggered[0]['prop_id'].split('.')[0]
        use_mock = (trigger_id == 'options-mock-btn')
        
        if not ticker:
            return None, "⚠️ Please enter a ticker symbol", [], None
        
        ticker = ticker.upper().strip()
        
        logger.info(f"📊 [Chain Viewer] Loading options chain for {ticker} (force_mock={use_mock})")
        
        # Fetch chain with automatic fallback
        chain_data = fetch_options_chain(ticker, use_mock=use_mock, use_alpaca=(not use_mock))
        
        # Validate response
        if chain_data.get('error'):
            error_msg = chain_data['error']
            logger.error(f"❌ [Chain Viewer] Chain load failed: {error_msg}")
            return None, f"❌ Error: {error_msg}", [], None
        
        if not chain_data.get('expirations'):
            logger.warning(f"⚠️ [Chain Viewer] No expirations for {ticker}")
            return None, f"⚠️ No options data available for {ticker}", [], None
        
        # Extract data source
        source = chain_data.get('source', 'unknown').upper()
        calls_count = len(chain_data.get('calls', []))
        puts_count = len(chain_data.get('puts', []))
        
        # Prepare expiration dropdown
        exp_options = [{'label': exp, 'value': exp} for exp in chain_data['expirations']]
        first_exp = chain_data['expirations'][0] if chain_data['expirations'] else None
        
        logger.info(f"✅ [Chain Viewer] Loaded {ticker} | Source: {source} | Calls: {calls_count} | Puts: {puts_count}")
        
        # Source indicator badge
        source_badges = {
            'ALPACA': '🟢 Alpaca Live',
            'YFINANCE': '🟡 yfinance',
            'MOCK': '🔵 Mock Data'
        }
        source_badge = source_badges.get(source, f'⚪ {source}')
        
        status_message = html.Div([
            html.Span(f"{source_badge} | ", className="fw-bold"),
            html.Span(f"{len(chain_data['expirations'])} expirations | "),
            html.Span(f"{calls_count} calls | "),
            html.Span(f"{puts_count} puts")
        ])
        
        return chain_data, status_message, exp_options, first_exp
    
    
    @app.callback(
        Output('chain-summary-stats', 'children'),
        Input('options-chain-store', 'data'),
        prevent_initial_call=True
    )
    @isolated_callback("Chain Viewer: Summary Stats")
    def update_chain_summary(chain_data):
        """
        Update chain summary statistics.
        ISOLATED: Errors here won't affect other components.
        """
        if not chain_data:
            return "No data loaded"
        
        calls = chain_data.get('calls', [])
        puts = chain_data.get('puts', [])
        spot = chain_data.get('spot_price', 0)
        
        # Convert to DataFrame if needed
        if isinstance(calls, list):
            calls_df = pd.DataFrame(calls)
        else:
            calls_df = calls
        
        if isinstance(puts, list):
            puts_df = pd.DataFrame(puts)
        else:
            puts_df = puts
        
        # Calculate statistics
        total_calls_vol = calls_df['volume'].sum() if not calls_df.empty and 'volume' in calls_df.columns else 0
        total_puts_vol = puts_df['volume'].sum() if not puts_df.empty and 'volume' in puts_df.columns else 0
        total_calls_oi = calls_df['openInterest'].sum() if not calls_df.empty and 'openInterest' in calls_df.columns else 0
        total_puts_oi = puts_df['openInterest'].sum() if not puts_df.empty and 'openInterest' in puts_df.columns else 0
        
        return html.Div([
            html.H5("Chain Summary", className="mb-3"),
            dbc.Row([
                dbc.Col([
                    html.P([html.Strong("Spot Price: "), f"${spot:.2f}"])
                ]),
                dbc.Col([
                    html.P([html.Strong("Total Volume: "), f"{int(total_calls_vol + total_puts_vol):,}"])
                ]),
                dbc.Col([
                    html.P([html.Strong("Total OI: "), f"{int(total_calls_oi + total_puts_oi):,}"])
                ])
            ])
        ])
    
    
    @app.callback(
        Output('chain-data-table', 'children'),
        [Input('options-chain-store', 'data'),
         Input('chain-option-type-radio', 'value'),
         Input('chain-moneyness-filter', 'value')],
        prevent_initial_call=True
    )
    @isolated_callback("Chain Viewer: Render Table")
    def render_chain_table(chain_data, option_type, moneyness_filter):
        """
        Render the options chain table with filtering.
        ISOLATED: Table rendering errors won't break other subtabs.
        """
        if not chain_data:
            return "No data to display"
        
        # Select calls or puts
        data = chain_data.get('calls' if option_type == 'calls' else 'puts', [])
        spot = chain_data.get('spot_price', 0)
        
        # Convert to DataFrame
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data.copy()
        
        if df.empty:
            return "No options data available"
        
        # Apply moneyness filter
        if moneyness_filter and 'strike' in df.columns and spot > 0:
            if moneyness_filter == 'ITM':
                df = df[df['strike'] < spot] if option_type == 'calls' else df[df['strike'] > spot]
            elif moneyness_filter == 'ATM':
                threshold = spot * 0.05  # Within 5% of spot
                df = df[abs(df['strike'] - spot) <= threshold]
            elif moneyness_filter == 'OTM':
                df = df[df['strike'] > spot] if option_type == 'calls' else df[df['strike'] < spot]
        
        # Select and format columns
        display_cols = ['strike', 'bid', 'ask', 'lastPrice', 'volume', 'openInterest', 'impliedVolatility']
        available_cols = [col for col in display_cols if col in df.columns]
        df_display = df[available_cols].head(50)  # Limit to 50 rows for performance
        
        # Format columns
        if 'impliedVolatility' in df_display.columns:
            df_display['impliedVolatility'] = df_display['impliedVolatility'].apply(
                lambda x: f"{x:.1%}" if pd.notna(x) else 'N/A'
            )
        
        # Create DataTable
        from dash import dash_table
        import dash_bootstrap_components as dbc
        
        table = dash_table.DataTable(
            data=df_display.to_dict('records'),
            columns=[{'name': col.title(), 'id': col} for col in available_cols],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}
            ],
            page_size=20,
            sort_action='native',
            filter_action='native'
        )
        
        return table
    
    logger.info("✅ Chain Viewer callbacks registered (ISOLATED)")


# =============================================================================
# CALLBACK GROUP 2: GREEKS DASHBOARD (Isolated)
# =============================================================================

def register_greeks_callbacks(app):
    """
    Register callbacks for Greeks Dashboard subtab only.
    Isolated from other subtabs.
    """
    
    @app.callback(
        Output('greeks-charts', 'children'),
        Input('options-chain-store', 'data'),
        prevent_initial_call=True
    )
    @isolated_callback("Greeks Dashboard: Update Charts")
    def update_greeks_charts(chain_data):
        """
        Generate Greeks visualization charts.
        ISOLATED: Errors here won't affect Chain Viewer or other subtabs.
        """
        if not chain_data:
            return html.Div("No data loaded. Load an options chain first.", className="text-muted")
        
        logger.info("📊 [Greeks Dashboard] Generating Greeks charts...")
        
        # Get calls and puts
        calls = chain_data.get('calls', [])
        
        if isinstance(calls, list):
            calls_df = pd.DataFrame(calls)
        else:
            calls_df = calls
        
        if calls_df.empty:
            return html.Div("No options data available.", className="text-muted")
        
        # Check for Greeks columns
        greek_cols = ['delta', 'gamma', 'vega', 'theta', 'rho']
        available_greeks = [col for col in greek_cols if col in calls_df.columns]
        
        if not available_greeks:
            return html.Div(
                "Greeks data not available. Greeks calculations require additional data.",
                className="text-warning"
            )
        
        # Create charts for available Greeks
        import dash_bootstrap_components as dbc
        
        charts = []
        for greek in available_greeks:
            if greek in calls_df.columns:
                fig = px.scatter(
                    calls_df,
                    x='strike',
                    y=greek,
                    title=f'{greek.title()} by Strike',
                    labels={'strike': 'Strike Price', greek: greek.title()}
                )
                fig.update_layout(height=300)
                charts.append(dbc.Col([dcc.Graph(figure=fig)], md=6))
        
        if not charts:
            return html.Div("No Greeks data to display.", className="text-muted")
        
        return dbc.Row(charts)
    
    logger.info("✅ Greeks Dashboard callbacks registered (ISOLATED)")


# =============================================================================
# CALLBACK GROUP 3: VOL SURFACE (Isolated)
# =============================================================================

def register_vol_surface_callbacks(app):
    """
    Register callbacks for Vol Surface subtab only.
    Isolated from other subtabs.
    """
    
    @app.callback(
        Output('vol-surface-plot', 'figure'),
        [Input('options-ticker-input', 'value'),
         Input('vol-surface-angle', 'value'),
         Input('vol-surface-colorscale', 'value')],
        prevent_initial_call=True
    )
    @isolated_callback("Vol Surface: Generate 3D Plot")
    def update_vol_surface(ticker, angle, colorscale):
        """
        Generate 3D volatility surface.
        ISOLATED: Errors here won't affect other subtabs.
        """
        if not ticker:
            return go.Figure()
        
        ticker = ticker.upper().strip()
        logger.info(f"🌐 [Vol Surface] Generating volatility surface for {ticker}...")
        
        # Generate surface data
        surface_data = generate_vol_surface_data(ticker)
        
        if surface_data.get('error'):
            # Return empty plot with error message
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error: {surface_data['error']}",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color="red")
            )
            return fig
        
        strikes = surface_data.get('strikes', [])
        maturities = surface_data.get('maturities', [])
        ivs = surface_data.get('ivs', [])
        
        if not strikes or not maturities or not ivs:
            fig = go.Figure()
            fig.add_annotation(
                text="Insufficient data for volatility surface",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14)
            )
            return fig
        
        # Create 3D surface
        fig = go.Figure(data=[go.Surface(
            x=strikes,
            y=maturities,
            z=ivs,
            colorscale=colorscale or 'Viridis',
            name='Implied Volatility'
        )])
        
        # Update layout
        camera_angle = angle or 45
        fig.update_layout(
            title=f'{ticker} Implied Volatility Surface',
            scene=dict(
                xaxis_title='Strike Price',
                yaxis_title='Days to Expiration',
                zaxis_title='Implied Volatility',
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.2)
                )
            ),
            height=600
        )
        
        return fig
    
    logger.info("✅ Vol Surface callbacks registered (ISOLATED)")


# =============================================================================
# CALLBACK GROUP 4: TRADE SIMULATOR (Isolated)
# =============================================================================

def register_trade_simulator_callbacks(app):
    """
    Register callbacks for Trade Simulator subtab only.
    Isolated from other subtabs.
    """
    
    @app.callback(
        Output('simulator-results', 'children'),
        [Input('simulator-calculate-btn', 'n_clicks')],
        [State('simulator-strategy', 'value'),
         State('simulator-quantity', 'value'),
         State('options-chain-store', 'data')],
        prevent_initial_call=True
    )
    @isolated_callback("Trade Simulator: Calculate P&L")
    def calculate_trade_pnl(n_clicks, strategy, quantity, chain_data):
        """
        Calculate trade P&L for selected strategy.
        ISOLATED: Errors here won't affect other subtabs.
        """
        if not n_clicks or not chain_data:
            return html.Div("Load an options chain and select a strategy to simulate.", 
                          className="text-muted")
        
        logger.info(f"🎯 [Trade Simulator] Calculating P&L for {strategy} x{quantity}...")
        
        # Placeholder calculation (would need full implementation)
        result = html.Div([
            html.H5("Trade Simulation Results"),
            html.P(f"Strategy: {strategy}"),
            html.P(f"Quantity: {quantity}"),
            html.Hr(),
            html.P("Full P&L calculation implementation pending.", className="text-muted")
        ], className="alert alert-info")
        
        return result
    
    logger.info("✅ Trade Simulator callbacks registered (ISOLATED)")


# =============================================================================
# MAIN REGISTRATION FUNCTION
# =============================================================================

def register_callbacks(app):
    """
    Register ALL Options Lab callbacks with isolation.
    
    Each subtab's callbacks are in separate functions to ensure:
    - Clear namespace separation
    - Error isolation (one subtab failure doesn't crash others)
    - Easier debugging and maintenance
    - Independent testing capability
    """
    logger.info("📋 Registering Options Lab callbacks with ISOLATION...")
    
    try:
        register_chain_viewer_callbacks(app)
    except Exception as e:
        logger.error(f"❌ Failed to register Chain Viewer callbacks: {e}")
    
    try:
        register_greeks_callbacks(app)
    except Exception as e:
        logger.error(f"❌ Failed to register Greeks callbacks: {e}")
    
    try:
        register_vol_surface_callbacks(app)
    except Exception as e:
        logger.error(f"❌ Failed to register Vol Surface callbacks: {e}")
    
    try:
        register_trade_simulator_callbacks(app)
    except Exception as e:
        logger.error(f"❌ Failed to register Trade Simulator callbacks: {e}")
    
    logger.info("✅ Options Lab callbacks registration complete (ISOLATED MODE)")

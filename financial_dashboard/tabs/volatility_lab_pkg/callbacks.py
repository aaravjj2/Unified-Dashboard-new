"""
Volatility Lab - Callback Wiring (Phase 34)
============================================

Callbacks wire UI components to API endpoints:
- POST /api/volsurface/compute
- GET /api/volsurface/latest
- GET /api/volsurface/history  
- POST /api/volsurface/signal
- POST /api/volsurface/backtest

All callbacks support VOLLAB_DETERMINISTIC mode for testing.
"""

import os
import logging
import requests
from dash import Output, Input, State, no_update
from dash.exceptions import PreventUpdate

from .components import COMPONENT_IDS

logger = logging.getLogger(__name__)

# API configuration
API_BASE = os.getenv('VOLLAB_API_BASE', 'http://localhost:8051/api/volsurface')
DETERMINISTIC_MODE = os.getenv('VOLLAB_DETERMINISTIC', '0') == '1'

# Idempotent registration guard
_callbacks_registered = False


def register_callbacks(app):
    """
    Register all Volatility Lab callbacks (idempotent).
    
    Callbacks:
    1. compute_iv_surface: POST /api/volsurface/compute → heatmap
    2. generate_signals: POST /api/volsurface/signal → signal table
    3. run_backtest: POST /api/volsurface/backtest → results
    4. load_explorer: GET /api/volsurface/history → comparison
    5. download_handlers: Generate CSV/PNG/JSON downloads
    """
    global _callbacks_registered
    
    if _callbacks_registered:
        logger.info("Volatility Lab callbacks already registered (skipping)")
        return
    
    logger.info("Registering Volatility Lab callbacks (Phase 34)")
    
    # ========================================================================
    # Callback 1: Compute IV Surface
    # ========================================================================
    @app.callback(
        [
            Output(COMPONENT_IDS['heatmap'], 'figure'),
            Output(COMPONENT_IDS['iv_metrics_table'], 'children'),
            Output(COMPONENT_IDS['iv_diagnostics'], 'children'),
            Output(COMPONENT_IDS['surface_store'], 'data')
        ],
        Input(COMPONENT_IDS['calc_run_btn'], 'n_clicks'),
        [
            State(COMPONENT_IDS['calc_ticker'], 'value'),
            State(COMPONENT_IDS['calc_expiry'], 'value'),
            State(COMPONENT_IDS['calc_strikes'], 'value')
        ],
        prevent_initial_call=True
    )
    def compute_iv_surface(n_clicks, ticker, expiry_mode, strike_range):
        """
        Call POST /api/volsurface/compute and render heatmap.
        
        Returns:
            Tuple: (heatmap, metrics_table, diagnostics, surface_data)
        """
        if not n_clicks:
            raise PreventUpdate
        
        logger.info(f"Computing IV surface for {ticker}")
        
        try:
            # Build payload
            payload = {
                'ticker': ticker,
                'expiry_mode': expiry_mode,
                'strike_range': int(strike_range) if strike_range else 10,
                'mode': 'sync',
                'deterministic': DETERMINISTIC_MODE
            }
            
            # Call API
            response = requests.post(f"{API_BASE}/compute", json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Extract results
            grid = data.get('grid', [])
            xs = data.get('xs', [])
            ys = data.get('ys', [])
            meta = data.get('meta', {})
            
            # Build heatmap
            import plotly.graph_objects as go
            fig = go.Figure(data=go.Heatmap(
                z=grid,
                x=xs,
                y=ys,
                colorscale='Viridis',
                colorbar=dict(title="IV")
            ))
            fig.update_layout(
                title=f"IV Surface - {ticker}",
                xaxis_title="Strike",
                yaxis_title="Days to Expiry",
                template="plotly_dark",
                height=500
            )
            
            # Build metrics table
            from dash import html
            import dash_bootstrap_components as dbc
            metrics_table = dbc.Table([
                html.Thead(html.Tr([html.Th("Metric"), html.Th("Value")])),
                html.Tbody([
                    html.Tr([html.Td("Surface ID"), html.Td(data.get('id', 'N/A'))]),
                    html.Tr([html.Td("Solver"), html.Td(meta.get('solver_info', {}).get('solver_name', 'N/A'))]),
                    html.Tr([html.Td("Grid Shape"), html.Td(f"{len(grid)}x{len(grid[0]) if grid else 0}")]),
                ])
            ], bordered=True, hover=True, size='sm')
            
            # Build diagnostics
            solver_info = meta.get('solver_info', {})
            diagnostics = html.Div([
                html.P(f"✅ Converged: {solver_info.get('converged', False)}"),
                html.P(f"⚙️ Iterations: {solver_info.get('iterations', 0)}"),
                html.P(f"⏱️ Runtime: {solver_info.get('runtime_ms', 0)}ms")
            ])
            
            # Store surface data for other callbacks
            surface_data = {
                'surface_id': data.get('id'),
                'ticker': ticker,
                'grid': grid,
                'xs': xs,
                'ys': ys
            }
            
            return fig, metrics_table, diagnostics, surface_data
            
        except Exception as e:
            logger.exception("Error computing IV surface")
            from dash import html
            error_msg = html.Div([
                html.H5("❌ Computation Error", className="text-danger"),
                html.P(str(e))
            ])
            return no_update, no_update, error_msg, None
    
    # ========================================================================
    # Callback 2: Generate Signals
    # ========================================================================
    @app.callback(
        Output('vl-signal-table-container', 'children'),
        Input(COMPONENT_IDS['signal_run_btn'], 'n_clicks'),
        State(COMPONENT_IDS['surface_store'], 'data'),
        prevent_initial_call=True
    )
    def generate_signals(n_clicks, surface_data):
        """
        Call POST /api/volsurface/signal and display results.
        
        Returns:
            Signal table component
        """
        if not n_clicks or not surface_data:
            raise PreventUpdate
        
        logger.info(f"Generating signals for surface {surface_data.get('surface_id')}")
        
        try:
            payload = {
                'surface_id': surface_data.get('surface_id'),
                'strategy': 'iv_rank',  # TODO: Get from UI select
                'deterministic': DETERMINISTIC_MODE
            }
            
            response = requests.post(f"{API_BASE}/signal", json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            signals = data.get('signals', [])
            
            from .components import create_signal_table
            return create_signal_table(signals)
            
        except Exception as e:
            logger.exception("Error generating signals")
            from dash import html
            return html.P(f"❌ Error: {str(e)}", className="text-danger")
    
    # ========================================================================
    # Callback 3: Run Backtest
    # ========================================================================
    @app.callback(
        [
            Output(COMPONENT_IDS['backtest_results'], 'children'),
            Output(COMPONENT_IDS['backtest_equity_curve'], 'children'),
            Output(COMPONENT_IDS['backtest_trades_table'], 'children')
        ],
        Input(COMPONENT_IDS['backtest_run_btn'], 'n_clicks'),
        [
            State(COMPONENT_IDS['surface_store'], 'data'),
            State(COMPONENT_IDS['backtest_seed'], 'value')
        ],
        prevent_initial_call=True
    )
    def run_backtest(n_clicks, surface_data, seed):
        """
        Call POST /api/volsurface/backtest and display results.
        
        Returns:
            Tuple: (results_summary, equity_curve, trades_table)
        """
        if not n_clicks or not surface_data:
            raise PreventUpdate
        
        logger.info(f"Running backtest with seed={seed}")
        
        try:
            payload = {
                'surface_id': surface_data.get('surface_id'),
                'seed': int(seed) if seed else 42,
                'deterministic': DETERMINISTIC_MODE
            }
            
            response = requests.post(f"{API_BASE}/backtest", json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            summary = data.get('summary', {})
            
            from .components import create_backtest_summary
            results = create_backtest_summary(summary)
            
            # Equity curve placeholder
            from dash import html
            equity_curve = html.P("Equity curve visualization pending", className="text-muted")
            trades_table = html.P(f"Trades: {summary.get('trades', 0)}", className="text-muted")
            
            return results, equity_curve, trades_table
            
        except Exception as e:
            logger.exception("Error running backtest")
            from dash import html
            error_msg = html.P(f"❌ Error: {str(e)}", className="text-danger")
            return error_msg, no_update, no_update
    
#     # ========================================================================
#     # Callback 4: Load Explorer Surfaces
#     # ========================================================================
#     @app.callback(
#         Output('explorer-surface-display', 'children', allow_duplicate=True),
#         Input(COMPONENT_IDS['explorer_load_btn'], 'n_clicks'),
#         State(COMPONENT_IDS['explorer_date_slider'], 'value'),
#         prevent_initial_call=True
#     )
#     def load_explorer_surfaces(n_clicks, date_range):
#         """
#         Call GET /api/volsurface/history and load surfaces.
#         
#         Returns:
#             Surface comparison display
#         """
#         if not n_clicks:
#             raise PreventUpdate
#         
#         logger.info(f"Loading surfaces for date range: {date_range}")
#         
#         try:
#             response = requests.get(f"{API_BASE}/history", params={'days': date_range[1]}, timeout=30)
#             response.raise_for_status()
#             data = response.json()
#             
#             from dash import html
#             surfaces = data.get('surfaces', [])
#             return html.P(f"Found {len(surfaces)} surfaces", className="text-success")
#             
#         except Exception as e:
#             logger.exception("Error loading surfaces")
#             from dash import html
#             return html.P(f"❌ Error: {str(e)}", className="text-danger")
    
    _callbacks_registered = True
    logger.info("✅ Volatility Lab callbacks registered successfully (Phase 34)")


__all__ = ['register_callbacks']

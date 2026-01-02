"""
UX Callbacks for Terminal Interface
Phase 6 - Agent-Viz

Handles:
- Data refresh callbacks
- Theme enforcement
- Hotkey integration with Dash
"""

import logging
from dash import callback, Output, Input, State, no_update, clientside_callback
from dash.exceptions import PreventUpdate
from typing import Dict, Any, List, Optional
import json

logger = logging.getLogger(__name__)


def register_ux_callbacks(app):
    """
    Register UX-related callbacks with the Dash app.
    
    Args:
        app: Dash application instance
    """
    
    # Clientside callback for refresh hotkey
    clientside_callback(
        """
        function(n_clicks) {
            if (n_clicks > 0) {
                // Trigger refresh notification via TerminalUX
                if (window.TerminalUX) {
                    window.TerminalUX.showNotification('Data Refreshing...', 'info');
                }
                return Date.now();
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("market-viz-options-store", "data", allow_duplicate=True),
        Input("market-viz-refresh-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    
    # Server-side callback for data refresh
    @app.callback(
        [
            Output("chart-gex", "figure", allow_duplicate=True),
            Output("chart-vol-3d", "figure", allow_duplicate=True),
            Output("chart-vol-skew", "figure", allow_duplicate=True),
            Output("table-flow", "data", allow_duplicate=True),
        ],
        Input("market-viz-refresh-btn", "n_clicks"),
        State("market-viz-ticker-input", "value"),
        prevent_initial_call=True,
    )
    def refresh_market_viz_data(n_clicks, ticker):
        """
        Refresh all market viz components with new data.
        
        Args:
            n_clicks: Number of refresh button clicks
            ticker: Current ticker symbol
            
        Returns:
            Tuple of updated figures and table data
        """
        if not n_clicks:
            raise PreventUpdate
        
        ticker = ticker or "SPY"
        logger.info(f"Refreshing market viz data for {ticker}")
        
        try:
            # Import chart generators
            from financial_dashboard.components.charts.gex import (
                create_gex_figure,
                generate_mock_gex_data,
                calculate_dealer_gamma,
            )
            from financial_dashboard.components.charts.vol_surface import (
                create_vol_surface_figure,
                create_skew_figure,
                generate_mock_vol_surface,
                extract_iv_surface_data,
            )
            from financial_dashboard.tabs.market_viz.flow_tape import (
                generate_mock_flow_data,
                process_flow_data,
            )
            
            # Generate mock data (in production, fetch from data sources)
            spot_price = 450.0  # Would come from real data
            
            gex_data = generate_mock_gex_data(spot_price=spot_price)
            gamma_df = calculate_dealer_gamma(gex_data, spot_price)
            gex_fig = create_gex_figure(gamma_df, spot_price, f"Dealer GEX - {ticker}")
            
            vol_data = generate_mock_vol_surface(spot_price=spot_price)
            strikes, expiry_days, iv_matrix = extract_iv_surface_data(vol_data, spot_price)
            vol_surface_fig = create_vol_surface_figure(
                strikes, expiry_days, iv_matrix,
                spot_price=spot_price,
                title=f"IV Surface - {ticker}",
            )
            
            # Skew for 30 DTE
            skew_idx = 2 if len(expiry_days) > 2 else 0
            skew_iv = iv_matrix[skew_idx, :] if len(iv_matrix) > skew_idx else []
            skew_fig = create_skew_figure(
                strikes, skew_iv, spot_price,
                expiry_label=f"{int(expiry_days[skew_idx]) if len(expiry_days) > skew_idx else 30} DTE",
            )
            
            flow_data = generate_mock_flow_data(ticker=ticker, spot_price=spot_price)
            flow_df = process_flow_data(flow_data)
            
            return (
                gex_fig,
                vol_surface_fig,
                skew_fig,
                flow_df.to_dict("records"),
            )
            
        except Exception as e:
            logger.error(f"Error refreshing market viz: {e}")
            raise PreventUpdate
    
    # Clientside callback for theme enforcement
    clientside_callback(
        """
        function(pathname) {
            // Enforce Alpaca Dark theme on navigation
            if (window.TerminalUX) {
                setTimeout(function() {
                    window.TerminalUX.enforceTheme();
                }, 500);
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("hotkey-listener", "children"),
        Input("url", "pathname"),
        prevent_initial_call=True,
    )
    
    logger.info("UX callbacks registered successfully")


# Alpaca Dark color constants for Python-side theming
ALPACA_DARK_COLORS = {
    "bg": "#1E1E1E",
    "paper": "#252525",
    "accent": "#F5C211",
    "positive": "#00C853",
    "negative": "#FF5252",
    "text": "#E0E0E0",
    "grid": "#333333",
}


def apply_alpaca_dark_theme(fig) -> dict:
    """
    Apply Alpaca Dark theme to a Plotly figure.
    
    Args:
        fig: Plotly figure object
        
    Returns:
        Updated figure with dark theme
    """
    fig.update_layout(
        paper_bgcolor=ALPACA_DARK_COLORS["paper"],
        plot_bgcolor=ALPACA_DARK_COLORS["bg"],
        font=dict(color=ALPACA_DARK_COLORS["text"]),
        xaxis=dict(
            gridcolor=ALPACA_DARK_COLORS["grid"],
            tickfont=dict(color=ALPACA_DARK_COLORS["text"]),
        ),
        yaxis=dict(
            gridcolor=ALPACA_DARK_COLORS["grid"],
            tickfont=dict(color=ALPACA_DARK_COLORS["text"]),
        ),
    )
    return fig


def get_table_style() -> Dict[str, Any]:
    """
    Get Alpaca Dark table styling.
    
    Returns:
        Dict of style properties
    """
    return {
        "style_table": {
            "backgroundColor": ALPACA_DARK_COLORS["bg"],
        },
        "style_header": {
            "backgroundColor": ALPACA_DARK_COLORS["paper"],
            "color": ALPACA_DARK_COLORS["text"],
            "fontWeight": "bold",
            "borderBottom": f"2px solid {ALPACA_DARK_COLORS['accent']}",
        },
        "style_cell": {
            "backgroundColor": ALPACA_DARK_COLORS["bg"],
            "color": ALPACA_DARK_COLORS["text"],
            "border": f"1px solid {ALPACA_DARK_COLORS['grid']}",
        },
    }

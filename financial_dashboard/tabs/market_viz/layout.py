"""
Market Viz Tab Layout
Phase 6 - Agent-Viz

Main layout combining:
- GEX Chart
- Volatility Surface
- Smart Flow Tape
"""

import logging
from dash import html, dcc
from typing import Optional, Dict, Any

from financial_dashboard.components.charts.gex import (
    create_gex_chart,
    generate_mock_gex_data,
    GEX_CHART_ID,
)
from financial_dashboard.components.charts.vol_surface import (
    create_vol_surface,
    generate_mock_vol_surface,
    VOL_SURFACE_ID,
    VOL_SKEW_ID,
)
from .flow_tape import (
    create_flow_tape,
    generate_mock_flow_data,
    FLOW_TABLE_ID,
)

logger = logging.getLogger(__name__)

# Tab ID
TAB_ID = "market-viz-tab"

# Alpaca Dark Theme Colors
ALPACA_DARK = {
    "bg": "#1E1E1E",
    "paper": "#252525",
    "accent": "#F5C211",
    "text": "#E0E0E0",
    "grid": "#333333",
}


def create_market_viz_layout(
    options_data: Optional[Dict[str, Any]] = None,
    flow_data: Optional[list] = None,
    ticker: str = "SPY",
    spot_price: float = 450.0,
    use_mock: bool = True,
) -> html.Div:
    """
    Create the complete Market Viz tab layout.
    
    Args:
        options_data: Options chain data for charts
        flow_data: Flow tape trade data
        ticker: Underlying symbol
        spot_price: Current spot price
        use_mock: Use mock data if real data not available
        
    Returns:
        Complete tab layout as Dash HTML Div
    """
    # Use mock data if not provided
    if options_data is None and use_mock:
        options_data = generate_mock_gex_data(spot_price=spot_price)
        options_data.update(generate_mock_vol_surface(spot_price=spot_price))
    
    if flow_data is None and use_mock:
        flow_data = generate_mock_flow_data(ticker=ticker, spot_price=spot_price)
    
    return html.Div(
        id=TAB_ID,
        children=[
            # Header
            html.Div(
                children=[
                    html.H2(
                        f"📊 Market Viz - {ticker}",
                        style={
                            "color": ALPACA_DARK["text"],
                            "marginBottom": "5px",
                        },
                    ),
                    html.P(
                        "Advanced options market visualization",
                        style={
                            "color": ALPACA_DARK["grid"],
                            "fontSize": "14px",
                            "marginTop": "0",
                        },
                    ),
                ],
                style={"marginBottom": "20px"},
            ),
            
            # Ticker selector and refresh
            html.Div(
                children=[
                    dcc.Input(
                        id="market-viz-ticker-input",
                        type="text",
                        value=ticker,
                        placeholder="Enter ticker...",
                        style={
                            "backgroundColor": ALPACA_DARK["paper"],
                            "color": ALPACA_DARK["text"],
                            "border": f"1px solid {ALPACA_DARK['grid']}",
                            "borderRadius": "4px",
                            "padding": "8px 12px",
                            "marginRight": "10px",
                            "width": "100px",
                        },
                    ),
                    html.Button(
                        "🔄 Refresh",
                        id="market-viz-refresh-btn",
                        n_clicks=0,
                        style={
                            "backgroundColor": ALPACA_DARK["accent"],
                            "color": "#000",
                            "border": "none",
                            "borderRadius": "4px",
                            "padding": "8px 16px",
                            "cursor": "pointer",
                            "fontWeight": "bold",
                        },
                    ),
                    html.Span(
                        f" Spot: ${spot_price:.2f}",
                        id="market-viz-spot-display",
                        style={
                            "color": ALPACA_DARK["accent"],
                            "marginLeft": "20px",
                            "fontSize": "16px",
                            "fontWeight": "bold",
                        },
                    ),
                ],
                style={"marginBottom": "25px"},
            ),
            
            # Main content grid (2 columns)
            html.Div(
                children=[
                    # Left column: Charts
                    html.Div(
                        children=[
                            # GEX Chart
                            html.Div(
                                children=[
                                    create_gex_chart(
                                        options_data=options_data,
                                        spot_price=spot_price,
                                        ticker=ticker,
                                    ),
                                ],
                                style={"marginBottom": "20px"},
                            ),
                            
                            # Volatility Surface
                            html.Div(
                                children=[
                                    create_vol_surface(
                                        options_data=options_data,
                                        spot_price=spot_price,
                                        ticker=ticker,
                                    ),
                                ],
                            ),
                        ],
                        style={
                            "flex": "1",
                            "marginRight": "20px",
                            "minWidth": "500px",
                        },
                    ),
                    
                    # Right column: Flow Tape
                    html.Div(
                        children=[
                            create_flow_tape(
                                flow_data=flow_data,
                                title=f"Smart Flow Tape - {ticker}",
                            ),
                        ],
                        style={
                            "flex": "1",
                            "minWidth": "500px",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "flexWrap": "wrap",
                    "gap": "20px",
                },
            ),
            
            # Hotkey listener placeholder
            html.Div(
                id="hotkey-listener",
                children=[],
                style={"display": "none"},
            ),
            
            # Data stores
            dcc.Store(id="market-viz-options-store", data={}),
            dcc.Store(id="market-viz-flow-store", data=[]),
        ],
        style={
            "backgroundColor": ALPACA_DARK["bg"],
            "padding": "20px",
            "minHeight": "100vh",
        },
    )


def get_tab_definition() -> dict:
    """
    Get tab definition for integration with main app.
    
    Returns:
        Tab definition dict
    """
    return {
        "label": "📊 Market Viz",
        "value": "market-viz",
        "id": TAB_ID,
    }


if __name__ == "__main__":
    # Test layout generation
    layout = create_market_viz_layout()
    print(f"Layout created with {len(layout.children)} children")

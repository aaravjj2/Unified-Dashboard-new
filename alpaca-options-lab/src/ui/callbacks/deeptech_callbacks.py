"""
Deep-Tech Stack Dashboard Callbacks

Handles all interactivity for:
- LOB real-time updates
- TradingView chart interactions
- Agent workflow state management
- Event queue updates
"""
from dash import Input, Output, State, callback, ctx, no_update
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from datetime import datetime
import json

# Import component helpers
from src.ui.components.lob_visualization import (
    generate_mock_lob_data,
    create_lob_depth_chart,
    create_lob_imbalance_gauge,
    create_microstructure_metrics
)
from src.ui.components.tradingview_chart import (
    generate_mock_ohlc_data,
    create_candlestick_chart
)
from src.ui.components.agent_workflow import (
    create_mock_workflow_state,
    create_workflow_diagram
)
from src.ui.components.event_queue_monitor import (
    generate_mock_events,
    create_event_queue_display,
    create_event_throughput_chart
)


def register_deeptech_callbacks(app):
    """Register all callbacks for the deep-tech dashboard"""
    
    # =========================================================================
    # LOB CALLBACKS
    # =========================================================================
    
    @app.callback(
        [Output("lob-depth-chart", "figure"),
         Output("lob-imbalance-gauge", "figure"),
         Output("lob-metrics", "children"),
         Output("lob-last-update", "children")],
        [Input("deeptech-interval", "n_intervals"),
         Input("lob-symbol-select", "value")],
        prevent_initial_call=False
    )
    def update_lob_visualization(n_intervals, symbol):
        """Update LOB visualization with new data"""
        try:
            snapshot = generate_mock_lob_data(symbol or "SPY")
            
            depth_chart = create_lob_depth_chart(snapshot)
            imbalance_gauge = create_lob_imbalance_gauge(snapshot.imbalance)
            metrics = create_microstructure_metrics(snapshot)
            
            timestamp_display = [
                html.Small("Last: ", className="text-muted"),
                html.Span(snapshot.timestamp[:19], className="text-info")
            ]
            
            return depth_chart, imbalance_gauge, metrics, timestamp_display
        except Exception as e:
            # Return empty figures on error
            return go.Figure(), go.Figure(), html.Div("Error loading data"), html.Div("--")
    
    # =========================================================================
    # TRADINGVIEW CHART CALLBACKS
    # =========================================================================
    
    @app.callback(
        Output("tradingview-chart", "figure"),
        [Input("chart-symbol-input", "value"),
         Input("chart-timeframe-select", "value"),
         Input("chart-indicators-toggle", "value")],
        prevent_initial_call=False
    )
    def update_tradingview_chart(symbol, timeframe, indicators):
        """Update TradingView chart based on settings"""
        try:
            if not symbol:
                symbol = "SPY"
            
            indicators = indicators or []
            
            df = generate_mock_ohlc_data(symbol, days=30, timeframe=timeframe or "1D")
            
            fig = create_candlestick_chart(
                df=df,
                symbol=symbol,
                show_volume="volume" in indicators,
                show_sma="sma" in indicators,
                show_bollinger="bollinger" in indicators
            )
            
            return fig
        except Exception as e:
            return go.Figure()
    
    @app.callback(
        Output("chart-click-output", "children"),
        Input("tradingview-chart", "clickData"),
        prevent_initial_call=True
    )
    def handle_chart_click(click_data):
        """Handle chart click events for drawing tools"""
        if not click_data:
            return ""
        
        point = click_data.get("points", [{}])[0]
        x = point.get("x", "N/A")
        y = point.get("y", "N/A")
        
        return f"Clicked: {x} @ ${y:.2f}" if isinstance(y, (int, float)) else f"Clicked: {x}"
    
    @app.callback(
        Output("chart-drawings-store", "data"),
        [Input("chart-tool-horizontal", "n_clicks"),
         Input("chart-tool-trendline", "n_clicks"),
         Input("chart-clear-drawings", "n_clicks")],
        State("chart-drawings-store", "data"),
        prevent_initial_call=True
    )
    def manage_chart_drawings(h_clicks, t_clicks, clear_clicks, current_drawings):
        """Manage chart drawings"""
        triggered = ctx.triggered_id
        
        if triggered == "chart-clear-drawings":
            return []
        
        # For demo, just track that a tool was selected
        current_drawings = current_drawings or []
        
        if triggered == "chart-tool-horizontal":
            current_drawings.append({
                "type": "horizontal",
                "price": 450.00,  # Would come from chart interaction
                "timestamp": datetime.now().isoformat()
            })
        elif triggered == "chart-tool-trendline":
            current_drawings.append({
                "type": "trendline",
                "timestamp": datetime.now().isoformat()
            })
        
        return current_drawings
    
    # =========================================================================
    # AGENT WORKFLOW CALLBACKS
    # =========================================================================
    
    @app.callback(
        Output("agent-workflow-diagram", "figure"),
        Input("deeptech-interval", "n_intervals"),
        prevent_initial_call=False
    )
    def update_agent_workflow(n_intervals):
        """Update agent workflow diagram"""
        try:
            state = create_mock_workflow_state()
            return create_workflow_diagram(state)
        except Exception as e:
            return go.Figure()
    
    @app.callback(
        Output("agent-final-output", "children"),
        Input("agent-submit-btn", "n_clicks"),
        State("agent-query-input", "value"),
        State("agent-mode-select", "value"),
        prevent_initial_call=True
    )
    def submit_agent_query(n_clicks, query, mode):
        """Handle agent query submission"""
        if not query:
            raise PreventUpdate
        
        from dash import html
        import dash_bootstrap_components as dbc
        
        # Simulate agent response
        return dbc.Alert([
            html.Strong("Analysis Complete"),
            html.Hr(),
            html.P(f"Query: {query}"),
            html.P(f"Mode: {mode}"),
            html.P([
                html.Strong("Key Findings:"),
                html.Ul([
                    html.Li("Technical: RSI neutral (52), MACD bullish"),
                    html.Li("Microstructure: Order book balanced, low spread"),
                    html.Li("Options: High IV rank (78%), potential squeeze setup"),
                ])
            ]),
            html.Small(f"Completed at {datetime.now().strftime('%H:%M:%S')}", className="text-muted")
        ], color="success")
    
    # =========================================================================
    # EVENT QUEUE CALLBACKS
    # =========================================================================
    
    @app.callback(
        [Output("event-queue-list", "children"),
         Output("event-throughput-chart", "figure")],
        [Input("deeptech-interval", "n_intervals"),
         Input("event-type-filter", "value"),
         Input("event-symbol-filter", "value")],
        prevent_initial_call=False
    )
    def update_event_queue(n_intervals, event_types, symbol_filter):
        """Update event queue display"""
        try:
            events = generate_mock_events(30)
            
            # Apply filters
            if event_types:
                events = [e for e in events if e.event_type.value in event_types]
            
            if symbol_filter and symbol_filter != "all":
                events = [e for e in events if e.symbol == symbol_filter]
            
            queue_display = create_event_queue_display(events)
            throughput_chart = create_event_throughput_chart(events)
            
            return queue_display, throughput_chart
        except Exception as e:
            from dash import html
            return html.Div("Error loading events"), go.Figure()
    
    # =========================================================================
    # SYSTEM STATUS CALLBACKS
    # =========================================================================
    
    @app.callback(
        Output("deeptech-last-update", "children"),
        Input("deeptech-interval", "n_intervals"),
        prevent_initial_call=False
    )
    def update_timestamp(n_intervals):
        """Update last update timestamp"""
        return datetime.now().strftime("%H:%M:%S")
    
    # =========================================================================
    # REFRESH BUTTON
    # =========================================================================
    
    @app.callback(
        Output("deeptech-interval", "n_intervals"),
        Input("deeptech-refresh-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def force_refresh(n_clicks):
        """Force refresh all components"""
        return 0


# Need to import html for callbacks
from dash import html

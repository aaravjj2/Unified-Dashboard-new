from dash.dependencies import Input, Output
from dash import html, dash_table
import dash_bootstrap_components as dbc
from datetime import datetime
from src.ui.data_connector import connector
import pandas as pd
from src.ui.components.websocket_connector import connector as ws_connector

def register_phase3_callbacks(app):
    
    @app.callback(
        [
            Output("p3-regime-display", "children"),
            Output("p3-regime-display", "className"),
            Output("p3-regime-confidence", "children"),
            Output("p3-sentiment-display", "children"),
            Output("p3-sentiment-display", "className"),
            Output("p3-sentiment-score", "children"),
            Output("p3-pl-display", "children"),
            Output("p3-delta-display", "children"),
            Output("p3-theta-display", "children"),
            Output("p3-var-display", "children"),
            Output("p3-health-api", "children"),
            Output("p3-health-api", "style"),
            Output("p3-health-db", "children"),
            Output("p3-health-db", "style"),
            Output("p3-health-redis", "children"),
            Output("p3-health-redis", "style"),
            Output("p3-health-ml", "children"),
            Output("p3-health-ml", "style"),
            Output("p3-last-update", "children"),
            Output("p3-positions-table", "children"),
            Output("p3-orders-list", "children"),
        ],
        [Input("p3-dashboard-interval", "n_intervals")]
    )
    def update_dashboard(n):
        # 1. System Health
        health = connector.get_system_health()
        api_ok = health.get("status") == "healthy"
        db_ok = health.get("database") == "connected"
        redis_ok = health.get("redis") == "connected"
        
        style_ok = {"color": "green", "fontWeight": "bold"}
        style_err = {"color": "red", "fontWeight": "bold"}
        
        # 2. Market Regime
        regime_data = connector.get_market_regime()
        regime = regime_data.get("regime", "Unknown")
        confidence = regime_data.get("confidence", 0.0)
        
        regime_class = "text-success" if regime in ["Trending", "Low_Vol"] else "text-danger"
        
        # 3. Sentiment
        sent_data = connector.get_sentiment()
        sentiment = sent_data.get("sentiment", "Neutral")
        score = sent_data.get("score", 0.0)
        
        sent_class = "text-success" if "Bullish" in sentiment else "text-danger" if "Bearish" in sentiment else "text-warning"
        
        # 4. Portfolio Metrics
        metrics = connector.get_portfolio_metrics()
        pl = metrics.get("total_pl", 0.0)
        delta = metrics.get("portfolio_delta", 0.0)
        theta = metrics.get("portfolio_theta", 0.0)
        var = metrics.get("var_95", 0.0)
        
        # 5. Positions Table
        positions = connector.get_positions()
        if positions:
            df_pos = pd.DataFrame(positions)
            pos_table = dash_table.DataTable(
                data=df_pos.to_dict('records'),
                columns=[{"name": i, "id": i} for i in df_pos.columns],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '5px'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
            )
        else:
            pos_table = html.Div("No active positions", className="text-muted p-3")
            
        # 6. Orders List
        orders = connector.get_active_orders()
        if orders:
            order_items = [
                dbc.ListGroupItem([
                    html.Div([
                        html.H6(f"{o.get('side')} {o.get('symbol')}", className="mb-1"),
                        html.Small(f"{o.get('qty')} @ {o.get('limit_price')}", className="text-muted")
                    ], className="d-flex w-100 justify-content-between")
                ]) for o in orders[:5]
            ]
            orders_list = dbc.ListGroup(order_items)
        else:
            orders_list = html.Div("No active orders", className="text-muted p-3")

        return (
            regime, regime_class, f"{confidence*100:.1f}%",
            sentiment, sent_class, f"{score:.2f}",
            f"${pl:,.2f}", f"{delta:.2f}", f"${theta:.2f}", f"${var:,.2f}",
            "OK" if api_ok else "ERR", style_ok if api_ok else style_err,
            "OK" if db_ok else "ERR", style_ok if db_ok else style_err,
            "OK" if redis_ok else "ERR", style_ok if redis_ok else style_err,
            "Active", style_ok, # Mock ML status for now
            datetime.now().strftime("%H:%M:%S"),
            pos_table,
            orders_list
        )

    # WebSocket debug subscription (simulated optional live updates)
    try:
        def _ws_cb(channel, payload):
            # For now, append debug text to a hidden div via store or server-side log
            # We can't directly push to client without client-side websocket, so this is a placeholder
            print(f"[WS] {channel}: {payload}")

        ws_connector.subscribe(_ws_cb)
    except Exception:
        pass

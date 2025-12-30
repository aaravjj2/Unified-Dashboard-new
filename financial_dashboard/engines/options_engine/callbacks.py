"""
Options Bot Dashboard Callbacks
================================

Registers all callbacks for the Options Bot Dashboard.
Handles bot creation, start/stop, and real-time updates.

This module should be imported and register_options_callbacks(app) called
during app initialization.
"""

import logging
import json
from dash import Input, Output, State, callback_context, no_update, ALL, MATCH
from dash import html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime

logger = logging.getLogger(__name__)

# Import Options Engine components
try:
    from financial_dashboard.engines.options_engine.scheduler import (
        get_options_scheduler,
        create_gld_rsi_bot,
        OptionsScheduler,
    )
    from financial_dashboard.engines.options_engine.live_data import (
        AlpacaDataHandler,
        create_live_data_handler,
    )
    from financial_dashboard.engines.options_engine.schema import (
        create_short_put_spread_recipe,
        create_iron_condor_recipe,
    )
    from financial_dashboard.engines.options_engine.dashboard_ui import (
        create_bot_card,
        create_status_badge,
    )
    OPTIONS_ENGINE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Options Engine not available: {e}")
    OPTIONS_ENGINE_AVAILABLE = False


def register_options_callbacks(app):
    """
    Register all Options Bot callbacks with the Dash app.
    
    Call this in your app initialization:
    ```python
    from financial_dashboard.engines.options_engine.callbacks import register_options_callbacks
    register_options_callbacks(app)
    ```
    """
    if not OPTIONS_ENGINE_AVAILABLE:
        logger.warning("Options Engine not available, callbacks not registered")
        return
    
    # Get shared instances
    scheduler = get_options_scheduler()
    data_handler = create_live_data_handler()
    
    # =========================================================================
    # CONNECTION STATUS
    # =========================================================================
    
    @app.callback(
        [
            Output("options-alpaca-status", "children"),
            Output("options-market-status", "children"),
            Output("options-buying-power", "children"),
            Output("options-active-bots", "children"),
            Output("options-connection-badge", "children"),
            Output("options-connection-badge", "color"),
        ],
        [
            Input("options-refresh-connection", "n_clicks"),
            Input("options-bots-interval", "n_intervals"),
        ],
        prevent_initial_call=False
    )
    def update_connection_status(n_clicks, n_intervals):
        """Update connection status panel."""
        try:
            # Get connection status
            status = data_handler.get_connection_status()
            
            # Alpaca status
            alpaca_connected = status.get("alpaca", {}).get("connected", False)
            alpaca_text = [
                html.I(className=f"fas fa-check-circle text-success me-1" if alpaca_connected else "fas fa-times-circle text-danger me-1"),
                "Connected" if alpaca_connected else "Not Connected"
            ]
            
            # Market status
            market_status = data_handler.get_market_status()
            is_open = market_status.get("is_open", False)
            market_text = [
                dbc.Badge("OPEN", color="success", className="me-1") if is_open else dbc.Badge("CLOSED", color="secondary", className="me-1"),
            ]
            
            # Buying power
            buying_power = status.get("alpaca", {}).get("buying_power", 0)
            bp_text = f"${buying_power:,.0f}" if buying_power else "$--"
            
            # Active bots
            running_bots = len(scheduler.get_running_bots())
            active_text = str(running_bots)
            
            # Connection badge
            badge_text = "LIVE" if alpaca_connected else "OFFLINE"
            badge_color = "success" if alpaca_connected else "danger"
            
            return alpaca_text, market_text, bp_text, active_text, badge_text, badge_color
            
        except Exception as e:
            logger.exception("Error updating connection status")
            return ["Error"], ["--"], ["$--"], ["0"], "ERROR", "danger"
    
    # =========================================================================
    # LIVE MARKET DATA
    # =========================================================================
    
    @app.callback(
        [
            Output("options-live-price", "children"),
            Output("options-live-change", "children"),
            Output("options-live-change", "className"),
            Output("options-live-rsi", "children"),
            Output("options-rsi-signal", "children"),
            Output("options-live-vix", "children"),
            Output("options-live-ivrank", "children"),
            Output("options-rsi-gauge", "figure"),
        ],
        [
            Input("options-data-interval", "n_intervals"),
            Input("options-symbol-select", "value"),
        ],
        prevent_initial_call=False
    )
    def update_market_data(n_intervals, symbol):
        """Update live market data panel."""
        try:
            if not symbol:
                symbol = "GLD"
            
            # Get quote
            quote = data_handler.get_quote(symbol)
            price_text = f"${quote.price:,.2f}"
            
            # Change
            change = quote.change
            change_pct = quote.change_pct
            change_text = f"${change:+,.2f} ({change_pct:+.2f}%)"
            change_class = "fs-5 fw-bold text-success" if change >= 0 else "fs-5 fw-bold text-danger"
            
            # RSI
            rsi = data_handler.get_indicator(symbol, "RSI", 14)
            rsi_value = rsi.value
            rsi_text = f"{rsi_value:.1f}"
            
            # RSI signal badge
            if rsi_value < 30:
                rsi_signal = dbc.Badge("OVERSOLD", color="success", pill=True)
            elif rsi_value > 70:
                rsi_signal = dbc.Badge("OVERBOUGHT", color="danger", pill=True)
            else:
                rsi_signal = dbc.Badge("NEUTRAL", color="secondary", pill=True)
            
            # VIX
            try:
                vix = data_handler.get_indicator("VIX", "VIX", 1)
                vix_text = f"{vix.value:.1f}"
            except Exception:
                vix_text = "--"
            
            # IV Rank
            try:
                iv = data_handler.get_indicator(symbol, "IV_RANK", 1)
                iv_text = f"{iv.value:.0f}%"
            except Exception:
                iv_text = "--"
            
            # RSI Gauge
            gauge_fig = create_rsi_gauge(rsi_value)
            
            return (
                price_text, change_text, change_class, rsi_text, 
                rsi_signal, vix_text, iv_text, gauge_fig
            )
            
        except Exception as e:
            logger.exception("Error updating market data")
            return ("$--", "--", "fs-5 fw-bold", "--", "", "--", "--", {})
    
    # =========================================================================
    # BOT CREATION
    # =========================================================================
    
    @app.callback(
        [
            Output("options-toast", "is_open", allow_duplicate=True),
            Output("options-toast", "header", allow_duplicate=True),
            Output("options-toast", "children", allow_duplicate=True),
            Output("options-toast", "icon", allow_duplicate=True),
            Output("options-bots-store", "data", allow_duplicate=True),
        ],
        [Input("options-create-bot-btn", "n_clicks")],
        [
            State("options-bot-name", "value"),
            State("options-bot-symbol", "value"),
            State("options-bot-strategy", "value"),
            State("options-bot-interval", "value"),
            State("options-rsi-threshold", "value"),
            State("options-vix-threshold", "value"),
            State("options-iv-threshold", "value"),
            State("options-market-condition", "value"),
        ],
        prevent_initial_call=True
    )
    def create_bot(n_clicks, name, symbol, strategy, interval, rsi, vix, iv, market):
        """Create a new options bot."""
        if not n_clicks:
            return no_update, no_update, no_update, no_update, no_update
        
        try:
            # Create recipe based on strategy
            if strategy == "short_put_spread":
                recipe = create_short_put_spread_recipe(
                    symbol=symbol,
                    rsi_threshold=float(rsi or 30),
                    vix_threshold=float(vix or 20),
                )
            elif strategy == "iron_condor":
                recipe = create_iron_condor_recipe(
                    symbol=symbol,
                    rsi_threshold=float(rsi or 30),
                )
            else:
                # Default to short put spread
                recipe = create_short_put_spread_recipe(
                    symbol=symbol,
                    rsi_threshold=float(rsi or 30),
                )
            
            # Create bot
            bot_id = scheduler.create_bot(
                name=name or f"{symbol} Bot",
                recipe=recipe,
                symbol=symbol,
                check_interval=int(interval or 60),
            )
            
            logger.info(f"Created bot: {bot_id}")
            
            return (
                True,
                "Bot Created!",
                f"Successfully created '{name}' for {symbol}",
                "success",
                {"refresh": datetime.now().isoformat()},
            )
            
        except Exception as e:
            logger.exception("Error creating bot")
            return (
                True,
                "Error",
                f"Failed to create bot: {str(e)}",
                "danger",
                no_update,
            )
    
    # =========================================================================
    # BOTS LIST
    # =========================================================================
    
    @app.callback(
        Output("options-bots-container", "children"),
        [
            Input("options-refresh-bots", "n_clicks"),
            Input("options-bots-interval", "n_intervals"),
            Input("options-bots-store", "data"),
        ],
        prevent_initial_call=False
    )
    def update_bots_list(n_clicks, n_intervals, store_data):
        """Update the list of bots."""
        try:
            bots = scheduler.get_all_bots_status()
            
            if not bots:
                return dbc.Alert([
                    html.I(className="fas fa-info-circle me-2"),
                    "No bots created yet. Create one above!"
                ], color="info", className="text-center")
            
            cards = []
            for bot in bots:
                cards.append(
                    create_bot_card(
                        bot_id=bot["bot_id"],
                        name=bot["name"],
                        symbol=bot["symbol"],
                        status=bot["status"],
                        stats=bot["stats"],
                    )
                )
            
            return cards
            
        except Exception as e:
            logger.exception("Error updating bots list")
            return dbc.Alert(f"Error loading bots: {str(e)}", color="danger")
    
    # =========================================================================
    # BOT TOGGLE (START/STOP)
    # =========================================================================
    
    @app.callback(
        [
            Output("options-toast", "is_open", allow_duplicate=True),
            Output("options-toast", "header", allow_duplicate=True),
            Output("options-toast", "children", allow_duplicate=True),
            Output("options-toast", "icon", allow_duplicate=True),
            Output("options-bots-store", "data", allow_duplicate=True),
        ],
        [Input({"type": "bot-toggle", "index": ALL}, "n_clicks")],
        prevent_initial_call=True
    )
    def toggle_bot(n_clicks_list):
        """Start or stop a bot."""
        ctx = callback_context
        if not ctx.triggered or not any(n_clicks_list):
            return no_update, no_update, no_update, no_update, no_update
        
        try:
            # Get which button was clicked
            triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
            bot_id = json.loads(triggered_id)["index"]
            
            # Check current status
            status = scheduler.get_bot_status(bot_id)
            is_running = status.get("is_running", False)
            
            if is_running:
                scheduler.stop_bot(bot_id)
                return (
                    True, "Bot Stopped", 
                    f"Stopped {status['name']}", 
                    "warning",
                    {"refresh": datetime.now().isoformat()}
                )
            else:
                scheduler.start_bot(bot_id)
                return (
                    True, "Bot Started",
                    f"Started {status['name']} - checking conditions every {status['check_interval']}s",
                    "success",
                    {"refresh": datetime.now().isoformat()}
                )
                
        except Exception as e:
            logger.exception("Error toggling bot")
            return True, "Error", str(e), "danger", no_update
    
    # =========================================================================
    # BOT TRIGGER ONCE
    # =========================================================================
    
    @app.callback(
        [
            Output("options-toast", "is_open", allow_duplicate=True),
            Output("options-toast", "header", allow_duplicate=True),
            Output("options-toast", "children", allow_duplicate=True),
            Output("options-toast", "icon", allow_duplicate=True),
        ],
        [Input({"type": "bot-trigger", "index": ALL}, "n_clicks")],
        prevent_initial_call=True
    )
    def trigger_bot_once(n_clicks_list):
        """Manually trigger a bot once."""
        ctx = callback_context
        if not ctx.triggered or not any(n_clicks_list):
            return no_update, no_update, no_update, no_update
        
        try:
            triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
            bot_id = json.loads(triggered_id)["index"]
            
            result = scheduler.trigger_once(bot_id)
            
            if result.get("success"):
                msg = f"Price: ${result.get('price', 0):.2f}, RSI: {result.get('rsi', 0):.1f}"
                if result.get("triggered"):
                    msg += " - CONDITIONS MET!"
                    icon = "success"
                else:
                    msg += " - conditions not met"
                    icon = "info"
                return True, "Manual Trigger", msg, icon
            else:
                return True, "Trigger Failed", result.get("error", "Unknown error"), "danger"
                
        except Exception as e:
            logger.exception("Error triggering bot")
            return True, "Error", str(e), "danger"
    
    # =========================================================================
    # BOT DELETE
    # =========================================================================
    
    @app.callback(
        [
            Output("options-toast", "is_open", allow_duplicate=True),
            Output("options-toast", "header", allow_duplicate=True),
            Output("options-toast", "children", allow_duplicate=True),
            Output("options-toast", "icon", allow_duplicate=True),
            Output("options-bots-store", "data", allow_duplicate=True),
        ],
        [Input({"type": "bot-delete", "index": ALL}, "n_clicks")],
        prevent_initial_call=True
    )
    def delete_bot(n_clicks_list):
        """Delete a bot."""
        ctx = callback_context
        if not ctx.triggered or not any(n_clicks_list):
            return no_update, no_update, no_update, no_update, no_update
        
        try:
            triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
            bot_id = json.loads(triggered_id)["index"]
            
            status = scheduler.get_bot_status(bot_id)
            scheduler.delete_bot(bot_id)
            
            return (
                True, "Bot Deleted",
                f"Deleted {status.get('name', bot_id)}",
                "warning",
                {"refresh": datetime.now().isoformat()}
            )
            
        except Exception as e:
            logger.exception("Error deleting bot")
            return True, "Error", str(e), "danger", no_update
    
    # =========================================================================
    # TRADE LOG
    # =========================================================================
    
    @app.callback(
        Output("options-trade-log", "children"),
        [Input("options-bots-interval", "n_intervals")],
        prevent_initial_call=False
    )
    def update_trade_log(n_intervals):
        """Update trade log panel."""
        try:
            bots = scheduler.get_all_bots_status()
            
            all_trades = []
            for bot in bots:
                for trade in bot.get("recent_trades", []):
                    trade["bot_name"] = bot["name"]
                    all_trades.append(trade)
            
            # Sort by timestamp
            all_trades.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            if not all_trades:
                return html.Div([
                    html.I(className="fas fa-clock text-muted me-2"),
                    html.Span("No trades yet", className="text-muted")
                ], className="text-center py-3")
            
            trade_items = []
            for trade in all_trades[:20]:
                pnl = trade.get("pnl", 0)
                pnl_color = "success" if pnl >= 0 else "danger"
                
                trade_items.append(
                    html.Div([
                        html.Div([
                            html.Strong(trade.get("symbol", "?"), className="me-2"),
                            dbc.Badge(trade.get("action", "?"), color="primary", className="me-2"),
                            html.Small(trade.get("strategy", ""), className="text-muted"),
                        ]),
                        html.Div([
                            html.Small(trade.get("bot_name", ""), className="text-muted me-2"),
                            html.Span(f"${pnl:+.2f}", className=f"text-{pnl_color}"),
                        ]),
                    ], className="d-flex justify-content-between py-1 border-bottom")
                )
            
            return trade_items
            
        except Exception as e:
            logger.exception("Error updating trade log")
            return html.Div(f"Error: {str(e)}", className="text-danger")
    
    # =========================================================================
    # EVENT LOG
    # =========================================================================
    
    @app.callback(
        [
            Output("options-event-log", "children"),
            Output("options-event-count", "children"),
        ],
        [Input("options-bots-interval", "n_intervals")],
        prevent_initial_call=False
    )
    def update_event_log(n_intervals):
        """Update event log panel."""
        try:
            bots = scheduler.get_all_bots_status()
            
            all_events = []
            for bot in bots:
                for event in bot.get("recent_events", []):
                    event["bot_name"] = bot["name"]
                    all_events.append(event)
            
            # Sort by timestamp
            all_events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            event_items = []
            for event in all_events[:30]:
                event_type = event.get("event_type", "info")
                
                # Icon based on type
                icon_map = {
                    "check": "fa-search text-info",
                    "trade_executed": "fa-check-circle text-success",
                    "bot_started": "fa-play text-success",
                    "bot_stopped": "fa-stop text-warning",
                    "error": "fa-exclamation-circle text-danger",
                    "bot_created": "fa-plus text-primary",
                }
                icon = icon_map.get(event_type, "fa-info-circle text-secondary")
                
                # Parse timestamp
                ts = event.get("timestamp", "")
                try:
                    dt = datetime.fromisoformat(ts)
                    time_str = dt.strftime("%H:%M:%S")
                except Exception:
                    time_str = "--:--:--"
                
                event_items.append(
                    html.Div([
                        html.I(className=f"fas {icon} me-2"),
                        html.Small(time_str, className="text-muted me-2"),
                        html.Small(event.get("bot_name", ""), className="fw-bold me-1"),
                        html.Small(event.get("message", "")[:50]),
                    ], className="py-1")
                )
            
            return event_items, str(len(all_events))
            
        except Exception as e:
            logger.exception("Error updating event log")
            return [html.Div(f"Error: {str(e)}", className="text-danger")], "0"
    
    # =========================================================================
    # CONDITION PREVIEW
    # =========================================================================
    
    @app.callback(
        Output("options-condition-preview", "children"),
        [
            Input("options-rsi-threshold", "value"),
            Input("options-vix-threshold", "value"),
            Input("options-iv-threshold", "value"),
            Input("options-market-condition", "value"),
        ],
        prevent_initial_call=False
    )
    def update_condition_preview(rsi, vix, iv, market):
        """Update the condition preview text."""
        conditions = []
        
        if rsi:
            conditions.append(f"RSI < {rsi}")
        if vix:
            conditions.append(f"VIX > {vix}")
        if iv:
            conditions.append(f"IV_RANK > {iv}")
        if market == "open":
            conditions.append("Market = OPEN")
        
        return " AND ".join(conditions) if conditions else "No conditions set"
    
    # =========================================================================
    # QUICK STATS
    # =========================================================================
    
    @app.callback(
        [
            Output("stat-active-bots", "children"),
            Output("stat-today-trades", "children"),
            Output("stat-total-pnl", "children"),
            Output("stat-win-rate", "children"),
        ],
        [Input("options-bots-interval", "n_intervals")],
        prevent_initial_call=False
    )
    def update_quick_stats(n_intervals):
        """Update quick stats cards."""
        from .dashboard_ui import create_stat_card
        
        try:
            bots = scheduler.get_all_bots_status()
            
            active_count = sum(1 for b in bots if b.get("is_running"))
            total_trades = sum(b.get("stats", {}).get("trades_executed", 0) for b in bots)
            total_pnl = sum(b.get("stats", {}).get("total_pnl", 0) for b in bots)
            
            # Win rate (placeholder)
            win_rate = 0
            if total_trades > 0:
                wins = sum(b.get("stats", {}).get("conditions_met", 0) for b in bots)
                win_rate = (wins / max(1, total_trades)) * 100 if total_trades else 0
            
            pnl_color = "success" if total_pnl >= 0 else "danger"
            
            return (
                create_stat_card("Active Bots", str(active_count), "fa-robot", "primary"),
                create_stat_card("Total Trades", str(total_trades), "fa-exchange-alt", "success"),
                create_stat_card("Total P&L", f"${total_pnl:,.2f}", "fa-dollar-sign", pnl_color),
                create_stat_card("Win Rate", f"{win_rate:.0f}%", "fa-chart-pie", "warning"),
            )
            
        except Exception as e:
            logger.exception("Error updating quick stats")
            return (
                create_stat_card("Active Bots", "?", "fa-robot", "secondary"),
                create_stat_card("Total Trades", "?", "fa-exchange-alt", "secondary"),
                create_stat_card("Total P&L", "$?", "fa-dollar-sign", "secondary"),
                create_stat_card("Win Rate", "?%", "fa-chart-pie", "secondary"),
            )
    
    logger.info("✅ Options Bot callbacks registered successfully")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_rsi_gauge(rsi_value: float) -> dict:
    """Create an RSI gauge chart."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=rsi_value,
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 30], 'color': "lightgreen"},
                {'range': [30, 70], 'color': "lightyellow"},
                {'range': [70, 100], 'color': "lightcoral"},
            ],
            'threshold': {
                'line': {'color': "red", 'width': 2},
                'thickness': 0.75,
                'value': rsi_value
            }
        },
        title={'text': "RSI", 'font': {'size': 12}}
    ))
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=10),
        height=100,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    
    return fig

"""
Options Bots Tab Callbacks
==========================
All callback functions for the Options Bots tab.
"""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from dash import callback, Input, Output, State, html, no_update, ctx
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px

logger = logging.getLogger(__name__)

# Try to import options engine components
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
    OPTIONS_ENGINE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Options engine not available: {e}")
    OPTIONS_ENGINE_AVAILABLE = False


def register_options_bots_callbacks(app) -> None:
    """Register all callbacks for the Options Bots tab."""
    
    if not OPTIONS_ENGINE_AVAILABLE:
        logger.warning("Options engine not available - callbacks not registered")
        return
    
    # =========================================================================
    # CONNECTION & MARKET DATA
    # =========================================================================
    
    @app.callback(
        [
            Output("options-bots-connection-status", "children"),
            Output("options-bots-connection-store", "data"),
        ],
        [
            Input("options-bots-refresh-interval", "n_intervals"),
            Input("options-bots-refresh-all", "n_clicks"),
        ],
        prevent_initial_call=False,
    )
    def update_connection_status(n_intervals, refresh_clicks):
        """Update API connection status."""
        try:
            handler = create_live_data_handler()
            status = handler.get_connection_status()
            
            alpaca_connected = status.get("alpaca", {}).get("connected", False)
            
            connection_ui = html.Div([
                # Alpaca API
                html.Div([
                    html.Div([
                        html.Span(
                            className=f"status-dot {'status-connected' if alpaca_connected else 'status-disconnected'} me-2"
                        ),
                        html.Strong("Alpaca API"),
                    ], className="d-flex align-items-center"),
                    html.Small(
                        "Connected" if alpaca_connected else "Disconnected",
                        className="text-success" if alpaca_connected else "text-danger"
                    ),
                ], className="mb-3"),
                # yFinance
                html.Div([
                    html.Div([
                        html.Span(className="status-dot status-connected me-2"),
                        html.Strong("yFinance"),
                    ], className="d-flex align-items-center"),
                    html.Small("Available (fallback)", className="text-success"),
                ]),
            ])
            
            return connection_ui, status
            
        except Exception as e:
            logger.error(f"Error checking connection: {e}")
            return html.Div([
                html.P(f"Error: {str(e)}", className="text-danger")
            ]), {}
    
    @app.callback(
        [
            Output("options-bots-market-status", "children"),
            Output("options-bots-spy-price", "children"),
            Output("options-bots-vix-price", "children"),
            Output("options-bots-gld-price", "children"),
        ],
        [
            Input("options-bots-refresh-interval", "n_intervals"),
            Input("options-bots-refresh-all", "n_clicks"),
        ],
        prevent_initial_call=False,
    )
    def update_market_overview(n_intervals, refresh_clicks):
        """Update market overview data."""
        try:
            handler = create_live_data_handler()
            
            # Market status
            market = handler.get_market_status()
            is_open = market.get("is_open", False)
            market_status = html.Span(
                "Open" if is_open else "Closed",
                className="text-success fw-bold" if is_open else "text-danger fw-bold"
            )
            
            # Get quotes
            try:
                spy = handler.get_quote("SPY")
                spy_text = f"${spy.price:.2f}"
            except:
                spy_text = "--"
            
            try:
                # VIX might not be available via Alpaca
                vix_text = "--"
            except:
                vix_text = "--"
            
            try:
                gld = handler.get_quote("GLD")
                gld_text = f"${gld.price:.2f}"
            except:
                gld_text = "--"
            
            return market_status, spy_text, vix_text, gld_text
            
        except Exception as e:
            logger.error(f"Error updating market overview: {e}")
            return "Error", "--", "--", "--"
    
    # =========================================================================
    # DASHBOARD STATS
    # =========================================================================
    
    @app.callback(
        [
            Output("options-bots-total-bots", "children"),
            Output("options-bots-running-bots", "children"),
            Output("options-bots-total-trades", "children"),
            Output("options-bots-total-pnl", "children"),
            Output("options-bots-active-preview", "children"),
            Output("options-bots-recent-activity", "children"),
        ],
        [
            Input("options-bots-refresh-interval", "n_intervals"),
            Input("options-bots-refresh-all", "n_clicks"),
        ],
        prevent_initial_call=False,
    )
    def update_dashboard_stats(n_intervals, refresh_clicks):
        """Update dashboard statistics."""
        try:
            scheduler = get_options_scheduler()
            all_bots = scheduler.get_all_bots_status()
            
            total_bots = len(all_bots)
            running_bots = len([b for b in all_bots if b.get("is_running")])
            
            total_trades = sum(b.get("stats", {}).get("trades_executed", 0) for b in all_bots)
            total_pnl = sum(b.get("stats", {}).get("total_pnl", 0) for b in all_bots)
            
            # Active bots preview
            if all_bots:
                active_preview = []
                for bot in all_bots[:5]:  # Show top 5
                    status_badge = dbc.Badge(
                        "Running" if bot.get("is_running") else "Stopped",
                        color="success" if bot.get("is_running") else "secondary",
                        className="ms-2"
                    )
                    active_preview.append(
                        html.Div([
                            html.Div([
                                html.Strong(bot.get("name", "Unknown")),
                                status_badge,
                            ], className="d-flex justify-content-between"),
                            html.Small(f"{bot.get('symbol', '--')} • {bot.get('stats', {}).get('trades_executed', 0)} trades", className="text-muted"),
                        ], className="border-bottom pb-2 mb-2")
                    )
            else:
                active_preview = [html.P("No bots created yet", className="text-muted text-center my-4")]
            
            # Recent activity
            recent_activity = []
            for bot in all_bots:
                events = bot.get("recent_events", [])[:3]
                for event in events:
                    recent_activity.append(
                        html.Div([
                            html.Small(event.get("timestamp", "")[:19], className="text-muted"),
                            html.P(f"[{event.get('event_type', '')}] {event.get('message', '')[:40]}", className="mb-1 small"),
                        ], className="border-bottom pb-1 mb-1")
                    )
            
            if not recent_activity:
                recent_activity = [html.P("No recent activity", className="text-muted text-center my-4")]
            else:
                recent_activity = recent_activity[:10]  # Limit to 10
            
            pnl_text = f"${total_pnl:,.2f}" if total_pnl >= 0 else f"-${abs(total_pnl):,.2f}"
            
            return str(total_bots), str(running_bots), str(total_trades), pnl_text, active_preview, recent_activity
            
        except Exception as e:
            logger.error(f"Error updating dashboard stats: {e}")
            return "0", "0", "0", "$0", [html.P("Error loading bots", className="text-danger")], []
    
    # =========================================================================
    # BOT CREATION
    # =========================================================================
    
    @app.callback(
        Output("options-bots-recipe-preview", "children"),
        [
            Input("options-bots-template-select", "value"),
            Input("options-bots-symbol-select", "value"),
            Input("options-bots-rsi-threshold", "value"),
            Input("options-bots-take-profit", "value"),
            Input("options-bots-stop-loss", "value"),
        ],
    )
    def update_recipe_preview(template, symbol, rsi_threshold, take_profit, stop_loss):
        """Update the recipe JSON preview."""
        try:
            if template == "rsi_put_spread":
                recipe = create_short_put_spread_recipe(
                    symbol=symbol or "GLD",
                    rsi_threshold=float(rsi_threshold or 40),
                    take_profit_pct=float(take_profit or 50),
                    stop_loss_pct=float(stop_loss or 200),
                )
                return json.dumps(json.loads(recipe.model_dump_json()), indent=2)
            elif template == "vix_iron_condor":
                recipe = create_iron_condor_recipe(
                    symbol=symbol or "SPY",
                    take_profit_pct=float(take_profit or 50),
                )
                return json.dumps(json.loads(recipe.model_dump_json()), indent=2)
            else:
                return "Custom recipe editor coming soon..."
        except Exception as e:
            return f"Error generating recipe: {str(e)}"
    
    @app.callback(
        [
            Output("options-bots-list-container", "children", allow_duplicate=True),
            Output("options-bots-active-bots-store", "data"),
        ],
        [
            Input("options-bots-create-btn", "n_clicks"),
        ],
        [
            State("options-bots-name-input", "value"),
            State("options-bots-symbol-select", "value"),
            State("options-bots-template-select", "value"),
            State("options-bots-rsi-threshold", "value"),
            State("options-bots-check-interval", "value"),
            State("options-bots-options", "value"),
        ],
        prevent_initial_call=True,
    )
    def create_new_bot(n_clicks, name, symbol, template, rsi_threshold, check_interval, options):
        """Create a new trading bot."""
        if not n_clicks:
            return no_update, no_update
        
        try:
            scheduler = get_options_scheduler()
            
            # Create recipe based on template
            if template == "rsi_put_spread":
                require_market_hours = "market_hours" in (options or [])
                recipe = create_short_put_spread_recipe(
                    symbol=symbol or "GLD",
                    rsi_threshold=float(rsi_threshold or 40),
                    require_market_hours=require_market_hours,
                )
            elif template == "vix_iron_condor":
                recipe = create_iron_condor_recipe(
                    symbol=symbol or "SPY",
                )
            else:
                return html.Div([
                    dbc.Alert("Template not supported yet", color="warning"),
                ]), no_update
            
            # Create bot
            paper_mode = "paper" in (options or [])
            bot_id = scheduler.create_bot(
                name=name or f"{symbol} Bot",
                recipe=recipe,
                symbol=symbol,
                check_interval=int(check_interval or 60),
                paper_mode=paper_mode,
            )
            
            # Auto-start if selected
            if "auto_start" in (options or []):
                scheduler.start_bot(bot_id)
            
            # Return updated bot list
            all_bots = scheduler.get_all_bots_status()
            bot_list_ui = _render_bot_list(all_bots)
            
            return bot_list_ui, [b["bot_id"] for b in all_bots]
            
        except Exception as e:
            logger.error(f"Error creating bot: {e}")
            return html.Div([
                dbc.Alert(f"Error creating bot: {str(e)}", color="danger"),
            ]), no_update
    
    # =========================================================================
    # BOT MANAGEMENT
    # =========================================================================
    
    @app.callback(
        Output("options-bots-list-container", "children"),
        [
            Input("options-bots-refresh-list", "n_clicks"),
            Input("options-bots-tabs", "active_tab"),
        ],
        prevent_initial_call=False,
    )
    def refresh_bot_list(refresh_clicks, active_tab):
        """Refresh the bot list."""
        try:
            scheduler = get_options_scheduler()
            all_bots = scheduler.get_all_bots_status()
            return _render_bot_list(all_bots)
        except Exception as e:
            logger.error(f"Error refreshing bot list: {e}")
            return html.Div([
                dbc.Alert(f"Error loading bots: {str(e)}", color="danger"),
            ])
    
    @app.callback(
        Output("options-bots-list-container", "children", allow_duplicate=True),
        [
            Input({"type": "options-bot-toggle", "index": dash.ALL}, "n_clicks"),
            Input({"type": "options-bot-delete", "index": dash.ALL}, "n_clicks"),
            Input({"type": "options-bot-trigger", "index": dash.ALL}, "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def handle_bot_actions(toggle_clicks, delete_clicks, trigger_clicks):
        """Handle bot action buttons."""
        if not ctx.triggered_id:
            return no_update
        
        try:
            scheduler = get_options_scheduler()
            bot_id = ctx.triggered_id["index"]
            action = ctx.triggered_id["type"]
            
            if action == "options-bot-toggle":
                status = scheduler.get_bot_status(bot_id)
                if status.get("is_running"):
                    scheduler.stop_bot(bot_id)
                else:
                    scheduler.start_bot(bot_id)
            
            elif action == "options-bot-delete":
                scheduler.delete_bot(bot_id)
            
            elif action == "options-bot-trigger":
                scheduler.trigger_once(bot_id)
            
            # Refresh list
            all_bots = scheduler.get_all_bots_status()
            return _render_bot_list(all_bots)
            
        except Exception as e:
            logger.error(f"Error handling bot action: {e}")
            return no_update
    
    # =========================================================================
    # QUICK ACTIONS
    # =========================================================================
    
    @app.callback(
        Output("options-bots-list-container", "children", allow_duplicate=True),
        [
            Input("options-bots-quick-gld", "n_clicks"),
            Input("options-bots-quick-spy-ic", "n_clicks"),
            Input("options-bots-stop-all", "n_clicks"),
            Input("options-bots-start-all", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def handle_quick_actions(gld_clicks, spy_ic_clicks, stop_all_clicks, start_all_clicks):
        """Handle quick action buttons."""
        if not ctx.triggered_id:
            return no_update
        
        try:
            scheduler = get_options_scheduler()
            trigger = ctx.triggered_id
            
            if trigger == "options-bots-quick-gld":
                bot_id = create_gld_rsi_bot(
                    name="Quick GLD RSI Bot",
                    rsi_threshold=40.0,
                    check_interval=60,
                    require_market_hours=True,
                )
                scheduler.start_bot(bot_id)
            
            elif trigger == "options-bots-quick-spy-ic":
                recipe = create_iron_condor_recipe(symbol="SPY")
                bot_id = scheduler.create_bot(
                    name="Quick SPY Iron Condor",
                    recipe=recipe,
                    symbol="SPY",
                    check_interval=60,
                )
                scheduler.start_bot(bot_id)
            
            elif trigger == "options-bots-stop-all":
                scheduler.stop_all()
            
            elif trigger == "options-bots-start-all":
                for bot in scheduler.get_all_bots_status():
                    if not bot.get("is_running"):
                        scheduler.start_bot(bot["bot_id"])
            
            # Refresh list
            all_bots = scheduler.get_all_bots_status()
            return _render_bot_list(all_bots)
            
        except Exception as e:
            logger.error(f"Error handling quick action: {e}")
            return no_update
    
    # =========================================================================
    # PERFORMANCE CHARTS
    # =========================================================================
    
    @app.callback(
        [
            Output("options-bots-win-rate", "children"),
            Output("options-bots-avg-win", "children"),
            Output("options-bots-avg-loss", "children"),
            Output("options-bots-profit-factor", "children"),
            Output("options-bots-pnl-chart", "figure"),
            Output("options-bots-strategy-chart", "figure"),
        ],
        [
            Input("options-bots-tabs", "active_tab"),
            Input("options-bots-refresh-interval", "n_intervals"),
        ],
    )
    def update_performance_metrics(active_tab, n_intervals):
        """Update performance metrics and charts."""
        if active_tab != "tab-bots-performance":
            return no_update, no_update, no_update, no_update, no_update, no_update
        
        try:
            # Placeholder charts
            pnl_fig = go.Figure()
            pnl_fig.add_trace(go.Scatter(
                x=[],
                y=[],
                mode="lines",
                name="Cumulative P&L",
            ))
            pnl_fig.update_layout(
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            
            strategy_fig = go.Figure()
            strategy_fig.add_trace(go.Bar(
                x=["Put Spread", "Iron Condor"],
                y=[0, 0],
            ))
            strategy_fig.update_layout(
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            
            return "0%", "$0", "$0", "0.00", pnl_fig, strategy_fig
            
        except Exception as e:
            logger.error(f"Error updating performance: {e}")
            return "--", "--", "--", "--", {}, {}
    
    # =========================================================================
    # SETTINGS MODAL
    # =========================================================================
    
    @app.callback(
        Output("options-bots-settings-modal", "is_open"),
        [
            Input("options-bots-settings-btn", "n_clicks"),
            Input("options-bots-settings-close", "n_clicks"),
        ],
        [State("options-bots-settings-modal", "is_open")],
        prevent_initial_call=True,
    )
    def toggle_settings_modal(open_clicks, close_clicks, is_open):
        """Toggle settings modal."""
        return not is_open


def _render_bot_list(bots: List[Dict]) -> html.Div:
    """Render the bot list UI."""
    if not bots:
        return html.Div([
            html.P("No bots created yet. Use the 'Create Bot' tab to get started.", 
                   className="text-muted text-center my-5"),
        ])
    
    bot_cards = []
    for bot in bots:
        bot_id = bot.get("bot_id", "")
        is_running = bot.get("is_running", False)
        stats = bot.get("stats", {})
        
        status_badge = dbc.Badge(
            "Running" if is_running else "Stopped",
            color="success" if is_running else "secondary",
        )
        
        card = dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.H5([
                            bot.get("name", "Unknown Bot"),
                            status_badge,
                        ], className="mb-1"),
                        html.P([
                            html.Span(bot.get("symbol", "--"), className="badge bg-primary me-2"),
                            html.Small(f"ID: {bot_id[:12]}...", className="text-muted"),
                        ], className="mb-0"),
                    ], md=4),
                    dbc.Col([
                        html.Small("Checks", className="text-muted d-block"),
                        html.Strong(str(stats.get("total_checks", 0))),
                    ], md=2, className="text-center"),
                    dbc.Col([
                        html.Small("Conditions Met", className="text-muted d-block"),
                        html.Strong(str(stats.get("conditions_met", 0))),
                    ], md=2, className="text-center"),
                    dbc.Col([
                        html.Small("Trades", className="text-muted d-block"),
                        html.Strong(str(stats.get("trades_executed", 0))),
                    ], md=2, className="text-center"),
                    dbc.Col([
                        dbc.ButtonGroup([
                            dbc.Button(
                                html.I(className="fas fa-stop" if is_running else "fas fa-play"),
                                id={"type": "options-bot-toggle", "index": bot_id},
                                color="warning" if is_running else "success",
                                size="sm",
                                title="Stop" if is_running else "Start",
                            ),
                            dbc.Button(
                                html.I(className="fas fa-bolt"),
                                id={"type": "options-bot-trigger", "index": bot_id},
                                color="info",
                                size="sm",
                                title="Trigger Now",
                            ),
                            dbc.Button(
                                html.I(className="fas fa-trash"),
                                id={"type": "options-bot-delete", "index": bot_id},
                                color="danger",
                                size="sm",
                                title="Delete",
                            ),
                        ]),
                    ], md=2, className="text-end"),
                ]),
            ]),
        ], className="mb-2")
        
        bot_cards.append(card)
    
    return html.Div(bot_cards)


# Import dash for pattern matching callbacks
import dash

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
import numpy as np

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
        create_bull_put_spread_recipe,
        create_bear_call_spread_recipe,
        create_long_straddle_recipe,
        create_short_strangle_recipe,
        create_calendar_spread_recipe,
        create_iron_butterfly_recipe,
        create_delta_neutralizer_recipe,
        create_vix_hedge_recipe,
        create_covered_call_recipe,
        create_wheel_strategy_recipe,
    )
    from financial_dashboard.engines.options_engine.greeks import (
        get_greeks_calculator,
        calculate_greeks,
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
    # PORTFOLIO GREEKS (NEW)
    # =========================================================================
    
    @app.callback(
        [
            Output("ob-portfolio-delta", "children"),
            Output("ob-portfolio-gamma", "children"),
            Output("ob-portfolio-theta", "children"),
            Output("ob-portfolio-vega", "children"),
        ],
        [
            Input("options-bots-refresh-interval", "n_intervals"),
            Input("options-bots-refresh-all", "n_clicks"),
        ],
        prevent_initial_call=False,
    )
    def update_portfolio_greeks(n_intervals, refresh_clicks):
        """Update portfolio-level Greeks from all active positions."""
        try:
            scheduler = get_options_scheduler()
            all_bots = scheduler.get_all_bots_status()
            
            # Aggregate Greeks from all active positions
            total_delta = 0
            total_gamma = 0
            total_theta = 0
            total_vega = 0
            
            for bot in all_bots:
                if bot.get("is_running"):
                    greeks = bot.get("portfolio_greeks", {})
                    total_delta += greeks.get("delta", 0)
                    total_gamma += greeks.get("gamma", 0)
                    total_theta += greeks.get("theta", 0)
                    total_vega += greeks.get("vega", 0)
            
            # Format with color indicators
            def format_greek(value, prefix=""):
                if value > 0:
                    return f"+{prefix}{value:.1f}"
                elif value < 0:
                    return f"{prefix}{value:.1f}"
                return f"{prefix}0"
            
            return (
                format_greek(total_delta),
                format_greek(total_gamma),
                format_greek(total_theta, "$"),
                format_greek(total_vega, "$"),
            )
            
        except Exception as e:
            logger.error(f"Error updating portfolio Greeks: {e}")
            return "0", "0", "$0", "$0"
    
    # =========================================================================
    # IV RANK & PERCENTILE
    # =========================================================================
    
    @app.callback(
        [
            Output("options-bots-iv-rank", "children"),
            Output("options-bots-iv-percentile", "children"),
        ],
        [
            Input("options-bots-refresh-interval", "n_intervals"),
            Input("options-bots-refresh-all", "n_clicks"),
        ],
        prevent_initial_call=False,
    )
    def update_iv_metrics(n_intervals, refresh_clicks):
        """Update IV Rank and IV Percentile for SPY."""
        try:
            import yfinance as yf
            
            # Get VIX historical data (1 year)
            vix = yf.Ticker("^VIX")
            hist = vix.history(period="1y")
            
            if hist.empty:
                return "--", "--"
            
            current_vix = hist['Close'].iloc[-1]
            vix_52wk_high = hist['Close'].max()
            vix_52wk_low = hist['Close'].min()
            
            # IV Rank = (Current - 52wk Low) / (52wk High - 52wk Low) * 100
            iv_range = vix_52wk_high - vix_52wk_low
            if iv_range > 0:
                iv_rank = ((current_vix - vix_52wk_low) / iv_range) * 100
            else:
                iv_rank = 50
            
            # IV Percentile = % of days current VIX was above
            iv_percentile = (hist['Close'] < current_vix).sum() / len(hist) * 100
            
            # Color coding based on levels
            def get_iv_color(value):
                if value < 25:
                    return "text-danger"  # Low IV - red (bad for selling)
                elif value < 50:
                    return "text-warning"  # Medium IV
                else:
                    return "text-success"  # High IV - green (good for selling)
            
            iv_rank_text = html.Span(f"{iv_rank:.0f}%", className=get_iv_color(iv_rank))
            iv_percentile_text = html.Span(f"{iv_percentile:.0f}%", className=get_iv_color(iv_percentile))
            
            return iv_rank_text, iv_percentile_text
            
        except Exception as e:
            logger.error(f"Error calculating IV metrics: {e}")
            return "--", "--"
    
    # =========================================================================
    # POSITION SIZING CALCULATOR
    # =========================================================================
    
    @app.callback(
        Output("ob-position-size-result", "children"),
        [
            Input("ob-account-value", "value"),
            Input("ob-risk-per-trade", "value"),
            Input("ob-max-spread", "value"),
            Input("ob-target-winrate", "value"),
        ],
    )
    def calculate_position_size(account_value, risk_pct, max_spread, target_winrate):
        """Calculate optimal position sizing based on account and risk parameters."""
        try:
            if not all([account_value, risk_pct, max_spread]):
                return no_update
            
            # Max risk per trade
            max_risk = account_value * (risk_pct / 100)
            
            # Max contracts based on spread width (risk = spread width * 100)
            max_contracts = int(max_risk / (max_spread * 100))
            if max_contracts < 1:
                max_contracts = 1
            
            # Margin requirement (typically spread width * contracts * 100)
            margin_req = max_contracts * max_spread * 100
            
            # Kelly criterion suggestion
            if target_winrate:
                win_rate = target_winrate / 100
                loss_rate = 1 - win_rate
                # Assume 2:1 risk/reward for credit spreads
                avg_win = max_spread * 0.5  # Keep ~50% of premium
                avg_loss = max_spread  # Lose full spread
                kelly_pct = (win_rate / avg_loss) - (loss_rate / avg_win) if avg_win > 0 else 0
                kelly_contracts = max(1, int(account_value * max(0, kelly_pct) / (max_spread * 100)))
            else:
                kelly_contracts = max_contracts
            
            # Use the more conservative of kelly and risk-based
            recommended_contracts = min(max_contracts, kelly_contracts)
            
            return dbc.Row([
                dbc.Col([
                    html.Small("Max Risk", className="text-muted d-block"),
                    html.H5(f"${max_risk:,.0f}", className="text-danger mb-0"),
                ], width=4, className="text-center"),
                dbc.Col([
                    html.Small("Contracts", className="text-muted d-block"),
                    html.H5(f"{recommended_contracts}", className="text-success mb-0"),
                ], width=4, className="text-center"),
                dbc.Col([
                    html.Small("Margin Req", className="text-muted d-block"),
                    html.H5(f"${margin_req:,.0f}", className="text-info mb-0"),
                ], width=4, className="text-center"),
            ])
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return html.P("Error calculating", className="text-danger")
    
    # =========================================================================
    # TEMPLATE DESCRIPTIONS
    # =========================================================================
    
    @app.callback(
        Output("options-bots-template-description", "children"),
        Input("options-bots-template-select", "value"),
    )
    def update_template_description(template):
        """Update template description with strategy details."""
        templates = {
            "rsi_put_spread": {
                "name": "RSI Short Put Spread",
                "desc": "Sell put spreads when RSI indicates oversold conditions (<40). Auto-closes on profit target or RSI recovery.",
                "risk": 2,
                "win_rate": "65-70%",
                "capital": "$2K-5K",
                "mechanics": "Sell OTM put, buy further OTM put for protection. Profit if stock stays above short strike."
            },
            "vix_iron_condor": {
                "name": "VIX Iron Condor",
                "desc": "Sell iron condors when VIX is elevated, capturing premium decay. Works best in range-bound markets.",
                "risk": 2,
                "win_rate": "60-65%", 
                "capital": "$5K-10K",
                "mechanics": "Sell call spread + put spread. Profit if underlying stays between short strikes."
            },
            "iron_butterfly": {
                "name": "Iron Butterfly",
                "desc": "Sell ATM call and put spreads for maximum premium. Best in high IV with low price movement.",
                "risk": 2,
                "win_rate": "55-60%",
                "capital": "$5K-10K",
                "mechanics": "Sell ATM call & put, buy OTM wings. Max profit at the money, defined risk."
            },
            "bull_put_spread": {
                "name": "Bull Put Spread",
                "desc": "Bullish credit spread. Profit when stock stays above short strike or rises.",
                "risk": 2,
                "win_rate": "65-75%",
                "capital": "$2K-5K",
                "mechanics": "Sell higher strike put, buy lower strike put. Defined risk bullish trade."
            },
            "bear_call_spread": {
                "name": "Bear Call Spread",
                "desc": "Bearish credit spread. Profit when stock stays below short strike or falls.",
                "risk": 2,
                "win_rate": "65-75%",
                "capital": "$2K-5K",
                "mechanics": "Sell lower strike call, buy higher strike call. Defined risk bearish trade."
            },
            "calendar_spread": {
                "name": "Calendar Spread",
                "desc": "Time decay play. Sell near-term option, buy longer-term option at same strike.",
                "risk": 2,
                "win_rate": "55-65%",
                "capital": "$2K-4K",
                "mechanics": "Profit from faster time decay of short-term option vs. long-term option."
            },
            "long_straddle": {
                "name": "Long Straddle",
                "desc": "Buy ATM call and put. Profit from large moves in either direction.",
                "risk": 3,
                "win_rate": "40-50%",
                "capital": "$2K-5K",
                "mechanics": "Pay premium for unlimited profit potential. Need big move to overcome theta decay."
            },
            "short_strangle": {
                "name": "Short Strangle",
                "desc": "Sell OTM call and put. Collect premium if stock stays in range.",
                "risk": 3,
                "win_rate": "65-75%",
                "capital": "$10K-20K",
                "mechanics": "Undefined risk strategy. Profit if underlying stays between short strikes."
            },
            "wheel_strategy": {
                "name": "The Wheel Strategy",
                "desc": "Cycle between selling cash-secured puts and covered calls for consistent income.",
                "risk": 2,
                "win_rate": "70-80%",
                "capital": "$10K-25K",
                "mechanics": "Sell CSPs until assigned, then sell CCs until called away. Repeat."
            },
            "covered_call": {
                "name": "Covered Call",
                "desc": "Sell calls against stock you own to generate income.",
                "risk": 1,
                "win_rate": "75-85%",
                "capital": "Stock ownership",
                "mechanics": "Own 100 shares, sell OTM call. Limited upside but consistent income."
            },
            "delta_neutralizer": {
                "name": "Delta Neutralizer",
                "desc": "Auto-hedge portfolio when delta exceeds threshold. Maintains market neutral exposure.",
                "risk": 1,
                "win_rate": "N/A (hedge)",
                "capital": "$5K-15K",
                "mechanics": "Buy puts/calls or adjust positions to bring portfolio delta back to neutral."
            },
            "vix_hedge": {
                "name": "VIX Tail Hedge",
                "desc": "Buy VIX calls when SPY crashes to protect portfolio from tail risk events.",
                "risk": 3,
                "win_rate": "20-30% (hedge)",
                "capital": "$2K-5K",
                "mechanics": "Insurance policy. Small constant cost, big payout in crashes."
            },
            "custom": {
                "name": "Custom Recipe",
                "desc": "Build your own strategy from scratch. Full control over triggers, actions, and exit rules.",
                "risk": 3,
                "win_rate": "Varies",
                "capital": "Varies",
                "mechanics": "Define custom entry/exit conditions, position sizing, and risk management rules."
            },
        }
        
        t = templates.get(template, templates["rsi_put_spread"])
        risk_icons = [
            html.I(className=f"fas fa-circle {'text-warning' if i < t['risk'] else 'text-secondary'} me-1")
            for i in range(3)
        ]
        
        return html.Div([
            html.H6(t["name"]),
            html.P(t["desc"], className="text-muted small"),
            html.P(t["mechanics"], className="small fst-italic"),
            dbc.Row([
                dbc.Col([
                    html.Small("Risk Level", className="text-muted"),
                    html.Div(risk_icons),
                ], width=4),
                dbc.Col([
                    html.Small("Win Rate", className="text-muted"),
                    html.Div(t["win_rate"], className="fw-bold text-success"),
                ], width=4),
                dbc.Col([
                    html.Small("Capital Req", className="text-muted"),
                    html.Div(t["capital"], className="fw-bold"),
                ], width=4),
            ], className="mt-2"),
        ])
    
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

    # =========================================================================
    # PAYOFF DIAGRAM
    # =========================================================================
    
    @app.callback(
        Output("options-bots-payoff-diagram", "figure"),
        [
            Input("options-bots-template-select", "value"),
            Input("options-bots-symbol-select", "value"),
        ],
    )
    def update_payoff_diagram(template, symbol):
        """Generate the payoff diagram for the selected strategy."""
        import numpy as np
        
        fig = go.Figure()
        
        # Get approx price for the symbol (default to 200)
        spot = 200
        strikes = None
        
        if template == "rsi_put_spread":
            # Short Put Spread: Sell Put at ATM, Buy Put OTM
            sell_strike = spot
            buy_strike = spot - 10
            strikes = [buy_strike, sell_strike]
            premium_received = 1.50  # Example net credit
            
            prices = np.linspace(spot * 0.85, spot * 1.15, 100)
            payoff = np.where(
                prices < buy_strike,
                -(sell_strike - buy_strike) + premium_received,
                np.where(
                    prices < sell_strike,
                    -(sell_strike - prices) + premium_received,
                    premium_received
                )
            )
            payoff = payoff * 100  # Per contract
            
            fig.add_trace(go.Scatter(x=prices, y=payoff, mode='lines', name='Short Put Spread', line=dict(color='#28a745', width=3)))
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            fig.add_vline(x=sell_strike, line_dash="dash", line_color="red", annotation_text=f"Sell Put ${sell_strike}")
            fig.add_vline(x=buy_strike, line_dash="dash", line_color="blue", annotation_text=f"Buy Put ${buy_strike}")
            
        elif template == "vix_iron_condor":
            # Iron Condor: Short Call Spread + Short Put Spread
            put_buy = spot - 20
            put_sell = spot - 10
            call_sell = spot + 10
            call_buy = spot + 20
            strikes = [put_buy, put_sell, call_sell, call_buy]
            premium_received = 2.00
            
            prices = np.linspace(spot * 0.80, spot * 1.20, 100)
            
            # Put spread payoff (short)
            put_payoff = np.where(
                prices < put_buy,
                -(put_sell - put_buy),
                np.where(
                    prices < put_sell,
                    -(put_sell - prices),
                    0
                )
            )
            
            # Call spread payoff (short)
            call_payoff = np.where(
                prices > call_buy,
                -(call_buy - call_sell),
                np.where(
                    prices > call_sell,
                    -(prices - call_sell),
                    0
                )
            )
            
            payoff = (put_payoff + call_payoff + premium_received) * 100
            
            fig.add_trace(go.Scatter(x=prices, y=payoff, mode='lines', name='Iron Condor', line=dict(color='#007bff', width=3)))
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            
        elif template == "earnings_strangle":
            # Long Strangle
            put_strike = spot - 10
            call_strike = spot + 10
            premium_paid = 4.00
            
            prices = np.linspace(spot * 0.80, spot * 1.20, 100)
            put_payoff = np.maximum(put_strike - prices, 0)
            call_payoff = np.maximum(prices - call_strike, 0)
            payoff = (put_payoff + call_payoff - premium_paid) * 100
            
            fig.add_trace(go.Scatter(x=prices, y=payoff, mode='lines', name='Long Strangle', line=dict(color='#ffc107', width=3)))
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            
        elif template == "momentum_call_spread":
            # Bull Call Spread
            buy_strike = spot - 5  # ATM/ITM call
            sell_strike = spot + 10  # OTM call
            premium_paid = 3.50  # Net debit
            
            prices = np.linspace(spot * 0.80, spot * 1.20, 100)
            long_call = np.maximum(prices - buy_strike, 0)
            short_call = np.maximum(prices - sell_strike, 0)
            payoff = (long_call - short_call - premium_paid) * 100
            
            fig.add_trace(go.Scatter(x=prices, y=payoff, mode='lines', name='Bull Call Spread', line=dict(color='#17a2b8', width=3)))
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            fig.add_vline(x=buy_strike, line_dash="dash", line_color="green", annotation_text=f"Buy ${buy_strike}")
            fig.add_vline(x=sell_strike, line_dash="dash", line_color="red", annotation_text=f"Sell ${sell_strike}")
            
        elif template == "protective_collar":
            # Protective Collar: Long Stock + Long Put + Short Call
            stock_price = spot
            put_strike = spot - 10  # Protective put
            call_strike = spot + 10  # Covered call
            net_credit = 0.50  # Slight credit from call > put premium
            
            prices = np.linspace(spot * 0.70, spot * 1.30, 100)
            stock_pnl = prices - stock_price
            long_put = np.maximum(put_strike - prices, 0)
            short_call = -np.maximum(prices - call_strike, 0)
            payoff = (stock_pnl + long_put + short_call + net_credit) * 100
            
            fig.add_trace(go.Scatter(x=prices, y=payoff, mode='lines', name='Collar', line=dict(color='#6f42c1', width=3)))
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            fig.add_vline(x=put_strike, line_dash="dash", line_color="blue", annotation_text=f"Put ${put_strike}")
            fig.add_vline(x=call_strike, line_dash="dash", line_color="orange", annotation_text=f"Call ${call_strike}")
            
        else:
            fig.add_annotation(text="Select a strategy template", x=0.5, y=0.5, showarrow=False, font=dict(size=16))
        
        fig.update_layout(
            title=f"{template.replace('_', ' ').title()} Payoff at Expiration",
            xaxis_title="Underlying Price at Expiration ($)",
            yaxis_title="Profit / Loss ($)",
            template="plotly_white",
            margin=dict(l=50, r=20, t=50, b=50),
            showlegend=True,
        )
        
        return fig
    
    # =========================================================================
    # 3D VOLATILITY SURFACE
    # =========================================================================
    
    @app.callback(
        Output("options-bots-vol-surface", "figure"),
        [
            Input("options-bots-symbol-select", "value"),
            Input("options-bots-surface-angle", "value"),
            Input("options-bots-surface-color", "value"),
        ],
    )
    def update_vol_surface(symbol, angle, colorscale):
        """Update 3D volatility surface visualization."""
        try:
            # Generate mock volatility surface data
            # In production, this would fetch real IV data from options chain
            spot = {"GLD": 175, "SPY": 600, "QQQ": 520, "IWM": 200, "TLT": 90}.get(symbol, 100)
            
            # Create meshgrid for strikes and days to expiration
            strikes = np.linspace(spot * 0.85, spot * 1.15, 25)
            dtes = np.array([7, 14, 21, 30, 45, 60, 90, 120])
            
            X, Y = np.meshgrid(strikes, dtes)
            
            # Generate realistic IV surface (smile + term structure)
            # Moneyness effect (smile)
            moneyness = (X - spot) / spot
            smile = 0.20 + 0.15 * moneyness**2  # U-shaped smile
            
            # Term structure effect (contango)
            term_structure = 0.05 * np.log(Y / 30 + 1)
            
            # Add some randomness for realism
            np.random.seed(42)  # Consistent for demo
            noise = np.random.normal(0, 0.01, X.shape)
            
            Z = smile + term_structure + noise
            Z = np.clip(Z, 0.10, 0.80)  # Cap IV between 10% and 80%
            
            # Create 3D surface
            fig = go.Figure(data=[go.Surface(
                x=X, y=Y, z=Z * 100,  # Convert to percentage
                colorscale=colorscale or 'Viridis',
                colorbar=dict(
                    title="IV %",
                    titlefont=dict(color='#e6eef8'),
                    tickfont=dict(color='#e6eef8'),
                ),
                contours=dict(
                    z=dict(show=True, highlightcolor="limegreen", project_z=True)
                ),
            )])
            
            # Camera angle
            angle_rad = np.radians(angle or 45)
            fig.update_layout(
                title=dict(
                    text=f"{symbol} Volatility Surface",
                    font=dict(color='#e6eef8', size=14),
                ),
                scene=dict(
                    xaxis=dict(
                        title="Strike Price ($)",
                        backgroundcolor="rgba(30,30,30,0.8)",
                        gridcolor="rgba(255,255,255,0.1)",
                        tickfont=dict(color='#e6eef8'),
                        titlefont=dict(color='#e6eef8'),
                    ),
                    yaxis=dict(
                        title="Days to Expiration",
                        backgroundcolor="rgba(30,30,30,0.8)",
                        gridcolor="rgba(255,255,255,0.1)",
                        tickfont=dict(color='#e6eef8'),
                        titlefont=dict(color='#e6eef8'),
                    ),
                    zaxis=dict(
                        title="Implied Volatility (%)",
                        backgroundcolor="rgba(30,30,30,0.8)",
                        gridcolor="rgba(255,255,255,0.1)",
                        tickfont=dict(color='#e6eef8'),
                        titlefont=dict(color='#e6eef8'),
                    ),
                    camera=dict(
                        eye=dict(
                            x=1.5 * np.cos(angle_rad),
                            y=1.5 * np.sin(angle_rad),
                            z=1.2
                        )
                    ),
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=40, b=0),
                height=400,
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error updating vol surface: {e}")
            fig = go.Figure()
            fig.add_annotation(text=f"Error: {str(e)}", x=0.5, y=0.5, showarrow=False)
            return fig
    
    @app.callback(
        [
            Output("options-bots-list-container", "children", allow_duplicate=True),
            Output("options-bots-active-bots-store", "data"),
            Output("options-bots-create-status", "children"),
            Output("options-bots-toast", "is_open"),
            Output("options-bots-toast", "children"),
            Output("options-bots-toast", "icon"),
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
            return no_update, no_update, no_update, False, "", "info"
        
        try:
            scheduler = get_options_scheduler()
            symbol = symbol or "SPY"
            
            # Create recipe based on template using factory functions
            if template == "rsi_put_spread":
                recipe = create_short_put_spread_recipe(
                    symbol=symbol,
                    rsi_threshold=float(rsi_threshold or 40),
                )
            elif template == "vix_iron_condor":
                recipe = create_iron_condor_recipe(symbol=symbol)
            elif template == "iron_butterfly":
                recipe = create_iron_butterfly_recipe(symbol=symbol)
            elif template == "bull_put_spread":
                recipe = create_bull_put_spread_recipe(
                    symbol=symbol,
                    rsi_threshold=float(rsi_threshold or 35),
                )
            elif template == "bear_call_spread":
                recipe = create_bear_call_spread_recipe(
                    symbol=symbol,
                    rsi_threshold=float(rsi_threshold or 70),
                )
            elif template == "calendar_spread":
                recipe = create_calendar_spread_recipe(symbol=symbol)
            elif template == "long_straddle":
                recipe = create_long_straddle_recipe(symbol=symbol)
            elif template == "short_strangle":
                recipe = create_short_strangle_recipe(symbol=symbol)
            elif template == "wheel_strategy":
                recipe = create_wheel_strategy_recipe(symbol=symbol)
            elif template == "covered_call":
                recipe = create_covered_call_recipe(symbol=symbol)
            elif template == "delta_neutralizer":
                recipe = create_delta_neutralizer_recipe(symbol=symbol)
            elif template == "vix_hedge":
                recipe = create_vix_hedge_recipe()
            else:
                status_msg = dbc.Alert([
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    f"Template '{template}' not supported yet. Please select a valid strategy template."
                ], color="warning")
                return no_update, no_update, status_msg, True, "Template not supported", "warning"
            
            # Create bot
            paper_mode = "paper" in (options or [])
            bot_id = scheduler.create_bot(
                name=name or f"{symbol} {template.replace('_', ' ').title()} Bot",
                recipe=recipe,
                symbol=symbol,
                check_interval=int(check_interval or 60),
                paper_mode=paper_mode,
            )
            
            # Auto-start if selected
            auto_started = False
            if "auto_start" in (options or []):
                scheduler.start_bot(bot_id)
                auto_started = True
            
            # Return updated bot list
            all_bots = scheduler.get_all_bots_status()
            bot_list_ui = _render_bot_list(all_bots)
            
            # Success status message
            status_msg = dbc.Alert([
                html.I(className="fas fa-check-circle me-2"),
                html.Strong("Bot Created Successfully!"),
                html.Br(),
                html.Small([
                    f"Bot ID: {bot_id[:8]}... | Symbol: {symbol} | Template: {template}",
                    html.Br(),
                    f"Mode: {'Paper' if paper_mode else 'Live'} | Status: {'Running' if auto_started else 'Stopped'}",
                    html.Br(),
                    html.A("View in Active Bots tab →", href="#", id="go-to-active-bots", className="text-white"),
                ]),
            ], color="success", className="mt-3")
            
            toast_msg = f"✅ Bot '{name or symbol + ' Bot'}' created successfully!"
            
            return bot_list_ui, [b["bot_id"] for b in all_bots], status_msg, True, toast_msg, "success"
            
        except Exception as e:
            logger.error(f"Error creating bot: {e}")
            import traceback
            traceback.print_exc()
            
            status_msg = dbc.Alert([
                html.I(className="fas fa-times-circle me-2"),
                html.Strong("Error Creating Bot"),
                html.Br(),
                html.Small(str(e)),
            ], color="danger", className="mt-3")
            
            return no_update, no_update, status_msg, True, f"❌ Error: {str(e)}", "danger"
    
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
            scheduler = get_options_scheduler()
            all_bots = scheduler.get_all_bots_status()
            
            # Collect all closed trades with P&L
            all_pnls = []
            strategy_pnls = {"Put Spread": [], "Iron Condor": [], "Strangle": []}
            
            for bot in all_bots:
                trades = bot.get("trade_history", [])
                for trade in trades:
                    pnl = trade.get("pnl")
                    if pnl is not None:
                        all_pnls.append(pnl)
                        strategy = trade.get("strategy", "Other")
                        if "Put" in strategy:
                            strategy_pnls["Put Spread"].append(pnl)
                        elif "Condor" in strategy:
                            strategy_pnls["Iron Condor"].append(pnl)
                        else:
                            strategy_pnls["Strangle"].append(pnl)
            
            # Use demo data if no real trades
            if not all_pnls:
                all_pnls = [80, -25, 120, 95, -40, 65, 110, -15, 75, 55]
                strategy_pnls = {
                    "Put Spread": [80, 95, 65, 75],
                    "Iron Condor": [120, -40, 110, 55],
                    "Strangle": [-25, -15]
                }
            
            # Calculate metrics
            wins = [p for p in all_pnls if p > 0]
            losses = [p for p in all_pnls if p < 0]
            
            win_rate = f"{len(wins) / len(all_pnls) * 100:.1f}%" if all_pnls else "0%"
            avg_win = f"${np.mean(wins):.2f}" if wins else "$0"
            avg_loss = f"${np.mean(losses):.2f}" if losses else "$0"
            
            gross_profit = sum(wins)
            gross_loss = abs(sum(losses))
            profit_factor = f"{gross_profit / gross_loss:.2f}" if gross_loss > 0 else "∞"
            
            # P&L Chart - Cumulative
            dates = [f"Week {i+1}" for i in range(len(all_pnls))]
            cumulative = np.cumsum(all_pnls)
            
            pnl_fig = go.Figure()
            pnl_fig.add_trace(go.Scatter(
                x=dates,
                y=cumulative,
                mode="lines+markers",
                name="Cumulative P&L",
                line=dict(color="#00d4aa", width=3),
                fill='tozeroy',
                fillcolor='rgba(0, 212, 170, 0.2)',
            ))
            pnl_fig.add_hline(y=0, line_dash="dash", line_color="gray")
            pnl_fig.update_layout(
                margin=dict(l=40, r=20, t=30, b=40),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(30,30,30,0.8)",
                font=dict(color="#e6eef8"),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)", title="P&L ($)"),
                title=dict(text="Cumulative P&L", font=dict(size=14)),
            )
            
            # Strategy Chart
            strategy_totals = {k: sum(v) for k, v in strategy_pnls.items()}
            colors = ["#00d4aa" if v > 0 else "#ff6b6b" for v in strategy_totals.values()]
            
            strategy_fig = go.Figure()
            strategy_fig.add_trace(go.Bar(
                x=list(strategy_totals.keys()),
                y=list(strategy_totals.values()),
                marker_color=colors,
            ))
            strategy_fig.update_layout(
                margin=dict(l=40, r=20, t=30, b=40),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(30,30,30,0.8)",
                font=dict(color="#e6eef8"),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)", title="P&L ($)"),
                title=dict(text="P&L by Strategy", font=dict(size=14)),
            )
            
            return win_rate, avg_win, avg_loss, profit_factor, pnl_fig, strategy_fig
            
        except Exception as e:
            logger.error(f"Error updating performance: {e}")
            return "--", "--", "--", "--", {}, {}
    
    # =========================================================================
    # TRADE HISTORY
    # =========================================================================
    
    @app.callback(
        Output("options-bots-trade-table", "children"),
        [
            Input("options-bots-tabs", "active_tab"),
            Input("options-bots-refresh-interval", "n_intervals"),
        ],
    )
    def update_trade_history(active_tab, n_intervals):
        """Update trade history table."""
        if active_tab != "tab-bots-history":
            return no_update
        
        try:
            scheduler = get_options_scheduler()
            all_bots = scheduler.get_all_bots_status()
            
            # Collect all trades from all bots
            all_trades = []
            for bot in all_bots:
                trades = bot.get("trade_history", [])
                for trade in trades:
                    trade["bot_name"] = bot.get("name", "Unknown")
                    all_trades.append(trade)
            
            if not all_trades:
                # Show demo data if no real trades
                demo_trades = [
                    {"timestamp": "2025-12-30 10:15:32", "bot_name": "GLD RSI Bot", "symbol": "GLD", 
                     "action": "OPEN", "strategy": "Short Put Spread", "strike": "175/170", "quantity": 1, 
                     "premium": 1.25, "status": "Filled", "pnl": None},
                    {"timestamp": "2025-12-29 14:30:15", "bot_name": "GLD RSI Bot", "symbol": "GLD",
                     "action": "CLOSE", "strategy": "Short Put Spread", "strike": "180/175", "quantity": 1,
                     "premium": 0.45, "status": "Filled", "pnl": 80.00},
                    {"timestamp": "2025-12-28 09:45:00", "bot_name": "SPY Iron Condor", "symbol": "SPY",
                     "action": "OPEN", "strategy": "Iron Condor", "strike": "590/585-610/615", "quantity": 2,
                     "premium": 2.10, "status": "Filled", "pnl": None},
                ]
                all_trades = demo_trades
            
            # Sort by timestamp (most recent first)
            all_trades.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            # Build table
            table_header = html.Thead(html.Tr([
                html.Th("Time"),
                html.Th("Bot"),
                html.Th("Symbol"),
                html.Th("Action"),
                html.Th("Strategy"),
                html.Th("Strike"),
                html.Th("Qty"),
                html.Th("Premium"),
                html.Th("Status"),
                html.Th("P&L"),
            ]))
            
            rows = []
            for trade in all_trades[:50]:  # Limit to 50 most recent
                pnl = trade.get("pnl")
                pnl_class = "text-success" if pnl and pnl > 0 else "text-danger" if pnl and pnl < 0 else ""
                pnl_text = f"${pnl:+.2f}" if pnl is not None else "--"
                
                action_badge = dbc.Badge(
                    trade.get("action", "--"),
                    color="success" if trade.get("action") == "OPEN" else "warning",
                    className="me-1"
                )
                status_badge = dbc.Badge(
                    trade.get("status", "--"),
                    color="success" if trade.get("status") == "Filled" else "secondary",
                )
                
                rows.append(html.Tr([
                    html.Td(trade.get("timestamp", "--")[:16]),
                    html.Td(trade.get("bot_name", "--")),
                    html.Td(html.Span(trade.get("symbol", "--"), className="badge bg-primary")),
                    html.Td(action_badge),
                    html.Td(trade.get("strategy", "--")),
                    html.Td(trade.get("strike", "--")),
                    html.Td(str(trade.get("quantity", "--"))),
                    html.Td(f"${trade.get('premium', 0):.2f}"),
                    html.Td(status_badge),
                    html.Td(html.Span(pnl_text, className=pnl_class)),
                ]))
            
            table = dbc.Table(
                [table_header, html.Tbody(rows)],
                striped=True, bordered=True, hover=True, responsive=True,
                className="table-dark"
            )
            
            return table
            
        except Exception as e:
            logger.error(f"Error updating trade history: {e}")
            return html.Div([
                dbc.Alert(f"Error loading trades: {str(e)}", color="danger"),
            ])
    
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
    """Render the bot list UI with detailed trade information."""
    if not bots:
        return html.Div([
            html.Div([
                html.I(className="fas fa-robot fa-3x text-muted mb-3"),
                html.H5("No Active Bots", className="text-muted"),
                html.P("Use the 'Create Bot' tab to set up your first trading bot.", 
                       className="text-muted"),
            ], className="text-center my-5"),
        ])
    
    bot_cards = []
    for bot in bots:
        bot_id = bot.get("bot_id", "")
        is_running = bot.get("is_running", False)
        stats = bot.get("stats", {})
        trades = bot.get("recent_trades", []) or bot.get("trades", []) or []
        recent_activity = bot.get("recent_events", []) or bot.get("recent_activity", []) or []
        
        # Status badge
        status_badge = dbc.Badge(
            "🟢 Running" if is_running else "🔴 Stopped",
            color="success" if is_running else "secondary",
            className="ms-2"
        )
        
        # Paper mode badge
        paper_badge = dbc.Badge(
            "📄 Paper",
            color="info",
            className="ms-1"
        ) if bot.get("paper_mode", True) else dbc.Badge(
            "💵 Live",
            color="warning",
            className="ms-1"
        )
        
        # Calculate P&L
        total_pnl = sum(t.get("pnl", 0) or 0 for t in trades)
        pnl_class = "text-success" if total_pnl > 0 else "text-danger" if total_pnl < 0 else "text-muted"
        pnl_icon = "fa-arrow-up" if total_pnl > 0 else "fa-arrow-down" if total_pnl < 0 else "fa-minus"
        
        # Recent trades display (last 5)
        recent_trades = trades[:5] if trades else []
        trade_rows = []
        for trade in recent_trades:
            action_color = "success" if trade.get("action") == "OPEN" else "warning"
            pnl = trade.get("pnl")
            pnl_text = f"${pnl:+.2f}" if pnl is not None else "--"
            timestamp = trade.get("timestamp", trade.get("created_at", "--"))
            if timestamp and len(str(timestamp)) > 10:
                timestamp = str(timestamp)[:10]
            trade_rows.append(
                html.Tr([
                    html.Td(timestamp, className="small"),
                    html.Td(dbc.Badge(trade.get("action", "--"), color=action_color, pill=True)),
                    html.Td(str(trade.get("strategy", "--"))[:15], className="small"),
                    html.Td(f"${trade.get('premium', trade.get('price', 0)):.2f}", className="small"),
                    html.Td(
                        html.Span(pnl_text, className="text-success" if pnl and pnl > 0 else "text-danger" if pnl else ""),
                        className="small"
                    ),
                    html.Td(
                        dbc.Badge(trade.get("status", "Pending"), 
                                 color="success" if trade.get("status") == "Filled" else "secondary",
                                 pill=True),
                        className="small"
                    ),
                ], className="small")
            )
        
        # Trade history table
        trade_table = None
        if trade_rows:
            trade_table = dbc.Table([
                html.Thead(html.Tr([
                    html.Th("Date", className="small"),
                    html.Th("Action", className="small"),
                    html.Th("Strategy", className="small"),
                    html.Th("Premium", className="small"),
                    html.Th("P&L", className="small"),
                    html.Th("Status", className="small"),
                ])),
                html.Tbody(trade_rows)
            ], bordered=True, hover=True, size="sm", className="mb-0 mt-2")
        else:
            trade_table = html.Div([
                html.Small("No trades executed yet", className="text-muted fst-italic")
            ], className="mt-2 text-center py-2 bg-dark rounded")
        
        # Activity log from events
        activity_log = []
        for activity in recent_activity[:3]:
            event_msg = activity.get("message", str(activity)) if isinstance(activity, dict) else str(activity)
            activity_log.append(
                html.Div([
                    html.I(className="fas fa-circle text-primary me-2", style={"fontSize": "6px"}),
                    html.Small(event_msg[:50], className="text-muted"),
                ], className="d-flex align-items-center mb-1")
            )
        
        card = dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col([
                        html.H5([
                            html.I(className="fas fa-robot me-2 text-primary"),
                            bot.get("name", "Unknown Bot"),
                            status_badge,
                            paper_badge,
                        ], className="mb-0"),
                    ], md=8),
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
                                html.I(className="fas fa-eye"),
                                id={"type": "options-bot-details", "index": bot_id},
                                color="secondary",
                                size="sm",
                                title="View Details",
                            ),
                            dbc.Button(
                                html.I(className="fas fa-trash"),
                                id={"type": "options-bot-delete", "index": bot_id},
                                color="danger",
                                size="sm",
                                title="Delete",
                            ),
                        ]),
                    ], md=4, className="text-end"),
                ]),
            ], className="bg-dark"),
            dbc.CardBody([
                # Bot Info Row
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.Span(bot.get("symbol", "--"), className="badge bg-primary me-2"),
                            html.Span(bot.get("template", bot.get("status", "--")), className="badge bg-secondary me-2"),
                            html.Small(f"ID: {bot_id[:8]}...", className="text-muted"),
                        ]),
                    ], md=12, className="mb-3"),
                ]),
                
                # Stats Row
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.Div([
                                    html.I(className="fas fa-search text-info me-2"),
                                    html.Small("Checks", className="text-muted"),
                                ], className="d-flex align-items-center"),
                                html.H4(str(stats.get("total_checks", 0)), className="mb-0 mt-1"),
                            ], className="p-2 text-center"),
                        ], className="bg-dark border-secondary"),
                    ], md=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.Div([
                                    html.I(className="fas fa-check-circle text-success me-2"),
                                    html.Small("Conditions Met", className="text-muted"),
                                ], className="d-flex align-items-center"),
                                html.H4(str(stats.get("conditions_met", 0)), className="mb-0 mt-1"),
                            ], className="p-2 text-center"),
                        ], className="bg-dark border-secondary"),
                    ], md=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.Div([
                                    html.I(className="fas fa-exchange-alt text-warning me-2"),
                                    html.Small("Trades", className="text-muted"),
                                ], className="d-flex align-items-center"),
                                html.H4(str(stats.get("trades_executed", 0)), className="mb-0 mt-1"),
                            ], className="p-2 text-center"),
                        ], className="bg-dark border-secondary"),
                    ], md=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.Div([
                                    html.I(className=f"fas {pnl_icon} {pnl_class} me-2"),
                                    html.Small("Total P&L", className="text-muted"),
                                ], className="d-flex align-items-center"),
                                html.H4(f"${total_pnl:+.2f}", className=f"mb-0 mt-1 {pnl_class}"),
                            ], className="p-2 text-center"),
                        ], className="bg-dark border-secondary"),
                    ], md=3),
                ], className="mb-3"),
                
                # Trade History Section
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.H6([
                                html.I(className="fas fa-history me-2"),
                                "Recent Trades"
                            ], className="mb-0"),
                        ]),
                        trade_table,
                    ], md=8),
                    dbc.Col([
                        html.Div([
                            html.H6([
                                html.I(className="fas fa-bell me-2"),
                                "Activity Log"
                            ], className="mb-2"),
                        ]),
                        html.Div(
                            activity_log if activity_log else [
                                html.Small("No recent activity", className="text-muted fst-italic")
                            ],
                            className="bg-dark rounded p-2"
                        ),
                        html.Hr(className="my-2"),
                        html.Div([
                            html.Small([
                                html.I(className="fas fa-clock me-1"),
                                f"Interval: {bot.get('check_interval', 60)}s"
                            ], className="text-muted d-block"),
                            html.Small([
                                html.I(className="fas fa-calendar me-1"),
                                f"Created: {str(bot.get('created_at', '--'))[:10] if bot.get('created_at') else '--'}"
                            ], className="text-muted d-block"),
                        ], className="mt-2"),
                    ], md=4),
                ]),
            ]),
        ], className="mb-3 border-primary")
        bot_cards.append(card)
    
    return html.Div(bot_cards)


# Import dash for pattern matching callbacks
import dash

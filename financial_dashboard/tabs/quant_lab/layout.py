"""
Phase 3: Quant Lab Dashboard Layout

Provides unified UI for:
- RL Trading Agent (PPO/A2C/DQN)
- QLib Factor Analysis
- Deep Hedging vs. Black-Scholes

Author: Agent-P3
Date: December 28, 2025
"""

import os
from dash import html, dcc, callback, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ========== LAYOUT COMPONENTS ==========

def create_rl_agent_tab():
    """Create RL Trading Agent tab content."""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-robot me-2"),
            "🤖 RL Trading Agent"
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Ticker Symbol"),
                    dbc.Input(
                        id="phase3-rl-ticker-input",
                        type="text",
                        value="SPY",
                        placeholder="Enter ticker..."
                    )
                ], md=3),
                dbc.Col([
                    dbc.Label("Algorithm"),
                    dcc.Dropdown(
                        id="phase3-rl-algorithm",
                        options=[
                            {"label": "PPO (Proximal Policy Optimization)", "value": "PPO"},
                            {"label": "A2C (Advantage Actor-Critic)", "value": "A2C"},
                            {"label": "DQN (Deep Q-Network)", "value": "DQN"}
                        ],
                        value="PPO"
                    )
                ], md=3),
                dbc.Col([
                    dbc.Label("Training Episodes"),
                    dbc.Input(
                        id="phase3-rl-episodes",
                        type="number",
                        value=50,
                        min=10,
                        max=500
                    )
                ], md=2),
                dbc.Col([
                    dbc.Label("Action"),
                    dbc.Button(
                        "Train Agent",
                        id="phase3-rl-train-btn",
                        color="primary",
                        className="w-100"
                    )
                ], md=2),
                dbc.Col([
                    dbc.Label("Status"),
                    html.Div(id="phase3-rl-status", className="text-muted")
                ], md=2)
            ], className="mb-3"),
            
            # Metrics cards
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Total Return", className="text-muted"),
                            html.H4(id="phase3-rl-return", children="--")
                        ])
                    ], color="light")
                ], md=2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Sharpe Ratio", className="text-muted"),
                            html.H4(id="phase3-rl-sharpe", children="--")
                        ])
                    ], color="light")
                ], md=2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Max Drawdown", className="text-muted"),
                            html.H4(id="phase3-rl-maxdd", children="--")
                        ])
                    ], color="light")
                ], md=2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Win Rate", className="text-muted"),
                            html.H4(id="phase3-rl-winrate", children="--")
                        ])
                    ], color="light")
                ], md=2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Total Trades", className="text-muted"),
                            html.H4(id="phase3-rl-trades", children="--")
                        ])
                    ], color="light")
                ], md=2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Final Value", className="text-muted"),
                            html.H4(id="phase3-rl-final", children="--")
                        ])
                    ], color="light")
                ], md=2)
            ], className="mb-3"),
            
            # Charts
            dbc.Row([
                dbc.Col([
                    dcc.Graph(id="phase3-rl-equity-chart", style={"height": "350px"})
                ], md=8),
                dbc.Col([
                    dcc.Graph(id="phase3-rl-action-chart", style={"height": "350px"})
                ], md=4)
            ])
        ])
    ])


def create_qlib_factor_tab():
    """Create QLib Factor Analysis tab content."""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-chart-pie me-2"),
            "📊 Factor Analysis"
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Ticker Symbol"),
                    dbc.Input(
                        id="phase3-qlib-ticker-input",
                        type="text",
                        value="AAPL",
                        placeholder="Enter ticker..."
                    )
                ], md=3),
                dbc.Col([
                    dbc.Label("Factor Weights"),
                    dcc.Dropdown(
                        id="phase3-qlib-weights",
                        options=[
                            {"label": "Equal Weighted", "value": "equal"},
                            {"label": "Momentum Tilted", "value": "momentum"},
                            {"label": "Value Tilted", "value": "value"},
                            {"label": "Quality Focus", "value": "quality"}
                        ],
                        value="equal"
                    )
                ], md=3),
                dbc.Col([
                    dbc.Label("Action"),
                    dbc.Button(
                        "Analyze Factors",
                        id="phase3-qlib-analyze-btn",
                        color="success",
                        className="w-100"
                    )
                ], md=2),
                dbc.Col([
                    dbc.Label("Status"),
                    html.Div(id="phase3-qlib-status", className="text-muted")
                ], md=4)
            ], className="mb-3"),
            
            # Alpha and recommendation
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Alpha Score", className="text-muted"),
                            html.H3(id="phase3-qlib-alpha", children="--"),
                            html.Small(id="phase3-qlib-direction", className="text-info")
                        ])
                    ], color="light")
                ], md=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Recommendation", className="text-muted"),
                            html.H3(id="phase3-qlib-recommendation", children="--"),
                            html.Small(id="phase3-qlib-confidence", className="text-success")
                        ])
                    ], color="light")
                ], md=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Expected Return", className="text-muted"),
                            html.H3(id="phase3-qlib-expected-return", children="--")
                        ])
                    ], color="light")
                ], md=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Risk Score", className="text-muted"),
                            html.H3(id="phase3-qlib-risk", children="--")
                        ])
                    ], color="light")
                ], md=3)
            ], className="mb-3"),
            
            # Charts
            dbc.Row([
                dbc.Col([
                    dcc.Graph(id="phase3-qlib-exposure-chart", style={"height": "300px"})
                ], md=6),
                dbc.Col([
                    dcc.Graph(id="phase3-qlib-radar-chart", style={"height": "300px"})
                ], md=6)
            ]),
            
            # Factor details table
            dbc.Row([
                dbc.Col([
                    html.H6("Factor Details", className="mt-3 mb-2"),
                    html.Div(id="phase3-qlib-factor-table")
                ])
            ])
        ])
    ])


def create_deep_hedge_tab():
    """Create Deep Hedging tab content."""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-shield-alt me-2"),
            "🛡️ Deep Hedging"
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Underlying"),
                    dbc.Input(
                        id="phase3-hedge-ticker-input",
                        type="text",
                        value="SPY",
                        placeholder="Enter ticker..."
                    )
                ], md=2),
                dbc.Col([
                    dbc.Label("Maturity (Days)"),
                    dbc.Input(
                        id="phase3-hedge-maturity",
                        type="number",
                        value=30,
                        min=7,
                        max=365
                    )
                ], md=2),
                dbc.Col([
                    dbc.Label("Volatility (%)"),
                    dbc.Input(
                        id="phase3-hedge-volatility",
                        type="number",
                        value=25,
                        min=5,
                        max=100
                    )
                ], md=2),
                dbc.Col([
                    dbc.Label("Trans. Cost (bps)"),
                    dbc.Input(
                        id="phase3-hedge-cost",
                        type="number",
                        value=10,
                        min=1,
                        max=50
                    )
                ], md=2),
                dbc.Col([
                    dbc.Label("Simulation Paths"),
                    dbc.Input(
                        id="phase3-hedge-paths",
                        type="number",
                        value=500,
                        min=100,
                        max=5000
                    )
                ], md=2),
                dbc.Col([
                    dbc.Label("Action"),
                    dbc.Button(
                        "Run Comparison",
                        id="phase3-hedge-run-btn",
                        color="warning",
                        className="w-100"
                    )
                ], md=2)
            ], className="mb-3"),
            
            # Results metrics
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Deep Hedge PnL", className="text-muted"),
                            html.H4(id="phase3-hedge-deep-pnl", children="--"),
                            html.Small(id="phase3-hedge-deep-std", className="text-info")
                        ])
                    ], color="primary", outline=True)
                ], md=2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("BS Hedge PnL", className="text-muted"),
                            html.H4(id="phase3-hedge-bs-pnl", children="--"),
                            html.Small(id="phase3-hedge-bs-std", className="text-danger")
                        ])
                    ], color="danger", outline=True)
                ], md=2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Deep Costs", className="text-muted"),
                            html.H4(id="phase3-hedge-deep-cost", children="--")
                        ])
                    ], color="light")
                ], md=2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("BS Costs", className="text-muted"),
                            html.H4(id="phase3-hedge-bs-cost", children="--")
                        ])
                    ], color="light")
                ], md=2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Improvement", className="text-muted"),
                            html.H4(id="phase3-hedge-improvement", children="--", className="text-success")
                        ])
                    ], color="success", outline=True)
                ], md=2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Strike / Spot", className="text-muted"),
                            html.H4(id="phase3-hedge-strike", children="--")
                        ])
                    ], color="light")
                ], md=2)
            ], className="mb-3"),
            
            # Charts
            dbc.Row([
                dbc.Col([
                    dcc.Graph(id="phase3-hedge-delta-chart", style={"height": "300px"})
                ], md=6),
                dbc.Col([
                    dcc.Graph(id="phase3-hedge-pnl-chart", style={"height": "300px"})
                ], md=6)
            ]),
            
            dbc.Row([
                dbc.Col([
                    dcc.Graph(id="phase3-hedge-spot-chart", style={"height": "250px"})
                ])
            ])
        ])
    ])


def create_layout():
    """Create the main Quant Lab layout."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H3([
                    html.I(className="fas fa-atom me-2"),
                    "Quant Lab",
                    dbc.Badge("Phase 3", color="info", className="ms-2")
                ]),
                html.P("Advanced quantitative analysis: RL agents, factor models, and deep hedging.", 
                       className="text-muted")
            ])
        ], className="mb-3"),
        
        dbc.Tabs([
            dbc.Tab(
                create_rl_agent_tab(),
                label="🤖 RL Agent",
                tab_id="phase3-tab-rl"
            ),
            dbc.Tab(
                create_qlib_factor_tab(),
                label="📊 Factors",
                tab_id="phase3-tab-factors"
            ),
            dbc.Tab(
                create_deep_hedge_tab(),
                label="🛡️ Deep Hedge",
                tab_id="phase3-tab-hedge"
            )
        ], id="phase3-quant-tabs", active_tab="phase3-tab-rl"),
        
        # Store for results
        dcc.Store(id="phase3-rl-store"),
        dcc.Store(id="phase3-qlib-store"),
        dcc.Store(id="phase3-hedge-store")
    ], fluid=True)


# ========== CALLBACKS ==========

def register_callbacks(app):
    """Register all Phase 3 callbacks."""
    
    @app.callback(
        [
            Output("phase3-rl-status", "children"),
            Output("phase3-rl-return", "children"),
            Output("phase3-rl-sharpe", "children"),
            Output("phase3-rl-maxdd", "children"),
            Output("phase3-rl-winrate", "children"),
            Output("phase3-rl-trades", "children"),
            Output("phase3-rl-final", "children"),
            Output("phase3-rl-equity-chart", "figure"),
            Output("phase3-rl-action-chart", "figure"),
            Output("phase3-rl-store", "data")
        ],
        [Input("phase3-rl-train-btn", "n_clicks")],
        [
            State("phase3-rl-ticker-input", "value"),
            State("phase3-rl-algorithm", "value"),
            State("phase3-rl-episodes", "value")
        ],
        prevent_initial_call=True
    )
    def update_rl_agent(n_clicks, ticker, algorithm, episodes):
        """Train RL agent and update dashboard."""
        if not n_clicks or not ticker:
            return [no_update] * 10
        
        try:
            from financial_dashboard.engines.rl_trading_agent import get_rl_trading_agent
            
            agent = get_rl_trading_agent(algorithm)
            result = agent.train(ticker, episodes=episodes or 50)
            chart_data = agent.get_chart_data(result)
            
            # Equity curve chart
            equity_fig = go.Figure()
            equity_fig.add_trace(go.Scatter(
                x=chart_data['equity_curve']['x'],
                y=chart_data['equity_curve']['y'],
                mode='lines',
                name='Portfolio Value',
                line=dict(color='#2196F3', width=2)
            ))
            
            # Add buy/sell markers
            if chart_data['buy_markers']['x']:
                equity_fig.add_trace(go.Scatter(
                    x=chart_data['buy_markers']['x'],
                    y=chart_data['buy_markers']['y'],
                    mode='markers',
                    name='Buy',
                    marker=dict(color='green', size=8, symbol='triangle-up')
                ))
            
            if chart_data['sell_markers']['x']:
                equity_fig.add_trace(go.Scatter(
                    x=chart_data['sell_markers']['x'],
                    y=chart_data['sell_markers']['y'],
                    mode='markers',
                    name='Sell',
                    marker=dict(color='red', size=8, symbol='triangle-down')
                ))
            
            equity_fig.update_layout(
                title=f"{ticker} - {algorithm} Agent Equity Curve",
                xaxis_title="Time Step",
                yaxis_title="Portfolio Value ($)",
                template="plotly_white",
                margin=dict(l=50, r=50, t=50, b=50)
            )
            
            # Action distribution pie
            action_fig = go.Figure(data=[go.Pie(
                labels=chart_data['action_distribution']['labels'],
                values=chart_data['action_distribution']['values'],
                hole=0.4,
                marker_colors=['gray', 'green', 'red']
            )])
            action_fig.update_layout(
                title="Action Distribution",
                template="plotly_white",
                margin=dict(l=20, r=20, t=50, b=20)
            )
            
            return [
                html.Span("✅ Complete", className="text-success"),
                chart_data['metrics']['total_return'],
                chart_data['metrics']['sharpe_ratio'],
                chart_data['metrics']['max_drawdown'],
                chart_data['metrics']['win_rate'],
                str(chart_data['metrics']['num_trades']),
                f"${result.final_portfolio_value:,.0f}",
                equity_fig,
                action_fig,
                chart_data
            ]
            
        except Exception as e:
            logger.error(f"RL Agent error: {e}")
            empty_fig = go.Figure()
            return [
                html.Span(f"❌ Error: {str(e)[:50]}", className="text-danger"),
                "--", "--", "--", "--", "--", "--",
                empty_fig, empty_fig, None
            ]
    
    @app.callback(
        [
            Output("phase3-qlib-status", "children"),
            Output("phase3-qlib-alpha", "children"),
            Output("phase3-qlib-direction", "children"),
            Output("phase3-qlib-recommendation", "children"),
            Output("phase3-qlib-confidence", "children"),
            Output("phase3-qlib-expected-return", "children"),
            Output("phase3-qlib-risk", "children"),
            Output("phase3-qlib-exposure-chart", "figure"),
            Output("phase3-qlib-radar-chart", "figure"),
            Output("phase3-qlib-factor-table", "children"),
            Output("phase3-qlib-store", "data")
        ],
        [Input("phase3-qlib-analyze-btn", "n_clicks")],
        [
            State("phase3-qlib-ticker-input", "value"),
            State("phase3-qlib-weights", "value")
        ],
        prevent_initial_call=True
    )
    def update_factor_analysis(n_clicks, ticker, weights):
        """Run factor analysis and update dashboard."""
        if not n_clicks or not ticker:
            return [no_update] * 11
        
        try:
            from financial_dashboard.engines.qlib_factor_engine import get_qlib_engine
            
            engine = get_qlib_engine()
            result = engine.analyze(ticker)
            chart_data = engine.get_chart_data(result)
            
            # Exposure bar chart
            exposure_fig = go.Figure()
            colors = ['green' if e > 0 else 'red' for e in chart_data['exposure_bar']['y']]
            exposure_fig.add_trace(go.Bar(
                x=chart_data['exposure_bar']['x'],
                y=chart_data['exposure_bar']['y'],
                marker_color=colors,
                name='Factor Exposure'
            ))
            exposure_fig.update_layout(
                title="Factor Exposures (Z-Score)",
                xaxis_title="Factor",
                yaxis_title="Exposure",
                template="plotly_white",
                margin=dict(l=50, r=50, t=50, b=50)
            )
            
            # Radar chart
            radar_fig = go.Figure()
            radar_fig.add_trace(go.Scatterpolar(
                r=chart_data['radar_data']['r'],
                theta=chart_data['radar_data']['theta'],
                fill='toself',
                name=ticker,
                line_color='#2196F3'
            ))
            radar_fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100])
                ),
                title="Factor Percentiles",
                template="plotly_white",
                margin=dict(l=50, r=50, t=50, b=50)
            )
            
            # Factor details table
            factor_table = dbc.Table([
                html.Thead([
                    html.Tr([
                        html.Th("Factor"),
                        html.Th("Value"),
                        html.Th("Z-Score"),
                        html.Th("Percentile"),
                        html.Th("Signal")
                    ])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td(f['name']),
                        html.Td(f['value']),
                        html.Td(f['z_score']),
                        html.Td(f['percentile']),
                        html.Td(
                            dbc.Badge(
                                f['signal'].upper(),
                                color="success" if f['signal'] == 'bullish' else 
                                      "danger" if f['signal'] == 'bearish' else "secondary"
                            )
                        )
                    ])
                    for f in chart_data['factor_details']
                ])
            ], bordered=True, striped=True, size="sm")
            
            return [
                html.Span("✅ Complete", className="text-success"),
                chart_data['metrics']['alpha_score'],
                chart_data['metrics']['direction'],
                chart_data['metrics']['recommendation'],
                f"Confidence: {chart_data['metrics']['confidence']}",
                chart_data['metrics']['expected_return'],
                chart_data['metrics']['risk_score'],
                exposure_fig,
                radar_fig,
                factor_table,
                chart_data
            ]
            
        except Exception as e:
            logger.error(f"Factor analysis error: {e}")
            empty_fig = go.Figure()
            return [
                html.Span(f"❌ Error: {str(e)[:50]}", className="text-danger"),
                "--", "--", "--", "--", "--", "--",
                empty_fig, empty_fig, None, None
            ]
    
    @app.callback(
        [
            Output("phase3-hedge-deep-pnl", "children"),
            Output("phase3-hedge-deep-std", "children"),
            Output("phase3-hedge-bs-pnl", "children"),
            Output("phase3-hedge-bs-std", "children"),
            Output("phase3-hedge-deep-cost", "children"),
            Output("phase3-hedge-bs-cost", "children"),
            Output("phase3-hedge-improvement", "children"),
            Output("phase3-hedge-strike", "children"),
            Output("phase3-hedge-delta-chart", "figure"),
            Output("phase3-hedge-pnl-chart", "figure"),
            Output("phase3-hedge-spot-chart", "figure"),
            Output("phase3-hedge-store", "data")
        ],
        [Input("phase3-hedge-run-btn", "n_clicks")],
        [
            State("phase3-hedge-ticker-input", "value"),
            State("phase3-hedge-maturity", "value"),
            State("phase3-hedge-volatility", "value"),
            State("phase3-hedge-cost", "value"),
            State("phase3-hedge-paths", "value")
        ],
        prevent_initial_call=True
    )
    def update_deep_hedging(n_clicks, ticker, maturity, volatility, cost, n_paths):
        """Run deep hedging comparison and update dashboard."""
        if not n_clicks or not ticker:
            return [no_update] * 12
        
        try:
            from financial_dashboard.engines.deep_hedging import get_deep_hedging_engine
            
            engine = get_deep_hedging_engine()
            result = engine.run_hedge_comparison(
                ticker=ticker,
                maturity_days=maturity or 30,
                volatility=(volatility or 25) / 100,
                transaction_cost=(cost or 10) / 10000,
                n_paths=n_paths or 500
            )
            chart_data = engine.get_chart_data(result)
            
            # Delta comparison chart
            delta_fig = go.Figure()
            for trace in chart_data['delta_chart']['traces']:
                delta_fig.add_trace(go.Scatter(**trace))
            delta_fig.update_layout(
                title="Delta Comparison: Deep Hedge vs. Black-Scholes",
                xaxis_title="Time Step",
                yaxis_title="Delta",
                template="plotly_white",
                margin=dict(l=50, r=50, t=50, b=50)
            )
            
            # PnL comparison chart
            pnl_fig = go.Figure()
            for trace in chart_data['pnl_chart']['traces']:
                pnl_fig.add_trace(go.Scatter(**trace))
            pnl_fig.update_layout(
                title="Cumulative Hedge PnL Comparison",
                xaxis_title="Time Step",
                yaxis_title="PnL ($)",
                template="plotly_white",
                margin=dict(l=50, r=50, t=50, b=50)
            )
            
            # Spot price chart
            spot_fig = go.Figure()
            spot_fig.add_trace(go.Scatter(
                x=chart_data['spot_chart']['x'],
                y=chart_data['spot_chart']['y'],
                mode='lines',
                name='Spot Price',
                line=dict(color='purple', width=2)
            ))
            # Add strike line
            spot_fig.add_hline(
                y=result.strike,
                line_dash="dash",
                annotation_text=f"Strike: ${result.strike:.0f}",
                line_color="orange"
            )
            spot_fig.update_layout(
                title="Underlying Price Path",
                xaxis_title="Time Step",
                yaxis_title="Price ($)",
                template="plotly_white",
                margin=dict(l=50, r=50, t=50, b=50)
            )
            
            return [
                chart_data['metrics']['deep_pnl'],
                f"Std: {chart_data['metrics']['deep_std']}",
                chart_data['metrics']['bs_pnl'],
                f"Std: {chart_data['metrics']['bs_std']}",
                chart_data['metrics']['deep_costs'],
                chart_data['metrics']['bs_costs'],
                chart_data['metrics']['improvement'],
                f"{chart_data['metrics']['strike']} / {chart_data['metrics']['initial_spot']}",
                delta_fig,
                pnl_fig,
                spot_fig,
                chart_data
            ]
            
        except Exception as e:
            logger.error(f"Deep hedging error: {e}")
            empty_fig = go.Figure()
            return [
                "--", "--", "--", "--", "--", "--", "--", "--",
                empty_fig, empty_fig, empty_fig, None
            ]


# Export layout
layout = create_layout()

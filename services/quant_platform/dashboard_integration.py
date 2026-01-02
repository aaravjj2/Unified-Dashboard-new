"""
Quant Platform Dashboard Integration
Integrates all quant services into the Dash dashboard
"""

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import sys
import os

# Add services to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.quant_platform.market_data_service import MarketDataService
from services.quant_platform.factor_model_service import FactorModelService
from services.quant_platform.options_analytics_service import OptionsAnalyticsService
from services.quant_platform.portfolio_optimizer_service import PortfolioOptimizerService
from services.quant_platform.risk_analytics_service import RiskAnalyticsService
from services.quant_platform.execution_service import ExecutionService
from services.quant_platform.ml_pipeline_service import MLPipelineService
from services.quant_platform.visualization_service import VisualizationService

# Initialize services
market_data = MarketDataService()
factor_model = FactorModelService()
options_analytics = OptionsAnalyticsService()
portfolio_optimizer = PortfolioOptimizerService()
risk_analytics = RiskAnalyticsService()
execution_service = ExecutionService()
ml_pipeline = MLPipelineService()
visualization = VisualizationService()

def create_quant_platform_layout():
    """Create the Quant Platform dashboard layout"""
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H2("🚀 Quant Platform Dashboard", className="text-primary mb-0"),
                html.P("540 Improvements | 29 GitHub Repos Integrated", className="text-muted")
            ], width=12)
        ], className="mb-4"),
        
        # Service Status Cards
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Market Data", className="card-title"),
                        html.Div(id="market-data-status"),
                        dbc.Badge("Active", color="success", className="mt-2")
                    ])
                ], className="h-100")
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Factor Models", className="card-title"),
                        html.Div(id="factor-model-status"),
                        dbc.Badge("Active", color="success", className="mt-2")
                    ])
                ], className="h-100")
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Options", className="card-title"),
                        html.Div(id="options-status"),
                        dbc.Badge("Active", color="success", className="mt-2")
                    ])
                ], className="h-100")
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Portfolio", className="card-title"),
                        html.Div(id="portfolio-status"),
                        dbc.Badge("Active", color="success", className="mt-2")
                    ])
                ], className="h-100")
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Risk", className="card-title"),
                        html.Div(id="risk-status"),
                        dbc.Badge("Active", color="success", className="mt-2")
                    ])
                ], className="h-100")
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("ML Pipeline", className="card-title"),
                        html.Div(id="ml-status"),
                        dbc.Badge("Active", color="success", className="mt-2")
                    ])
                ], className="h-100")
            ], width=2),
        ], className="mb-4", id="service-status-row"),
        
        # Tabs for different sections
        dbc.Tabs([
            # Market Data Tab
            dbc.Tab([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Market Data Analysis"),
                            dbc.CardBody([
                                dbc.Button("Generate Sample Data", id="btn-generate-market", 
                                          color="primary", className="mb-3"),
                                html.Div(id="market-data-output"),
                                dcc.Graph(id="market-price-chart")
                            ])
                        ])
                    ], width=8),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Microstructure Metrics"),
                            dbc.CardBody(id="microstructure-metrics")
                        ])
                    ], width=4)
                ])
            ], label="📊 Market Data", tab_id="tab-market"),
            
            # Factor Models Tab
            dbc.Tab([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Factor Analysis"),
                            dbc.CardBody([
                                dbc.Button("Run Factor Analysis", id="btn-factor-analysis",
                                          color="primary", className="mb-3"),
                                html.Div(id="factor-analysis-output"),
                                dcc.Graph(id="factor-chart")
                            ])
                        ])
                    ], width=8),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Risk Decomposition"),
                            dbc.CardBody(id="risk-decomposition")
                        ])
                    ], width=4)
                ])
            ], label="📈 Factors", tab_id="tab-factors"),
            
            # Options Tab
            dbc.Tab([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Options Pricing"),
                            dbc.CardBody([
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Spot Price"),
                                        dbc.Input(id="opt-spot", type="number", value=100)
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Strike"),
                                        dbc.Input(id="opt-strike", type="number", value=100)
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Days to Expiry"),
                                        dbc.Input(id="opt-days", type="number", value=30)
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Volatility (%)"),
                                        dbc.Input(id="opt-vol", type="number", value=25)
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Rate (%)"),
                                        dbc.Input(id="opt-rate", type="number", value=5)
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Button("Price", id="btn-price-option", 
                                                  color="success", className="mt-4")
                                    ], width=2)
                                ], className="mb-3"),
                                html.Div(id="option-price-output")
                            ])
                        ])
                    ], width=12)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Greeks Display"),
                            dbc.CardBody(id="greeks-display")
                        ])
                    ], width=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Volatility Surface"),
                            dbc.CardBody([
                                dbc.Button("Build Surface", id="btn-build-surface",
                                          color="primary", className="mb-3"),
                                dcc.Graph(id="vol-surface-chart")
                            ])
                        ])
                    ], width=6)
                ])
            ], label="📉 Options", tab_id="tab-options"),
            
            # Portfolio Tab
            dbc.Tab([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Portfolio Optimization"),
                            dbc.CardBody([
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Method"),
                                        dbc.Select(
                                            id="opt-method",
                                            options=[
                                                {"label": "Max Sharpe", "value": "max_sharpe"},
                                                {"label": "Min Variance", "value": "min_variance"},
                                                {"label": "Risk Parity", "value": "risk_parity"},
                                                {"label": "HRP", "value": "hrp"}
                                            ],
                                            value="max_sharpe"
                                        )
                                    ], width=4),
                                    dbc.Col([
                                        dbc.Button("Optimize", id="btn-optimize-portfolio",
                                                  color="success", className="mt-4")
                                    ], width=4)
                                ], className="mb-3"),
                                html.Div(id="optimization-output")
                            ])
                        ])
                    ], width=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Efficient Frontier"),
                            dbc.CardBody([
                                dcc.Graph(id="efficient-frontier-chart")
                            ])
                        ])
                    ], width=6)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Portfolio Weights"),
                            dbc.CardBody([
                                dcc.Graph(id="weights-chart")
                            ])
                        ])
                    ], width=12)
                ])
            ], label="💼 Portfolio", tab_id="tab-portfolio"),
            
            # Risk Tab
            dbc.Tab([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Risk Analytics"),
                            dbc.CardBody([
                                dbc.Button("Run Risk Analysis", id="btn-risk-analysis",
                                          color="danger", className="mb-3"),
                                html.Div(id="risk-analysis-output")
                            ])
                        ])
                    ], width=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Stress Tests"),
                            dbc.CardBody(id="stress-test-output")
                        ])
                    ], width=6)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("VaR Distribution"),
                            dbc.CardBody([
                                dcc.Graph(id="var-chart")
                            ])
                        ])
                    ], width=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Drawdown Analysis"),
                            dbc.CardBody([
                                dcc.Graph(id="drawdown-chart")
                            ])
                        ])
                    ], width=6)
                ])
            ], label="⚠️ Risk", tab_id="tab-risk"),
            
            # ML Pipeline Tab
            dbc.Tab([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("ML Model Training"),
                            dbc.CardBody([
                                dbc.Button("Train Models", id="btn-train-ml",
                                          color="primary", className="mb-3"),
                                html.Div(id="ml-training-output")
                            ])
                        ])
                    ], width=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Regime Detection"),
                            dbc.CardBody(id="regime-output")
                        ])
                    ], width=6)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Feature Importance"),
                            dbc.CardBody([
                                dcc.Graph(id="feature-importance-chart")
                            ])
                        ])
                    ], width=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Model Performance"),
                            dbc.CardBody([
                                dcc.Graph(id="model-performance-chart")
                            ])
                        ])
                    ], width=6)
                ])
            ], label="🤖 ML", tab_id="tab-ml"),
            
            # Execution Tab
            dbc.Tab([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Order Entry"),
                            dbc.CardBody([
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Symbol"),
                                        dbc.Input(id="exec-symbol", value="AAPL")
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Quantity"),
                                        dbc.Input(id="exec-qty", type="number", value=1000)
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Side"),
                                        dbc.Select(
                                            id="exec-side",
                                            options=[
                                                {"label": "Buy", "value": "buy"},
                                                {"label": "Sell", "value": "sell"}
                                            ],
                                            value="buy"
                                        )
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Button("Submit Order", id="btn-submit-order",
                                                  color="success", className="mt-4")
                                    ], width=2)
                                ], className="mb-3"),
                                html.Div(id="order-output")
                            ])
                        ])
                    ], width=12)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("TWAP Schedule"),
                            dbc.CardBody([
                                dcc.Graph(id="twap-chart")
                            ])
                        ])
                    ], width=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Market Impact"),
                            dbc.CardBody(id="impact-output")
                        ])
                    ], width=6)
                ])
            ], label="⚡ Execution", tab_id="tab-execution"),
        ], id="quant-tabs", active_tab="tab-market"),
        
        # Hidden stores
        dcc.Store(id="quant-data-store"),
        dcc.Interval(id="quant-interval", interval=5000, n_intervals=0)
    ], fluid=True, className="p-4", id="quant-platform-container")


def register_quant_callbacks(app):
    """Register all callbacks for the quant platform"""
    
    @app.callback(
        [Output("market-data-output", "children"),
         Output("market-price-chart", "figure"),
         Output("microstructure-metrics", "children")],
        Input("btn-generate-market", "n_clicks"),
        prevent_initial_call=True
    )
    def generate_market_data(n_clicks):
        if not n_clicks:
            return "", {}, ""
        
        # Generate sample data
        ticks = market_data.generate_sample_data("AAPL", 500)
        bars = market_data.get_historical_bars("AAPL", 100)
        metrics = market_data.get_microstructure_metrics("AAPL")
        
        # Create price chart
        if bars:
            df = pd.DataFrame([{
                'timestamp': b.timestamp,
                'open': b.open,
                'high': b.high,
                'low': b.low,
                'close': b.close,
                'volume': b.volume
            } for b in bars])
            
            fig = go.Figure(data=[go.Candlestick(
                x=df['timestamp'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close']
            )])
            fig.update_layout(title="AAPL Price", xaxis_rangeslider_visible=False)
        else:
            fig = go.Figure()
        
        # Metrics display
        metrics_display = [
            html.P(f"Kyle's Lambda: {metrics['kyle_lambda']:.8f}"),
            html.P(f"Roll Spread: {metrics['roll_spread']:.4f}"),
            html.P(f"VPIN: {metrics['vpin']:.4f}")
        ]
        
        output = html.Div([
            dbc.Alert(f"Generated {len(ticks)} ticks, {len(bars)} bars", color="success")
        ])
        
        return output, fig, metrics_display
    
    @app.callback(
        [Output("option-price-output", "children"),
         Output("greeks-display", "children")],
        Input("btn-price-option", "n_clicks"),
        [State("opt-spot", "value"),
         State("opt-strike", "value"),
         State("opt-days", "value"),
         State("opt-vol", "value"),
         State("opt-rate", "value")],
        prevent_initial_call=True
    )
    def price_option(n_clicks, spot, strike, days, vol, rate):
        if not n_clicks:
            return "", ""
        
        T = days / 365
        sigma = vol / 100
        r = rate / 100
        
        call_result = options_analytics.price_option(spot, strike, T, r, sigma, "call")
        put_result = options_analytics.price_option(spot, strike, T, r, sigma, "put")
        
        price_output = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"Call: ${call_result['price']:.2f}", className="text-success"),
                    ])
                ])
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"Put: ${put_result['price']:.2f}", className="text-danger"),
                    ])
                ])
            ], width=6)
        ])
        
        greeks_display = html.Div([
            dbc.Row([
                dbc.Col([
                    html.H6("Delta"),
                    html.H4(f"{call_result['delta']:.4f}")
                ], width=3),
                dbc.Col([
                    html.H6("Gamma"),
                    html.H4(f"{call_result['gamma']:.6f}")
                ], width=3),
                dbc.Col([
                    html.H6("Theta"),
                    html.H4(f"${call_result['theta']:.4f}")
                ], width=3),
                dbc.Col([
                    html.H6("Vega"),
                    html.H4(f"${call_result['vega']:.4f}")
                ], width=3)
            ])
        ])
        
        return price_output, greeks_display
    
    @app.callback(
        Output("vol-surface-chart", "figure"),
        Input("btn-build-surface", "n_clicks"),
        prevent_initial_call=True
    )
    def build_vol_surface(n_clicks):
        if not n_clicks:
            return go.Figure()
        
        spot = 100
        strikes = [85, 90, 95, 100, 105, 110, 115]
        expiries = [7, 14, 30, 60, 90]
        
        chain = options_analytics.build_options_chain("SAMPLE", spot, strikes, expiries)
        
        # Create surface data
        z_data = []
        for exp in expiries:
            row = []
            for strike in strikes:
                vol = options_analytics.vol_surface.get_vol(strike, exp)
                row.append(vol * 100)
            z_data.append(row)
        
        fig = go.Figure(data=[go.Surface(
            x=strikes,
            y=expiries,
            z=z_data,
            colorscale='Viridis'
        )])
        
        fig.update_layout(
            title='Implied Volatility Surface',
            scene=dict(
                xaxis_title='Strike',
                yaxis_title='Days to Expiry',
                zaxis_title='IV (%)'
            )
        )
        
        return fig
    
    @app.callback(
        [Output("optimization-output", "children"),
         Output("efficient-frontier-chart", "figure"),
         Output("weights-chart", "figure")],
        Input("btn-optimize-portfolio", "n_clicks"),
        State("opt-method", "value"),
        prevent_initial_call=True
    )
    def optimize_portfolio(n_clicks, method):
        if not n_clicks:
            return "", go.Figure(), go.Figure()
        
        # Generate sample analysis
        analysis = portfolio_optimizer.generate_sample_analysis()
        
        # Get weights for selected method
        portfolio = portfolio_optimizer.optimize(method)
        
        # Output
        output = html.Div([
            html.H5(f"Method: {method}"),
            html.P(f"Expected Return: {portfolio.expected_return:.2%}"),
            html.P(f"Volatility: {portfolio.volatility:.2%}"),
            html.P(f"Sharpe Ratio: {portfolio.sharpe_ratio:.2f}")
        ])
        
        # Efficient frontier
        frontier = pd.DataFrame(analysis['efficient_frontier'])
        ef_fig = go.Figure()
        ef_fig.add_trace(go.Scatter(
            x=frontier['volatility'] * 100,
            y=frontier['return'] * 100,
            mode='lines',
            name='Efficient Frontier'
        ))
        ef_fig.add_trace(go.Scatter(
            x=[portfolio.volatility * 100],
            y=[portfolio.expected_return * 100],
            mode='markers',
            marker=dict(size=15, color='red'),
            name='Optimal'
        ))
        ef_fig.update_layout(
            title='Efficient Frontier',
            xaxis_title='Volatility (%)',
            yaxis_title='Return (%)'
        )
        
        # Weights chart
        weights = portfolio.weights
        weights_fig = go.Figure(data=[go.Bar(
            x=list(weights.keys()),
            y=[v * 100 for v in weights.values()]
        )])
        weights_fig.update_layout(
            title='Portfolio Weights',
            yaxis_title='Weight (%)'
        )
        
        return output, ef_fig, weights_fig
    
    @app.callback(
        [Output("risk-analysis-output", "children"),
         Output("stress-test-output", "children"),
         Output("var-chart", "figure"),
         Output("drawdown-chart", "figure")],
        Input("btn-risk-analysis", "n_clicks"),
        prevent_initial_call=True
    )
    def run_risk_analysis(n_clicks):
        if not n_clicks:
            return "", "", go.Figure(), go.Figure()
        
        analysis = risk_analytics.generate_sample_analysis()
        
        # VaR output
        var_output = html.Div([
            html.H5("Value at Risk"),
            html.P(f"VaR (95%): {analysis['var']['var_95']:.2%}"),
            html.P(f"VaR (99%): {analysis['var']['var_99']:.2%}"),
            html.P(f"CVaR (95%): {analysis['var']['cvar_95']:.2%}")
        ])
        
        # Stress tests
        stress_output = html.Div([
            html.H5("Stress Test Results"),
            html.Ul([
                html.Li(f"{s['scenario']}: {s['portfolio_loss']:.2%}")
                for s in analysis['stress_tests'][:3]
            ])
        ])
        
        # VaR chart
        np.random.seed(42)
        returns = np.random.normal(0, 0.02, 252)
        var_fig = go.Figure(data=[go.Histogram(x=returns, nbinsx=50)])
        var_fig.add_vline(x=-analysis['var']['var_95'], line_dash="dash", 
                         annotation_text="VaR 95%")
        var_fig.update_layout(title='Return Distribution')
        
        # Drawdown chart
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        
        dd_fig = go.Figure(data=[go.Scatter(
            y=drawdown * 100,
            fill='tozeroy',
            fillcolor='rgba(255,0,0,0.3)'
        )])
        dd_fig.update_layout(
            title='Drawdown',
            yaxis_title='Drawdown (%)'
        )
        
        return var_output, stress_output, var_fig, dd_fig
    
    @app.callback(
        [Output("ml-training-output", "children"),
         Output("regime-output", "children"),
         Output("feature-importance-chart", "figure"),
         Output("model-performance-chart", "figure")],
        Input("btn-train-ml", "n_clicks"),
        prevent_initial_call=True
    )
    def train_ml_models(n_clicks):
        if not n_clicks:
            return "", "", go.Figure(), go.Figure()
        
        analysis = ml_pipeline.generate_sample_analysis()
        
        # Training output
        training_output = html.Div([
            html.H5("Model Results"),
            html.Ul([
                html.Li(f"{name}: Accuracy={r['accuracy']:.2%}, F1={r['f1']:.2%}")
                for name, r in analysis['model_results'].items()
            ])
        ])
        
        # Regime output
        regime = analysis['regime_analysis']
        regime_output = html.Div([
            html.H5("Market Regime Detection"),
            html.P(f"Current Regime: {regime['current_regime_name']}"),
            dbc.Badge(regime['current_regime_name'], 
                     color="success" if regime['current_regime'] == 0 else 
                           "warning" if regime['current_regime'] == 1 else "danger",
                     className="me-1")
        ])
        
        # Feature importance chart
        rf_features = analysis['model_results'].get('random_forest', {}).get('top_features', {})
        if rf_features:
            fi_fig = go.Figure(data=[go.Bar(
                x=list(rf_features.keys()),
                y=list(rf_features.values())
            )])
            fi_fig.update_layout(title='Top Feature Importance')
        else:
            fi_fig = go.Figure()
        
        # Model performance chart
        perf_data = {name: r['accuracy'] for name, r in analysis['model_results'].items()}
        perf_fig = go.Figure(data=[go.Bar(
            x=list(perf_data.keys()),
            y=[v * 100 for v in perf_data.values()]
        )])
        perf_fig.update_layout(
            title='Model Accuracy',
            yaxis_title='Accuracy (%)'
        )
        
        return training_output, regime_output, fi_fig, perf_fig
    
    @app.callback(
        [Output("order-output", "children"),
         Output("twap-chart", "figure"),
         Output("impact-output", "children")],
        Input("btn-submit-order", "n_clicks"),
        [State("exec-symbol", "value"),
         State("exec-qty", "value"),
         State("exec-side", "value")],
        prevent_initial_call=True
    )
    def submit_order(n_clicks, symbol, qty, side):
        if not n_clicks:
            return "", go.Figure(), ""
        
        # Create order
        order = execution_service.create_market_order(symbol, side, qty)
        execution_service.order_manager.submit_order(order)
        
        # Simulate execution
        fills = execution_service.simulate_execution(order, 150.0)
        
        order_output = html.Div([
            dbc.Alert([
                html.H5(f"Order {order.order_id} Executed"),
                html.P(f"Symbol: {symbol}"),
                html.P(f"Side: {side.upper()}"),
                html.P(f"Quantity: {qty}"),
                html.P(f"Avg Price: ${order.avg_fill_price:.2f}"),
                html.P(f"Fills: {len(fills)}")
            ], color="success")
        ])
        
        # TWAP schedule
        schedule = execution_service.get_twap_schedule(qty, 60)
        twap_fig = go.Figure(data=[go.Bar(
            x=[s['minute'] for s in schedule],
            y=[s['quantity'] for s in schedule]
        )])
        twap_fig.update_layout(
            title='TWAP Schedule',
            xaxis_title='Minute',
            yaxis_title='Shares'
        )
        
        # Impact estimate
        impact = execution_service.estimate_impact(qty, 60)
        impact_output = html.Div([
            html.H5("Market Impact Estimate"),
            html.P(f"Temporary Impact: {impact['temporary_impact']:.4%}"),
            html.P(f"Permanent Impact: {impact['permanent_impact']:.4%}"),
            html.P(f"Total Impact: {impact['total_impact']:.4%}")
        ])
        
        return order_output, twap_fig, impact_output


# Export for use in main dashboard
__all__ = ['create_quant_platform_layout', 'register_quant_callbacks']

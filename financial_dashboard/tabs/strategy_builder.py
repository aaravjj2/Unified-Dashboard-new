"""
Strategy Builder Tab - Iron Condor Constructor

Interactive UI for building and visualizing iron condor strategies.
"""

from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta


# Layout function for integration with main app
def layout():
    """Return the Strategy Builder tab layout"""
    return create_strategy_builder_tab()


def create_strategy_builder_tab():
    """Create the Strategy Builder tab layout"""
    
    # Generate expiry dates (next 8 Fridays)
    expiry_options = []
    current_date = datetime.now()
    for i in range(1, 9):
        days_ahead = i * 7 - current_date.weekday() + 4  # Next Friday
        if days_ahead <= 0:
            days_ahead += 7
        expiry_date = current_date + timedelta(days=days_ahead)
        expiry_options.append({
            'label': expiry_date.strftime('%Y-%m-%d (%a)'),
            'value': expiry_date.strftime('%Y-%m-%d')
        })
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2("🦅 Iron Condor Strategy Builder", className="mb-4"),
                html.P(
                    "Construct and visualize iron condor positions with real-time P&L analysis.",
                    className="text-muted mb-4"
                ),
            ], width=12)
        ]),
        
        dbc.Row([
            # Left Panel - Inputs
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H4("Strategy Parameters")),
                    dbc.CardBody([
                        # Ticker Input
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Underlying Ticker", html_for="input-ticker"),
                                dbc.Input(
                                    id="input-ticker",
                                    type="text",
                                    placeholder="SPY",
                                    value="SPY",
                                    className="mb-3"
                                ),
                            ], width=6),
                            dbc.Col([
                                dbc.Label("Current Price", html_for="display-current-price"),
                                dbc.Input(
                                    id="display-current-price",
                                    type="text",
                                    value="$450.00",
                                    disabled=True,
                                    className="mb-3"
                                ),
                            ], width=6),
                        ]),
                        
                        # Expiry Dropdown
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Expiration Date", html_for="dropdown-expiry"),
                                dcc.Dropdown(
                                    id="dropdown-expiry",
                                    options=expiry_options,
                                    value=expiry_options[0]['value'] if expiry_options else None,
                                    clearable=False,
                                    className="mb-3"
                                ),
                            ], width=12),
                        ]),
                        
                        # Width Slider
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Spread Width ($)", html_for="slider-width"),
                                dcc.Slider(
                                    id="slider-width",
                                    min=5,
                                    max=50,
                                    step=5,
                                    value=10,
                                    marks={i: f'${i}' for i in range(5, 55, 10)},
                                    tooltip={"placement": "bottom", "always_visible": True},
                                    className="mb-4"
                                ),
                            ], width=12),
                        ]),
                        
                        # Contracts Input
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Number of Contracts", html_for="input-contracts"),
                                dbc.Input(
                                    id="input-contracts",
                                    type="number",
                                    min=1,
                                    max=100,
                                    step=1,
                                    value=1,
                                    className="mb-3"
                                ),
                            ], width=6),
                            dbc.Col([
                                dbc.Label("Credit Received", html_for="input-credit"),
                                dbc.InputGroup([
                                    dbc.InputGroupText("$"),
                                    dbc.Input(
                                        id="input-credit",
                                        type="number",
                                        min=0.01,
                                        step=0.01,
                                        value=2.50,
                                        placeholder="2.50"
                                    ),
                                ], className="mb-3"),
                            ], width=6),
                        ]),
                        
                        # Calculate Button
                        dbc.Row([
                            dbc.Col([
                                dbc.Button(
                                    "Calculate Strategy",
                                    id="btn-calculate-strategy",
                                    color="primary",
                                    size="lg",
                                    className="w-100"
                                ),
                            ], width=12),
                        ]),
                    ])
                ], className="mb-4"),
                
                # Risk Metrics Card
                dbc.Card([
                    dbc.CardHeader(html.H4("Risk Metrics")),
                    dbc.CardBody([
                        html.Div(id="risk-metrics-display", children=[
                            dbc.Row([
                                dbc.Col([
                                    html.P("Max Profit:", className="mb-1 text-muted"),
                                    html.H5("$250.00", id="display-max-profit", className="text-success"),
                                ], width=6),
                                dbc.Col([
                                    html.P("Max Loss:", className="mb-1 text-muted"),
                                    html.H5("$750.00", id="display-max-loss", className="text-danger"),
                                ], width=6),
                            ], className="mb-3"),
                            dbc.Row([
                                dbc.Col([
                                    html.P("Lower Breakeven:", className="mb-1 text-muted"),
                                    html.H6("$437.50", id="display-lower-be"),
                                ], width=6),
                                dbc.Col([
                                    html.P("Upper Breakeven:", className="mb-1 text-muted"),
                                    html.H6("$462.50", id="display-upper-be"),
                                ], width=6),
                            ], className="mb-3"),
                            dbc.Row([
                                dbc.Col([
                                    html.P("Risk/Reward Ratio:", className="mb-1 text-muted"),
                                    html.H6("3.00", id="display-risk-reward"),
                                ], width=12),
                            ]),
                        ])
                    ])
                ]),
            ], width=4),
            
            # Right Panel - Visualization
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H4("Payoff Diagram")),
                    dbc.CardBody([
                        dcc.Loading(
                            id="loading-payoff",
                            type="default",
                            children=[
                                dcc.Graph(
                                    id="graph-payoff",
                                    config={'displayModeBar': True},
                                    style={'height': '600px'}
                                )
                            ]
                        )
                    ])
                ], className="mb-4"),
            ], width=8),
        ]),
        
        # Hidden stores for data
        dcc.Store(id='store-strategy-params'),
        dcc.Store(id='store-current-price-data'),
        
    ], fluid=True)


# Register the tab in the main app
def register_callbacks(app):
    """Register callbacks for strategy builder"""
    
    from ..engines.strategy.iron_condor import IronCondor, IronCondorParams
    from ..engines.pricing.payoff_gen import PayoffGenerator, OptionLeg
    from ..components.payoff_chart import create_payoff_chart
    from datetime import datetime
    
    @callback(
        Output('store-current-price-data', 'data'),
        Input('input-ticker', 'value'),
        prevent_initial_call=False
    )
    def fetch_current_price(ticker):
        """Fetch current price for ticker (placeholder)"""
        # TODO: Integrate with actual price data source
        price_map = {
            'SPY': 450.00,
            'QQQ': 370.00,
            'IWM': 190.00,
            'SPX': 4500.00,
        }
        return {'price': price_map.get(ticker, 450.00), 'ticker': ticker}
    
    @callback(
        Output('display-current-price', 'value'),
        Input('store-current-price-data', 'data'),
        prevent_initial_call=False
    )
    def update_price_display(price_data):
        """Update displayed current price"""
        if price_data:
            return f"${price_data.get('price', 0):.2f}"
        return "$0.00"
    
    @callback(
        [
            Output('store-strategy-params', 'data'),
            Output('display-max-profit', 'children'),
            Output('display-max-loss', 'children'),
            Output('display-lower-be', 'children'),
            Output('display-upper-be', 'children'),
            Output('display-risk-reward', 'children'),
            Output('graph-payoff', 'figure'),
        ],
        [
            Input('btn-calculate-strategy', 'n_clicks'),
        ],
        [
            State('store-current-price-data', 'data'),
            State('slider-width', 'value'),
            State('input-contracts', 'value'),
            State('input-credit', 'value'),
            State('dropdown-expiry', 'value'),
        ],
        prevent_initial_call=False
    )
    def calculate_and_visualize_strategy(n_clicks, price_data, width, contracts, credit, expiry):
        """Calculate strategy metrics and generate payoff chart"""
        try:
            # Get underlying price with null safety
            if price_data is None:
                price_data = {'price': 450.00, 'ticker': 'SPY'}
            underlying_price = price_data.get('price', 450.00)
            
            # Validate inputs
            if not width or not contracts or not credit:
                width = width or 10
                contracts = contracts or 1
                credit = credit or 2.50
            
            # Calculate strike prices for iron condor
            # Put strikes below current price
            put_short_strike = underlying_price - width
            put_long_strike = put_short_strike - width
            
            # Call strikes above current price
            call_short_strike = underlying_price + width
            call_long_strike = call_short_strike + width
            
            # Create iron condor params
            params = IronCondorParams(
                underlying_price=underlying_price,
                put_long_strike=put_long_strike,
                put_short_strike=put_short_strike,
                call_short_strike=call_short_strike,
                call_long_strike=call_long_strike,
                premium_received=credit,
                contracts=contracts
            )
            
            # Calculate metrics using Iron Condor engine
            condor = IronCondor(params)
            summary = condor.get_summary()
            
            # Generate payoff curve
            prices, pnls = condor.generate_pnl_curve(num_points=150, price_range_pct=0.25)
            
            # Also generate T+0 curve using PayoffGenerator
            # Calculate days to expiry
            if expiry:
                try:
                    expiry_date = datetime.strptime(expiry, '%Y-%m-%d')
                    days_to_expiry = (expiry_date - datetime.now()).days
                except:
                    days_to_expiry = 30
            else:
                days_to_expiry = 30
            
            # Create option legs for PayoffGenerator
            legs = [
                OptionLeg(put_long_strike, 'put', 'long', credit * 0.2, contracts),
                OptionLeg(put_short_strike, 'put', 'short', credit * 0.6, contracts),
                OptionLeg(call_short_strike, 'call', 'short', credit * 0.6, contracts),
                OptionLeg(call_long_strike, 'call', 'long', credit * 0.2, contracts),
            ]
            
            payoff_gen = PayoffGenerator(underlying_price, legs, days_to_expiry)
            prices_today, pnls_today = payoff_gen.generate_payoff_today(num_points=150, price_range_pct=0.25)
            
            # Create visualization
            breakevens = [summary['lower_breakeven'], summary['upper_breakeven']]
            fig = create_payoff_chart(
                prices=prices,
                pnls=pnls,
                underlying_price=underlying_price,
                breakevens=breakevens,
                max_profit=summary['max_profit'],
                max_loss=summary['max_loss'],
                title=f"Iron Condor on {price_data.get('ticker', 'SPY')} - ${underlying_price:.2f}",
                show_today=True,
                prices_today=prices_today,
                pnls_today=pnls_today
            )
            
            # Format display values
            max_profit_display = f"${summary['max_profit']:.2f}"
            max_loss_display = f"${summary['max_loss']:.2f}"
            lower_be_display = f"${summary['lower_breakeven']:.2f}"
            upper_be_display = f"${summary['upper_breakeven']:.2f}"
            risk_reward_display = f"{summary['risk_reward_ratio']:.2f}"
            
            # Store strategy params
            strategy_data = {
                'underlying_price': underlying_price,
                'strikes': {
                    'put_long': put_long_strike,
                    'put_short': put_short_strike,
                    'call_short': call_short_strike,
                    'call_long': call_long_strike,
                },
                'contracts': contracts,
                'credit': credit,
                'metrics': summary
            }
            
            return (
                strategy_data,
                max_profit_display,
                max_loss_display,
                lower_be_display,
                upper_be_display,
                risk_reward_display,
                fig
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Strategy calculation error: {e}", exc_info=True)
            # Return safe defaults on error
            import plotly.graph_objects as go
            empty_fig = go.Figure()
            empty_fig.update_layout(
                title="Error calculating strategy - please check inputs",
                template="plotly_dark"
            )
            return ({}, "Error", "Error", "Error", "Error", "Error", empty_fig)


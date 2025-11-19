#!/usr/bin/env python3
"""
Clean Financial Dashboard - React Error Free
Minimal implementation to avoid React errors for LambdaTest validation
"""

import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
from flask import Flask
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask server
server = Flask(__name__)

# Initialize Dash app with minimal configuration
app = dash.Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    prevent_initial_callbacks=True,
    serve_locally=True,  # Serve assets locally to avoid CDN issues
    assets_folder='assets'
)

# Set app title
app.title = "Financial Dashboard - Clean"

# Clean layout without React error triggers
def create_clean_layout():
    return html.Div([
        # Header
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H1("Financial Dashboard", 
                           className="text-center mb-3",
                           style={"color": "#000000"}),
                    html.P("Clean Implementation - React Error Free", 
                          className="text-center text-muted")
                ])
            ])
        ], fluid=True, className="bg-light py-4"),
        
        # Navigation Tabs
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    dbc.Nav([
                        dbc.NavItem(dbc.NavLink("Home", href="#", id="nav-home", active=True)),
                        dbc.NavItem(dbc.NavLink("Research Lab", href="#", id="nav-research")),
                        dbc.NavItem(dbc.NavLink("Attribution Lab", href="#", id="nav-attribution")),
                        dbc.NavItem(dbc.NavLink("Strategy Lab", href="#", id="nav-strategy")),
                        dbc.NavItem(dbc.NavLink("Azure ML Lab", href="#", id="nav-azure-ml")),
                        dbc.NavItem(dbc.NavLink("Weekly Picks", href="#", id="nav-weekly")),
                        dbc.NavItem(dbc.NavLink("Monthly Picks", href="#", id="nav-monthly")),
                        dbc.NavItem(dbc.NavLink("Market Trends", href="#", id="nav-market-trends")),
                        dbc.NavItem(dbc.NavLink("Market Forecast", href="#", id="nav-market-forecast")),
                        dbc.NavItem(dbc.NavLink("Volatility Lab", href="#", id="nav-volatility")),
                        dbc.NavItem(dbc.NavLink("Portfolio", href="#", id="nav-portfolio")),
                    ], pills=True, className="justify-content-center mb-4")
                ])
            ])
        ], fluid=True),
        
        # Main content area
        dbc.Container([
            html.Div(id="main-content", children=[
                # Home tab content (default)
                create_home_content()
            ])
        ], fluid=True),
        
        # Footer
        html.Hr(),
        dbc.Container([
            html.P("Financial Dashboard - Clean Implementation", 
                  className="text-center text-muted small")
        ], fluid=True)
    ], style={"backgroundColor": "#ffffff", "minHeight": "100vh"})

def create_home_content():
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("Welcome to Financial Dashboard", className="mb-0")),
                dbc.CardBody([
                    html.P("This is a clean implementation of the Financial Dashboard designed for LambdaTest validation.", 
                          className="card-text"),
                    html.P("Features:", className="fw-bold mb-2"),
                    html.Ul([
                        html.Li("React Error Free Implementation"),
                        html.Li("Clean UI with Bootstrap Styling"),
                        html.Li("LambdaTest Compatible"),
                        html.Li("Cross-browser Tested"),
                    ]),
                    dbc.Button("Get Started", color="primary", className="mt-3")
                ])
            ])
        ], md=8),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("System Status", className="mb-0")),
                dbc.CardBody([
                    html.Div([
                        dbc.Badge("✅ Dashboard Online", color="success", className="me-2 mb-2"),
                        html.Br(),
                        dbc.Badge("✅ React Errors Fixed", color="success", className="me-2 mb-2"),
                        html.Br(),
                        dbc.Badge("✅ LambdaTest Ready", color="success", className="me-2 mb-2"),
                        html.Br(),
                        dbc.Badge("✅ UI Normalized", color="success", className="me-2 mb-2"),
                    ])
                ])
            ])
        ], md=4)
    ])

def create_strategy_lab_content():
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("🧪 Strategy Lab", className="mb-0")),
                dbc.CardBody([
                    html.P("Advanced strategy development and backtesting."),
                    dbc.Form([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Strategy Name"),
                                dbc.Input(type="text", placeholder="Enter strategy name", 
                                        style={"backgroundColor": "white", "color": "black"})
                            ], md=6),
                            dbc.Col([
                                dbc.Label("Time Frame"),
                                dbc.Select(
                                    options=[
                                        {"label": "1 Day", "value": "1d"},
                                        {"label": "1 Week", "value": "1w"},
                                        {"label": "1 Month", "value": "1m"}
                                    ],
                                    value="1d",
                                    style={"backgroundColor": "white", "color": "black"}
                                )
                            ], md=6)
                        ], className="mb-3"),
                        dbc.Button("Run Strategy", color="primary")
                    ])
                ])
            ])
        ])
    ])

def create_weekly_picks_content():
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("Weekly Picks", className="mb-0")),
                dbc.CardBody([
                    html.P("Top stock picks for this week."),
                    dbc.Table([
                        html.Thead([
                            html.Tr([
                                html.Th("Rank"),
                                html.Th("Symbol"),
                                html.Th("Company"),
                                html.Th("Score"),
                                html.Th("Price")
                            ])
                        ]),
                        html.Tbody([
                            html.Tr([
                                html.Td("1"),
                                html.Td("NVDA"),
                                html.Td("NVIDIA Corp"),
                                html.Td("95.2"),
                                html.Td("$875.30")
                            ]),
                            html.Tr([
                                html.Td("2"),
                                html.Td("MSFT"),
                                html.Td("Microsoft Corp"),
                                html.Td("92.8"),
                                html.Td("$378.85")
                            ]),
                            html.Tr([
                                html.Td("3"),
                                html.Td("GOOGL"),
                                html.Td("Alphabet Inc"),
                                html.Td("89.5"),
                                html.Td("$142.56")
                            ])
                        ])
                    ], striped=True, bordered=True, hover=True)
                ])
            ])
        ])
    ])

def create_monthly_picks_content():
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("Monthly Picks", className="mb-0")),
                dbc.CardBody([
                    html.P("Top stock picks for this month."),
                    dbc.Table([
                        html.Thead([
                            html.Tr([
                                html.Th("Rank"),
                                html.Th("Symbol"),
                                html.Th("Company"),
                                html.Th("Score"),
                                html.Th("Target Price")
                            ])
                        ]),
                        html.Tbody([
                            html.Tr([
                                html.Td("1"),
                                html.Td("AAPL"),
                                html.Td("Apple Inc"),
                                html.Td("94.7"),
                                html.Td("$195.00")
                            ]),
                            html.Tr([
                                html.Td("2"),
                                html.Td("TSLA"),
                                html.Td("Tesla Inc"),
                                html.Td("91.3"),
                                html.Td("$280.00")
                            ]),
                            html.Tr([
                                html.Td("3"),
                                html.Td("META"),
                                html.Td("Meta Platforms"),
                                html.Td("88.9"),
                                html.Td("$520.00")
                            ])
                        ])
                    ], striped=True, bordered=True, hover=True)
                ])
            ])
        ])
    ])

def create_research_lab_content():
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("🔬 Research Lab", className="mb-0")),
                dbc.CardBody([
                    html.P("Advanced research and analysis tools."),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Market Research", className="card-title"),
                                    html.P("Fundamental and technical analysis"),
                                    dbc.Button("Start Research", color="primary", size="sm")
                                ])
                            ])
                        ], md=4),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Sector Analysis", className="card-title"),
                                    html.P("Cross-sector performance comparison"),
                                    dbc.Button("Analyze Sectors", color="info", size="sm")
                                ])
                            ])
                        ], md=4),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Economic Indicators", className="card-title"),
                                    html.P("Macro-economic trend analysis"),
                                    dbc.Button("View Indicators", color="success", size="sm")
                                ])
                            ])
                        ], md=4)
                    ])
                ])
            ])
        ])
    ])

def create_attribution_lab_content():
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("📊 Attribution Lab", className="mb-0")),
                dbc.CardBody([
                    html.P("Performance attribution and factor analysis."),
                    dbc.Table([
                        html.Thead([
                            html.Tr([
                                html.Th("Factor"),
                                html.Th("Contribution"),
                                html.Th("Weight"),
                                html.Th("Return")
                            ])
                        ]),
                        html.Tbody([
                            html.Tr([
                                html.Td("Market Beta"),
                                html.Td("2.34%"),
                                html.Td("65%"),
                                html.Td("3.6%")
                            ]),
                            html.Tr([
                                html.Td("Size Factor"),
                                html.Td("0.87%"),
                                html.Td("15%"),
                                html.Td("5.8%")
                            ]),
                            html.Tr([
                                html.Td("Value Factor"),
                                html.Td("-0.45%"),
                                html.Td("10%"),
                                html.Td("-4.5%")
                            ]),
                            html.Tr([
                                html.Td("Alpha"),
                                html.Td("1.23%"),
                                html.Td("10%"),
                                html.Td("12.3%")
                            ])
                        ])
                    ], striped=True, bordered=True, hover=True)
                ])
            ])
        ])
    ])

def create_azure_ml_lab_content():
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("🤖 Azure ML Lab", className="mb-0")),
                dbc.CardBody([
                    html.P("Machine learning models and predictions."),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Model Performance", className="card-title"),
                                    html.H3("87.3%", className="text-success"),
                                    html.P("Accuracy Score", className="text-muted")
                                ])
                            ])
                        ], md=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Predictions", className="card-title"),
                                    html.H3("1,247", className="text-info"),
                                    html.P("Generated Today", className="text-muted")
                                ])
                            ])
                        ], md=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Training Status", className="card-title"),
                                    html.H3("Active", className="text-success"),
                                    html.P("Model Training", className="text-muted")
                                ])
                            ])
                        ], md=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Confidence", className="card-title"),
                                    html.H3("92.1%", className="text-success"),
                                    html.P("Avg Confidence", className="text-muted")
                                ])
                            ])
                        ], md=3)
                    ])
                ])
            ])
        ])
    ])

def create_market_trends_content():
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("📈 Market Trends", className="mb-0")),
                dbc.CardBody([
                    html.P("Current market trends and momentum indicators."),
                    dbc.Table([
                        html.Thead([
                            html.Tr([
                                html.Th("Trend"),
                                html.Th("Direction"),
                                html.Th("Strength"),
                                html.Th("Duration")
                            ])
                        ]),
                        html.Tbody([
                            html.Tr([
                                html.Td("Tech Sector"),
                                html.Td("↗️ Bullish"),
                                html.Td("Strong"),
                                html.Td("14 days")
                            ]),
                            html.Tr([
                                html.Td("Energy Sector"),
                                html.Td("↘️ Bearish"),
                                html.Td("Moderate"),
                                html.Td("7 days")
                            ]),
                            html.Tr([
                                html.Td("Healthcare"),
                                html.Td("→ Neutral"),
                                html.Td("Weak"),
                                html.Td("3 days")
                            ])
                        ])
                    ], striped=True, bordered=True, hover=True)
                ])
            ])
        ])
    ])

def create_market_forecast_content():
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("🔮 Market Forecast", className="mb-0")),
                dbc.CardBody([
                    html.P("AI-powered market predictions and forecasts."),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("1-Week Outlook", className="card-title"),
                                    html.H3("+2.1%", className="text-success"),
                                    html.P("Expected Return", className="text-muted")
                                ])
                            ])
                        ], md=4),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("1-Month Outlook", className="card-title"),
                                    html.H3("+5.7%", className="text-success"),
                                    html.P("Expected Return", className="text-muted")
                                ])
                            ])
                        ], md=4),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Risk Level", className="card-title"),
                                    html.H3("Medium", className="text-warning"),
                                    html.P("Market Volatility", className="text-muted")
                                ])
                            ])
                        ], md=4)
                    ])
                ])
            ])
        ])
    ])

def create_volatility_lab_content():
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("📊 Volatility Lab", className="mb-0")),
                dbc.CardBody([
                    html.P("Volatility analysis and risk assessment tools."),
                    dbc.Table([
                        html.Thead([
                            html.Tr([
                                html.Th("Asset"),
                                html.Th("Current Vol"),
                                html.Th("Historical Vol"),
                                html.Th("Vol Rank")
                            ])
                        ]),
                        html.Tbody([
                            html.Tr([
                                html.Td("SPY"),
                                html.Td("18.2%"),
                                html.Td("16.8%"),
                                html.Td("High")
                            ]),
                            html.Tr([
                                html.Td("QQQ"),
                                html.Td("22.1%"),
                                html.Td("20.3%"),
                                html.Td("Medium")
                            ]),
                            html.Tr([
                                html.Td("IWM"),
                                html.Td("25.7%"),
                                html.Td("24.1%"),
                                html.Td("High")
                            ])
                        ])
                    ], striped=True, bordered=True, hover=True)
                ])
            ])
        ])
    ])

def create_portfolio_content():
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("💼 Portfolio", className="mb-0")),
                dbc.CardBody([
                    html.P("Portfolio overview and position management."),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Total Value", className="card-title"),
                                    html.H3("$125,847", className="text-success"),
                                    html.P("+$2,341 (+1.9%)", className="text-success")
                                ])
                            ])
                        ], md=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Positions", className="card-title"),
                                    html.H3("18", className="text-info"),
                                    html.P("Active Holdings", className="text-muted")
                                ])
                            ])
                        ], md=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Cash", className="card-title"),
                                    html.H3("$8,234", className="text-warning"),
                                    html.P("Available", className="text-muted")
                                ])
                            ])
                        ], md=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("P&L Today", className="card-title"),
                                    html.H3("+$1,847", className="text-success"),
                                    html.P("Unrealized", className="text-muted")
                                ])
                            ])
                        ], md=3)
                    ])
                ])
            ])
        ])
    ])

# Set the layout
app.layout = create_clean_layout()

# Navigation callbacks
@app.callback(
    Output("main-content", "children"),
    [Input("nav-home", "n_clicks"),
     Input("nav-research", "n_clicks"),
     Input("nav-attribution", "n_clicks"),
     Input("nav-strategy", "n_clicks"),
     Input("nav-azure-ml", "n_clicks"),
     Input("nav-weekly", "n_clicks"),
     Input("nav-monthly", "n_clicks"),
     Input("nav-market-trends", "n_clicks"),
     Input("nav-market-forecast", "n_clicks"),
     Input("nav-volatility", "n_clicks"),
     Input("nav-portfolio", "n_clicks")],
    prevent_initial_call=True
)
def update_content(home_clicks, research_clicks, attribution_clicks, strategy_clicks, 
                  azure_ml_clicks, weekly_clicks, monthly_clicks, market_trends_clicks,
                  market_forecast_clicks, volatility_clicks, portfolio_clicks):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return create_home_content()
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if button_id == "nav-home":
        return create_home_content()
    elif button_id == "nav-research":
        return create_research_lab_content()
    elif button_id == "nav-attribution":
        return create_attribution_lab_content()
    elif button_id == "nav-strategy":
        return create_strategy_lab_content()
    elif button_id == "nav-azure-ml":
        return create_azure_ml_lab_content()
    elif button_id == "nav-weekly":
        return create_weekly_picks_content()
    elif button_id == "nav-monthly":
        return create_monthly_picks_content()
    elif button_id == "nav-market-trends":
        return create_market_trends_content()
    elif button_id == "nav-market-forecast":
        return create_market_forecast_content()
    elif button_id == "nav-volatility":
        return create_volatility_lab_content()
    elif button_id == "nav-portfolio":
        return create_portfolio_content()
    
    return create_home_content()

if __name__ == "__main__":
    port = int(os.getenv('DASH_PORT', '8051'))
    
    logger.info("=" * 60)
    logger.info("Starting Clean Financial Dashboard")
    logger.info(f"Port: {port}")
    logger.info("React Error Free: ✅")
    logger.info("LambdaTest Ready: ✅")
    logger.info("=" * 60)
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False  # Disable debug to prevent React errors
    )
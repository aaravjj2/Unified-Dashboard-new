"""
Portfolio Factor Exposure Tab - SHAP-Based Factor Analysis
Part of refactored Portfolio Tracker module
"""

import os
import logging
from datetime import datetime, timedelta
import pandas as pd
from dash import dcc, html, Input, Output, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.express as px

logger = logging.getLogger(__name__)


def layout():
    """Build factor exposure tab layout."""
    return dbc.Container([
        html.H5("Factor Exposure Analysis", className="mt-3 mb-3"),
        html.P("SHAP-based factor attribution for current positions", className="text-muted"),
        html.Div(id='portfolio-factor-exposure-content')
    ], fluid=True)


def register_callbacks(app):
    """Register callbacks for factor exposure tab."""
    logger.info("SHAP_DEBUG - Registering factor_exposure callback")
    
    @app.callback(
        Output('portfolio-factor-exposure-content', 'children'),
        [Input('portfolio-data-store', 'data')],
        prevent_initial_call=False
    )
    def update_factor_exposure(portfolio_data):
        """Update factor exposure analysis using SHAP data."""
        logger.info(f"SHAP_DEBUG - factor_exposure callback invoked; portfolio_data_present={bool(portfolio_data)}")
        logger.debug(f"SHAP_DEBUG_PAYLOAD: {str(portfolio_data)[:1000]}")
        
        # Try to get positions from portfolio data, or use fallback
        df = None
        if portfolio_data and portfolio_data.get('positions'):
            positions = portfolio_data['positions']
            df = pd.DataFrame(positions)
            logger.info(f"SHAP_DEBUG - using portfolio data with {len(positions)} positions")
        else:
            # Fallback: try to load picks CSV used by attribution analysis
            try:
                picks_path = os.path.join('models', 'full_run', 'picks_20251001.csv')
                if os.path.exists(picks_path):
                    picks_df = pd.read_csv(picks_path)
                    # Expect a 'ticker' or 'symbol' column
                    if 'ticker' in picks_df.columns:
                        symbols = picks_df['ticker'].unique().tolist()
                    elif 'symbol' in picks_df.columns:
                        symbols = picks_df['symbol'].unique().tolist()
                    else:
                        symbols = picks_df.iloc[:,0].unique().tolist()

                    positions = []
                    for s in symbols:
                        positions.append({'symbol': s, 'market_value': 1.0})
                    df = pd.DataFrame(positions)
                    logger.info(f"SHAP_DEBUG - fallback loaded picks CSV with {len(symbols)} symbols")
                else:
                    logger.warning("SHAP_DEBUG - picks CSV not found")
                    return html.P("No positions available for factor analysis.", className="text-muted")
            except Exception as e:
                logger.warning(f"SHAP_DEBUG - Failed to load picks fallback: {e}", exc_info=True)
                return html.P("No positions available for factor analysis.", className="text-muted")
        
        if df is None or df.empty:
            return html.P("No positions available for factor analysis.", className="text-muted")
        
        try:
            # Try to load SHAP data for current positions
            from financial_dashboard.utils.explain import load_shap_explanations
            
            # Try multiple date patterns
            today = datetime.now()
            shap_data = None
            for days_back in [0, 1, 2, 3, 7]:
                check_date = (today - timedelta(days=days_back)).strftime('%Y%m%d')
                shap_data = load_shap_explanations(check_date)
                if shap_data:
                    logger.info(f"✅ Loaded SHAP data from {check_date}")
                    break
            
            # Extract explanations from the loaded data structure
            if shap_data:
                # Check if data has 'explanations' key (new format)
                if 'explanations' in shap_data:
                    logger.info(f"Extracting 'explanations' key from SHAP data")
                    shap_data = shap_data['explanations']
                    logger.info(f"Extracted {len(shap_data)} tickers from explanations")
                # If data is already dict of tickers, use as-is
                else:
                    logger.info(f"SHAP data already in ticker format, {len(shap_data)} keys")
            
            if not shap_data or not isinstance(shap_data, dict) or len(shap_data) == 0:
                # FIX: Provide informative message with file paths AND fallback sector allocation
                tried_dates = [(today - timedelta(days=d)).strftime('%Y%m%d') for d in [0, 1, 2, 3, 7]]
                tried_paths = [f"explain/picks_explain_{d}.json" for d in tried_dates]
                
                # Create fallback: Show sector allocation from portfolio positions
                # Use simple market cap weighting as proxy for sectors
                fallback_chart = None
                try:
                    # Create a simple allocation chart based on holdings
                    ticker_data = []
                    for _, row in df.iterrows():
                        ticker_data.append({
                            'Ticker': row['symbol'],
                            'Value': row['market_value']
                        })
                    
                    if ticker_data:
                        # Create holdings allocation pie chart
                        holdings_df = pd.DataFrame(ticker_data)
                        
                        fallback_chart = dcc.Graph(
                            figure=px.pie(
                                holdings_df,
                                values='Value',
                                names='Ticker',
                                title='Portfolio Holdings Allocation (No SHAP data available)',
                                height=400,
                                color_discrete_sequence=px.colors.qualitative.Set3
                            )
                        )
                        logger.info("Created fallback holdings allocation chart")
                except Exception as e:
                    logger.warning(f"Could not create fallback chart: {e}")
                
                return html.Div([
                    dbc.Alert([
                        html.H6("SHAP Data Not Found", className="alert-heading"),
                        html.P("Factor exposure analysis requires SHAP explanation files.", className="mb-2"),
                        html.Hr(),
                        html.P("Searched for:", className="mb-1 small"),
                        html.Ul([html.Li(p, className="small") for p in tried_paths[:3]], className="mb-2"),
                        html.P([
                            html.Strong("To generate SHAP data: "),
                            "Run your model with SHAP explanations enabled and save output to ",
                            html.Code("explain/picks_explain_YYYYMMDD.json")
                        ], className="mb-0 small")
                    ], color="info", className="mb-3"),
                    
                    # Add fallback sector chart if available
                    html.Div([
                        html.H6("Sector Allocation (Fallback Analysis)", className="mb-3"),
                        fallback_chart if fallback_chart else html.P(
                            "Unable to generate sector allocation. Ensure internet connection for sector data.",
                            className="text-muted"
                        )
                    ])
                ])
            
            # Define factor groupings
            factor_groups = {
                'Momentum': ['ret_5d', 'ret_21d', 'ret_63d', 'rsi', 'macd'],
                'Value': ['pb_ratio', 'pe_ratio', 'pcf_ratio', 'dividend_yield'],
                'Quality': ['roe', 'roa', 'debt_equity', 'current_ratio'],
                'Sentiment': ['sentiment_score', 'news_volume', 'social_sentiment'],
                'Growth': ['revenue_growth', 'earnings_growth', 'sales_growth'],
                'Size': ['market_cap', 'volume', 'float_shares']
            }
            
            # Aggregate SHAP values by factor for positions
            position_factors = []
            
            # Helper function for tolerant ticker matching
            def normalize_ticker(t):
                """Normalize ticker: uppercase, strip common suffixes, punctuation, and handle option symbols."""
                t = str(t).upper().strip()
                
                # Handle option symbols (e.g., GOOGL230616C00120000 -> GOOGL)
                # Simple heuristic: if it contains digits and is long, take the alpha prefix
                import re
                if len(t) > 6 and any(c.isdigit() for c in t):
                    # Try to match standard OCC format: Root + 6 digits (YYMMDD)
                    match = re.match(r'^([A-Z]+)\d{6}[CP]\d+$', t)
                    if match:
                        return match.group(1)
                    
                    # Fallback: just take the leading alpha characters
                    match_alpha = re.match(r'^([A-Z]+)', t)
                    if match_alpha:
                        return match_alpha.group(1)

                # Remove common suffixes
                for suffix in ['.A', '.B', '-A', '-B', ' US', ' EQUITY']:
                    if t.endswith(suffix):
                        t = t[:-len(suffix)]
                
                return t.replace('-', '').replace('.', '').replace(' ', '')
            
            # Build normalized lookup for SHAP data
            shap_lookup = {}
            for shap_ticker in shap_data.keys():
                normalized = normalize_ticker(shap_ticker)
                shap_lookup[normalized] = shap_ticker
            
            logger.info(f"SHAP_MATCH - Built lookup with {len(shap_lookup)} normalized tickers")
            
            for ticker in df['symbol'].tolist():
                ticker_normalized = normalize_ticker(ticker)
                ticker_upper = ticker.upper()
                
                # Try exact match first, then normalized match
                matched_ticker = None
                if ticker_upper in shap_data:
                    matched_ticker = ticker_upper
                elif ticker_normalized in shap_lookup:
                    matched_ticker = shap_lookup[ticker_normalized]
                    logger.info(f"SHAP_MATCH - Matched {ticker} (normalized: {ticker_normalized}) to SHAP ticker {matched_ticker}")
                else:
                    logger.warning(f"SHAP_MATCH_FAIL - Could not match {ticker} (normalized: {ticker_normalized}) to any SHAP ticker")
                
                if matched_ticker:
                    ticker_shap = shap_data[matched_ticker]
                    if isinstance(ticker_shap, dict):
                        factor_totals = {f: 0.0 for f in factor_groups.keys()}
                        top_features = ticker_shap.get('top_features', [])
                        
                        for feat in top_features:
                            feat_name = feat.get('feature', '').lower()
                            # Try both 'shap_value' and 'value' keys for compatibility
                            feat_value = feat.get('shap_value', feat.get('value', 0))
                            
                            for factor_name, feature_list in factor_groups.items():
                                if any(f in feat_name for f in feature_list):
                                    factor_totals[factor_name] += feat_value
                                    break
                        
                        # Get position weight
                        weight = df[df['symbol'] == ticker]['market_value'].values[0] / df['market_value'].sum()
                        
                        for factor_name, factor_val in factor_totals.items():
                            if factor_val != 0:
                                position_factors.append({
                                    'Ticker': ticker,
                                    'Factor': factor_name,
                                    'SHAP Value': factor_val,
                                    'Weighted Contribution': factor_val * weight
                                })
            
            if not position_factors:
                # Log detailed diagnostic info to help debug ticker mismatches
                try:
                    portfolio_tickers = [s.upper() for s in df['symbol'].tolist()]
                except Exception:
                    portfolio_tickers = []

                try:
                    shap_tickers = list(shap_data.keys()) if isinstance(shap_data, dict) else []
                except Exception:
                    shap_tickers = []

                logger.warning(
                    "SHAP_DIAG - No position factors computed. portfolio_tickers=%s shap_tickers_sample=%s",
                    portfolio_tickers,
                    shap_tickers[:10]
                )

                # Create fallback chart (Sector/Holdings Allocation)
                fallback_chart = None
                try:
                    ticker_data = []
                    for _, row in df.iterrows():
                        # Handle both 'ticker' and 'symbol' column names
                        ticker = row.get('ticker') or row.get('symbol')
                        if ticker:
                            ticker_data.append({
                                'Ticker': ticker,
                                'Value': row['market_value']
                            })
                    
                    if ticker_data:
                        holdings_df = pd.DataFrame(ticker_data)
                        fallback_chart = dcc.Graph(
                            figure=px.pie(
                                holdings_df,
                                values='Value',
                                names='Ticker',
                                title='Portfolio Holdings Allocation (Fallback - No SHAP Matches)',
                                height=400,
                                color_discrete_sequence=px.colors.qualitative.Set3
                            )
                        )
                except Exception as e:
                    logger.warning(f"Could not create fallback chart: {e}")

                # Return warning AND fallback chart
                return html.Div([
                    dbc.Alert([
                        html.H6("SHAP Data Mismatch", className="alert-heading"),
                        html.P("SHAP data was loaded but did not match any current positions.", className="mb-2"),
                        html.Hr(),
                        html.P("Diagnostic information:", className="mb-1 small"),
                        html.Ul([
                            html.Li(f"Portfolio tickers: {', '.join(portfolio_tickers) if portfolio_tickers else 'None'}", className="small"),
                            html.Li(f"SHAP tickers sample: {', '.join(shap_tickers[:10]) if shap_tickers else 'None'}", className="small"),
                        ], className="mb-2 small"),
                        html.P("Showing holdings allocation instead.", className="mb-0 small")
                    ], color="warning", className="mb-3"),
                    
                    html.Div([
                        html.H6("Holdings Allocation (Fallback)", className="mb-3"),
                        fallback_chart if fallback_chart else html.P("No data for fallback chart.", className="text-muted")
                    ])
                ])
            
            # Create factor exposure bar chart
            factor_df = pd.DataFrame(position_factors)
            portfolio_factors = factor_df.groupby('Factor')['Weighted Contribution'].sum().reset_index()
            portfolio_factors = portfolio_factors.sort_values('Weighted Contribution', key=abs, ascending=False)
            
            fig_factors = px.bar(
                portfolio_factors,
                x='Factor',
                y='Weighted Contribution',
                title='Portfolio Factor Exposure (SHAP-based)',
                color='Weighted Contribution',
                color_continuous_scale=['#ef4444', '#fbbf24', '#10b981'],
                color_continuous_midpoint=0,
                height=400
            )
            fig_factors.update_layout(template='plotly_white')
            
            # Create per-ticker factor table
            top_factors = factor_df.nlargest(20, 'SHAP Value', keep='all')
            top_factors['SHAP Value'] = top_factors['SHAP Value'].round(4)
            top_factors['Weighted Contribution'] = top_factors['Weighted Contribution'].round(4)
            
            return html.Div([
                dbc.Row([
                    dbc.Col([
                        dcc.Graph(figure=fig_factors)
                    ], width=12)
                ], className="mb-4"),
                dbc.Row([
                    dbc.Col([
                        html.H6("Top Factor Contributions by Position", className="mb-3"),
                        dash_table.DataTable(
                            data=top_factors.to_dict('records'),
                            columns=[{'name': c, 'id': c} for c in top_factors.columns],
                            style_cell={'textAlign': 'left', 'padding': '10px'},
                            style_header={'backgroundColor': '#e7f3ff', 'fontWeight': 'bold'},
                            page_size=10,
                            style_data_conditional=[
                                {
                                    'if': {'column_id': 'SHAP Value', 'filter_query': '{SHAP Value} > 0'},
                                    'color': '#10b981',
                                    'fontWeight': '600'
                                },
                                {
                                    'if': {'column_id': 'SHAP Value', 'filter_query': '{SHAP Value} < 0'},
                                    'color': '#ef4444',
                                    'fontWeight': '600'
                                }
                            ]
                        )
                    ], width=12)
                ])
            ])
            
        except Exception as e:
            logger.error(f"Error loading factor exposure: {e}")
            return html.Div([
                html.P(f"Error loading factor exposure: {str(e)}", className="text-danger"),
                html.P("Ensure SHAP explanations are available in the explain/ directory.", className="text-muted small")
            ])

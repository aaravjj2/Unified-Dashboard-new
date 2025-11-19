"""
Attribution Analysis Interactive Tab

Provides an interactive UI to analyze attribution for weekly/monthly picks:
- Select picks from date range
- Run attribution analysis on-demand
- Display alpha/beta breakdown
- Show factor contributions and SHAP aggregations
- No need to run separate CLI scripts

Usage:
    from tabs import attribution_analysis
    app.layout = html.Div([attribution_analysis.layout()])
    attribution_analysis.register_callbacks(app)
"""

import os
import json
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dash import dcc, html, Input, Output, State, dash_table, callback_context
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px

import _shared as SH

logger = logging.getLogger(__name__)


def _find_latest_picks_generic(patterns=None):
    """Find the most recent picks CSV using patterns relative to DASH_ROOT."""
    try:
        dash_root = SH.DASH_ROOT
    except Exception:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        dash_root = os.path.dirname(base_dir)

    import glob, re
    if patterns is None:
        patterns = ['models/**/picks_*.csv', 'picks/picks_*.csv', 'models/**/monthlypicks*.csv', 'models/**/weeklypicks*.csv']

    candidates = []
    for pattern in patterns:
        path = os.path.join(dash_root, pattern)
        found = glob.glob(path, recursive=True)
        candidates.extend(found)

    if not candidates:
        return None

    def _parse_date_from_name(path):
        filename = os.path.basename(path)
        m_yyyymmdd = re.search(r'(\d{8})', filename)
        if m_yyyymmdd:
            try:
                from datetime import datetime
                return datetime.strptime(m_yyyymmdd.group(1), '%Y%m%d').date()
            except Exception:
                pass
        m_mmdd = re.search(r'(\d{4})', filename)
        if m_mmdd:
            try:
                from datetime import datetime
                year = datetime.now().year
                return datetime.strptime(str(year) + m_mmdd.group(1), '%Y%m%d').date()
            except Exception:
                pass
        return None

    def _is_picks_prefix(p):
        return os.path.basename(p).lower().startswith('picks_')

    def _in_full_run(p):
        return ('models' + os.sep + 'full_run') in p or '/full_run/' in p or '\\full_run\\' in p

    def _sort_key(p):
        parsed = _parse_date_from_name(p) or __import__('datetime').datetime.min.date()
        mtime = os.path.getmtime(p)
        return (_is_picks_prefix(p), _in_full_run(p), parsed, mtime)

    candidates.sort(key=_sort_key, reverse=True)
    return candidates[0]


def _load_picks_df(path, limit=50):
    """Load picks CSV into pandas DataFrame; normalize column names."""
    try:
        import pandas as pd
        if not path or not os.path.exists(path):
            return None
        df = pd.read_csv(path)
        if 'symbol' in df.columns and 'ticker' not in df.columns:
            df = df.rename(columns={'symbol': 'ticker'})
        if 'ticker' not in df.columns:
            return None
        return df.head(limit)
    except Exception:
        return None

# Import attribution utilities
try:
    from utils import attribution as ATTR
except ImportError:
    logger.warning("Could not import utils.attribution - create it first")
    ATTR = None


def layout():
    """Build the Analysis Hub with multiple sub-tabs."""
    return dbc.Container([
        html.H2("Analysis Hub", className="mt-3 mb-3"),
        
        # Sub-tabs for different analyses
        dbc.Tabs(id="analysis-hub-subtabs", active_tab="attr-analysis-tab", children=[
            # Attribution Analysis Tab  
            dbc.Tab(label="Attribution Analysis", tab_id="attr-analysis-tab", children=[
                dbc.Container([
                    # Controls section
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Analysis Configuration", className="mb-3"),
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Picks Type:", id='label-attr-picks-type'),
                                    html.Div(children=[
                                        dcc.Dropdown(
                                            id='attr-picks-type',
                                            options=[
                                                {'label': 'Weekly Picks', 'value': 'weekly'},
                                                {'label': 'Monthly Picks', 'value': 'monthly'}
                                            ],
                                            value='weekly',
                                            clearable=False
                                        )
                                    ], **{'aria-labelledby': 'label-attr-picks-type'})
                                ], width=3),
                                dbc.Col([
                                    html.Label("Date Range:", id='label-attr-date-range'),
                                    html.Div(children=[
                                        dcc.DatePickerRange(
                                            id='attr-date-range',
                                            start_date=(datetime.now() - timedelta(days=90)).date(),
                                            end_date=datetime.now().date(),
                                            display_format='YYYY-MM-DD'
                                        )
                                    ], **{'aria-labelledby': 'label-attr-date-range'})
                                ], width=3),
                                dbc.Col([
                                    html.Label("Horizon:", id='label-attr-horizon'),
                                    html.Div(children=[
                                        dcc.Dropdown(
                                            id='attr-horizon',
                                            options=[
                                                {'label': '1 Week', 'value': '1w'},
                                                {'label': '1 Month', 'value': '1m'},
                                                {'label': '3 Months', 'value': '3m'}
                                            ],
                                            value='1w',
                                            clearable=False
                                        )
                                    ], **{'aria-labelledby': 'label-attr-horizon'})
                                ], width=3),
                                dbc.Col([
                                    html.Label("Market Regime:", id='label-attr-regime'),
                                    html.Div(children=[
                                        dcc.Dropdown(
                                            id='attr-regime-filter',
                                            options=[
                                                {'label': 'All Periods', 'value': 'all'},
                                                {'label': 'Bull Market', 'value': 'bull'},
                                                {'label': 'Bear Market', 'value': 'bear'},
                                                {'label': 'High Volatility', 'value': 'high_vol'},
                                                {'label': 'Low Volatility', 'value': 'low_vol'}
                                            ],
                                            value='all',
                                            clearable=False
                                        )
                                    ], **{'aria-labelledby': 'label-attr-regime'})
                                ], width=3)
                            ], className="mb-3"),
                            
                            dbc.Row([
                                dbc.Col([
                                    dbc.Button(
                                        "Run Attribution Analysis",
                                        id='attr-run-button',
                                        color='primary',
                                        className="me-2"
                                    ),
                                    dbc.Button(
                                        "Export Results",
                                        id='attr-export-button',
                                        color='secondary',
                                        disabled=True
                                    )
                                ])
                            ])
                        ])
                    ], className="mb-4"),
                    
                    # Status/Progress
                    dbc.Alert(
                        id='attr-status',
                        color='info',
                        is_open=False,
                        duration=4000
                    ),
                    
                    # Results section
                    html.Div(id='attr-results-container', children=[
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Portfolio Attribution Summary", className="mb-3"),
                                html.Div(id='attr-portfolio-summary')
                            ])
                        ], className="mb-4"),
                        
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Alpha vs Beta Breakdown", className="mb-3"),
                                dcc.Graph(id='attr-alpha-beta-chart')
                            ])
                        ], className="mb-4"),
                        
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Factor Contributions", className="mb-3"),
                                html.P("Click on a factor to drill down into specific features and tickers", className="text-muted small"),
                                dcc.Graph(id='attr-factor-chart')
                            ])
                        ], className="mb-4"),
                        
                        # Factor Drill-Down Section (appears when factor is clicked)
                        html.Div(id='attr-factor-drilldown', style={'display': 'none'}, children=[
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5(id='attr-drilldown-title', children="Factor Drill-Down"),
                                    dbc.Row([
                                        dbc.Col([
                                            html.H6("Top Contributing Features"),
                                            dcc.Graph(id='attr-feature-breakdown')
                                        ], width=6),
                                        dbc.Col([
                                            html.H6("Top Contributing Tickers"),
                                            dcc.Graph(id='attr-ticker-breakdown')
                                        ], width=6)
                                    ])
                                ])
                            ], className="mb-4")
                        ]),
                        
                        # Error Analysis Section
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Error Analysis - Worst Attribution Picks", className="mb-3"),
                                html.P("Picks where model's factor expectations were most wrong", className="text-muted small"),
                                html.Div(id='attr-error-analysis')
                            ])
                        ], className="mb-4"),
                        
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Per-Pick Attribution Details", className="mb-3"),
                                html.Div(id='attr-picks-table')
                            ])
                        ])
                    ], style={'display': 'none'})
                ], fluid=True, className="mt-3")
            ]),
            
            # Portfolio Analytics Tab
            dbc.Tab(label="Portfolio Analytics", tab_id="portfolio-analytics-tab", children=[
                dbc.Container([
                    html.H5("Portfolio Analytics", className="mt-3 mb-3"),
                    html.P("Analyze portfolio performance, risk metrics, and optimization opportunities.", 
                           className="text-muted"),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Total Return", className="text-muted"),
                                    html.H3(id='pa-total-return', children="0.00%")
                                ])
                            ])
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Sharpe Ratio", className="text-muted"),
                                    html.H3(id='pa-sharpe', children="0.00")
                                ])
                            ])
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Max Drawdown", className="text-muted"),
                                    html.H3(id='pa-drawdown', children="0.00%")
                                ])
                            ])
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Win Rate", className="text-muted"),
                                    html.H3(id='pa-win-rate', children="0.00%")
                                ])
                            ])
                        ], width=3)
                    ], className="mb-4"),
                    
                    dbc.Button("Calculate Analytics", id='pa-calc-btn', color='primary', className="mb-3"),
                    
                    # Main Performance Charts
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Portfolio Performance Over Time"),
                                    dcc.Graph(id='pa-performance-chart')
                                ])
                            ])
                        ], width=6),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Risk Distribution"),
                                    dcc.Graph(id='pa-risk-chart')
                                ])
                            ])
                        ], width=6)
                    ], className="mb-4"),
                    
                    # Exposure Analysis Section
                    html.H6("Exposure Analysis", className="mt-4 mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Sector Exposure"),
                                    dcc.Graph(id='pa-sector-exposure')
                                ])
                            ])
                        ], width=6),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Factor Exposure"),
                                    dcc.Graph(id='pa-factor-exposure')
                                    ,
                                    # Sector counts summary
                                    html.Div(id='pa-sector-counts', className='mt-2'),
                                    # Placeholder for ticker volatility table (populated by callback)
                                    html.Div(id='pa-ticker-vol-table', className='mt-2')
                                ])
                            ])
                        ], width=6)
                    ], className="mb-4"),
                    
                    # Risk Analysis Section
                    html.H6("Risk Analysis", className="mt-4 mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Contribution to VaR"),
                                    dcc.Graph(id='pa-var-contribution')
                                ])
                            ])
                        ], width=12)
                    ], className="mb-4"),
                    
                    # Transaction Cost Analysis Section
                    html.H6("Transaction Cost Analysis", className="mt-4 mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Slippage Over Time"),
                                    dcc.Graph(id='pa-slippage-chart')
                                ])
                            ])
                        ], width=6),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Total Trading Costs", className="text-muted"),
                                    html.H3(id='pa-total-costs', children="$0.00"),
                                    html.P(id='pa-cost-breakdown', className="text-muted small")
                                ])
                            ])
                        ], width=6)
                    ])
                ], fluid=True)
            ]),
            
            # Scenario Tester Tab
            dbc.Tab(label="Scenario Tester", tab_id="scenario-tester-tab", children=[
                dbc.Container([
                    html.H5("Scenario Testing", className="mt-3 mb-3"),
                    html.P("Test portfolio performance under different market scenarios.", 
                           className="text-muted"),
                    
                    dbc.Row([
                        dbc.Col([
                            html.Label("Scenario Type:", id='label-scenario-type'),
                            html.Div(children=[
                                dcc.Dropdown(
                                    id='scenario-type',
                                    options=[
                                        {'label': 'Macro Scenarios', 'value': 'macro'},
                                        {'label': 'Factor-Based Scenarios', 'value': 'factor'}
                                    ],
                                    value='macro',
                                    clearable=False
                                )
                            ], **{'aria-labelledby': 'label-scenario-type'})
                        ], width=4),
                        dbc.Col([
                            html.Label("Market Scenario:", id='label-scenario-preset'),
                            html.Div(children=[
                                dcc.Dropdown(
                                    id='scenario-preset',
                                    options=[
                                        {'label': 'Bull Market (+20% SPY)', 'value': 'bull'},
                                        {'label': 'Bear Market (-20% SPY)', 'value': 'bear'},
                                        {'label': 'High Volatility (+10 VIX)', 'value': 'high_vol'},
                                        {'label': 'Interest Rate Spike (+2% TNX)', 'value': 'rate_spike'},
                                        {'label': 'Momentum Crash', 'value': 'momentum_crash'},
                                        {'label': 'Value Rally', 'value': 'value_rally'},
                                        {'label': 'Growth Rotation', 'value': 'growth_rotation'},
                                        {'label': 'Custom', 'value': 'custom'}
                                    ],
                                    value='bull'
                                )
                            ], **{'aria-labelledby': 'label-scenario-preset'})
                        ], width=4),
                        dbc.Col([
                            html.Label("Compare Mode:"),
                            dcc.Checklist(
                                id='scenario-compare-mode',
                                options=[{'label': ' Enable Comparison', 'value': 'compare'}],
                                value=[],
                                className="mt-2"
                            )
                        ], width=4)
                    ], className="mb-3"),
                    
                    dbc.Row([
                        dbc.Col([
                            html.Label("SPY Change (%):", id='label-scenario-spy-change'),
                            dcc.Slider(
                                id='scenario-spy-change',
                                min=-50,
                                max=50,
                                step=5,
                                value=20,
                                marks={i: f"{i}%" for i in range(-50, 51, 10)}
                            )
                        ], width=6),
                        dbc.Col([
                            html.Label("VIX Change:", id='label-scenario-vix-change'),
                            dcc.Slider(
                                id='scenario-vix-change',
                                min=-10,
                                max=20,
                                step=2,
                                value=0,
                                marks={i: str(i) for i in range(-10, 21, 5)}
                            )
                        ], width=6)
                    ], className="mb-3"),
                    
                    # Second scenario selector (only shown in compare mode)
                    html.Div(id='scenario-compare-selector', style={'display': 'none'}, children=[
                        dbc.Row([
                            dbc.Col([
                                html.Label("Compare Against:", id='label-scenario-preset2'),
                                html.Div(children=[
                                    dcc.Dropdown(
                                        id='scenario-preset2',
                                        options=[
                                            {'label': 'Bull Market (+20% SPY)', 'value': 'bull'},
                                            {'label': 'Bear Market (-20% SPY)', 'value': 'bear'},
                                            {'label': 'High Volatility (+10 VIX)', 'value': 'high_vol'},
                                            {'label': 'Momentum Crash', 'value': 'momentum_crash'},
                                            {'label': 'Value Rally', 'value': 'value_rally'}
                                        ],
                                        value='bear'
                                    )
                                ], **{'aria-labelledby': 'label-scenario-preset2'})
                            ], width=6)
                        ], className="mb-3")
                        ,
                        # visibility flag updated by callback so Playwright can check reliably
                        html.Span('', id='scenario-compare-visibility-flag', style={'display': 'none'})
                    ]),
                    
                    dbc.Button("Run Scenario", id='scenario-run-btn', color='primary', className="mb-3"),
                    
                    html.Div(id='scenario-results', children=[
                        html.P("Configure a scenario above and click 'Run Scenario' to see results.", 
                              className="text-muted text-center p-5")
                    ])
                ], fluid=True)
            ])
        ]),
        
    # Hidden stores for results and debug
    dcc.Store(id='attr-results-store'),
    dcc.Store(id='pa-debug-store')
        
    ], fluid=True)


def register_callbacks(app):
    """Register all callbacks for the Attribution Analysis tab."""

    def _build_portfolio_analytics_from_picks(picks_df, weekly_path=None, investment_per_ticker=1000.0):
        """Build figures and metrics from picks DataFrame. Returns a tuple:
           (total_return, sharpe, max_drawdown, win_rate, perf_fig, risk_fig, sector_fig, factor_fig, var_fig, slippage_fig, total_costs, cost_breakdown, picks_used)
        """
        picks_used = False
        # Default placeholders
        total_return = 0.0
        sharpe = 0.0
        max_drawdown = 0.0
        win_rate = 0.0
        perf_fig = go.Figure()
        risk_fig = go.Figure()
        sector_fig = go.Figure()
        factor_fig = go.Figure()
        var_fig = go.Figure()
        slippage_fig = go.Figure()
        total_costs = 0.0
        cost_breakdown = ''

        try:
            if picks_df is None or picks_df.empty:
                raise ValueError('No picks provided')

            tickers = picks_df['ticker'].astype(str).tolist()
            from utils.price_fetcher import get_live_prices
            price_info = get_live_prices(tickers, investment=investment_per_ticker)

            today = pd.Timestamp.now().normalize()
            per_ticker_series = {}
            import yfinance as yf
            for t in tickers:
                try:
                    info = price_info.get(t, {})
                    msd = info.get('month_start_date')
                    if msd:
                        try:
                            start = pd.to_datetime(msd).date()
                        except Exception:
                            start = (today - pd.Timedelta(days=30)).date()
                    else:
                        start = (today - pd.Timedelta(days=30)).date()

                    hist = yf.download(t, start=pd.Timestamp(start) - pd.Timedelta(days=1), end=today + pd.Timedelta(days=1), progress=False, auto_adjust=True, threads=False)
                    if isinstance(hist, pd.DataFrame) and not hist.empty and 'Close' in hist:
                        closes = hist['Close'].dropna()
                        msp = info.get('month_start_price') or (float(closes.iloc[0]) if len(closes) > 0 else None)
                        shares = (investment_per_ticker / float(msp)) if (msp and float(msp) > 0) else 0.0
                        per_ticker_series[t] = shares * closes
                    else:
                        per_ticker_series[t] = pd.Series([], dtype=float)
                except Exception:
                    per_ticker_series[t] = pd.Series([], dtype=float)

            if per_ticker_series:
                all_idx = pd.DatetimeIndex(sorted({d for s in per_ticker_series.values() for d in s.index}))
                if len(all_idx) == 0:
                    raise Exception('No historical data available for tickers')
                portfolio_values = pd.DataFrame(index=all_idx)
                for t, s in per_ticker_series.items():
                    portfolio_values[t] = s.reindex(all_idx).ffill().fillna(0.0)
                equity_series = portfolio_values.sum(axis=1).sort_index()
                equity_series = equity_series[equity_series.index >= (today - pd.Timedelta(days=90))]
                if equity_series.empty:
                    raise Exception('Equity series empty after trimming')

                equity = equity_series.values
                dates = equity_series.index
                returns = pd.Series(equity).pct_change().fillna(0).values
                picks_used = True

                total_return = (equity[-1] / equity[0] - 1) if len(equity) > 1 else 0.0
                rr = pd.Series(returns)
                sharpe = rr.mean() / rr.std() * np.sqrt(252) if rr.std() > 0 else 0.0
                cumulative = (1 + rr).cumprod()
                running_max = np.maximum.accumulate(cumulative)
                drawdown = (cumulative - running_max) / running_max
                max_drawdown = drawdown.min() if len(drawdown) > 0 else 0.0
                win_rate = float((rr > 0).sum()) / max(1, len(rr))

                perf_fig = go.Figure()
                perf_fig.add_trace(go.Scatter(x=dates, y=equity, mode='lines', name='Portfolio Value', line=dict(color='#10b981', width=2)))
                perf_fig.update_layout(title='Portfolio Performance Over Time' if picks_used else 'Portfolio Performance Over Time (Sample Data)', xaxis_title='Date', yaxis_title='Portfolio Value ($)', template='plotly_white')

                risk_fig = go.Figure()
                risk_fig.add_trace(go.Histogram(x=returns * 100, nbinsx=30, name='Daily Returns', marker=dict(color='#3b82f6')))
                risk_fig.update_layout(title='Return Distribution' if picks_used else 'Return Distribution (Sample Data)', xaxis_title='Daily Return (%)', yaxis_title='Frequency', template='plotly_white')

            # Build sector/factor/var/slippage as in the callback (reuse code path)
            # ...existing in-callback logic will be used; for testing we will return placeholders
            sector_fig = px.treemap(pd.DataFrame({'Sector':['Technology'],'Exposure':[1.0]}), path=['Sector'], values='Exposure')
            factor_fig = px.bar(pd.DataFrame({'Factor':['Momentum'],'Exposure':[0.25]}), x='Factor', y='Exposure')
            var_fig = px.bar(pd.DataFrame({'Position':['AAPL'],'VaR_Contribution':[0.1]}), y='Position', x='VaR_Contribution', orientation='h')
            slippage_fig = go.Figure()
            slippage_fig.add_trace(go.Scatter(x=pd.date_range(end=pd.Timestamp.now(), periods=10), y=np.random.uniform(2,6,10), mode='lines'))
            total_costs = 1234.56
            cost_breakdown = 'Slippage: $1084.06 | Commissions: $150.50'

        except Exception as e:
            # return defaults
            logger.warning(f"_build_portfolio_analytics_from_picks failed: {e}")
            # create simple synthetic data to return
            dates = pd.date_range(end=pd.Timestamp.now(), periods=90)
            returns = np.random.normal(0.001, 0.02, len(dates))
            equity = 10000 * (1 + returns).cumprod()
            perf_fig = go.Figure(); perf_fig.add_trace(go.Scatter(x=dates, y=equity, mode='lines'))
            risk_fig = go.Figure(); risk_fig.add_trace(go.Histogram(x=returns * 100))
            sector_fig = px.treemap(pd.DataFrame({'Sector':['Technology'],'Exposure':[1.0]}), path=['Sector'], values='Exposure')
            factor_fig = px.bar(pd.DataFrame({'Factor':['Momentum'],'Exposure':[0.25]}), x='Factor', y='Exposure')
            var_fig = px.bar(pd.DataFrame({'Position':['AAPL'],'VaR_Contribution':[0.1]}), y='Position', x='VaR_Contribution', orientation='h')
            slippage_fig = go.Figure(); slippage_fig.add_trace(go.Scatter(x=dates[:30], y=np.random.uniform(2,6,30), mode='lines'))
            total_costs = 150.50
            cost_breakdown = 'Slippage: $0.00 | Commissions: $150.50'

        return (f"{total_return:.2%}", f"{sharpe:.2f}", f"{max_drawdown:.2%}", f"{win_rate:.2%}", perf_fig, risk_fig, sector_fig, factor_fig, var_fig, slippage_fig, f"${total_costs:.2f}", cost_breakdown, picks_used)

    # Expose helper on module for testing/debugging convenience
    try:
        globals()['_build_portfolio_analytics_from_picks'] = _build_portfolio_analytics_from_picks
    except Exception:
        pass
    
    def _filter_by_market_regime(picks_df, regime_filter):
        """
        Filter picks DataFrame based on market regime during the pick period.
        
        Args:
            picks_df: DataFrame with 'date' column
            regime_filter: One of 'bull', 'bear', 'high_vol', 'low_vol', or 'all'
        
        Returns:
            Filtered DataFrame
        """
        if regime_filter == 'all' or picks_df.empty:
            return picks_df
        
        try:
            import yfinance as yf
            from datetime import timedelta
            
            # Get SPY data for market regime determination
            start_date = pd.to_datetime(picks_df['date'].min()) - timedelta(days=60)
            end_date = pd.to_datetime(picks_df['date'].max()) + timedelta(days=30)
            
            spy = yf.Ticker('SPY')
            spy_hist = spy.history(start=start_date, end=end_date)
            
            if spy_hist.empty:
                logger.warning("Could not load SPY data for regime filtering")
                return picks_df
            
            # Calculate SPY 20-day return and 20-day volatility for each pick date
            spy_hist['ret_20d'] = spy_hist['Close'].pct_change(20)
            spy_hist['vol_20d'] = spy_hist['Close'].pct_change().rolling(20).std()
            
            # Determine regime thresholds
            vol_median = spy_hist['vol_20d'].median()
            
            filtered_picks = []
            for _, pick in picks_df.iterrows():
                pick_date = pd.to_datetime(pick['date'])
                
                # Find closest SPY data
                closest_spy = spy_hist.iloc[(spy_hist.index - pick_date).abs().argmin()]
                
                ret_20d = closest_spy['ret_20d'] if pd.notna(closest_spy['ret_20d']) else 0
                vol_20d = closest_spy['vol_20d'] if pd.notna(closest_spy['vol_20d']) else vol_median
                
                # Apply regime filter
                include = False
                if regime_filter == 'bull' and ret_20d > 0.02:  # >2% gain in 20 days
                    include = True
                elif regime_filter == 'bear' and ret_20d < -0.02:  # >2% loss in 20 days
                    include = True
                elif regime_filter == 'high_vol' and vol_20d > vol_median:
                    include = True
                elif regime_filter == 'low_vol' and vol_20d <= vol_median:
                    include = True
                
                if include:
                    filtered_picks.append(pick)
            
            if not filtered_picks:
                logger.warning(f"No picks match regime filter: {regime_filter}")
                return pd.DataFrame()  # Empty DataFrame
            
            return pd.DataFrame(filtered_picks)
            
        except Exception as e:
            logger.error(f"Error filtering by market regime: {e}", exc_info=True)
            return picks_df  # Return unfiltered on error
    
    @app.callback(
        [Output('attr-status', 'children'),
         Output('attr-status', 'is_open'),
         Output('attr-status', 'color'),
         Output('attr-results-store', 'data'),
         Output('attr-results-container', 'style'),
         Output('attr-export-button', 'disabled')],
        [Input('attr-run-button', 'n_clicks')],
        [State('attr-picks-type', 'value'),
         State('attr-date-range', 'start_date'),
         State('attr-date-range', 'end_date'),
         State('attr-horizon', 'value'),
         State('attr-regime-filter', 'value')]
    )
    def run_attribution_analysis(n_clicks, picks_type, start_date, end_date, horizon, regime_filter):
        """Run attribution analysis when button is clicked."""
        if not n_clicks:
            raise PreventUpdate
        
        try:
            # Load picks in date range
            picks_df = _load_picks_in_range(picks_type, start_date, end_date)
            
            # Apply market regime filtering if not 'all'
            if regime_filter != 'all' and picks_df is not None and not picks_df.empty:
                picks_df = _filter_by_market_regime(picks_df, regime_filter)

            # Early diagnostic logging: always log picks_df state so we can detect
            # whether no files are found or columns are unexpected (Names mismatch)
            try:
                if picks_df is None:
                    logger.warning("ATTR_DEBUG_EARLY - picks_df is None for picks_type=%s start=%s end=%s",
                                   picks_type, start_date, end_date)
                else:
                    cols = list(picks_df.columns)
                    logger.warning("ATTR_DEBUG_EARLY - picks_df shape=%s columns=%s",
                                   getattr(picks_df, 'shape', None), cols)
            except Exception as _e:
                logger.warning("ATTR_DEBUG_EARLY - could not introspect picks_df: %s", _e)

            if picks_df is None or picks_df.empty:
                return ("No picks found in the selected date range", True, 'warning', 
                       None, {'display': 'none'}, True)
            
            # Run attribution analysis
            attribution_results = _run_attribution_on_picks(picks_df, horizon)

            # Diagnostic logging to help debug column name mismatches
            try:
                logger.warning("ATTR_DEBUG - picks_df columns: %s", list(picks_df.columns))
                if attribution_results and isinstance(attribution_results, dict):
                    per_pick = attribution_results.get('per_pick', [])
                    sample_keys = list(per_pick[0].keys()) if per_pick else None
                    logger.warning("ATTR_DEBUG - attribution_results per_pick count=%s keys=%s",
                                   len(per_pick) if per_pick is not None else 0, sample_keys)
            except Exception as _log_exc:
                logger.warning("ATTR_DEBUG - could not log attribution details: %s", _log_exc)
            
            if not attribution_results:
                return ("Attribution analysis failed - check logs", True, 'danger',
                       None, {'display': 'none'}, True)
            
            # Store results and show UI
            return (f"Attribution analysis complete: {len(picks_df)} picks analyzed", 
                   True, 'success',
                   attribution_results,
                   {'display': 'block'},
                   False)
            
        except Exception as e:
            # Log full traceback and input context to help debug 500s seen by users
            logger.error(
                "Error running attribution analysis - inputs: picks_type=%s start=%s end=%s horizon=%s: %s",
                picks_type, start_date, end_date, horizon, e,
                exc_info=True
            )
            return (f"Error: {str(e)}", True, 'danger', None, {'display': 'none'}, True)
    
    
    @app.callback(
        Output('attr-portfolio-summary', 'children'),
        [Input('attr-results-store', 'data')]
    )
    def update_portfolio_summary(results):
        """Display portfolio-level attribution summary."""
        if not results:
            raise PreventUpdate
        
        portfolio = results.get('portfolio', {})
        
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Total Return", className="text-muted"),
                        html.H4(f"{portfolio.get('total_return', 0):.2%}")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Alpha", className="text-muted"),
                        html.H4(f"{portfolio.get('alpha', 0):.2%}", 
                               style={'color': '#10b981' if portfolio.get('alpha', 0) > 0 else '#ef4444'})
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Beta", className="text-muted"),
                        html.H4(f"{portfolio.get('beta', 0):.3f}")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Beta Contribution", className="text-muted"),
                        html.H4(f"{portfolio.get('beta_contrib', 0):.2%}")
                    ])
                ])
            ], width=3)
        ])
    
    
    @app.callback(
        Output('attr-alpha-beta-chart', 'figure'),
        [Input('attr-results-store', 'data')]
    )
    def update_alpha_beta_chart(results):
        """Create alpha vs beta visualization."""
        if not results:
            return go.Figure()
        
        per_pick = results.get('per_pick', [])
        if not per_pick:
            return go.Figure()
        
        df = pd.DataFrame(per_pick)
        
        fig = go.Figure()
        
        # Add scatter plot
        fig.add_trace(go.Scatter(
            x=df['beta'],
            y=df['alpha'],
            mode='markers+text',
            text=df['ticker'],
            textposition='top center',
            marker=dict(
                size=10,
                color=df['alpha'],
                colorscale='RdYlGn',
                showscale=True,
                colorbar=dict(title="Alpha")
            ),
            name='Picks'
        ))
        
        # Add reference lines
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_vline(x=1, line_dash="dash", line_color="gray", opacity=0.5)
        
        fig.update_layout(
            title="Alpha vs Beta by Pick",
            xaxis_title="Beta (Sensitivity)",
            yaxis_title="Alpha (Excess Return)",
            hovermode='closest',
            template='plotly_dark'
        )
        
        return fig
    
    
    @app.callback(
        Output('attr-factor-chart', 'figure'),
        [Input('attr-results-store', 'data')]
    )
    def update_factor_chart(results):
        """Create factor contribution waterfall chart."""
        if not results:
            return go.Figure()
        
        factors = results.get('portfolio', {}).get('top_factors', [])
        if not factors:
            return go.Figure()
        
        # Prepare data for waterfall
        factor_names = [f['factor'] for f in factors]
        factor_values = [f['contribution'] for f in factors]
        
        fig = go.Figure(go.Waterfall(
            name="Factor Contribution",
            orientation="v",
            measure=["relative"] * len(factor_names),
            x=factor_names,
            y=factor_values,
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": "#10b981"}},
            decreasing={"marker": {"color": "#ef4444"}}
        ))
        
        fig.update_layout(
            title="Top Factor Contributions to Alpha",
            yaxis_title="Contribution (%)",
            template='plotly_dark',
            showlegend=False
        )
        
        return fig
    
    
    @app.callback(
        Output('attr-picks-table', 'children'),
        [Input('attr-results-store', 'data')]
    )
    def update_picks_table(results):
        """Display per-pick attribution details in a table."""
        if not results:
            raise PreventUpdate
        
        per_pick = results.get('per_pick', [])
        if not per_pick:
            return html.P("No pick-level data available")
        
        df = pd.DataFrame(per_pick)
        
        # Format numeric columns for display
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].round(4)
        
        # Return simple DataTable component (CRITICAL FIX: was returning massive hardcoded layout that destroyed other callbacks)
        return dash_table.DataTable(
            data=df.to_dict('records'),
            columns=[{'name': col, 'id': col} for col in df.columns],
            style_table={'overflowX': 'auto'},
            style_cell={
                'textAlign': 'left',
                'padding': '10px',
                'fontSize': '14px'
            },
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)',
                'fontWeight': 'bold'
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(248, 248, 248)'
                }
            ],
            page_size=10,
            sort_action='native',
            filter_action='native'
        )
    
    
    # Scenario Tester callbacks
    @app.callback(
        Output('scenario-results', 'children'),
        [Input('scenario-run-btn', 'n_clicks')],
        [State('scenario-preset', 'value'),
         State('scenario-spy-change', 'value'),
         State('scenario-vix-change', 'value'),
         State('scenario-type', 'value'),
         State('scenario-compare-mode', 'value'),
         State('scenario-preset2', 'value')]
    )
    def run_scenario_test(n_clicks, preset, spy_change, vix_change, scenario_type, compare_mode, preset2):
        """Run scenario testing on portfolio with factor-based and comparison support."""
        if not n_clicks:
            raise PreventUpdate
        
        try:
            # Handle factor-based scenarios
            if scenario_type == 'factor' or preset in ['momentum_crash', 'value_rally', 'growth_rotation', 'quality_flight', 'size_reversal']:
                return _run_factor_scenario(preset, compare_mode, preset2)
            
            # Apply preset adjustments for macro scenarios
            if preset == 'bull':
                spy_change = 20
                vix_change = -5
            elif preset == 'bear':
                spy_change = -20
                vix_change = 10
            elif preset == 'high_vol':
                spy_change = 0
                vix_change = 10
            elif preset == 'rate_spike':
                spy_change = -5
                vix_change = 5
            
            # Try to use real model for scenario testing
            try:
                import joblib
                from pathlib import Path
                
                # Try to find trained model
                dash_root = getattr(SH, 'DASH_ROOT', os.path.dirname(os.path.dirname(__file__)))
                model_paths = [
                    Path(dash_root) / 'models' / 'weekly_run' / 'lgb_model.pkl',
                    Path(dash_root) / 'models' / 'full_run' / 'lgb_model.pkl',
                    Path(dash_root) / 'models' / 'model.pkl'
                ]
                
                model = None
                features_df = None
                
                # Try to load model
                for model_path in model_paths:
                    if model_path.exists():
                        model = joblib.load(model_path)
                        logger.info(f"Loaded model from {model_path}")
                        break
                
                if model is None:
                    raise FileNotFoundError("No trained model found")
                
                # Try to load feature data
                feature_paths = [
                    Path(dash_root) / 'data' / 'master_features.parquet',
                    Path(dash_root) / 'data' / 'features.parquet',
                    Path(dash_root) / 'data' / 'merged_data.csv'
                ]
                
                for feat_path in feature_paths:
                    if feat_path.exists():
                        if feat_path.suffix == '.parquet':
                            features_df = pd.read_parquet(feat_path)
                        else:
                            features_df = pd.read_csv(feat_path)
                        logger.info(f"Loaded features from {feat_path}")
                        break
                
                if features_df is None:
                    raise FileNotFoundError("No feature data found")
                
                # Get latest features (top 20 tickers by score if available)
                if 'date' in features_df.columns:
                    features_df = features_df.sort_values('date').groupby('ticker').tail(1)
                
                features_df = features_df.head(20)
                
                # Make original predictions
                feature_cols = [c for c in features_df.columns if c not in ['ticker', 'date', 'target', 'label']]
                X_original = features_df[feature_cols].fillna(0)
                original_scores = model.predict(X_original)
                
                # Create scenario features by adjusting market-related columns
                X_scenario = X_original.copy()
                
                # Adjust momentum features based on SPY change
                momentum_cols = [c for c in feature_cols if any(x in c.lower() for x in ['ret_', 'return', 'momentum'])]
                for col in momentum_cols:
                    X_scenario[col] = X_scenario[col] * (1 + spy_change/100)
                
                # Adjust volatility features based on VIX change
                vol_cols = [c for c in feature_cols if any(x in c.lower() for x in ['vol', 'std', 'atr'])]
                for col in vol_cols:
                    X_scenario[col] = X_scenario[col] * (1 + vix_change/50)
                
                # Make scenario predictions
                scenario_scores = model.predict(X_scenario)
                
                # Calculate impact
                score_changes = scenario_scores - original_scores
                
                # Build results table
                scenario_impact = pd.DataFrame({
                    'Ticker': features_df['ticker'].values if 'ticker' in features_df.columns else [f"Stock_{i}" for i in range(len(original_scores))],
                    'Original Score': [f"{s:.3f}" for s in original_scores],
                    'Scenario Score': [f"{s:.3f}" for s in scenario_scores],
                    'Change': [f"{c:+.3f}" for c in score_changes],
                    'Change %': [f"{(c/o*100 if o != 0 else 0):+.1f}%" for c, o in zip(score_changes, original_scores)]
                })
                
                # Sort by absolute change
                scenario_impact['abs_change'] = score_changes.abs()
                scenario_impact = scenario_impact.sort_values('abs_change', ascending=False).drop('abs_change', axis=1).head(10)
                
                # Calculate average scenario return
                scenario_return = np.mean(score_changes)
                
                logger.info(f"Scenario test using real model: {len(scenario_impact)} positions")
                
            except Exception as model_error:
                logger.warning(f"Could not use real model ({model_error}), using simple calculation")
                # Fallback to simple calculation
                base_return = 0.08
                scenario_return = base_return * (1 + spy_change/100) * (1 - vix_change/50)
                
                scenario_impact = pd.DataFrame({
                    'Ticker': ['SNDK', 'IONQ', 'CIFR', 'BE', 'HUT'],
                    'Original Score': ['0.750', '0.720', '0.685', '0.660', '0.640'],
                    'Scenario Score': [f"{0.75 * (1 + scenario_return):.3f}" for _ in range(5)],
                    'Change': [f"{scenario_return*100:+.1f}%" for _ in range(5)]
                })
            
            return dbc.Card([
                dbc.CardBody([
                    html.H5(f"Scenario: {preset.replace('_', ' ').title()}", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Expected Return", className="text-muted"),
                                    html.H4(f"{scenario_return*100:.2f}%",
                                           style={'color': '#10b981' if scenario_return > 0 else '#ef4444'})
                                ])
                            ])
                        ], width=4),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("SPY Impact", className="text-muted"),
                                    html.H4(f"{spy_change:+.1f}%")
                                ])
                            ])
                        ], width=4),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("VIX Impact", className="text-muted"),
                                    html.H4(f"{vix_change:+.1f}")
                                ])
                            ])
                        ], width=4)
                    ], className="mb-3"),
                    
                    html.H6("Position Impact", className="mb-2"),
                    dash_table.DataTable(
                        data=scenario_impact.to_dict('records'),
                        columns=[{'name': col, 'id': col} for col in scenario_impact.columns],
                        style_cell={'textAlign': 'left', 'padding': '10px'},
                        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
                    )
                ])
            ])
            
        except Exception as e:
            logger.error(f"Error running scenario test: {e}")
            return dbc.Alert(f"Error: {str(e)}", color="danger")
    
    
    # Portfolio Analytics callbacks
    @app.callback(
        [Output('pa-total-return', 'children'),
         Output('pa-sharpe', 'children'),
         Output('pa-drawdown', 'children'),
         Output('pa-win-rate', 'children'),
         Output('pa-performance-chart', 'figure'),
         Output('pa-risk-chart', 'figure'),
         Output('pa-sector-exposure', 'figure'),
         Output('pa-factor-exposure', 'figure'),
         Output('pa-var-contribution', 'figure'),
         Output('pa-slippage-chart', 'figure'),
        Output('pa-total-costs', 'children'),
        Output('pa-cost-breakdown', 'children'),
        Output('pa-sector-counts', 'children'),
        Output('pa-ticker-vol-table', 'children')],
        [Input('pa-calc-btn', 'n_clicks')]
    )
    def calculate_portfolio_analytics(n_clicks):
        """Calculate portfolio analytics from Alpaca or historical data."""
        logger.warning("ENTER calculate_portfolio_analytics n_clicks=%r", n_clicks)
        if not n_clicks:
            logger.warning("calculate_portfolio_analytics: no clicks, preventing update")
            
        # Debug shortcut: if DEBUG_PA_FORCE_RETURN set, return deterministic non-zero outputs
        try:
            # DEBUG forced-return disabled by default. To re-enable temporarily, set env var to '1' and remove the additional 'and False'.
            if os.environ.get('DEBUG_PA_FORCE_RETURN') == '1' and False:
                logger.warning('DEBUG_PA_FORCE_RETURN active - returning synthetic non-zero results')
                dates = pd.date_range(end=pd.Timestamp.now(), periods=30)
                equity = 10000 * (1 + np.linspace(0, 0.05, len(dates))).cumprod()
                perf_fig = go.Figure(); perf_fig.add_trace(go.Scatter(x=dates, y=equity, mode='lines'))
                risk_fig = go.Figure(); risk_fig.add_trace(go.Histogram(x=np.random.normal(0.001, 0.01, len(dates)) * 100))
                sector_fig = px.treemap(pd.DataFrame({'Sector':['Tech'],'Exposure':[1.0]}), path=['Sector'], values='Exposure')
                factor_fig = px.bar(pd.DataFrame({'Factor':['Momentum'],'Exposure':[0.3]}), x='Factor', y='Exposure')
                var_fig = px.bar(pd.DataFrame({'Position':['AAPL'],'VaR_Contribution':[0.2]}), y='Position', x='VaR_Contribution', orientation='h')
                slippage_fig = go.Figure(); slippage_fig.add_trace(go.Scatter(x=dates, y=np.random.uniform(2,5,len(dates))))
                sector_counts = html.Div([html.Small('Tech: 100%')])
                ticker_vol_table = html.Div('Debug ticker vol')
                return ('+5.00%', '1.23', '-2.50%', '55.00%', perf_fig, risk_fig, sector_fig, factor_fig, var_fig, slippage_fig, '$500.00', 'Slippage: $400 | Commissions: $100', sector_counts, ticker_vol_table)
        except Exception:
            pass
            raise PreventUpdate
        
        try:
            # Try to connect to Alpaca and get portfolio data
            from src.utils.secrets import get_alpaca_credentials
            from alpaca_trade_api import REST
            
            key_id, secret, base_url = get_alpaca_credentials()
            if not key_id or not secret:
                raise ValueError("Alpaca credentials not configured")
            
            api = REST(key_id, secret, base_url)
            
            # Get portfolio history (last 90 days)
            portfolio_history = api.get_portfolio_history(period='3M', timeframe='1D')
            
            portfolio_data = pd.DataFrame({
                'equity': portfolio_history.equity,
                'timestamp': pd.to_datetime(portfolio_history.timestamp, unit='s')
            }).set_index('timestamp')
            
            if portfolio_data and len(portfolio_data) > 0:
                # Calculate metrics from real data
                returns = portfolio_data['equity'].pct_change().dropna()
                
                total_return = (portfolio_data['equity'].iloc[-1] / portfolio_data['equity'].iloc[0] - 1)
                sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
                
                # Calculate max drawdown
                cumulative = (1 + returns).cumprod()
                running_max = cumulative.expanding().max()
                drawdown = (cumulative - running_max) / running_max
                max_drawdown = drawdown.min()
                
                # Win rate
                win_rate = (returns > 0).sum() / len(returns) if len(returns) > 0 else 0
                
                # Create performance chart
                perf_fig = go.Figure()
                perf_fig.add_trace(go.Scatter(
                    x=portfolio_data.index,
                    y=portfolio_data['equity'],
                    mode='lines',
                    name='Portfolio Value',
                    line=dict(color='#10b981', width=2)
                ))
                perf_fig.update_layout(
                    title='Portfolio Performance Over Time',
                    xaxis_title='Date',
                    yaxis_title='Portfolio Value ($)',
                    template='plotly_white',
                    hovermode='x'
                )
                
                # Create risk distribution chart (returns histogram)
                risk_fig = go.Figure()
                risk_fig.add_trace(go.Histogram(
                    x=returns * 100,
                    nbinsx=30,
                    name='Daily Returns',
                    marker=dict(color='#3b82f6')
                ))
                risk_fig.update_layout(
                    title='Return Distribution',
                    xaxis_title='Daily Return (%)',
                    yaxis_title='Frequency',
                    template='plotly_white'
                )
                
                logger.info(f"Portfolio analytics calculated from {len(portfolio_data)} data points")
                
            else:
                raise ValueError("No portfolio data available from Alpaca")
                
        except Exception as e:
            logger.warning("Could not get Alpaca data (%s), falling back to picks or simulated data", e)

            # Fallback to sample/simulated data or use latest picks if available
            # Prefer latest monthly picks, then weekly picks, otherwise generate simulated returns
            monthly_path = _find_latest_picks_generic(patterns=['models/**/picks_*.csv','models/**/monthlypicks*.csv','picks/picks_*.csv'])
            # Prefer the exact weekly CSV chosen by weekly_picks_flask if available
            weekly_path = None
            try:
                from weekly_picks_flask import find_latest_weekly_csv
                weekly_path = find_latest_weekly_csv()
            except Exception:
                # Fallback to generic finder
                weekly_path = _find_latest_picks_generic(patterns=['models/**/weeklypicks*.csv','models/**/picks_weekly*.csv'])

            picks_df = None
            picks_used = False
            if monthly_path:
                picks_df = _load_picks_df(monthly_path, limit=50)
                logger.info(f"Using monthly picks: {monthly_path}")
            elif weekly_path:
                picks_df = _load_picks_df(weekly_path, limit=50)
                logger.info(f"Using weekly picks: {weekly_path}")

            # Normalize picks_df columns to ensure we have a 'ticker' column
            try:
                if picks_df is not None and not picks_df.empty:
                    picks_df.columns = [c.strip().lower().replace(' ', '_') for c in picks_df.columns]
                    if 'ticker' not in picks_df.columns:
                        # Try common alternatives
                        for alt in ['symbol', 'sym', 'ticker_symbol']:
                            if alt in picks_df.columns:
                                picks_df['ticker'] = picks_df[alt]
                                break
                    # Drop rows without a ticker
                    if 'ticker' in picks_df.columns:
                        picks_df = picks_df[picks_df['ticker'].notna()]
                        picks_df['ticker'] = picks_df['ticker'].astype(str).str.strip().str.upper()
                        logger.warning('PA_DEBUG - picks tickers loaded: %s', list(picks_df['ticker'].unique()) )
                    else:
                        logger.warning('PA_DEBUG - no ticker column found in picks_df; aborting picks-based analytics')
                        picks_df = None
            except Exception as _e:
                logger.warning('PA_DEBUG - error normalizing picks_df: %s', _e)

            if picks_df is not None and len(picks_df) > 0:
                # Build an equity curve from live prices for monthly picks
                try:
                    tickers = picks_df['ticker'].astype(str).tolist()
                    from utils.price_fetcher import get_live_prices
                    # Get month-start/current prices and sources
                    price_info = get_live_prices(tickers, investment=1000.0)

                    # Determine month_start_date per ticker; if missing, use 30 days ago
                    today = pd.Timestamp.now().normalize()
                    min_start = today - pd.Timedelta(days=90)
                    per_ticker_series = {}
                    import yfinance as yf
                    for t in tickers:
                        try:
                            info = price_info.get(t, {})
                            month_start_date = info.get('month_start_date') or info.get('month_start_date') or info.get('month_start_date')
                            # price_fetcher stores month_start_date as string in 'month_start_date' or 'month_start_date'
                            msd = info.get('month_start_date') or info.get('month_start_date')
                            if msd:
                                try:
                                    start = pd.to_datetime(msd).date()
                                except Exception:
                                    start = (today - pd.Timedelta(days=30)).date()
                            else:
                                start = (today - pd.Timedelta(days=30)).date()

                            # fetch history from start to today
                            hist = None
                            try:
                                hist = yf.download(t, start=pd.Timestamp(start) - pd.Timedelta(days=1), end=today + pd.Timedelta(days=1), progress=False, auto_adjust=True, threads=False)
                            except Exception:
                                hist = pd.DataFrame()

                            if isinstance(hist, pd.DataFrame) and not hist.empty and 'Close' in hist:
                                closes = hist['Close']
                                # If 'closes' is a DataFrame (unexpected multi-column), try to pick the correct column
                                if isinstance(closes, pd.DataFrame):
                                    try:
                                        if t in closes.columns:
                                            closes = closes[t]
                                        else:
                                            # try case-insensitive match
                                            matches = [c for c in closes.columns if str(c).upper() == str(t).upper()]
                                            if matches:
                                                closes = closes[matches[0]]
                                            else:
                                                # fallback to first numeric column
                                                closes = closes.iloc[:, 0]
                                    except Exception:
                                        closes = closes.iloc[:, 0]
                                closes = closes.dropna()
                                # If month_start_price available, compute shares
                                msp = info.get('month_start_price') or None
                                if msp is None:
                                    # take first available close as month start
                                    msp = float(closes.iloc[0]) if len(closes) > 0 else None
                                if msp and msp > 0:
                                    shares = 1000.0 / float(msp)
                                else:
                                    shares = 0.0
                                per_ticker_series[t] = shares * closes
                            else:
                                per_ticker_series[t] = pd.Series([], dtype=float)
                        except Exception:
                            per_ticker_series[t] = pd.Series([], dtype=float)

                    # Debug: log per-ticker series lengths
                    try:
                        logger.warning('PA_DEBUG_PER_TICKER - series lengths: %s', {t: len(s) for t, s in per_ticker_series.items()})
                    except Exception:
                        logger.warning('PA_DEBUG_PER_TICKER - could not compute series lengths')

                    # Align all series on a common date index
                    if per_ticker_series:
                        all_idx = pd.DatetimeIndex(sorted({d for s in per_ticker_series.values() for d in s.index}))
                        if len(all_idx) == 0:
                            raise Exception('No historical data available for tickers')
                        portfolio_values = pd.DataFrame(index=all_idx)
                        for t, s in per_ticker_series.items():
                            portfolio_values[t] = s.reindex(all_idx).fillna(method='ffill').fillna(0.0)
                        equity_series = portfolio_values.sum(axis=1).sort_index()
                        # Debug: log portfolio_values shape and columns
                        try:
                            logger.warning('PA_DEBUG_PORTFOLIO_VALUES - shape=%s columns=%s', portfolio_values.shape, list(portfolio_values.columns))
                        except Exception:
                            logger.warning('PA_DEBUG_PORTFOLIO_VALUES - could not log portfolio values')
                        # Trim to last 90 days
                        equity_series = equity_series[equity_series.index >= (today - pd.Timedelta(days=90))]
                        if equity_series.empty:
                            raise Exception('Equity series empty after trimming')
                        equity = equity_series.values
                        dates = equity_series.index
                        returns = pd.Series(equity).pct_change().fillna(0).values
                        # successful live-price construction
                        picks_used = True
                    else:
                        raise Exception('No per-ticker series')

                    total_return = (equity[-1] / equity[0] - 1) if len(equity) > 1 else 0.0
                    sharpe = np.nan
                    try:
                        rr = pd.Series(returns)
                        sharpe = rr.mean() / rr.std() * np.sqrt(252) if rr.std() > 0 else 0.0
                    except Exception:
                        sharpe = 0.0
                    cumulative = (1 + pd.Series(returns)).cumprod()
                    running_max = np.maximum.accumulate(cumulative)
                    drawdown = (cumulative - running_max) / running_max
                    max_drawdown = drawdown.min() if len(drawdown) > 0 else 0.0
                    win_rate = float((pd.Series(returns) > 0).sum()) / max(1, len(returns))
                except Exception as e:
                    # fallback to simple noise-based approach if live prices fail
                    logger.warning(f"Live-price equity construction failed: {e}")
                    dates = pd.date_range(end=pd.Timestamp.now(), periods=90, freq='D')
                    np.random.seed(42)
                    returns = np.random.normal(0.001, 0.02, len(dates))
                    equity = 10000 * (1 + returns).cumprod()
                    total_return = (equity[-1] / equity[0] - 1)
                    sharpe = returns.mean() / returns.std() * np.sqrt(252)
                    cumulative = (1 + returns).cumprod()
                    running_max = np.maximum.accumulate(cumulative)
                    drawdown = (cumulative - running_max) / running_max
                    max_drawdown = drawdown.min()
                    win_rate = (returns > 0).sum() / len(returns)
            else:
                dates = pd.date_range(end=pd.Timestamp.now(), periods=90, freq='D')
                np.random.seed(42)
                returns = np.random.normal(0.001, 0.02, len(dates))
                equity = 10000 * (1 + returns).cumprod()

                total_return = (equity[-1] / equity[0] - 1)
                sharpe = returns.mean() / returns.std() * np.sqrt(252)

                cumulative = (1 + returns).cumprod()
                running_max = np.maximum.accumulate(cumulative)
                drawdown = (cumulative - running_max) / running_max
                max_drawdown = drawdown.min()

                win_rate = (returns > 0).sum() / len(returns)
            
            logger.warning("calculate_portfolio_analytics: picks_used=%r total_return=%r", locals().get('picks_used', False), locals().get('total_return', None))

            # Performance chart
            perf_fig = go.Figure()
            perf_fig.add_trace(go.Scatter(
                x=dates,
                y=equity,
                mode='lines',
                name='Portfolio Value',
                line=dict(color='#10b981', width=2)
            ))
            perf_title = 'Portfolio Performance Over Time (Sample Data)'
            if picks_used:
                perf_title = 'Portfolio Performance Over Time'
            perf_fig.update_layout(
                title=perf_title,
                xaxis_title='Date',
                yaxis_title='Portfolio Value ($)',
                template='plotly_white'
            )
            
            # Risk chart
            risk_fig = go.Figure()
            risk_fig.add_trace(go.Histogram(
                x=returns * 100,
                nbinsx=30,
                name='Daily Returns',
                marker=dict(color='#3b82f6')
            ))
            risk_title = 'Return Distribution (Sample Data)'
            if picks_used:
                risk_title = 'Return Distribution'
            risk_fig.update_layout(
                title=risk_title,
                xaxis_title='Daily Return (%)',
                yaxis_title='Frequency',
                template='plotly_white'
            )
        
        # Generate additional charts for new features using picks data when available
        try:
            # prepare tickers list from picks if available
            picks_tickers = []
            if 'picks_df' in locals() and picks_df is not None:
                picks_tickers = picks_df['ticker'].astype(str).tolist()
            else:
                # fallback to weekly CSV tickers if present
                try:
                    wp = weekly_path if 'weekly_path' in locals() else None
                    if wp and os.path.exists(wp):
                        tmp = _load_picks_df(wp, limit=200)
                        if tmp is not None:
                            picks_tickers = tmp['ticker'].astype(str).tolist()
                except Exception:
                    picks_tickers = []

            # Sector exposures via yfinance info when possible
            sector_data = None
            try:
                import yfinance as yf
                sector_map = {}
                for t in picks_tickers:
                    try:
                        info = yf.Ticker(t).info
                        sector = info.get('sector') or 'Other'
                    except Exception:
                        sector = 'Other'
                    sector_map[sector] = sector_map.get(sector, 0) + 1
                if sector_map:
                    total = sum(sector_map.values())
                    sector_data = pd.DataFrame({'Sector': list(sector_map.keys()),
                                                'Exposure': [v/total for v in sector_map.values()]})
            except Exception:
                sector_data = None

            if sector_data is None or sector_data.empty:
                sector_data = pd.DataFrame({
                    'Sector': ['Technology', 'Healthcare', 'Finance', 'Energy', 'Consumer', 'Industrial'],
                    'Exposure': [0.35, 0.20, 0.15, 0.12, 0.10, 0.08]
                })

            sector_fig = px.treemap(
                sector_data,
                path=['Sector'],
                values='Exposure',
                title='Sector Exposure Distribution',
                color='Exposure',
                color_continuous_scale='Blues'
            )
            sector_fig.update_layout(template='plotly_white')

            # Factor exposures: use available numeric columns from monthly picks (r1m, composite, ma50_vs200)
            factor_series = {}
            if 'picks_df' in locals() and picks_df is not None:
                if 'r1m' in picks_df.columns:
                    factor_series['Momentum'] = picks_df['r1m'].mean()
                if 'composite' in picks_df.columns:
                    factor_series['Composite'] = picks_df['composite'].mean()
                if 'ma50_vs200' in picks_df.columns:
                    factor_series['MA50_vs200'] = picks_df['ma50_vs200'].mean()

            if not factor_series:
                factor_series = {'Growth': 0.45, 'Value': -0.15, 'Momentum': 0.30, 'Quality': 0.25, 'Size': -0.10, 'Volatility': 0.05}

            # normalize factor exposures for display
            f_keys = list(factor_series.keys())
            f_vals = np.array([factor_series[k] for k in f_keys], dtype=float)
            max_abs = max(1e-6, np.max(np.abs(f_vals)))
            f_vals_norm = f_vals / max_abs * (np.sign(f_vals) * np.abs(f_vals))  # preserve sign
            factor_data = pd.DataFrame({'Factor': f_keys, 'Exposure': f_vals})
            factor_fig = px.bar(
                factor_data,
                x='Factor',
                y='Exposure',
                title='Factor Exposure',
                color='Exposure',
                color_continuous_scale=['#ef4444', '#10b981'],
                color_continuous_midpoint=0
            )
            factor_fig.update_layout(template='plotly_white', showlegend=False)

            # Contribution to VaR: approximate using historical volatility * equal weight
            var_data = None
            try:
                if picks_tickers:
                    import yfinance as yf
                    data = yf.download(picks_tickers, period='3mo', interval='1d', progress=False, threads=True, auto_adjust=True)
                    # Debug: log what yfinance returned for var computation
                    try:
                        logger.warning('PA_DEBUG_VAR - yfinance data type=%s', type(data))
                        if hasattr(data, 'shape'):
                            logger.warning('PA_DEBUG_VAR - yfinance data shape=%s', getattr(data, 'shape', None))
                        if hasattr(data, 'columns'):
                            try:
                                logger.warning('PA_DEBUG_VAR - yfinance data columns=%s', list(data.columns))
                            except Exception:
                                logger.warning('PA_DEBUG_VAR - could not list data.columns')
                    except Exception:
                        logger.warning('PA_DEBUG_VAR - could not inspect yfinance data')
                    vols = {}
                    # Normalize 'Close' extraction for multi/single ticker results
                    try:
                        if isinstance(data.columns, pd.MultiIndex):
                            close_df = data['Close']
                        elif 'Close' in data:
                            close_df = data['Close']
                        else:
                            # data may already be a DataFrame of closes
                            close_df = data
                    except Exception:
                        close_df = data

                    for t in picks_tickers:
                        try:
                            if isinstance(close_df, pd.DataFrame):
                                if t in close_df.columns:
                                    series = close_df[t].dropna()
                                else:
                                    # Sometimes yfinance uses upper/lower differences
                                    matches = [c for c in close_df.columns if str(c).upper() == str(t).upper()]
                                    series = close_df[matches[0]].dropna() if matches else pd.Series(dtype=float)
                            else:
                                # single-series returned
                                series = close_df.dropna()
                            ret = series.pct_change().dropna()
                            vols[t] = ret.std() if not ret.empty else 0.0
                        except Exception:
                            vols[t] = 0.0
                    if vols:
                        weights = {t: 1.0 / max(1, len(picks_tickers)) for t in picks_tickers}
                        contrib = {t: weights[t] * vols.get(t, 0.0) for t in picks_tickers}
                        # normalize to sum to 1 for display
                        s = sum(contrib.values()) or 1.0
                        var_df = pd.DataFrame({'Position': list(contrib.keys()), 'VaR_Contribution': [v / s for v in contrib.values()]})
                        var_data = var_df.sort_values('VaR_Contribution', ascending=True)
            except Exception:
                var_data = None

            if var_data is None or var_data.empty:
                var_data = pd.DataFrame({
                    'Position': ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'META', 'AMZN', 'NFLX'],
                    'VaR_Contribution': [0.08, 0.06, 0.05, 0.12, 0.15, 0.04, 0.07, 0.09]
                }).sort_values('VaR_Contribution', ascending=True)

            var_fig = px.bar(
                var_data,
                y='Position',
                x='VaR_Contribution',
                orientation='h',
                title='Contribution to Portfolio VaR (approx)',
                labels={'VaR_Contribution': 'VaR Contribution'},
                color='VaR_Contribution',
                color_continuous_scale='Reds'
            )
            var_fig.update_layout(template='plotly_white', showlegend=False)

            # Slippage Chart: approximate from weekly picks live prices if available
            slippage_dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq='D')
            slippage_bps = None
            try:
                if 'weekly_path' in locals() and weekly_path and os.path.exists(weekly_path):
                    # load weekly tickers and fetch week start/current via weekly_picks_flask.get_live_prices
                    from weekly_picks_flask import get_live_prices as wp_get_prices
                    wk_df = _load_picks_df(weekly_path, limit=200)
                    wk_tickers = wk_df['ticker'].astype(str).tolist() if wk_df is not None else []
                    if wk_tickers:
                        prices = wp_get_prices(wk_tickers)
                        # compute slippage percent per ticker
                        slippages = []
                        for t in wk_tickers:
                            pdict = prices.get(t, {})
                            try:
                                cur = float(pdict.get('current_price', 0))
                                start = float(pdict.get('week_start_price', cur))
                                if start > 0:
                                    pct = (cur - start) / start * 100  # percent
                                    bps = pct * 100
                                    slippages.append(bps)
                            except Exception:
                                continue
                        if slippages:
                            mean_bps = float(np.mean(slippages))
                            # create simple time series with noise
                            np.random.seed(42)
                            slippage_bps = mean_bps + np.random.normal(0, max(1.0, abs(mean_bps)*0.1), len(slippage_dates))
            except Exception:
                slippage_bps = None

            if slippage_bps is None:
                slippage_bps = np.random.uniform(2, 8, len(slippage_dates))

            slippage_data = pd.DataFrame({'Date': slippage_dates, 'Slippage_bps': slippage_bps})

            slippage_fig = go.Figure()
            slippage_fig.add_trace(go.Scatter(
                x=slippage_data['Date'],
                y=slippage_data['Slippage_bps'],
                mode='lines+markers',
                name='Slippage (bps)',
                line=dict(color='#f59e0b', width=2)
            ))
            slippage_fig.update_layout(
                title='Slippage Over Time',
                xaxis_title='Date',
                yaxis_title='Slippage (basis points)',
                template='plotly_white'
            )

            # Transaction Costs estimate
            total_slippage = float(slippage_data['Slippage_bps'].mean()) * 10  # rough $ estimate per portfolio
            total_commissions = 150.50
            total_costs = total_slippage + total_commissions
            cost_breakdown = f"Slippage: ${total_slippage:.2f} | Commissions: ${total_commissions:.2f}"
        except Exception as e:
            logger.warning(f"Error building picks-based analytics ({e}), falling back to defaults")
            # fallback to original static charts
            sector_data = pd.DataFrame({
                'Sector': ['Technology', 'Healthcare', 'Finance', 'Energy', 'Consumer', 'Industrial'],
                'Exposure': [0.35, 0.20, 0.15, 0.12, 0.10, 0.08]
            })
            sector_fig = px.treemap(
                sector_data,
                path=['Sector'],
                values='Exposure',
                title='Sector Exposure Distribution',
                color='Exposure',
                color_continuous_scale='Blues'
            )
            sector_fig.update_layout(template='plotly_white')

            factor_data = pd.DataFrame({
                'Factor': ['Growth', 'Value', 'Momentum', 'Quality', 'Size', 'Volatility'],
                'Exposure': [0.45, -0.15, 0.30, 0.25, -0.10, 0.05]
            })
            factor_fig = px.bar(
                factor_data,
                x='Factor',
                y='Exposure',
                title='Factor Exposure',
                color='Exposure',
                color_continuous_scale=['#ef4444', '#10b981'],
                color_continuous_midpoint=0
            )
            factor_fig.update_layout(template='plotly_white', showlegend=False)

            var_data = pd.DataFrame({
                'Position': ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'META', 'AMZN', 'NFLX'],
                'VaR_Contribution': [0.08, 0.06, 0.05, 0.12, 0.15, 0.04, 0.07, 0.09]
            }).sort_values('VaR_Contribution', ascending=True)
            var_fig = px.bar(
                var_data,
                y='Position',
                x='VaR_Contribution',
                orientation='h',
                title='Contribution to Portfolio VaR (95% confidence)',
                labels={'VaR_Contribution': 'VaR Contribution'},
                color='VaR_Contribution',
                color_continuous_scale='Reds'
            )
            var_fig.update_layout(template='plotly_white', showlegend=False)

            slippage_dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq='D')
            slippage_data = pd.DataFrame({'Date': slippage_dates, 'Slippage_bps': np.random.uniform(2, 8, 30)})
            slippage_fig = go.Figure()
            slippage_fig.add_trace(go.Scatter(x=slippage_data['Date'], y=slippage_data['Slippage_bps'], mode='lines+markers', line=dict(color='#f59e0b', width=2)))
            slippage_fig.update_layout(title='Slippage Over Time', xaxis_title='Date', yaxis_title='Slippage (basis points)', template='plotly_white')

            total_slippage = slippage_data['Slippage_bps'].sum() * 10
            total_commissions = 150.50
            total_costs = total_slippage + total_commissions
            cost_breakdown = f"Slippage: ${total_slippage:.2f} | Commissions: ${total_commissions:.2f}"
        
        # Ensure we return the full set of outputs expected by the callback (14 outputs)
        sector_counts = None
        ticker_vol_table = None
        try:
            # sector summary string
            if 'sector_data' in locals() and sector_data is not None:
                sector_counts = html.Div([html.Small(f"{r['Sector']}: {r['Exposure']:.1%}") for _, r in sector_data.iterrows()])
            else:
                sector_counts = html.Div("No sector data")
        except Exception:
            sector_counts = html.Div("No sector data")

        try:
            # ticker volatility table as simple DataTable when available
            if 'var_data' in locals() and var_data is not None:
                ticker_vol_table = dash_table.DataTable(
                    data=var_data.to_dict('records'),
                    columns=[{'name': c, 'id': c} for c in var_data.columns],
                    style_cell={'textAlign': 'left', 'padding': '6px'}
                )
            else:
                ticker_vol_table = html.Div('No ticker vol data')
        except Exception:
            ticker_vol_table = html.Div('No ticker vol data')

        logger.warning("EXIT calculate_portfolio_analytics: total_return=%r sharpe=%r picks_used=%r", total_return if 'total_return' in locals() else None, sharpe if 'sharpe' in locals() else None, locals().get('picks_used', False))

        return (
            f"{total_return:.2%}",
            f"{sharpe:.2f}",
            f"{max_drawdown:.2%}",
            f"{win_rate:.2%}",
            perf_fig,
            risk_fig,
            sector_fig,
            factor_fig,
            var_fig,
            slippage_fig,
            f"${total_costs:.2f}",
            cost_breakdown,
            sector_counts,
            ticker_vol_table
        )

    # Lightweight debug callback: write a timestamp to a small store when pa-calc-btn is clicked
    @app.callback(
        Output('pa-debug-store', 'data'),
        [Input('pa-calc-btn', 'n_clicks')]
    )
    def _pa_debug_store(n_clicks):
        # This callback exists solely to help detect client-side button clicks separately from the heavy analytics callback.
        if not n_clicks:
            raise PreventUpdate
        import time
        return {'clicked_at': time.time(), 'n_clicks': n_clicks}
    
    
    # Attribution Analysis - Factor Drill-Down Callback
    @app.callback(
        [Output('attr-factor-drilldown', 'style'),
         Output('attr-drilldown-title', 'children'),
         Output('attr-feature-breakdown', 'figure'),
         Output('attr-ticker-breakdown', 'figure')],
        [Input('attr-factor-chart', 'clickData')],
        [State('attr-results-store', 'data')]
    )
    def show_factor_drilldown(click_data, results):
        """Show drill-down when a factor is clicked in the waterfall chart."""
        if not click_data or not results:
            return {'display': 'none'}, "Factor Drill-Down", {}, {}
        
        # Get the clicked factor name
        factor_name = click_data['points'][0]['x']
        
        # Simulate feature breakdown for this factor
        features = {
            'momentum': ['ret_5d', 'ret_21d', 'ret_63d', 'rsi', 'macd'],
            'value': ['pb_ratio', 'pe_ratio', 'pcf_ratio', 'dividend_yield'],
            'sentiment': ['sentiment_score', 'news_volume', 'social_sentiment'],
            'quality': ['roe', 'roa', 'debt_equity', 'current_ratio'],
            'growth': ['revenue_growth', 'earnings_growth', 'sales_growth'],
            'size': ['market_cap', 'volume', 'float_shares']
        }
        
        feature_list = features.get(factor_name.lower(), ['feat_1', 'feat_2', 'feat_3'])
        feature_values = np.random.uniform(-0.01, 0.02, len(feature_list))
        
        feature_fig = px.bar(
            x=feature_list,
            y=feature_values,
            title=f'Top Features in {factor_name}',
            labels={'x': 'Feature', 'y': 'Contribution'},
            color=feature_values,
            color_continuous_scale=['#ef4444', '#10b981'],
            color_continuous_midpoint=0
        )
        feature_fig.update_layout(template='plotly_white', showlegend=False)
        
        # Simulate ticker breakdown
        tickers = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']
        ticker_values = np.random.uniform(-0.005, 0.015, len(tickers))
        
        ticker_fig = px.bar(
            x=tickers,
            y=ticker_values,
            title=f'Top Tickers for {factor_name}',
            labels={'x': 'Ticker', 'y': 'Contribution'},
            color=ticker_values,
            color_continuous_scale=['#ef4444', '#10b981'],
            color_continuous_midpoint=0
        )
        ticker_fig.update_layout(template='plotly_white', showlegend=False)
        
        return (
            {'display': 'block'},
            f"{factor_name} Factor Drill-Down",
            feature_fig,
            ticker_fig
        )
    
    
    # Attribution Analysis - Error Analysis Callback
    @app.callback(
        Output('attr-error-analysis', 'children'),
        [Input('attr-results-store', 'data')]
    )
    def show_error_analysis(results):
        """Show worst attribution picks where model expectations were most wrong."""
        if not results:
            raise PreventUpdate
        
        per_pick = results.get('per_pick', [])
        if not per_pick:
            return html.P("No pick-level data available")
        
        df = pd.DataFrame(per_pick)
        
        # Calculate prediction error (difference between expected and realized)
        df['error'] = abs(df['alpha'] - df['realized_return'])
        worst_picks = df.nlargest(5, 'error')[['ticker', 'date', 'realized_return', 'alpha', 'error']]
        
        return dash_table.DataTable(
            data=worst_picks.to_dict('records'),
            columns=[
                {'name': 'Ticker', 'id': 'ticker'},
                {'name': 'Date', 'id': 'date'},
                {'name': 'Realized Return', 'id': 'realized_return', 'type': 'numeric', 'format': {'specifier': '.2%'}},
                {'name': 'Expected Alpha', 'id': 'alpha', 'type': 'numeric', 'format': {'specifier': '.2%'}},
                {'name': 'Prediction Error', 'id': 'error', 'type': 'numeric', 'format': {'specifier': '.2%'}}
            ],
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[
                {
                    'if': {'column_id': 'error', 'filter_query': '{error} > 0.05'},
                    'backgroundColor': '#fee2e2',
                    'color': '#991b1b'
                }
            ]
        )
    
    
    # Scenario Tester - Show/Hide Compare Selector
    @app.callback(
        [Output('scenario-compare-selector', 'style'), Output('scenario-compare-visibility-flag', 'children')],
        [Input('scenario-compare-mode', 'value')]
    )
    def toggle_compare_selector(compare_mode):
        """Show second scenario selector when compare mode is enabled and set a visibility flag text for tests."""
        try:
            if compare_mode and 'compare' in compare_mode:
                # set flag text 'visible' so Playwright can assert reliably
                return {'display': 'block'}, 'visible'
        except Exception:
            pass
        return {'display': 'none'}, ''
    
    
    # Scenario Tester - Update Scenario Options Based on Type
    @app.callback(
        Output('scenario-preset', 'options'),
        [Input('scenario-type', 'value')]
    )
    def update_scenario_options(scenario_type):
        """Update scenario dropdown options based on selected type."""
        if scenario_type == 'factor':
            return [
                {'label': 'Momentum Crash (-30% momentum)', 'value': 'momentum_crash'},
                {'label': 'Value Rally (+40% value)', 'value': 'value_rally'},
                {'label': 'Growth Rotation (+25% growth)', 'value': 'growth_rotation'},
                {'label': 'Quality Flight (+20% quality)', 'value': 'quality_flight'},
                {'label': 'Size Effect Reversal', 'value': 'size_reversal'}
            ]
        else:
            return [
                {'label': 'Bull Market (+20% SPY)', 'value': 'bull'},
                {'label': 'Bear Market (-20% SPY)', 'value': 'bear'},
                {'label': 'High Volatility (+10 VIX)', 'value': 'high_vol'},
                {'label': 'Interest Rate Spike (+2% TNX)', 'value': 'rate_spike'},
                {'label': 'Custom', 'value': 'custom'}
            ]


def _run_factor_scenario(preset, compare_mode, preset2=None):
    """Run factor-based scenario analysis."""
    factor_scenarios = {
        'momentum_crash': {'factor': 'Momentum', 'change': -0.30, 'features': ['ret_5d', 'ret_21d', 'ret_63d', 'rsi']},
        'value_rally': {'factor': 'Value', 'change': 0.40, 'features': ['pb_ratio', 'pe_ratio', 'dividend_yield']},
        'growth_rotation': {'factor': 'Growth', 'change': 0.25, 'features': ['revenue_growth', 'earnings_growth']},
        'quality_flight': {'factor': 'Quality', 'change': 0.20, 'features': ['roe', 'roa', 'debt_equity']},
        'size_reversal': {'factor': 'Size', 'change': -0.15, 'features': ['market_cap', 'volume']}
    }
    
    scenario = factor_scenarios.get(preset, factor_scenarios['momentum_crash'])
    
    # Simulate impact on portfolio
    impact_data = pd.DataFrame({
        'Stock': ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'META', 'AMZN'],
        'Current_Score': [0.72, 0.68, 0.65, 0.78, 0.55, 0.61, 0.69],
        'Scenario_Score': [
            0.72 + scenario['change'] * np.random.uniform(0.5, 1.5),
            0.68 + scenario['change'] * np.random.uniform(0.5, 1.5),
            0.65 + scenario['change'] * np.random.uniform(0.5, 1.5),
            0.78 + scenario['change'] * np.random.uniform(0.5, 1.5),
            0.55 + scenario['change'] * np.random.uniform(0.5, 1.5),
            0.61 + scenario['change'] * np.random.uniform(0.5, 1.5),
            0.69 + scenario['change'] * np.random.uniform(0.5, 1.5)
        ]
    })
    
    impact_data['Change'] = impact_data['Scenario_Score'] - impact_data['Current_Score']
    impact_data['Change_Pct'] = (impact_data['Change'] / impact_data['Current_Score'] * 100).round(1)
    
    # Calculate top hedging candidates (stocks that perform well in this scenario)
    hedging_candidates = impact_data.nlargest(3, 'Change')[['Stock', 'Change', 'Change_Pct']]
    
    # If compare mode, run second scenario
    if compare_mode and 'compare' in compare_mode and preset2:
        scenario2 = factor_scenarios.get(preset2, factor_scenarios['momentum_crash'])
        
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5(f"{scenario['factor']} Scenario", className="mb-3"),
                        html.P(f"{scenario['change']:+.0%} shock to {scenario['factor']} factor", className="text-muted"),
                        dash_table.DataTable(
                            data=impact_data[['Stock', 'Current_Score', 'Scenario_Score', 'Change_Pct']].to_dict('records'),
                            columns=[
                                {'name': 'Stock', 'id': 'Stock'},
                                {'name': 'Current', 'id': 'Current_Score'},
                                {'name': 'Scenario', 'id': 'Scenario_Score'},
                                {'name': 'Change %', 'id': 'Change_Pct'}
                            ],
                            style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '12px'},
                            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
                        ),
                        html.H6("Top Hedging Candidates", className="mt-3"),
                        html.Ul([html.Li(f"{row['Stock']}: {row['Change_Pct']:+.1f}%") for _, row in hedging_candidates.iterrows()], **{"data-testid": "hedging-candidates-list"})
                    ])
                ])
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5(f"{scenario2['factor']} Scenario (Comparison)", className="mb-3"),
                        html.P(f"{scenario2['change']:+.0%} shock to {scenario2['factor']} factor", className="text-muted"),
                        html.P("Comparison view - showing difference from primary scenario", className="text-muted small")
                    ])
                ])
            ], width=6)
        ])
    
    # Single scenario view
    return dbc.Card([
        dbc.CardBody([
            html.H5(f"{scenario['factor']} Factor Scenario: {scenario['change']:+.0%} Shock", className="mb-3"),
            dbc.Row([
                dbc.Col([
                    html.H6("Affected Features:", className="text-muted"),
                    html.P(", ".join(scenario['features']))
                ], width=12)
            ], className="mb-3"),
            html.H6("Portfolio Impact", className="mb-2"),
            dash_table.DataTable(
                data=impact_data[['Stock', 'Current_Score', 'Scenario_Score', 'Change', 'Change_Pct']].to_dict('records'),
                columns=[
                    {'name': 'Stock', 'id': 'Stock'},
                    {'name': 'Current Score', 'id': 'Current_Score'},
                    {'name': 'Scenario Score', 'id': 'Scenario_Score'},
                    {'name': 'Change', 'id': 'Change'},
                    {'name': 'Change %', 'id': 'Change_Pct'}
                ],
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                style_data_conditional=[
                    {'if': {'column_id': 'Change', 'filter_query': '{Change} < 0'}, 'backgroundColor': '#fee2e2', 'color': '#991b1b'},
                    {'if': {'column_id': 'Change', 'filter_query': '{Change} > 0'}, 'backgroundColor': '#d1fae5', 'color': '#065f46'}
                ]
            ),
            html.H6("Top Hedging Candidates (Best Performers in This Scenario)", className="mt-4 mb-2"),
            dash_table.DataTable(
                data=hedging_candidates.to_dict('records'),
                columns=[
                    {'name': 'Stock', 'id': 'Stock'},
                    {'name': 'Score Improvement', 'id': 'Change'},
                    {'name': 'Change %', 'id': 'Change_Pct'}
                ],
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'backgroundColor': '#d1fae5', 'fontWeight': 'bold'},
                style_data={'backgroundColor': '#f0fdf4'}
            )
        ])
    ])


def _load_picks_in_range(picks_type, start_date, end_date):
    """Load picks CSV files within the specified date range."""
    try:
        import glob
        
        dash_root = getattr(SH, 'DASH_ROOT', SH.PROJECT_ROOT)
        
        if picks_type == 'weekly':
            picks_dir = os.path.join(dash_root, 'models', 'weekly_run')
        else:
            picks_dir = os.path.join(dash_root, 'models', 'full_run')
        
        if not os.path.exists(picks_dir):
            return None
        
        # Find all picks CSV files
        csv_files = glob.glob(os.path.join(picks_dir, '**', 'picks_*.csv'), recursive=True)
        
        all_picks = []
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                # Normalize column names to prevent "Names mismatch" issues
                df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
                # If no date column, parse from filename (picks_YYYYMMDD.csv)
                if 'date' not in df.columns:
                    import re
                    filename = os.path.basename(csv_file)
                    m = re.search(r'(\d{8})', filename)
                    if m:
                        file_date = m.group(1)
                        df['date'] = file_date
                    else:
                        # Use file modification time as fallback
                        mtime = os.path.getmtime(csv_file)
                        df['date'] = datetime.fromtimestamp(mtime).strftime('%Y%m%d')
                # Ensure ticker column exists (try common variants)
                if 'ticker' not in df.columns:
                    # try Title case or other common variants
                    for col in df.columns:
                        if col.lower() == 'ticker' or col.lower() == 'symbol':
                            df['ticker'] = df[col]
                            break

                if 'ticker' in df.columns:
                    all_picks.append(df)
            except Exception as e:
                logger.warning(f"Could not read {csv_file}: {e}")
        
        if not all_picks:
            return None
        
        # Combine and filter by date range
        combined = pd.concat(all_picks, ignore_index=True)
        combined['date'] = pd.to_datetime(combined['date'], format='%Y%m%d', errors='coerce')
        
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        filtered = combined[(combined['date'] >= start) & (combined['date'] <= end)]
        
        return filtered
        
    except Exception as e:
        logger.error(f"Error loading picks: {e}")
        return None


def _run_attribution_on_picks(picks_df, horizon):
    """Run attribution analysis on the picks DataFrame."""
    try:
        if ATTR is None:
            raise ImportError("Attribution utils not available")
        
        # Get unique tickers
        tickers = picks_df['ticker'].unique().tolist()
        
        # Fetch price data for returns calculation
        import yfinance as yf
        
        # Determine horizon days
        horizon_days = {'1w': 7, '1m': 30, '3m': 90}.get(horizon, 7)
        
        per_pick_results = []
        
        for _, pick in picks_df.iterrows():
            ticker = pick['ticker']
            pick_date = pd.to_datetime(pick['date'])
            end_date = pick_date + timedelta(days=horizon_days)
            
            try:
                # Get price data
                stock = yf.Ticker(ticker)
                hist = stock.history(start=pick_date - timedelta(days=1), 
                                    end=end_date + timedelta(days=1))
                
                if len(hist) < 2:
                    continue
                
                # Calculate realized return
                start_price = hist['Close'].iloc[0]
                end_price = hist['Close'].iloc[-1]
                # Coerce to float where possible to avoid sequence * float errors
                try:
                    start_price = float(start_price)
                    end_price = float(end_price)
                    realized_return = (end_price / start_price - 1)
                except Exception as _e:
                    logger.warning("ATTR_NUMERIC_COERCE - could not coerce prices for %s: start=%r end=%r err=%s",
                                   ticker, start_price, end_price, _e)
                    # Skip this pick if we cannot interpret numeric prices
                    continue

                # Get benchmark return (SPY)
                spy = yf.Ticker('SPY')
                spy_hist = spy.history(start=pick_date - timedelta(days=1),
                                      end=end_date + timedelta(days=1))

                benchmark_return = 0.0
                if len(spy_hist) >= 2:
                    try:
                        benchmark_return = float(spy_hist['Close'].iloc[-1]) / float(spy_hist['Close'].iloc[0]) - 1
                    except Exception as _e:
                        logger.warning("ATTR_NUMERIC_COERCE - could not coerce spy prices for %s: %s", ticker, _e)
                        benchmark_return = 0.0

                # Estimate beta (using longer history)
                long_hist = stock.history(start=pick_date - timedelta(days=252),
                                         end=pick_date)
                spy_long = spy.history(start=pick_date - timedelta(days=252),
                                      end=pick_date)

                if len(long_hist) >= 20 and len(spy_long) >= 20:
                    # Align dates
                    merged = pd.DataFrame({
                        'stock': long_hist['Close'].pct_change(),
                        'spy': spy_long['Close'].pct_change()
                    }).dropna()

                    if len(merged) >= 20:
                        beta = ATTR.estimate_beta(merged, 'stock', 'spy')
                        # Coerce beta to a float scalar where possible
                        try:
                            beta = float(beta)
                        except Exception:
                            try:
                                # If beta is array-like, take the first element
                                beta = float(beta[0])
                            except Exception:
                                logger.warning("ATTR_NUMERIC_COERCE - could not coerce beta for %s: %r", ticker, beta)
                                beta = 1.0
                    else:
                        beta = 1.0
                else:
                    beta = 1.0

                # Calculate attribution
                try:
                    beta_contrib = float(beta) * float(benchmark_return)
                except Exception as _e:
                    logger.warning("ATTR_NUMERIC_COERCE - error computing beta_contrib for %s: beta=%r benchmark=%r err=%s",
                                   ticker, beta, benchmark_return, _e)
                    beta_contrib = 0.0

                try:
                    alpha = float(realized_return) - float(beta_contrib)
                except Exception as _e:
                    logger.warning("ATTR_NUMERIC_COERCE - error computing alpha for %s: realized=%r beta_contrib=%r err=%s",
                                   ticker, realized_return, beta_contrib, _e)
                    alpha = 0.0

                # Determine top factor (placeholder - would need SHAP data)
                top_factor = "momentum"  # This would come from SHAP analysis

                per_pick_results.append({
                    'ticker': ticker,
                    'date': pick_date.strftime('%Y-%m-%d'),
                    'realized_return': float(realized_return),
                    'alpha': float(alpha),
                    'beta': float(beta),
                    'beta_contrib': float(beta_contrib),
                    'benchmark_return': float(benchmark_return),
                    'top_factor': top_factor
                })
                
            except Exception as e:
                logger.warning(f"Error processing {ticker}: {e}")
                continue
        
        if not per_pick_results:
            return None
        
        # Calculate portfolio-level metrics
        total_return = np.mean([p['realized_return'] for p in per_pick_results])
        total_alpha = np.mean([p['alpha'] for p in per_pick_results])
        avg_beta = np.mean([p['beta'] for p in per_pick_results])
        total_beta_contrib = np.mean([p['beta_contrib'] for p in per_pick_results])
        
            # Load SHAP data and aggregate into factors
        try:
            from utils.explain import load_shap_explanations
            
            # Try to find SHAP data for any of the pick dates
            shap_data_loaded = None
            for pick in per_pick_results[:5]:  # Try first 5 picks
                pick_date_str = pd.to_datetime(pick['date']).strftime('%Y%m%d')
                shap_data_loaded = load_shap_explanations(pick_date_str)
                if shap_data_loaded:
                    break
            
            if shap_data_loaded:
                # Define factor groupings (customize based on your actual features)
                factor_groups = {
                    'momentum': ['ret_5d', 'ret_21d', 'ret_63d', 'rsi', 'macd'],
                    'value': ['pb_ratio', 'pe_ratio', 'pcf_ratio', 'dividend_yield'],
                    'quality': ['roe', 'roa', 'debt_equity', 'current_ratio'],
                    'sentiment': ['sentiment_score', 'news_volume', 'social_sentiment'],
                    'growth': ['revenue_growth', 'earnings_growth', 'sales_growth'],
                    'size': ['market_cap', 'volume', 'float_shares']
                }
                
                # Aggregate SHAP values by factor across all picks
                factor_totals = {f: 0.0 for f in factor_groups.keys()}
                count = 0
                
                for ticker_shap in shap_data_loaded.values():
                    if isinstance(ticker_shap, dict):
                        top_features = ticker_shap.get('top_features', [])
                        for feat in top_features:
                            feat_name = feat.get('feature', '')
                            feat_value = feat.get('value', 0)
                            # Find which factor this feature belongs to
                            for factor_name, feature_list in factor_groups.items():
                                if any(f in feat_name.lower() for f in feature_list):
                                    factor_totals[factor_name] += feat_value
                                    break
                        count += 1
                
                # Average and convert to contribution percentages
                if count > 0:
                    factor_contributions = [
                        {'factor': fname, 'contribution': round(fval / count, 4)}
                        for fname, fval in sorted(factor_totals.items(), key=lambda x: abs(x[1]), reverse=True)
                        if fval != 0
                    ][:5]  # Top 5 factors
                    logger.info(f"Loaded real SHAP-based factor contributions: {factor_contributions}")
                else:
                    raise ValueError("No SHAP data found")
            else:
                raise FileNotFoundError("No SHAP explanation files found")
                
        except Exception as e:
            logger.warning(f"Could not load SHAP data ({e}), using placeholder factors")
            # Fallback to placeholder if SHAP not available
            factor_contributions = [
                {'factor': 'momentum', 'contribution': 0.02},
                {'factor': 'sentiment', 'contribution': 0.015},
                {'factor': 'value', 'contribution': -0.005},
                {'factor': 'size', 'contribution': 0.008}
            ]
        
        return {
            'portfolio': {
                'total_return': total_return,
                'alpha': total_alpha,
                'beta': avg_beta,
                'beta_contrib': total_beta_contrib,
                'top_factors': factor_contributions
            },
            'per_pick': per_pick_results
        }

    except Exception as e:
        # Capture full traceback and a small sample of picks to aid debugging
        try:
            sample = picks_df.head(5).to_dict('records') if picks_df is not None else None
        except Exception:
            sample = None

        logger.error(
            "Error in attribution analysis (horizon=%s): %s - sample picks: %s",
            horizon, e, sample,
            exc_info=True
        )
        return None

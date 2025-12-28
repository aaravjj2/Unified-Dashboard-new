"""
Alpha Sim Console - Interactive AlphaVantage API Recreation
============================================================
Complete recreation of AlphaVantage's API capabilities including:
- Time Series (Daily, Intraday, Weekly, Monthly)
- Technical Indicators (50+ indicators)
- Fundamental Data (Company Overview, Earnings, Financials)
- Alpha Intelligence (News Sentiment, Insider Transactions)
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, ALL
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .engine import get_engine, AlphaSimEngine
from .indicators import macd  # Basic indicators
from .indicators_extended import (
    AVAILABLE_INDICATORS, get_indicator_categories,
    sma, ema, rsi, bbands, stoch, adx, atr, obv
)

logger = logging.getLogger(__name__)


# ==============================================================================
# COMPONENT IDS
# ==============================================================================

COMPONENT_IDS = {
    'ticker_input': 'alpha-sim-ticker-input',
    'function_dropdown': 'alpha-sim-function-dropdown',
    'interval_dropdown': 'alpha-sim-interval-dropdown',
    'outputsize_toggle': 'alpha-sim-outputsize-toggle',
    'indicator_dropdown': 'alpha-sim-indicator-dropdown',
    'period_input': 'alpha-sim-period-input',
    'execute_button': 'alpha-sim-execute-btn',
    'output_tabs': 'alpha-sim-output-tabs',
    'chart_output': 'alpha-sim-chart-output',
    'json_output': 'alpha-sim-json-output',
    'table_output': 'alpha-sim-table-output',
    'api_log': 'alpha-sim-api-log',
    'api_url_display': 'alpha-sim-api-url',
    'status_badge': 'alpha-sim-status-badge',
    'store': 'alpha-sim-store',
}


# ==============================================================================
# API FUNCTIONS MAPPING
# ==============================================================================

API_FUNCTIONS = {
    'Time Series': {
        'TIME_SERIES_DAILY': 'Daily time series (open, high, low, close, volume)',
        'TIME_SERIES_DAILY_ADJUSTED': 'Daily adjusted (includes dividends/splits)',
        'TIME_SERIES_INTRADAY': 'Intraday data (1min, 5min, 15min, 30min, 60min)',
        'TIME_SERIES_WEEKLY': 'Weekly time series',
        'TIME_SERIES_MONTHLY': 'Monthly time series',
        'GLOBAL_QUOTE': 'Real-time quote snapshot',
    },
    'Technical Indicators': {
        'SMA': 'Simple Moving Average',
        'EMA': 'Exponential Moving Average',
        'WMA': 'Weighted Moving Average',
        'DEMA': 'Double EMA',
        'TEMA': 'Triple EMA',
        'RSI': 'Relative Strength Index',
        'MACD': 'Moving Average Convergence/Divergence',
        'STOCH': 'Stochastic Oscillator',
        'ADX': 'Average Directional Index',
        'CCI': 'Commodity Channel Index',
        'AROON': 'Aroon Indicator',
        'BBANDS': 'Bollinger Bands',
        'ATR': 'Average True Range',
        'OBV': 'On Balance Volume',
        'AD': 'Chaikin A/D Line',
    },
    'Fundamental Data': {
        'OVERVIEW': 'Company overview and key metrics',
        'INCOME_STATEMENT': 'Income statement (annual/quarterly)',
        'BALANCE_SHEET': 'Balance sheet (annual/quarterly)',
        'CASH_FLOW': 'Cash flow statement',
        'EARNINGS': 'Earnings reports and estimates',
        'EARNINGS_CALENDAR': 'Upcoming earnings dates',
    },
    'Alpha Intelligence': {
        'NEWS_SENTIMENT': 'News and sentiment analysis',
        'INSIDER_TRANSACTIONS': 'Insider trading data',
        'ANALYST_RECOMMENDATIONS': 'Analyst ratings',
        'MARKET_MOVERS': 'Top gainers/losers',
    },
}


# ==============================================================================
# LAYOUT
# ==============================================================================

def create_alpha_sim_console_layout() -> html.Div:
    """Create the Alpha Sim Console layout."""
    
    # Build function options
    function_options = []
    for category, funcs in API_FUNCTIONS.items():
        for func_name, description in funcs.items():
            function_options.append({
                'label': f"{func_name} - {description}",
                'value': func_name,
            })
    
    # Build indicator options
    indicator_options = []
    for category, indicators in get_indicator_categories().items():
        for ind in indicators:
            indicator_options.append({
                'label': f"{ind} ({category})",
                'value': ind,
            })
    
    return html.Div([
        # Header
        dbc.Row([
            dbc.Col([
                html.H4([
                    html.I(className="fas fa-code me-2"),
                    "Alpha Sim Console"
                ], className="mb-0"),
                html.Small("AlphaVantage-Compatible API Recreation", className="text-muted"),
            ], width=8),
            dbc.Col([
                dbc.Badge(
                    "Ready",
                    id=COMPONENT_IDS['status_badge'],
                    color="success",
                    className="float-end"
                ),
            ], width=4),
        ], className="mb-4"),
        
        # API Builder Section
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-terminal me-2"),
                "API Request Builder"
            ]),
            dbc.CardBody([
                dbc.Row([
                    # Function Selection
                    dbc.Col([
                        dbc.Label("Function", className="fw-bold"),
                        dcc.Dropdown(
                            id=COMPONENT_IDS['function_dropdown'],
                            options=function_options,
                            value='TIME_SERIES_DAILY',
                            placeholder="Select API function...",
                            className="mb-2",
                        ),
                    ], width=6),
                    
                    # Symbol Input
                    dbc.Col([
                        dbc.Label("Symbol", className="fw-bold"),
                        dbc.Input(
                            id=COMPONENT_IDS['ticker_input'],
                            type="text",
                            value="AAPL",
                            placeholder="Enter ticker symbol...",
                            className="mb-2",
                        ),
                    ], width=3),
                    
                    # Interval (for intraday)
                    dbc.Col([
                        dbc.Label("Interval", className="fw-bold"),
                        dcc.Dropdown(
                            id=COMPONENT_IDS['interval_dropdown'],
                            options=[
                                {'label': '1 Minute', 'value': '1min'},
                                {'label': '5 Minutes', 'value': '5min'},
                                {'label': '15 Minutes', 'value': '15min'},
                                {'label': '30 Minutes', 'value': '30min'},
                                {'label': '60 Minutes', 'value': '60min'},
                            ],
                            value='5min',
                            disabled=True,
                            className="mb-2",
                        ),
                    ], width=3),
                ], className="mb-3"),
                
                dbc.Row([
                    # Technical Indicator Period
                    dbc.Col([
                        dbc.Label("Period", className="fw-bold"),
                        dbc.Input(
                            id=COMPONENT_IDS['period_input'],
                            type="number",
                            value=14,
                            min=1,
                            max=500,
                            className="mb-2",
                        ),
                    ], width=2),
                    
                    # Output Size
                    dbc.Col([
                        dbc.Label("Output Size", className="fw-bold"),
                        dbc.RadioItems(
                            id=COMPONENT_IDS['outputsize_toggle'],
                            options=[
                                {'label': 'Compact (100)', 'value': 'compact'},
                                {'label': 'Full', 'value': 'full'},
                            ],
                            value='compact',
                            inline=True,
                            className="mb-2",
                        ),
                    ], width=4),
                    
                    # Execute Button
                    dbc.Col([
                        html.Br(),
                        dbc.Button([
                            html.I(className="fas fa-play me-2"),
                            "Execute"
                        ], id=COMPONENT_IDS['execute_button'], color="primary", className="w-100"),
                    ], width=3),
                    
                    # Additional Indicator
                    dbc.Col([
                        dbc.Label("Overlay Indicator", className="fw-bold"),
                        dcc.Dropdown(
                            id=COMPONENT_IDS['indicator_dropdown'],
                            options=indicator_options,
                            value=None,
                            placeholder="Add indicator overlay...",
                            className="mb-2",
                        ),
                    ], width=3),
                ]),
                
                # API URL Display
                dbc.Row([
                    dbc.Col([
                        html.Pre(
                            id=COMPONENT_IDS['api_url_display'],
                            className="bg-dark text-success p-2 rounded small mb-0",
                            style={'fontFamily': 'monospace'},
                        ),
                    ]),
                ], className="mt-3"),
            ]),
        ], className="mb-4"),
        
        # Output Section
        dbc.Card([
            dbc.CardHeader([
                dbc.Tabs([
                    dbc.Tab(label="Chart", tab_id="chart"),
                    dbc.Tab(label="JSON Response", tab_id="json"),
                    dbc.Tab(label="Data Table", tab_id="table"),
                    dbc.Tab(label="API Log", tab_id="log"),
                ], id=COMPONENT_IDS['output_tabs'], active_tab="chart"),
            ]),
            dbc.CardBody([
                # Chart Output
                html.Div(
                    id=COMPONENT_IDS['chart_output'],
                    style={'minHeight': '400px'},
                ),
                # JSON Output (hidden by default)
                html.Div(
                    id=COMPONENT_IDS['json_output'],
                    style={'display': 'none', 'maxHeight': '500px', 'overflow': 'auto'},
                ),
                # Table Output (hidden by default)
                html.Div(
                    id=COMPONENT_IDS['table_output'],
                    style={'display': 'none', 'maxHeight': '500px', 'overflow': 'auto'},
                ),
                # API Log (hidden by default)
                html.Div(
                    id=COMPONENT_IDS['api_log'],
                    style={'display': 'none'},
                ),
            ]),
        ]),
        
        # Store for data
        dcc.Store(id=COMPONENT_IDS['store'], data={}),
        
        # Quick Reference
        dbc.Accordion([
            dbc.AccordionItem([
                _create_api_reference(),
            ], title="📖 AlphaVantage API Reference"),
        ], className="mt-4", start_collapsed=True),
        
    ], className="p-3")


def _create_api_reference() -> html.Div:
    """Create API reference documentation."""
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H6("Time Series Functions", className="text-primary"),
                html.Ul([
                    html.Li([html.Code("TIME_SERIES_DAILY"), " - Daily OHLCV data"]),
                    html.Li([html.Code("TIME_SERIES_INTRADAY"), " - Intraday (1/5/15/30/60min)"]),
                    html.Li([html.Code("TIME_SERIES_WEEKLY"), " - Weekly aggregated"]),
                    html.Li([html.Code("TIME_SERIES_MONTHLY"), " - Monthly aggregated"]),
                    html.Li([html.Code("GLOBAL_QUOTE"), " - Real-time snapshot"]),
                ]),
            ], width=4),
            dbc.Col([
                html.H6("Technical Indicators", className="text-success"),
                html.Ul([
                    html.Li([html.Code("SMA, EMA, WMA"), " - Moving averages"]),
                    html.Li([html.Code("RSI, STOCH, CCI"), " - Momentum"]),
                    html.Li([html.Code("MACD, ADX, AROON"), " - Trend"]),
                    html.Li([html.Code("BBANDS, ATR"), " - Volatility"]),
                    html.Li([html.Code("OBV, AD, ADOSC"), " - Volume"]),
                ]),
            ], width=4),
            dbc.Col([
                html.H6("Fundamental Data", className="text-warning"),
                html.Ul([
                    html.Li([html.Code("OVERVIEW"), " - Company profile"]),
                    html.Li([html.Code("INCOME_STATEMENT"), " - P&L"]),
                    html.Li([html.Code("BALANCE_SHEET"), " - Assets/Liabilities"]),
                    html.Li([html.Code("EARNINGS"), " - EPS reports"]),
                    html.Li([html.Code("NEWS_SENTIMENT"), " - News analysis"]),
                ]),
            ], width=4),
        ]),
    ])


# ==============================================================================
# DATA FETCHING & PROCESSING
# ==============================================================================

class AlphaSimConsole:
    """Console for executing AlphaVantage-compatible API calls."""
    
    def __init__(self):
        self.engine = get_engine()
        self.api_log: List[Dict] = []
    
    def execute(
        self,
        function: str,
        symbol: str,
        interval: str = '5min',
        outputsize: str = 'compact',
        period: int = 14,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute an API function and return results."""
        
        start_time = datetime.now()
        result = {'success': False, 'data': None, 'error': None}
        
        try:
            # Time Series functions
            if function == 'TIME_SERIES_DAILY':
                result['data'] = self.engine.time_series_daily(symbol, outputsize)
                result['success'] = True
                
            elif function == 'TIME_SERIES_DAILY_ADJUSTED':
                data = self.engine.time_series_daily(symbol, outputsize)
                # Add adjusted close (same as close for now)
                data['Meta Data']['1. Information'] = 'Daily Adjusted (AlphaSim)'
                result['data'] = data
                result['success'] = True
                
            elif function == 'TIME_SERIES_INTRADAY':
                result['data'] = self.engine.time_series_intraday(symbol, interval, outputsize)
                result['success'] = True
                
            elif function == 'TIME_SERIES_WEEKLY':
                result['data'] = self._get_weekly_series(symbol)
                result['success'] = True
                
            elif function == 'TIME_SERIES_MONTHLY':
                result['data'] = self._get_monthly_series(symbol)
                result['success'] = True
                
            elif function == 'GLOBAL_QUOTE':
                result['data'] = self._get_global_quote(symbol)
                result['success'] = True
            
            # Technical Indicators
            elif function in AVAILABLE_INDICATORS:
                result['data'] = self._calculate_indicator(function, symbol, period)
                result['success'] = True
                
            elif function == 'MACD':
                result['data'] = self._calculate_macd(symbol)
                result['success'] = True
            
            # Fundamental Data
            elif function == 'OVERVIEW':
                result['data'] = self._get_company_overview(symbol)
                result['success'] = True
                
            elif function in ['INCOME_STATEMENT', 'BALANCE_SHEET', 'CASH_FLOW']:
                result['data'] = self._get_financial_statement(symbol, function)
                result['success'] = True
                
            elif function == 'EARNINGS':
                result['data'] = self._get_earnings(symbol)
                result['success'] = True
                
            elif function == 'EARNINGS_CALENDAR':
                result['data'] = self._get_earnings_calendar(symbol)
                result['success'] = True
            
            # Alpha Intelligence
            elif function == 'NEWS_SENTIMENT':
                result['data'] = self._get_news_sentiment(symbol)
                result['success'] = True
                
            elif function == 'INSIDER_TRANSACTIONS':
                result['data'] = self._get_insider_transactions(symbol)
                result['success'] = True
                
            elif function == 'ANALYST_RECOMMENDATIONS':
                result['data'] = self._get_analyst_recommendations(symbol)
                result['success'] = True
                
            elif function == 'MARKET_MOVERS':
                result['data'] = self._get_market_movers()
                result['success'] = True
                
            else:
                result['error'] = f"Unknown function: {function}"
                
        except Exception as e:
            logger.error(f"Alpha Sim Console error: {e}")
            result['error'] = str(e)
        
        # Log the request
        elapsed = (datetime.now() - start_time).total_seconds()
        self.api_log.append({
            'timestamp': start_time.isoformat(),
            'function': function,
            'symbol': symbol,
            'success': result['success'],
            'elapsed_ms': round(elapsed * 1000, 2),
            'error': result.get('error'),
        })
        
        return result
    
    def _get_weekly_series(self, symbol: str) -> Dict:
        """Get weekly time series."""
        daily = self.engine.time_series_daily(symbol, 'full')
        if 'Time Series (Daily)' not in daily:
            return daily
        
        # Resample to weekly
        ts = daily['Time Series (Daily)']
        df = pd.DataFrame.from_dict(ts, orient='index')
        df.index = pd.to_datetime(df.index)
        df = df.astype(float)
        
        weekly = df.resample('W').agg({
            '1. open': 'first',
            '2. high': 'max',
            '3. low': 'min',
            '4. close': 'last',
            '5. volume': 'sum'
        })
        
        result = {}
        for idx, row in weekly.dropna().iterrows():
            result[idx.strftime('%Y-%m-%d')] = {
                '1. open': f"{row['1. open']:.4f}",
                '2. high': f"{row['2. high']:.4f}",
                '3. low': f"{row['3. low']:.4f}",
                '4. close': f"{row['4. close']:.4f}",
                '5. volume': f"{int(row['5. volume'])}"
            }
        
        return {
            'Meta Data': {
                '1. Information': 'Weekly Time Series (AlphaSim)',
                '2. Symbol': symbol,
                '3. Last Refreshed': datetime.now().strftime('%Y-%m-%d'),
            },
            'Weekly Time Series': result
        }
    
    def _get_monthly_series(self, symbol: str) -> Dict:
        """Get monthly time series."""
        daily = self.engine.time_series_daily(symbol, 'full')
        if 'Time Series (Daily)' not in daily:
            return daily
        
        ts = daily['Time Series (Daily)']
        df = pd.DataFrame.from_dict(ts, orient='index')
        df.index = pd.to_datetime(df.index)
        df = df.astype(float)
        
        monthly = df.resample('ME').agg({
            '1. open': 'first',
            '2. high': 'max',
            '3. low': 'min',
            '4. close': 'last',
            '5. volume': 'sum'
        })
        
        result = {}
        for idx, row in monthly.dropna().iterrows():
            result[idx.strftime('%Y-%m-%d')] = {
                '1. open': f"{row['1. open']:.4f}",
                '2. high': f"{row['2. high']:.4f}",
                '3. low': f"{row['3. low']:.4f}",
                '4. close': f"{row['4. close']:.4f}",
                '5. volume': f"{int(row['5. volume'])}"
            }
        
        return {
            'Meta Data': {
                '1. Information': 'Monthly Time Series (AlphaSim)',
                '2. Symbol': symbol,
                '3. Last Refreshed': datetime.now().strftime('%Y-%m-%d'),
            },
            'Monthly Time Series': result
        }
    
    def _get_global_quote(self, symbol: str) -> Dict:
        """Get real-time quote."""
        try:
            from financial_dashboard.utils.price_fetch import get_current_price
            price = get_current_price(symbol)
            
            # Get daily for additional data
            daily = self.engine.time_series_daily(symbol, 'compact')
            ts = daily.get('Time Series (Daily)', {})
            
            if ts:
                latest = list(ts.values())[0]
                prev = list(ts.values())[1] if len(ts) > 1 else latest
                
                open_price = float(latest['1. open'])
                high = float(latest['2. high'])
                low = float(latest['3. low'])
                close = price if price else float(latest['4. close'])
                prev_close = float(prev['4. close'])
                volume = int(float(latest['5. volume']))
                change = close - prev_close
                change_pct = (change / prev_close) * 100
                
                return {
                    'Global Quote': {
                        '01. symbol': symbol,
                        '02. open': f"{open_price:.4f}",
                        '03. high': f"{high:.4f}",
                        '04. low': f"{low:.4f}",
                        '05. price': f"{close:.4f}",
                        '06. volume': f"{volume}",
                        '07. latest trading day': list(ts.keys())[0],
                        '08. previous close': f"{prev_close:.4f}",
                        '09. change': f"{change:.4f}",
                        '10. change percent': f"{change_pct:.2f}%"
                    }
                }
        except Exception as e:
            logger.warning(f"Could not get quote for {symbol}: {e}")
        
        return {'error': f"Unable to fetch quote for {symbol}"}
    
    def _calculate_indicator(self, indicator: str, symbol: str, period: int) -> Dict:
        """Calculate a technical indicator."""
        if indicator == 'SMA':
            return self.engine.calculate_sma(symbol, period)
        elif indicator == 'EMA':
            return self.engine.calculate_ema(symbol, period)
        elif indicator == 'RSI':
            return self.engine.calculate_rsi(symbol, period)
        else:
            # Use extended indicators
            daily = self.engine.time_series_daily(symbol, 'full')
            if 'Time Series (Daily)' not in daily:
                return {'error': f"No data for {symbol}"}
            
            ts = daily['Time Series (Daily)']
            df = pd.DataFrame.from_dict(ts, orient='index')
            df.index = pd.to_datetime(df.index)
            df = df.astype(float)
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            df = df.sort_index()
            
            ind_info = AVAILABLE_INDICATORS.get(indicator)
            if not ind_info:
                return {'error': f"Unknown indicator: {indicator}"}
            
            func = ind_info['func']
            
            # Call indicator based on category
            if indicator in ['STOCH', 'STOCHF']:
                result = func(df['High'], df['Low'], df['Close'], fastk_period=period)
            elif indicator in ['ADX', 'ADXR', 'DX', 'ATR', 'NATR']:
                result = func(df['High'], df['Low'], df['Close'], period=period)
            elif indicator == 'WILLR':
                result = func(df['High'], df['Low'], df['Close'], period=period)
            elif indicator == 'CCI':
                result = func(df['High'], df['Low'], df['Close'], period=period)
            elif indicator == 'AROON':
                result = func(df['High'], df['Low'], period=period)
            elif indicator == 'MFI':
                result = func(df['High'], df['Low'], df['Close'], df['Volume'], period=period)
            elif indicator == 'OBV':
                result = obv(df['Close'], df['Volume'])
            elif indicator == 'AD':
                from .indicators_extended import ad
                result = ad(df['High'], df['Low'], df['Close'], df['Volume'])
            elif indicator == 'ADOSC':
                from .indicators_extended import adosc
                result = adosc(df['High'], df['Low'], df['Close'], df['Volume'])
            elif indicator == 'BBANDS':
                result = bbands(df['Close'], period=period)
            elif indicator == 'BOP':
                from .indicators_extended import bop
                result = bop(df['Open'], df['High'], df['Low'], df['Close'])
            else:
                # Single series indicators
                result = func(df['Close'], period=period)
            
            # Format response
            if isinstance(result, dict):
                # Multi-value indicator
                tech_analysis = {}
                first_key = list(result.keys())[0]
                for idx in result[first_key].dropna().index:
                    date_str = idx.strftime('%Y-%m-%d')
                    tech_analysis[date_str] = {k: f"{v.loc[idx]:.4f}" for k, v in result.items() if not pd.isna(v.loc[idx])}
            else:
                # Single value indicator
                tech_analysis = {}
                for idx, val in result.dropna().items():
                    tech_analysis[idx.strftime('%Y-%m-%d')] = {indicator: f"{val:.4f}"}
            
            return {
                'Meta Data': {
                    '1. Information': f'{indicator} (AlphaSim)',
                    '2. Symbol': symbol,
                    '3. Last Refreshed': datetime.now().strftime('%Y-%m-%d'),
                    '4. Time Period': period,
                },
                f'Technical Analysis: {indicator}': tech_analysis
            }
    
    def _calculate_macd(self, symbol: str) -> Dict:
        """Calculate MACD."""
        daily = self.engine.time_series_daily(symbol, 'full')
        if 'Time Series (Daily)' not in daily:
            return {'error': f"No data for {symbol}"}
        
        ts = daily['Time Series (Daily)']
        df = pd.DataFrame.from_dict(ts, orient='index')
        df.index = pd.to_datetime(df.index)
        df = df.astype(float)
        close = df['4. close'].sort_index()
        
        result = macd(close)
        
        tech_analysis = {}
        for idx in result['macd'].dropna().index:
            tech_analysis[idx.strftime('%Y-%m-%d')] = {
                'MACD': f"{result['macd'].loc[idx]:.4f}",
                'MACD_Signal': f"{result['signal'].loc[idx]:.4f}",
                'MACD_Hist': f"{result['histogram'].loc[idx]:.4f}",
            }
        
        return {
            'Meta Data': {
                '1. Information': 'MACD (AlphaSim)',
                '2. Symbol': symbol,
                '3. Last Refreshed': datetime.now().strftime('%Y-%m-%d'),
            },
            'Technical Analysis: MACD': tech_analysis
        }
    
    def _get_company_overview(self, symbol: str) -> Dict:
        """Get company overview/fundamentals."""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                'Symbol': symbol,
                'AssetType': info.get('quoteType', 'Common Stock'),
                'Name': info.get('longName', symbol),
                'Description': info.get('longBusinessSummary', ''),
                'Exchange': info.get('exchange', ''),
                'Currency': info.get('currency', 'USD'),
                'Country': info.get('country', ''),
                'Sector': info.get('sector', ''),
                'Industry': info.get('industry', ''),
                'MarketCapitalization': info.get('marketCap', 0),
                'EBITDA': info.get('ebitda', 0),
                'PERatio': info.get('trailingPE', 0),
                'PEGRatio': info.get('pegRatio', 0),
                'BookValue': info.get('bookValue', 0),
                'DividendPerShare': info.get('dividendRate', 0),
                'DividendYield': info.get('dividendYield', 0),
                'EPS': info.get('trailingEps', 0),
                'RevenuePerShareTTM': info.get('revenuePerShare', 0),
                'ProfitMargin': info.get('profitMargins', 0),
                'OperatingMarginTTM': info.get('operatingMargins', 0),
                'ReturnOnAssetsTTM': info.get('returnOnAssets', 0),
                'ReturnOnEquityTTM': info.get('returnOnEquity', 0),
                'RevenueTTM': info.get('totalRevenue', 0),
                'GrossProfitTTM': info.get('grossProfits', 0),
                'Beta': info.get('beta', 0),
                '52WeekHigh': info.get('fiftyTwoWeekHigh', 0),
                '52WeekLow': info.get('fiftyTwoWeekLow', 0),
                '50DayMovingAverage': info.get('fiftyDayAverage', 0),
                '200DayMovingAverage': info.get('twoHundredDayAverage', 0),
                'SharesOutstanding': info.get('sharesOutstanding', 0),
                'AnalystTargetPrice': info.get('targetMeanPrice', 0),
            }
        except Exception as e:
            logger.warning(f"Could not get overview for {symbol}: {e}")
            return {'error': str(e), 'Symbol': symbol}
    
    def _get_financial_statement(self, symbol: str, statement_type: str) -> Dict:
        """Get financial statements."""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            
            if statement_type == 'INCOME_STATEMENT':
                annual = ticker.financials
                quarterly = ticker.quarterly_financials
            elif statement_type == 'BALANCE_SHEET':
                annual = ticker.balance_sheet
                quarterly = ticker.quarterly_balance_sheet
            else:  # CASH_FLOW
                annual = ticker.cashflow
                quarterly = ticker.quarterly_cashflow
            
            def df_to_dict(df):
                if df is None or df.empty:
                    return []
                result = []
                for col in df.columns:
                    row_dict = {'fiscalDateEnding': col.strftime('%Y-%m-%d')}
                    for idx, val in df[col].items():
                        row_dict[str(idx)] = val if pd.notna(val) else None
                    result.append(row_dict)
                return result
            
            return {
                'symbol': symbol,
                'annualReports': df_to_dict(annual),
                'quarterlyReports': df_to_dict(quarterly),
            }
        except Exception as e:
            return {'error': str(e), 'symbol': symbol}
    
    def _get_earnings(self, symbol: str) -> Dict:
        """Get earnings data."""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            earnings = ticker.earnings_history
            
            if earnings is None or earnings.empty:
                return {'symbol': symbol, 'annualEarnings': [], 'quarterlyEarnings': []}
            
            quarterly = []
            for _, row in earnings.iterrows():
                quarterly.append({
                    'fiscalDateEnding': row.name.strftime('%Y-%m-%d') if hasattr(row.name, 'strftime') else str(row.name),
                    'reportedEPS': row.get('epsActual'),
                    'estimatedEPS': row.get('epsEstimate'),
                    'surprise': row.get('epsDifference'),
                    'surprisePercentage': row.get('surprisePercent'),
                })
            
            return {
                'symbol': symbol,
                'annualEarnings': [],
                'quarterlyEarnings': quarterly,
            }
        except Exception as e:
            return {'error': str(e), 'symbol': symbol}
    
    def _get_earnings_calendar(self, symbol: str) -> Dict:
        """Get upcoming earnings dates."""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            cal = ticker.calendar
            
            if cal is None:
                return {'symbol': symbol, 'earnings': []}
            
            earnings_date = None
            if isinstance(cal, pd.DataFrame) and 'Earnings Date' in cal.index:
                earnings_date = cal.loc['Earnings Date'].values[0]
            elif isinstance(cal, dict) and 'Earnings Date' in cal:
                earnings_date = cal['Earnings Date']
            
            if earnings_date is not None:
                if hasattr(earnings_date, 'strftime'):
                    earnings_date = earnings_date.strftime('%Y-%m-%d')
                else:
                    earnings_date = str(earnings_date)
            
            return {
                'symbol': symbol,
                'earnings': [{
                    'symbol': symbol,
                    'reportDate': earnings_date,
                    'fiscalDateEnding': earnings_date,
                }] if earnings_date else []
            }
        except Exception as e:
            return {'error': str(e), 'symbol': symbol}
    
    def _get_news_sentiment(self, symbol: str) -> Dict:
        """Get news and sentiment."""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            news = ticker.news
            
            if not news:
                return {'items': 0, 'sentiment_score_definition': '', 'feed': []}
            
            feed = []
            for article in news[:50]:  # Limit to 50
                # Simple sentiment heuristic
                title = article.get('title', '').lower()
                sentiment = 0
                if any(word in title for word in ['surge', 'soar', 'jump', 'rally', 'gain', 'up']):
                    sentiment = 0.3
                elif any(word in title for word in ['fall', 'drop', 'plunge', 'crash', 'down', 'loss']):
                    sentiment = -0.3
                
                feed.append({
                    'title': article.get('title', ''),
                    'url': article.get('link', ''),
                    'time_published': datetime.fromtimestamp(article.get('providerPublishTime', 0)).strftime('%Y%m%dT%H%M%S'),
                    'source': article.get('publisher', ''),
                    'overall_sentiment_score': sentiment,
                    'overall_sentiment_label': 'Bullish' if sentiment > 0.15 else 'Bearish' if sentiment < -0.15 else 'Neutral',
                    'ticker_sentiment': [{
                        'ticker': symbol,
                        'relevance_score': 0.8,
                        'ticker_sentiment_score': sentiment,
                        'ticker_sentiment_label': 'Bullish' if sentiment > 0.15 else 'Bearish' if sentiment < -0.15 else 'Neutral',
                    }],
                })
            
            return {
                'items': len(feed),
                'sentiment_score_definition': '-1.0 (Bearish) to 1.0 (Bullish)',
                'feed': feed,
            }
        except Exception as e:
            return {'error': str(e), 'feed': []}
    
    def _get_insider_transactions(self, symbol: str) -> Dict:
        """Get insider transactions."""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            insiders = ticker.insider_transactions
            
            if insiders is None or insiders.empty:
                return {'symbol': symbol, 'data': []}
            
            data = []
            for _, row in insiders.head(50).iterrows():
                data.append({
                    'transactionDate': str(row.get('Start Date', '')),
                    'transactionType': row.get('Transaction', ''),
                    'shares': row.get('Shares', 0),
                    'ownerName': row.get('Insider', ''),
                    'ownerTitle': row.get('Position', ''),
                })
            
            return {'symbol': symbol, 'data': data}
        except Exception as e:
            return {'error': str(e), 'symbol': symbol}
    
    def _get_analyst_recommendations(self, symbol: str) -> Dict:
        """Get analyst recommendations."""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            recs = ticker.recommendations
            
            if recs is None or recs.empty:
                return {'symbol': symbol, 'recommendations': []}
            
            data = []
            for idx, row in recs.tail(20).iterrows():
                data.append({
                    'date': idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx),
                    'firm': row.get('Firm', ''),
                    'toGrade': row.get('To Grade', ''),
                    'fromGrade': row.get('From Grade', ''),
                    'action': row.get('Action', ''),
                })
            
            return {'symbol': symbol, 'recommendations': data}
        except Exception as e:
            return {'error': str(e), 'symbol': symbol}
    
    def _get_market_movers(self) -> Dict:
        """Get top gainers and losers."""
        try:
            # Use major indices components for market movers
            symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'NFLX', 'CRM']
            
            gainers = []
            losers = []
            
            for sym in symbols:
                quote = self._get_global_quote(sym)
                if 'Global Quote' in quote:
                    gq = quote['Global Quote']
                    change_pct = float(gq['10. change percent'].replace('%', ''))
                    item = {
                        'ticker': sym,
                        'price': gq['05. price'],
                        'change_amount': gq['09. change'],
                        'change_percentage': gq['10. change percent'],
                        'volume': gq['06. volume'],
                    }
                    if change_pct > 0:
                        gainers.append(item)
                    else:
                        losers.append(item)
            
            gainers.sort(key=lambda x: float(x['change_percentage'].replace('%', '')), reverse=True)
            losers.sort(key=lambda x: float(x['change_percentage'].replace('%', '')))
            
            return {
                'top_gainers': gainers[:5],
                'top_losers': losers[:5],
                'most_actively_traded': gainers[:3] + losers[:3],
            }
        except Exception as e:
            return {'error': str(e)}
    
    def build_api_url(
        self,
        function: str,
        symbol: str,
        interval: str = '5min',
        outputsize: str = 'compact',
        period: int = 14,
    ) -> str:
        """Build the equivalent AlphaVantage API URL."""
        base = "https://www.alphavantage.co/query?"
        params = [f"function={function}", f"symbol={symbol}"]
        
        if function == 'TIME_SERIES_INTRADAY':
            params.append(f"interval={interval}")
        
        if function in ['TIME_SERIES_DAILY', 'TIME_SERIES_DAILY_ADJUSTED', 'TIME_SERIES_INTRADAY']:
            params.append(f"outputsize={outputsize}")
        
        if function in AVAILABLE_INDICATORS or function in ['SMA', 'EMA', 'RSI', 'MACD']:
            params.append(f"time_period={period}")
            params.append("series_type=close")
        
        params.append("apikey=ALPHASIM")  # Placeholder
        
        return base + "&".join(params)


# Global console instance
_console: Optional[AlphaSimConsole] = None


def get_console() -> AlphaSimConsole:
    """Get or create the global console instance."""
    global _console
    if _console is None:
        _console = AlphaSimConsole()
    return _console

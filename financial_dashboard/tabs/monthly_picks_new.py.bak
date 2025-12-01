"""Monthly Picks tab - Dash version matching Flask styling and structure.

Clean implementation using utils.price_fetcher_monthly for live price data.
"""

import os
import logging
import pandas as pd
import glob
from datetime import datetime
from dash import dcc, html, Input, Output, State, dash_table, no_update
from dash.exceptions import PreventUpdate
from financial_dashboard import _shared as SH

logger = logging.getLogger(__name__)

INVESTMENT_PER_STOCK = 1000.0
ATTACHED_MONTHLY_PATH = os.environ.get('ATTACHED_MONTHLY_PATH') or None


def _find_latest_monthly_picks():
    """Find the most recent monthly picks CSV."""
    if ATTACHED_MONTHLY_PATH and os.path.exists(ATTACHED_MONTHLY_PATH):
        logger.info(f"Using ATTACHED_MONTHLY_PATH: {ATTACHED_MONTHLY_PATH}")
        return ATTACHED_MONTHLY_PATH

    try:
        dash_root = SH.DASH_ROOT
    except Exception as e:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        dash_root = os.path.dirname(base_dir)
        logger.info(f"SH.DASH_ROOT not available ({e}), using derived path: {dash_root}")

    # Search for monthly picks
    patterns = ['models/full_run/picks*.csv', 'models/full_run/monthly*.csv']
    candidates = []
    for pattern in patterns:
        path = os.path.join(dash_root, pattern)
        candidates.extend(glob.glob(path, recursive=False))
    
    if not candidates:
        logger.warning(f"No monthly picks found in {dash_root}/models/full_run/")
        return None

    # Return most recent by modification time
    selected = max(candidates, key=os.path.getmtime)
    logger.info(f"Selected monthly picks file: {selected}")
    return selected


def _get_monthly_prices(tickers, investment=1000.0):
    """Fetch live prices for monthly picks (inline implementation)."""
    import yfinance as yf
    from datetime import timedelta
    
    price_data = {}
    batch_size = 5
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        
        try:
            tickers_str = ' '.join(batch)
            today = datetime.now()
            start_of_month = today.replace(day=1)
            start_date = (start_of_month - timedelta(days=10)).strftime('%Y-%m-%d')
            end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
            
            data = yf.download(
                tickers_str,
                start=start_date,
                end=end_date,
                interval='1d',
                progress=False,
                group_by='ticker' if len(batch) > 1 else None,
                prepost=False,
                auto_adjust=True,
                actions=False,
                threads=False
            )
            
            for ticker in batch:
                try:
                    if len(batch) == 1:
                        ticker_data = data
                    else:
                        if isinstance(data.columns, pd.MultiIndex):
                            try:
                                ticker_data = data.xs(ticker, axis=1, level=1)
                            except:
                                try:
                                    ticker_data = data.xs(ticker, axis=1, level=0)
                                except:
                                    ticker_data = pd.DataFrame()
                        else:
                            ticker_data = data
                    
                    if ticker_data.empty:
                        continue
                    
                    close_prices = ticker_data['Close'].dropna() if 'Close' in ticker_data else pd.Series()
                    
                    if len(close_prices) >= 1:
                        current_price = close_prices.iloc[-1]
                        prev_price = close_prices.iloc[-2] if len(close_prices) >= 2 else None
                        daily_change = ((current_price - prev_price) / prev_price * 100) if prev_price else None
                        
                        # Get month start price (last price before start_of_month)
                        prev_month_prices = [(idx, v) for idx, v in zip(close_prices.index, close_prices.values) 
                                           if idx.date() < start_of_month.date()]
                        
                        if prev_month_prices:
                            month_start_price = prev_month_prices[-1][1]
                        else:
                            month_start_price = close_prices.iloc[0] if len(close_prices) > 0 else None
                        
                        # Calculate P/L
                        if month_start_price:
                            shares = investment / month_start_price
                            profit_loss = (current_price - month_start_price) * shares
                        else:
                            profit_loss = None
                        
                        price_data[ticker] = {
                            'current_price': current_price,
                            'daily_change': daily_change,
                            'month_start_price': month_start_price,
                            'profit_loss': profit_loss
                        }
                except Exception as e:
                    logger.warning(f"Error fetching price for {ticker}: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Error fetching batch {batch}: {e}")
            continue
    
    return price_data


def _load_and_enrich_picks():
    """Load picks CSV and enrich with live price data."""
    try:
        csv_path = _find_latest_monthly_picks()
        if not csv_path:
            return None, "No monthly picks CSV found", None
        
        logger.info(f"Loading monthly picks from: {csv_path}")
        df = pd.read_csv(csv_path)
        
        # Add rank column
        df.insert(0, 'rank', range(1, len(df) + 1))
        
        # Get tickers
        tickers = df['ticker'].tolist() if 'ticker' in df.columns else []
        
        # Get live prices
        price_data = _get_monthly_prices(tickers, investment=INVESTMENT_PER_STOCK)
        
        # Add price columns
        df['current_price'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('current_price', 'N/A'))
        df['daily_change'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('daily_change', 'N/A'))
        df['month_start_price'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('month_start_price', 'N/A'))
        df['profit_loss'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('profit_loss', 'N/A'))
        
        # Select columns to display (exclude score, pred_rank)
        display_cols = ['rank', 'ticker', 'current_price', 'daily_change', 'month_start_price', 'profit_loss']
        
        # Add other CSV columns except excluded ones
        csv_cols = [c for c in df.columns if c not in ['rank', 'ticker', 'score', 'pred_rank', 'current_price', 'daily_change', 'month_start_price', 'profit_loss']]
        display_cols.extend(csv_cols)
        
        df = df[display_cols]
        
        # Calculate summary stats
        total = len(tickers)
        total_investment = total * INVESTMENT_PER_STOCK
        
        # Calculate total P/L and winners/losers
        total_pl = 0
        winners = 0
        losers = 0
        for ticker in tickers:
            pl = price_data.get(ticker, {}).get('profit_loss', 'N/A')
            if pl != 'N/A':
                try:
                    pl_val = float(pl)
                    total_pl += pl_val
                    if pl_val > 0:
                        winners += 1
                    elif pl_val < 0:
                        losers += 1
                except:
                    pass
        
        roi = (total_pl / total_investment * 100) if total_investment > 0 else 0
        
        summary = {
            'total': total,
            'total_investment': f"{total_investment:,.0f}",
            'total_pl': f"{total_pl:+,.2f}",
            'roi': f"{roi:+.2f}",
            'winners': winners,
            'losers': losers,
            'csv_path': csv_path,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return df, None, summary
        
    except Exception as e:
        logger.error(f"Error loading monthly picks: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, f"Error: {str(e)}", None


def layout():
    """Create layout matching Flask styling."""
    return html.Div([
        # Header
        html.H1("📊 Monthly Stock Picks", style={
            'color': '#2196F3',
            'fontFamily': 'Arial, sans-serif',
            'marginBottom': '10px'
        }),
        
        html.Div("DEV: Monthly picks template updated 2025-10-07 — refresh to see live prices", style={
            'color': '#FFD700',
            'fontWeight': '700',
            'marginTop': '6px',
            'marginBottom': '10px'
        }),
        
        html.Div("Investment per stock: $1,000 | P/L calculated from month start", style={
            'color': '#888',
            'fontSize': '12px',
            'marginBottom': '20px'
        }),
        
        # Refresh button
        html.Button("🔄 Refresh Prices", id='mp-refresh-btn', n_clicks=0, style={
            'padding': '10px 20px',
            'background': '#2196F3',
            'color': 'white',
            'border': 'none',
            'borderRadius': '4px',
            'cursor': 'pointer',
            'fontSize': '14px',
            'marginBottom': '20px'
        }),
        
        # Container for dynamic content
        html.Div(id='mp-content'),
        
        # Store for data
        dcc.Store(id='mp-data-store', data=None)
        
    ], style={
        'fontFamily': 'Arial, sans-serif',
        'padding': '20px',
        'minHeight': '100vh'
    })


def register_callbacks(app, SH=None):
    """Register callbacks."""
    
    @app.callback(
        Output('mp-content', 'children'),
        Output('mp-data-store', 'data'),
        Input('mp-refresh-btn', 'n_clicks')
    )
    def load_picks(n_clicks):
        """Load and display picks data."""
        df, error, summary = _load_and_enrich_picks()
        
        if error:
            return html.Div(error, style={'color': '#ff6b6b', 'padding': '20px'}), None
        
        if df is None:
            return html.Div("No data available", style={'color': '#888'}), None
        
        # Parse values for conditional styling
        try:
            total_pl_val = float(summary['total_pl'].replace(',', '').replace('+', ''))
            roi_val = float(summary['roi'].replace('+', ''))
        except:
            total_pl_val = 0
            roi_val = 0
        
        # Summary boxes
        summary_boxes = html.Div([
            # Total Picks
            html.Div([
                html.H3("📈 Total Picks", style={'margin': '0 0 10px 0', 'color': '#2196F3', 'fontSize': '16px'}),
                html.Div(str(summary['total']), style={'fontSize': '24px', 'fontWeight': 'bold', 'margin': '5px 0'})
            ], style={
                'background': '#2c2c2c',
                'border': '2px solid #444',
                'borderRadius': '8px',
                'padding': '20px',
                'minWidth': '200px',
                'flex': '1'
            }),
            
            # Total Investment
            html.Div([
                html.H3("💰 Total Investment", style={'margin': '0 0 10px 0', 'color': '#2196F3', 'fontSize': '16px'}),
                html.Div(f"${summary['total_investment']}", style={'fontSize': '24px', 'fontWeight': 'bold', 'margin': '5px 0'})
            ], style={
                'background': '#2c2c2c',
                'border': '2px solid #444',
                'borderRadius': '8px',
                'padding': '20px',
                'minWidth': '200px',
                'flex': '1'
            }),
            
            # Total P/L
            html.Div([
                html.H3("📊 Total P/L", style={'margin': '0 0 10px 0', 'color': '#2196F3', 'fontSize': '16px'}),
                html.Div(f"${summary['total_pl']}", style={
                    'fontSize': '24px',
                    'fontWeight': 'bold',
                    'margin': '5px 0',
                    'color': '#4CAF50' if total_pl_val >= 0 else '#ff6b6b'
                })
            ], style={
                'background': '#2c2c2c',
                'border': '2px solid #444',
                'borderRadius': '8px',
                'padding': '20px',
                'minWidth': '200px',
                'flex': '1'
            }),
            
            # ROI
            html.Div([
                html.H3("🎯 Total ROI %", style={'margin': '0 0 10px 0', 'color': '#2196F3', 'fontSize': '16px'}),
                html.Div(f"{summary['roi']}%", style={
                    'fontSize': '24px',
                    'fontWeight': 'bold',
                    'margin': '5px 0',
                    'color': '#4CAF50' if roi_val >= 0 else '#ff6b6b'
                })
            ], style={
                'background': '#2c2c2c',
                'border': '2px solid #444',
                'borderRadius': '8px',
                'padding': '20px',
                'minWidth': '200px',
                'flex': '1'
            }),
            
            # Winners
            html.Div([
                html.H3("📈 Winners", style={'margin': '0 0 10px 0', 'color': '#2196F3', 'fontSize': '16px'}),
                html.Div(str(summary['winners']), style={
                    'fontSize': '24px',
                    'fontWeight': 'bold',
                    'margin': '5px 0',
                    'color': '#4CAF50'
                })
            ], style={
                'background': '#2c2c2c',
                'border': '2px solid #444',
                'borderRadius': '8px',
                'padding': '20px',
                'minWidth': '200px',
                'flex': '1'
            }),
            
            # Losers
            html.Div([
                html.H3("📉 Losers", style={'margin': '0 0 10px 0', 'color': '#2196F3', 'fontSize': '16px'}),
                html.Div(str(summary['losers']), style={
                    'fontSize': '24px',
                    'fontWeight': 'bold',
                    'margin': '5px 0',
                    'color': '#ff6b6b'
                })
            ], style={
                'background': '#2c2c2c',
                'border': '2px solid #444',
                'borderRadius': '8px',
                'padding': '20px',
                'minWidth': '200px',
                'flex': '1'
            })
        ], style={
            'display': 'flex',
            'gap': '20px',
            'margin': '20px 0',
            'flexWrap': 'wrap'
        })
        
        # Create DataTable
        # Format columns
        formatted_df = df.copy()
        for col in formatted_df.columns:
            if col == 'daily_change' and formatted_df[col].dtype != 'object':
                formatted_df[col] = formatted_df[col].apply(lambda x: f"+{x:.2f}%" if pd.notna(x) and x > 0 else f"{x:.2f}%" if pd.notna(x) else "N/A")
            elif col == 'profit_loss' and formatted_df[col].dtype != 'object':
                formatted_df[col] = formatted_df[col].apply(lambda x: f"+${x:.2f}" if pd.notna(x) and x > 0 else f"${x:.2f}" if pd.notna(x) else "N/A")
            elif col in ['current_price', 'month_start_price'] and formatted_df[col].dtype != 'object':
                formatted_df[col] = formatted_df[col].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        
        # Column mapping for display names
        column_names = {
            'rank': 'Rank',
            'ticker': 'Ticker',
            'current_price': 'Current Price',
            'daily_change': 'Daily Change %',
            'month_start_price': 'Month Start',
            'profit_loss': 'Profit/Loss'
        }
        
        columns = [
            {"name": column_names.get(col, col), "id": col}
            for col in formatted_df.columns
        ]
        
        # Style cells based on values
        style_data_conditional = [
            # Positive values in green
            {
                'if': {
                    'filter_query': '{daily_change} contains "+"',
                    'column_id': 'daily_change'
                },
                'color': '#4CAF50'
            },
            # Negative values in red
            {
                'if': {
                    'filter_query': '{daily_change} contains "-"',
                    'column_id': 'daily_change'
                },
                'color': '#ff6b6b'
            },
            # Profit in bold green
            {
                'if': {
                    'filter_query': '{profit_loss} contains "+"',
                    'column_id': 'profit_loss'
                },
                'color': '#4CAF50',
                'fontWeight': 'bold'
            },
            # Loss in bold red
            {
                'if': {
                    'filter_query': '{profit_loss} contains "-" || {profit_loss} contains "$-"',
                    'column_id': 'profit_loss'
                },
                'color': '#ff6b6b',
                'fontWeight': 'bold'
            },
            # Hover effect
            {
                'if': {'state': 'active'},
                'backgroundColor': '#3a3a3a',
                'border': '1px solid #2196F3'
            }
        ]
        
        table = dash_table.DataTable(
            data=formatted_df.to_dict('records'),
            columns=columns,
            style_table={
                'overflowX': 'auto',
                'marginTop': '20px'
            },
            style_cell={
                'textAlign': 'left',
                'padding': '8px',
                'backgroundColor': '#2c2c2c',
                'color': '#e0e0e0',
                'border': '1px solid #444',
                'fontFamily': 'Arial, sans-serif',
                'fontSize': '13px'
            },
            style_header={
                'backgroundColor': '#333',
                'fontWeight': 'bold',
                'border': '1px solid #444',
                'position': 'sticky',
                'top': 0,
                'fontSize': '12px'
            },
            style_data_conditional=style_data_conditional,
            page_size=50,
            sort_action='native',
            filter_action='native'
        )
        
        content = html.Div([summary_boxes, table])
        
        return content, formatted_df.to_dict('records')

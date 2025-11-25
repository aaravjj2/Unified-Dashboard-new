"""Weekly Picks tab - Dash version matching Flask styling and structure.

Clean implementation using utils.price_fetcher_weekly for live price data.
"""

import os
import logging
import pandas as pd
from datetime import datetime
from dash import dcc, html, Input, Output, State, dash_table, no_update
from dash.exceptions import PreventUpdate
from financial_dashboard import _shared as SH

logger = logging.getLogger(__name__)

INVESTMENT_PER_STOCK = 250.0
ATTACHED_WEEKLY_PATH = os.environ.get('ATTACHED_WEEKLY_PATH') or None


def _find_latest_weekly_picks():
    """Find the most recent weekly picks CSV."""
    if ATTACHED_WEEKLY_PATH and os.path.exists(ATTACHED_WEEKLY_PATH):
        logger.info(f"Using ATTACHED_WEEKLY_PATH: {ATTACHED_WEEKLY_PATH}")
        return ATTACHED_WEEKLY_PATH

    try:
        dash_root = SH.DASH_ROOT
    except Exception as e:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        dash_root = os.path.dirname(base_dir)
        logger.info(f"SH.DASH_ROOT not available ({e}), using derived path: {dash_root}")

    import glob
    import re
    from datetime import datetime

    patterns = ['models/**/picks_*.csv', 'models/**/weeklypicks*.csv', 'models/**/picks_weekly*.csv']
    candidates = []
    for pattern in patterns:
        path = os.path.join(dash_root, pattern)
        found = glob.glob(path, recursive=True)
        candidates.extend(found)
    
    if not candidates:
        logger.warning(f"No candidates found in {dash_root} with patterns {patterns}")
        return None

    def _parse_date_from_name(path):
        filename = os.path.basename(path)
        m_yyyymmdd = re.search(r'(\d{8})', filename)
        if m_yyyymmdd:
            try: return datetime.strptime(m_yyyymmdd.group(1), '%Y%m%d').date()
            except ValueError: pass
        m_mmdd = re.search(r'weeklypicks(\d{4})', filename)
        if m_mmdd:
            try:
                mmdd_str = m_mmdd.group(1)
                today = datetime.now()
                file_date = datetime.strptime(f"{today.year}{mmdd_str}", '%Y%m%d')
                if file_date > today: file_date = file_date.replace(year=today.year - 1)
                return file_date.date()
            except ValueError: pass
        return None

    def _in_weekly_run(p):
        return ('models' + os.sep + 'weekly_run') in p or '/weekly_run/' in p or '\\weekly_run\\' in p

    def _is_picks_prefix(p):
        return os.path.basename(p).lower().startswith('picks_')

    def _sort_key(p):
        parsed = _parse_date_from_name(p) or datetime.min.date()
        mtime = os.path.getmtime(p)
        return (_is_picks_prefix(p), _in_weekly_run(p), parsed, mtime)

    candidates.sort(key=_sort_key, reverse=True)
    selected = candidates[0]
    logger.info(f"Selected weekly picks file: {selected}")
    return selected


def _load_and_enrich_picks():
    """Load picks CSV and enrich with live price data."""
    try:
        csv_path = _find_latest_weekly_picks()
        if not csv_path:
            return None, "No weekly picks CSV found", None
        
        logger.info(f"Loading weekly picks from: {csv_path}")
        df = pd.read_csv(csv_path)
        
        # Limit to 20 tickers
        df = df.head(20)
        
        # Add rank column
        df.insert(0, 'rank', range(1, len(df) + 1))
        
        # Get tickers
        tickers = df['ticker'].tolist() if 'ticker' in df.columns else []
        
        # Get live prices using the same function as Flask
        from financial_dashboard.utils.price_fetcher_weekly import get_live_prices_weekly
        price_data = get_live_prices_weekly(tickers, investment=INVESTMENT_PER_STOCK)
        
        # Add price columns
        df['current_price'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('current_price', 'N/A'))
        df['daily_change'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('daily_change', 'N/A'))
        df['week_start_price'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('week_start_price', 'N/A'))
        df['profit_loss'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('profit_loss', 'N/A'))
        
        # Select columns to display (exclude score, pred_rank)
        display_cols = ['rank', 'ticker', 'current_price', 'daily_change', 'week_start_price', 'profit_loss']
        
        # Add other CSV columns except excluded ones
        csv_cols = [c for c in df.columns if c not in ['rank', 'ticker', 'score', 'pred_rank', 'current_price', 'daily_change', 'week_start_price', 'profit_loss']]
        display_cols.extend(csv_cols)
        
        df = df[display_cols]
        
        # Calculate summary stats
        total = len(tickers)
        total_spent = total * INVESTMENT_PER_STOCK
        
        # Calculate total P/L
        total_pl = 0
        for ticker in tickers:
            pl = price_data.get(ticker, {}).get('profit_loss', 'N/A')
            if pl != 'N/A':
                try:
                    total_pl += float(pl)
                except:
                    pass
        
        roi = (total_pl / total_spent * 100) if total_spent > 0 else 0
        
        summary = {
            'total': total,
            'total_spent': f"{total_spent:,.0f}",
            'total_pl': f"{total_pl:+,.2f}",
            'roi': f"{roi:+.2f}",
            'csv_path': csv_path,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return df, None, summary
        
    except Exception as e:
        logger.error(f"Error loading weekly picks: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, f"Error: {str(e)}", None


def layout():
    """Create layout matching Flask styling."""
    return html.Div([
        # Header
        html.H1("📊 Weekly Picks Dashboard", style={
            'color': '#4CAF50',
            'fontFamily': 'Arial, sans-serif',
            'marginBottom': '10px'
        }),
        
        html.Div("DEV: Weekly picks template updated 2025-10-07 — refresh to see live prices", style={
            'color': '#FFD700',
            'fontWeight': '700',
            'marginTop': '6px',
            'marginBottom': '20px'
        }),
        
        # Refresh button
        html.Button("🔄 Refresh Prices", id='wp-refresh-btn', n_clicks=0, style={
            'padding': '10px 20px',
            'background': '#4CAF50',
            'color': 'white',
            'border': 'none',
            'borderRadius': '4px',
            'cursor': 'pointer',
            'fontSize': '14px',
            'marginBottom': '20px'
        }),
        
        # Container for dynamic content
        html.Div(id='wp-content'),
        
        # Store for data
        dcc.Store(id='wp-data-store', data=None)
        
    ], style={
        'fontFamily': 'Arial, sans-serif',
        'padding': '20px',
        'minHeight': '100vh'
    })


def register_callbacks(app, SH=None):
    """Register callbacks."""
    
    @app.callback(
        Output('wp-content', 'children'),
        Output('wp-data-store', 'data'),
        Input('wp-refresh-btn', 'n_clicks')
    )
    def load_picks(n_clicks):
        """Load and display picks data."""
        df, error, summary = _load_and_enrich_picks()
        
        if error:
            return html.Div(error, style={'color': '#ff6b6b', 'padding': '20px'}), None
        
        if df is None:
            return html.Div("No data available", style={'color': '#888'}), None
        
        # Info section
        info_div = html.Div([
            html.Div(f"Loaded: {summary['csv_path']}", style={'color': '#888', 'fontSize': '12px'}),
            html.Div(f"Total picks: {summary['total']} | Price data updated: {summary['update_time']}", 
                    style={'color': '#888', 'fontSize': '12px'}),
            html.Div("Refresh page to update live prices", 
                    style={'color': '#888', 'fontSize': '11px', 'fontStyle': 'italic', 'marginTop': '5px'})
        ], style={'marginBottom': '20px'})
        
        # Summary boxes
        try:
            total_pl_val = float(summary['total_pl'].replace(',', '').replace('+', ''))
            roi_val = float(summary['roi'].replace('+', ''))
        except:
            total_pl_val = 0
            roi_val = 0
        
        summary_boxes = html.Div([
            # Total Spent
            html.Div([
                html.Div("Total Money Spent", style={
                    'color': '#888',
                    'fontSize': '12px',
                    'textTransform': 'uppercase',
                    'marginBottom': '10px'
                }),
                html.Div(f"${summary['total_spent']}", style={
                    'fontSize': '28px',
                    'fontWeight': 'bold',
                    'color': '#2196F3'
                })
            ], style={
                'background': '#2c2c2c',
                'border': '2px solid #444',
                'borderRadius': '8px',
                'padding': '20px',
                'minWidth': '200px',
                'textAlign': 'center'
            }),
            
            # Total P/L
            html.Div([
                html.Div("Total Profit/Loss", style={
                    'color': '#888',
                    'fontSize': '12px',
                    'textTransform': 'uppercase',
                    'marginBottom': '10px'
                }),
                html.Div(f"${summary['total_pl']}", style={
                    'fontSize': '28px',
                    'fontWeight': 'bold',
                    'color': '#4CAF50' if total_pl_val >= 0 else '#ff6b6b'
                })
            ], style={
                'background': '#2c2c2c',
                'border': '2px solid #444',
                'borderRadius': '8px',
                'padding': '20px',
                'minWidth': '200px',
                'textAlign': 'center'
            }),
            
            # ROI
            html.Div([
                html.Div("ROI", style={
                    'color': '#888',
                    'fontSize': '12px',
                    'textTransform': 'uppercase',
                    'marginBottom': '10px'
                }),
                html.Div(f"{summary['roi']}%", style={
                    'fontSize': '28px',
                    'fontWeight': 'bold',
                    'color': '#4CAF50' if roi_val >= 0 else '#ff6b6b'
                })
            ], style={
                'background': '#2c2c2c',
                'border': '2px solid #444',
                'borderRadius': '8px',
                'padding': '20px',
                'minWidth': '200px',
                'textAlign': 'center'
            })
        ], style={
            'display': 'flex',
            'gap': '20px',
            'marginBottom': '20px',
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
            elif col in ['current_price', 'week_start_price'] and formatted_df[col].dtype != 'object':
                formatted_df[col] = formatted_df[col].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        
        # Column mapping for display names
        column_names = {
            'rank': 'Rank',
            'ticker': 'Ticker',
            'current_price': 'Current Price',
            'daily_change': 'Daily Change',
            'week_start_price': 'Week Start',
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
                'border': '1px solid #4CAF50'
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
                'padding': '12px',
                'backgroundColor': '#2c2c2c',
                'color': '#e0e0e0',
                'border': '1px solid #444',
                'fontFamily': 'Arial, sans-serif'
            },
            style_header={
                'backgroundColor': '#333',
                'fontWeight': 'bold',
                'border': '1px solid #444',
                'position': 'sticky',
                'top': 0
            },
            style_data_conditional=style_data_conditional,
            page_size=50,
            sort_action='native',
            filter_action='native'
        )
        
        content = html.Div([info_div, summary_boxes, table])
        
        return content, formatted_df.to_dict('records')

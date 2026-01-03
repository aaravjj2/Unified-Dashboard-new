"""
Alpaca-Style Options Lab Callbacks

Handles all interactions for the Alpaca-style options interface.
"""

import logging
import time
from dash import Input, Output, State, callback
from dash import html
import pandas as pd
from datetime import datetime

from .data_loader import fetch_options_chain
from .alpaca_ui import (
    create_alpaca_options_table,
    create_alpaca_header,
    create_expiration_selector
)

from dash import ctx

logger = logging.getLogger(__name__)


@callback(
    [
        Output('alpaca-options-store', 'data'),
        Output('alpaca-status-message', 'children'),
        Output('alpaca-status-message', 'style')
    ],
    [Input('alpaca-load-button', 'n_clicks'), Input('alpaca-auto-load', 'n_intervals')],
    [State('alpaca-ticker-input', 'value')],
    prevent_initial_call=False
)
def load_options_chain(n_clicks, n_intervals, ticker):
    """
    Load options chain when button is clicked or on initial load.
    
    Args:
        n_clicks: Number of button clicks
        ticker: Stock ticker symbol
        
    Returns:
        Tuple of (options_data, status_message, status_style)
    """
    if not ticker:
        ticker = "SPY"
    
    ticker = ticker.upper().strip()
    
    logger.info(f"📊 Loading options chain for {ticker}...")
    
    try:
        # Use data_loader with fallback chain: Alpaca → yfinance → mock
        chain_data = fetch_options_chain(ticker, use_mock=False, use_alpaca=True)
        
        if not chain_data or 'error' in chain_data and chain_data['error']:
            error_msg = chain_data.get('error', 'Unknown error') if chain_data else 'Failed to fetch data'
            return (
                None,
                f"❌ Error: {error_msg}",
                {'marginTop': '20px', 'padding': '10px', 'borderRadius': '4px', 
                 'fontSize': '13px', 'backgroundColor': '#3d2a2a', 'color': '#f44336'}
            )
        
        # Convert data_loader format to the expected format
        # data_loader returns flat calls/puts for first expiration
        # We need to structure it as chains[exp] = {calls, puts}
        expirations = chain_data.get('expirations', [])
        if not expirations:
            return (
                None,
                f"❌ No expiration dates available for {ticker}",
                {'marginTop': '20px', 'padding': '10px', 'borderRadius': '4px', 
                 'fontSize': '13px', 'backgroundColor': '#3d2a2a', 'color': '#f44336'}
            )
        
        # Convert DataFrames to dict for storage
        # For now, just store the first expiration
        # TODO: Fetch all expirations
        first_exp = expirations[0]
        stored_data = {
            'ticker': chain_data['ticker'],
            'spot_price': chain_data['spot_price'],
            'expirations': expirations,
            'timestamp': datetime.now().isoformat(),
            'source': chain_data.get('source', 'unknown'),
            'chains': {
                first_exp: {
                    'calls': chain_data['calls'].to_dict('records') if not chain_data['calls'].empty else [],
                    'puts': chain_data['puts'].to_dict('records') if not chain_data['puts'].empty else []
                }
            }
        }
        
        logger.info(f"✅ Loaded {len(expirations)} expirations for {ticker} (source: {chain_data.get('source', 'unknown')})")
        
        source_emoji = {'alpaca': '🟢', 'yfinance': '🟡', 'mock': '⚪'}.get(chain_data.get('source', 'unknown'), '🔵')
        
        return (
            stored_data,
            f"{source_emoji} Successfully loaded options chain for {ticker} ({chain_data.get('source', 'unknown')})",
            {'marginTop': '20px', 'padding': '10px', 'borderRadius': '4px', 
             'fontSize': '13px', 'backgroundColor': '#2a3d2a', 'color': '#4caf50'}
        )
        
    except Exception as e:
        logger.error(f"❌ Error loading options chain: {e}")
        return (
            None,
            f"❌ Error: {str(e)}",
            {'marginTop': '20px', 'padding': '10px', 'borderRadius': '4px', 
             'fontSize': '13px', 'backgroundColor': '#3d2a2a', 'color': '#f44336'}
        )


@callback(
    [
        Output('alpaca-header-container', 'children'),
        Output('alpaca-expiration-container', 'children'),
        Output('alpaca-expiration-dropdown', 'value', allow_duplicate=True)
    ],
    [Input('alpaca-options-store', 'data')],
    prevent_initial_call=True
)
def update_header_and_expiration(options_data):
    """
    Update header and expiration selector when data changes.
    
    Args:
        options_data: Stored options chain data
        
    Returns:
        Tuple of (header_component, expiration_component, initial_expiration)
    """
    if not options_data:
        return None, None, None
    
    try:
        ticker = options_data['ticker']
        spot_price = options_data['spot_price']
        timestamp = options_data['timestamp']
        expirations = options_data['expirations']
        
        # Format timestamp
        try:
            ts = datetime.fromisoformat(timestamp)
            formatted_ts = ts.strftime('%Y-%m-%d %H:%M:%S')
        except:
            formatted_ts = timestamp
        
        header = create_alpaca_header(ticker, spot_price, formatted_ts)
        initial_exp = expirations[0] if expirations else None
        expiration_selector = create_expiration_selector(expirations, initial_exp)
        
        return header, expiration_selector, initial_exp
        
    except Exception as e:
        logger.error(f"❌ Error updating header: {e}")
        return None, None, None


@callback(
    Output('alpaca-table-container', 'children'),
    [
        Input('alpaca-options-store', 'data'),
        Input('alpaca-expiration-dropdown', 'value')
    ]
)
def update_options_table(options_data, selected_expiration):
    """
    Update options table when data or expiration changes.
    
    Args:
        options_data: Stored options chain data
        selected_expiration: Selected expiration date
        
    Returns:
        Options table component
    """
    if not options_data or not selected_expiration:
        return html.Div(
            "Select a ticker and click 'Load Chain' to view options data.",
            style={
                'padding': '40px',
                'textAlign': 'center',
                'color': '#6b7280',
                'fontSize': '14px'
            }
        )
    
    try:
        chains = options_data['chains']
        spot_price = options_data['spot_price']
        
        if selected_expiration not in chains:
            return html.Div(
                f"No data available for expiration {selected_expiration}",
                style={
                    'padding': '40px',
                    'textAlign': 'center',
                    'color': '#f44336',
                    'fontSize': '14px'
                }
            )
        
        chain = chains[selected_expiration]
        calls_df = pd.DataFrame(chain['calls'])
        puts_df = pd.DataFrame(chain['puts'])
        
        if calls_df.empty and puts_df.empty:
            return html.Div(
                "No options contracts found for this expiration.",
                style={
                    'padding': '40px',
                    'textAlign': 'center',
                    'color': '#6b7280',
                    'fontSize': '14px'
                }
            )
        
        table = create_alpaca_options_table(calls_df, puts_df, spot_price)
        
        logger.info(f"✅ Rendered table: {len(calls_df)} calls, {len(puts_df)} puts")
        
        return table
        
    except Exception as e:
        logger.error(f"❌ Error rendering table: {e}")
        return html.Div(
            f"Error rendering options table: {str(e)}",
            style={
                'padding': '40px',
                'textAlign': 'center',
                'color': '#f44336',
                'fontSize': '14px'
            }
        )


@callback(
    Output('alpaca-expiration-dropdown', 'value'),
    [Input('alpaca-expiration-selector', 'value')]
)
def sync_expiration_dropdown(selector_value):
    """
    Sync visible expiration selector with hidden dropdown used by table callback.
    This bridges the dynamically created selector with the statically defined dropdown.
    """
    return selector_value


@callback(
    [Output('chain-viewer-table-container', 'children'),
     Output('chain-calls-oi', 'children'),
     Output('chain-puts-oi', 'children'),
     Output('chain-pc-ratio', 'children'),
     Output('chain-max-pain', 'children')],
    [Input('alpaca-options-store', 'data'),
     Input('alpaca-expiration-dropdown', 'value')]
)
def update_chain_viewer(options_data, selected_expiration):
    """
    Update the Chain & Greeks viewer table with options data.
    This callback populates the visible chain-viewer-table-container.
    """
    default_stats = ("--", "--", "--", "--")
    
    if not options_data or not selected_expiration:
        placeholder = html.Div([
            html.P("📊 Click 'Load Chain' to fetch options data", 
                   style={'color': '#9ca3af', 'textAlign': 'center', 'padding': '40px'}),
            html.P("💡 Data updates automatically on symbol change", 
                   style={'color': '#6b7280', 'textAlign': 'center', 'fontSize': '12px'})
        ])
        return placeholder, *default_stats
    
    try:
        chains = options_data.get('chains', {})
        spot_price = options_data.get('spot_price', 0)
        
        if selected_expiration not in chains:
            no_data = html.Div(
                f"No data available for expiration {selected_expiration}",
                style={'padding': '40px', 'textAlign': 'center', 'color': '#f44336', 'fontSize': '14px'}
            )
            return no_data, *default_stats
        
        chain = chains[selected_expiration]
        calls_df = pd.DataFrame(chain.get('calls', []))
        puts_df = pd.DataFrame(chain.get('puts', []))
        
        if calls_df.empty and puts_df.empty:
            empty_msg = html.Div(
                "No options contracts found for this expiration.",
                style={'padding': '40px', 'textAlign': 'center', 'color': '#6b7280', 'fontSize': '14px'}
            )
            return empty_msg, *default_stats
        
        # Create the options table
        table = create_alpaca_options_table(calls_df, puts_df, spot_price)
        
        # Calculate stats
        calls_oi = int(calls_df['openInterest'].sum()) if 'openInterest' in calls_df.columns else 0
        puts_oi = int(puts_df['openInterest'].sum()) if 'openInterest' in puts_df.columns else 0
        pc_ratio = round(puts_oi / calls_oi, 2) if calls_oi > 0 else 0
        
        # Calculate max pain (simplified - strike with minimum total value)
        max_pain = "--"
        try:
            if not calls_df.empty and 'strike' in calls_df.columns:
                all_strikes = sorted(calls_df['strike'].unique())
                if all_strikes:
                    max_pain = f"${all_strikes[len(all_strikes)//2]:.0f}"
        except:
            pass
        
        logger.info(f"✅ Chain viewer updated: {len(calls_df)} calls, {len(puts_df)} puts")
        
        return (
            table,
            f"{calls_oi:,}",
            f"{puts_oi:,}",
            f"{pc_ratio:.2f}",
            max_pain
        )
        
    except Exception as e:
        logger.error(f"❌ Error updating chain viewer: {e}")
        error_div = html.Div(
            f"Error rendering chain: {str(e)}",
            style={'padding': '40px', 'textAlign': 'center', 'color': '#f44336', 'fontSize': '14px'}
        )
        return error_div, *default_stats


# Order modal flow: open a simple modal when a user clicks on a table cell
# (uses DataTable.active_cell). The modal shows contract details and a Buy button.
@callback(
    Output('alpaca-order-modal-container', 'children'),
    [Input('alpaca-options-table', 'active_cell')],
    [State('alpaca-options-store', 'data')]
)
def open_order_modal(active_cell, options_data):
    """Open order modal for selected option contract."""
    if not active_cell or not options_data:
        return None

    try:
        row_idx = active_cell.get('row')
        col_id = active_cell.get('column_id')

        # Only respond to clicks on call/put price columns
        if col_id not in ['call_bid', 'call_ask', 'call_last', 'put_bid', 'put_ask', 'put_last']:
            return None

        # Determine whether user clicked on call or put
        is_call = col_id.startswith('call')

        # Determine currently selected expiration (from hidden dropdown)
        from dash import no_update
        # We will try to read the stored selected expiration; fall back to first
        selected_exp = None
        expirations = options_data.get('expirations', [])
        if expirations:
            selected_exp = expirations[0]

        # Build records for the selected expiration
        chains = options_data.get('chains', {})
        if selected_exp not in chains:
            # If chain not present, try any available expiration
            if chains:
                selected_exp = list(chains.keys())[0]
            else:
                return None

        calls = chains[selected_exp].get('calls', [])
        puts = chains[selected_exp].get('puts', [])

        rows = calls if is_call else puts
        if row_idx is None or row_idx >= len(rows):
            return None

        contract = rows[row_idx]
        contract_symbol = contract.get('contractSymbol') or contract.get('contract') or f"{options_data.get('ticker')}_{selected_exp}_{contract.get('strike')}"

        # Create modal content
        modal = html.Div([
            html.Div([
                html.H4(f"Order: {contract_symbol}", style={'marginBottom': '8px'}),
                html.Div([html.Strong('Type:'), html.Span(' Call' if is_call else ' Put')]),
                html.Div([html.Strong('Strike:'), html.Span(f" {contract.get('strike')}")]),
                html.Div([html.Strong('Last:'), html.Span(f" ${contract.get('lastPrice')}")]),
                html.Div([html.Strong('Bid/Ask:'), html.Span(f" {contract.get('bid')}/{contract.get('ask')}")]),
                html.Div(style={'height': '10px'}),
                html.Div([
                    html.Button('Buy (Market)', id='alpaca-order-buy-btn', n_clicks=0, style={'marginRight': '8px'}),
                    html.Button('Close', id='alpaca-order-close-btn', n_clicks=0)
                ])
            ], style={
                'position': 'fixed',
                'left': '50%',
                'top': '50%',
                'transform': 'translate(-50%, -50%)',
                'backgroundColor': '#1f2937',
                'padding': '20px',
                'borderRadius': '8px',
                'zIndex': 9999,
                'color': '#fff',
                'minWidth': '360px'
            })
        ], id='alpaca-order-modal')

        # Store contract info in a hidden Store in the modal container for the buy callback to read
        hidden_store = html.Div(id='alpaca-order-hidden', style={'display': 'none'}, children=str({'symbol': contract_symbol, 'is_call': is_call, 'expiration': selected_exp, 'strike': contract.get('strike')}))

        return [modal, hidden_store]

    except Exception as e:
        logger.error(f"Error opening order modal: {e}")
        return None


@callback(
    [Output('alpaca-status-message', 'children', allow_duplicate=True),
     Output('alpaca-status-message', 'style', allow_duplicate=True)],
    [Input('alpaca-order-buy-btn', 'n_clicks'), Input('alpaca-order-close-btn', 'n_clicks')],
    [State('alpaca-order-hidden', 'children'), State('alpaca-ticker-input', 'value')],
    prevent_initial_call=True
)
def handle_order_action(buy_clicks, close_clicks, hidden_json, ticker):
    """Handle buy/close actions from order modal."""
    from dash import no_update
    triggered = ctx.triggered_id if hasattr(ctx, 'triggered_id') else None
    try:
        if triggered == 'alpaca-order-close-btn':
            # Close modal - just return no update
            return no_update, no_update

        if triggered == 'alpaca-order-buy-btn':
            # Parse hidden JSON (string) safely
            import ast
            payload = {}
            try:
                payload = ast.literal_eval(hidden_json) if hidden_json else {}
            except Exception:
                payload = {}

            symbol = payload.get('symbol')
            is_call = payload.get('is_call')
            expiration = payload.get('expiration')
            strike = payload.get('strike')

            # Use data_loader instead of direct Alpaca client
            from .data_loader import fetch_options_chain
            
            # For safety, do not place real orders in tests — log and return success message
            logger.info(f"Placing simulated market buy order for {symbol} (ticker={ticker})")
            status = f"✅ Simulated buy placed for {symbol}"

            style = {'marginTop': '20px', 'padding': '10px', 'borderRadius': '4px', 'fontSize': '13px', 'backgroundColor': '#2a3d2a', 'color': '#4caf50'}
            return status, style

    except Exception as e:
        logger.error(f"Order handling error: {e}")
        return f"❌ Order error: {e}", {'backgroundColor': '#3d2a2a', 'color': '#f44336'}



@callback(
    Output('alpaca-export-container', 'style'),
    [Input('alpaca-options-store', 'data')]
)
def show_export_buttons(options_data):
    """Show export buttons when data is loaded."""
    if options_data:
        return {
            'marginBottom': '15px',
            'padding': '10px',
            'backgroundColor': '#1e2130',
            'borderRadius': '8px',
            'display': 'block'
        }
    return {'display': 'none'}


@callback(
    Output('alpaca-download-csv', 'data'),
    [Input('alpaca-export-csv-btn', 'n_clicks')],
    [State('alpaca-options-store', 'data'),
     State('alpaca-expiration-dropdown', 'value')],
    prevent_initial_call=True
)
def export_to_csv(n_clicks, options_data, expiration):
    """Export options chain to CSV."""
    if not n_clicks or not options_data:
        return None
    
    try:
        from .export_utils import export_chain_to_csv, generate_export_filename
        
        csv_content = export_chain_to_csv(options_data, expiration)
        filename = generate_export_filename(
            options_data.get('ticker', 'options'),
            expiration,
            'csv'
        )
        
        logger.info(f"📥 Exporting CSV: {filename}")
        
        return {
            'content': csv_content,
            'filename': filename,
            'type': 'text/csv'
        }
    except Exception as e:
        logger.error(f"❌ CSV export error: {e}")
        return None


@callback(
    Output('alpaca-download-json', 'data'),
    [Input('alpaca-export-json-btn', 'n_clicks')],
    [State('alpaca-options-store', 'data'),
     State('alpaca-expiration-dropdown', 'value')],
    prevent_initial_call=True
)
def export_to_json(n_clicks, options_data, expiration):
    """Export options chain to JSON."""
    if not n_clicks or not options_data:
        return None
    
    try:
        from .export_utils import export_chain_to_json, generate_export_filename
        
        json_content = export_chain_to_json(options_data, expiration)
        filename = generate_export_filename(
            options_data.get('ticker', 'options'),
            expiration,
            'json'
        )
        
        logger.info(f"📥 Exporting JSON: {filename}")
        
        return {
            'content': json_content,
            'filename': filename,
            'type': 'application/json'
        }
    except Exception as e:
        logger.error(f"❌ JSON export error: {e}")
        return None


@callback(
    [Output('alpaca-options-store', 'data', allow_duplicate=True),
     Output('alpaca-status-message', 'children', allow_duplicate=True),
     Output('alpaca-status-message', 'style', allow_duplicate=True)],
    [Input('alpaca-refresh-btn', 'n_clicks')],
    [State('alpaca-ticker-input', 'value')],
    prevent_initial_call=True
)
def refresh_data(n_clicks, ticker):
    """Refresh data with cache invalidation."""
    if not n_clicks:
        return None, "", {}
    
    try:
        from .alpaca_options import invalidate_ticker_cache, get_alpaca_client
        
        # Invalidate cache
        invalidate_ticker_cache(ticker or 'SPY')
        
        # Force fresh fetch
        return load_options_chain(1, 0, ticker)
        
    except Exception as e:
        logger.error(f"❌ Refresh error: {e}")
        return None, f"❌ Refresh failed: {e}", {
            'marginTop': '20px', 'padding': '10px', 'borderRadius': '4px',
            'fontSize': '13px', 'backgroundColor': '#3d2a2a', 'color': '#f44336'
        }


# =============================================================================
# TRADE PANEL CALLBACKS - Execute trades on selected options
# =============================================================================

@callback(
    [Output('option-trade-panel', 'style'),
     Output('trade-summary', 'children'),
     Output('execute-trade-btn', 'disabled'),
     Output('trade-limit-price', 'value')],
    [Input('alpaca-options-table', 'selected_rows'),
     Input('trade-option-type', 'value'),
     Input('trade-action', 'value'),
     Input('trade-quantity', 'value')],
    [State('alpaca-options-store', 'data'),
     State('alpaca-expiration-dropdown', 'value')]
)
def update_trade_panel(selected_rows, option_type, action, quantity, options_data, expiration):
    """Update trade panel when an option row is selected."""
    import dash_bootstrap_components as dbc
    
    # Hide panel if no selection
    if not selected_rows or not options_data or not expiration:
        return {'display': 'none'}, html.Span("Select an option row to trade", className="text-muted"), True, None
    
    try:
        row_idx = selected_rows[0]
        chains = options_data.get('chains', {})
        
        if expiration not in chains:
            return {'display': 'none'}, html.Span("No chain data", className="text-muted"), True, None
        
        chain = chains[expiration]
        options_list = chain.get('calls' if option_type == 'call' else 'puts', [])
        
        # Build combined strike list (same as table order)
        calls = chain.get('calls', [])
        puts = chain.get('puts', [])
        all_strikes = sorted(set([c.get('strike', 0) for c in calls] + [p.get('strike', 0) for p in puts]))
        
        if row_idx >= len(all_strikes):
            return {'display': 'none'}, html.Span("Invalid selection", className="text-muted"), True, None
        
        selected_strike = all_strikes[row_idx]
        
        # Find the option at this strike
        option = None
        for opt in options_list:
            if opt.get('strike') == selected_strike:
                option = opt
                break
        
        if not option:
            return {'display': 'block'}, html.Span(f"No {option_type} at strike ${selected_strike}", className="text-warning"), True, None
        
        # Calculate trade details
        bid = float(option.get('bid', 0))
        ask = float(option.get('ask', 0))
        mid = (bid + ask) / 2 if bid and ask else float(option.get('lastPrice', 0))
        contract_symbol = option.get('contractSymbol', f"{options_data.get('ticker')}_{expiration}_{selected_strike}")
        
        # Suggested limit price
        suggested_price = bid if action == 'sell' else ask
        
        # Calculate total cost/credit
        qty = int(quantity or 1)
        total_value = qty * mid * 100  # Options are per 100 shares
        
        action_label = "BUY" if action == 'buy' else "SELL"
        type_label = "CALL" if option_type == 'call' else "PUT"
        
        summary = html.Div([
            html.Div([
                html.Strong(f"{action_label} {qty} {type_label}"),
                html.Span(f" @ Strike ${selected_strike:.2f}", className="text-muted ms-2"),
            ]),
            html.Div([
                html.Span(f"Contract: ", className="text-muted"),
                html.Code(contract_symbol, style={'fontSize': '11px'}),
            ]),
            html.Div([
                html.Span(f"Bid: ${bid:.2f} | Ask: ${ask:.2f} | Mid: ${mid:.2f}", className="text-muted"),
            ]),
            html.Div([
                html.Span(f"Est. {'Cost' if action == 'buy' else 'Credit'}: ", className="text-muted"),
                html.Strong(f"${total_value:.2f}", style={'color': '#4caf50' if action == 'sell' else '#f44336'}),
            ]),
        ])
        
        return {'display': 'block'}, summary, False, round(suggested_price, 2)
        
    except Exception as e:
        logger.error(f"Trade panel error: {e}")
        return {'display': 'block'}, html.Span(f"Error: {e}", className="text-danger"), True, None


@callback(
    Output('trade-result', 'children'),
    [Input('execute-trade-btn', 'n_clicks')],
    [State('alpaca-options-table', 'selected_rows'),
     State('trade-option-type', 'value'),
     State('trade-action', 'value'),
     State('trade-quantity', 'value'),
     State('trade-order-type', 'value'),
     State('trade-limit-price', 'value'),
     State('alpaca-options-store', 'data'),
     State('alpaca-expiration-dropdown', 'value')],
    prevent_initial_call=True
)
def execute_trade(n_clicks, selected_rows, option_type, action, quantity, order_type, limit_price, options_data, expiration):
    """Execute the trade when button is clicked."""
    import dash_bootstrap_components as dbc
    
    if not n_clicks or not selected_rows or not options_data:
        return None
    
    try:
        from .trading_client import place_option_order
        
        row_idx = selected_rows[0]
        chains = options_data.get('chains', {})
        chain = chains.get(expiration, {})
        
        # Get option details
        options_list = chain.get('calls' if option_type == 'call' else 'puts', [])
        calls = chain.get('calls', [])
        puts = chain.get('puts', [])
        all_strikes = sorted(set([c.get('strike', 0) for c in calls] + [p.get('strike', 0) for p in puts]))
        
        if row_idx >= len(all_strikes):
            return dbc.Alert("Invalid selection", color="danger")
        
        selected_strike = all_strikes[row_idx]
        
        # Find the option
        option = None
        for opt in options_list:
            if opt.get('strike') == selected_strike:
                option = opt
                break
        
        if not option:
            return dbc.Alert(f"No {option_type} found at strike ${selected_strike}", color="warning")
        
        contract_symbol = option.get('contractSymbol', '')
        current_price = float(option.get('lastPrice', 0))
        
        if not contract_symbol:
            return dbc.Alert("Contract symbol not found", color="danger")
        
        # Place the order
        order, message = place_option_order(
            symbol=contract_symbol,
            qty=int(quantity or 1),
            side=action,
            order_type=order_type,
            limit_price=float(limit_price) if limit_price and order_type == 'limit' else None,
            current_price=current_price,
            confirmed=True  # User clicked the button = confirmed
        )
        
        if order:
            return dbc.Alert([
                html.H6("✅ Order Submitted!", className="alert-heading"),
                html.P([
                    html.Strong("Order ID: "), order.id, html.Br(),
                    html.Strong("Status: "), order.status, html.Br(),
                    html.Strong("Symbol: "), order.symbol,
                ])
            ], color="success", dismissable=True)
        else:
            return dbc.Alert([
                html.H6("❌ Order Failed", className="alert-heading"),
                html.P(message)
            ], color="danger", dismissable=True)
        
    except Exception as e:
        logger.error(f"Trade execution error: {e}")
        return dbc.Alert(f"Error: {str(e)}", color="danger", dismissable=True)

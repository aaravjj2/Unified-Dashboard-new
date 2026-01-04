from dash.dependencies import Input, Output, State
from dash import html
import dash_bootstrap_components as dbc
from src.ui.data_connector import connector
import pandas as pd

def register_phase3_extra_callbacks(app):

    # Populate strategy dropdowns on interval or startup
    @app.callback(
        Output('backtest-strategy-select', 'options'),
        [Input('backtest-pnl-graph', 'id')]
    )
    def populate_strategy_options(_):
        try:
            strategies = connector.list_strategies()
            options = []
            for s in strategies:
                options.append({'label': s.get('name', s.get('id')), 'value': s.get('id')})
            return options
        except Exception:
            return []


    @app.callback(
        Output('backtest-pnl-graph', 'figure'),
        [Input('backtest-strategy-select', 'value'), Input('backtest-date-range', 'start_date'), Input('backtest-date-range', 'end_date')]
    )
    def update_backtest_graph(strategy, start, end):
        # Minimal placeholder: return empty figure or sample
        import plotly.graph_objs as go
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1,2,3], y=[0,1,0], name='P&L'))
        fig.update_layout(title='Backtest P&L')
        return fig

    @app.callback(
        Output('backtest-trades-table', 'children'),
        [Input('backtest-strategy-select', 'value')]
    )
    def update_backtest_trades(strategy):
        return html.Div('No backtest loaded', className='text-muted p-2')

    @app.callback(
        Output('sb-preview', 'children'),
        [Input('sb-generate', 'n_clicks')],
        [State('sb-symbol','value'), State('sb-strategy-type','value')]
    )
    def generate_strategy(n, symbol, stype):
        if not n:
            return ''
        return html.Div([html.Strong('Preview:'), html.Div(f'Symbol={symbol}, Type={stype}')])

    @app.callback(
        Output('exec-result', 'children'),
        [Input('exec-place-order', 'n_clicks')],
        [State('exec-symbol','value'), State('exec-side','value'), State('exec-qty','value'), State('exec-price','value')]
    )
    def place_order(n, symbol, side, qty, price):
        if not n:
            return ''
        try:
            # Call backend endpoint to place order
            payload = {
                'contract': symbol or '',
                'side': side or 'buy',
                'quantity': int(qty or 1),
                'order_type': 'limit' if price else 'market',
                'limit_price': float(price) if price else None,
            }
            res = connector.place_order(payload)
            if res.get('error'):
                return dbc.Alert(f"Order failed: {res.get('error')}", color='danger')
            return dbc.Alert(f"Order submitted: {res.get('message', res)}", color='success')
        except Exception as e:
            return dbc.Alert(f'Error: {e}', color='danger')

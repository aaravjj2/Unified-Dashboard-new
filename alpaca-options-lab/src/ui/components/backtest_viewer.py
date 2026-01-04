from dash import html, dcc
import dash_bootstrap_components as dbc

def create_backtest_viewer():
    """Simple Backtest Viewer panel showing historical P&L and trades."""
    return dbc.Card([
        dbc.CardHeader("Backtest Viewer"),
        dbc.CardBody([
            html.Div("Select timeframe and strategy:", className="mb-2"),
            dcc.Dropdown(id='backtest-strategy-select', options=[], placeholder='Select strategy'),
            dcc.DatePickerRange(id='backtest-date-range', start_date_placeholder_text='Start', end_date_placeholder_text='End', className='mt-2'),
            dcc.Loading(dcc.Graph(id='backtest-pnl-graph'), type='default', className='mt-3'),
            html.Div(id='backtest-trades-table', className='mt-2')
        ])
    ], className='mb-3')

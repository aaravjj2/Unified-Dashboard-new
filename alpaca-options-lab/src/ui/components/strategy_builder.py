from dash import html, dcc
import dash_bootstrap_components as dbc

def create_strategy_builder():
    """Minimal interactive strategy builder (symbol, legs, DTE)."""
    return dbc.Card([
        dbc.CardHeader("Strategy Builder"),
        dbc.CardBody([
            html.Div([
                dcc.Input(id='sb-symbol', placeholder='Underlying symbol (e.g. SPY)', type='text'),
                dcc.Dropdown(id='sb-strategy-type', options=[{'label':'Iron Condor','value':'ic'},{'label':'Vertical Spread','value':'vs'}], placeholder='Select strategy', className='mt-2')
            ]),
            html.Div(id='sb-legs-editor', className='mt-2'),
            dbc.Button('Generate Orders', id='sb-generate', color='primary', className='mt-2'),
            html.Div(id='sb-preview', className='mt-2')
        ])
    ], className='mb-3')

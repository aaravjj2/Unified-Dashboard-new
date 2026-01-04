from dash import html, dcc
import dash_bootstrap_components as dbc

def create_execution_controls():
    """Order placement controls: symbol, side, qty, price, submit."""
    return dbc.Card([
        dbc.CardHeader("Execution Controls"),
        dbc.CardBody([
            dcc.Input(id='exec-symbol', placeholder='Symbol (SPY)', type='text'),
            dcc.Dropdown(id='exec-side', options=[{'label':'Buy','value':'buy'},{'label':'Sell','value':'sell'}], placeholder='Side', className='mt-2'),
            dcc.Input(id='exec-qty', placeholder='Quantity', type='number', className='mt-2'),
            dcc.Input(id='exec-price', placeholder='Limit Price (optional)', type='number', className='mt-2'),
            dbc.Button('Place Order', id='exec-place-order', color='success', className='mt-2'),
            html.Div(id='exec-result', className='mt-2')
        ])
    ], className='mb-3')

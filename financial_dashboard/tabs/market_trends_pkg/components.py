"""UI helper components for Market Trends (pure helpers)"""
from dash import html
import dash_bootstrap_components as dbc


def build_brief_card(title, summary):
    return dbc.Card([
        dbc.CardBody([
            html.H5(title, className='card-title'),
            html.P(summary, className='card-text')
        ])
    ])

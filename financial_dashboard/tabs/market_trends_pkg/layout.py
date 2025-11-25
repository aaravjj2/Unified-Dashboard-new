"""Pure layout builder for Market Trends (lazy, no heavy imports at module import time)"""
from dash import html
import dash_bootstrap_components as dbc

from .components import build_brief_card


def create_layout():
    """Return the Market Trends layout. Heavy data retrieval is done
    through functions in `data.py` and executed lazily inside this function.
    """
    return dbc.Container([
        html.H2('Market Trends'),
        html.Div(id='market-trends-main'),
        dbc.Spinner(html.Div(id='market-trends-spinner'))
    ], fluid=True)

"""
Minimal Market Trends with ONLY the Run Analysis button callback.
This tests if we can get callbacks working without the full file.
"""
from dash import html, Input, Output, State, no_update, callback_context
from dash.exceptions import PreventUpdate
import logging
import time

logger = logging.getLogger(__name__)

def layout():
    """Minimal layout with just Run Analysis button"""
    return html.Div([
        html.H3('Market Trends (Minimal Test)'),
        html.Button('Run Analysis', id='mt-run-analysis-btn', n_clicks=0),
        html.Div(id='status', children='Ready', style={'marginTop': 10}),
        html.Div(id='results-area', children='No results yet')
    ])

def register_callbacks(app):
    """Register ONLY the Run Analysis callback"""
    logger.critical("🔵 MINIMAL: Registering callbacks...")
    
    @app.callback(
        Output('status', 'children'),
        Output('results-area', 'children'),
        Input('mt-run-analysis-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def run_analysis(n_clicks):
        logger.critical(f"🚨 RUN ANALYSIS CLICKED! n_clicks={n_clicks}")
        
        if not n_clicks or n_clicks == 0:
            raise PreventUpdate
        
        # Simulate analysis
        time.sleep(1)
        
        status = f"Analysis complete! Clicked {n_clicks} times"
        results = html.Div([
            html.H4("Analysis Results"),
            html.P(f"Job executed at {time.strftime('%H:%M:%S')}")
        ])
        
        return status, results
    
    logger.critical("🔵 MINIMAL: Callback registered successfully!")

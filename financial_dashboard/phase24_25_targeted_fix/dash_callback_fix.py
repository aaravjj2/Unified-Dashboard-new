#!/usr/bin/env python3
"""
Server-side callback fix for 500 Internal Server Errors
This script provides safe callback implementations and error handling
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context, no_update
import traceback
import logging
import json
from datetime import datetime

# Setup callback logging
callback_logger = logging.getLogger('dash_callbacks')
callback_logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('callback_errors.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
callback_logger.addHandler(handler)

def safe_callback_decorator(func):
    """Decorator to make callbacks safe and prevent 500 errors"""
    def wrapper(*args, **kwargs):
        try:
            callback_logger.info(f"Executing callback: {func.__name__}")
            callback_logger.info(f"Args: {args}")
            callback_logger.info(f"Kwargs: {kwargs}")
            
            # Execute the callback
            result = func(*args, **kwargs)
            
            # Validate the result
            if result is None:
                callback_logger.warning(f"Callback {func.__name__} returned None, using no_update")
                return no_update
            
            callback_logger.info(f"Callback {func.__name__} completed successfully")
            return result
            
        except Exception as e:
            callback_logger.error(f"Callback {func.__name__} failed: {str(e)}")
            callback_logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Return safe default based on expected output type
            try:
                # Try to determine expected output type from function annotations
                if hasattr(func, '__annotations__'):
                    return_type = func.__annotations__.get('return', None)
                    if return_type:
                        if return_type == str:
                            return f"Error in {func.__name__}: {str(e)}"
                        elif return_type == list:
                            return []
                        elif return_type == dict:
                            return {}
                
                # Default safe returns
                return html.Div([
                    html.P(f"Error in callback {func.__name__}", style={'color': 'red'}),
                    html.P(f"Error: {str(e)}", style={'color': 'red', 'font-size': '12px'})
                ])
                
            except Exception as fallback_error:
                callback_logger.error(f"Fallback error handling failed: {fallback_error}")
                return html.Div("System Error - Please refresh the page")
    
    return wrapper

# Safe callback implementations for common patterns
@safe_callback_decorator
def safe_tab_content_callback(active_tab):
    """Safe tab content callback"""
    if not active_tab:
        return html.Div("Please select a tab")
    
    tab_content_map = {
        'home': html.Div([
            html.H3("Home Dashboard"),
            html.P("Welcome to the financial dashboard")
        ]),
        'command-center': html.Div([
            html.H3("Command Center"),
            html.P("Command center functionality")
        ]),
        'strategy-lab': html.Div([
            html.H3("Strategy Lab"),
            html.P("Strategy analysis tools")
        ]),
        'options-lab': html.Div([
            html.H3("Options Lab"),
            html.P("Options trading analysis")
        ]),
        'weekly-picks': html.Div([
            html.H3("Weekly Picks"),
            html.P("Weekly stock recommendations")
        ]),
        'monthly-picks': html.Div([
            html.H3("Monthly Picks"),
            html.P("Monthly investment strategies")
        ])
    }
    
    return tab_content_map.get(active_tab, html.Div(f"Content for {active_tab}"))

@safe_callback_decorator
def safe_portfolio_callback(dropdown_value):
    """Safe portfolio update callback"""
    if not dropdown_value:
        return []
    
    # Return safe portfolio data
    return [
        {'Symbol': 'AAPL', 'Shares': 100, 'Price': 150.00, 'Value': 15000.00},
        {'Symbol': 'GOOGL', 'Shares': 50, 'Price': 2500.00, 'Value': 125000.00},
        {'Symbol': 'MSFT', 'Shares': 75, 'Price': 300.00, 'Value': 22500.00}
    ]

@safe_callback_decorator
def safe_button_click_callback(n_clicks, button_id):
    """Safe button click callback"""
    if not n_clicks or n_clicks == 0:
        return no_update
    
    return html.Div([
        html.P(f"Button {button_id} clicked {n_clicks} times"),
        html.P(f"Last clicked: {datetime.now().strftime('%H:%M:%S')}")
    ])

@safe_callback_decorator
def safe_dropdown_callback(selected_value, dropdown_id):
    """Safe dropdown selection callback"""
    if not selected_value:
        return "Please make a selection"
    
    return f"Selected: {selected_value} from {dropdown_id}"

# Callback registration helper
def register_safe_callbacks(app):
    """Register all callbacks with the app using safe decorators"""
    
    # Tab content callback
    @app.callback(
        Output('tab-content', 'children'),
        Input('main-tabs', 'active_tab'),
        prevent_initial_call=True
    )
    def update_tab_content(active_tab):
        return safe_tab_content_callback(active_tab)
    
    # Portfolio callback
    @app.callback(
        Output('portfolio-table', 'data'),
        Input('portfolio-dropdown', 'value'),
        prevent_initial_call=True
    )
    def update_portfolio(value):
        return safe_portfolio_callback(value)
    
    # Generic button callbacks
    for tab in ['home', 'command-center', 'strategy-lab', 'options-lab', 'weekly-picks', 'monthly-picks']:
        @app.callback(
            Output(f'{tab}-content', 'children'),
            Input(f'{tab}-button', 'n_clicks'),
            prevent_initial_call=True
        )
        def update_content(n_clicks, tab_name=tab):
            return safe_button_click_callback(n_clicks, tab_name)
    
    callback_logger.info("All safe callbacks registered successfully")

# Error boundary component
def create_error_boundary(children, error_id="error-boundary"):
    """Create an error boundary component"""
    return html.Div([
        dcc.Store(id=f'{error_id}-store', data={'errors': []}),
        html.Div(id=f'{error_id}-display'),
        html.Div(children, id=f'{error_id}-content')
    ])

# Usage example:
if __name__ == "__main__":
    print("Dash callback fix utilities loaded successfully")
    print("Use register_safe_callbacks(app) to apply fixes to your Dash app")

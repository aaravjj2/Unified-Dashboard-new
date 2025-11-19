#!/usr/bin/env python3
"""
React Error #31 Fix: "Objects are not valid as a React child"
This error occurs when trying to render objects directly as React children
"""

import dash
from dash import dcc, html
import json

def safe_render_children(value):
    """Safely render any value as React children"""
    if value is None:
        return ""
    elif isinstance(value, (str, int, float, bool)):
        return str(value)
    elif isinstance(value, dict):
        # Convert dict to JSON string for display
        return html.Pre(json.dumps(value, indent=2, default=str))
    elif isinstance(value, list):
        # Handle list of values
        safe_items = []
        for item in value:
            if isinstance(item, (str, int, float, bool)):
                safe_items.append(html.Li(str(item)))
            elif isinstance(item, dict):
                safe_items.append(html.Li(html.Pre(json.dumps(item, indent=2, default=str))))
            else:
                safe_items.append(html.Li(str(item)))
        return html.Ul(safe_items)
    else:
        return str(value)

def safe_component_props(**props):
    """Ensure all component props are safe for React"""
    safe_props = {}
    
    for key, value in props.items():
        if key == 'children':
            safe_props[key] = safe_render_children(value)
        elif key in ['id', 'className', 'style']:
            # These should be strings or dicts
            safe_props[key] = value
        elif isinstance(value, (str, int, float, bool, type(None))):
            safe_props[key] = value
        else:
            # Convert complex objects to strings
            safe_props[key] = str(value)
    
    return safe_props

# Safe component wrappers
def SafeDiv(children=None, **kwargs):
    """Safe Div component that prevents React Error #31"""
    safe_props = safe_component_props(children=children, **kwargs)
    return html.Div(**safe_props)

def SafeP(children=None, **kwargs):
    """Safe P component"""
    safe_props = safe_component_props(children=children, **kwargs)
    return html.P(**safe_props)

def SafeSpan(children=None, **kwargs):
    """Safe Span component"""
    safe_props = safe_component_props(children=children, **kwargs)
    return html.Span(**safe_props)

def SafeH1(children=None, **kwargs):
    """Safe H1 component"""
    safe_props = safe_component_props(children=children, **kwargs)
    return html.H1(**safe_props)

def SafeH2(children=None, **kwargs):
    """Safe H2 component"""
    safe_props = safe_component_props(children=children, **kwargs)
    return html.H2(**safe_props)

def SafeH3(children=None, **kwargs):
    """Safe H3 component"""
    safe_props = safe_component_props(children=children, **kwargs)
    return html.H3(**safe_props)

def SafeButton(children=None, **kwargs):
    """Safe Button component"""
    safe_props = safe_component_props(children=children, **kwargs)
    return html.Button(**safe_props)

def SafeTable(data=None, **kwargs):
    """Safe table component that handles data properly"""
    if not data:
        return SafeDiv("No data available")
    
    try:
        if isinstance(data, list) and len(data) > 0:
            # Create table from list of dicts
            if isinstance(data[0], dict):
                headers = list(data[0].keys())
                header_row = html.Tr([html.Th(safe_render_children(h)) for h in headers])
                
                rows = []
                for row_data in data:
                    cells = [html.Td(safe_render_children(row_data.get(h, ""))) for h in headers]
                    rows.append(html.Tr(cells))
                
                return html.Table([
                    html.Thead(header_row),
                    html.Tbody(rows)
                ], **kwargs)
        
        # Fallback to simple display
        return SafeDiv(safe_render_children(data))
        
    except Exception as e:
        return SafeDiv(f"Error displaying table: {str(e)}")

# Component validation
def validate_component_tree(component):
    """Validate component tree to prevent React Error #31"""
    if component is None:
        return SafeDiv("")
    
    if isinstance(component, (str, int, float, bool)):
        return component
    
    if isinstance(component, dict):
        # This is likely the source of React Error #31
        if 'props' in component and 'type' in component:
            # This looks like a React element object - convert to safe format
            return SafeDiv(f"Component: {component.get('type', 'Unknown')}")
        else:
            # Regular dict - convert to JSON display
            return html.Pre(json.dumps(component, indent=2, default=str))
    
    if isinstance(component, list):
        # Validate each item in the list
        safe_items = []
        for item in component:
            safe_items.append(validate_component_tree(item))
        return safe_items
    
    # For other objects, convert to string
    return str(component)

# Layout validation helper
def create_safe_layout(layout_func):
    """Wrapper to create safe layouts"""
    def safe_layout(*args, **kwargs):
        try:
            layout = layout_func(*args, **kwargs)
            return validate_component_tree(layout)
        except Exception as e:
            return SafeDiv([
                SafeH3("Layout Error"),
                SafeP(f"Error creating layout: {str(e)}"),
                SafeP("Please check the layout function for React Error #31 issues")
            ])
    return safe_layout

# Example usage:
if __name__ == "__main__":
    print("React Error #31 fix utilities loaded")
    print("Use Safe* components instead of html.* components")
    print("Use validate_component_tree() to check for problematic objects")

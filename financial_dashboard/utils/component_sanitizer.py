"""
Component Sanitizer - Fixes React rendering errors
Sanitizes Dash components to ensure valid React children.
"""
import logging
from dash import html

logger = logging.getLogger(__name__)


def is_invalid_object(obj):
    """
    Detect invalid objects with {props, type, namespace} structure.
    
    These are raw Dash component objects that haven't been properly
    instantiated and will cause React error #31.
    
    Args:
        obj: Object to check
        
    Returns:
        bool: True if object is invalid for React rendering
    """
    if not isinstance(obj, dict):
        return False
    
    # Check for the telltale signs of a raw Dash component object
    has_props = 'props' in obj
    has_type = 'type' in obj
    has_namespace = 'namespace' in obj
    
    # If it has all three keys, it's likely a raw component object
    if has_props and has_type and has_namespace:
        logger.warning(f"Detected invalid component object: type={obj.get('type')}, namespace={obj.get('namespace')}")
        return True
    
    return False


def sanitize_component(component):
    """
    Sanitize a component to ensure valid React rendering.
    
    Converts invalid objects to valid Dash components.
    Recursively sanitizes nested structures.
    
    Args:
        component: Component or object to sanitize
        
    Returns:
        Sanitized component safe for React rendering
    """
    # Handle None
    if component is None:
        return None
    
    # Handle strings and numbers (valid React children)
    if isinstance(component, (str, int, float, bool)):
        return component
    
    # Handle lists (recursively sanitize each item)
    if isinstance(component, list):
        return [sanitize_component(item) for item in component]
    
    # Handle tuples (convert to list and sanitize)
    if isinstance(component, tuple):
        return [sanitize_component(item) for item in component]
    
    # Check if it's an invalid object
    if is_invalid_object(component):
        # Convert to a safe placeholder
        comp_type = component.get('type', 'Unknown')
        comp_namespace = component.get('namespace', 'unknown')
        logger.warning(f"Sanitizing invalid component: {comp_namespace}.{comp_type}")
        
        return html.Div([
            html.P(f"[Component: {comp_namespace}.{comp_type}]", 
                   style={'color': '#ff6b6b', 'fontStyle': 'italic'})
        ])
    
    # Handle Dash components (they have a _type attribute)
    if hasattr(component, '_type'):
        # It's a proper Dash component, check its children
        if hasattr(component, 'children'):
            # Recursively sanitize children
            component.children = sanitize_children(component.children)
        return component
    
    # Handle dictionaries (might be component props)
    if isinstance(component, dict):
        # Recursively sanitize dictionary values
        sanitized = {}
        for key, value in component.items():
            if key == 'children':
                sanitized[key] = sanitize_children(value)
            else:
                sanitized[key] = sanitize_component(value)
        return sanitized
    
    # For anything else, return as-is
    return component


def sanitize_children(children):
    """
    Sanitize component children.
    
    Handles various children formats:
    - None
    - Single component
    - List of components
    - Nested structures
    
    Args:
        children: Children to sanitize
        
    Returns:
        Sanitized children safe for React rendering
    """
    if children is None:
        return None
    
    # Handle single component
    if not isinstance(children, (list, tuple)):
        return sanitize_component(children)
    
    # Handle list/tuple of components
    sanitized = []
    for child in children:
        sanitized_child = sanitize_component(child)
        if sanitized_child is not None:
            sanitized.append(sanitized_child)
    
    return sanitized


def sanitize_layout(layout):
    """
    Sanitize an entire layout structure.
    
    This is the main entry point for layout sanitization.
    Call this on your app.layout before setting it.
    
    Args:
        layout: Layout structure to sanitize
        
    Returns:
        Sanitized layout safe for React rendering
    """
    logger.info("Sanitizing layout...")
    
    try:
        sanitized = sanitize_component(layout)
        logger.info("✅ Layout sanitization complete")
        return sanitized
    except Exception as e:
        logger.error(f"❌ Layout sanitization failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Return a safe fallback layout
        return html.Div([
            html.H1("Dashboard Loading Error"),
            html.P(f"Layout sanitization failed: {str(e)}"),
            html.P("Please check the logs for details.")
        ])

"""
Enhanced Tooltip System - Week 2 Implementation
================================================
Provides consistent, accessible tooltips with rich content.

Features:
- 300ms delay for consistent UX
- Rich formatted content support
- Keyboard accessible (focus/blur)
- Multiple placement options
- Dark theme styling
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
from typing import Union, Literal, Optional, List, Dict

# =============================================================================
# TOOLTIP STYLES
# =============================================================================

TOOLTIP_STYLE = {
    "backgroundColor": "#161B22",
    "color": "#E6EDF3",
    "border": "1px solid #30363D",
    "borderRadius": "6px",
    "padding": "8px 12px",
    "fontSize": "13px",
    "fontWeight": "400",
    "lineHeight": "1.5",
    "maxWidth": "300px",
    "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.4)",
    "zIndex": "10000",
}

TOOLTIP_DELAY = {"show": 300, "hide": 100}  # 300ms show delay for consistency

# =============================================================================
# BASIC TOOLTIP
# =============================================================================

def create_tooltip(
    target_id: str,
    content: Union[str, html.Div],
    placement: Literal["top", "bottom", "left", "right", "auto"] = "top",
    delay: Optional[Dict[str, int]] = None
) -> dbc.Tooltip:
    """
    Create a basic tooltip with consistent styling.
    
    Args:
        target_id: ID of the element to attach tooltip to
        content: Text or HTML content for the tooltip
        placement: Where to position the tooltip
        delay: Custom show/hide delays (default: 300ms/100ms)
    
    Returns:
        dbc.Tooltip component
    """
    return dbc.Tooltip(
        content,
        target=target_id,
        placement=placement,
        delay=delay or TOOLTIP_DELAY,
        style=TOOLTIP_STYLE,
        **{'data-test-id': f'tooltip-{target_id}'}
    )


# =============================================================================
# RICH TOOLTIP
# =============================================================================

def create_rich_tooltip(
    target_id: str,
    title: str,
    description: str,
    metrics: Optional[List[Dict[str, str]]] = None,
    placement: Literal["top", "bottom", "left", "right", "auto"] = "top"
) -> dbc.Tooltip:
    """
    Create a rich tooltip with formatted content (title, description, metrics).
    
    Args:
        target_id: ID of the element to attach tooltip to
        title: Bold title text
        description: Secondary description text
        metrics: List of {"label": str, "value": str} dicts for key metrics
        placement: Where to position the tooltip
    
    Example:
        create_rich_tooltip(
            "delta-metric",
            "Portfolio Delta",
            "Measures directional exposure",
            metrics=[
                {"label": "Current", "value": "-125"},
                {"label": "Target", "value": "0"},
            ]
        )
    """
    content = []
    
    # Title
    content.append(
        html.Div(
            title,
            style={
                "fontWeight": "600",
                "fontSize": "14px",
                "marginBottom": "6px",
                "color": "#F5C211",  # Alpaca gold for titles
            }
        )
    )
    
    # Description
    content.append(
        html.Div(
            description,
            style={
                "fontSize": "12px",
                "color": "#8B949E",
                "marginBottom": "8px" if metrics else "0",
                "lineHeight": "1.4",
            }
        )
    )
    
    # Metrics (if provided)
    if metrics:
        metric_rows = []
        for metric in metrics:
            metric_rows.append(
                html.Div([
                    html.Span(
                        f"{metric['label']}: ",
                        style={"color": "#8B949E", "fontSize": "11px"}
                    ),
                    html.Span(
                        metric['value'],
                        style={"color": "#E6EDF3", "fontSize": "11px", "fontWeight": "600"}
                    ),
                ], style={"marginBottom": "2px"})
            )
        
        content.append(
            html.Div(
                metric_rows,
                style={
                    "borderTop": "1px solid #30363D",
                    "paddingTop": "6px",
                }
            )
        )
    
    return dbc.Tooltip(
        html.Div(content),
        target=target_id,
        placement=placement,
        delay=TOOLTIP_DELAY,
        style={**TOOLTIP_STYLE, "maxWidth": "350px"},
        **{'data-test-id': f'rich-tooltip-{target_id}'}
    )


# =============================================================================
# GREEKS TOOLTIP
# =============================================================================

def create_greeks_tooltip(
    target_id: str,
    greek_name: str,
    value: str,
    interpretation: str
) -> dbc.Tooltip:
    """
    Create a specialized tooltip for option Greeks.
    
    Args:
        target_id: ID of the Greek metric element
        greek_name: Name of the Greek (Delta, Gamma, etc.)
        value: Current value
        interpretation: What the value means
    """
    greek_symbols = {
        "Delta": "Δ",
        "Gamma": "Γ",
        "Theta": "Θ",
        "Vega": "ν",
        "Rho": "ρ",
    }
    
    symbol = greek_symbols.get(greek_name, greek_name[0])
    
    content = html.Div([
        # Greek symbol and name
        html.Div([
            html.Span(
                symbol,
                style={
                    "fontSize": "24px",
                    "fontWeight": "700",
                    "color": "#F5C211",
                    "marginRight": "8px",
                }
            ),
            html.Span(
                greek_name,
                style={
                    "fontSize": "16px",
                    "fontWeight": "600",
                    "color": "#E6EDF3",
                }
            ),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "8px"}),
        
        # Current value
        html.Div([
            html.Span("Value: ", style={"color": "#8B949E", "fontSize": "12px"}),
            html.Span(value, style={"color": "#E6EDF3", "fontSize": "14px", "fontWeight": "600"}),
        ], style={"marginBottom": "8px"}),
        
        # Interpretation
        html.Div(
            interpretation,
            style={
                "fontSize": "11px",
                "color": "#8B949E",
                "lineHeight": "1.4",
                "borderTop": "1px solid #30363D",
                "paddingTop": "6px",
            }
        ),
    ])
    
    return dbc.Tooltip(
        content,
        target=target_id,
        placement="top",
        delay=TOOLTIP_DELAY,
        style={**TOOLTIP_STYLE, "maxWidth": "280px"},
        **{'data-test-id': f'greek-tooltip-{target_id}'}
    )


# =============================================================================
# KEYBOARD SHORTCUT TOOLTIP
# =============================================================================

def create_shortcut_tooltip(
    target_id: str,
    action: str,
    shortcut_keys: List[str]
) -> dbc.Tooltip:
    """
    Create a tooltip showing keyboard shortcut for an action.
    
    Args:
        target_id: ID of the button/element
        action: What the shortcut does
        shortcut_keys: List of keys (e.g., ["Cmd", "K"])
    """
    # Format shortcut keys with styling
    key_elements = []
    for i, key in enumerate(shortcut_keys):
        key_elements.append(
            html.Span(
                key,
                style={
                    "backgroundColor": "#30363D",
                    "color": "#E6EDF3",
                    "padding": "2px 6px",
                    "borderRadius": "4px",
                    "fontSize": "11px",
                    "fontWeight": "600",
                    "border": "1px solid #6E7681",
                    "fontFamily": "'SF Mono', 'Consolas', monospace",
                }
            )
        )
        if i < len(shortcut_keys) - 1:
            key_elements.append(
                html.Span(" + ", style={"color": "#8B949E", "margin": "0 4px"})
            )
    
    content = html.Div([
        html.Div(
            action,
            style={
                "color": "#E6EDF3",
                "fontSize": "12px",
                "marginBottom": "6px",
            }
        ),
        html.Div(
            key_elements,
            style={"display": "flex", "alignItems": "center"}
        ),
    ])
    
    return dbc.Tooltip(
        content,
        target=target_id,
        placement="bottom",
        delay=TOOLTIP_DELAY,
        style=TOOLTIP_STYLE,
        **{'data-test-id': f'shortcut-tooltip-{target_id}'}
    )


# =============================================================================
# HELPER: ADD TOOLTIP TO COMPONENT
# =============================================================================

def with_tooltip(
    component: html.Div,
    tooltip_content: Union[str, html.Div],
    component_id: Optional[str] = None,
    placement: str = "top"
) -> html.Div:
    """
    Wrap a component with a tooltip.
    
    Args:
        component: The Dash component to add tooltip to
        tooltip_content: Tooltip text or HTML
        component_id: ID for the component (generated if None)
        placement: Tooltip placement
    
    Returns:
        Wrapped component with tooltip
    """
    import uuid
    
    # Generate ID if not provided
    if component_id is None:
        component_id = f"tooltip-target-{uuid.uuid4().hex[:8]}"
    
    # Add ID to component if it doesn't have one
    if not hasattr(component, 'id') or component.id is None:
        component.id = component_id
    
    return html.Div([
        component,
        create_tooltip(component_id, tooltip_content, placement=placement)
    ])


# =============================================================================
# ACCESSIBILITY ENHANCEMENTS
# =============================================================================

def create_accessible_tooltip(
    target_id: str,
    content: str,
    placement: str = "top"
) -> html.Div:
    """
    Create tooltip with full accessibility support (ARIA, keyboard navigation).
    
    Adds:
    - aria-describedby on target
    - Role="tooltip" on tooltip
    - Keyboard show/hide on focus/blur
    """
    return html.Div([
        dbc.Tooltip(
            content,
            target=target_id,
            placement=placement,
            delay=TOOLTIP_DELAY,
            style=TOOLTIP_STYLE,
            **{
                'data-test-id': f'accessible-tooltip-{target_id}',
                'role': 'tooltip',
                'aria-hidden': 'true',
            }
        ),
        # Hidden live region for screen readers
        html.Div(
            content,
            role="status",
            aria_live="polite",
            style={"position": "absolute", "left": "-10000px", "width": "1px", "height": "1px"}
        )
    ])


# =============================================================================
# TOOLTIP PRESETS
# =============================================================================

TOOLTIP_PRESETS = {
    "refresh": lambda target: create_shortcut_tooltip(
        target,
        "Refresh Data",
        ["R"]
    ),
    "save": lambda target: create_shortcut_tooltip(
        target,
        "Save Configuration",
        ["Cmd", "S"]
    ),
    "search": lambda target: create_shortcut_tooltip(
        target,
        "Quick Search",
        ["Cmd", "K"]
    ),
    "delta": lambda target: create_greeks_tooltip(
        target,
        "Delta",
        "Portfolio delta exposure",
        "Measures sensitivity to $1 move in underlying. +100 delta ≈ long 100 shares."
    ),
    "theta": lambda target: create_greeks_tooltip(
        target,
        "Theta",
        "Daily time decay",
        "Amount your position loses per day due to time decay. Negative theta means you pay decay."
    ),
}


def get_preset_tooltip(preset_name: str, target_id: str) -> dbc.Tooltip:
    """Get a pre-configured tooltip by name."""
    if preset_name in TOOLTIP_PRESETS:
        return TOOLTIP_PRESETS[preset_name](target_id)
    else:
        raise ValueError(f"Unknown tooltip preset: {preset_name}")

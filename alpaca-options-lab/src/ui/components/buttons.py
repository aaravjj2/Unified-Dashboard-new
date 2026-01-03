"""
Enhanced Button System - Week 2 Implementation
===============================================
Provides consistent button styles with smooth hover/active states.

Features:
- 200ms transitions for all state changes
- Clear visual feedback for hover/active/disabled
- Multiple variants (primary, secondary, success, danger)
- Icon support
- Loading states
- Keyboard accessible
"""

from dash import html
import dash_bootstrap_components as dbc
from typing import Literal, Optional, Callable

# =============================================================================
# BUTTON STYLE CONSTANTS
# =============================================================================

TRANSITION = "all 0.2s ease"  # 200ms smooth transitions

BUTTON_BASE_STYLE = {
    "border": "none",
    "borderRadius": "6px",
    "padding": "10px 20px",
    "fontSize": "14px",
    "fontWeight": "600",
    "cursor": "pointer",
    "transition": TRANSITION,
    "display": "inline-flex",
    "alignItems": "center",
    "justifyContent": "center",
    "gap": "8px",
    "outline": "none",
    "textDecoration": "none",
    "userSelect": "none",
}

# Button variants with hover/active states
BUTTON_VARIANTS = {
    "primary": {
        "default": {
            "backgroundColor": "#F5C211",  # Alpaca gold
            "color": "#0D1117",
            "boxShadow": "0 1px 3px rgba(0, 0, 0, 0.2)",
        },
        "hover": {
            "backgroundColor": "#FFD54F",  # Lighter gold
            "transform": "translateY(-1px)",
            "boxShadow": "0 4px 8px rgba(245, 194, 17, 0.3)",
        },
        "active": {
            "backgroundColor": "#C9A000",  # Darker gold
            "transform": "translateY(0)",
            "boxShadow": "0 1px 2px rgba(0, 0, 0, 0.3)",
        },
        "disabled": {
            "backgroundColor": "#6E7681",
            "color": "#30363D",
            "cursor": "not-allowed",
            "opacity": "0.5",
        }
    },
    "secondary": {
        "default": {
            "backgroundColor": "#21262D",
            "color": "#E6EDF3",
            "border": "1px solid #30363D",
        },
        "hover": {
            "backgroundColor": "#30363D",
            "borderColor": "#8B949E",
            "transform": "translateY(-1px)",
        },
        "active": {
            "backgroundColor": "#161B22",
            "transform": "translateY(0)",
        },
        "disabled": {
            "backgroundColor": "#161B22",
            "color": "#6E7681",
            "cursor": "not-allowed",
            "opacity": "0.5",
        }
    },
    "success": {
        "default": {
            "backgroundColor": "#3FB950",
            "color": "#FFFFFF",
            "boxShadow": "0 1px 3px rgba(0, 0, 0, 0.2)",
        },
        "hover": {
            "backgroundColor": "#56D364",
            "transform": "translateY(-1px)",
            "boxShadow": "0 4px 8px rgba(63, 185, 80, 0.3)",
        },
        "active": {
            "backgroundColor": "#2EA043",
            "transform": "translateY(0)",
        },
        "disabled": {
            "backgroundColor": "#6E7681",
            "color": "#30363D",
            "cursor": "not-allowed",
            "opacity": "0.5",
        }
    },
    "danger": {
        "default": {
            "backgroundColor": "#F85149",
            "color": "#FFFFFF",
            "boxShadow": "0 1px 3px rgba(0, 0, 0, 0.2)",
        },
        "hover": {
            "backgroundColor": "#FF6B6B",
            "transform": "translateY(-1px)",
            "boxShadow": "0 4px 8px rgba(248, 81, 73, 0.3)",
        },
        "active": {
            "backgroundColor": "#D73A49",
            "transform": "translateY(0)",
        },
        "disabled": {
            "backgroundColor": "#6E7681",
            "color": "#30363D",
            "cursor": "not-allowed",
            "opacity": "0.5",
        }
    },
    "ghost": {
        "default": {
            "backgroundColor": "transparent",
            "color": "#E6EDF3",
        },
        "hover": {
            "backgroundColor": "rgba(255, 255, 255, 0.05)",
        },
        "active": {
            "backgroundColor": "rgba(255, 255, 255, 0.02)",
        },
        "disabled": {
            "color": "#6E7681",
            "cursor": "not-allowed",
            "opacity": "0.5",
        }
    },
}

# Size variants
BUTTON_SIZES = {
    "sm": {
        "padding": "6px 12px",
        "fontSize": "12px",
    },
    "md": {
        "padding": "10px 20px",
        "fontSize": "14px",
    },
    "lg": {
        "padding": "14px 28px",
        "fontSize": "16px",
    },
}

# =============================================================================
# ENHANCED BUTTON COMPONENT
# =============================================================================

def create_button(
    button_id: str,
    text: str,
    variant: Literal["primary", "secondary", "success", "danger", "ghost"] = "primary",
    size: Literal["sm", "md", "lg"] = "md",
    icon: Optional[str] = None,
    icon_position: Literal["left", "right"] = "left",
    disabled: bool = False,
    loading: bool = False,
    full_width: bool = False,
    on_click: Optional[Callable] = None,
    href: Optional[str] = None,
    **kwargs
) -> dbc.Button:
    """
    Create an enhanced button with smooth hover/active states.
    
    Args:
        button_id: Unique ID for the button
        text: Button label text
        variant: Visual style variant
        size: Button size
        icon: Optional icon (emoji or unicode)
        icon_position: Position of icon relative to text
        disabled: Whether button is disabled
        loading: Show loading spinner
        full_width: Make button full width
        on_click: Click handler (optional)
        href: Link URL (makes button act as link)
        **kwargs: Additional props
    
    Returns:
        dbc.Button component
    """
    # Get base styles
    base_style = {**BUTTON_BASE_STYLE}
    base_style.update(BUTTON_SIZES[size])
    base_style.update(BUTTON_VARIANTS[variant]["default" if not disabled else "disabled"])
    
    if full_width:
        base_style["width"] = "100%"
    
    # Build button content
    content = []
    
    if loading:
        content.append(
            dbc.Spinner(
                size="sm",
                color="light" if variant in ["primary", "success", "danger"] else "secondary",
                **{'data-test-id': f'{button_id}-spinner'}
            )
        )
    elif icon:
        icon_elem = html.Span(icon, style={"fontSize": "16px"})
        if icon_position == "left":
            content.append(icon_elem)
            content.append(text)
        else:
            content.append(text)
            content.append(icon_elem)
    else:
        content.append(text)
    
    # Create button
    # Add alpaca-btn-{variant} class
    existing_class = kwargs.pop("className", "")
    class_name = f"alpaca-btn-{variant} {existing_class}".strip()

    button = dbc.Button(
        content,
        id=button_id,
        color=None,  # We use custom styles
        style=base_style,
        className=class_name,
        disabled=disabled or loading,
        href=href,
        n_clicks=0,
        **kwargs
    )
    
    return button


# =============================================================================
# BUTTON GROUP
# =============================================================================

def create_button_group(
    buttons: list,
    spacing: str = "8px"
) -> html.Div:
    """
    Create a horizontal group of buttons with consistent spacing.
    
    Args:
        buttons: List of button components
        spacing: Space between buttons
    
    Returns:
        html.Div containing button group
    """
    return html.Div(
        buttons,
        style={
            "display": "flex",
            "gap": spacing,
            "alignItems": "center",
        },
        **{'data-test-id': 'button-group'}
    )


# =============================================================================
# ICON BUTTON
# =============================================================================

def create_icon_button(
    button_id: str,
    icon: str,
    variant: Literal["primary", "secondary", "success", "danger", "ghost"] = "ghost",
    size: Literal["sm", "md", "lg"] = "md",
    disabled: bool = False,
    tooltip: Optional[str] = None,
    **kwargs
) -> html.Div:
    """
    Create a square icon-only button.
    
    Args:
        button_id: Unique ID
        icon: Icon character (emoji or unicode)
        variant: Style variant
        size: Button size
        disabled: Whether disabled
        tooltip: Optional tooltip text
        **kwargs: Additional props
    
    Returns:
        Icon button (wrapped with tooltip if provided)
    """
    size_map = {
        "sm": {"width": "32px", "height": "32px", "fontSize": "14px"},
        "md": {"width": "40px", "height": "40px", "fontSize": "18px"},
        "lg": {"width": "48px", "height": "48px", "fontSize": "22px"},
    }
    
    base_style = {**BUTTON_BASE_STYLE}
    base_style.update(size_map[size])
    base_style.update(BUTTON_VARIANTS[variant]["default" if not disabled else "disabled"])
    base_style["padding"] = "0"
    base_style["borderRadius"] = "8px"
    
    button = dbc.Button(
        icon,
        id=button_id,
        color=None,
        style=base_style,
        disabled=disabled,
        n_clicks=0,
        **{'data-test-id': button_id},
        **kwargs
    )
    
    if tooltip:
        from .tooltips import with_tooltip
        return with_tooltip(button, tooltip, component_id=button_id)
    
    return button


# =============================================================================
# TOGGLE BUTTON
# =============================================================================

def create_toggle_button(
    button_id: str,
    label: str,
    is_active: bool = False,
    active_variant: str = "primary",
    inactive_variant: str = "secondary",
    **kwargs
) -> dbc.Button:
    """
    Create a toggle button (on/off state).
    
    Args:
        button_id: Unique ID
        label: Button label
        is_active: Initial state
        active_variant: Style when active
        inactive_variant: Style when inactive
        **kwargs: Additional props
    
    Returns:
        Toggle button component
    """
    variant = active_variant if is_active else inactive_variant
    
    return create_button(
        button_id=button_id,
        text=label,
        variant=variant,
        **kwargs
    )


# =============================================================================
# CSS FOR HOVER/ACTIVE STATES
# =============================================================================

def inject_button_css() -> html.Div:
    """
    Inject CSS for button hover and active states.
    DEPRECATED: CSS is now loaded from assets/alpaca_ui.css
    """
    return html.Div(style={"display": "none"})

def _unused_inject_button_css():
    """Legacy implementation kept for reference."""
    pass


# =============================================================================
# BUTTON WITH CONFIRMATION
# =============================================================================

def create_confirm_button(
    button_id: str,
    text: str,
    confirm_text: str = "Are you sure?",
    variant: str = "danger",
    **kwargs
) -> html.Div:
    """
    Create a button that requires confirmation before action.
    
    Returns a button wrapped with a confirmation modal.
    """
    return html.Div([
        create_button(
            button_id=f"{button_id}-trigger",
            text=text,
            variant=variant,
            **kwargs
        ),
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Confirmation")),
            dbc.ModalBody(confirm_text),
            dbc.ModalFooter([
                create_button(
                    button_id=f"{button_id}-cancel",
                    text="Cancel",
                    variant="secondary",
                    size="sm"
                ),
                create_button(
                    button_id=button_id,
                    text="Confirm",
                    variant=variant,
                    size="sm"
                ),
            ]),
        ], id=f"{button_id}-modal", is_open=False)
    ])


# =============================================================================
# SPLIT BUTTON (ACTION + DROPDOWN)
# =============================================================================

def create_split_button(
    button_id: str,
    main_text: str,
    main_variant: str = "primary",
    dropdown_items: list = None,
    **kwargs
) -> html.Div:
    """
    Create a split button with main action + dropdown menu.
    
    Args:
        button_id: Unique ID prefix
        main_text: Text for main button
        main_variant: Style for main button
        dropdown_items: List of dropdown menu items
        **kwargs: Additional props
    
    Returns:
        Split button component
    """
    dropdown_items = dropdown_items or []
    
    return html.Div([
        create_button(
            button_id=f"{button_id}-main",
            text=main_text,
            variant=main_variant,
            **kwargs
        ),
        dbc.DropdownMenu(
            children=[
                dbc.DropdownMenuItem(item["label"], id=item["id"])
                for item in dropdown_items
            ],
            label="▼",
            color=main_variant,
            size="sm",
            style={"marginLeft": "2px"}
        ),
    ], style={
        "display": "inline-flex",
        "gap": "2px",
    }, **{'data-test-id': f'{button_id}-split-button'})

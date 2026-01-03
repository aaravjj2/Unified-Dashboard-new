"""
Loading States & Skeleton Screens - Week 2 Implementation
===========================================================
Provides consistent loading experiences across all workspaces.

Features:
- Skeleton screens with shimmer effects
- Unified loading spinners
- Progress indicators
- Lazy loading utilities
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
from typing import Literal, Optional

# =============================================================================
# STYLING CONSTANTS
# =============================================================================

SHIMMER_KEYFRAMES = """
@keyframes shimmer {
    0% { background-position: -1000px 0; }
    100% { background-position: 1000px 0; }
}
"""

SKELETON_BASE_STYLE = {
    "backgroundColor": "#21262D",
    "background": "linear-gradient(90deg, #21262D 25%, #30363D 50%, #21262D 75%)",
    "backgroundSize": "1000px 100%",
    "animation": "shimmer 2s infinite",
    "borderRadius": "8px",
}

SPINNER_STYLE = {
    "display": "flex",
    "justifyContent": "center",
    "alignItems": "center",
    "minHeight": "200px",
}

# =============================================================================
# SKELETON COMPONENTS
# =============================================================================

def create_skeleton_card(
    height: str = "200px",
    width: str = "100%",
    margin_bottom: str = "16px"
) -> html.Div:
    """Create a skeleton placeholder card with shimmer effect."""
    return html.Div(
        className="skeleton-card",
        **{'data-test-id': 'skeleton-loading'},
        style={
            **SKELETON_BASE_STYLE,
            "height": height,
            "width": width,
            "marginBottom": margin_bottom,
        }
    )


def create_skeleton_text(
    lines: int = 3,
    line_height: str = "16px",
    last_line_width: str = "60%"
) -> html.Div:
    """Create skeleton text lines."""
    elements = []
    for i in range(lines):
        is_last = i == lines - 1
        width = last_line_width if is_last else "100%"
        
        elements.append(
            html.Div(
                style={
                    **SKELETON_BASE_STYLE,
                    "height": line_height,
                    "width": width,
                    "marginBottom": "8px",
                }
            )
        )
    
    return html.Div(elements)


def create_skeleton_gauge() -> html.Div:
    """Create skeleton placeholder for hype gauge."""
    return html.Div([
        # Symbol header
        html.Div(
            style={
                **SKELETON_BASE_STYLE,
                "height": "24px",
                "width": "80px",
                "marginBottom": "12px",
            }
        ),
        # Gauge circle
        html.Div(
            style={
                **SKELETON_BASE_STYLE,
                "height": "120px",
                "width": "120px",
                "borderRadius": "50%",
                "margin": "0 auto 12px auto",
            }
        ),
        # Metrics
        html.Div([
            html.Div(
                style={
                    **SKELETON_BASE_STYLE,
                    "height": "14px",
                    "width": "60px",
                    "marginBottom": "4px",
                }
            ),
            html.Div(
                style={
                    **SKELETON_BASE_STYLE,
                    "height": "14px",
                    "width": "80px",
                }
            ),
        ], style={"textAlign": "center"})
    ], **{'data-test-id': 'skeleton-gauge'})


def create_skeleton_chart(height: str = "400px") -> html.Div:
    """Create skeleton placeholder for charts."""
    return html.Div([
        # Chart title
        html.Div(
            style={
                **SKELETON_BASE_STYLE,
                "height": "20px",
                "width": "200px",
                "marginBottom": "16px",
            }
        ),
        # Chart area
        html.Div(
            style={
                **SKELETON_BASE_STYLE,
                "height": height,
                "width": "100%",
            }
        ),
    ], **{'data-test-id': 'skeleton-chart'})


def create_skeleton_table(rows: int = 5) -> html.Div:
    """Create skeleton placeholder for tables."""
    header = html.Div(
        style={
            **SKELETON_BASE_STYLE,
            "height": "40px",
            "width": "100%",
            "marginBottom": "8px",
        }
    )
    
    row_elements = [
        html.Div(
            style={
                **SKELETON_BASE_STYLE,
                "height": "48px",
                "width": "100%",
                "marginBottom": "4px",
            }
        )
        for _ in range(rows)
    ]
    
    return html.Div(
        [header] + row_elements,
        **{'data-test-id': 'skeleton-table'}
    )


# =============================================================================
# LOADING SPINNERS
# =============================================================================

def create_loading_spinner(
    size: Literal["sm", "md", "lg"] = "md",
    text: Optional[str] = None,
    fullscreen: bool = False
) -> html.Div:
    """Create a unified loading spinner with optional text."""
    size_map = {
        "sm": {"width": "1.5rem", "height": "1.5rem"},
        "md": {"width": "3rem", "height": "3rem"},
        "lg": {"width": "5rem", "height": "5rem"},
    }
    
    spinner = dbc.Spinner(
        color="warning",  # Alpaca gold
        spinner_style=size_map[size],
        **{'data-test-id': 'loading-spinner'}
    )
    
    content = [spinner]
    if text:
        content.append(
            html.Div(
                text,
                style={
                    "color": "#8B949E",
                    "marginTop": "16px",
                    "fontSize": "14px",
                    "fontWeight": "500",
                }
            )
        )
    
    container_style = {**SPINNER_STYLE}
    if fullscreen:
        container_style.update({
            "position": "fixed",
            "top": "0",
            "left": "0",
            "right": "0",
            "bottom": "0",
            "backgroundColor": "rgba(13, 17, 23, 0.95)",
            "zIndex": "9999",
            "minHeight": "100vh",
        })
    
    return html.Div(
        content,
        style=container_style,
        **{'data-test-id': 'loading-container'}
    )


# =============================================================================
# PROGRESS INDICATORS
# =============================================================================

def create_progress_bar(
    progress: int,
    label: Optional[str] = None,
    color: str = "#F5C211",
    height: str = "8px"
) -> html.Div:
    """Create a progress bar."""
    progress = max(0, min(100, progress))  # Clamp 0-100
    
    elements = []
    if label:
        elements.append(
            html.Div(
                label,
                style={
                    "color": "#E6EDF3",
                    "fontSize": "12px",
                    "marginBottom": "8px",
                    "fontWeight": "500",
                }
            )
        )
    
    elements.append(
        html.Div([
            html.Div(
                style={
                    "width": f"{progress}%",
                    "height": height,
                    "backgroundColor": color,
                    "borderRadius": "4px",
                    "transition": "width 0.3s ease",
                }
            )
        ], style={
            "width": "100%",
            "height": height,
            "backgroundColor": "#21262D",
            "borderRadius": "4px",
            "overflow": "hidden",
        })
    )
    
    return html.Div(
        elements,
        **{'data-test-id': f'progress-bar-{progress}'}
    )


# =============================================================================
# LAZY LOADING WRAPPER
# =============================================================================

def create_lazy_wrapper(
    component_id: str,
    placeholder: html.Div,
    load_trigger: str = "viewport"
) -> html.Div:
    """
    Create a lazy-loading wrapper for heavy components.
    
    Args:
        component_id: Unique ID for the component
        placeholder: Placeholder to show while loading
        load_trigger: When to load ("viewport", "interaction", "immediate")
    """
    return html.Div([
        # Placeholder shown initially
        html.Div(
            placeholder,
            id=f"{component_id}-placeholder",
            **{'data-test-id': f'{component_id}-lazy-placeholder'}
        ),
        # Actual component loaded dynamically
        html.Div(
            id=f"{component_id}-content",
            **{'data-test-id': f'{component_id}-lazy-content'}
        ),
        # Store to track loading state
        dcc.Store(
            id=f"{component_id}-loaded",
            data={"loaded": False, "trigger": load_trigger}
        ),
    ], **{'data-test-id': f'{component_id}-lazy-wrapper'})


# =============================================================================
# LOADING STATE MANAGER
# =============================================================================

class LoadingStateManager:
    """
    Utility class to manage loading states across components.
    
    Usage:
        manager = LoadingStateManager()
        manager.add_loading("chart-1", "Loading market data...")
        manager.remove_loading("chart-1")
    """
    
    def __init__(self):
        self.loading_states = {}
    
    def add_loading(self, component_id: str, message: str = "Loading..."):
        """Mark component as loading."""
        self.loading_states[component_id] = {
            "loading": True,
            "message": message,
            "start_time": None  # Could add timestamp for timeout handling
        }
    
    def remove_loading(self, component_id: str):
        """Mark component as loaded."""
        if component_id in self.loading_states:
            self.loading_states[component_id]["loading"] = False
    
    def is_loading(self, component_id: str) -> bool:
        """Check if component is loading."""
        return self.loading_states.get(component_id, {}).get("loading", False)
    
    def get_loading_message(self, component_id: str) -> str:
        """Get loading message for component."""
        return self.loading_states.get(component_id, {}).get("message", "Loading...")


# =============================================================================
# CSS INJECTION
# =============================================================================

def inject_loading_css() -> html.Div:
    """
    Inject CSS for loading animations.
    DEPRECATED: CSS is now loaded from assets/alpaca_ui.css
    """
    return html.Div(style={"display": "none"})

def _unused_inject_loading_css():
    """Legacy implementation."""
    return html.Div(f"""
        {SHIMMER_KEYFRAMES}
        
        .skeleton-card, .skeleton-text, .skeleton-gauge, 
        .skeleton-chart, .skeleton-table {{
            animation: shimmer 2s infinite;
        }}
        
        .fade-in {{
            animation: fadeIn 0.3s ease-in;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        
        .slide-in {{
            animation: slideIn 0.3s ease-out;
        }}
        
        @keyframes slideIn {{
            from {{ 
                transform: translateY(20px);
                opacity: 0;
            }}
            to {{ 
                transform: translateY(0);
                opacity: 1;
            }}
        }}
    """)

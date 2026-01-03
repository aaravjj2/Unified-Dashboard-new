"""
Accessibility & Responsive Design Components
Phase 6 - Visualization & UX (Items 488-496)

Provides:
- ARIA labels and roles
- Keyboard navigation
- High contrast mode
- Screen reader support
- Responsive breakpoints
- Mobile-friendly layouts
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
from typing import Dict, Optional

# Design tokens
THEME = {
    "bg_primary": "#0D1117",
    "bg_secondary": "#161B22",
    "bg_tertiary": "#21262D",
    "gold": "#F5C211",
    "success": "#3FB950",
    "danger": "#F85149",
    "warning": "#D29922",
    "info": "#58A6FF",
    "text_primary": "#E6EDF3",
    "text_secondary": "#8B949E",
    "text_muted": "#6E7681",
    "border": "#30363D",
}

# High contrast theme
HIGH_CONTRAST_THEME = {
    "bg_primary": "#000000",
    "bg_secondary": "#1A1A1A",
    "bg_tertiary": "#333333",
    "gold": "#FFD700",
    "success": "#00FF00",
    "danger": "#FF0000",
    "warning": "#FFFF00",
    "info": "#00FFFF",
    "text_primary": "#FFFFFF",
    "text_secondary": "#E0E0E0",
    "text_muted": "#B0B0B0",
    "border": "#666666",
}


def create_accessibility_controls() -> html.Div:
    """Create accessibility control panel."""
    
    return html.Div([
        html.Div([
            html.Span("♿", style={"fontSize": "16px", "marginRight": "8px"}),
            html.Span("Accessibility", style={
                "fontSize": "13px",
                "fontWeight": "500",
                "color": THEME["text_primary"],
            }),
        ], style={"marginBottom": "12px"}),
        
        # High Contrast Toggle
        html.Div([
            html.Label("High Contrast", style={
                "color": THEME["text_secondary"],
                "fontSize": "12px",
                "marginRight": "12px",
            }),
            dbc.Switch(
                id="high-contrast-toggle",
                value=False,
                className="custom-switch",
            ),
        ], style={
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "marginBottom": "10px",
        }),
        
        # Font Size
        html.Div([
            html.Label("Font Size", style={
                "color": THEME["text_secondary"],
                "fontSize": "12px",
                "marginRight": "12px",
            }),
            html.Div([
                html.Button("A-", id="font-decrease", style={
                    "padding": "4px 8px",
                    "backgroundColor": THEME["bg_tertiary"],
                    "border": f"1px solid {THEME['border']}",
                    "borderRadius": "4px 0 0 4px",
                    "color": THEME["text_primary"],
                    "cursor": "pointer",
                }),
                html.Span("100%", id="font-size-display", style={
                    "padding": "4px 12px",
                    "backgroundColor": THEME["bg_tertiary"],
                    "border": f"1px solid {THEME['border']}",
                    "borderLeft": "none",
                    "borderRight": "none",
                    "color": THEME["text_primary"],
                    "fontSize": "11px",
                }),
                html.Button("A+", id="font-increase", style={
                    "padding": "4px 8px",
                    "backgroundColor": THEME["bg_tertiary"],
                    "border": f"1px solid {THEME['border']}",
                    "borderRadius": "0 4px 4px 0",
                    "color": THEME["text_primary"],
                    "cursor": "pointer",
                }),
            ], style={"display": "flex"}),
        ], style={
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "marginBottom": "10px",
        }),
        
        # Reduce Motion
        html.Div([
            html.Label("Reduce Motion", style={
                "color": THEME["text_secondary"],
                "fontSize": "12px",
                "marginRight": "12px",
            }),
            dbc.Switch(
                id="reduce-motion-toggle",
                value=False,
                className="custom-switch",
            ),
        ], style={
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "marginBottom": "10px",
        }),
        
        # Screen Reader Mode
        html.Div([
            html.Label("Screen Reader", style={
                "color": THEME["text_secondary"],
                "fontSize": "12px",
                "marginRight": "12px",
            }),
            dbc.Switch(
                id="screen-reader-toggle",
                value=False,
                className="custom-switch",
            ),
        ], style={
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
        }),
        
    ], style={
        "backgroundColor": THEME["bg_secondary"],
        "border": f"1px solid {THEME['border']}",
        "borderRadius": "8px",
        "padding": "16px",
    })


def create_skip_links() -> html.Div:
    """Create skip navigation links for keyboard users."""
    
    return html.Div([
        html.A("Skip to main content", href="#main-content", className="skip-link",
               style={
                   "position": "absolute",
                   "top": "-40px",
                   "left": "0",
                   "backgroundColor": THEME["gold"],
                   "color": THEME["bg_primary"],
                   "padding": "8px 16px",
                   "zIndex": "1000",
                   "transition": "top 0.3s",
               }),
        html.A("Skip to navigation", href="#main-nav", className="skip-link",
               style={
                   "position": "absolute",
                   "top": "-40px",
                   "left": "150px",
                   "backgroundColor": THEME["gold"],
                   "color": THEME["bg_primary"],
                   "padding": "8px 16px",
                   "zIndex": "1000",
                   "transition": "top 0.3s",
               }),
    ], style={"position": "relative"})


def create_aria_live_region() -> html.Div:
    """Create ARIA live region for screen reader announcements."""
    
    return html.Div([
        html.Div(id="aria-live-polite", role="status", **{"aria-live": "polite"},
                 style={"position": "absolute", "left": "-10000px", "width": "1px", "height": "1px", "overflow": "hidden"}),
        html.Div(id="aria-live-assertive", role="alert", **{"aria-live": "assertive"},
                 style={"position": "absolute", "left": "-10000px", "width": "1px", "height": "1px", "overflow": "hidden"}),
    ])


def create_responsive_container(content: html.Div, breakpoints: Optional[Dict] = None) -> html.Div:
    """Create a responsive container with breakpoint-based styling."""
    
    default_breakpoints = {
        "xs": {"maxWidth": "575px", "padding": "8px"},
        "sm": {"minWidth": "576px", "maxWidth": "767px", "padding": "12px"},
        "md": {"minWidth": "768px", "maxWidth": "991px", "padding": "16px"},
        "lg": {"minWidth": "992px", "maxWidth": "1199px", "padding": "20px"},
        "xl": {"minWidth": "1200px", "padding": "24px"},
    }
    
    breakpoints = breakpoints or default_breakpoints
    
    return html.Div(
        content,
        className="responsive-container",
        style={
            "width": "100%",
            "maxWidth": "1600px",
            "margin": "0 auto",
            "padding": "16px",
        }
    )


def create_mobile_nav() -> html.Div:
    """Create mobile-friendly navigation."""
    
    return html.Div([
        # Hamburger button
        html.Button([
            html.Span(className="hamburger-line"),
            html.Span(className="hamburger-line"),
            html.Span(className="hamburger-line"),
        ], id="mobile-nav-toggle", className="hamburger-btn", style={
            "display": "none",  # Hidden on desktop
            "flexDirection": "column",
            "justifyContent": "space-between",
            "width": "24px",
            "height": "18px",
            "backgroundColor": "transparent",
            "border": "none",
            "cursor": "pointer",
            "padding": "0",
        }),
        
        # Mobile menu
        html.Div([
            html.A("🔭 Scanner", href="#scanner", className="mobile-nav-link"),
            html.A("⚔️ Strategy", href="#strategy", className="mobile-nav-link"),
            html.A("🎮 Command", href="#command", className="mobile-nav-link"),
            html.A("🔧 Admin", href="#admin", className="mobile-nav-link"),
        ], id="mobile-menu", style={
            "display": "none",
            "position": "absolute",
            "top": "100%",
            "left": "0",
            "right": "0",
            "backgroundColor": THEME["bg_secondary"],
            "border": f"1px solid {THEME['border']}",
            "borderRadius": "0 0 8px 8px",
            "padding": "16px",
            "zIndex": "100",
        }),
    ], style={"position": "relative"})


# CSS for accessibility and responsive features
ACCESSIBILITY_CSS = """
<style>
/* Skip links */
.skip-link:focus {
    top: 0 !important;
}

/* High contrast mode */
.high-contrast {
    --bg-primary: #000000 !important;
    --bg-secondary: #1A1A1A !important;
    --text-primary: #FFFFFF !important;
    --gold: #FFD700 !important;
}

/* Reduce motion */
@media (prefers-reduced-motion: reduce) {
    * {
        animation: none !important;
        transition: none !important;
    }
}

.reduce-motion * {
    animation: none !important;
    transition: none !important;
}

/* Focus indicators */
*:focus {
    outline: 2px solid var(--alpaca-gold, #F5C211) !important;
    outline-offset: 2px;
}

*:focus:not(:focus-visible) {
    outline: none !important;
}

*:focus-visible {
    outline: 2px solid var(--alpaca-gold, #F5C211) !important;
    outline-offset: 2px;
}

/* Responsive breakpoints */
@media (max-width: 575px) {
    .responsive-container {
        padding: 8px !important;
    }
    .hide-xs {
        display: none !important;
    }
    .mobile-nav-toggle {
        display: flex !important;
    }
    .desktop-nav {
        display: none !important;
    }
}

@media (min-width: 576px) and (max-width: 767px) {
    .responsive-container {
        padding: 12px !important;
    }
    .hide-sm {
        display: none !important;
    }
}

@media (min-width: 768px) and (max-width: 991px) {
    .responsive-container {
        padding: 16px !important;
    }
    .hide-md {
        display: none !important;
    }
}

@media (min-width: 992px) {
    .mobile-nav-toggle {
        display: none !important;
    }
    .mobile-menu {
        display: none !important;
    }
}

/* Mobile navigation */
.hamburger-line {
    display: block;
    width: 100%;
    height: 2px;
    background-color: var(--text-primary, #E6EDF3);
    border-radius: 1px;
}

.mobile-nav-link {
    display: block;
    padding: 12px 16px;
    color: var(--text-primary, #E6EDF3);
    text-decoration: none;
    border-bottom: 1px solid var(--border-primary, #30363D);
}

.mobile-nav-link:last-child {
    border-bottom: none;
}

.mobile-nav-link:hover {
    background-color: var(--bg-tertiary, #21262D);
}

/* Touch-friendly targets */
@media (pointer: coarse) {
    button, a, input, select {
        min-height: 44px;
        min-width: 44px;
    }
}

/* Screen reader only */
.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}
</style>
"""

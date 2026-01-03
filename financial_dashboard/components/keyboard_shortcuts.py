"""
Keyboard Shortcuts Modal Component
Phase 6 - Visualization & UX (Item 497)

Provides a comprehensive keyboard shortcuts cheat-sheet modal
that can be triggered with Ctrl+/ or a button.
"""

from dash import html, dcc
import dash_bootstrap_components as dbc

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

# Global shortcuts dictionary for external access
KEYBOARD_SHORTCUTS = {
    "Navigation": [
        ("Ctrl + 1", "Scanner Workspace"),
        ("Ctrl + 2", "Strategy Workspace"),
        ("Ctrl + 3", "Command Center"),
        ("Ctrl + 4", "Admin Panel"),
        ("Tab", "Next Input/Control"),
        ("Shift + Tab", "Previous Input/Control"),
    ],
    "Command Palette": [
        ("Ctrl + K", "Open Command Palette"),
        ("Esc", "Close Palette/Modal"),
        ("↑ / ↓", "Navigate Options"),
        ("Enter", "Execute Command"),
    ],
    "Trading Actions": [
        ("Ctrl + N", "New Trade Order"),
        ("Ctrl + O", "Options Chain"),
        ("Ctrl + B", "Quick Buy"),
        ("Ctrl + S", "Quick Sell"),
        ("Ctrl + E", "Edit Position"),
    ],
    "Analysis": [
        ("Ctrl + F", "Focus Search"),
        ("Ctrl + R", "Refresh Data"),
        ("Ctrl + G", "Greek Calculator"),
        ("Ctrl + V", "Volatility Lab"),
    ],
    "Journal & Export": [
        ("Ctrl + J", "Open Trade Journal"),
        ("Ctrl + Shift + E", "Export Data"),
        ("Ctrl + Shift + S", "Screenshot Chart"),
        ("Ctrl + P", "Print View"),
    ],
    "General": [
        ("Ctrl + /", "Show Shortcuts"),
        ("Ctrl + ,", "Settings"),
        ("F11", "Fullscreen Toggle"),
        ("Ctrl + Z", "Undo Last Action"),
]
}


def create_keyboard_shortcuts_modal() -> dbc.Modal:
    """Create the keyboard shortcuts modal."""
    
    shortcuts = KEYBOARD_SHORTCUTS
    
    # Create shortcut sections
    sections = []
    for category, items in shortcuts.items():
        section = html.Div([
            html.H6(category, style={
                "color": THEME["gold"],
                "fontSize": "13px",
                "fontWeight": "600",
                "textTransform": "uppercase",
                "letterSpacing": "0.5px",
                "marginBottom": "12px",
                "paddingBottom": "6px",
                "borderBottom": f"1px solid {THEME['border']}",
            }),
            html.Div([
                _create_shortcut_row(key, desc) for key, desc in items
            ]),
        ], style={"marginBottom": "24px"})
        sections.append(section)
    
    # Split into 2 columns
    left_sections = sections[:3]
    right_sections = sections[3:]
    
    return dbc.Modal([
        dbc.ModalHeader([
            html.Div([
                html.Span("⌨️", style={"fontSize": "24px", "marginRight": "12px"}),
                html.Span("Keyboard Shortcuts", style={
                    "fontSize": "18px",
                    "fontWeight": "600",
                    "color": THEME["text_primary"],
                }),
            ], style={"display": "flex", "alignItems": "center"}),
        ], style={
            "backgroundColor": THEME["bg_secondary"],
            "borderBottom": f"1px solid {THEME['border']}",
            "padding": "16px 24px",
        }, close_button=True),
        
        dbc.ModalBody([
            html.Div([
                # Left column
                html.Div(left_sections, style={
                    "flex": "1",
                    "paddingRight": "20px",
                }),
                # Right column
                html.Div(right_sections, style={
                    "flex": "1",
                    "paddingLeft": "20px",
                    "borderLeft": f"1px solid {THEME['border']}",
                }),
            ], style={
                "display": "flex",
                "gap": "20px",
            }),
        ], style={
            "backgroundColor": THEME["bg_primary"],
            "padding": "24px",
        }),
        
        dbc.ModalFooter([
            html.Span("Press Ctrl + / anytime to show this modal", style={
                "color": THEME["text_muted"],
                "fontSize": "12px",
            }),
        ], style={
            "backgroundColor": THEME["bg_secondary"],
            "borderTop": f"1px solid {THEME['border']}",
            "padding": "12px 24px",
        }),
    ], id="keyboard-shortcuts-modal", is_open=False, size="lg", centered=True)


def _create_shortcut_row(key: str, description: str) -> html.Div:
    """Create a single shortcut row."""
    # Split key into parts for styling
    key_parts = key.split(" + ")
    
    key_badges = []
    for i, part in enumerate(key_parts):
        key_badges.append(
            html.Span(part, style={
                "display": "inline-block",
                "padding": "4px 8px",
                "backgroundColor": THEME["bg_tertiary"],
                "border": f"1px solid {THEME['border']}",
                "borderRadius": "4px",
                "fontSize": "11px",
                "fontFamily": "'JetBrains Mono', monospace",
                "fontWeight": "500",
                "color": THEME["text_primary"],
                "minWidth": "24px",
                "textAlign": "center",
            })
        )
        if i < len(key_parts) - 1:
            key_badges.append(
                html.Span(" + ", style={
                    "color": THEME["text_muted"],
                    "fontSize": "10px",
                    "margin": "0 2px",
                })
            )
    
    return html.Div([
        html.Div(key_badges, style={
            "display": "flex",
            "alignItems": "center",
            "minWidth": "120px",
        }),
        html.Span(description, style={
            "color": THEME["text_secondary"],
            "fontSize": "13px",
            "marginLeft": "12px",
        }),
    ], style={
        "display": "flex",
        "alignItems": "center",
        "marginBottom": "10px",
    })


def create_shortcuts_trigger_button() -> html.Button:
    """Create a button to trigger the shortcuts modal."""
    return html.Button([
        html.Span("⌨️", style={"marginRight": "6px"}),
        html.Span("Shortcuts"),
        html.Span("Ctrl+/", style={
            "marginLeft": "8px",
            "padding": "2px 6px",
            "backgroundColor": THEME["bg_tertiary"],
            "borderRadius": "4px",
            "fontSize": "10px",
            "opacity": "0.7",
        }),
    ], id="shortcuts-trigger-btn", style={
        "padding": "6px 12px",
        "backgroundColor": "transparent",
        "border": f"1px solid {THEME['border']}",
        "borderRadius": "6px",
        "color": THEME["text_secondary"],
        "fontSize": "12px",
        "cursor": "pointer",
        "display": "flex",
        "alignItems": "center",
        "transition": "all 0.2s ease",
    })


# JavaScript for keyboard shortcut detection
SHORTCUTS_JS = """
<script>
document.addEventListener('keydown', function(e) {
    // Ctrl + / to show shortcuts
    if (e.ctrlKey && e.key === '/') {
        e.preventDefault();
        document.getElementById('shortcuts-trigger-btn')?.click();
    }
    
    // Ctrl + K for command palette
    if (e.ctrlKey && e.key === 'k') {
        e.preventDefault();
        document.getElementById('command-palette-trigger')?.click();
    }
    
    // Ctrl + 1-4 for workspace navigation
    if (e.ctrlKey && ['1', '2', '3', '4'].includes(e.key)) {
        e.preventDefault();
        const tabIndex = parseInt(e.key) - 1;
        const tabs = document.querySelectorAll('.workspace-tab');
        if (tabs[tabIndex]) {
            tabs[tabIndex].click();
        }
    }
    
    // Ctrl + R for refresh
    if (e.ctrlKey && e.key === 'r') {
        e.preventDefault();
        document.getElementById('refresh-data-btn')?.click();
    }
});
</script>
"""

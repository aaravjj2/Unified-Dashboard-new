"""
Theme Toggle Component for Sprint 6
Provides light/dark mode switching with persistent storage
"""
from dash import html, dcc
import dash_bootstrap_components as dbc

# Theme definitions
THEMES = {
    'dark': {
        'background': '#0a0e27',
        'surface': '#1a1f3a',
        'primary': '#60a5fa',
        'text': '#e6eef8',
        'text_secondary': '#94a3b8',
        'border': '#334155',
        'success': '#10b981',
        'warning': '#f59e0b',
        'danger': '#ef4444',
    },
    'light': {
        'background': '#f8fafc',
        'surface': '#ffffff',
        'primary': '#3b82f6',
        'text': '#1e293b',
        'text_secondary': '#64748b',
        'border': '#e2e8f0',
        'success': '#22c55e',
        'warning': '#eab308',
        'danger': '#f87171',
    }
}

def create_theme_toggle():
    """Create theme toggle button component"""
    return html.Div([
        dbc.Button(
            [
                html.I(className="fas fa-moon", id="theme-icon"),
                html.Span(" Theme", className="ms-2")
            ],
            id="theme-toggle-btn",
            color="secondary",
            outline=True,
            size="sm",
            className="me-2"
        ),
        dcc.Store(id='theme-store', storage_type='local', data='dark')
    ])

def get_theme_css(theme_mode='dark'):
    """Generate dynamic CSS for the current theme"""
    theme = THEMES.get(theme_mode, THEMES['dark'])
    
    return f"""
        :root {{
            --bg-primary: {theme['background']};
            --bg-surface: {theme['surface']};
            --color-primary: {theme['primary']};
            --text-primary: {theme['text']};
            --text-secondary: {theme['text_secondary']};
            --border-color: {theme['border']};
            --color-success: {theme['success']};
            --color-warning: {theme['warning']};
            --color-danger: {theme['danger']};
        }}
        
        body {{
            background-color: {theme['background']};
            color: {theme['text']};
        }}
        
        .card {{
            background-color: {theme['surface']};
            border-color: {theme['border']};
            color: {theme['text']};
        }}
        
        .table {{
            color: {theme['text']};
            background-color: {theme['surface']};
        }}
        
        .table-striped tbody tr:nth-of-type(odd) {{
            background-color: {theme['background']};
        }}
        
        .form-control, .form-select {{
            background-color: {theme['surface']};
            color: {theme['text']};
            border-color: {theme['border']};
        }}
        
        .btn-outline-primary {{
            color: {theme['primary']};
            border-color: {theme['primary']};
        }}
        
        .btn-outline-primary:hover {{
            background-color: {theme['primary']};
            color: {theme['background']};
        }}
    """

def register_theme_callbacks(app):
    """Register theme toggle callbacks"""
    from dash import Output, Input, State, callback_context
    
    @app.callback(
        [Output('theme-store', 'data'),
         Output('theme-icon', 'className'),
         Output('theme-styles', 'children', allow_duplicate=True)],
        [Input('theme-toggle-btn', 'n_clicks')],
        [State('theme-store', 'data')],
        prevent_initial_call=True
    )
    def toggle_theme(n_clicks, current_theme):
        if n_clicks is None:
            return current_theme or 'dark', 'fas fa-moon', get_theme_css('dark')
        
        # Toggle theme
        new_theme = 'light' if current_theme == 'dark' else 'dark'
        icon = 'fas fa-sun' if new_theme == 'light' else 'fas fa-moon'
        
        return new_theme, icon, get_theme_css(new_theme)
    
    @app.callback(
        [Output('theme-icon', 'className', allow_duplicate=True),
         Output('theme-styles', 'children')],
        [Input('theme-store', 'data')],
        prevent_initial_call='initial_duplicate'
    )
    def apply_theme_on_load(theme_mode):
        """Apply theme on initial page load"""
        theme_mode = theme_mode or 'dark'
        icon = 'fas fa-sun' if theme_mode == 'light' else 'fas fa-moon'
        return icon, get_theme_css(theme_mode)

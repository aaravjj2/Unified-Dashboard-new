"""
Phase 17: Command Palette UI Component
OpenBB-Inspired slash-command system for the Options Lab
"""

from dash import html, dcc, callback, Input, Output, State, no_update, ctx
import dash_bootstrap_components as dbc
from typing import List, Dict, Any
import json


def create_command_palette() -> html.Div:
    """
    Create the Command Palette UI component.
    
    Features:
    - Ctrl+K to open
    - Slash commands (/gex SPY, /flow TSLA)
    - Autocomplete suggestions
    - Command history
    """
    return html.Div([
        # Hidden trigger for keyboard shortcut
        dcc.Store(id='command-palette-open', data=False),
        dcc.Store(id='command-history-store', data=[]),
        dcc.Store(id='command-result-store', data=None),
        
        # Command Palette Modal
        dbc.Modal([
            dbc.ModalHeader([
                html.Div([
                    html.Span("⌘", style={
                        'backgroundColor': '#3d4050',
                        'padding': '2px 8px',
                        'borderRadius': '4px',
                        'marginRight': '8px',
                        'fontSize': '12px'
                    }),
                    html.Span("Command Palette", style={'fontWeight': 'bold'})
                ], style={'display': 'flex', 'alignItems': 'center'})
            ], close_button=True, style={'backgroundColor': '#1e2130', 'borderBottom': '1px solid #3d4050'}),
            
            dbc.ModalBody([
                # Command Input
                html.Div([
                    dcc.Input(
                        id='command-input',
                        type='text',
                        placeholder='Type a command (e.g., /gex SPY, /flow TSLA)...',
                        autoFocus=True,
                        style={
                            'width': '100%',
                            'padding': '12px 15px',
                            'backgroundColor': '#2a2d3a',
                            'color': '#ffffff',
                            'border': '2px solid #F5C211',
                            'borderRadius': '8px',
                            'fontSize': '16px',
                            'outline': 'none'
                        }
                    ),
                ], style={'marginBottom': '15px'}),
                
                # Suggestions List
                html.Div(
                    id='command-suggestions',
                    children=[],
                    style={
                        'maxHeight': '300px',
                        'overflowY': 'auto',
                        'backgroundColor': '#1e2130',
                        'borderRadius': '8px'
                    }
                ),
                
                # Result Display
                html.Div(
                    id='command-result-display',
                    children=[],
                    style={'marginTop': '15px'}
                ),
                
                # Help Footer
                html.Div([
                    html.Span("↑↓ Navigate", style={'marginRight': '15px', 'color': '#6b7280'}),
                    html.Span("Enter Execute", style={'marginRight': '15px', 'color': '#6b7280'}),
                    html.Span("Esc Close", style={'color': '#6b7280'}),
                ], style={
                    'marginTop': '15px',
                    'paddingTop': '10px',
                    'borderTop': '1px solid #3d4050',
                    'fontSize': '12px'
                })
            ], style={'backgroundColor': '#16181f', 'padding': '20px'}),
        ], 
        id='command-palette-modal',
        is_open=False,
        size='lg',
        centered=True,
        backdrop=True,
        style={'backgroundColor': 'rgba(0,0,0,0.8)'}
        ),
        
        # Keyboard Listener (JavaScript injection)
        html.Div(id='keyboard-listener', style={'display': 'none'}),
    ])


def create_suggestion_item(name: str, usage: str, description: str, is_selected: bool = False) -> html.Div:
    """Create a single suggestion item."""
    return html.Div([
        html.Div([
            html.Span(name, style={
                'color': '#F5C211',
                'fontWeight': 'bold',
                'marginRight': '10px'
            }),
            html.Span(usage, style={
                'color': '#6b7280',
                'fontSize': '12px'
            }),
        ]),
        html.Div(description, style={
            'color': '#9ca3af',
            'fontSize': '12px',
            'marginTop': '2px'
        })
    ], style={
        'padding': '10px 15px',
        'borderRadius': '4px',
        'backgroundColor': '#2a2d3a' if is_selected else 'transparent',
        'cursor': 'pointer',
        'borderLeft': '3px solid #F5C211' if is_selected else '3px solid transparent',
        'marginBottom': '2px'
    }, className='command-suggestion-item')


def get_all_commands() -> List[Dict[str, str]]:
    """Get all available commands for display."""
    return [
        {"name": "/gex", "usage": "/gex <TICKER>", "description": "Show Gamma Exposure (GEX) chart"},
        {"name": "/flow", "usage": "/flow <TICKER>", "description": "Show options flow tape"},
        {"name": "/iv", "usage": "/iv <TICKER>", "description": "Show IV surface"},
        {"name": "/chain", "usage": "/chain <TICKER>", "description": "Load options chain"},
        {"name": "/forecast", "usage": "/forecast <TICKER>", "description": "Get AI forecast"},
        {"name": "/positions", "usage": "/positions", "description": "Show current positions"},
        {"name": "/risk", "usage": "/risk", "description": "Show risk metrics"},
        {"name": "/scanner", "usage": "/scanner", "description": "Switch to Scanner workspace"},
        {"name": "/strategy", "usage": "/strategy", "description": "Switch to Strategy workspace"},
        {"name": "/command", "usage": "/command", "description": "Switch to Command workspace"},
        {"name": "/admin", "usage": "/admin", "description": "Switch to Admin workspace"},
        {"name": "/export", "usage": "/export [--format csv|json]", "description": "Export current data"},
        {"name": "/help", "usage": "/help [command]", "description": "Show help"},
    ]


def filter_commands(query: str) -> List[Dict[str, str]]:
    """Filter commands based on query."""
    all_cmds = get_all_commands()
    
    if not query:
        return all_cmds
    
    query_lower = query.lower().strip()
    if query_lower.startswith('/'):
        query_lower = query_lower[1:]
    
    # Split to get command part only
    parts = query_lower.split()
    cmd_part = parts[0] if parts else ''
    
    filtered = []
    for cmd in all_cmds:
        cmd_name = cmd['name'][1:].lower()  # Remove /
        if cmd_name.startswith(cmd_part) or cmd_part in cmd_name:
            filtered.append(cmd)
    
    return filtered


# Callback to register
def register_command_palette_callbacks(app):
    """Register all command palette callbacks."""
    
    @app.callback(
        Output('command-suggestions', 'children'),
        Input('command-input', 'value'),
        prevent_initial_call=True
    )
    def update_suggestions(query):
        """Update suggestions based on input."""
        if query is None:
            query = ''
        
        commands = filter_commands(query)
        
        if not commands:
            return html.Div("No matching commands", style={
                'padding': '15px',
                'color': '#6b7280',
                'textAlign': 'center'
            })
        
        return [
            create_suggestion_item(
                cmd['name'],
                cmd['usage'],
                cmd['description'],
                is_selected=(i == 0)
            ) for i, cmd in enumerate(commands)
        ]
    
    @app.callback(
        [Output('command-result-display', 'children'),
         Output('command-palette-modal', 'is_open', allow_duplicate=True),
         Output('main-workspace-tabs', 'value', allow_duplicate=True),
         Output('alpaca-ticker-input', 'value', allow_duplicate=True),
         Output('alpaca-load-button', 'n_clicks', allow_duplicate=True)],
        Input('command-input', 'n_submit'),
        State('command-input', 'value'),
        State('alpaca-load-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def execute_command(n_submit, command_str, current_clicks):
        """Execute the command when Enter is pressed."""
        if not command_str:
            return no_update, no_update, no_update, no_update, no_update
        
        command_str = command_str.strip()
        if not command_str.startswith('/'):
            command_str = '/' + command_str
        
        # Parse command
        parts = command_str[1:].split()
        if not parts:
            return no_update, no_update, no_update, no_update, no_update
        
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        ticker = args[0].upper() if args else None
        
        # Tab switching commands
        tab_map = {
            'scanner': 'scanner-workspace-tab',
            'strategy': 'strategy-workspace-tab',
            'command': 'command-workspace-tab',
            'admin': 'admin-workspace-tab',
            'gex': 'scanner-workspace-tab',
            'flow': 'scanner-workspace-tab',
            'iv': 'strategy-workspace-tab',
            'positions': 'command-workspace-tab',
            'risk': 'command-workspace-tab',
        }
        
        new_tab = tab_map.get(cmd, no_update)
        
        # Commands that need ticker
        if cmd in ['chain', 'gex', 'flow', 'iv', 'forecast'] and ticker:
            result = html.Div([
                dbc.Alert(f"✅ Loading {ticker}...", color="success", duration=2000)
            ])
            return result, False, new_tab, ticker, (current_clicks or 0) + 1
        
        # Tab switch only
        if cmd in tab_map:
            result = html.Div([
                dbc.Alert(f"✅ Switched to {cmd} view", color="success", duration=2000)
            ])
            return result, False, new_tab, no_update, no_update
        
        # Help command
        if cmd == 'help':
            help_text = "**Available Commands:**\n"
            for c in get_all_commands():
                help_text += f"\n`{c['name']}` - {c['description']}"
            result = html.Div([
                dcc.Markdown(help_text, style={'color': '#e0e0e0'})
            ])
            return result, True, no_update, no_update, no_update
        
        # Unknown command
        result = html.Div([
            dbc.Alert(f"❌ Unknown command: {cmd}", color="danger", duration=3000)
        ])
        return result, True, no_update, no_update, no_update


# JavaScript for keyboard shortcut (Ctrl+K)
KEYBOARD_SHORTCUT_JS = """
document.addEventListener('keydown', function(e) {
    // Ctrl+K or Cmd+K to open command palette
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        // Find and click the invisible trigger
        var modal = document.querySelector('#command-palette-modal');
        if (modal) {
            // Toggle modal using Dash callback
            var event = new CustomEvent('open-command-palette');
            document.dispatchEvent(event);
        }
    }
});
"""

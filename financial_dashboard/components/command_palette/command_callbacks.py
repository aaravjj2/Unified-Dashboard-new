"""
Phase 17: Command Palette Callbacks
Handles command execution, suggestions, and modal control
"""

from dash import callback, Input, Output, State, no_update, ctx
import dash_bootstrap_components as dbc
from dash import html
import logging

logger = logging.getLogger(__name__)


def register_command_palette_callbacks(app):
    """Register all command palette callbacks."""
    
    @app.callback(
        Output('command-palette-modal', 'is_open'),
        [Input('command-palette-trigger', 'n_clicks')],
        [State('command-palette-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_command_palette(n_clicks, is_open):
        """Toggle command palette modal on button click."""
        if n_clicks:
            return not is_open
        return is_open
    
    @app.callback(
        [Output('command-result-display', 'children'),
         Output('command-palette-modal', 'is_open', allow_duplicate=True),
         Output('main-workspace-tabs', 'value', allow_duplicate=True),
         Output('alpaca-ticker-input', 'value', allow_duplicate=True),
         Output('alpaca-load-button', 'n_clicks', allow_duplicate=True)],
        Input('command-input', 'n_submit'),
        [State('command-input', 'value'),
         State('alpaca-load-button', 'n_clicks')],
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
        
        logger.info(f"Command palette: executing '{cmd}' with args {args}")
        
        # Tab switching commands
        tab_map = {
            'scanner': 'scanner-workspace-tab',
            'scan': 'scanner-workspace-tab',
            'strategy': 'strategy-workspace-tab',
            'strat': 'strategy-workspace-tab',
            'command': 'command-workspace-tab',
            'cmd': 'command-workspace-tab',
            'admin': 'admin-workspace-tab',
            'status': 'admin-workspace-tab',
            'gex': 'scanner-workspace-tab',
            'gamma': 'scanner-workspace-tab',
            'flow': 'scanner-workspace-tab',
            'iv': 'strategy-workspace-tab',
            'vol': 'strategy-workspace-tab',
            'positions': 'command-workspace-tab',
            'pos': 'command-workspace-tab',
            'risk': 'command-workspace-tab',
        }
        
        new_tab = tab_map.get(cmd, no_update)
        
        # Commands that need ticker and should load chain
        if cmd in ['chain', 'gex', 'flow', 'iv', 'forecast', 'load'] and ticker:
            result = html.Div([
                dbc.Alert([
                    html.Strong(f"✅ Loading {ticker}..."),
                    html.Br(),
                    html.Small(f"Switching to Strategy tab and loading options chain data")
                ], color="success", duration=4000),
                html.Div([
                    html.Span("Command executed: ", style={'fontWeight': 'bold'}),
                    html.Code(f"/{cmd} {ticker}", style={'backgroundColor': '#e9ecef', 'padding': '2px 6px', 'borderRadius': '4px'})
                ], style={'marginTop': '10px', 'padding': '10px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px'})
            ])
            return result, False, new_tab if new_tab != no_update else 'strategy-workspace-tab', ticker, (current_clicks or 0) + 1
        
        # Tab switch only (no ticker needed)
        if cmd in tab_map:
            result = html.Div([
                dbc.Alert([
                    html.Strong(f"✅ Switched to {cmd.title()} workspace"),
                    html.Br(),
                    html.Small("Use the tab to explore the workspace features")
                ], color="info", duration=3000)
            ])
            return result, False, new_tab, no_update, no_update
        
        # Help command - keep modal open
        if cmd == 'help':
            help_items = [
                ("/gex <TICKER>", "Show Gamma Exposure chart", "📊"),
                ("/chain <TICKER>", "Load options chain", "📈"),
                ("/flow <TICKER>", "Show options flow tape", "💹"),
                ("/iv <TICKER>", "Show IV surface", "📉"),
                ("/forecast <TICKER>", "Get AI forecast", "🔮"),
                ("/scanner", "Switch to Scanner workspace", "🔭"),
                ("/strategy", "Switch to Strategy workspace", "⚔️"),
                ("/command", "Switch to Command workspace", "🎮"),
                ("/admin", "Switch to Admin workspace", "🔧"),
                ("/positions", "Show positions", "💼"),
                ("/risk", "Show risk metrics", "⚠️"),
            ]
            result = html.Div([
                html.H5("📖 Available Commands", style={'color': '#0d6efd', 'marginBottom': '15px', 'borderBottom': '2px solid #0d6efd', 'paddingBottom': '10px'}),
                html.Div([
                    html.Div([
                        html.Span(icon, style={'fontSize': '16px', 'marginRight': '8px'}),
                        html.Span(cmd, style={'color': '#b88c00', 'fontWeight': 'bold', 'marginRight': '15px', 'fontFamily': 'monospace'}),
                        html.Span(desc, style={'color': '#6c757d'})
                    ], style={'marginBottom': '12px', 'padding': '8px', 'backgroundColor': '#f8f9fa', 'borderRadius': '6px', 'borderLeft': '3px solid #ffc107'})
                    for cmd, desc, icon in help_items
                ])
            ], style={'padding': '15px', 'backgroundColor': '#ffffff', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
            return result, True, no_update, no_update, no_update
        
        # Unknown command
        result = html.Div([
            dbc.Alert([
                html.Strong(f"❌ Unknown command: /{cmd}"),
                html.Br(),
                html.Small("Type /help for available commands")
            ], color="danger", duration=5000)
        ])
        return result, True, no_update, no_update, no_update
    
    @app.callback(
        Output('command-suggestions', 'children'),
        Input('command-input', 'value'),
        prevent_initial_call=True
    )
    def update_suggestions(query):
        """Update suggestions based on input."""
        all_commands = [
            {"name": "/gex", "args": "<TICKER>", "desc": "Show Gamma Exposure (GEX) chart"},
            {"name": "/chain", "args": "<TICKER>", "desc": "Load options chain for ticker"},
            {"name": "/flow", "args": "<TICKER>", "desc": "Show options flow tape"},
            {"name": "/iv", "args": "<TICKER>", "desc": "Show IV surface"},
            {"name": "/forecast", "args": "<TICKER>", "desc": "Get AI forecast"},
            {"name": "/scanner", "args": "", "desc": "Switch to Scanner workspace"},
            {"name": "/strategy", "args": "", "desc": "Switch to Strategy workspace"},
            {"name": "/command", "args": "", "desc": "Switch to Command workspace"},
            {"name": "/admin", "args": "", "desc": "Switch to Admin workspace"},
            {"name": "/positions", "args": "", "desc": "Show current positions"},
            {"name": "/risk", "args": "", "desc": "Show risk metrics"},
            {"name": "/help", "args": "", "desc": "Show all available commands"},
        ]
        
        if not query:
            filtered = all_commands
        else:
            query_lower = query.lower().strip()
            if query_lower.startswith('/'):
                query_lower = query_lower[1:]
            
            # Get just the command part
            parts = query_lower.split()
            cmd_part = parts[0] if parts else ''
            
            filtered = [c for c in all_commands if cmd_part in c['name'][1:].lower()]
        
        if not filtered:
            return html.Div("No matching commands. Type /help for all commands.", 
                          style={'padding': '15px', 'color': '#6b7280', 'textAlign': 'center'})
        
        return [
            html.Div([
                html.Div([
                    html.Span(cmd['name'], style={'color': '#F5C211', 'fontWeight': 'bold', 'marginRight': '10px'}),
                    html.Span(cmd['args'], style={'color': '#6b7280', 'fontSize': '12px'}),
                ]),
                html.Div(cmd['desc'], style={'color': '#9ca3af', 'fontSize': '12px', 'marginTop': '2px'})
            ], style={
                'padding': '10px 15px',
                'borderLeft': '3px solid #F5C211' if i == 0 else '3px solid transparent',
                'backgroundColor': '#2a2d3a' if i == 0 else 'transparent',
                'marginBottom': '2px',
                'cursor': 'pointer'
            })
            for i, cmd in enumerate(filtered)
        ]

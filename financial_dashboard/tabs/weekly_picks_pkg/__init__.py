"""
Weekly Picks Package - UI Components with Stable IDs

Implements dry-run/approve workflow for weekly picks with:
- Stable element IDs (wp-*)
- Diff visualization (added/removed/changed)
- Admin approve modal
- Download CSV functionality
"""

from dash import html, dcc
import dash_bootstrap_components as dbc


def create_layout(initial_data=None):
    """
    Create Weekly Picks layout with stable IDs.
    
    Args:
        initial_data: Initial picks data to display
        
    Returns:
        html.Div with complete layout
    """
    initial_data = initial_data or {}
    
    return html.Div([
        # Header
        html.Div([
            html.H3('Weekly Picks', style={'color': 'white'}),
            html.Span(
                'Pipeline Status: Ready',
                id='wp-pipeline-status',
                style={
                    'backgroundColor': '#94a3b8',
                    'color': 'white',
                    'padding': '4px 12px',
                    'borderRadius': '4px',
                    'fontSize': '14px',
                    'marginLeft': '12px'
                }
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '16px'}),
        
        # Controls
        html.Div([
            html.Label('Run Mode:', style={'marginRight': '8px', 'color': 'white'}),
            dcc.Dropdown(
                id='wp-run-mode',
                options=[
                    {'label': 'Dry Run (Preview)', 'value': 'dryrun'},
                    {'label': 'Publish (Admin)', 'value': 'publish'}
                ],
                value='dryrun',
                style={'width': '200px', 'display': 'inline-block', 'marginRight': '12px'}
            ),
            html.Button(
                'Run Pipeline',
                id='wp-run-btn',
                n_clicks=0,
                style={
                    'backgroundColor': '#3b82f6',
                    'color': 'white',
                    'padding': '8px 16px',
                    'border': 'none',
                    'borderRadius': '4px',
                    'cursor': 'pointer',
                    'marginRight': '8px'
                }
            ),
            html.Button(
                'Approve & Publish',
                id='wp-approve-btn',
                n_clicks=0,
                disabled=True,
                style={
                    'backgroundColor': '#10b981',
                    'color': 'white',
                    'padding': '8px 16px',
                    'border': 'none',
                    'borderRadius': '4px',
                    'cursor': 'pointer',
                    'marginRight': '8px',
                    'opacity': '0.5'
                }
            ),
            html.Button(
                'Download CSV',
                id='wp-download-csv',
                n_clicks=0,
                style={
                    'backgroundColor': '#6b7280',
                    'color': 'white',
                    'padding': '8px 16px',
                    'border': 'none',
                    'borderRadius': '4px',
                    'cursor': 'pointer'
                }
            ),
        ], style={'marginBottom': '16px'}),
        
        # Run Status
        html.Div(
            'Ready to run pipeline',
            id='wp-run-status',
            style={
                'padding': '8px 12px',
                'backgroundColor': '#f3f4f6',
                'color': '#1f2937',
                'borderRadius': '4px',
                'marginBottom': '16px'
            }
        ),
        
        # Diff Panel (hidden by default)
        html.Div(
            id='wp-diff-panel',
            children=[],
            style={'display': 'none', 'marginBottom': '16px'}
        ),
        
        # Published Picks Table
        html.Div([
            html.H4('Published Weekly Picks', style={'color': 'white', 'marginBottom': '8px'}),
            html.Div(
                'No picks published yet. Run pipeline to generate.',
                id='wp-published-table',
                style={'padding': '20px', 'textAlign': 'center', 'color': '#9ca3af'}
            )
        ], style={'marginBottom': '16px'}),
        
        # Staging/Preview Table (for dry-run results)
        html.Div([
            html.H4('Staging Preview', style={'color': 'white', 'marginBottom': '8px'}),
            html.Div(
                'Run dry-run to preview picks',
                id='wp-staging-table',
                style={'padding': '20px', 'textAlign': 'center', 'color': '#9ca3af'}
            )
        ]),
        
        # Hidden stores
        dcc.Store(id='wp-current-run-id', data=None),
        dcc.Store(id='wp-staging-data', data=None),
        dcc.Download(id='wp-csv-download'),
        
        # Approve Modal
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle('Approve and Publish')),
            dbc.ModalBody([
                html.P('Are you sure you want to publish these picks?'),
                html.P('This will replace the currently published weekly picks.', style={'color': '#ef4444'}),
                html.Div([
                    html.Label('Admin Token:', style={'marginBottom': '4px'}),
                    dcc.Input(
                        id='wp-admin-token-input',
                        type='password',
                        placeholder='Enter admin token',
                        style={'width': '100%', 'padding': '8px'}
                    )
                ], style={'marginTop': '12px'})
            ]),
            dbc.ModalFooter([
                dbc.Button('Cancel', id='wp-approve-cancel', color='secondary'),
                dbc.Button('Confirm Publish', id='wp-approve-confirm', color='success')
            ])
        ], id='wp-approve-modal', is_open=False)
        
    ], style={'padding': '20px', 'maxWidth': '1200px', 'margin': '0 auto'})

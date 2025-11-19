
import dash_bootstrap_components as dbc
from dash import dcc, html

def get_all_placeholders():
    """
    Returns a list of all placeholder components needed for callbacks.
    This centralizes placeholder definitions to prevent DuplicateIdError.
    """
    return [
        # General-purpose stores and divs. Provide small fallback text so
        # headless snapshot tools see non-empty content even before
        # callbacks complete.
        html.Div(id='modal-content'),
    html.Div(id='mp-results-area', children=html.Div('Monthly picks: loading...')),
        html.Div(id='mp-standalone-table', children=html.Div('Monthly picks table: loading...')),
        html.Div(id='mp-status', children=html.Div('')),
        html.Div(id='wp-standalone-table', children=html.Div('Weekly picks table: loading...')),
        html.Div(id='wp-status', children=html.Div('')),
        html.Div(id='wp-debug-log', children=html.Div('', style={'display': 'none'})),
        html.Div(id='mf-ping-output', children=html.Div('Forecast: loading...')),
        # visible debug badge helps Playwright detect page readiness
        html.Div(id='debug-badge', children='dashboard-ready', style={'color': '#00aaff'}),
        html.Div(id='dashboard-queued-job-output'), # Renamed from dashboard-queued-job to avoid conflict with dcc.Store
        
        # dcc.Store components for holding data
        dcc.Store(id='last-edit'),
        dcc.Store(id='dashboard-queued-job'),
        dcc.Store(id='trends-last-cached'), # Renamed from last-cached
        dcc.Store(id='rebuild-last-cached'),
        dcc.Store(id='mf-results-store'),
        dcc.Store(id='mp-current-job'),
        dcc.Store(id='mp-page-load-ts'),
        dcc.Store(id='wp-current-job'),

        # dcc.Download components
        dcc.Download(id='download-data'),
        dcc.Download(id='mf-download'),

        # dbc.Modal for details
        dbc.Modal(
            [
                dbc.ModalHeader("Detail View"),
                dbc.ModalBody(id="modal-content-body"),
                dbc.ModalFooter(dbc.Button("Close", id="close-modal", className="ml-auto")),
            ],
            id="detail-modal",
            is_open=False,
        ),

        # Intervals
    # Global poll interval used by some tabs (placeholder to avoid missing Input errors)
    dcc.Interval(id='poll-interval', interval=5 * 1000, n_intervals=0, disabled=True),
    dcc.Interval(id='mp-poll-interval', interval=5 * 1000, n_intervals=0, disabled=True),
    # Minimal placeholders used by callbacks that reference DataTable ids
    html.Div(id='results-table-client', style={'display': 'none'}),
    html.Div(id='results-table', style={'display': 'none'}),
    # Results area placeholder used by Market Trends callbacks
    html.Div(id='results-area', children=html.Div('Results area: loading...')),
    # Global store for job tracking expected by various tabs
    dcc.Store(id='current-job'),
    # Buttons and triggers expected by some callbacks
    html.Button('Refresh prices', id='mp-refresh-prices', n_clicks=0, style={'display': 'none'}),
    html.Button('Run full', id='run-btn', n_clicks=0, style={'display': 'none'}),
    # Store-based trigger used for programmatic reloads
    dcc.Store(id='reload-trigger'),
    ]

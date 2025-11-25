import dash_bootstrap_components as dbc
from dash import dcc, html


def get_all_placeholders():
    """Returns a list of all placeholder components needed for callbacks.
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
        # visible debug badge helps Playwright detect page readiness
        html.Div(id='debug-badge', children='dashboard-ready', style={'color': '#00aaff'}),
        html.Div(id='dashboard-queued-job-output'),  # Renamed from dashboard-queued-job to avoid conflict with dcc.Store

        # dcc.Store components for holding data
        dcc.Store(id='last-edit'),
        # NOTE: dashboard-queued-job Store is defined in index.py directly (removed duplicate)
        # NOTE: trends-last-cached Store is defined in index.py directly (removed duplicate)
        dcc.Store(id='trends-results-store'),
        dcc.Store(id='mt-status-store'),
        dcc.Store(id='news-store'),
        dcc.Store(id='rebuild-last-cached'),
        dcc.Store(id='mf-results-store'),
        dcc.Store(id='mp-current-job'),
        dcc.Store(id='mp-page-load-ts'),
        dcc.Store(id='wp-current-job'),

        # dcc.Download components
        dcc.Download(id='download-data'),

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
        dcc.Interval(id='mp-poll-interval', interval=5 * 1000, n_intervals=0, disabled=True),
        # Minimal placeholders for DataTables used by callbacks before tab loads
        html.Div(id='results-table-client', style={'display': 'none'}),
        html.Div(id='results-table', style={'display': 'none'}),
        # Buttons and triggers expected by some callbacks
        html.Button('Refresh prices', id='mp-refresh-prices', n_clicks=0, style={'display': 'none'}),
    ]

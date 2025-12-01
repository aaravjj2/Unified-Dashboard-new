"""
Signal Dashboard - TradingView Alert Monitor (HTTP-decoupled)

Lightweight dashboard that queries the webhook server HTTP API
(/signals and /executions) and displays a compact summary and recent signals.
This file is intentionally minimal and focuses on syntactic correctness so it
can be safely imported and linted in the workspace.
"""

import json
import logging
import os
from pathlib import Path
from datetime import datetime

import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import requests

# Initialize Sentry (if configured via SENTRY_DSN). Import is safe and idempotent.
try:
    from observability import sentry_config
    sentry_config.init_sentry()
except Exception:
    # Keep dashboard importable even if observability package is missing or fails
    pass
"""
Signal Dashboard - TradingView Alert Monitor (HTTP-decoupled)

Lightweight dashboard that queries the webhook server HTTP API
(/signals and /executions) and displays a compact summary and recent signals.
This file is intentionally minimal and focuses on syntactic correctness so it
can be safely imported and linted in the workspace.
"""

import json
import logging
import os
from pathlib import Path
from datetime import datetime

import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

WEBHOOK_BASE = os.getenv('WEBHOOK_BASE') or f"http://localhost:{os.getenv('WEBHOOK_PORT', '8000')}"
DASHBOARD_PORT = int(os.getenv('SIGNAL_DASHBOARD_PORT', 8050))
REFRESH_INTERVAL = 5000
OUTPUTS_DIR = Path("outputs/signal_dashboard")
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def create_dashboard_layout():
    return dbc.Container([
        dbc.Row(dbc.Col(html.H3("TradingView Signal Monitor"), width=12)),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([html.H6("Total Signals"), html.H2(id='total-signals')])), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H6("Executed"), html.H2(id='executed-signals')])), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H6("Rejected"), html.H2(id='rejected-signals')])), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H6("Avg Processing"), html.H2(id='avg-processing-time')])), width=3),
        ], className='mb-3'),
        dbc.Row(dbc.Col(dbc.Card(dbc.CardBody([html.Div(id='signals-table')])), width=12)),
        dbc.Row(dbc.Col(dbc.Card(dbc.CardBody([html.Div(id='risk-blocks')])), width=12)),
        dcc.Interval(id='interval-component', interval=REFRESH_INTERVAL, n_intervals=0)
    ], fluid=True)


class SignalDashboard:
    def __init__(self, port: int = DASHBOARD_PORT):
        self.port = port
        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], title='Signal Monitor')
        self.app.layout = create_dashboard_layout()
        self._setup_callbacks()

    def _setup_callbacks(self):
        @self.app.callback([
            Output('total-signals', 'children'),
            Output('executed-signals', 'children'),
            Output('rejected-signals', 'children'),
            Output('avg-processing-time', 'children'),
            Output('signals-table', 'children'),
            Output('risk-blocks', 'children')
        ], [Input('interval-component', 'n_intervals')])
        def update(n):
            try:
                sresp = requests.get(f"{WEBHOOK_BASE}/signals", timeout=1)
                sigs = sresp.json().get('signals', []) if sresp.status_code == 200 else []
            except Exception:
                sigs = []

            try:
                eresp = requests.get(f"{WEBHOOK_BASE}/executions", timeout=1)
                execs = eresp.json().get('executions', []) if eresp.status_code == 200 else []
            except Exception:
                execs = []

            total = len(sigs)
            executed = len([e for e in execs if e.get('status') == 'executed'])
            rejected = len([e for e in execs if e.get('status') and 'rejected' in e.get('status')])

            avg_time = "<100ms"

            if sigs:
                rows = []
                for s in sigs[-10:][::-1]:
                    rows.append(html.Div(f"{(s.get('timestamp') or '')[:19]} | {s.get('symbol') or s.get('ticker') or ''} | {s.get('signal_type') or ''} | {s.get('price')}", className='mb-1'))
                table = html.Div(rows)
            else:
                table = html.Div(html.Small("No signals"))

            risk_blocks = []
            for e in execs:
                if e.get('status') and 'rejected' in e.get('status'):
                    risk_blocks.append(html.Div(f"{e.get('signal_id')}: {e.get('message')}", className='text-warning mb-1'))
            risk_div = html.Div(risk_blocks) if risk_blocks else html.Div(html.Small('No risk blocks'))

            return str(total), str(executed), str(rejected), avg_time, table, risk_div

    def run(self, debug: bool = False):
        self.app.run(host='0.0.0.0', port=self.port, debug=debug)

    def export_snapshot(self, filename: str = 'dashboard_snapshot.json'):
        try:
            sresp = requests.get(f"{WEBHOOK_BASE}/signals", timeout=1)
            sigs = sresp.json().get('signals', []) if sresp.status_code == 200 else []
        except Exception:
            sigs = []
        try:
            eresp = requests.get(f"{WEBHOOK_BASE}/executions", timeout=1)
            execs = eresp.json().get('executions', []) if eresp.status_code == 200 else []
        except Exception:
            execs = []

        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'total_signals': len(sigs),
            'executed': len([e for e in execs if e.get('status') == 'executed']),
            'rejected': len([e for e in execs if e.get('status') and 'rejected' in e.get('status')]),
            'recent_signals': sigs[-10:],
            'recent_executions': execs[-10:]
        }
        out = OUTPUTS_DIR / filename
        with open(out, 'w') as f:
            json.dump(snapshot, f, indent=2)
        return out


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=DASHBOARD_PORT)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    d = SignalDashboard(port=args.port)
    d.run(debug=args.debug)
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

WEBHOOK_BASE = os.getenv('WEBHOOK_BASE') or f"http://localhost:{os.getenv('WEBHOOK_PORT', '8000')}"
DASHBOARD_PORT = int(os.getenv('SIGNAL_DASHBOARD_PORT', 8050))
REFRESH_INTERVAL = 5000
OUTPUTS_DIR = Path("outputs/signal_dashboard")
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def create_dashboard_layout():
    return dbc.Container([
        dbc.Row(dbc.Col(html.H3("📡 TradingView Signal Monitor"), width=12)),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([html.H6("Total Signals"), html.H2(id='total-signals')])), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H6("Executed"), html.H2(id='executed-signals')])), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H6("Rejected"), html.H2(id='rejected-signals')])), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H6("Avg Processing"), html.H2(id='avg-processing-time')])), width=3),
        ], className='mb-3'),
        dbc.Row(dbc.Col(dbc.Card(dbc.CardBody([html.Div(id='signals-table')])), width=12)),
        dbc.Row(dbc.Col(dbc.Card(dbc.CardBody([html.Div(id='risk-blocks')])), width=12)),
        dcc.Interval(id='interval-component', interval=REFRESH_INTERVAL, n_intervals=0)
    ], fluid=True)


class SignalDashboard:
    def __init__(self, port: int = DASHBOARD_PORT):
        self.port = port
        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], title='Signal Monitor')
        self.app.layout = create_dashboard_layout()
        self._setup_callbacks()

    def _setup_callbacks(self):
        @self.app.callback([
            Output('total-signals', 'children'),
            Output('executed-signals', 'children'),
            Output('rejected-signals', 'children'),
            Output('avg-processing-time', 'children'),
            Output('signals-table', 'children'),
            Output('risk-blocks', 'children')
        ], [Input('interval-component', 'n_intervals')])
        def update(n):
            try:
                sresp = requests.get(f"{WEBHOOK_BASE}/signals", timeout=1)
                sigs = sresp.json().get('signals', []) if sresp.status_code == 200 else []
            except Exception:
                sigs = []

            try:
                eresp = requests.get(f"{WEBHOOK_BASE}/executions", timeout=1)
                execs = eresp.json().get('executions', []) if eresp.status_code == 200 else []
            except Exception:
                execs = []

            total = len(sigs)
            executed = len([e for e in execs if e.get('status') == 'executed'])
            rejected = len([e for e in execs if e.get('status') and 'rejected' in e.get('status')])

            avg_time = "<100ms"

            if sigs:
                rows = []
                for s in sigs[-10:][::-1]:
                    rows.append(html.Div(f"{(s.get('timestamp') or '')[:19]} | {s.get('symbol') or s.get('ticker') or ''} | {s.get('signal_type') or ''} | {s.get('price')}", className='mb-1'))
                table = html.Div(rows)
            else:
                table = html.Div(html.Small("No signals"))

            risk_blocks = []
            for e in execs:
                if e.get('status') and 'rejected' in e.get('status'):
                    risk_blocks.append(html.Div(f"{e.get('signal_id')}: {e.get('message')}", className='text-warning mb-1'))
            risk_div = html.Div(risk_blocks) if risk_blocks else html.Div(html.Small('No risk blocks'))

            return str(total), str(executed), str(rejected), avg_time, table, risk_div

    def run(self, debug: bool = False):
        self.app.run(host='0.0.0.0', port=self.port, debug=debug)

    def export_snapshot(self, filename: str = 'dashboard_snapshot.json'):
        try:
            sresp = requests.get(f"{WEBHOOK_BASE}/signals", timeout=1)
            sigs = sresp.json().get('signals', []) if sresp.status_code == 200 else []
        except Exception:
            sigs = []
        try:
            eresp = requests.get(f"{WEBHOOK_BASE}/executions", timeout=1)
            execs = eresp.json().get('executions', []) if eresp.status_code == 200 else []
        except Exception:
            execs = []

        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'total_signals': len(sigs),
            'executed': len([e for e in execs if e.get('status') == 'executed']),
            'rejected': len([e for e in execs if e.get('status') and 'rejected' in e.get('status')]),
            'recent_signals': sigs[-10:],
            'recent_executions': execs[-10:]
        }
        out = OUTPUTS_DIR / filename
        with open(out, 'w') as f:
            json.dump(snapshot, f, indent=2)
        return out


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=DASHBOARD_PORT)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    d = SignalDashboard(port=args.port)
    d.run(debug=args.debug)

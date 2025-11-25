"""Serve the Volatility Lab component directly on port 8050.

This lightweight runner is for testing only (local test harness). It mounts
the layout from `financial_dashboard.components.volatility_lab` and starts a
Dash app on port 8050 so E2E tests that target http://localhost:8050 can
exercise the Volatility Lab content.
"""
import os
from dash import Dash

from financial_dashboard.components import volatility_lab as vol_comp


def create_app():
    app = Dash(__name__, suppress_callback_exceptions=True)
    try:
        app.layout = vol_comp.create_volatility_lab_layout()
        if hasattr(vol_comp, 'register_volatility_lab_callbacks'):
            try:
                vol_comp.register_volatility_lab_callbacks(app)
            except Exception:
                # swallow callback registration errors for test runner
                pass
    except Exception as e:
        # fallback minimal layout
        import dash_bootstrap_components as dbc
        from dash import html
        app.layout = dbc.Container([
            dbc.Row(dbc.Col(html.H4('Volatility Lab (failed to build)'))),
            dbc.Row(dbc.Col(html.P(str(e))))
        ], fluid=True)
    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 8050))
    print(f"Starting Volatility Test Runner on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)

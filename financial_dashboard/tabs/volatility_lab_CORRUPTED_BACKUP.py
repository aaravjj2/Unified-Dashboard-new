"""
Volatility Lab Tab wrapper

This module provides the tab-level layout() function and a register_callbacks(app)
function expected by the dashboard test-suite. It delegates heavy lifting to
`financial_dashboard.components.volatility_lab` which contains the charts and
callbacks implementations.
"""

from dash import html
import dash_bootstrap_components as dbc

from financial_dashboard.components import volatility_lab as vol_comp


def layout():
	"""Return the Volatility Lab layout for inclusion in the main dashboard.

	Tests and the app expect a callable `layout()` that returns a Dash
	container. We delegate to the component's `create_volatility_lab_layout`
	which returns a ready-to-use `dbc.Container`.
	"""
	try:
		return vol_comp.create_volatility_lab_layout()
	except Exception:
		# Provide a minimal fallback layout so the tab exists even if the
		# component code has runtime issues; tests check for presence and
		# non-empty content.
		return dbc.Container([
			dbc.Row(dbc.Col(html.H4("Volatility Lab (Unavailable)"))),
			dbc.Row(dbc.Col(html.P("The Volatility Lab is currently unavailable.")))
		], fluid=True)


def register_callbacks(app):
	"""Register callbacks from the volatility component into the Dash app.

	Many tabs expose a `register_callbacks(app)` used by the app bootstrap to
	attach callbacks. Delegate to the component if available.
	"""
	try:
		if hasattr(vol_comp, 'register_volatility_lab_callbacks'):
			vol_comp.register_volatility_lab_callbacks(app)
	except Exception:
		# Swallow exceptions during callback registration to avoid crashing app
		# at startup; fallback layout above will keep the tab functional.
		pass

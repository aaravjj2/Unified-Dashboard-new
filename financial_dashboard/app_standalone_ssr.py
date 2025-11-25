import os
import sys
import types
import logging
import traceback
from flask import Flask
from dash_extensions.enrich import Dash, dcc, html, Input, Output, MultiplexerTransform
import dash_bootstrap_components as dbc

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add project root to path to allow imports from `tabs` and `_shared`
APP_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# --- App Initialization ---
server = Flask(__name__)
app = Dash(
    __name__,
    server=server,
    transforms=[MultiplexerTransform()],
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)
app.title = "Standalone SSR Test"

# --- Layout and Callbacks ---
try:
    # Directly load the layout and callbacks from the target tab
    from tabs import market_trends
    
    # The layout function needs to be called to get the component tree
    app.layout = market_trends.layout()
    
    # Register the callbacks for the tab
    if hasattr(market_trends, 'register_callbacks'):
        # Mock the shared module if necessary
        SH = None
        try:
            from . import _shared as SH
        except ImportError:
            logging.warning("Could not import _shared module.")
        
        try:
            market_trends.register_callbacks(app, shared=SH)
        except TypeError:
            market_trends.register_callbacks(app)

    logging.info("Successfully loaded layout and callbacks from 'market_trends.py'.")

except Exception as e:
    logging.error(f"Failed to load market_trends tab: {e}")
    logging.error(traceback.format_exc())
    app.layout = html.Div([
        html.H1("Error Loading Tab"),
        html.Pre(str(e))
    ])

# --- SSR Monkey-Patch ---
if os.environ.get("DASH_TEST_SSR") == "true":
    logging.info("Applying SSR monkey-patch.")
    
    def _ssr_index(self_dash, *args, **kwargs):
        try:
            layout = self_dash.layout
            layout_html = self_dash.renderer.render(layout.to_plotly_json())
            content = f'<div id="react-entry-point"><div class="_dash-loading"><div id="_dash-app-content">{layout_html}</div></div></div>'
        except Exception as e:
            tb = traceback.format_exc()
            logging.error(f"SSR rendering failed:\n{tb}")
            content = f'<h1>Error during Server-Side Rendering</h1><pre>{tb}</pre>'

        return f'''
            <!DOCTYPE html>
            <html>
                <head>
                    <meta charset="UTF-8">
                    <title>{self_dash.title}</title>
                    {self_dash._generate_css_dist_html()}
                </head>
                <body>
                    {content}
                    <footer>
                        {self_dash._generate_config_html()}
                        {self_dash._generate_scripts_html()}
                        {self_dash._generate_renderer()}
                    </footer>
                </body>
            </html>
        '''
    app.index = types.MethodType(_ssr_index, app)

# --- Run Server ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8050))
    logging.info(f"Starting Standalone SSR Test on http://0.0.0.0:{port}")
    app.run_server(debug=True, host='0.0.0.0', port=port)

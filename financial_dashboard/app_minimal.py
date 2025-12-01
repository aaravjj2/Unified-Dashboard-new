import os
import sys
import types
import logging
import traceback
import importlib
from flask import Flask
from dash_extensions.enrich import Dash, dcc, html, Input, Output, MultiplexerTransform
import dash_bootstrap_components as dbc

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add project root to path
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
app.title = "Minimal SSR Test"

# --- Layout and Callbacks ---
try:
    from tabs import market_trends
    app.layout = market_trends.layout()
    
    SH = None
    try:
        # Attempt to import _shared for the callbacks
        shared_path = os.path.join(APP_DIR, '_shared.py')
        if os.path.exists(shared_path):
            spec = importlib.util.spec_from_file_location('Dash._shared', shared_path)
            shared_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(shared_mod)
            sys.modules['Dash._shared'] = shared_mod
            SH = shared_mod
    except Exception as e:
        logging.warning(f"Could not load _shared.py: {e}")

    if hasattr(market_trends, 'register_callbacks'):
        market_trends.register_callbacks(app, shared=SH)

    logging.info("Successfully loaded 'market_trends.py'.")

except Exception as e:
    logging.error(f"Failed to load market_trends tab: {e}")
    app.layout = html.Div(f"Error: {e}")

# --- SSR Monkey-Patch ---
if os.environ.get("DASH_TEST_SSR") == "true":
    logging.info("Applying SSR monkey-patch.")
    
    def _ssr_index(self_dash, *args, **kwargs):
        try:
            layout_html = self_dash.renderer.render(self_dash.layout.to_plotly_json())
            content = f'<div id="react-entry-point"><div class="_dash-loading"><div id="_dash-app-content">{layout_html}</div></div></div>'
        except Exception as e:
            tb = traceback.format_exc()
            content = f'<h1>SSR Error</h1><pre>{tb}</pre>'

        return f'''
            <!DOCTYPE html>
            <html>
                <head><title>{self_dash.title}</title></head>
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
    app.run_server(debug=True, host='0.0.0.0', port=port)

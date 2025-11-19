import os
import sys
import types
import logging
import importlib.util
import traceback
from flask import Flask
from dash_extensions.enrich import Dash, dcc, html, Input, Output, MultiplexerTransform
import dash_bootstrap_components as dbc

def run_app(port=8050, debug=True):
    # Basic configuration
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # App initialization
    server = Flask(__name__)
    app = Dash(
        __name__,
        server=server,
        transforms=[MultiplexerTransform()],
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True
    )
    app.title = "Simplified Dashboard"

    # --- Simplified Layout ---
    # Directly load the market_trends tab for simplicity
    TABS_DIR = os.path.join(os.path.dirname(__file__), 'tabs')
    market_trends_path = os.path.join(TABS_DIR, 'market_trends.py')
    
    try:
        spec = importlib.util.spec_from_file_location("tabs.market_trends", market_trends_path)
        mt_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mt_mod)
        
        # In SSR mode, we just take the layout directly.
        if os.environ.get("DASH_TEST_SSR") == "true":
            app.layout = mt_mod.layout()
        else:
            # For client-side rendering, we need a container to render into.
            app.layout = html.Div([
                html.H1("Dashboard"),
                dcc.Tabs(id="tabs-container", value="tab-market_trends", children=[
                    dcc.Tab(label="Market Trends", value="tab-market_trends")
                ]),
                html.Div(id="tab-content")
            ])
            # Register callback to load content
            @app.callback(Output("tab-content", "children"), Input("tabs-container", "value"))
            def render_tab(tab):
                if tab == "tab-market_trends":
                    return mt_mod.layout()
                return "Select a tab"

    except Exception as e:
        logging.error(f"Failed to load market_trends tab: {e}")
        app.layout = html.Div(f"Error loading tab: {e}")


    # --- SSR Patch ---
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
    logging.info(f"Starting Simplified Dashboard on http://0.0.0.0:{port}")
    app.run_server(debug=debug, host='0.0.0.0', port=port)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8050))
    run_app(port=port)

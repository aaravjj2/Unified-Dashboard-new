import os
import sys
import types
import logging
import importlib.util
import traceback
from flask import Flask
from dash_extensions.enrich import Dash, dcc, html, Input, Output, MultiplexerTransform
import dash_bootstrap_components as dbc

class DashboardApp:
    def __init__(self, port=8050, debug=True):
        self.port = port
        self.debug = debug
        self.SH = None
        self.TAB_MODULES = {}
        self.tab_map = []
        self.tab_items = []

        self._configure_logging()
        self._setup_paths()
        self._load_shared_module()
        
        # Initialize the app using the correct pattern for dash-extensions
        self.server = Flask(__name__)
        self.app = Dash(
            __name__,
            server=self.server,
            external_stylesheets=[dbc.themes.BOOTSTRAP, '/assets/custom.css'],
            suppress_callback_exceptions=True,
            transforms=[MultiplexerTransform()]
        )
        self.app.title = "Unified Market Dashboard"

        self._discover_tabs()
        self._build_tabs()
        self.app.layout = self._create_layout
        self._register_callbacks()
        self._apply_ssr_patch()

    def _configure_logging(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info("Starting application setup")

    def _setup_paths(self):
        self.APP_DIR = os.path.dirname(__file__)
        self.PROJECT_ROOT = os.path.abspath(os.path.join(self.APP_DIR, '..'))
        self.TABS_DIR = os.path.join(self.APP_DIR, 'tabs')
        if self.PROJECT_ROOT not in sys.path:
            sys.path.insert(0, self.PROJECT_ROOT)

    def _load_shared_module(self):
        try:
            shared_path = os.path.join(self.APP_DIR, '_shared.py')
            if os.path.exists(shared_path):
                spec = importlib.util.spec_from_file_location('Dash._shared', shared_path)
                shared_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(shared_mod)
                sys.modules['Dash._shared'] = shared_mod
                self.SH = shared_mod
        except Exception as e:
            logging.error(f"Error loading _shared.py: {e}")

    def _discover_tabs(self):
        for fn in os.listdir(self.TABS_DIR):
            if fn.endswith('.py') and not fn.startswith('__'):
                name = os.path.splitext(fn)[0]
                path = os.path.join(self.TABS_DIR, fn)
                self.TAB_MODULES[name] = {'path': path, 'mod': None}

    def _build_tabs(self):
        desired_order = ['market_trends', 'market_forecast', 'monthly_picks']
        remaining = [k for k in sorted(self.TAB_MODULES.keys()) if k not in desired_order]
        
        for key in [k for k in desired_order if k in self.TAB_MODULES] + remaining:
            label = key.replace('_', ' ').title()
            value = f'tab-{key}'
            self.tab_items.append(dcc.Tab(label=label, value=value, children=None))
            self.tab_map.append((value, key))
        logging.info(f"Prepared {len(self.tab_items)} tabs: {[t.value for t in self.tab_items]}")

    def _create_layout(self):
        initial_tab_children = self._get_initial_tab_children()
        placeholder_children = self._get_placeholder_children()

        return html.Div([
            html.H1("Unified Market Dashboard"),
            dcc.Tabs(id='tabs-container', value=self.tab_items[0].value if self.tab_items else None, children=self.tab_items),
            html.Div(id='tab-content', children=initial_tab_children),
            html.Div(placeholder_children, id='global-placeholders', style={'display': 'none'}),
        ])

    def _get_initial_tab_children(self):
        if not (os.environ.get("DASH_TEST_SSR") == "true" and self.tab_map):
            return []

        logging.info("SSR is enabled. Pre-loading initial tab content.")
        first_tab_key = self.tab_map[0][1]
        mod = self._load_tab_module(first_tab_key)

        if mod and hasattr(mod, 'layout'):
            try:
                layout = mod.layout(is_tab=True) if callable(mod.layout) else mod.layout
                children = layout.children if hasattr(layout, 'children') else [layout]
                
                GLOBAL_PLACEHOLDER_IDS = {'status', 'job-history', 'download-btn', 'poll-interval'}
                return [child for child in children if not (hasattr(child, 'id') and child.id in GLOBAL_PLACEHOLDER_IDS)]
            except Exception as e:
                logging.error(f"Error generating initial layout for '{first_tab_key}': {e}")
        return []

    def _get_placeholder_children(self):
        return [
            html.Div(id='status'),
            dcc.Store(id='job-history'),
            dcc.Download(id='download-btn'),
            dcc.Interval(id='poll-interval', interval=5*1000, n_intervals=0),
        ]

    def _load_tab_module(self, key):
        entry = self.TAB_MODULES.get(key)
        if entry and entry['mod'] is None:
            try:
                fullname = f'Dash.tabs.{key}'
                spec = importlib.util.spec_from_file_location(fullname, entry['path'])
                mod = importlib.util.module_from_spec(spec)
                sys.modules[fullname] = mod
                spec.loader.exec_module(mod)
                entry['mod'] = mod
                
                if hasattr(mod, 'register_callbacks'):
                    mod.register_callbacks(self.app, shared=self.SH)
            except Exception as e:
                logging.error(f"Failed to load or register callbacks for tab '{key}': {e}")
                return None
        return entry['mod'] if entry else None

    def _register_callbacks(self):
        @self.app.callback(Output('tab-content', 'children'), [Input('tabs-container', 'value')])
        def render_tab(tab_value):
            if not tab_value:
                return []
            
            key = next((k for v, k in self.tab_map if v == tab_value), None)
            if not key:
                return "404 - Tab not found"

            mod = self._load_tab_module(key)
            if mod and hasattr(mod, 'layout'):
                return mod.layout(is_tab=True) if callable(mod.layout) else mod.layout
            return f"Failed to load layout for {key}"

    def _apply_ssr_patch(self):
        if os.environ.get("DASH_TEST_SSR") != "true":
            return

        logging.info("Applying SSR monkey-patch to Dash.index for testing.")
        
        def _ssr_index(self_dash, *args, **kwargs):
            try:
                layout = self_dash.layout()
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
                        {self_dash._generate_meta_html()}
                        <title>{self_dash.title}</title>
                        {self_dash._generate_css_dist_html()}
                        {self_dash._generate_favicon_html()}
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
        self.app.index = types.MethodType(_ssr_index, self.app)

    def run(self):
        logging.info(f"Starting Unified Dashboard on http://0.0.0.0:{self.port}")
        self.app.run_server(debug=self.debug, host='0.0.0.0', port=self.port)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8050))
    app_instance = DashboardApp(port=port)
    app_instance.run()

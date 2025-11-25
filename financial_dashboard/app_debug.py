import os
import sys
import importlib.util
import traceback
import json
import time
import types
import logging
from dash import Dash, dcc, html, Input, Output, State, dash_table
from dash.exceptions import PreventUpdate
from flask import jsonify, request
import dash_bootstrap_components as dbc
from flask_caching import Cache

# New import for the centralized placeholder system
from layout_placeholders import get_all_placeholders

APP_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, '..'))
TABS_DIR = os.path.join(APP_DIR, 'tabs')

# make project root importable (many modules expect repo root on sys.path)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def safe_load_module(path, name=None):
    if not os.path.exists(path):
        return None
    try:
        name = name or os.path.splitext(os.path.basename(path))[0]
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        print(f"Failed to load module from {path}")
        traceback.print_exc()
        return None


# Shared helpers object (simple shim to the repo _shared.py if present)
SH = None
try:
    import _shared as SH_local
    SH = SH_local
except Exception:
    SH = type('SHShim', (), {})()


app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app._allow_dynamic_callbacks = True
server = app.server

# A special route just for logging
@server.route('/log-message', methods=['POST'])
def log_message():
    # Get the message sent from the browser
    message = request.json.get('message', 'No message received')
    
    # Print the message to your VS Code terminal logs
    print(f"--- LOG FROM BROWSER: {message} ---")
    
    # Send a confirmation back to the browser
    return {"status": "Message received and logged"}

# Simple filesystem cache for quick reads (can be swapped to Redis in prod)
cache = Cache(server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': os.path.join(APP_DIR, 'cache')
})


# Discover available tab modules in tabs/
# Ensure a package-like entry for 'Dash' exists so relative imports inside
# tab modules (e.g. `from .. import _shared`) can resolve to Dash._shared.
if 'Dash' not in sys.modules:
    pkg = types.ModuleType('Dash')
    pkg.__path__ = [APP_DIR]
    sys.modules['Dash'] = pkg
# create Dash.tabs package entry
if 'Dash.tabs' not in sys.modules:
    tabs_pkg = types.ModuleType('Dash.tabs')
    tabs_pkg.__path__ = [TABS_DIR]
    sys.modules['Dash.tabs'] = tabs_pkg

# Load repo _shared.py into sys.modules as Dash._shared so relative imports
# inside tabs like `from .. import _shared as SH` will find it.
shared_path = os.path.join(APP_DIR, '_shared.py')
if os.path.exists(shared_path):
    try:
        spec = importlib.util.spec_from_file_location('_shared', shared_path)
        shared_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(shared_mod)
        sys.modules['_shared'] = shared_mod
        # also expose as SH variable for local use
        SH = shared_mod
        # expose under the Dash package name so handlers that look
        # up 'Dash._shared' (used elsewhere) will find the module.
        try:
            sys.modules['Dash._shared'] = shared_mod
        except Exception:
            pass
    except Exception:
        print('Failed to load _shared')
        traceback.print_exc()

# All placeholder generation logic is now removed from here.
# The logic for pre-loading trends cache can remain if needed, but the
# complex layout-related logic is gone.

TAB_MODULES = {}
for fn in os.listdir(TABS_DIR):
    if fn.endswith('.py') and not fn.startswith('__'):
        path = os.path.join(TABS_DIR, fn)
        name = os.path.splitext(fn)[0]
        # Store path and leave module unloaded until the tab is activated
        # Modules will be imported and their register_callbacks called lazily
        # inside `get_tab_children` to avoid premature callback registration
        # which can cause client-side invalid-prop/ReferenceError issues.
        TAB_MODULES[name] = {'path': path, 'mod': None}

# Eagerly load all tab modules and register callbacks at startup
for key, entry in TAB_MODULES.items():
    try:
        mod = safe_load_module(entry['path'], name=f'tabs.{key}')
        if mod:
            entry['mod'] = mod
            if hasattr(mod, 'register_callbacks'):
                mod.register_callbacks(app)
    except Exception:
        print(f"Failed to load or register callbacks for {key}")
        traceback.print_exc()
        
print("TAB_MODULES:", TAB_MODULES)


# Build tabs list from discovered modules (preserve ordering)
tab_items = []
tab_map = []

# Desired tab ordering: show Trends first, then Forecast, then Monthly Picks.
# Any additional tab modules will be appended after these.
desired_order = ['market_trends', 'market_forecast', 'monthly_picks']

# iterate desired order first, then any remaining tabs alphabetically
remaining = [k for k in sorted(TAB_MODULES.keys()) if k not in desired_order]
for key in [k for k in desired_order if k in TAB_MODULES] + remaining:
    label = key.replace('_', ' ').title()
    value = f'tab-{key}'
    entry = TAB_MODULES.get(key)
    mod = entry.get('mod') if entry else None

    # Do NOT embed module layout into the Tab children. The active tab's
    # content will be rendered into the `tab-content` container by the
    # `render_tab_content` callback. Embedding layouts here previously led to
    # DuplicateIdError when the same components were also rendered by the
    # callback.
    tab_items.append(dcc.Tab(label=label, value=value, children=None))
    tab_map.append((value, key))
print("tab_items:", tab_items)

# The main application layout is now much simpler.
# It includes the tabs container and a div for tab content, wrapped in a Loading component.
# All placeholders are injected from our centralized function.
app.layout = dbc.Container([
    html.H2('Unified Market Dashboard'),
    dcc.Tabs(id='tabs', value=tab_items[0].value if tab_items else None, children=tab_items),
    html.Div(id='tab-content', style={'marginTop': '12px'}),
    # Inject global placeholders (hidden) so callbacks that reference
    # commonly-used ids like 'poll-interval' and stores can register
    # without causing ReferenceError on the client renderer.
    html.Div(get_all_placeholders(), style={'display': 'none'}),
], fluid=True)


@app.callback(Output('tab-content', 'children'), Input('tabs', 'value'))
def render_tab_content(value):
    if not value:
        return html.Div('No tabs available')
    # find module key for this tab value
    key = None
    for v, k in tab_map:
        if v == value:
            key = k
            break
    if not key:
        return html.Div('Unknown tab')
    entry = TAB_MODULES.get(key)
    if entry is None:
        return html.Div(f'Module {key} not found')
    mod = entry.get('mod')
    # Module should be pre-loaded now, but check just in case
    if mod is None:
        return html.Div(f'Module {key} is not loaded')
    # call layout() if present, otherwise return a placeholder
    try:
        base_layout = None
        if hasattr(mod, 'layout') and callable(mod.layout):
            base_layout = mod.layout()
        elif hasattr(mod, 'LAYOUT'):
            base_layout = getattr(mod, 'LAYOUT')
        else:
            return html.Div(f'Module {key} has no layout() or LAYOUT')

        # Inject only the placeholders relevant for this tab into the returned layout.
        # This keeps placeholder components inside the visible tab content so
        # callbacks that target those IDs will populate visible children.
        try:
            placeholders = get_all_placeholders()
            # map common prefixes to tab keys
            prefix_map = {
                'monthly_picks': 'mp-',
                'weekly_picks': 'wp-',
                'market_forecast': 'mf-',
                'market_trends': 'mt-',
                'market_trends_rebuild': 'rebuild-'
            }
            prefix = prefix_map.get(key)
            if prefix:
                matched = []
                for comp in placeholders:
                    cid = getattr(comp, 'id', None)
                    if not cid:
                        try:
                            cid = comp.props.get('id')
                        except Exception:
                            cid = None
                    if cid and cid.startswith(prefix):
                        matched.append(comp)
                if matched:
                    # Return a container that includes the module layout and
                    # the matched placeholders so callbacks can populate them.
                    return html.Div([base_layout, html.Div(matched)])
        except Exception:
            # If placeholder injection fails, fall back to returning the base layout
            traceback.print_exc()

        # If the module returned an effectively-empty layout (no visible
        # children), provide a lightweight visible fallback so the client
        # and headless captures don't see an empty #tab-content. This is a
        # short-term safeguard while we track down duplicate-callback
        # registrations that are preventing callbacks from populating
        # content.
        def _is_empty_layout(comp):
            if comp is None:
                return True
            try:
                # components expose .children; treat empty/None/[] as empty
                c = getattr(comp, 'children', None)
                if c is None:
                    return True
                if isinstance(c, (list, tuple)) and len(c) == 0:
                    return True
                return False
            except Exception:
                return False

        if _is_empty_layout(base_layout):
            return html.Div([html.H4(label if (label:=key.replace('_',' ').title()) else 'Tab'), html.Div('Loading content...', style={'color': '#666'})])

        return base_layout
    except Exception:
        traceback.print_exc()
        return html.Div(f'Error rendering {key}')


# Populate initial tab content now that render_tab_content is defined.
# NOTE: synchronous server-side population removed. We rely on client-side
# rendering of tabs to avoid duplicate component instances and ensure
# callbacks bind correctly. A client-side MutationObserver (assets/tab_ready.js)
# will emit a `#tab-ready` marker when the tab content is populated so
# headless capture scripts can wait deterministically.


if __name__ == '__main__':
    # Allow overriding the bind port via environment (e.g. PORT=8600)
    host = '0.0.0.0'
    # Prefer common env vars; fall back to the original default 8050
    try:
        port = int(os.environ.get('PORT') or os.environ.get('DASH_PORT') or 8050)
    except Exception:
        port = 8050
    print(f'Starting Unified Dashboard on http://{host}:{port}')
    # Bind to host/port and disable the debug reloader so the server is stable
    # for headless browser smoke tests.
    app.run(debug=False, host=host, port=port, use_reloader=False)
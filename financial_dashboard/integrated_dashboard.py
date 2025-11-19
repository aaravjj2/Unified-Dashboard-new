"""
Integrated Financial Dashboard - import-time shim

This module provides a thin wrapper that imports the canonical Dash
app (from `index.py` or `app.py`) and post-processes its layout to ensure
tab panes have stable element ids. We avoid injecting arbitrary `data-*`
attributes here because some component versions (for example,
`dash_bootstrap_components==2.0.4`) do not accept unknown props and will
raise errors during rendering.
"""

import logging
import os
import ast
from typing import Any

try:
    # Defer importing Dash html until the runtime provides it
    from dash import html
except Exception:  # pragma: no cover - environment imports may vary
    html = None
"""
Integrated Financial Dashboard - import-time shim

This module provides a thin wrapper that imports the canonical Dash
app (from `index.py` or `app.py`) and post-processes its layout to ensure
tab panes have stable element ids. We avoid injecting arbitrary `data-*`
attributes here because some component versions (for example,
`dash_bootstrap_components==2.0.4`) do not accept unknown props and will
raise errors during rendering.
"""

import logging
import os
import ast
from typing import Any

try:
    # Defer importing Dash html until the runtime provides it
    from dash import html
except Exception:  # pragma: no cover - environment imports may vary
    html = None

logger = logging.getLogger(__name__)

# Import the canonical app from index.py (which builds the Dash app)
try:
    # index.py exposes `app` and `server` and a create_layout function
    from .index import app, server, create_layout as _create_layout
except Exception:
    # Fallbacks for alternate layouts
    try:
        from .app import app, server

        _create_layout = getattr(app, 'layout', lambda: None)
    except Exception:
        app = None
        server = None
        _create_layout = lambda: None


def _ensure_test_attrs(layout: Any) -> Any:
    """Walk the returned layout and add stable ids to tab pane containers.

    We don't add `data-test-id` attributes here to avoid passing unexpected
    kwargs into component constructors at import time.
    """
    if layout is None or html is None:
        return layout

    def _safe_get_props(node):
        # Try common places where component props live
        return getattr(node, 'props', None) or getattr(node, '__dict__', None) or {}

    def walk(node):
        try:
            # If node is already a plain dict (serialized component), skip mutation
            if isinstance(node, dict):
                return
            props = _safe_get_props(node)
            if isinstance(props, dict):
                tab_id = props.get('tab_id') or props.get('tabId') or props.get('id')
                if isinstance(tab_id, str) and str(tab_id).startswith('tab-'):
                    children = props.get('children')
                    if children is not None:
                        try:
                            # Wrap children in a Div with a stable id (best-effort).
                            props['children'] = html.Div(
                                children=children,
                                id=f"tab-pane-{str(tab_id).replace('tab-', '')}",
                            )
                        except Exception:
                            # Be defensive: if dash.html is not available or props can't be mutated
                            pass
                # Recurse into children
                children = props.get('children')
                if children:
                    if isinstance(children, (list, tuple)):
                        for c in children:
                            walk(c)
                    else:
                        walk(children)
        except Exception:
            # Swallow to avoid breaking the import-time shim
            return

    try:
        walk(layout)
    except Exception:
        logger.exception('Error ensuring test attrs on layout')
    return layout


# Apply the layout transformation at import time so downstream callers
# see the modified layout. Use a deterministic approach driven by
# TAB_CONFIG when possible. This is more robust than attempting to
# infer tab components by inspecting arbitrary props.
def _apply_layout_transform():
    if not (_create_layout and callable(_create_layout)):
        return
    try:
        layout = _create_layout()

        # If TAB_CONFIG is available and lists tab ids, use it to map
        # to the constructed Tabs component. We look for the first
        # Tabs-like component in the layout and then align its children
        # to TAB_CONFIG entries.
        try:
            cfg_ids = [str(t.get('id') or t.get('tab_id') or t.get('tabId') or t.get('tab')) for t in TAB_CONFIG]
        except Exception:
            cfg_ids = []

        def _is_tabs_component(node):
            # Heuristic: dash-bootstrap-components Tabs has _type 'Tabs' or a class name 'Tabs'
            try:
                # Skip serialized dict nodes
                if isinstance(node, dict):
                    return False
                cls = getattr(node, '__class__', None)
                if cls is not None:
                    name = getattr(cls, '__name__', '')
                    if 'Tabs' in name:
                        return True
                # Fallback: check props for 'children' that look like Tab elements
                props = getattr(node, 'props', None) or getattr(node, '__dict__', None) or {}
                if isinstance(props, dict) and isinstance(props.get('children'), (list, tuple)):
                    # quick check for child with tab_id or tabId
                    for c in props.get('children'):
                        try:
                            p = getattr(c, 'props', None) or getattr(c, '__dict__', None) or {}
                            if isinstance(p, dict) and any(k in p for k in ('tab_id', 'tabId', 'tab')):
                                return True
                        except Exception:
                            continue
            except Exception:
                return False
            return False

        def _wrap_children_with_ids(tabs_node):
            # Attempt to align each child Tab with a TAB_CONFIG id and
            # wrap its children in an html.Div with stable id.
            try:
                # Avoid operating on plain dicts (serialized components)
                if isinstance(tabs_node, dict):
                    return
                props = getattr(tabs_node, 'props', None) or getattr(tabs_node, '__dict__', None) or {}
                children = props.get('children') if isinstance(props, dict) else None
                if not children:
                    return
                # If cfg_ids available and lengths match, align by index.
                if cfg_ids and len(cfg_ids) == len(children):
                    for i, child in enumerate(children):
                        tab_id = cfg_ids[i]
                        try:
                            # Try to fetch child's props and replace children
                            cprops = getattr(child, 'props', None) or getattr(child, '__dict__', None) or {}
                            inner = cprops.get('children') if isinstance(cprops, dict) else None
                            if inner is not None and html is not None:
                                cprops['children'] = html.Div(children=inner, id=f"tab-pane-{str(tab_id).replace('tab-', '')}")
                        except Exception:
                            continue
                else:
                    # Best-effort: if cfg_ids not helpful, scan children for tab_id prop
                    for child in children:
                        try:
                            cprops = getattr(child, 'props', None) or getattr(child, '__dict__', None) or {}
                            if isinstance(cprops, dict):
                                tab_id = cprops.get('tab_id') or cprops.get('tabId') or cprops.get('id')
                                if tab_id and isinstance(tab_id, str) and tab_id.startswith('tab-') and html is not None:
                                    inner = cprops.get('children')
                                    if inner is not None:
                                        cprops['children'] = html.Div(children=inner, id=f"tab-pane-{str(tab_id).replace('tab-', '')}")
                        except Exception:
                            continue
            except Exception:
                logger.exception('Error wrapping Tabs children')

        # Walk layout to find Tabs-like component and apply wrapping
        def walk_and_apply(node):
            try:
                if node is None:
                    return False
                if _is_tabs_component(node):
                    _wrap_children_with_ids(node)
                    return True
                # Recurse into children
                props = getattr(node, 'props', None) or getattr(node, '__dict__', None) or {}
                children = None
                if isinstance(props, dict):
                    children = props.get('children')
                elif hasattr(node, 'children'):
                    children = getattr(node, 'children')
                if isinstance(children, (list, tuple)):
                    for c in children:
                        if walk_and_apply(c):
                            return True
                else:
                    return walk_and_apply(children)
            except Exception:
                return False
            return False

        walk_and_apply(layout)

        # Finally apply the original best-effort walker for other cases
        layout = _ensure_test_attrs(layout)

        if app is not None:
            try:
                app.layout = lambda: layout
            except Exception:
                app.layout = layout
    except Exception:
        logger.exception('Failed to create wrapped layout')


# Run transformation at import time
_apply_layout_transform()


# Expose app/server for external runners and TAB_CONFIG for tests
try:
    # Prefer local package import
    from .index import TAB_CONFIG
except Exception:
    # Fallback: parse the TAB_CONFIG literal from index.py without executing it
    TAB_CONFIG = []
    index_path = os.path.join(os.path.dirname(__file__), 'index.py')
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            src = f.read()
        tree = ast.parse(src, filename=index_path)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if getattr(target, 'id', None) == 'TAB_CONFIG':
                        try:
                            TAB_CONFIG = ast.literal_eval(node.value)
                        except Exception:
                            TAB_CONFIG = []
                        break
            if TAB_CONFIG:
                break
    except Exception:
        TAB_CONFIG = []

__all__ = ['app', 'server', 'TAB_CONFIG']


if __name__ == '__main__':
    # Run the Dash server
    app.run_server(host='0.0.0.0', port=8050, debug=True)

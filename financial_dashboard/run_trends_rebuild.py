"""
Runner for the rebuild Trends tab.
Creates a minimal Dash app, mounts the `market_trends_rebuild` layout and
registers callbacks, then runs on port 8060.
"""
import os
import sys
import subprocess
from dash import Dash

# ensure repo root on path if needed
APP_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, '..'))
# ensure project root on sys.path so modules using package-relative imports
# such as `from .. import _shared` resolve correctly when importing from
# the `tabs` package.
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Create a package stub for 'Dash' so `from Dash.tabs import ...` style
# resolves when modules expect the app to be a package.
if 'Dash' not in sys.modules:
    import types
    pkg = types.ModuleType('Dash')
    pkg.__path__ = [APP_DIR]
    sys.modules['Dash'] = pkg

try:
    # Load the rebuild module directly by file path to avoid importing the
    # full `Dash.tabs` package (which imports other heavy modules). This
    # keeps the runner lightweight and prevents long import stalls.
    import importlib.util
    mt_path = os.path.join(APP_DIR, 'tabs', 'market_trends_rebuild.py')
    spec = importlib.util.spec_from_file_location('market_trends_rebuild', mt_path)
    mt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mt)
except Exception as e:
    print('Failed to import tabs.market_trends_rebuild by path:', e)
    raise

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Small request logger to help debugging client->server activity. This
# will print method/path and (for JSON POSTs) the JSON payload so we can
# observe whether the browser sent the callback update.
@server.before_request
def _log_incoming_request():
    try:
        from flask import request
        if request.method == 'POST' and request.path.startswith('/_dash-update-component'):
            try:
                payload = request.get_json(silent=True)
            except Exception:
                payload = None
            print(f"INCOMING DASH POST: path={request.path} json_keys={list(payload.keys()) if isinstance(payload, dict) else type(payload)}")
    except Exception:
        # Best-effort logging; don't break the app on failures here
        pass

# mount layout (standalone mode)
app.layout = mt.layout(is_tab=False)

# register callbacks (pass None for SH for now)
try:
    if hasattr(mt, 'register_callbacks'):
        mt.register_callbacks(app, sh=None)
        print('Registered rebuild callbacks')
except Exception as e:
    print('Error registering callbacks:', e)

def _run_server_foreground(port):
    host = os.environ.get('TRENDS_REBUILD_HOST', '127.0.0.1')
    print(f"Starting Trends rebuild app on http://{host}:{port}")
    # When running in foreground we let Flask/Dash print to stdout
    app.run(host=host, port=port, debug=False)


def _spawn_background(port, logpath='/tmp/rebuild.log'):
    # Spawn a detached background process that runs this script without
    # re-entering this branch. Use setsid to detach from controlling TTY.
    python = sys.executable or 'python3'
    cmd = [python, os.path.abspath(__file__), '--no-daemon']
    # Ensure log directory exists
    try:
        d = os.path.dirname(logpath)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
        lf = open(logpath, 'a')
    except Exception:
        lf = open('/dev/null', 'w')

    # Start detached
    proc = subprocess.Popen(cmd, stdout=lf, stderr=lf, preexec_fn=os.setsid)
    print(f'Started background Trends rebuild (pid={proc.pid}), logs -> {logpath}')
    return proc.pid


if __name__ == '__main__':
    port = int(os.environ.get('TRENDS_REBUILD_PORT', '8060'))
    # If user passed --no-daemon explicitly, run in foreground. Otherwise
    # background by default unless TRENDS_REBUILD_BACKGROUND=0 is set.
    args = sys.argv[1:]
    no_daemon = '--no-daemon' in args or os.environ.get('TRENDS_REBUILD_BACKGROUND') == '0'
    if not no_daemon:
        # spawn background and exit parent
        _spawn_background(port)
        sys.exit(0)
    else:
        _run_server_foreground(port)

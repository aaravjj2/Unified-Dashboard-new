"""Standalone runner for the Market Forecast Dash tab.
This script loads Dash/_shared.py and Dash/tabs/market_forecast.py via file-loader
and starts a Dash app that serves only the Forecast tab (port 8052).
"""
import os
import importlib.util
from dash import Dash
from flask import request, got_request_exception
from flask import send_from_directory
import time
import traceback

base = os.path.dirname(__file__)

def _load_mod(path, name=None):
    try:
        name = name or os.path.splitext(os.path.basename(path))[0]
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:
        print('load_mod failed', path, e)
        return None

sh_path = os.path.join(base, '_shared.py')
mf_path = os.path.join(base, 'tabs', 'market_forecast.py')

SH = _load_mod(sh_path, 'Dash._shared')
market_forecast_tab = _load_mod(mf_path, 'Dash.tabs.market_forecast')

app = Dash(__name__, suppress_callback_exceptions=True)


# simple request logger to help diagnose client requests (writes to forecast_debug.log)
def _req_log(msg: str):
    try:
        base = os.path.dirname(__file__)
        fn = os.path.join(base, '..', 'forecast_debug.log')
        fn = os.path.abspath(fn)
        with open(fn, 'a', encoding='utf-8') as fh:
            fh.write(f"{time.time()} {msg}\n")
    except Exception:
        pass


@app.server.before_request
def _log_request():
    try:
        _req_log(f"REQ {request.method} {request.path} args={dict(request.args)}")
    except Exception:
        pass


def _log_exception(sender, exception, **extra):
    try:
        _req_log('EXCEPTION ' + traceback.format_exc())
    except Exception:
        pass


got_request_exception.connect(_log_exception, app.server)

if market_forecast_tab is not None:
    try:
        app.layout = market_forecast_tab.layout()
        if hasattr(market_forecast_tab, 'register_callbacks'):
            # market_forecast register_callbacks takes only (app), not (app, SH)
            market_forecast_tab.register_callbacks(app)
            print('Registered market_forecast_tab callbacks')
        else:
            print('market_forecast_tab.register_callbacks missing')
    except Exception as e:
        print('Failed to mount market_forecast_tab:', e)
        import traceback
        traceback.print_exc()
        app.layout = market_forecast_tab.layout() if market_forecast_tab is not None else None
else:
    app.layout = None

print('Starting Market Forecast app on http://127.0.0.1:8052')
# Serve output images from the shared OUT_ROOT and repo forecast_outputs to avoid file:// blocking in browsers
try:
    out_root = getattr(SH, 'OUT_ROOT', None)
    proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    @app.server.route('/outputs/<path:fname>')
    def _serve_output_file(fname):
        # try shared OUT_ROOT first
        try:
            if out_root and os.path.exists(os.path.join(out_root, fname)):
                return send_from_directory(out_root, fname)
        except Exception:
            pass
        # fallback to repo-level forecast_outputs
        try:
            repo_dir = os.path.join(proj_root, 'forecast_outputs')
            if os.path.exists(os.path.join(repo_dir, fname)):
                return send_from_directory(repo_dir, fname)
        except Exception:
            pass
        return ('Not found', 404)
except Exception:
    pass
try:
    print("Starting Market Forecast app on http://0.0.0.0:8051")
    app.run(host='0.0.0.0', port=8051, debug=False)
except Exception as e:
    print('Failed to start server:', e)

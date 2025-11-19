"""Start the Dash unified dashboard and optional auxiliary services in foreground.
This mirrors the `Gradio/run_all_services.py` pattern: start the dashboard in the
foreground (so Ctrl+C in the terminal stops children) and optionally start the
legacy Trends server (if requested) and other services.
"""
import argparse
import subprocess
import sys
import signal
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOGS = ROOT / 'logs'
LOGS.mkdir(exist_ok=True)

PYTHON = sys.executable

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--start-trends', action='store_true', help='Also start the legacy market_trends_dash.py as a separate process')
parser.add_argument('--open-browser', action='store_true', help='Open http://127.0.0.1:8051 after starting the dashboard')
parser.add_argument('--browser-path', type=str, default='', help='Optional explicit browser executable to open the UI')
args, _ = parser.parse_known_args()

p_dashboard = None
p_trends = None

try:
    print('Starting unified dashboard (foreground)...')
    p_dashboard = subprocess.Popen([PYTHON, str(ROOT / 'market_dashboard.py')], cwd=str(ROOT))
    print('dashboard pid', p_dashboard.pid)
except Exception as e:
    print('Failed to start dashboard', e)

if args.start_trends:
    try:
        print('Starting legacy Trends server in background...')
        p_trends = subprocess.Popen([PYTHON, str(ROOT / 'market_trends_dash.py')], cwd=str(ROOT))
        print('trends pid', p_trends.pid)
    except Exception as e:
        print('Failed to start trends', e)

def _terminate_children(grace=1.0):
    children = [p_dashboard, p_trends]
    print('Terminating children:', [p.pid for p in children if p is not None])
    for p in children:
        if p is None:
            continue
        try:
            p.terminate()
        except Exception:
            pass
    time.sleep(grace)
    for p in children:
        if p is None:
            continue
        try:
            if p.poll() is None:
                p.kill()
        except Exception:
            pass


def _signal_handler(signum, frame):
    print(f'Received signal {signum}, shutting down...')
    _terminate_children()
    sys.exit(0)

signal.signal(signal.SIGINT, _signal_handler)
try:
    signal.signal(signal.SIGTERM, _signal_handler)
except Exception:
    pass

try:
    for p in [p_dashboard, p_trends]:
        if p is not None:
            p.wait()
except KeyboardInterrupt:
    print('Interrupted, terminating children')
    _terminate_children()
    print('Exited')

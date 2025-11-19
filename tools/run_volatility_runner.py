"""Run the Volatility Lab test runner with repo-root import path.

Use this when running the runner from arbitrary CWDs or from background jobs so
the `financial_dashboard` package is importable.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from financial_dashboard.run_volatility_on_8050 import create_app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8050)), debug=False)

TODOs for Agent-1A (callback migration & wiring)

1. Market Trends callbacks migration
   - File: `financial_dashboard/tabs/market_trends.py`
   - Action: Move `@app.callback` functions into `financial_dashboard/tabs/market_trends_pkg/callbacks.py`.
   - Notes: Update imports inside moved functions to use `from .data import ...` and `from .components import ...`.
   - Rationale: Eliminates heavy imports at module import time. Do NOT change decorator signatures.

2. Admin diagnostics registration
   - File: `financial_dashboard/app.py`
   - Action: Optionally register the admin blueprint by adding:
     ```python
     from api.admin_diagnostics import admin_bp
     server.register_blueprint(admin_bp)
     ```
   - Notes: Coordinate with security team before exposing endpoints.

3. Update tab loader
   - File: (loader may be `financial_dashboard/index.py` or `financial_dashboard/callbacks.py`)
   - Action: When ready, update the loaded_tabs mapping for market_trends to point to `financial_dashboard.tabs.market_trends_pkg` as the module providing `create_layout()`.


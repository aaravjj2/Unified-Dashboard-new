Market Trends migration summary

What moved:
- Created `financial_dashboard/tabs/market_trends_pkg/` with:
  - `layout.py`: pure layout builder, lazy data use
  - `components.py`: UI helper components
  - `data.py`: heavy imports and I/O moved here (lazy functions)
  - `callbacks.py`: shim (no-op) and TODO for Agent-1A

Why:
- Prevent import-time side effects and centralize heavy I/O.
- Provide a migration path for Agent-1A to move callback code into a per-tab callbacks.py that imports from `data` and `components`.

How Agent-1A should proceed:
1. Move callback definitions from `financial_dashboard/tabs/market_trends.py` into `financial_dashboard/tabs/market_trends_pkg/callbacks.py`.
2. Update imports inside those callback functions to use `from .data import ...` and `from .components import ...`.
3. Replace tab loader to point to `financial_dashboard.ttabs.market_trends_pkg.create_layout` (or change `loaded_tabs` mapping) — coordinate with AGENT-2A for exact loader change.

Notes & TODOs for Agent-1A:
- TODO: update any `@app.callback` definitions to be present in the new callbacks.py file. Please avoid changing decorator signatures.
- TODO: wire the blueprint `api/admin_diagnostics.py` into the Flask app after review.

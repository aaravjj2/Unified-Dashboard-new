# Structural Isolation Blueprint

Proposal:
- Per-tab package under `financial_dashboard/tabs/<tab_name>/` with:
  - `layout.py` (creates layout only)
  - `callbacks.py` (register_callbacks(app) only)
  - `components.py` (UI helper components)
  - `data.py` (tab-local data loaders)
- No cross-imports between tabs: use dependency injection via a `services` module.
- Namespacing IDs: prefix all IDs with tab shortnames (e.g., `mt-`, `rl-`).
- Central tab registry: a single `callbacks.register_all_callbacks` drives per-tab `register_callbacks` and tracks registered tabs to prevent duplicates.

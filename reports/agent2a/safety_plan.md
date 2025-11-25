# System Safety Plan

Measures to prevent callback duplication and cross-tab leakage:
- Enforce `register_callbacks(app)` signature per tab.
- Static pre-merge hook: run analyzer to fail on duplicated IDs or cross-tab imports.
- CI job: run `python -m tools.analysis.agent2a_analysis` and block on non-zero exit if leaks found.
- Lint rules: ruff + custom flake plugin to prohibit imports from `financial_dashboard.tabs.*` across tabs.
- Runtime guard: app._registered_tabs set on app instance (already present) plus check to prevent re-registration.

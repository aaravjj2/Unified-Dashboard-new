Volatility Lab remediation

- Target: financial_dashboard/tests/test_e2e_complete.py::test_volatility_lab_layout_defined
- Problem: `financial_dashboard/tabs/volatility_lab.py` was empty which caused the Dash app and E2E tests to report "Volatility Lab layout is not defined".
- Fixes applied:
  - Added `financial_dashboard/tabs/volatility_lab.py` wrapper delegating to `financial_dashboard.components.volatility_lab.create_volatility_lab_layout()` and registering callbacks if present. Provides a fallback layout in case of runtime errors.
  - Updated `financial_dashboard/tabs/__init__.py` to export `volatility_lab`.
  - Added unit test `financial_dashboard/tests/test_volatility_tab.py`.
- Verification:
  - Started Market Forecast app (8051) and unified dashboard.
  - Used Playwright to click "⚡ Volatility Lab" and confirmed content loaded (no 'undefined').
  - Ran focused pytest for `test_volatility_lab_layout_defined` and it passed.

Notes:
- Consider adding unit tests for helper functions in `components/volatility_lab.py` and applying wrapper pattern to other tabs if needed.

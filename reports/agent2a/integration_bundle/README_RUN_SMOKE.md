# Integration smoke run - README

This README describes the minimal steps Agent-1A should run after callback fixes are deployed locally. These are non-invasive instructions to reproduce the smoke checks we produced.

Prerequisites
- Python 3.10+
- Repo checked out at project root
- Ensure required dev packages are installed (Playwright optional for full scan):

pip install -r requirements-dev.txt || true
# Install Playwright and browsers only if you intend to run the ID->page scan
pip install playwright || true
playwright install || true

Artifacts produced by this bundle (already in `reports/agent2a`):
- `reports/agent2a/integration_bundle/mock_bento_predict.json` - sample predict output
- `reports/agent2a/integration_bundle/mock_bento_info.json` - mock Bento root info
- `reports/agent2a/integration_bundle/admin_callback_map.json` - admin callback map (may be empty until admin blueprint registered)
- `reports/agent2a/integration_bundle/ids_registry.json` - Playwright ID registry used for scan

Quick commands (run from repo root)

1) Start mock Bento (background)
```
nohup python services/mock_bento/app.py > reports/agent2a/logs/mock_bento_run.log 2>&1 &
echo $! > reports/agent2a/diagnostics/mock_bento_pid.txt
```

2) Start dashboard with admin blueprint (dev helper)
```
PORT=8029 python run_with_admin.py > reports/agent2a/logs/dash_with_admin_run.log 2>&1 &
echo $! > reports/agent2a/diagnostics/dash_with_admin_pid.txt
sleep 3
tail -n 200 reports/agent2a/logs/dash_with_admin_run.log | sed -n '1,200p' > reports/agent2a/diagnostics/dash_with_admin_tail_after_restart.txt
```

3) Admin smoke checks (curl)
```
curl -sS http://localhost:8029/ > reports/agent2a/diagnostics/root_index_after_restart.html 2>&1 || true
curl -sS http://localhost:8029/admin/ > reports/agent2a/diagnostics/admin_info_after_restart.json 2>&1 || true
curl -sS http://localhost:8029/admin/callback_map > reports/agent2a/diagnostics/admin_callback_map_after.json 2>&1 || true
curl -sS http://localhost:8029/admin/tab_health/market_trends > reports/agent2a/diagnostics/admin_tab_health_market_trends_after.json 2>&1 || true
curl -sS http://localhost:8029/admin/tab_health/volatility_lab > reports/agent2a/diagnostics/admin_tab_health_volatility_lab_after.json 2>&1 || true

# capture response codes
curl -s -o /dev/null -w "%{http_code}" http://localhost:8029/ > reports/agent2a/diagnostics/admin_smoke_codes.txt || true
```

4) Validate mock Bento endpoints
```
curl -sS http://localhost:5001/ > reports/agent2a/diagnostics/mock_bento_info_after_restart.json 2>&1 || true
curl -sS -X POST http://localhost:5001/predict -H 'Content-Type: application/json' -d '{}' > reports/agent2a/diagnostics/mock_bento_predict_after_restart.json 2>&1 || true
curl -sS -X POST http://localhost:5001/explain -H 'Content-Type: application/json' -d '{}' > reports/agent2a/diagnostics/mock_bento_explain_after_restart.json 2>&1 || true
```

5) Run Playwright headed ID→page scan (optional, requires Playwright)
```
python tests/playwright/id_page_scan_headed.py
# results will appear in: reports/agent2a/playwright/id_scan/id_scan_results.json
```

Stopping services and collecting logs
- Stop mock Bento: `kill $(cat reports/agent2a/diagnostics/mock_bento_pid.txt) 2>/dev/null || true`
- Stop dashboard: `kill $(cat reports/agent2a/diagnostics/dash_with_admin_pid.txt) 2>/dev/null || true`
- Logs are in `reports/agent2a/logs/` and diagnostics in `reports/agent2a/diagnostics/`.

Interpretation guidance
- `admin_callback_map_after.json` should contain mapping of registered Dash callbacks (if admin blueprint registered). If empty, ensure `run_with_admin.py` registered the blueprint.
- `mock_bento_predict_after_restart.json` should contain a `forecast` array with `yhat` values.
- `id_scan_results.json` lists each ID, whether it was found, and snapshot/dom paths if present.

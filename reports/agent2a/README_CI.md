Agent-2A CI notes

The `./github/workflows/static_checks.yml` workflow runs on PR and executes:
- `python3 tools/analysis/agent2a_analysis.py` to generate `reports/agent2a/architecture_report.json`
- `python3 tools/ci_duplicate_id_check.py reports/agent2a/architecture_report.json` to fail if duplicate IDs or cross-tab imports are found
- `ruff check`
- `black --check`

If the CI fails on duplicate IDs or cross-tab imports, review `reports/agent2a/architecture_report.json` for `ids_by_file` and `major_tabs` sections to understand collisions.

# NEXT PHASE OVERVIEW

This document summarizes the planned ML and Azure integration labs, their
purpose, and the minimal scaffolds included in this repo to allow parallel
development and safe testing by Agent 1A.

Goals:
- Add ML-based predictions, feature interpretations, and strategy recommendations
- Integrate model deployment, monitoring, and autoscaling on Azure
- Keep all work isolated from the live dashboard so automated tests can run
  without changing production artifacts.

Included Scaffolds (high-level):
- `financial_dashboard/ml_integration_lab/` : placeholders for UI, callbacks, and data loaders
- `financial_dashboard/azure_integration_lab/` : placeholders for deployment and monitoring
- `mock_data/` : sample datasets plus a generator script to synthesize realistic data
- `tests/` : Playwright and pytest templates for E2E validation (non-invasive)
- `config/config.yaml` : configuration template for storing non-secret defaults

Next steps:
1. Agent 1B to iterate on models and add offline tests using `mock_data/`.
2. Agent 1A continues UI E2E tests against the live dashboard; no server restarts
   or production file writes are performed by these scaffolds.

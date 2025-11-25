# ML Features - Subtab Details & Expected Metrics

This file documents the intended subtabs for the ML Integration Lab and the
expected inputs/outputs for each placeholder. Use this as a contract when
implementing UI and backend wiring.

Subtabs and contracts:

- ML Predictions
  - Inputs: historical price returns (DataFrame), feature matrix (DataFrame), model spec
  - Outputs: predictions (DataFrame indexed by date/ticker), confidence scores (Series)
  - Visuals: time-series predictions, thresholded signals, prediction heatmap

- Feature Importance
  - Inputs: trained model artifact, feature names
  - Outputs: ranked feature importance (table), SHAP summary plot (image/Object)

- Model Metrics
  - Inputs: predictions + labels or backtest returns
  - Outputs: backtest metrics (CAGR, Sharpe, MaxDD), classification metrics (AUC, precision)

- Strategy Recommendations
  - Inputs: predictions, portfolio constraints
  - Outputs: suggested weights, rebalancing schedule, risk estimates

- User Feedback
  - Inputs: free-form feedback payload
  - Outputs: stored feedback entry id, anonymized telemetry

Notes:
- All outputs should be serializable (JSON friendly) so tests can assert structure.
- Use `mock_data/` for offline validation before wiring to production data.

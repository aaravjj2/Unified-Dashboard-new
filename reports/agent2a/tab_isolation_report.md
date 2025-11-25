# Tab Isolation Report

## market_trends

- Files:
  - financial_dashboard/tabs/market_trends.py
  - financial_dashboard/tabs/market_trends_callbacks_fixed.py
  - financial_dashboard/tabs/market_trends_refactored.py
- Component IDs: ['analysis-options', 'backtest-btn', 'backtest-modal', 'backtest-results-content', 'close-backtest-modal', 'close-debug-modal', 'compact-brief', 'compact-brief-wrapper', 'debug-input', 'debug-log-btn', 'debug-logs-btn', 'debug-logs-content', 'debug-logs-modal', 'debug-output', 'download-btn', 'download-data', 'full-brief', 'job-history', 'job-status-display', 'loading', 'market-trends-table', 'model-status', 'mount-trigger', 'mt-download-btn', 'mt-model-status', 'news-container', 'news-last-updated', 'news-poll-interval', 'period-input', 'refresh-cached', 'reload-model', 'results-area', 'results-table-client', 'run-btn', 'status', 'tab-visibility-indicator', 'tickers-input', 'toggle-brief', 'trends-composite-results', 'trends-html-table-container', 'trends-results-table-container']
- Stores: ['news-last-updated']
- Module-level globals: ['SERVER_RUN_FN', '_NEWS_CACHE', '_NEWS_CACHE_TTL_SECONDS', '_NEWS_ENRICHMENT_JOB', '_callbacks_file_handler', '_callbacks_log_file']
- External imports count: 12
  - dash
  - financial_dashboard
  - financial_dashboard._shared
  - financial_dashboard.utils
  - financial_dashboard.utils.events_helper
  - financial_dashboard.utils.news_client
  - financial_dashboard.utils.sync_manifest
  - logging
  - os
  - re
  - time
  - utils


## volatility_lab

- No files matched this tab (search by filename)

## options_lab

- No files matched this tab (search by filename)

## strategy_lab

- No files matched this tab (search by filename)

## portfolio

- Files:
  - financial_dashboard/tabs/portfolio_analytics.py
  - financial_dashboard/tabs/portfolio_factors.py
  - financial_dashboard/tabs/portfolio_optimization.py
  - financial_dashboard/tabs/portfolio_positions.py
  - financial_dashboard/tabs/portfolio_tracker_refactored.py
  - financial_dashboard/tabs/portfolio_orders.py
- Component IDs: ['analytics', 'analytics-loading', 'analytics-period', 'factors', 'inspect-modal', 'inspect-modal-body', 'inspect-modal-close', 'inspect-modal-title', 'monte-carlo-btn', 'monte-carlo-loading', 'monte-carlo-results', 'news-prefetch-status', 'opt-period-slider', 'opt-results-container', 'opt-run-btn', 'opt-strategy', 'opt-tickers-input', 'optimization', 'order-date-range', 'order-filter', 'orders', 'portfolio-alpaca-alert', 'portfolio-analytics-content', 'portfolio-beta', 'portfolio-buying-power', 'portfolio-cvar', 'portfolio-data-store', 'portfolio-factor-exposure-content', 'portfolio-interval', 'portfolio-invested', 'portfolio-load-trigger', 'portfolio-orders-table', 'portfolio-positions-refresh-btn', 'portfolio-positions-table', 'portfolio-refresh-btn', 'portfolio-sharpe', 'portfolio-tracker-subtabs', 'portfolio-unrealized-pl', 'portfolio-value', 'portfolio-var', 'positions', 'positions-datatable', 'regen-shap-btn', 'shap-regen-status']
- Stores: ['portfolio-data-store', 'portfolio-load-trigger']
- Module-level globals: []
- External imports count: 6
  - dash
  - financial_dashboard.utils.normalize
  - financial_dashboard.utils.sync_manifest
  - logging
  - os
  - time


## market_forecast

- Files:
  - financial_dashboard/tabs/market_forecast.py
  - financial_dashboard/tabs/market_forecast_rebuild.py
- Component IDs: ['mf-confidence-selector', 'mf-details-table', 'mf-forecast-store', 'mf-generate-btn', 'mf-horizon-selector', 'mf-loading', 'mf-loading-output', 'mf-params-store', 'mf-returns-chart', 'mf-store-debug', 'mf-summary-cards', 'mf-ticker-input', 'mf-ticker-selector', 'mf-volatility-chart']
- Stores: ['mf-forecast-store', 'mf-params-store']
- Module-level globals: ['CACHE_DIR', 'COMPONENT_IDS', 'EXPLAIN_DIR', '__all__']
- External imports count: 3
  - dash
  - logging
  - os


## research_lab

- Files:
  - financial_dashboard/tabs/research_lab_tab.py
- Component IDs: []
- Stores: []
- Module-level globals: []
- External imports count: 2
  - dash
  - logging


## attribution_lab

- No files matched this tab (search by filename)

# Azure ML Lab - Architecture & Integration Guide

**Phase 3 Scaffold Documentation**  
**Version:** 1.0.0  
**Status:** Placeholder - No live ML execution  
**Date:** October 28, 2025

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Data Flow](#data-flow)
4. [Module Structure](#module-structure)
5. [Expected Inputs & Outputs](#expected-inputs--outputs)
6. [Developer Quick Reference](#developer-quick-reference)
7. [Phase 4 Integration Plan](#phase-4-integration-plan)
8. [Testing Strategy](#testing-strategy)

---

## 🎯 Overview

The Azure ML Lab provides a modular integration layer for machine learning-powered predictive analytics within the Unified Financial Dashboard. Phase 3 delivers a complete scaffold with placeholder functionality, ready for real Azure ML integration in Phase 4.

### Key Features (Phase 3 Scaffold)

✅ **4-Section UI Layout:**
- ML Model Setup (model selection, feature toggles)
- Prediction Configuration (horizon, date range, parameters)
- Insights & Metrics (prediction results, performance)
- Logs / Diagnostics (system status, validation)

✅ **Mock Prediction Pipeline:**
- Portfolio data ingestion from Home Lab
- Feature engineering and preprocessing
- Mock prediction generation
- Result caching and retrieval

✅ **Beginner-Friendly UX:**
- Black text (#000000) for readability
- Tooltips on all complex metrics
- Progressive disclosure (tabs, accordions)
- Clear "What This Shows" / "How to Use" sections

✅ **Docker-Ready:**
- No external dependencies (Azure ML endpoints)
- Self-contained mock data
- Isolated from live dashboard testing

---

## 🏗️ Architecture

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNIFIED FINANCIAL DASHBOARD                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────┐     │
│  │  Home Lab    │  │ Market        │  │ Strategy Lab     │     │
│  │  (Portfolio) │  │ Forecast      │  │ (Backtesting)    │     │
│  └──────┬───────┘  └───────┬───────┘  └────────┬────────┘     │
│         │                   │                    │               │
│         └───────────────────┼────────────────────┘               │
│                             ▼                                    │
│                   ┌──────────────────┐                          │
│                   │  AZURE ML LAB    │                          │
│                   │  (Phase 3)       │                          │
│                   └──────────────────┘                          │
│                             │                                    │
│         ┌───────────────────┼───────────────────┐               │
│         ▼                   ▼                   ▼               │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
│  │ Predictions │   │ Simulations │   │ Risk        │          │
│  │ (Returns,   │   │ (Strategy   │   │ Assessment  │          │
│  │  Volatility)│   │  Backtest)  │   │ (Exposure)  │          │
│  └─────────────┘   └─────────────┘   └─────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Module Structure

```
financial_dashboard/tabs/azure_ml_lab/
├── __init__.py           # Package initialization, exports
├── layout.py             # 4-section UI (550+ lines)
├── callbacks.py          # 6 Dash callbacks (400+ lines)
├── helpers.py            # Data processing, mock ML (500+ lines)
└── diagnostics_azure_ml.py  # Pre-flight validation (300+ lines)

mock_data/azure_ml/
├── generate_azure_ml_mocks.py  # Mock data generator
├── mock_portfolio.csv          # Portfolio snapshot
├── mock_market_factors.json    # Fama-French factors
├── mock_time_series.csv        # Historical prices
└── mock_volatility_forecast.json  # Vol forecasts

docs/
└── AZURE_ML_LAB_ARCHITECTURE.md  # This file
```

---

## 📊 Data Flow

### Phase 3 (Mock/Placeholder)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. USER INTERACTION                                         │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. DATA INGESTION                                           │
│    • Portfolio: home_lab.helpers.get_portfolio_summary()    │
│    • Market: mock_market_forecast_data()                    │
│    • Factors: mock_factor_data()                            │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. PREPROCESSING                                            │
│    • preprocess_portfolio_data(portfolio_dict)              │
│    • engineer_features(df, lookback=30)                     │
│    • preprocess_market_factors(factor_dict)                 │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. MOCK PREDICTION (Phase 3)                                │
│    • generate_mock_predictions(df, model, horizon)          │
│    • Random returns with confidence intervals               │
│    • Simulate strategy performance                          │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. CACHING & RETRIEVAL                                      │
│    • cache_predictions(predictions, key)                    │
│    • load_cached_predictions(key)                           │
│    • JSON files in cache/ml_predictions/                    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. RESULT DISPLAY                                           │
│    • Predictions table (ticker, return, confidence)         │
│    • Performance metrics (Sharpe, MAE, win rate)            │
│    • Feature importance (mock SHAP values)                  │
│    • Risk analysis (exposure, correlations)                 │
└─────────────────────────────────────────────────────────────┘
```

### Phase 4 (Real Azure ML) - Planned

```
┌─────────────────────────────────────────────────────────────┐
│ 1. DATA INGESTION (same as Phase 3)                        │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. AZURE ML ENDPOINT CALL                                   │
│    • POST request to Azure ML workspace                     │
│    • Authentication via Azure SDK                           │
│    • Payload: {features, horizon, model_config}             │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. REAL-TIME PREDICTION                                     │
│    • Ensemble model (LSTM + XGBoost + Linear)               │
│    • Feature importance (SHAP values)                       │
│    • Confidence intervals (quantile regression)             │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. RESULT PROCESSING & DISPLAY (same as Phase 3)           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📥 Expected Inputs & Outputs

### Inputs

#### 1. Portfolio Data (from Home Lab)
```python
{
    'total_positions': 10,
    'total_value': 132250.0,
    'daily_change_pct': 1.2,
    'positions': [
        {
            'ticker': 'AAPL',
            'shares': 100,
            'last_price': 175.0,
            'market_value': 17500.0,
            'sector': 'Technology',
            'daily_change_pct': 1.5,
            'predicted_return': 2.3  # Optional
        },
        # ... more positions
    ],
    'last_updated': '2025-10-28',
    'source': 'csv'  # or 'cache' or 'mock'
}
```

#### 2. Market Factors (Fama-French)
```python
{
    'mkt_rf': 0.05,   # Market risk premium
    'smb': 0.02,      # Small minus big
    'hml': -0.01,     # High minus low
    'rmw': 0.03,      # Robust minus weak
    'cma': 0.01,      # Conservative minus aggressive
    'vix': 18.5,      # Volatility index
    'sentiment': 0.65 # Sentiment score (0-1)
}
```

#### 3. User Configuration
```python
{
    'model_type': 'ensemble',      # or 'lstm', 'xgboost', 'linear'
    'prediction_horizon': 5,       # days
    'confidence_threshold': 0.7,   # 0.5-0.95
    'features': ['technical', 'factors', 'volatility'],
    'advanced_options': ['cache', 'shap'],
    'target': 'both',              # 'returns', 'volatility', 'both'
    'universe': 'current',         # 'top20', 'custom'
    'date_range': ('2024-10-28', '2025-10-28')
}
```

### Outputs

#### 1. Predictions
```python
{
    'predictions': [
        {
            'ticker': 'AAPL',
            'predicted_return': 0.025,     # 2.5%
            'confidence': 0.85,
            'lower_bound': -0.005,
            'upper_bound': 0.055,
            'horizon_days': 5
        },
        # ... more predictions
    ],
    'model_type': 'ensemble',
    'horizon_days': 5,
    'overall_confidence': 0.78,
    'timestamp': '2025-10-28T14:30:00',
    'status': 'mock_success',  # or 'success' in Phase 4
    'note': 'Phase 3 scaffold - mock predictions only'
}
```

#### 2. Performance Metrics
```python
{
    'prediction_accuracy': 0.735,  # 73.5%
    'mean_absolute_error': 0.028,  # 2.8%
    'sharpe_ratio': 1.85,
    'win_rate': 0.582,             # 58.2%
    'max_drawdown': -0.12,
    'information_ratio': 1.42
}
```

#### 3. Feature Importance (Phase 4)
```python
{
    'shap_values': {
        'momentum_5d': 0.35,
        'mkt_rf': 0.28,
        'volatility_10d': 0.22,
        'smb': 0.10,
        'hml': 0.05
    },
    'top_features': ['momentum_5d', 'mkt_rf', 'volatility_10d']
}
```

---

## 👨‍💻 Developer Quick Reference

### Functions to Implement (Phase 4)

**High Priority:**
1. `call_azure_ml_endpoint(features, config)` → Connect to Azure ML workspace
2. `authenticate_azure_ml()` → Azure SDK authentication
3. `validate_prediction_response(response)` → Error handling
4. `compute_shap_values(model, features)` → Real feature importance
5. `stream_prediction_progress(callback)` → Real-time updates

**Medium Priority:**
6. `train_custom_model(data, params)` → Custom model training
7. `deploy_model_to_azure(model)` → Model deployment
8. `monitor_model_drift(predictions)` → Model monitoring
9. `optimize_hyperparameters(data)` → AutoML integration
10. `integrate_real_time_data_feed()` → Live market data

**Low Priority:**
11. `export_predictions_to_excel(predictions)` → Reporting
12. `schedule_automated_predictions(cron)` → Automation
13. `multi_asset_allocation(predictions)` → Portfolio optimization

### Callback Placeholders

All callbacks in `callbacks.py` are functional but use mock data:

```python
# Callback 1: Model Status Update
Input: model_type, features, options
Output: Status text display

# Callback 2: Run Prediction
Input: Button click + config states
Output: Prediction results alert

# Callback 3: Update Predictions Table
Input: Prediction results
Output: Data table

# Callback 4: Performance Metrics
Input: Prediction results
Output: Metric cards

# Callback 5: Refresh Diagnostics
Input: Button click
Output: System status text

# Callback 6: Pre-Flight Check
Input: Button click
Output: Execution logs
```

### E2E Testing Expectations

Phase 3 E2E tests should verify:

✅ Tab visibility and navigation  
✅ Dropdown/input interactions  
✅ Button click handlers  
✅ Mock prediction execution  
✅ Result display rendering  
✅ Diagnostic log updates  

❌ NOT testing in Phase 3:
- Real ML model execution
- Azure endpoint connectivity
- Live data feeds
- Performance under load

---

## 🚀 Phase 4 Integration Plan

### Step 1: Azure ML Workspace Setup
- Create Azure ML workspace
- Deploy trained models as endpoints
- Configure authentication (service principal)
- Set up managed identities

### Step 2: Replace Mock Functions
```python
# helpers.py changes:

# BEFORE (Phase 3):
def generate_mock_predictions(portfolio_df, model_type, horizon):
    # Mock implementation
    return {'predictions': [...], 'status': 'mock_success'}

# AFTER (Phase 4):
def call_azure_ml_prediction(portfolio_df, model_type, horizon):
    from azure.ai.ml import MLClient
    from azure.identity import DefaultAzureCredential
    
    # Authenticate
    credential = DefaultAzureCredential()
    ml_client = MLClient(credential, subscription_id, resource_group, workspace)
    
    # Prepare payload
    payload = {
        'features': portfolio_df.to_dict('records'),
        'model_type': model_type,
        'horizon_days': horizon
    }
    
    # Call endpoint
    endpoint = ml_client.online_endpoints.get(name='portfolio-prediction-v1')
    response = endpoint.invoke(payload)
    
    return process_azure_ml_response(response)
```

### Step 3: Add Monitoring
- Implement logging to Azure Application Insights
- Track prediction latency
- Monitor model drift
- Alert on errors

### Step 4: Optimize Performance
- Cache frequent predictions
- Batch similar requests
- Use async/await for non-blocking calls
- Implement circuit breaker pattern

### Step 5: Real Data Integration
- Connect to live market data APIs
- Stream Fama-French factors
- Integrate with yfinance for historical data
- Add sentiment analysis feeds

---

## 🧪 Testing Strategy

### Phase 3 Testing (Current)

**Unit Tests** (not yet implemented):
```python
# tests/test_azure_ml_lab_helpers.py
def test_preprocess_portfolio_data():
    mock_portfolio = {...}
    df = preprocess_portfolio_data(mock_portfolio)
    assert len(df) > 0
    assert 'market_value_normalized' in df.columns

def test_generate_mock_predictions():
    predictions = generate_mock_predictions(df, 'ensemble', 5)
    assert 'predictions' in predictions
    assert predictions['status'] == 'mock_success'
```

**E2E Playwright Tests** (scaffold):
```python
# tests/test_azure_ml_lab_e2e.py (to create)

async def test_azure_ml_tab_visibility(page):
    await page.goto('http://localhost:8050')
    await page.click('a:has-text("Azure ML Lab")')
    assert await page.is_visible('text=ML Model Setup')

async def test_run_prediction_workflow(page):
    # Navigate to tab
    await page.goto('http://localhost:8050')
    await page.click('a:has-text("Azure ML Lab")')
    
    # Select model
    await page.select_option('#azure-ml-model-type', 'ensemble')
    
    # Set horizon
    await page.select_option('#azure-ml-prediction-horizon', '5')
    
    # Run prediction
    await page.click('#azure-ml-run-prediction-btn')
    
    # Verify results
    await page.wait_for_selector('text=Prediction Complete')
    assert await page.is_visible('text=Generated')
```

**Diagnostic Script** (implemented):
```bash
python financial_dashboard/tabs/azure_ml_lab/diagnostics_azure_ml.py
```

### Phase 4 Testing (Planned)

- Integration tests with Azure ML endpoints
- Performance benchmarks (latency, throughput)
- Load testing (concurrent predictions)
- Model accuracy validation
- Regression tests for predictions

---

## 📦 Deliverables Summary

**Code:**
- ✅ `__init__.py` - Package initialization (40 lines)
- ✅ `layout.py` - 4-section UI layout (550+ lines)
- ✅ `callbacks.py` - 6 Dash callbacks (400+ lines)
- ✅ `helpers.py` - Data processing + mock ML (500+ lines)
- ✅ `diagnostics_azure_ml.py` - Pre-flight validation (300+ lines)

**Mock Data:**
- ✅ `generate_azure_ml_mocks.py` - Data generator (200+ lines)
- ✅ Mock portfolio CSV
- ✅ Mock market factors JSON
- ✅ Mock time series CSV
- ✅ Mock volatility forecast JSON

**Documentation:**
- ✅ `AZURE_ML_LAB_ARCHITECTURE.md` - This file
- ✅ Inline docstrings (all functions)
- ✅ TODO comments (all placeholders)

**Testing Scaffolds:**
- ✅ Diagnostic script (module validation)
- 🔲 Playwright E2E template (next step)

---

## ✅ Next Steps

**Immediate (Before Phase 4):**
1. Create Playwright E2E test scaffolds
2. Run diagnostic validation script
3. Generate mock data files
4. Verify Docker-ready imports

**Phase 4 (Real ML Integration):**
1. Set up Azure ML workspace
2. Train and deploy models
3. Replace mock functions with real endpoints
4. Add monitoring and logging
5. Optimize performance
6. Expand test coverage

---

**Document Version:** 1.0.0  
**Last Updated:** October 28, 2025  
**Maintained By:** Agent 1B - Lead Engineer  
**Status:** Phase 3 Scaffold Complete ✅

# Azure ML Workspace Deployment Guide - Phase 5

**Project:** Unified Financial Dashboard  
**Phase:** 5 - Azure ML Real Data Integration  
**Date:** October 28, 2025

---

## 📋 Overview

This guide provides step-by-step instructions for deploying a real Azure ML workspace, registering models, creating managed endpoints, and transitioning the Azure ML Lab from mock mode to live predictions.

**Prerequisites:**
- Azure subscription with Azure ML permissions
- Azure CLI installed (`az --version`)
- Python 3.9+ with `azure-ai-ml` SDK
- Unified Dashboard codebase (Phase 4 completed)

---

## ✅ Local Preflight & Readiness Checks (what to verify locally before provisioning Azure)

This section lists explicit, runnable validations you should perform locally before you attempt to provision Azure resources and deploy live models. The goal is to prove the dashboard and Azure ML Lab are "deployment-ready" on your machine and to avoid surprises during the Azure deployment step.

Run these checks in order. Each step includes a command and expected outcome.

1) Repository & Python environment

```bash
# From project root
python --version
pip --version
python -c "import sys; print('Working dir:', __import__('pathlib').Path('.').resolve())"
```

Expected: Python 3.9+ (or project's supported version). Ensure you run commands with the same interpreter used for the dashboard.

2) Environment files and feature flags

Check that you have `.env`, `doppler.env`, or `financial_dashboard/.env` in place (or are prepared to set env variables). The critical flags are:

- `AZURE_ML_USE_MOCK` (default: true) -- when true, mock mode is active and safe for local testing
- `AZURE_ML_ENDPOINT_URL` and `AZURE_ML_API_KEY` (only when you are ready to enable real predictions)

Commands:

```bash
# show current AZURE_ML flags (if present in environment files)
grep -n "AZURE_ML_" .env doppler.env financial_dashboard/.env 2>/dev/null || true

# Quick show of runtime environment (if variables are already exported):
python - <<'PY'
import os
print('AZURE_ML_USE_MOCK=', os.getenv('AZURE_ML_USE_MOCK'))
print('AZURE_ML_ENDPOINT_URL=', bool(os.getenv('AZURE_ML_ENDPOINT_URL')))
print('AZURE_ML_API_KEY=', bool(os.getenv('AZURE_ML_API_KEY')))
PY
```

Expected: If you are not ready for Azure, `AZURE_ML_USE_MOCK` should be `true` or unset. If you plan to enable real mode, confirm the endpoint URL and API key are set and tested (see testing steps below).

3) Mock data presence

The project ships mock data for Phase-4/5 validation. Confirm the mock files exist:

```bash
ls -lh mock_data/azure_ml || true
```

Expected files (examples):
- `mock_market_factors.json`
- `mock_time_series.csv`
- `mock_portfolio.csv`
- `mock_volatility_forecast.json`

4) Import checks (sanity import of the tab package)

This verifies the new `azure_ml_lab` package can be imported without starting the dashboard.

```bash
python - <<'PY'
import importlib
try:
  mod = importlib.import_module('financial_dashboard.tabs.azure_ml_lab.helpers')
  print('OK: imported azure_ml_lab.helpers')
  print('Has preprocess_portfolio_data:', hasattr(mod, 'preprocess_portfolio_data'))
  print('Has call_azure_ml_endpoint:', hasattr(mod, 'call_azure_ml_endpoint'))
except Exception as e:
  print('IMPORT FAILED:', e)
  raise SystemExit(2)
PY
```

Expected: The import succeeds and the key functions are present. If this fails, run `python -c 'import sys; print(sys.path)'` and ensure repo root is on `PYTHONPATH` when running dashboard.

5) Quick diagnostics (Phase 4 diagnostic script)

Run the existing lightweight diagnostic to validate configuration and mock fallback.

```bash
python phase4_integration_diagnostic.py
```

Expected (mock mode): configuration reports `mock_mode: True` and helper functions return mock predictions. If you see import errors, make sure your working directory is the repo root and the virtualenv uses the project's interpreter.

6) linter / syntax checks

Run a quick syntax check across the repo to catch obvious issues introduced by edits.

```bash
python -m py_compile $(find financial_dashboard -name '*.py') 2>/dev/null || true
```

Expected: No syntax errors. If errors are found, open the file and fix them before deploying.

7) E2E smoke (optional but recommended)

Start the dashboard locally and run a single Playwright test (headed) to verify tab rendering and basic callbacks.

```bash
# Start the dashboard in the background
python financial_dashboard/app.py &
# Wait a few seconds for startup
sleep 5
# Run a single Playwright/pytest test (headed) - this will open a browser so run on a workstation
pytest tests/test_azure_ml_lab_e2e_scaffold.py -k "tab_visibility" -q --headed
```

Expected: The Azure ML Lab tab is visible, layout renders, and no fatal callbacks occur. If the test fails, inspect the test output and dashboard logs.

8) Docker readiness (if you plan to use Docker)

Confirm `docker` and `docker-compose` are available and that the `financial_dashboard/docker-compose.yml` is present.

```bash
docker --version || true
docker-compose --version || true
ls financial_dashboard/docker-compose.yml || true
```

Optional: Start the dashboard stack in Docker for a production-like run. See the `PHASE5_QUICK_REFERENCE.md` for minimal docker run commands.

9) Validation script (one-command local readiness)

To automate the checks above, we include a lightweight validator script: `scripts/validate_local_readiness.py`. It verifies env vars, mock files, important imports, and optional installed packages (`yfinance`, `azure-ai-ml`).

Run it as:

```bash
python scripts/validate_local_readiness.py
```

The script prints a human-readable report and returns exit code `0` when all non-blocking checks pass (mock mode OK). If it reports blocking failures, fix them before provisioning Azure resources.

---

Continue to Part 1 (Azure ML Workspace Setup) only after the local preflight passes or you acknowledge and accept the risks of proceeding.

## 🚀 Part 1: Azure ML Workspace Setup

### Step 1.1: Install Azure ML SDK

```bash
pip install azure-ai-ml azure-identity azure-mgmt-resource
```

### Step 1.2: Azure CLI Login

```bash
# Login to Azure
az login

# Set your subscription (replace with your subscription ID)
az account set --subscription <YOUR_SUBSCRIPTION_ID>

# Verify
az account show
```

### Step 1.3: Create Resource Group

```bash
az group create \
  --name unified-dashboard-rg \
  --location eastus
```

### Step 1.4: Create Azure ML Workspace

```bash
az ml workspace create \
  --name unified-dashboard-ml \
  --resource-group unified-dashboard-rg \
  --location eastus
```

**Expected Output:**
```
{
  "id": "/subscriptions/.../resourceGroups/unified-dashboard-rg/providers/Microsoft.MachineLearningServices/workspaces/unified-dashboard-ml",
  "name": "unified-dashboard-ml",
  "location": "eastus",
  ...
}
```

---

## 🤖 Part 2: Model Registration

### Step 2.1: Prepare Model Files

Create a simple prediction model (example: linear regression for portfolio returns):

```python
# scripts/train_simple_portfolio_model.py
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
import joblib

# Generate synthetic training data (replace with real data)
np.random.seed(42)
n_samples = 1000

X = pd.DataFrame({
    'market_value_normalized': np.random.rand(n_samples),
    'abs_daily_change': np.random.rand(n_samples),
    'momentum_20d': np.random.randn(n_samples) * 0.02,
    'volatility_20d': np.random.rand(n_samples) * 0.3,
    'sharpe_20d': np.random.randn(n_samples) * 0.5
})

y = (X['momentum_20d'] * 10 + X['sharpe_20d'] * 2 + np.random.randn(n_samples) * 0.01)

# Train model
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = LinearRegression()
model.fit(X_train, y_train)

# Save model
joblib.dump(model, 'models/portfolio_prediction_v1.pkl')
print(f"Model trained. R² score: {model.score(X_test, y_test):.4f}")
```

Run the training script:

```bash
python scripts/train_simple_portfolio_model.py
```

### Step 2.2: Register Model in Azure ML

```python
# scripts/register_model_azure_ml.py
from azure.ai.ml import MLClient
from azure.ai.ml.entities import Model
from azure.identity import DefaultAzureCredential

# Connect to workspace
ml_client = MLClient(
    credential=DefaultAzureCredential(),
    subscription_id="<YOUR_SUBSCRIPTION_ID>",
    resource_group_name="unified-dashboard-rg",
    workspace_name="unified-dashboard-ml"
)

# Register model
model = Model(
    path="models/portfolio_prediction_v1.pkl",
    name="portfolio-prediction",
    description="Linear regression model for portfolio return prediction",
    version="1"
)

registered_model = ml_client.models.create_or_update(model)
print(f"✅ Model registered: {registered_model.name} (version {registered_model.version})")
```

Run the registration script:

```bash
python scripts/register_model_azure_ml.py
```

---

## 🌐 Part 3: Deploy Managed Endpoint

### Step 3.1: Create Scoring Script

```python
# scripts/score.py
import json
import joblib
import numpy as np
import pandas as pd

def init():
    """Load model on startup."""
    global model
    model_path = './models/portfolio_prediction_v1.pkl'
    model = joblib.load(model_path)
    print("Model loaded successfully")

def run(raw_data):
    """
    Process prediction request.
    
    Input format:
    {
        "model_type": "ensemble",
        "horizon_days": 5,
        "features": [
            {"ticker": "AAPL", "market_value_normalized": 0.2, ...},
            ...
        ]
    }
    """
    try:
        data = json.loads(raw_data)
        features_df = pd.DataFrame(data['features'])
        
        # Select feature columns
        feature_cols = ['market_value_normalized', 'abs_daily_change', 'momentum_20d', 'volatility_20d', 'sharpe_20d']
        X = features_df[feature_cols].fillna(0)
        
        # Predict
        predictions = model.predict(X)
        
        # Format response
        result = {
            'predictions': [
                {
                    'ticker': features_df['ticker'].iloc[i],
                    'predicted_return': float(predictions[i]),
                    'confidence': 0.75  # Placeholder
                }
                for i in range(len(predictions))
            ],
            'model_type': data.get('model_type', 'linear'),
            'horizon_days': data.get('horizon_days', 5),
            'overall_confidence': 0.75,
            'timestamp': pd.Timestamp.now().isoformat(),
            'status': 'success'
        }
        
        return json.dumps(result)
    
    except Exception as e:
        return json.dumps({'error': str(e), 'status': 'error'})
```

### Step 3.2: Create Environment YAML

```yaml
# environment.yml
name: portfolio-prediction-env
channels:
  - conda-forge
dependencies:
  - python=3.9
  - pip
  - pip:
      - scikit-learn==1.3.0
      - pandas==2.0.3
      - numpy==1.24.3
      - joblib==1.3.2
      - azureml-defaults
```

### Step 3.3: Deploy Endpoint

```python
# scripts/deploy_endpoint_azure_ml.py
from azure.ai.ml import MLClient
from azure.ai.ml.entities import ManagedOnlineEndpoint, ManagedOnlineDeployment, Model, Environment, CodeConfiguration
from azure.identity import DefaultAzureCredential

ml_client = MLClient(
    credential=DefaultAzureCredential(),
    subscription_id="<YOUR_SUBSCRIPTION_ID>",
    resource_group_name="unified-dashboard-rg",
    workspace_name="unified-dashboard-ml"
)

# Create endpoint
endpoint = ManagedOnlineEndpoint(
    name="portfolio-prediction-v1",
    description="Portfolio prediction endpoint",
    auth_mode="key"
)

endpoint = ml_client.online_endpoints.begin_create_or_update(endpoint).result()
print(f"✅ Endpoint created: {endpoint.name}")

# Create deployment
deployment = ManagedOnlineDeployment(
    name="blue",
    endpoint_name="portfolio-prediction-v1",
    model=Model(name="portfolio-prediction", version="1"),
    environment=Environment(
        image="mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu20.04",
        conda_file="environment.yml"
    ),
    code_configuration=CodeConfiguration(
        code="scripts/",
        scoring_script="score.py"
    ),
    instance_type="Standard_DS2_v2",
    instance_count=1
)

deployment = ml_client.online_deployments.begin_create_or_update(deployment).result()
print(f"✅ Deployment created: {deployment.name}")

# Set 100% traffic to blue deployment
endpoint.traffic = {"blue": 100}
ml_client.online_endpoints.begin_create_or_update(endpoint).result()
print("✅ Traffic routed to blue deployment")
```

Run deployment:

```bash
python scripts/deploy_endpoint_azure_ml.py
```

**Note:** Deployment can take 10-15 minutes.

---

## 🔑 Part 4: Configure Dashboard Credentials

### Step 4.1: Get Endpoint URL and API Key

```bash
# Get endpoint URL
az ml online-endpoint show \
  --name portfolio-prediction-v1 \
  --resource-group unified-dashboard-rg \
  --workspace-name unified-dashboard-ml \
  --query scoring_uri -o tsv

# Get API key
az ml online-endpoint get-credentials \
  --name portfolio-prediction-v1 \
  --resource-group unified-dashboard-rg \
  --workspace-name unified-dashboard-ml \
  --query primaryKey -o tsv
```

### Step 4.2: Update Environment Variables

Add to `doppler.env` or `.env`:

```bash
# Azure ML Configuration
AZURE_SUBSCRIPTION_ID=your-subscription-id-here
AZURE_RESOURCE_GROUP=unified-dashboard-rg
AZURE_ML_WORKSPACE_NAME=unified-dashboard-ml
AZURE_TENANT_ID=your-tenant-id-here

# Azure ML Endpoint
AZURE_ML_ENDPOINT_NAME=portfolio-prediction-v1
AZURE_ML_ENDPOINT_URL=https://portfolio-prediction-v1.eastus.inference.ml.azure.com/score
AZURE_ML_API_KEY=your-api-key-here

# Feature Flags
AZURE_ML_USE_MOCK=false  # ✅ Enable real predictions
AZURE_ML_ENABLE_CACHE=true
AZURE_ML_CACHE_TTL=3600
AZURE_ML_DEBUG=false
```

### Step 4.3: Test Connection

```bash
python financial_dashboard/tabs/azure_ml_lab/diagnostics_azure_ml.py
```

**Expected Output:**
```
✅ Azure ML config loaded
✅ Workspace connection successful
✅ Endpoint accessible
📊 Real predictions enabled
```

---

## ✅ Part 5: Verification

### Step 5.1: Run Integration Diagnostic

```bash
python phase4_integration_diagnostic.py
```

Look for:
```
✅ Azure ML Configuration: REAL MODE ACTIVE
✅ API call returned real predictions (status: success)
```

### Step 5.2: Test in Dashboard

1. Start dashboard: `python financial_dashboard/app.py`
2. Navigate to **Azure ML Lab** tab
3. Click "Run Prediction"
4. Verify:
   - Status shows "Real prediction from Azure ML endpoint"
   - Predictions table populates with non-mock values
   - Logs show endpoint URL and response time

---

## 📊 Part 6: Monitoring & Troubleshooting

### Enable Application Insights (Optional)

```bash
# Create App Insights
az monitor app-insights component create \
  --app unified-dashboard-insights \
  --location eastus \
  --resource-group unified-dashboard-rg

# Link to endpoint
az ml online-endpoint update \
  --name portfolio-prediction-v1 \
  --resource-group unified-dashboard-rg \
  --workspace-name unified-dashboard-ml \
  --app-insights <APP_INSIGHTS_ID>
```

### Common Issues

| Issue | Solution |
|-------|----------|
| `AuthenticationError` | Run `az login` and verify subscription |
| `EndpointNotFound` | Check endpoint name in environment variables |
| `401 Unauthorized` | Regenerate API key and update `.env` |
| `Timeout` | Increase timeout in `helpers.py` (default 30s) |
| Mock fallback active | Set `AZURE_ML_USE_MOCK=false` in `.env` |

### View Endpoint Logs

```bash
az ml online-endpoint get-logs \
  --name portfolio-prediction-v1 \
  --deployment blue \
  --resource-group unified-dashboard-rg \
  --workspace-name unified-dashboard-ml \
  --lines 100
```

---

## 🔄 Rollback to Mock Mode

If issues arise, instantly revert to mock mode:

```bash
# In .env or doppler.env
AZURE_ML_USE_MOCK=true
```

Dashboard will automatically fall back to mock predictions without code changes.

---

## 📚 Next Steps

1. **Model Retraining:** Set up automated retraining pipeline with Dagster
2. **A/B Testing:** Deploy multiple model versions and split traffic
3. **Batch Predictions:** Add batch inference for historical backtests
4. **SHAP Explainability:** Integrate SHAP values for prediction explanations
5. **Real-time Monitoring:** Set up alerts for prediction latency and accuracy drift

---

## 📖 References

- [Azure ML Documentation](https://learn.microsoft.com/en-us/azure/machine-learning/)
- [Managed Online Endpoints](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-deploy-online-endpoints)
- [Model Registration](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-manage-models)
- [Azure ML SDK Python](https://learn.microsoft.com/en-us/python/api/overview/azure/ml/)

---

**Status:** ✅ Deployment guide complete - ready for Azure ML workspace provisioning

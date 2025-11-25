# Phase 4 - Implementation Guide

**Project:** Unified Financial Dashboard  
**Phase:** 4 - Hybrid Readiness (Azure Stubs & Contracts)  
**Agent:** Agent 1B - Lead Engineer  
**Date:** October 29, 2025

---

## Quick Start (5 Minutes)

### 1. Setup Environment

```bash
cd /mnt/c/Aarav/fin_env/unified-dashboard

# Add to PYTHONPATH
export PYTHONPATH=$(pwd):$PYTHONPATH

# Set offline mode (default)
export AZURE_ML_OFFLINE_MODE=true
```

### 2. Run Diagnostics

```bash
python -m phase4_hybrid_stubs.local_hybrid_bridge.hybrid_diagnostics --verbose
```

Expected output:
```
🎉 All diagnostics PASSED!
```

### 3. Test Analytics Interface

```python
from phase4_hybrid_stubs.local_hybrid_bridge import run_analytics

result = run_analytics(
    job_type='forecast',
    payload={
        'ticker': 'AAPL',
        'features': {'momentum_20d': 0.05, 'volatility_20d': 0.15},
        'date_range': ('2025-01-01', '2025-12-31'),
        'forecast_horizon': 'monthly'
    }
)

print(f"Predictions: {result['predictions']}")
print(f"Confidence: {result['confidence']}")
```

---

## Usage Examples

### Example 1: Basic Forecast

```python
from phase4_hybrid_stubs.local_hybrid_bridge import run_forecast

# Simple forecast with convenience wrapper
result = run_forecast(
    ticker='MSFT',
    features={
        'momentum_20d': 0.03,
        'volatility_20d': 0.18,
        'sharpe_20d': 1.5,
        'pe_ratio': 32.0
    },
    date_range=('2025-01-01', '2025-12-31'),
    horizon='monthly'
)

# Result contains 30 daily predictions
print(f"Generated {len(result['predictions'])} predictions")
print(f"Average confidence: {sum(result['confidence'])/len(result['confidence']):.2%}")
```

### Example 2: Backtest with Custom Contract

```python
from phase4_hybrid_stubs.azure_contracts import ContractInputSpec, ModelType, ForecastHorizon
from phase4_hybrid_stubs.local_hybrid_bridge import run_analytics

# Create detailed input spec
input_spec = ContractInputSpec(
    ticker='GOOGL',
    features={
        'momentum_20d': 0.08,
        'volatility_20d': 0.22,
        'market_beta': 1.1,
        'smb_exposure': 0.05,
        'hml_exposure': -0.02
    },
    date_range=('2024-01-01', '2024-12-31'),
    mode='backtest',
    model_type=ModelType.GRADIENT_BOOSTING,
    forecast_horizon=ForecastHorizon.QUARTERLY,
    confidence_level=0.99,
    explainability='full'
)

# Run analytics
result = run_analytics(
    job_type='backtest',
    payload=input_spec.to_dict()
)

# Access backtest metrics
metadata = result['metadata']
print(f"Win Rate: {metadata['win_rate']:.2%}")
print(f"Sharpe Ratio: {metadata['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {metadata['max_drawdown']:.2%}")
```

### Example 3: Risk Analysis with ComputeRouter

```python
from phase4_hybrid_stubs.local_hybrid_bridge import get_router

router = get_router()

# Dispatch risk calculation
result = router.dispatch(
    task_type='risk',
    payload={
        'ticker': 'TSLA',
        'features': {'volatility_20d': 0.45, 'beta': 1.8},
        'date_range': ('2025-01-01', '2025-10-29'),
        'confidence_level': 0.95
    },
    use_cache=True
)

# Extract risk metrics
print(f"VaR (95%): {result['metadata']['var_95']:.2%}")
print(f"CVaR (95%): {result['metadata']['cvar_95']:.2%}")
print(f"Volatility: {result['metadata']['volatility']:.2%}")
print(f"Backend used: {result['_backend']}")
print(f"From cache: {result['_from_cache']}")
```

### Example 4: SHAP Explainability

```python
from phase4_hybrid_stubs.local_hybrid_bridge import run_explainability

result = run_explainability(
    ticker='NVDA',
    features={
        'momentum_20d': 0.12,
        'volatility_20d': 0.35,
        'pe_ratio': 85.0,
        'roe': 0.35,
        'market_cap': 3.2e12
    },
    date_range=('2025-01-01', '2025-12-31')
)

# Access SHAP values
shap_blob = result['explainability_blob']
print("Top Features by SHAP Value:")
for feat in shap_blob['feature_importance'][:5]:
    print(f"  {feat['feature']}: {feat['shap_value']:+.4f}")
```

### Example 5: Batch Predictions

```python
from phase4_hybrid_stubs.local_hybrid_bridge import run_analytics

tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
results = []

for ticker in tickers:
    result = run_analytics(
        job_type='forecast',
        payload={
            'ticker': ticker,
            'features': {'momentum_20d': 0.05},
            'date_range': ('2025-01-01', '2025-12-31')
        }
    )
    results.append(result)

# Aggregate results
avg_prediction = sum(r['predictions'][0] for r in results) / len(results)
print(f"Portfolio average expected return: {avg_prediction:.2%}")
```

---

## Integration with Dashboard

### Dash Callback Integration

```python
from dash import Input, Output, State, callback
from phase4_hybrid_stubs.local_hybrid_bridge import run_analytics, get_telemetry

@callback(
    Output('forecast-results', 'data'),
    Input('run-forecast-btn', 'n_clicks'),
    State('ticker-input', 'value'),
    State('features-store', 'data'),
    prevent_initial_call=True
)
def run_forecast_callback(n_clicks, ticker, features):
    if not n_clicks or not ticker:
        return {}
    
    # Track telemetry
    telemetry = get_telemetry()
    
    try:
        # Run analytics
        result = run_analytics(
            job_type='forecast',
            payload={
                'ticker': ticker,
                'features': features,
                'date_range': ('2025-01-01', '2025-12-31'),
                'forecast_horizon': 'monthly'
            }
        )
        
        # Track success
        telemetry.track_event(
            'forecast_completed',
            properties={'ticker': ticker, 'features_count': len(features)},
            measurements={'latency_ms': result.get('latency_ms', 0)}
        )
        
        return result
        
    except Exception as e:
        # Track failure
        telemetry.track_exception(e, {'ticker': ticker})
        raise
```

### Caching Strategy

```python
from phase4_hybrid_stubs.local_hybrid_bridge import get_router

router = get_router()

# Configure task-specific cache TTL
from phase4_hybrid_stubs.local_hybrid_bridge.compute_router import TASK_CONFIGS

# Extend cache TTL for slow tasks
TASK_CONFIGS['optimization'].cache_ttl_seconds = 3600  # 1 hour

# Clear stale cache before important runs
router.clear_cache(task_type='forecast')

# Get cache performance stats
stats = router.get_cache_stats()
print(f"Cache size: {stats['total_cached_items']} items")
print(f"Cache hit rate: {stats['average_age_seconds']:.0f}s average age")
```

---

## Telemetry & Monitoring

### Tracking Custom Events

```python
from phase4_hybrid_stubs.local_hybrid_bridge import get_telemetry

telemetry = get_telemetry()

# Track model training start
telemetry.track_event(
    'model_training_started',
    properties={'model_type': 'random_forest', 'ticker': 'AAPL'},
    measurements={'training_samples': 1000}
)

# Track accuracy metric
telemetry.track_metric(
    'model_accuracy',
    value=0.92,
    properties={'model_type': 'random_forest', 'ticker': 'AAPL'}
)

# Track API request
telemetry.track_request(
    name='forecast_api',
    duration_ms=350.5,
    success=True,
    response_code=200,
    properties={'ticker': 'AAPL'}
)

# Flush to disk
telemetry.flush()
```

### Reading Telemetry Data

```python
from phase4_hybrid_stubs.local_hybrid_bridge import get_telemetry
from datetime import datetime, timedelta

telemetry = get_telemetry()

# Get last 100 events
events = telemetry.read_events(limit=100)

# Filter by event type
metrics = telemetry.read_events(event_type='metric', limit=50)

# Filter by time range
start = datetime.now() - timedelta(hours=24)
recent_events = telemetry.read_events(start_time=start)

# Get summary stats
summary = telemetry.get_summary()
print(f"Total events: {summary['total_events']}")
print(f"Event types: {summary['event_types']}")
print(f"Metric averages: {summary['metric_averages']}")
```

---

## Schema Validation

### Validating Payloads

```python
from phase4_hybrid_stubs.azure_contracts import load_schema, validate_payload

# Load input schema
schema = load_schema(version='0.1', schema_type='prediction_input')

# Create payload
payload = {
    'job_uuid': '12345-67890',
    'ticker': 'AAPL',
    'features': {'momentum': 0.05},
    'date_range': ['2025-01-01', '2025-12-31'],
    'mode': 'forecast'
}

# Validate
is_valid, errors = validate_payload(payload, schema=schema)

if is_valid:
    print("✅ Payload valid")
else:
    print(f"❌ Validation errors: {errors}")
```

### Custom Schema Extensions

```python
from phase4_hybrid_stubs.azure_contracts.azure_io_schema import SCHEMA_REGISTRY

# Add custom schema for v0.2
SCHEMA_REGISTRY['0.2'] = {
    'custom_prediction': {
        'schema_version': '0.2',
        'schema_type': 'custom_prediction',
        'required_fields': ['ticker', 'custom_field'],
        'field_specs': {
            'ticker': {'type': 'string'},
            'custom_field': {'type': 'number', 'min': 0.0, 'max': 1.0}
        }
    }
}

# Use custom schema
from phase4_hybrid_stubs.azure_contracts import load_schema
custom_schema = load_schema(version='0.2', schema_type='custom_prediction')
```

---

## Performance Optimization

### Tuning Cache Settings

```python
from phase4_hybrid_stubs.local_hybrid_bridge import get_router
from phase4_hybrid_stubs.local_hybrid_bridge.compute_router import TASK_CONFIGS

router = get_router()

# Reduce latency for high-priority tasks
TASK_CONFIGS['risk'].max_latency_ms = 500.0  # Stricter SLA

# Increase cache TTL for stable predictions
TASK_CONFIGS['forecast'].cache_ttl_seconds = 1800  # 30 minutes

# Disable cache for real-time tasks
router.dispatch(
    task_type='forecast',
    payload={...},
    use_cache=False  # Force fresh computation
)
```

### Batch Processing Optimization

```python
import asyncio
from phase4_hybrid_stubs.azure_contracts import AzureMLStubClient

async def batch_forecast(tickers):
    client = AzureMLStubClient()
    
    # Create tasks
    tasks = [
        client.submit_job(create_input_spec(ticker))
        for ticker in tickers
    ]
    
    # Run concurrently
    results = await asyncio.gather(*tasks)
    
    return results

# Run batch
tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
results = asyncio.run(batch_forecast(tickers))
```

---

## Troubleshooting

### Debug Mode

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Run analytics with verbose output
result = run_analytics(...)
```

### Cache Issues

```python
from phase4_hybrid_stubs.local_hybrid_bridge import get_router

router = get_router()

# Check cache stats
stats = router.get_cache_stats()
print(f"Cache size: {stats['total_cached_items']}")
print(f"Average age: {stats['average_age_seconds']:.0f}s")

# Clear specific task cache
router.clear_cache(task_type='forecast')

# Clear all caches
router.clear_cache()
```

### Performance Profiling

```python
from phase4_hybrid_stubs.local_hybrid_bridge import get_router

router = get_router()

# Get performance stats
perf = router.get_performance_stats()
print(f"Total tasks: {perf['total_tasks']}")
print(f"Average latency: {perf['average_latency_ms']:.0f}ms")
print(f"Success rate: {perf['success_rate']:.2%}")

# Per-task breakdown
for task_type, stats in perf['task_type_breakdown'].items():
    print(f"{task_type}: {stats['count']} runs, {stats['avg_latency_ms']:.0f}ms avg")
```

---

## Migration to Azure (Future)

### Step 1: Provision Azure Resources

```bash
# Create resource group
az group create --name unified-dashboard-rg --location westus2

# Create ML workspace
az ml workspace create \
  --name unified-dashboard-ml \
  --resource-group unified-dashboard-rg

# Create storage account
az storage account create \
  --name unifieddashboardstorage \
  --resource-group unified-dashboard-rg
```

### Step 2: Update Environment

```bash
# Set Azure credentials
export AZURE_ML_OFFLINE_MODE=false
export AZURE_SUBSCRIPTION_ID=<your-sub-id>
export AZURE_RESOURCE_GROUP=unified-dashboard-rg
export AZURE_ML_WORKSPACE=unified-dashboard-ml
export AZURE_STORAGE_CONNECTION_STRING=<connection-string>
```

### Step 3: No Code Changes Required!

```python
# Same code works in both modes!
from phase4_hybrid_stubs.local_hybrid_bridge import run_analytics

result = run_analytics(
    job_type='forecast',
    payload={...}
)
# Automatically routes to real Azure ML when OFFLINE_MODE=false
```

---

## Appendix: API Reference

### run_analytics()

```python
def run_analytics(
    job_type: Literal['forecast', 'backtest', 'risk', 'optimization', 'shap', 'batch'],
    payload: Dict[str, Any],
    use_cache: bool = True,
    save_to_blob: bool = True
) -> Dict[str, Any]
```

**Parameters:**
- `job_type`: Type of analytics job
- `payload`: Job configuration (ticker, features, date_range, etc.)
- `use_cache`: Enable LRU caching
- `save_to_blob`: Save results to blob storage

**Returns:** Dictionary with predictions, confidence, metadata, etc.

### ComputeRouter.dispatch()

```python
def dispatch(
    task_type: str,
    payload: Dict[str, Any],
    force_backend: Optional[str] = None,
    use_cache: bool = True
) -> Dict[str, Any]
```

**Parameters:**
- `task_type`: Task type ('forecast', 'backtest', etc.)
- `payload`: Task payload
- `force_backend`: Force 'local' or 'azure' backend
- `use_cache`: Enable caching

**Returns:** Task result with metadata (_backend, _from_cache, _dispatch_latency_ms)

### TelemetryProxy Methods

- `track_event(name, properties, measurements)`
- `track_metric(name, value, properties, count, min_value, max_value)`
- `track_request(name, duration_ms, success, response_code, properties)`
- `track_dependency(name, type, target, duration_ms, success, properties)`
- `track_exception(exception, properties, measurements)`

---

**Document Version:** 1.0  
**Last Updated:** October 29, 2025  
**Next:** Run diagnostics and review completion summary

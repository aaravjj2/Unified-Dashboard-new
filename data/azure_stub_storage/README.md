# Phase 4 Hybrid Stub Storage

This directory contains local mock data that mirrors Azure Blob Storage structure.

## Directory Structure

```
/data/azure_stub_storage/
├── sample_forecast.json       # Sample forecast predictions
├── mock_shap_values.json       # Sample SHAP explainability data
├── ml-predictions/             # Container for ML predictions
│   ├── results/
│   │   ├── forecast/
│   │   ├── backtest/
│   │   ├── risk/
│   │   └── shap/
│   └── jobs/                   # Job outputs
└── telemetry/                  # Optional: telemetry blobs

```

## Sample Data Files

### sample_forecast.json
30-day forecast predictions for AAPL with confidence scores.

### mock_shap_values.json
SHAP explainability data showing feature importance for AAPL predictions.

## Usage

This storage is used by `AzureBlobStubClient` to simulate Azure Blob operations locally.
All blob read/write operations are routed here when `OFFLINE_MODE=true`.

## Azure Compatibility

Directory layout mirrors Azure Blob Storage partitioning:
- `predictions/{year}/{month}/{day}/predictions_{ticker}_{timestamp}.parquet`
- `explainability/shap/{year}/{month}/{day}/shap_{ticker}_{timestamp}.parquet`

See `azure_io_schema.py` for full schema definitions.

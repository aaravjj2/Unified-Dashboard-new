# Phase 4 - Hybrid Readiness Design Specification

**Project:** Unified Financial Dashboard  
**Phase:** 4 - Hybrid Readiness (Azure Stubs & Contracts)  
**Agent:** Agent 1B - Lead Engineer  
**Date:** October 29, 2025  
**Version:** 1.0

---

## Executive Summary

Phase 4 establishes a **contract-driven hybrid architecture** that enables the dashboard to run locally using stubs while remaining **architecturally ready** for Azure ML integration. All ML operations are routed through standardized contracts, allowing seamless switching between local and cloud backends via a single configuration toggle.

### Key Achievements

- ✅ **Contract-Based I/O:** All ML interactions use standardized `ContractInputSpec` and `ContractOutputSpec`
- ✅ **Plug-Compatible Stubs:** Local mock clients with async signatures matching real Azure SDK
- ✅ **Intelligent Routing:** Compute router dispatches tasks based on complexity, latency, and resource availability
- ✅ **Telemetry Proxy:** Application Insights-compatible local telemetry logging
- ✅ **Zero Code Changes for Azure Go-Live:** Switch requires only credentials + `OFFLINE_MODE=false`

---

## Architecture Overview

### 1. Component Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     DASH CALLBACKS & UI                          │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                  HYBRID INTERFACE (Entry Point)                  │
│  run_analytics(job_type, payload) → Dict[str, Any]              │
│  - Offline/Online mode detection                                │
│  - Contract validation                                           │
│  - Client factory pattern                                        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                   ┌─────────┴──────────┐
                   │   COMPUTE ROUTER    │
                   │  - Task dispatching │
                   │  - Caching layer   │
                   │  - Load balancing  │
                   └─────────┬──────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
       OFFLINE MODE                  ONLINE MODE
              │                             │
    ┌─────────▼────────┐          ┌────────▼─────────┐
    │ STUB CLIENTS     │          │ REAL AZURE SDKs  │
    │ (Local Mock)     │          │ (Future)         │
    ├──────────────────┤          ├──────────────────┤
    │ AzureMLStubClient│          │ MLClient         │
    │ AzureBlobStubCli│          │ BlobServiceClient│
    │ AzureMonitorStub│          │ TelemetryClient  │
    └─────────┬────────┘          └────────┬─────────┘
              │                             │
       /data/azure_stub_storage/    Azure Blob Storage
       /data/hybrid_logs/           App Insights
```

### 2. Data Flow (Offline Mode)

```
1. User triggers prediction in UI
   │
2. Dash callback → run_analytics(job_type='forecast', payload={...})
   │
3. HybridInterface validates ContractInputSpec
   │
4. ComputeRouter selects backend (stub for offline)
   │
5. AzureMLStubClient.submit_job(input_spec) → ContractOutputSpec
   │
6. Router caches result (TTL = 600s)
   │
7. TelemetryProxy logs event to /data/hybrid_logs/telemetry.jsonl
   │
8. Result returned to UI
```

### 3. Contract Schema

#### Input Contract

```python
@dataclass
class ContractInputSpec:
    ticker: str
    features: Dict[str, Union[float, int, str]]
    date_range: Tuple[str, str]
    mode: str  # 'forecast', 'backtest', 'risk', 'optimization', 'shap'
    uuid: str = field(default_factory=uuid4)
    model_type: ModelType = ModelType.RANDOM_FOREST
    forecast_horizon: ForecastHorizon = ForecastHorizon.MONTHLY
    confidence_level: float = 0.95
    explainability: ExplainabilityLevel = ExplainabilityLevel.BASIC
    metadata: Dict[str, Any] = field(default_factory=dict)
```

#### Output Contract

```python
@dataclass
class ContractOutputSpec:
    job_uuid: str
    ticker: str
    predictions: List[float]
    confidence: List[float]
    timestamp: str
    explainability_blob: Optional[Dict[str, Any]] = None
    status: JobStatus = JobStatus.COMPLETED
    model_version: str = "1.0.0"
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
```

---

## Module Specifications

### 1. azure_contract_definitions.py (380 lines)

**Purpose:** Define standard contracts for all Azure ML interactions.

**Key Components:**
- `ContractInputSpec` dataclass with validation
- `ContractOutputSpec` dataclass with validation
- `ModelType`, `ForecastHorizon`, `JobStatus` enumerations
- Utility functions: `contract_to_json()`, `validate_contract()`, `create_mock_input()`

**Contract Guarantees:**
- All fields are type-checked via dataclass
- Post-init validation ensures data integrity
- Deterministic hashing for caching/deduplication
- JSON serialization with enum support

### 2. azure_io_schema.py (350 lines)

**Purpose:** Schema definitions for JSON/Parquet I/O matching Azure Blob layouts.

**Key Components:**
- Versioned schema registry (`IOSchemaVersion`)
- Schema definitions for input, output, SHAP, Parquet
- `load_schema(version, schema_type)` → Dict
- `validate_payload(payload, schema)` → (bool, errors)
- Azure Blob path utilities: `generate_blob_path()`, `parse_blob_path()`

**Blob Storage Layout:**

```
predictions/{year}/{month}/{day}/predictions_{ticker}_{timestamp}.parquet
explainability/shap/{year}/{month}/{day}/shap_{ticker}_{timestamp}.parquet
backtest/{year}/{month}/{day}/backtest_{ticker}_{timestamp}.parquet
```

### 3. azure_stub_clients.py (480 lines)

**Purpose:** Mock Azure services with async signatures.

**Key Components:**

#### AzureMLStubClient
- `submit_job(input_spec)` → ContractOutputSpec
- Generates predictions with deterministic seeding (ticker-based)
- Simulates realistic latency (200-500ms for forecast)
- 95% success rate simulation
- SHAP blob generation

#### AzureBlobStubClient
- `upload_blob(blob_name, data)` → bool
- `download_blob(blob_name)` → str
- `list_blobs(prefix)` → List[str]
- Local storage: `/data/azure_stub_storage/{container}/`

#### AzureMonitorStubClient
- `track_event(name, properties, measurements)`
- `track_metric(name, value, properties)`
- `track_request(name, duration_ms, success)`
- Writes to `/data/hybrid_logs/telemetry.jsonl`

### 4. hybrid_interface.py (300 lines)

**Purpose:** Unified entry point for all analytics operations.

**Key Function:**

```python
def run_analytics(
    job_type: Literal['forecast', 'backtest', 'risk', 'optimization', 'shap'],
    payload: Dict[str, Any],
    use_cache: bool = True,
    save_to_blob: bool = True
) -> Dict[str, Any]
```

**Configuration:**
- `OFFLINE_MODE` environment variable (default: true)
- `WORKSPACE_CONFIG` from environment

**Convenience Wrappers:**
- `run_forecast(ticker, features, date_range, horizon)`
- `run_backtest(ticker, features, date_range)`
- `run_risk_analysis(ticker, features, date_range, confidence_level)`

### 5. compute_router.py (350 lines)

**Purpose:** Intelligent task dispatch and caching.

**Key Components:**

#### TaskConfig
- `task_type`, `priority` (1-5)
- `max_latency_ms`, `prefer_local`, `requires_gpu`
- `cache_ttl_seconds`, `retry_on_failure`, `max_retries`

#### ComputeRouter
- `dispatch(task_type, payload, force_backend, use_cache)` → Dict
- Backend selection logic:
  - Offline mode → always local
  - High priority (≥4) → prefer Azure
  - GPU required → Azure only
  - Lightweight tasks → local
- LRU cache with TTL
- Retry with exponential backoff
- Performance tracking

### 6. telemetry_proxy.py (320 lines)

**Purpose:** Application Insights-compatible local telemetry.

**Event Types:**
- `TelemetryEvent` (customEvent)
- `MetricEvent` (metric)
- `RequestEvent` (request/operation)
- Dependency, Exception

**Storage Format:** JSONL (JSON Lines)

```json
{"timestamp": "2025-10-29T14:35:22", "event_type": "customEvent", "name": "prediction_completed", ...}
{"timestamp": "2025-10-29T14:35:23", "event_type": "metric", "metric_name": "latency_ms", "value": 350.0, ...}
```

**Features:**
- Buffered writes with auto-flush (interval configurable)
- `read_events(limit, event_type, start_time, end_time)` for analysis
- `get_summary()` for aggregated stats
- Drop-in replacement for Application Insights

### 7. hybrid_diagnostics.py (450 lines)

**Purpose:** Comprehensive integration testing and validation.

**Test Suite:**
1. Contract Definitions (validation, enum conversions)
2. I/O Schemas (schema loading, payload validation, blob paths)
3. Stub Clients (ML, Blob, Monitor async operations)
4. Hybrid Interface (offline mode, analytics execution)
5. Compute Router (dispatch, cache, performance)
6. Telemetry Proxy (event tracking, read/write)
7. End-to-End Integration (full workflow)

**Report Output:** `/docs/phase4_hybrid_stubs/PHASE4_DIAGNOSTIC_REPORT.md`

**CLI Usage:**

```bash
python -m phase4_hybrid_stubs.local_hybrid_bridge.hybrid_diagnostics --verbose
```

---

## Configuration & Environment Variables

### Required Environment Variables

```bash
# Offline/Online mode toggle
AZURE_ML_OFFLINE_MODE=true  # true = local stubs, false = real Azure

# Azure ML Workspace (for online mode)
AZURE_SUBSCRIPTION_ID=<your-subscription-id>
AZURE_RESOURCE_GROUP=unified-dashboard-rg
AZURE_ML_WORKSPACE=unified-dashboard-ml

# Azure Blob Storage (for online mode)
AZURE_BLOB_CONTAINER=ml-predictions
AZURE_STORAGE_CONNECTION_STRING=<connection-string>

# Application Insights (for online mode)
APPINSIGHTS_INSTRUMENTATION_KEY=<instrumentation-key>
```

### Configuration Files

- `.env` or `doppler.env` for local development
- `keys.env` for secure credential management
- No hardcoded credentials in code

---

## Performance Characteristics

### Latency Targets (Stub Mode)

| Task Type | Min (ms) | Max (ms) | Avg (ms) |
|-----------|----------|----------|----------|
| Forecast | 200 | 500 | 350 |
| Backtest | 500 | 1500 | 1000 |
| Risk | 300 | 800 | 550 |
| Optimization | 1000 | 3000 | 2000 |
| SHAP | 400 | 900 | 650 |
| Batch | 2000 | 5000 | 3500 |

### Caching

- **Cache TTL:** 5-30 minutes (task-dependent)
- **Cache Hit Rate:** Target >70% for repeated queries
- **Cache Key:** SHA256 hash of (task_type, ticker, features, date_range)

### Resource Usage

- **Memory:** ~50MB for stub clients + caching
- **Disk:** <100MB for telemetry logs (auto-rotation recommended)
- **CPU:** Minimal (<5% for typical workloads)

---

## Security & Compliance

### Data Handling

- **Local Storage:** All mock data stored in `/data/azure_stub_storage/` (gitignored)
- **Telemetry:** Sensitive data NOT logged (ticker and feature names only, no PII)
- **Credentials:** Never hardcoded; always from environment or secure stores

### Contract Validation

- All inputs validated before execution
- Type checking via dataclasses
- Schema validation for I/O payloads
- Error messages sanitized (no stack traces in production)

---

## Testing Strategy

### Unit Tests

- Contract validation (positive + negative cases)
- Schema loading and validation
- Stub client async behavior
- Caching and eviction logic

### Integration Tests

- Full workflow: Input → Analytics → Storage → Telemetry
- Multi-ticker batch operations
- Cache hit/miss scenarios
- Error handling and retries

### Performance Tests

- Latency benchmarks
- Cache performance under load
- Concurrent request handling

---

## Migration Path to Azure

### Phase 1: Local Development (Current)

```python
OFFLINE_MODE = true
# Uses stubs, no Azure credentials required
```

### Phase 2: Azure Go-Live

1. Provision Azure ML workspace
2. Register model in workspace
3. Deploy managed online endpoint
4. Set environment variables:

```bash
AZURE_ML_OFFLINE_MODE=false
AZURE_SUBSCRIPTION_ID=<real-sub-id>
AZURE_ML_WORKSPACE=<real-workspace>
AZURE_STORAGE_CONNECTION_STRING=<real-connection>
APPINSIGHTS_INSTRUMENTATION_KEY=<real-key>
```

5. **No code changes required!**

### Phase 3: Hybrid Mode (Future)

- Route lightweight tasks to local compute
- Route heavy tasks to Azure ML
- Use `ComputeRouter.dispatch(force_backend='azure')` for manual control

---

## Monitoring & Observability

### Local Telemetry

- **File:** `/data/hybrid_logs/telemetry.jsonl`
- **Format:** JSONL (one event per line)
- **Rotation:** Manual or cron-based

### Azure Application Insights (Online Mode)

- Custom events: `prediction_completed`, `model_training_started`
- Metrics: `forecast_accuracy`, `latency_ms`
- Requests: `forecast_api`, `backtest_api`
- Dependencies: `azure_blob_read`, `azure_ml_submit`

### Diagnostic Dashboard (Future)

- Grafana / Prometheus integration
- Real-time latency charts
- Cache hit rate monitoring
- Error rate alerts

---

## Troubleshooting

### Common Issues

**Issue:** Imports fail with `ModuleNotFoundError`  
**Solution:** Add project root to `PYTHONPATH`:

```bash
export PYTHONPATH=/mnt/c/Aarav/fin_env/unified-dashboard:$PYTHONPATH
```

**Issue:** Telemetry file grows too large  
**Solution:** Implement log rotation:

```bash
logrotate /data/hybrid_logs/telemetry.jsonl
```

**Issue:** Cache returns stale data  
**Solution:** Reduce TTL or clear cache:

```python
router = get_router()
router.clear_cache(task_type='forecast')
```

---

## Appendix

### A. File Tree

```
/phase4_hybrid_stubs/
├── __init__.py
├── azure_contracts/
│   ├── __init__.py
│   ├── azure_contract_definitions.py  (380 lines)
│   ├── azure_io_schema.py             (350 lines)
│   └── azure_stub_clients.py          (480 lines)
└── local_hybrid_bridge/
    ├── __init__.py
    ├── hybrid_interface.py            (300 lines)
    ├── compute_router.py              (350 lines)
    ├── telemetry_proxy.py             (320 lines)
    └── hybrid_diagnostics.py          (450 lines)

/data/
├── azure_stub_storage/
│   ├── sample_forecast.json
│   ├── mock_shap_values.json
│   └── ml-predictions/
└── hybrid_logs/
    └── telemetry.jsonl

/docs/phase4_hybrid_stubs/
├── PHASE4_DESIGN_SPEC.md              (this file)
├── PHASE4_IMPLEMENTATION_GUIDE.md
├── PHASE4_DIAGNOSTIC_REPORT.md
└── PHASE4_COMPLETION_SUMMARY.md
```

### B. Key Metrics

- **Total Lines of Code:** ~2,600
- **Documentation Lines:** ~2,000
- **Test Coverage:** 7 integration tests
- **API Surface:** 3 clients + 1 router + 1 telemetry proxy
- **Contract Schemas:** 4 (input, output, SHAP, Parquet)

---

**Document Version:** 1.0  
**Last Updated:** October 29, 2025  
**Next Review:** Phase 5 - Azure Go-Live Preparation

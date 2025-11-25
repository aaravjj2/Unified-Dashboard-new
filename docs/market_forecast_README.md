# Market Forecast - API Documentation

## Overview
Local-first market forecast service with Bento model serving, deterministic mode, and PostgreSQL/JSON persistence.

## Quick Start

### 1. Start Mock Bento Service
```bash
python services/mock_bento/app.py
# Service starts on http://localhost:5001
```

### 2. Configure Environment
```bash
export FORECAST_BENTO_URL=http://localhost:5001/predict
export FORECAST_DETERMINISTIC=1  # Use fixtures instead of Bento
export DB_URL=postgresql://user:pass@localhost/db  # Optional
```

### 3. Run Dashboard
```bash
python3 app.py
# Navigate to Market Forecast tab
```

---

## API Endpoints

### POST /api/market_forecast/run
Execute market forecast (sync or async).

**Request:**
```json
{
  "ticker": "AAPL",
  "horizon": 30,
  "confidence": 0.95,
  "model": "lstm",
  "mode": "sync"
}
```

**Parameters:**
- `ticker` (string, required): Stock ticker symbol (e.g., "AAPL", "TSLA")
- `horizon` (integer, required): Forecast horizon in days (7, 30, or 90)
- `confidence` (float, required): Confidence level (0.90, 0.95, or 0.99)
- `model` (string, required): Model type ("lstm", "prophet", or "ensemble")
- `mode` (string, optional): Execution mode ("sync" or "async", default: "sync")

**Response (sync):**
```json
{
  "forecast_id": "550e8400-e29b-41d4-a716-446655440000",
  "ticker": "AAPL",
  "horizon": 30,
  "confidence": 0.95,
  "model": "lstm",
  "status": "completed",
  "timestamp": "2024-01-15T12:00:00Z",
  "forecast": [
    {
      "date": "2024-01-15",
      "yhat": 150.25,
      "yhat_lower": 147.80,
      "yhat_upper": 152.70
    },
    ...
  ],
  "metrics": {
    "rmse": 2.45,
    "mae": 1.82,
    "mape": 0.0121
  }
}
```

**Response (async):**
```json
{
  "forecast_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "poll_url": "/api/market_forecast/status/550e8400-e29b-41d4-a716-446655440000"
}
```

---

### GET /api/market_forecast/latest
Retrieve the most recent forecast.

**Query Parameters:**
- `ticker` (string, optional): Filter by ticker symbol

**Response:** Same as POST /run (sync mode)

---

### GET /api/market_forecast/history
Retrieve historical forecast runs with pagination.

**Query Parameters:**
- `ticker` (string, optional): Filter by ticker
- `limit` (integer, optional): Max results (default: 20)
- `offset` (integer, optional): Pagination offset (default: 0)

**Response:**
```json
{
  "forecasts": [
    {
      "forecast_id": "...",
      "ticker": "AAPL",
      "horizon": 30,
      ...
    },
    ...
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

---

### GET /api/market_forecast/explain/:forecast_id
Retrieve SHAP explainability data for a specific forecast.

**Response:**
```json
{
  "forecast_id": "550e8400-e29b-41d4-a716-446655440000",
  "shap_values": [
    {
      "feature": "price_momentum",
      "importance": 0.325
    },
    {
      "feature": "volume_trend",
      "importance": 0.215
    },
    ...
  ],
  "base_value": 150.0,
  "features": {
    "price_momentum": 0.025,
    "volume_trend": 1.15,
    ...
  }
}
```

---

### GET /api/market_forecast/admin/health
Service health check.

**Response:**
```json
{
  "status": "healthy",
  "bento_available": true,
  "deterministic_mode": false,
  "persistence_type": "postgres",
  "timestamp": "2024-01-15T12:00:00Z"
}
```

**Status Values:**
- `healthy`: All systems operational
- `degraded`: Bento unavailable, using fallback
- `down`: Critical failure

---

## Component IDs

All UI components use the `mf-*` prefix:

```python
COMPONENT_IDS = {
    "ticker_input": "mf-ticker-input",
    "horizon_select": "mf-horizon-select",
    "confidence_select": "mf-confidence-select",
    "model_select": "mf-model-select",
    "mode_toggle": "mf-mode-toggle",
    "run_button": "mf-run-button",
    "forecast_chart": "mf-forecast-chart",
    "summary_table": "mf-summary-table",
    "download_button": "mf-download-button",
    "shap_chart": "mf-shap-chart",
    "shap_download": "mf-shap-download",
    "status_banner": "mf-status-banner",
    "loading_overlay": "mf-loading-overlay"
}
```

---

## Error Handling

### Validation Errors (400)
```json
{
  "error": "horizon must be 7, 30, or 90"
}
```

### Not Found (404)
```json
{
  "error": "No forecasts found"
}
```

### Internal Error (500)
```json
{
  "error": "Internal error: Bento service timeout"
}
```

### Service Unavailable (503)
```json
{
  "status": "down",
  "error": "Database connection failed",
  "timestamp": "2024-01-15T12:00:00Z"
}
```

---

## Deterministic Mode

For testing and development, enable deterministic mode to use fixtures:

```bash
export FORECAST_DETERMINISTIC=1
```

**Fixture Files:**
- `tests/fixtures/forecast/forecast_fixture.json` - 30-day AAPL forecast
- `tests/fixtures/forecast/explain_fixture.json` - SHAP explainability data

**Benefits:**
- Reproducible test results
- No dependency on Bento service
- Fast execution for CI/CD

---

## Persistence

### PostgreSQL (Primary)
Set `DB_URL` environment variable:
```bash
export DB_URL=postgresql://user:pass@localhost:5432/dashboard
```

**Schema:**
- `market_forecasts` - Forecast runs and predictions
- `forecast_explanations` - SHAP explainability data
- `forecast_performance` - Accuracy tracking (future)

**Migrations:**
```bash
psql -U user -d dashboard -f migrations/0001_create_market_forecasts.sql
```

### JSON (Fallback)
If PostgreSQL is unavailable, data is stored in:
- `data/forecast/<forecast_id>.json` - Forecast results
- `data/forecast/explain/<forecast_id>.json` - Explainability data

---

## BentoML Integration

### Production Deployment
```bash
cd bento_services/forecast_service
bentoml build
bentoml containerize forecast_service:latest
docker run -p 5001:5001 forecast_service:latest
```

### Docker Compose
```bash
docker-compose -f docker-compose.bento.yml up
```

---

## Testing

### Unit Tests
```bash
pytest tests/test_market_forecast_unit.py -v
```

**Coverage:**
- ✅ API endpoints (POST /run, GET /latest, GET /history, GET /explain, GET /health)
- ✅ Adapter logic (deterministic mode, Bento calls, fallback)
- ✅ Persistence layer (JSON save/retrieve, pagination)
- ✅ Property-based tests (forecast length, confidence intervals)

### Browser Tests
```bash
pytest tests/test_market_forecast_browser.py
```

---

## Monitoring

### Health Check
```bash
curl http://localhost:8050/api/market_forecast/admin/health
```

### Logs
```bash
tail -f logs/dashboard.log | grep market_forecast
```

---

## Troubleshooting

### Bento Service Unavailable
**Symptom:** `"status": "degraded"` in health check  
**Solution:** Start mock Bento service or check `FORECAST_BENTO_URL`

### Fixture Not Found
**Symptom:** `FileNotFoundError: tests/fixtures/forecast/forecast_fixture.json`  
**Solution:** Ensure fixture files exist in `tests/fixtures/forecast/`

### PostgreSQL Connection Error
**Symptom:** `"persistence_type": "json"` instead of `"postgres"`  
**Solution:** Verify `DB_URL` is set and database is accessible

### Duplicate Callback Errors
**Symptom:** Dash callback errors in browser console  
**Solution:** Ensure component IDs use `mf-*` prefix and are unique

---

## Architecture

```
┌─────────────────┐
│   Dash UI       │  (financial_dashboard/tabs/market_forecast_rebuild.py)
│   (3 panels)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Flask API      │  (api/market_forecast.py)
│  (5 endpoints)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Forecast Adapter│  (services/forecast_adapter.py)
│ (Bento client)  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌─────────────┐
│  Bento  │ │ Fixture     │
│ Service │ │ (JSON files)│
└─────────┘ └─────────────┘
         │
         ▼
┌─────────────────┐
│  Persistence    │  (services/forecast_persistence.py)
│  (Postgres/JSON)│
└─────────────────┘
```

---

## Production Checklist

- [ ] Configure `FORECAST_BENTO_URL` to production Bento service
- [ ] Set `FORECAST_DETERMINISTIC=0` (disable fixtures)
- [ ] Configure `DB_URL` for PostgreSQL
- [ ] Run database migrations
- [ ] Set up monitoring for `/admin/health` endpoint
- [ ] Configure log aggregation
- [ ] Enable HTTPS for API endpoints
- [ ] Set rate limiting on `/run` endpoint
- [ ] Deploy Bento service with auto-scaling
- [ ] Set up A/B testing for model selection

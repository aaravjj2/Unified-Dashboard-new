# Market Forecast - Mock Bento Service

Standalone Flask service simulating BentoML forecast endpoint for local development.

## Quick Start

```bash
# Run mock service
python services/mock_bento/app.py

# Service starts on http://localhost:5001
```

## Endpoints

### POST /predict
Execute forecast prediction.

**Request:**
```json
{
  "ticker": "AAPL",
  "horizon": 30,
  "confidence": 0.95,
  "model": "lstm"
}
```

**Response:**
```json
{
  "ticker": "AAPL",
  "forecast": [
    {"date": "2024-01-01", "yhat": 150.5, "yhat_lower": 148.0, "yhat_upper": 153.0},
    ...
  ],
  "metrics": {
    "rmse": 2.5,
    "mae": 1.8,
    "mape": 0.012
  },
  "model": "lstm",
  "horizon": 30,
  "confidence": 0.95
}
```

### GET /health
Service health check.

**Response:**
```json
{
  "status": "healthy",
  "service": "mock_bento_forecast",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Fixture Loading

Service loads from `tests/fixtures/forecast/forecast_fixture.json` if available.  
Falls back to synthetic forecast generation if fixture missing.

## Integration with Adapter

Set environment variable:
```bash
export FORECAST_BENTO_URL=http://localhost:5001/predict
```

The `ForecastAdapter` will automatically use this mock service for forecast requests.

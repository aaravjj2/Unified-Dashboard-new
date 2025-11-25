# Market Forecast Fixtures - AGENT-1B Phase 5

Deterministic test fixtures for reproducible testing.

## Files

### forecast_fixture.json
30-day AAPL forecast with confidence intervals.

**Structure:**
```json
{
  "forecast_id": "test-forecast-001",
  "ticker": "AAPL",
  "horizon": 30,
  "confidence": 0.95,
  "model": "lstm",
  "status": "completed",
  "timestamp": "2024-01-15T12:00:00Z",
  "forecast": [
    {"date": "YYYY-MM-DD", "yhat": float, "yhat_lower": float, "yhat_upper": float},
    ...
  ],
  "metrics": {
    "rmse": 2.45,
    "mae": 1.82,
    "mape": 0.0121
  }
}
```

### explain_fixture.json
SHAP explainability data for forecast.

**Structure:**
```json
{
  "forecast_id": "test-forecast-001",
  "shap_values": [
    {"feature": str, "importance": float},
    ...
  ],
  "base_value": float,
  "features": {
    "feature_name": float,
    ...
  }
}
```

## Usage

### In Tests
```python
import json
from pathlib import Path

fixture_path = Path("tests/fixtures/forecast/forecast_fixture.json")
with open(fixture_path) as f:
    forecast = json.load(f)
```

### With Adapter
```bash
export FORECAST_DETERMINISTIC=1
# Adapter will automatically use fixtures
```

### With Mock Bento
```bash
# Mock service loads fixtures on startup
python services/mock_bento/app.py
```

## Characteristics

- **Deterministic**: Same inputs always produce same outputs
- **Realistic**: Based on actual AAPL price patterns
- **Complete**: Includes all required fields for UI rendering
- **Versioned**: Copied to reports/market_forecast_rebuild/fixtures/ on commit

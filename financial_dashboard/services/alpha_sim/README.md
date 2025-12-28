# AlphaSim - Internal Alpha Vantage-Compatible API

AlphaSim is an internal service that provides Alpha Vantage-compatible API endpoints for the Research Lab. It fetches data from internal sources (PriceClient, yfinance) and provides technical indicators, news sentiment analysis, and options chain data.

## Features

- **TIME_SERIES_DAILY** - Daily OHLCV price data
- **TIME_SERIES_INTRADAY** - Intraday price data (1min, 5min, 15min, 30min, 60min)
- **SMA** - Simple Moving Average indicator
- **EMA** - Exponential Moving Average indicator
- **RSI** - Relative Strength Index indicator
- **NEWS_SENTIMENT** - News sentiment analysis using FinBERT (or mock)
- **HISTORICAL_OPTIONS** - Options chain data (synthetic when real data unavailable)

## Quick Start

### Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements-alpha-sim.txt

# Run the server
uvicorn financial_dashboard.services.alpha_sim.app:app --reload --port 8065
```

### Smoke Test

```bash
# Health check
curl http://localhost:8065/health

# Basic query
curl 'http://localhost:8065/query?function=TIME_SERIES_DAILY&symbol=AAPL&apikey=demo'

# SMA indicator
curl 'http://localhost:8065/query?function=SMA&symbol=AAPL&time_period=10&apikey=demo'

# News sentiment
curl 'http://localhost:8065/query?function=NEWS_SENTIMENT&symbol=AAPL&apikey=demo'

# Options chain
curl 'http://localhost:8065/query?function=HISTORICAL_OPTIONS&symbol=AAPL&apikey=demo'
```

## API Reference

### Query Endpoint

`GET /query`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `function` | string | Yes | AlphaV function (TIME_SERIES_DAILY, SMA, etc.) |
| `symbol` | string | Yes* | Ticker symbol (required for most functions) |
| `apikey` | string | Yes | API key for rate limiting |
| `outputsize` | string | No | `compact` (100 pts) or `full` |
| `interval` | string | No | Time interval for intraday (1min, 5min, etc.) |
| `time_period` | int | No | Periods for indicators (default: 10) |
| `series_type` | string | No | Price type: open, high, low, close |

**Response Format:**

All responses follow Alpha Vantage JSON format with `Meta Data` and data-specific keys.

### Health Endpoint

`GET /health`

Returns service health status.

### Metrics Endpoint

`GET /metrics`

Returns cache and rate limiter statistics. Supports Prometheus format with `?format=prometheus`.

### Admin Endpoints

Admin endpoints require the `X-Admin-Key` header.

- `GET /admin/quota/{key}` - Get quota info for an API key
- `POST /admin/reset/{key}` - Reset quota for an API key

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_ALPHA_SIM` | `false` | Feature flag to enable AlphaSim in PriceClient |
| `ALPHA_SIM_URL` | `http://localhost:8065` | AlphaSim service URL |
| `ALPHA_SIM_APIKEY` | `demo` | Default API key |
| `ALPHA_SIM_ADMIN_KEY` | `admin` | Admin API key |
| `ALPHA_SIM_CACHE_DIR` | `/tmp/alpha_sim_cache` | Cache directory |
| `ALPHA_SIM_CACHE_TTL` | `300` | Default cache TTL (seconds) |
| `ALPHA_SIM_REDIS_URL` | - | Redis URL for production cache |
| `FINBERT_MODEL` | `ProsusAI/finbert` | FinBERT model for sentiment |

## Cache TTL Policy

| Endpoint | Dev TTL | Prod TTL | Rationale |
|----------|---------|----------|-----------|
| TIME_SERIES_INTRADAY | 30s | 5s | Low-latency needs |
| TIME_SERIES_DAILY | 1h | 1h | Updates once per day |
| Technical Indicators | 10m | 5m | Save compute |
| NEWS_SENTIMENT | 15m | 5m | FinBERT is expensive |
| HISTORICAL_OPTIONS | 24h | 24h | Heavy data, rare updates |

## Rate Limiting

- Token bucket per API key
- Default: 25 requests/day
- Returns 429 when exhausted
- Admin can reset via `/admin/reset/{key}`

## Using AlphaSimClient

```python
from financial_dashboard.services.alpha_sim.client import AlphaSimClient, use_alpha_sim

# Check feature flag
if use_alpha_sim():
    client = AlphaSimClient()
    
    # Get daily data
    data = client.time_series_daily("AAPL")
    
    # Get SMA
    sma = client.sma("AAPL", time_period=20)
    
    # Get news sentiment
    sentiment = client.news_sentiment("AAPL")
    
    # Get options chain
    options = client.options_chain("AAPL")
```

## Running Tests

```bash
# Run all alpha_sim tests
pytest financial_dashboard/services/alpha_sim/tests/ -v

# Run specific test file
pytest financial_dashboard/services/alpha_sim/tests/test_news.py -v

# Run with coverage
pytest financial_dashboard/services/alpha_sim/tests/ --cov=financial_dashboard.services.alpha_sim
```

## Project Structure

```
financial_dashboard/services/alpha_sim/
├── __init__.py
├── app.py              # FastAPI application
├── engine.py           # Data fetching and processing
├── indicators.py       # Technical indicator calculations
├── news.py             # News sentiment (FinBERT)
├── options.py          # Options chain data
├── cache.py            # TTL caching (diskcache/Redis)
├── rate_limiter.py     # Token bucket rate limiting
├── schema.py           # Response builders
├── metrics.py          # Prometheus metrics
├── client.py           # AlphaSimClient for consumers
├── requirements-alpha-sim.txt
├── pytest.ini
├── README.md
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_cache.py
    ├── test_rate_limiter.py
    ├── test_schema.py
    ├── test_indicators.py
    ├── test_engine.py
    ├── test_endpoints.py
    ├── test_news.py
    └── test_options.py
```

## OpenAPI Specification

The full OpenAPI spec is available at `financial_dashboard/docs/openapi/alpha_sim_openapi.yaml`.

## CI/CD

The `alpha_sim:smoke` workflow runs on every push to paths under `financial_dashboard/services/alpha_sim/`:

1. Install dependencies
2. Run unit tests
3. Start server and run smoke tests
4. Verify all endpoints respond correctly

## Roadmap

- [x] MVP: TIME_SERIES_DAILY, SMA, cache, rate-limiter
- [x] Phase 2: NEWS_SENTIMENT with FinBERT
- [x] Phase 3: HISTORICAL_OPTIONS, admin endpoints
- [ ] Phase 4: BentoML/Triton model serving
- [ ] Phase 5: Redis production cache
- [ ] Phase 6: Full PriceClient integration

## Contact

For questions, message `#research-lab` in Slack.

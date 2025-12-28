# Alpaca Options Lab

A professional-grade options chain viewer with real-time data from Alpaca Markets.

## Features

- **Real-time Options Data**: Fetches live options chains via Alpaca API
- **Alpaca-style UI**: Clean, professional interface matching Alpaca web design
- **Side-by-side Display**: Calls and puts displayed together per strike
- **Full Greeks**: Delta, Gamma, Theta, Vega for all contracts
- **IV Display**: Implied volatility with visual indicators
- **Export**: CSV and JSON export for analysis
- **Caching**: TTL-based cache to reduce API calls
- **Circuit Breaker**: Resilient API handling with automatic recovery

## Quick Start

### 1. Set up API Keys

Create a `keys.env` file in the project root:

```bash
APCA_API_KEY_ID=your_api_key_here
APCA_API_SECRET_KEY=your_secret_key_here
```

### 2. Run the Standalone UI

```bash
python test_alpaca_options_ui.py
```

Open http://localhost:8053 in your browser.

### 3. Use in Main Dashboard

The Alpaca Options Lab is integrated into the main Financial Dashboard under the "💹 Options Lab" tab.

```bash
python financial_dashboard/index.py
```

## API Reference

### AlpacaOptionsClient

```python
from financial_dashboard.tabs.options_lab.alpaca_options import get_alpaca_client

client = get_alpaca_client()

# Fetch options chain
chain_data = client.get_option_chain('SPY')

# Access data
print(chain_data['ticker'])      # 'SPY'
print(chain_data['spot_price'])  # Current stock price
print(chain_data['expirations']) # Available expirations
print(chain_data['chains'])      # Dict of {expiration: {calls, puts}}
```

### Caching

```python
from financial_dashboard.tabs.options_lab.options_cache import get_options_cache

cache = get_options_cache(default_ttl=300, max_size=100)

# Get cached data
data = cache.get('SPY_2025-12-29')

# Get with auto-fetch
data, was_cached = cache.get_or_fetch(
    'SPY_2025-12-29',
    lambda: client.get_option_chain('SPY')
)

# Check stats
print(cache.stats.hit_rate)  # Cache hit rate
```

### Circuit Breaker

```python
from financial_dashboard.tabs.options_lab.circuit_breaker import with_circuit_breaker

@with_circuit_breaker("alpaca_api", failure_threshold=5, recovery_timeout=60)
def fetch_data():
    return client.get_option_chain('SPY')
```

### Export

```python
from financial_dashboard.tabs.options_lab.export_utils import (
    export_chain_to_csv,
    export_chain_to_json
)

# Export to CSV
csv_content = export_chain_to_csv(chain_data, '2025-12-29')

# Export to JSON
json_content = export_chain_to_json(chain_data, pretty=True)
```

## Testing

### Run Unit Tests

```bash
pytest tests/test_alpaca_callbacks.py -v
```

### Run E2E Tests

```bash
# Start test server
python test_alpaca_options_ui.py &

# Run Playwright tests
python test_alpaca_deep_8053.py
```

### Run All Tests

```bash
pytest tests/ -v --tb=short
```

## Health Endpoints

When integrated with the main dashboard, health endpoints are available:

- `GET /api/options/health` - Basic health check
- `GET /api/options/ready` - Readiness probe
- `GET /api/options/metrics` - Service metrics
- `GET /api/options/cache/info` - Cache details
- `POST /api/options/cache/clear` - Clear cache

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APCA_API_KEY_ID` | Alpaca API Key | Required |
| `APCA_API_SECRET_KEY` | Alpaca API Secret | Required |
| `APCA_API_BASE_URL` | Alpaca API URL | `https://paper-api.alpaca.markets` |
| `APCA_DATA_URL` | Alpaca Data URL | `https://data.alpaca.markets` |

### Cache Settings

Default cache configuration:
- **TTL**: 5 minutes (300 seconds)
- **Max Size**: 100 entries
- **Eviction**: LRU (Least Recently Used)

## Architecture

```
financial_dashboard/tabs/options_lab/
├── __init__.py           # Module exports
├── alpaca_options.py     # Alpaca API client
├── alpaca_ui.py          # Dash UI components
├── alpaca_callbacks.py   # Dash callbacks
├── options_cache.py      # TTL cache implementation
├── circuit_breaker.py    # Resilience pattern
├── export_utils.py       # CSV/JSON export
├── health_endpoints.py   # Health check API
└── types.py              # Type definitions
```

## Troubleshooting

### "Alpaca API credentials not configured"

Ensure `keys.env` contains valid Alpaca credentials and is loaded before starting the app.

### Cache not working

Check cache stats via `/api/options/cache/info` or programmatically:

```python
from financial_dashboard.tabs.options_lab.options_cache import get_options_cache
print(get_options_cache().get_info())
```

### API rate limiting

The circuit breaker will automatically back off when hitting rate limits. Check circuit state:

```python
from financial_dashboard.tabs.options_lab.circuit_breaker import get_all_breaker_stats
print(get_all_breaker_stats())
```

## License

Part of the Unified Dashboard project.

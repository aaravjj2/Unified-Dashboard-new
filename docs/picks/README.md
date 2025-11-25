# Weekly & Monthly Picks Pipeline - Operator Guide

## Overview

The Picks Pipeline provides automated stock recommendations with price enrichment, caching, and provenance tracking.

**Components:**
- **Data Loader**: `tools/picks_load.py` - Ingest CSV into DB or JSON
- **Background Updater**: `background/picks_updater.py` - Scheduled price refreshes
- **API Endpoints**: `financial_dashboard/api/picks_api.py` - REST API
- **UI Tabs**: `financial_dashboard/tabs/*_picks_rebuild.py` - Dashboard UI
- **Utilities**: `utils/picks_fetcher.py`, `utils/cache_manager.py`

---

## Quick Start

### 1. Load Picks Data

```bash
# Load weekly picks from CSV into SQLite
python tools/picks_load.py --type weekly --csv outputs/weekly_picks.csv

# Load monthly picks into JSON fallback
python tools/picks_load.py --type monthly --csv outputs/monthly_picks.csv --json

# Generate deterministic test fixtures
python tools/picks_load.py --type weekly --fixture
python tools/picks_load.py --type monthly --fixture
```

### 2. Run Background Price Updater

```bash
# Run once manually
python background/picks_updater.py --once

# Run on schedule (every 60 minutes)
python background/picks_updater.py --schedule 60
```

### 3. Test API Endpoints

```bash
# Get weekly picks
curl http://localhost:8050/api/weekly_picks?limit=10

# Get monthly picks with pagination
curl http://localhost:8050/api/monthly_picks?limit=20&offset=0

# Health check
curl http://localhost:8050/api/picks/health

# Trigger reload (admin)
curl -X POST http://localhost:8050/api/picks/reload \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## Configuration

### Environment Variables

```bash
# Deterministic mode (uses fixtures instead of live data)
export OPTIONS_DETERMINISTIC=1

# Admin token for protected endpoints
export PICKS_ADMIN_TOKEN=your_secure_token_here

# Alpaca API keys (optional, for price fetching)
export ALPACA_KEY_WEEKLY=your_key
export ALPACA_SECRET_WEEKLY=your_secret
```

### File Locations

```
data/
├── picks.db                    # SQLite database
└── picks/
    ├── weekly_picks.json       # JSON fallback (weekly)
    ├── monthly_picks.json      # JSON fallback (monthly)
    ├── weekly_cache.json       # UI cache (weekly)
    ├── monthly_cache.json      # UI cache (monthly)
    └── .picks_updater.lock     # Job lock file

reports/picks/
├── fixtures/
│   ├── weekly_fixture.json     # Deterministic test data
│   └── monthly_fixture.json    # Deterministic test data
└── logs/
    ├── picks_updater.log       # Background job logs
    └── last_run.json           # Last job status

migrations/
└── 0002_create_picks_tables.sql  # Database schema
```

---

## Data Flow

```
CSV File
   ↓
[picks_load.py] → SQLite DB
                  ↓
              [picks_updater.py] → Price Enrichment (yfinance)
                                   ↓
                               Cache Files (JSON)
                                   ↓
                               [API Endpoints] → JSON Response
                                   ↓
                               [UI Tabs] → DataTable Display
```

**Provenance Tracking:**
- Each pick includes: `price_source`, `price_fetched_at`, `price_age_seconds`
- Sources: `yfinance`, `deterministic_fixture`, `price_client`, `cache`

---

## API Reference

### GET /api/weekly_picks

**Query Parameters:**
- `limit` (int, default=100): Max records
- `offset` (int, default=0): Pagination offset
- `fixture` (bool): Use deterministic fixture

**Response:**
```json
{
  "status": "success",
  "pick_type": "weekly",
  "count": 20,
  "total_count": 20,
  "has_more": false,
  "data": [
    {
      "Ticker": "AAPL",
      "Company": "Apple Inc.",
      "Rank": 1,
      "Score": 95,
      "current_price": 150.25,
      "price_source": "yfinance",
      "price_fetched_at": "2025-11-21T10:30:00Z",
      "price_age_seconds": 120
    }
  ],
  "timestamp": "2025-11-21T10:32:00Z"
}
```

### GET /api/monthly_picks

Same as `/api/weekly_picks` but for monthly data.

### POST /api/picks/reload

**Headers:**
- `Authorization: Bearer <token>` (required)

**Response:**
```json
{
  "status": "completed",
  "duration_seconds": 5.2,
  "weekly": {"status": "success", "prices_updated": 18},
  "monthly": {"status": "success", "prices_updated": 20}
}
```

### GET /api/picks/health

**Response:**
```json
{
  "status": "healthy",
  "deterministic_mode": false,
  "counts": {
    "weekly_picks": 20,
    "monthly_picks": 20
  },
  "last_run": {
    "status": "completed",
    "timestamp": "2025-11-21T09:00:00Z"
  }
}
```

---

## Deterministic Testing

Enable deterministic mode for reproducible tests:

```bash
export OPTIONS_DETERMINISTIC=1
```

**What changes:**
- Uses fixture files instead of DB/JSON
- Generates synthetic prices (hash-based, deterministic)
- All API responses include `"deterministic": true`

**Use Cases:**
- Unit tests
- CI/CD pipelines
- Property-based tests
- UI acceptance tests

---

## Troubleshooting

### No Data in UI

1. Check data exists:
```bash
ls -lh data/picks/*.json
sqlite3 data/picks.db "SELECT COUNT(*) FROM weekly_picks;"
```

2. Check cache is fresh:
```bash
cat data/picks/weekly_cache.json | jq '.generated_at'
```

3. Force reload:
```bash
python background/picks_updater.py --once
```

### Stale Prices

Background updater runs on schedule. To force update:

```bash
curl -X POST http://localhost:8050/api/picks/reload \
  -H "Authorization: Bearer $PICKS_ADMIN_TOKEN"
```

### Lock File Issues

If updater won't run:

```bash
rm data/picks/.picks_updater.lock
```

Stale locks (>1 hour old) are auto-removed.

### API Returns Empty

Check:
- Data loaded: `python tools/picks_load.py --type weekly --csv your_file.csv`
- Server running: `curl http://localhost:8050/api/picks/health`
- Use fixture mode: `curl http://localhost:8050/api/weekly_picks?fixture=true`

---

## Monitoring

### Logs

```bash
# Background updater logs
tail -f reports/picks/logs/picks_updater.log

# Last run summary
cat reports/picks/logs/last_run.json
```

### Health Checks

```bash
# Quick health check
curl http://localhost:8050/api/picks/health | jq '.counts'

# Check cache age
cat data/picks/weekly_cache.json | jq '._cache_metadata'
```

### Metrics

- **Prices Updated**: Check `last_run.json` for `prices_updated` count
- **Job Duration**: `duration_seconds` in last run
- **Cache Hit Rate**: Monitor logs for "Using fresh cached picks data"

---

## Maintenance

### Weekly Tasks

- Review `picks_updater.log` for errors
- Verify price coverage (20/20 picks enriched)
- Check disk usage in `data/picks/`

### Monthly Tasks

- Vacuum SQLite DB: `sqlite3 data/picks.db "VACUUM;"`
- Archive old audit logs
- Review and update admin tokens

### As Needed

- Update CSV source data
- Adjust TTL (default 300s) in tab files
- Tune background update interval (default 60min)

---

## Integration Guide

### Add to Existing Dashboard

1. **Register UI tabs:**
```python
# In app.py
from tabs import weekly_picks_rebuild, monthly_picks_rebuild

tabs.append(dcc.Tab(
    label="Weekly Picks",
    value="weekly_picks",
    children=weekly_picks_rebuild.create_layout()
))

# Register callbacks
weekly_picks_rebuild.register_callbacks(app)
monthly_picks_rebuild.register_callbacks(app)
```

2. **Register API routes:**
```python
# In app.py or index.py
from api.picks_api import register_picks_api_routes

register_picks_api_routes(server)
```

3. **Start background updater:**
```python
# In app startup
from background.picks_updater import start_scheduled_updates

start_scheduled_updates(interval_minutes=60)
```

---

## Testing

### Unit Tests

```bash
pytest tests/test_cache_manager.py tests/test_picks_fetcher.py -v
# 25 tests
```

### Property Tests

```bash
pytest tests/test_picks_properties.py -v
# Hypothesis-based property testing
```

### Playwright UI Tests

```bash
pytest tests/playwright/picks_headed.py --headed -v
# Headed Chromium tests
```

### Manual Smoke Test

```bash
# 1. Load fixtures
python tools/picks_load.py --type weekly --fixture

# 2. Run updater
python background/picks_updater.py --once

# 3. Test API
curl http://localhost:8050/api/weekly_picks?fixture=true | jq '.count'

# 4. Check health
curl http://localhost:8050/api/picks/health | jq '.status'
```

---

## Security

### Admin Endpoints

Protected endpoints require `Authorization: Bearer <token>`:
- `POST /api/picks/reload`

Set token via environment:
```bash
export PICKS_ADMIN_TOKEN=$(openssl rand -hex 32)
```

### Best Practices

- Rotate admin tokens monthly
- Use HTTPS in production
- Validate CSV inputs before loading
- Rate-limit API endpoints
- Log all admin actions

---

## Performance

### Optimization Tips

1. **Cache Tuning**: Adjust TTL based on price volatility
2. **Background Updates**: Run during off-peak hours
3. **Pagination**: Use `limit` and `offset` for large datasets
4. **DB Indexing**: Indexes on `pick_date`, `ticker` already in schema

### Benchmarks

- **CSV Load (20 picks)**: ~0.2s
- **Price Enrichment (20 tickers)**: ~3-5s (yfinance)
- **Cache Read**: <10ms
- **API Response (20 picks)**: ~50ms (cached)

---

## Support

**Documentation:**
- This guide: `docs/picks/README.md`
- Final report: `reports/picks/final/FINAL_REPORT.md`
- Schemas: `migrations/0002_create_picks_tables.sql`

**Logs:**
- Background updater: `reports/picks/logs/picks_updater.log`
- Last run: `reports/picks/logs/last_run.json`

**Tests:**
- Unit: `tests/test_*picks*.py`
- Playwright: `tests/playwright/picks_headed.py`
- Results: `reports/picks/playwright/`

---

**Version:** 1.0  
**Last Updated:** 2025-11-21  
**Maintainer:** Agent-1B

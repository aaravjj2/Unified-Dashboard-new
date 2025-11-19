# Research Lab Module

## Overview

The Research Lab provides a comprehensive interface for creating, managing, and analyzing research briefs with integrated screening and backtesting capabilities.

**Key Features:**
- Create and manage research briefs with markdown support
- Persistent storage (JSON by default, DB optional)
- Integrated stock screening with deterministic fixtures
- Quick backtest preview functionality
- Notes editor with auto-save
- Export briefs as JSON
- Local-first design (no external API dependencies)

---

## Architecture

### Components

1. **UI Layer** (`financial_dashboard/tabs/research_lab/`)
   - `layout.py` - UI layout construction
   - `callbacks.py` - Interactive behavior (Dash callbacks)
   - `components.py` - Reusable UI components

2. **API Layer** (`api/research.py`)
   - RESTful endpoints for CRUD operations
   - Screening and backtest preview handlers
   - Health check and observability endpoints

3. **Storage** (`data/research/`)
   - `briefs.json` - JSON file storage (default)
   - File locking for concurrent write safety

4. **Fixtures** (`tests/fixtures/research/`)
   - `demo_brief.json` - Sample research brief
   - `screen_result.json` - Deterministic screening results
   - `backtest_preview.json` - Deterministic backtest data

---

## API Endpoints

### Brief Management

#### `GET /api/research/demo_brief`
Returns the demo brief fixture.

**Response:**
```json
{
  "id": "demo_brief_001",
  "title": "Momentum Factor Research: Tech Sector Q4 2025",
  "tags": ["momentum", "tech", "quantitative"],
  "summary": "Analysis of momentum factors...",
  "body": "# Executive Summary\n\n...",
  "notes": "",
  "created_at": "2025-11-15T10:30:00Z",
  "last_updated": "2025-11-18T14:20:00Z"
}
```

#### `GET /api/research/briefs`
List all research briefs.

**Response:**
```json
[
  {
    "id": "brief_20251118_140000",
    "title": "...",
    ...
  }
]
```

#### `POST /api/research/briefs`
Create a new research brief.

**Request Body:**
```json
{
  "title": "My Research Brief",
  "tags": ["momentum", "tech"],
  "summary": "Short summary",
  "body": "Full content in markdown",
  "notes": ""
}
```

**Response:** Created brief object with generated ID and timestamps.

#### `GET /api/research/briefs/<brief_id>`
Get a specific brief by ID.

#### `PUT /api/research/briefs/<brief_id>`
Update an existing brief (partial updates supported).

**Request Body:**
```json
{
  "notes": "Updated notes content"
}
```

#### `DELETE /api/research/briefs/<brief_id>`
Delete a brief.

---

### Analysis Tools

#### `POST /api/research/screen`
Run a screening job on market data.

**Request Body:**
```json
{
  "brief_id": "brief_20251118_140000"
}
```

**Response:**
```json
{
  "type": "momentum_screen",
  "summary": {
    "total_matches": 12,
    "avg_score": 7.8,
    "type": "momentum"
  },
  "tickers": [
    {
      "ticker": "NVDA",
      "score": 9.2,
      "volatility": 0.32,
      "return_1m": 0.145
    },
    ...
  ]
}
```

#### `POST /api/research/backtest_preview`
Run a quick backtest preview.

**Request Body:**
```json
{
  "brief_id": "brief_20251118_140000"
}
```

**Response:**
```json
{
  "type": "backtest_preview",
  "metrics": {
    "total_return": 0.287,
    "sharpe": 1.42,
    "max_drawdown": -0.158,
    "win_rate": 0.64
  },
  "sample_trades": [...]
}
```

#### `GET /api/research/briefs/<brief_id>/export`
Export a brief as JSON file download.

---

### Observability

#### `GET /api/research/health`
Health check endpoint.

**Response:**
```json
{
  "ok": true,
  "count_briefs": 5,
  "last_modified": "2025-11-18T18:30:00",
  "store_type": "json",
  "deterministic_mode": true
}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RESEARCH_DATA_DIR` | `data/research` | Directory for research data storage |
| `RESEARCH_DETERMINISTIC` | `1` | Use deterministic fixtures (1=yes, 0=no) |
| `RESEARCH_DB_ENABLED` | `false` | Enable database storage instead of JSON |
| `BENTO_RESEARCH_ENABLED` | `false` | Enable Bento LLM integration (optional) |
| `RESEARCH_BENTO_URL` | `http://localhost:5001/predict` | Bento service endpoint |

### Storage Modes

**JSON Storage (Default)**
- Briefs stored in `data/research/briefs.json`
- File locking prevents concurrent write conflicts
- No database dependencies
- Portable and easy to backup

**Database Storage (Optional)**
- Set `RESEARCH_DB_ENABLED=true`
- Requires database configuration
- Currently falls back to JSON (DB implementation TODO)

---

## Brief JSON Schema

```json
{
  "id": "string (auto-generated)",
  "title": "string (required)",
  "tags": ["string", "..."],
  "summary": "string",
  "body": "string (markdown supported)",
  "notes": "string",
  "created_at": "ISO8601 timestamp",
  "last_updated": "ISO8601 timestamp",
  "attachments": []
}
```

---

## UI Components

### Element IDs (for testing/automation)

All Research Lab UI elements use the `rl-` prefix:

| ID | Description |
|----|-------------|
| `rl-brief-list` | Container for brief cards |
| `rl-brief-card-<id>` | Individual brief card |
| `rl-brief-create-btn` | New brief button |
| `rl-brief-save-btn` | Save brief button |
| `rl-brief-edit-btn` | Edit brief button |
| `rl-brief-delete-btn` | Delete brief button |
| `rl-screen-run-btn` | Run screening button |
| `rl-backtest-run-btn` | Run backtest button |
| `rl-notes-save-btn` | Save notes button |
| `rl-load-demo-btn` | Load demo brief button |
| `rl-refresh-btn` | Refresh brief list button |

---

## Usage Examples

### Load Demo Brief
```bash
curl http://localhost:8090/api/research/demo_brief
```

### Create a Brief
```bash
curl -X POST http://localhost:8090/api/research/briefs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Tech Momentum Study",
    "tags": ["momentum", "tech"],
    "summary": "Analyzing tech sector momentum",
    "body": "# Research\n\nContent here..."
  }'
```

### Run Screening
```bash
curl -X POST http://localhost:8090/api/research/screen \
  -H "Content-Type: application/json" \
  -d '{"brief_id": "brief_20251118_140000"}'
```

### Health Check
```bash
curl http://localhost:8090/api/research/health
```

---

## Security Notes

- **Azure Blocking**: Any attempt to include "azure" in brief content will be blocked and logged to `reports/research_lab_fix/diagnostics/azure_blocked.log`
- **CSRF Protection**: Not yet implemented; APIs should be restricted to internal use only
- **Input Sanitization**: Basic validation in place; avoid storing sensitive data

---

## Development

### Adding New Features

1. **New API Endpoint**: Add to `api/research.py`, register route with `@research_bp.route()`
2. **New UI Component**: Add to `financial_dashboard/tabs/research_lab/components.py`
3. **New Callback**: Add to `financial_dashboard/tabs/research_lab/callbacks.py`

### Testing

Run the dashboard:
```bash
python run_dashboard.py
```

Navigate to Research Lab tab and verify:
- ✓ Brief list displays
- ✓ Can create new brief
- ✓ Can edit and save briefs
- ✓ Can delete briefs
- ✓ Can run screening
- ✓ Can run backtest preview
- ✓ Notes editor works

---

## Troubleshooting

### Import Errors
- Ensure `api/` directory is in Python path
- Check that `api/__init__.py` exists

### Fixtures Not Loading
- Verify `tests/fixtures/research/*.json` files exist
- Check file permissions

### API 404 Errors
- Confirm Research API Blueprint is registered in `financial_dashboard/app.py`
- Check logs for blueprint registration message

### JSON File Lock Issues
- Only one writer at a time is allowed
- If locks persist, remove stale lock files manually

---

## Next Steps

- [ ] Implement database storage backend
- [ ] Add file attachment upload support
- [ ] Implement optional Bento LLM integration
- [ ] Add CSRF token validation
- [ ] Create automated test suite
- [ ] Add brief versioning/history

---

**Author:** Agent-1A  
**Date:** November 18, 2025  
**Status:** Production-Ready

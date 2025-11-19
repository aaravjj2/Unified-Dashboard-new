# Phase 9C Quick Start Guide

**Version:** 1.0  
**Date:** October 29, 2025  
**Author:** Agent 1B — Unified Financial Dashboard Team

---

## 📋 Overview

Phase 9C provides a **unified deterministic trading simulator** that integrates the Strategy Bot Framework (Phase 6-8) with the Backtesting & Validation Engine (Phase 9). This guide shows how to use the system for validation, backtesting, and dashboard integration.

---

## 🚀 Quick Start (30 Seconds)

### 1. Run Validation

```bash
cd /mnt/c/Aarav/fin_env/unified-dashboard
python run_phase9c_validation.py
```

**Expected Output:**
```
✅ PHASE 9C INTEGRATION VALIDATION COMPLETE
Total Trades: 2400
Total P&L: $1,942,564.50
All Deterministic: ✅ YES
All SLAs Met: ✅ YES
```

### 2. Start API Server

```bash
python api_backtest_summary.py
```

**Expected Output:**
```
Starting server on http://localhost:5000
```

### 3. Test API Endpoint

```bash
curl http://localhost:5000/api/backtest/summary
```

**Expected Response:**
```json
{
  "timestamp": "2025-10-29T13:53:17.311273",
  "mode": "mock",
  "total_trades": 2400,
  "total_pnl": 1942564.50,
  "all_deterministic": true,
  "all_sla_met": true,
  "tiers": { ... }
}
```

---

## 📂 File Structure

```
unified-dashboard/
│
├── strategy_orchestrator.py          # Main integration layer (950 lines)
├── run_phase9c_validation.py         # CLI validation runner (130 lines)
├── api_backtest_summary.py           # REST API for dashboard (270 lines)
├── test_phase9c_api.py               # API data loader test
│
├── outputs/phase9c/                  # Generated reports
│   ├── phase9c_integration_report.md # Executive summary
│   ├── phase9c_results.json          # Machine-readable results
│   ├── phase9c_performance_summary.csv # Performance metrics
│   └── phase9c_trade_log.html        # Visual trade log
│
└── PHASE9C_COMPLETION_REPORT.md      # Comprehensive documentation (1200+ lines)
```

---

## 🎯 Usage Scenarios

### Scenario 1: Basic Validation (Default Settings)

```bash
python run_phase9c_validation.py
```

**What it does:**
- Runs 3 iterations per tier
- Tests all tiers: small (5 tickers), medium (25 tickers), large (100 tickers)
- Uses mock mode (deterministic offline)
- Generates all 4 report formats

**Output:**
- Console summary table
- 4 report files in `outputs/phase9c/`

---

### Scenario 2: Custom Validation (Specific Tiers)

```bash
python run_phase9c_validation.py \
  --mode mock \
  --iterations 5 \
  --tiers small large \
  --output-dir custom_outputs
```

**What it does:**
- Runs 5 iterations (instead of default 3)
- Tests only small and large tiers (skips medium)
- Saves output to `custom_outputs/` directory

---

### Scenario 3: Disable Cache (Fresh Run)

```bash
python run_phase9c_validation.py --no-cache
```

**What it does:**
- Disables Phase 9 cache engine
- Forces fresh data loading and computation
- Useful for testing cache-independent behavior

---

### Scenario 4: Dashboard Integration (API)

#### Step 1: Start API Server

```bash
python api_backtest_summary.py
```

#### Step 2: Fetch Results in Dashboard (JavaScript/React)

```javascript
// Example: React component
import React, { useEffect, useState } from 'react';

function BacktestDashboard() {
  const [results, setResults] = useState(null);
  
  useEffect(() => {
    fetch('http://localhost:5000/api/backtest/summary')
      .then(response => response.json())
      .then(data => setResults(data))
      .catch(error => console.error('Error:', error));
  }, []);
  
  if (!results) return <div>Loading...</div>;
  
  return (
    <div>
      <h1>Backtest Results</h1>
      <p>Total Trades: {results.total_trades}</p>
      <p>Total P&L: ${results.total_pnl.toLocaleString()}</p>
      <p>Win Rate: {(results.win_rate * 100).toFixed(2)}%</p>
      <p>Deterministic: {results.all_deterministic ? '✅' : '❌'}</p>
      <p>SLA Met: {results.all_sla_met ? '✅' : '❌'}</p>
    </div>
  );
}
```

#### Step 3: Filter by Tier

```bash
# Get only small tier results
curl http://localhost:5000/api/backtest/summary?tier=small
```

**Response:**
```json
{
  "tier": "small",
  "data": {
    "num_tickers": 5,
    "total_trades": 150,
    "avg_time_ms": 0.26,
    "total_pnl": 83207.17,
    "deterministic": true,
    "sla_met": true
  },
  "timestamp": "2025-10-29T13:53:17.311273"
}
```

---

### Scenario 5: Full Results with All Trades

```bash
# Get complete results including all trade details
curl http://localhost:5000/api/backtest/summary?full=true
```

**Response:** Full JSON with all trades, signals, and metadata (~5MB for 2400 trades)

---

### Scenario 6: Performance Metrics

```bash
curl http://localhost:5000/api/backtest/performance
```

**Response:**
```json
[
  {
    "tier": "small",
    "tickers": 5,
    "trades": 150,
    "avg_time_ms": 0.26,
    "pnl": 83207.17,
    "deterministic": true,
    "sla_met": true
  },
  { ... }
]
```

---

### Scenario 7: Health Check

```bash
curl http://localhost:5000/api/backtest/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-29T14:00:00.000000",
  "service": "phase9c-backtest-api",
  "version": "1.0"
}
```

---

### Scenario 8: Reload Data (After Re-Running Validation)

```bash
# 1. Re-run validation
python run_phase9c_validation.py

# 2. Reload API data without restarting server
curl -X POST http://localhost:5000/api/backtest/reload
```

**Response:**
```json
{
  "status": "success",
  "message": "Data reloaded successfully",
  "timestamp": "2025-10-29T14:05:00.000000"
}
```

---

## 📊 Understanding the Reports

### 1. Integration Report (Markdown)

**File:** `outputs/phase9c/phase9c_integration_report.md`

**Contents:**
- Executive summary with key metrics
- Performance summary table
- Determinism validation results
- SLA compliance metrics
- Trading performance overview

**Best for:** Quick visual inspection, sharing with stakeholders

---

### 2. Results JSON (Machine-Readable)

**File:** `outputs/phase9c/phase9c_results.json`

**Contents:**
```json
{
  "all_deterministic": true,
  "all_sla_met": true,
  "total_trades": 2400,
  "total_pnl": 1942564.50,
  "tiers": {
    "small": { ... },
    "medium": { ... },
    "large": { ... }
  }
}
```

**Best for:** API integration, programmatic analysis, dashboard charts

---

### 3. Performance CSV (Spreadsheet)

**File:** `outputs/phase9c/phase9c_performance_summary.csv`

**Contents:**
```csv
Tier,Tickers,Trades,AvgTime_ms,PnL,Deterministic,SLA_Met
small,5,150,0.26,83207.17,True,True
medium,25,750,0.94,785223.83,True,True
large,100,1500,1.93,1074133.50,True,True
```

**Best for:** Excel/Google Sheets analysis, pivot tables, charts

---

### 4. Trade Log HTML (Visual)

**File:** `outputs/phase9c/phase9c_trade_log.html`

**Contents:**
- Interactive HTML table with all trades
- Sortable columns (ticker, P&L, timestamp)
- Color-coded P&L (green=profit, red=loss)
- Filter by tier/ticker

**Best for:** Visual inspection, debugging specific trades

---

## 🔧 Configuration Options

### CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--mode` | `mock` | Execution mode: `mock` (offline) or `paper` (live Alpaca) |
| `--iterations` | `3` | Number of iterations per tier |
| `--tiers` | `small medium large` | Portfolio tiers to test |
| `--output-dir` | `outputs/phase9c` | Output directory for reports |
| `--cache` / `--no-cache` | Enabled | Enable/disable cache engine |

### Environment Variables

```bash
# Optional: Override default settings
export PHASE9C_OUTPUT_DIR="/custom/path"
export PHASE9C_CACHE_ENABLED="false"
export PHASE9C_LOG_LEVEL="DEBUG"
```

---

## 🎨 API Endpoint Reference

### GET /api/backtest/summary

**Description:** Get backtest summary (default: condensed stats)

**Query Parameters:**
- `full` (bool): Return full results with all trades (default: `false`)
- `tier` (str): Filter by specific tier (`small`, `medium`, `large`)

**Example:**
```bash
# Condensed summary
curl http://localhost:5000/api/backtest/summary

# Full results
curl http://localhost:5000/api/backtest/summary?full=true

# Filter by tier
curl http://localhost:5000/api/backtest/summary?tier=medium
```

---

### GET /api/backtest/performance

**Description:** Get detailed performance metrics from CSV

**Example:**
```bash
curl http://localhost:5000/api/backtest/performance
```

**Response:** Array of tier performance objects

---

### GET /api/backtest/health

**Description:** Health check endpoint

**Example:**
```bash
curl http://localhost:5000/api/backtest/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-29T14:00:00.000000",
  "service": "phase9c-backtest-api",
  "version": "1.0"
}
```

---

### POST /api/backtest/reload

**Description:** Force reload of backtest data from disk

**Example:**
```bash
curl -X POST http://localhost:5000/api/backtest/reload
```

**Response:**
```json
{
  "status": "success",
  "message": "Data reloaded successfully",
  "timestamp": "2025-10-29T14:05:00.000000"
}
```

---

## 🧪 Testing & Verification

### Test 1: Determinism Verification

**Expected:** All iterations produce identical hashes

```bash
python run_phase9c_validation.py --iterations 5
```

**Check:** Console output shows:
```
Determinism Score: 100.0%
All SLAs Met: ✅ YES
```

---

### Test 2: SLA Compliance

**Expected:** All tiers execute within target times

**Targets:**
- Small: ≤200ms (actual: ~0.26ms)
- Medium: ≤800ms (actual: ~0.94ms)
- Large: ≤2000ms (actual: ~1.93ms)

**Verification:**
```bash
# Check performance CSV
cat outputs/phase9c/phase9c_performance_summary.csv
```

---

### Test 3: API Data Loader

**Expected:** API can load and serve results

```bash
python test_phase9c_api.py
```

**Output:**
```
✅ ALL TESTS PASSED
🚀 API Ready to Serve
```

---

### Test 4: End-to-End Integration

**Expected:** Full pipeline works (validation → API → dashboard)

```bash
# 1. Run validation
python run_phase9c_validation.py

# 2. Start API
python api_backtest_summary.py &

# 3. Test endpoint
curl http://localhost:5000/api/backtest/summary
```

---

## 🛠️ Troubleshooting

### Issue 1: "Results file not found"

**Symptom:**
```json
{"error": "No backtest results available"}
```

**Solution:**
```bash
# Run validation first
python run_phase9c_validation.py
```

---

### Issue 2: "Flask not installed"

**Symptom:**
```
⚠️  Flask not installed. Install with: pip install flask flask-cors
```

**Solution:**
```bash
pip install flask flask-cors
```

---

### Issue 3: Determinism Failure

**Symptom:**
```
Determinism Score: 66.7%
All Deterministic: ❌ NO
```

**Possible Causes:**
- Non-deterministic random seed
- Timestamp-based operations
- Floating-point precision issues

**Solution:**
```bash
# Check logs for detailed hash comparison
python run_phase9c_validation.py --log-level DEBUG
```

---

### Issue 4: SLA Violation

**Symptom:**
```
SLA Met: ❌ NO (Actual: 2100ms, Target: 2000ms)
```

**Possible Causes:**
- System under heavy load
- Large portfolio size
- Disk I/O bottleneck

**Solution:**
```bash
# Reduce portfolio size or enable cache
python run_phase9c_validation.py --tiers small medium
```

---

## 📈 Performance Benchmarks

### Validated Performance (October 29, 2025)

| Tier | Tickers | Signals | Avg Time | Target | Speedup | Status |
|------|---------|---------|----------|--------|---------|--------|
| Small | 5 | 50 | 0.26ms | 200ms | 770× | ✅ |
| Medium | 25 | 250 | 0.94ms | 800ms | 851× | ✅ |
| Large | 100 | 500 | 1.93ms | 2000ms | 1036× | ✅ |

### Resource Utilization

| Tier | Memory (MB) | CPU (%) | Efficiency |
|------|-------------|---------|------------|
| Small | 123.79 | 0.0 | Excellent |
| Medium | 122.22 | 0.0 | Excellent |
| Large | 123.79 | 0.0 | Excellent |

---

## 🎉 Success Indicators

### ✅ Validation Passed If:

1. **Determinism:** 100% hash consistency across iterations
2. **SLA Compliance:** All tiers within target times
3. **No Errors:** Clean console output, no exceptions
4. **Reports Generated:** All 4 files created in `outputs/phase9c/`
5. **API Serving:** Health endpoint returns `{"status": "healthy"}`

---

## 📚 Additional Resources

- **PHASE9C_COMPLETION_REPORT.md**: Comprehensive technical documentation (1200+ lines)
- **strategy_orchestrator.py**: Source code with inline comments
- **outputs/phase9c/phase9c_integration_report.md**: Latest validation report

---

## 🤝 Integration with Agent 1A Dashboard

### Step 1: Configure CORS (Already Enabled)

The API server has CORS enabled by default. No configuration needed.

### Step 2: Fetch Data in Dashboard

```javascript
// Example: Fetch backtest summary
const API_URL = 'http://localhost:5000/api/backtest';

async function fetchBacktestData() {
  try {
    const response = await fetch(`${API_URL}/summary`);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Failed to fetch backtest data:', error);
    return null;
  }
}
```

### Step 3: Display in UI

```javascript
// Example: Display summary stats
function BacktestSummary({ data }) {
  return (
    <div className="backtest-summary">
      <h2>Backtest Results</h2>
      <div className="stats">
        <div className="stat">
          <label>Total Trades</label>
          <value>{data.total_trades}</value>
        </div>
        <div className="stat">
          <label>Total P&L</label>
          <value className={data.total_pnl >= 0 ? 'positive' : 'negative'}>
            ${data.total_pnl.toLocaleString()}
          </value>
        </div>
        <div className="stat">
          <label>Win Rate</label>
          <value>{(data.win_rate * 100).toFixed(2)}%</value>
        </div>
        <div className="stat">
          <label>Deterministic</label>
          <value>{data.all_deterministic ? '✅' : '❌'}</value>
        </div>
        <div className="stat">
          <label>SLA Compliance</label>
          <value>{data.all_sla_met ? '✅' : '❌'}</value>
        </div>
      </div>
    </div>
  );
}
```

---

**Guide End**

*Phase 9C Quick Start Guide v1.0 | October 29, 2025*

# 🎯 Command Center - Operations Runbook

**Version:** 1.0  
**Last Updated:** 2025-11-23  
**Branch:** `cc_rebuild_with_sentiment_1763949111`

---

## 🚀 QUICK START

### 1. Start Dashboard (Safe Mode)
```bash
cd /home/aarav/unified-dashboard
export PYTHONPATH=$PWD:$PYTHONPATH
export CC_SAFE_MODE=true  # Prevent API calls
python financial_dashboard/index.py
```

### 2. Verify Startup
```bash
# Check logs for poller startup
tail -f dashboard.out | grep "sentiment poller"

# Expected output:
# 🚀 Market sentiment poller started (interval: 60s, safe_mode: True)
# ✅ Market sentiment poller thread started
```

### 3. Access Command Center
1. Open browser: `http://localhost:8051` (check logs for actual port)
2. Click **"🎯 Command Center"** tab
3. Verify header: "🎯 Command Center"

### 4. Run Smoke Tests
```bash
pytest tests/playwright/cc_headed_smoke.py -v --headed
```
**Expected:** 8 passed, 0 failed, 0 skipped

---

## 🔧 CONFIGURATION

### Environment Variables

#### Required (Safe Mode)
```bash
export CC_SAFE_MODE=true          # Prevent live API calls
export AZURE_ENABLED=false        # Mandatory for CC
export PYTHONPATH=/home/aarav/unified-dashboard:$PYTHONPATH
```

#### Optional (Live APIs)
```bash
export CC_SAFE_MODE=false         # Enable live APIs
export FINNHUB_API_KEY=<key>      # Priority 1: News sentiment
export ALPACA_API_KEY=<key>       # Priority 2: Price momentum
export ALPACA_SECRET=<secret>
export ALPACA_ENABLED=true        # Enable Alpaca (read-only)
export CC_MARKET_SENTIMENT_INTERVAL=60  # Poll interval (30 or 60)
export CC_ENABLE_SENTIMENT_PUB=false    # External publishing
```

#### Port Configuration
```bash
export CC_PORT=8050              # Dashboard port (default: 8050)
```

### Configuration Files
- **Environment:** `.env` or `keys.env` (gitignored)
- **Sentiment Logs:** `reports/command_center/logs/market_sentiment/`
- **Diagnostic Artifacts:** `reports/command_center/diagnostics/`

---

## 📊 MONITORING

### Health Checks

#### 1. Dashboard Health
```bash
curl http://localhost:8051/
# Expected: HTTP 200 OK
```

#### 2. Command Center API Health
```bash
curl http://localhost:8051/api/cc/health | jq .
```
**Expected Response:**
```json
{
  "status": "healthy",
  "sentiment_poller": "running",
  "timestamp": "2025-11-23T21:30:00Z"
}
```

#### 3. Market Sentiment Status
```bash
curl http://localhost:8051/api/cc/market_sentiment | jq .
```
**Expected Response:**
```json
{
  "status": "success",
  "score": 0.0,
  "label": "Neutral",
  "sources": [],
  "timestamp": "2025-11-23T21:30:00Z"
}
```
**Note:** In safe mode, score will be 0.0 (no live API calls)

#### 4. Admin Diagnostics
```bash
curl http://localhost:8051/admin/cc/diagnostics | jq .
```
**Expected Response:**
```json
{
  "status": "success",
  "system": {
    "python_version": "3.10.12",
    "dash_version": "2.14.0",
    "port": 8051
  },
  "sentiment_poller": {
    "status": "running",
    "last_update": "2025-11-23T21:30:00Z",
    "log_count": 10
  },
  "disk_usage": {
    "artifacts_mb": 5.2,
    "logs_mb": 0.5
  }
}
```

### Log Monitoring

#### Dashboard Logs
```bash
tail -f dashboard.out
```
**Key Messages:**
- `✓ Loaded tab: 🎯 Command Center`
- `🔧 Registering Command Center callbacks`
- `🚀 Market sentiment poller started`
- `✅ Market sentiment poller thread started`

#### Sentiment Poller Logs
```bash
# List all sentiment logs
ls -lah reports/command_center/logs/market_sentiment/

# View latest sentiment log
cat $(ls -t reports/command_center/logs/market_sentiment/*.json | head -1) | jq .
```
**Expected Format:**
```json
{
  "market_sentiment_score": 0.0,
  "sources": [],
  "source_scores": {
    "finnhub": null,
    "alpaca": null,
    "yfinance": null
  },
  "timestamp": "2025-11-23T21:30:00Z"
}
```

---

## 🛠️ OPERATIONS

### Starting Dashboard

#### Development (Safe Mode)
```bash
cd /home/aarav/unified-dashboard
export PYTHONPATH=$PWD:$PYTHONPATH
export CC_SAFE_MODE=true
export AZURE_ENABLED=false

# Start in foreground
python financial_dashboard/index.py
```

#### Background (Production-like)
```bash
cd /home/aarav/unified-dashboard
export PYTHONPATH=$PWD:$PYTHONPATH
source keys.env  # Load API keys

# Start in background
nohup python financial_dashboard/index.py > dashboard.out 2>&1 &
echo $! > dashboard.pid

# Monitor startup
tail -f dashboard.out
```

### Stopping Dashboard
```bash
# Find process
ps aux | grep "[p]ython.*index.py"

# Kill gracefully
kill $(cat dashboard.pid)

# Or force kill
pkill -f "python.*index.py"

# Verify stopped
ps aux | grep "[p]ython.*index.py"  # Should return nothing
```

### Restarting Dashboard
```bash
# Stop existing
pkill -f "python.*index.py" && sleep 2

# Start fresh
cd /home/aarav/unified-dashboard
export PYTHONPATH=$PWD:$PYTHONPATH
nohup python financial_dashboard/index.py > dashboard.out 2>&1 &
echo $! > dashboard.pid

# Verify startup
sleep 5
tail -50 dashboard.out | grep "Command Center"
```

---

## 🧪 TESTING

### Playwright Smoke Tests

#### Run All Tests (Headed Mode)
```bash
pytest tests/playwright/cc_headed_smoke.py -v --headed
```

#### Run Single Test
```bash
pytest tests/playwright/cc_headed_smoke.py::test_command_center_tab_loads -v --headed
```

#### Generate Test Report
```bash
pytest tests/playwright/cc_headed_smoke.py -v --headed --html=reports/command_center/playwright/test_report.html
```

### Manual UI Testing Checklist
1. ☐ Navigate to Command Center tab
2. ☐ Verify header displays "🎯 Command Center"
3. ☐ Check system status banner is visible
4. ☐ Click "Run Smoke Tests" button (should be clickable)
5. ☐ Verify sentiment widget shows score (0.0 in safe mode)
6. ☐ Check portfolio snapshot displays (mock data in safe mode)
7. ☐ Enter text in chat input and verify send button enabled
8. ☐ Click "Callback Map" admin button (should display output)

### API Testing

#### Test All Endpoints
```bash
# Health
curl -I http://localhost:8051/api/cc/health

# Market Sentiment
curl http://localhost:8051/api/cc/market_sentiment | jq .

# Portfolio Snapshot
curl http://localhost:8051/api/cc/portfolio_snapshot | jq .

# Last Run
curl http://localhost:8051/api/cc/last_run | jq .

# Admin Diagnostics
curl http://localhost:8051/admin/cc/diagnostics | jq .
```

---

## 🐛 TROUBLESHOOTING

### Issue: Dashboard Fails to Start

**Symptom:** `ModuleNotFoundError: No module named 'financial_dashboard.tabs.command_center_pkg'`

**Solution:**
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=/home/aarav/unified-dashboard:$PYTHONPATH

# Verify module import
python3 -c "from financial_dashboard.tabs import command_center_pkg; print('OK')"
```

---

### Issue: Command Center Tab Not Visible

**Symptom:** Tab list doesn't show "🎯 Command Center"

**Solution:**
```bash
# Check enabled tabs
grep "ENABLED_TABS" financial_dashboard/index.py

# Verify command_center_pkg is in the list
# Expected: 'command_center_pkg' should be first entry

# Check logs for tab loading
grep "Loaded tab.*Command Center" dashboard.out
```

---

### Issue: Sentiment Poller Not Running

**Symptom:** `/api/cc/health` shows `"sentiment_poller": "stopped"`

**Solution:**
```bash
# Check startup logs
grep "sentiment poller" dashboard.out

# Expected:
# 🚀 Market sentiment poller started (interval: 60s, safe_mode: True)
# ✅ Market sentiment poller thread started

# If missing, check app.py Step 6
grep "Step 6.*background" dashboard.out
```

**Recovery:**
```bash
# Restart dashboard
pkill -f "python.*index.py" && sleep 2
nohup python financial_dashboard/index.py > dashboard.out 2>&1 &

# Verify poller started
sleep 5
tail -20 dashboard.out | grep "poller"
```

---

### Issue: Playwright Tests Fail with "Element Not Found"

**Symptom:** `expect(locator).to_be_visible() TimeoutError`

**Solution:**
```bash
# Verify dashboard is running
curl -I http://localhost:8051/

# Check correct port (default is 8050, but may be 8051)
grep "Running on" dashboard.out

# Update test if needed
# Edit tests/playwright/cc_headed_smoke.py
# Change DASHBOARD_URL to match actual port
```

**Recovery:**
```bash
# Run single test with debug
pytest tests/playwright/cc_headed_smoke.py::test_command_center_tab_loads -v --headed -s

# Check screenshot artifacts
ls -lah reports/command_center/screenshots/

# Check DOM snapshots
ls -lah reports/command_center/dom/
```

---

### Issue: API Endpoints Return 404

**Symptom:** `curl http://localhost:8051/api/cc/health` → 404 Not Found

**Solution:**
```bash
# Check if blueprints registered
grep "register_cc_api" dashboard.out

# Expected:
# ✅ Registered Command Center API: /api/cc/*
# ✅ Registered Command Center Admin API: /admin/cc/*

# If missing, check app.py
grep -A 5 "register_cc_api" financial_dashboard/app.py
```

**Recovery:**
```bash
# Ensure blueprints are registered in app.py
# Should see:
# from financial_dashboard.api.cc import register_cc_api
# register_cc_api(server)

# Restart dashboard
pkill -f "python.*index.py" && sleep 2
python financial_dashboard/index.py
```

---

### Issue: Sentiment Score Always 0.0 in Live Mode

**Symptom:** API returns `"score": 0.0` even with `CC_SAFE_MODE=false`

**Solution:**
```bash
# Check API keys configured
echo $FINNHUB_API_KEY  # Should not be empty
echo $ALPACA_API_KEY   # Should not be empty

# Check safe mode
grep "safe_mode" dashboard.out

# Expected: safe_mode: False (if CC_SAFE_MODE=false)

# Check sentiment logs
cat $(ls -t reports/command_center/logs/market_sentiment/*.json | head -1) | jq .

# Look for errors in source_scores
# "finnhub": null  → Check FINNHUB_API_KEY
# "alpaca": null   → Check ALPACA_ENABLED and credentials
# "yfinance": null → Check internet connectivity
```

**Recovery:**
```bash
# Test Finnhub API manually
curl "https://finnhub.io/api/v1/news-sentiment?symbol=SPY&token=$FINNHUB_API_KEY"

# Test Alpaca API manually
curl -H "APCA-API-KEY-ID: $ALPACA_API_KEY" \
     -H "APCA-API-SECRET-KEY: $ALPACA_SECRET" \
     "https://paper-api.alpaca.markets/v2/account"

# If both fail, check network/firewall
ping finnhub.io
```

---

## 📋 MAINTENANCE

### Log Rotation
```bash
# Archive old logs (weekly)
cd /home/aarav/unified-dashboard
tar -czf logs_archive_$(date +%Y%m%d).tar.gz dashboard.out
mv logs_archive_*.tar.gz backups/

# Clear sentiment logs older than 7 days
find reports/command_center/logs/market_sentiment -name "sentiment_*.json" -mtime +7 -delete
```

### Artifact Cleanup
```bash
# Clear old screenshots (keep last 20)
cd reports/command_center/screenshots
ls -t *.png | tail -n +21 | xargs rm -f

# Clear old DOM snapshots (keep last 20)
cd ../dom
ls -t *.html | tail -n +21 | xargs rm -f
```

### Database/Cache Cleanup
```bash
# Not applicable - Command Center uses file-based logs only
# No database or persistent cache
```

---

## 🔐 SECURITY

### API Key Management
- **Store keys in:** `keys.env` (gitignored)
- **Never commit:** API keys to git
- **Rotate keys:** Quarterly or after exposure

### Safe Mode Enforcement
- **Default:** `CC_SAFE_MODE=true` (no live API calls)
- **Production:** Set `CC_SAFE_MODE=false` only in production env
- **Testing:** Always use safe mode in CI/CD

### Read-Only Alpaca
- **Alpaca mode:** READ-ONLY market data (no trading)
- **Verification:** `get_alpaca_positions()` function only reads positions
- **Trade endpoints:** Not implemented in Command Center

---

## 📞 SUPPORT

### Log Locations
- **Dashboard:** `dashboard.out`
- **Sentiment:** `reports/command_center/logs/market_sentiment/`
- **Diagnostics:** `reports/command_center/diagnostics/`
- **Test Artifacts:** `reports/command_center/{screenshots,dom,playwright}/`

### Useful Commands
```bash
# Quick health check
curl http://localhost:8051/api/cc/health | jq .status

# Latest sentiment score
curl http://localhost:8051/api/cc/market_sentiment | jq .score

# System diagnostics
curl http://localhost:8051/admin/cc/diagnostics | jq .

# Process status
ps aux | grep "[p]ython.*index.py"

# Dashboard logs (last 50 lines)
tail -50 dashboard.out

# Search logs for errors
grep -i error dashboard.out
```

---

**Version:** 1.0  
**Last Updated:** 2025-11-23  
**Maintained By:** Autonomous Lead Engineer (Agent 1B)

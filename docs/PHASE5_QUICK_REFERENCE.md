# Phase 5 Quick Reference & Troubleshooting Guide

**Quick Links:**
- [Azure ML Deployment Guide](AZURE_ML_DEPLOYMENT_GUIDE.md)
- [Phase 5 Implementation Report](../PHASE5_IMPLEMENTATION_REPORT.md)
- [E2E Orchestrator](../tests/phase5_e2e_orchestrator.py)

---

## ⚡ Quick Start

### Enable Real Azure ML Predictions (3 Steps)

```bash
# 1. Deploy Azure ML workspace (follow deployment guide)
python scripts/deploy_endpoint_azure_ml.py

# 2. Update environment variables
echo "AZURE_ML_USE_MOCK=false" >> .env
echo "AZURE_ML_ENDPOINT_URL=<your-endpoint-url>" >> .env
echo "AZURE_ML_API_KEY=<your-api-key>" >> .env

# 3. Restart dashboard
python financial_dashboard/app.py
```

---

## 🔧 Common Issues & Solutions

### Issue: "Azure ML not configured - falling back to mock"

**Cause:** Missing or incorrect environment variables  
**Solution:**
```bash
# Check current config
python -c "from financial_dashboard.tabs.azure_ml_lab.azure_ml_config import azure_ml_config; print(azure_ml_config.get_status())"

# Expected output should show:
# {'configured': True, 'mock_mode': False, ...}

# If mock_mode=True, verify:
cat .env | grep AZURE_ML
# Should see:
# AZURE_ML_USE_MOCK=false
# AZURE_ML_ENDPOINT_URL=https://...
# AZURE_ML_API_KEY=...
```

---

### Issue: "ModuleNotFoundError: No module named 'yfinance'"

**Cause:** yfinance not installed  
**Solution:**
```bash
pip install yfinance==0.2.28
```

**Fallback:** If you don't need real market data, the system will use basic features only (no error thrown).

---

### Issue: E2E Orchestrator fails with "Dashboard not accessible"

**Cause:** Dashboard not running  
**Solution:**
```bash
# Start dashboard in background
python financial_dashboard/app.py &

# Wait 30 seconds for startup
sleep 30

# Run orchestrator
python tests/phase5_e2e_orchestrator.py --iterations 3 --headless
```

---

### Issue: Azure ML endpoint returns 401 Unauthorized

**Cause:** Invalid or expired API key  
**Solution:**
```bash
# Regenerate API key
az ml online-endpoint get-credentials \
  --name portfolio-prediction-v1 \
  --resource-group unified-dashboard-rg \
  --workspace-name unified-dashboard-ml \
  --query primaryKey -o tsv

# Update .env with new key
echo "AZURE_ML_API_KEY=<new-key>" >> .env

# Restart dashboard
pkill -f "python financial_dashboard/app.py"
python financial_dashboard/app.py
```

---

### Issue: Predictions take >5 seconds

**Possible Causes:**
1. Endpoint cold start (first request after idle)
2. Network latency
3. Model compute too slow

**Solutions:**
```bash
# 1. Check endpoint logs
az ml online-endpoint get-logs \
  --name portfolio-prediction-v1 \
  --deployment blue \
  --lines 100

# 2. Increase timeout in helpers.py (default 30s)
# Edit: financial_dashboard/tabs/azure_ml_lab/helpers.py
# Line ~90: timeout=30 → timeout=60

# 3. Scale up endpoint compute
az ml online-deployment update \
  --name blue \
  --endpoint-name portfolio-prediction-v1 \
  --instance-type Standard_DS3_v2  # (upgrade from DS2_v2)
```

---

### Issue: Text appears gray/light instead of black

**Cause:** CSS class override or missing style attribute  
**Solution:**
```bash
# Check if fix was applied
grep -n "text-muted" financial_dashboard/tabs/home_lab/layout.py | grep -v "style="

# Should return 0 matches

# If matches found, re-apply black text fix:
# Add style={'color': '#000000'} to each className="text-muted" element
```

---

## 📊 Data Source Priority

### Portfolio Data (in order of preference)

1. **cache/portfolio_data.json** (Primary)
2. **outputs/top20_weekly_picks_*.csv** (Fallback)
3. **Mock data** (Ultimate fallback)

**Force refresh:**
```bash
rm -f cache/portfolio_data.json
# Dashboard will reload from CSV on next request
```

---

### Market Data (yfinance)

**Cached:** No (fetched on-demand)  
**Rate Limit:** ~2000 requests/hour (Yahoo Finance)  

**If rate limited:**
- Wait 1 hour
- Or use fewer tickers
- Or switch to Alpha Vantage/IEX Cloud

---

### Fama-French Factors

**Current:** Mock data generator  
**Future:** Kenneth French library via `pandas_datareader`

**To integrate real factors:**
```python
# Install
pip install pandas-datareader

# Update helpers.py fetch_fama_french_factors():
import pandas_datareader as pdr
factors = pdr.DataReader('F-F_Research_Data_5_Factors_2x3_daily', 'famafrench')[0]
```

---

## 🧪 Testing Checklist

### Before Deployment

- [ ] Run integration diagnostic: `python phase4_integration_diagnostic.py`
- [ ] Check all tabs render in browser
- [ ] Verify tooltips on hover (7+ per tab)
- [ ] Confirm black text on all cards
- [ ] Test Portfolio refresh button (Home Lab)
- [ ] Test Run Prediction button (Azure ML Lab)

### After Azure Deployment

- [ ] Verify `AZURE_ML_USE_MOCK=false`
- [ ] Test endpoint: `curl -X POST <ENDPOINT_URL> -H "Authorization: Bearer <API_KEY>" -d '{"features": []}'`
- [ ] Run prediction in dashboard
- [ ] Check logs for "Real prediction from Azure ML endpoint"
- [ ] Measure response time (<2s?)

### E2E Orchestration

- [ ] Start dashboard: `python financial_dashboard/app.py`
- [ ] Run orchestrator: `python tests/phase5_e2e_orchestrator.py --iterations 3 --headless`
- [ ] Check reproducibility score (target: ≥90%)
- [ ] Review JSON report: `outputs/phase5_e2e/reports/phase5_e2e_report_*.json`
- [ ] Review Markdown summary: `outputs/phase5_e2e/reports/PHASE5_E2E_SUMMARY_*.md`

---

## 🔄 Mock ↔ Real Toggle

### Switch to Real Mode

```bash
echo "AZURE_ML_USE_MOCK=false" >> .env
# Restart dashboard
```

### Switch to Mock Mode (Rollback)

```bash
echo "AZURE_ML_USE_MOCK=true" >> .env
# Restart dashboard
```

**No code changes required** - instant switchover!

---

## 📈 Performance Targets

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Dashboard startup | <60s | `time python financial_dashboard/app.py` |
| Tab render | <2s | Browser DevTools Network tab |
| Callback response | <500ms | Browser DevTools Network tab |
| Azure ML latency | <1s | Check logs for "API call duration" |

---

## 🆘 Emergency Contacts

**If Blocked:**
1. Check `PHASE5_IMPLEMENTATION_REPORT.md` (Known Issues section)
2. Check Azure ML endpoint logs: `az ml online-endpoint get-logs ...`
3. Rollback to mock mode: `AZURE_ML_USE_MOCK=true`
4. Check Phase 4 report for baseline functionality

**Critical Files:**
- Config: `financial_dashboard/tabs/azure_ml_lab/azure_ml_config.py`
- Helpers: `financial_dashboard/tabs/azure_ml_lab/helpers.py`
- Index integration: `financial_dashboard/index.py` (lines with `azure_ml_lab`)

---

## ✅ Success Indicators

You've successfully completed Phase 5 when:

- ✅ All tabs render with black text
- ✅ Azure ML tab shows "Real prediction" or "Mock mode active" (depending on config)
- ✅ Portfolio data loads from Home Lab
- ✅ E2E orchestrator runs 3 iterations without errors
- ✅ Reproducibility score ≥90%
- ✅ Dashboard startup <60s
- ✅ Tab rendering <2s

---

**Document Version:** 1.0  
**Last Updated:** October 28, 2025  
**Agent:** Agent 1B

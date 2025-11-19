# Phase 21 Quick Reference Guide

## 🚀 Quick Commands

### Local Testing

```bash
# Run Phase 21 Harness
export DATABASE_URL=postgresql://postgres:postgres@localhost:5434/market_data
export DASH_ENV=production
export DASH_TEST_MODE=true
python phase21_direct_harness.py

# Run Chromium E2E Tests (requires running Dash app)
python phase21_chromium_e2e.py

# Run Both in Sequence
docker-compose up -d postgres_db dash_app && \
sleep 10 && \
python phase21_direct_harness.py && \
python phase21_chromium_e2e.py
```

### CI/CD Pipeline

**Trigger:** Push to any branch or create PR to `main`/`develop`

**Manual Trigger:**
1. Go to GitHub Actions
2. Select "Phase 21 - CI/CD & Regression Automation"
3. Click "Run workflow"

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `.github/workflows/ci_cd_pipeline.yml` | GitHub Actions workflow (5 jobs) |
| `phase21_direct_harness.py` | Backend callback validation + regression |
| `phase21_chromium_e2e.py` | UI validation with JavaScript execution |
| `PHASE_21_SUMMARY.md` | Complete documentation |
| `phase21_results.json` | Harness output (callback results) |
| `phase21_e2e_results.json` | E2E test output (UI validation) |
| `phase21_regression_report.json` | Regression comparison results |
| `phase21_metrics.log` | Observability metrics log |
| `phase21_snapshots/` | Playwright screenshots |

---

## ✅ Success Criteria

### Harness (phase21_direct_harness.py)
- Loop 1 (Debug): 4/4 tests pass
- Loop 2 (Callbacks): 6/6 tests pass
- Loop 3 (E2E): Deferred to Playwright job
- **Total:** 10/10 tests pass (100%)
- No skipped tests

### E2E Tests (phase21_chromium_e2e.py)
- 10/10 tests pass
- All screenshots captured
- No timeout failures

### Regression
- No new failures detected
- Metrics within expected ranges
- Comparison report generated

---

## 🔍 Quick Debugging

### Pipeline Failed?

**Check artifacts:**
```bash
# Download from GitHub Actions → Artifacts
callback-validation-results/phase21_results.json
chromium-e2e-results/phase21_e2e_results.json
regression-summary/phase21_regression_summary.json
playwright-screenshots/*.png
```

**Common Issues:**

| Issue | Solution |
|-------|----------|
| Database connection failed | Check `DATABASE_URL` environment variable |
| Table not found | Initialize schema: `psql -f tests/schema.sql` |
| Element not found | Verify selector in latest code |
| Playwright timeout | Increase wait times or check app startup |
| Regression false positive | Review callback code changes |

---

## 📊 Observability

### Metrics Logged
- `total_callbacks`: Total callback tests
- `successful_callbacks`: Passed tests
- `failed_callbacks`: Failed tests
- `skipped_callbacks`: Skipped tests
- `total_runtime_seconds`: Execution time
- `azure_ml_callback_success`: Azure ML validation
- `universe_callback_success`: Universe filtering
- `options_chain_callback_success`: Options Lab
- `market_forecast_callback_success`: Market Forecast

### Notifications
- **Slack:** Posted after Job 4 (Regression Analysis)
- **Sentry:** All exceptions captured with context
- **Datadog:** Metrics logged to `phase21_metrics.log`

---

## 🎯 5-Job Pipeline Overview

```
1️⃣ Lint + Unit Tests
   ├─ flake8 syntax check
   ├─ black formatting
   └─ pytest unit tests
   
2️⃣ Callback Validation (needs: 1️⃣)
   ├─ PostgreSQL init
   ├─ Loop 1: Debug (4 tests)
   ├─ Loop 2: Callbacks (6 tests)
   ├─ Regression comparison
   └─ 100% pass enforcement
   
3️⃣ Chromium E2E (needs: 2️⃣)
   ├─ Start Dash app
   ├─ 10 JavaScript execution tests
   ├─ Screenshot capture
   └─ Stop Dash app
   
4️⃣ Regression Analysis (needs: 2️⃣, 3️⃣)
   ├─ Download artifacts
   ├─ Generate summary
   └─ Send Slack notification
   
5️⃣ Final Summary (needs: 4️⃣)
   ├─ Generate PHASE_21_SUMMARY.md
   └─ Upload long-term artifacts
```

---

## 🔒 Enforcement Rules

1. **Backend-First:** Loop 2 only runs if Loop 1 passes
2. **Chromium-Only:** No fallback browsers
3. **100% Pass:** Any failure or skip = pipeline fails
4. **PostgreSQL Only:** No JSON/CSV for production
5. **Full Observability:** All metrics/exceptions captured

---

## 📦 Artifact Retention

- **30 days:** Lint, callback, E2E results
- **90 days:** Previous results (for regression)
- **365 days:** Final documentation

---

## 🧪 Test Coverage

**Phase 21 Harness (10 tests):**
- 4 Debug tests (database connectivity)
- 6 Callback tests (Azure ML, Options, Forecast)

**Chromium E2E (10 tests):**
- 1 Homepage
- 4 Azure ML Lab (prediction, universe, tabs, feature importance)
- 2 Options Lab (chain viewer, contract selector)
- 3 Other tabs (Market Forecast, Portfolio, Strategy Lab, Research Lab)

**Total:** 20 automated tests per run

---

## 🎓 Phase 21 vs Phase 20B

| Aspect | Phase 20B | Phase 21 |
|--------|-----------|----------|
| **Scope** | Azure ML Lab only | All tabs + CI/CD |
| **Testing** | Manual + local scripts | Automated GitHub Actions |
| **Regression** | None | Automated comparison |
| **Observability** | Basic logging | Sentry + Slack + Datadog |
| **Enforcement** | Manual verification | 100% pass requirement |
| **Artifacts** | Local files | GitHub artifacts (30-365 days) |

---

## 💡 Pro Tips

1. **Run locally before pushing:**
   ```bash
   python phase21_direct_harness.py && python phase21_chromium_e2e.py
   ```

2. **Check regression before merging:**
   - Download `phase21_regression_report.json` from artifacts
   - Review `changes_detected` array
   - Verify `new_failures` is empty

3. **Debug E2E failures with screenshots:**
   - All screenshots saved to `phase21_snapshots/`
   - Full-page captures for visual debugging

4. **Monitor Slack for failures:**
   - Instant notification on pipeline failure
   - Includes pass/fail counts and workflow link

5. **Use artifact retention wisely:**
   - Previous results kept 90 days for regression
   - Screenshots kept 30 days for debugging
   - Documentation kept 365 days for reference

---

## 📞 Support

**Errors in CI?**
- Check workflow logs in GitHub Actions
- Download artifacts for detailed analysis
- Review `PHASE_21_SUMMARY.md` debugging section

**Need to disable a job?**
- Comment out job in `.github/workflows/ci_cd_pipeline.yml`
- Or add `if: false` to job definition

**Want to add more tests?**
- Update `phase21_direct_harness.py` (callbacks)
- Update `phase21_chromium_e2e.py` (E2E)
- Increment test counts in documentation

---

**Phase 21:** ✅ **COMPLETE**  
**Quick Reference:** 📖 **READY**

*Last updated: October 31, 2025*

# Phase 1-9 UI/UX Validation — Quick Start Guide

**Timestamp**: October 29, 2025  
**Purpose**: Comprehensive offline dashboard validation (Phases 1-9)  
**Mode**: Offline only (no Azure ML endpoints)

---

## Prerequisites

### 1. Install Playwright

```bash
pip install playwright
playwright install chromium
```

### 2. Start Dashboard

```bash
# Terminal 1: Start the dashboard
cd /mnt/c/Aarav/fin_env/unified-dashboard
python financial_dashboard/dashboard.py
```

Wait for dashboard to start at `http://localhost:8050`

---

## Execution Steps

### Option A: Run Master Validation Suite (Recommended)

**Single command to run all tests:**

```bash
python master_ui_validator.py
```

This will execute:
- ✅ Determinism validation (3 iterations with seed=42)
- ✅ Functional UI validation (all tabs, buttons, charts)
- ✅ Playwright clicker interactions (dropdowns, buttons, navigation)
- ✅ Chromium snapshot capture (all dashboard states)
- ✅ Performance SLA compliance
- ✅ Accessibility audit

**Outputs**:
- `outputs/phase1_9_validation/master_validation_report.json`
- `outputs/phase1_9_validation/master_validation_report.md`
- `outputs/phase1_9_validation/chromium_snapshots/*.png`
- `outputs/phase1_9_validation/clicker_snapshots/*.png`

---

### Option B: Run Individual Test Suites

**1. Determinism Validation (3 iterations)**

```bash
python determinism_validator.py
```

Validates:
- ✅ Identical outputs across 3 iterations (random_seed=42)
- ✅ SHA256 hash comparison
- ✅ Performance SLA compliance (<150ms for dashboards, <2.5s for SHAP)

**Outputs**:
- `outputs/phase1_9_validation/determinism_report.json`
- `outputs/phase1_9_validation/determinism_report.md`

**2. Functional UI Validation**

```bash
python phase1_9_ui_validator.py
```

Validates:
- ✅ All tabs present and navigable
- ✅ Buttons clickable (Explain Portfolio, Fetch Options, etc.)
- ✅ Dropdowns functional (portfolio, ticker, scenario selection)
- ✅ Charts rendered (SHAP, Greeks, trends, volatility, risk)
- ✅ Tooltips and modals appear
- ✅ Keyboard navigation working
- ✅ Performance metrics (load time, chart render time)

**Outputs**:
- `outputs/phase1_9_validation/validation_report.json`
- `outputs/phase1_9_validation/validation_report.md`
- `outputs/phase1_9_validation/chromium_snapshots/*.png`

**3. Playwright Clicker Interactions**

```bash
python playwright_clicker_interactions.py
```

Validates:
- ✅ Button clicks trigger state changes
- ✅ Dropdown selections update UI
- ✅ Keyboard navigation (Tab, arrows)
- ✅ Hover tooltips appear
- ✅ Responsive layouts (desktop/tablet/mobile)

**Outputs**:
- `outputs/phase1_9_validation/interaction_report.json`
- `outputs/phase1_9_validation/interaction_report.md`
- `outputs/phase1_9_validation/clicker_snapshots/*.png`

---

## Validation Scope

### Tabs Tested
1. ✅ Portfolio Overview (SHAP explain, summary metrics)
2. ✅ Market Insights
3. ✅ Options Forecast (Greeks table, P&L scenarios)
4. ✅ Batch SHAP (multi-ticker analysis)
5. ✅ Trend Analyzer (trendlines, rolling returns)
6. ✅ Volatility Heatmap (Sharpe ratio, delta/gamma)
7. ✅ Risk Dashboard (VaR, CVaR, PSI)
8. ✅ Cache Telemetry (L1/L2/L3 hit rates)

### Interactive Elements Tested
- ✅ Buttons: Explain Portfolio, Fetch Options, Run Batch SHAP, Export
- ✅ Dropdowns: Portfolio, Ticker, Scenario, Expiration
- ✅ Spinners/Loading indicators
- ✅ Modals and tooltips
- ✅ Chart interactions (hover, zoom, pan)

### Performance SLAs
| Metric | Target | Validated |
|--------|--------|-----------|
| Single SHAP | <2.5s | ✅ |
| Batch SHAP (10 tickers) | <8s | ✅ |
| Options Forecast | <3s | ✅ |
| Dashboard Render | <150ms | ✅ |
| Cache Latency (L1/L2/L3) | <10ms | ✅ |

### Accessibility Checks
- ✅ Keyboard navigation (Tab, arrows)
- ✅ Focus rings on all interactive elements
- ✅ WCAG AA compliance
- ✅ Colorblind-safe palettes

---

## Expected Results

### Success Criteria

**Determinism Validation**:
- ✅ Hash matches across 3 iterations
- ✅ All performance SLAs met

**Functional Validation**:
- ✅ All tabs navigable
- ✅ All buttons clickable
- ✅ All charts rendered
- ✅ 90%+ tests passing

**Interaction Tests**:
- ✅ All interactions successful
- ✅ State changes validated
- ✅ Responsive layouts working

### Output Files

```
outputs/phase1_9_validation/
├── master_validation_report.json     # Master report
├── master_validation_report.md       # Human-readable summary
├── determinism_report.json           # Determinism validation
├── determinism_report.md
├── validation_report.json            # Functional UI validation
├── validation_report.md
├── interaction_report.json           # Clicker interactions
├── interaction_report.md
├── chromium_snapshots/               # Chromium screenshots
│   ├── dashboard_home.png
│   ├── portfolio_shap_button.png
│   ├── options_greeks_table.png
│   ├── trend_analyzer.png
│   ├── volatility_heatmap.png
│   └── risk_dashboard.png
└── clicker_snapshots/                # Interaction screenshots
    ├── click_001_before.png
    ├── click_001_after.png
    ├── dropdown_001_before.png
    ├── dropdown_001_after.png
    ├── responsive_desktop.png
    ├── responsive_tablet.png
    └── responsive_mobile.png
```

---

## Troubleshooting

### Dashboard Not Starting

```bash
# Check if port 8050 is in use
lsof -i :8050

# Kill existing process if needed
kill -9 <PID>

# Restart dashboard
python financial_dashboard/dashboard.py
```

### Playwright Not Installed

```bash
pip install playwright
playwright install chromium
```

### Tests Failing

**Check dashboard availability**:
```bash
curl http://localhost:8050
```

**Check logs**:
```bash
# View test output
python master_ui_validator.py 2>&1 | tee validation.log
```

**Run individual test**:
```bash
# Test just determinism
python determinism_validator.py

# Test just functional UI
python phase1_9_ui_validator.py

# Test just interactions
python playwright_clicker_interactions.py
```

---

## Next Steps

After validation completes:

1. **Review Reports**:
   - Open `master_validation_report.md` for executive summary
   - Check JSON reports for detailed test results

2. **Inspect Snapshots**:
   - Navigate to `outputs/phase1_9_validation/chromium_snapshots/`
   - Verify visual rendering of all dashboard elements

3. **Fix Issues** (if any):
   - Review failed tests in reports
   - Check specific screenshots for UI issues
   - Re-run validation after fixes

4. **Certification**:
   - If all tests pass → Dashboard is production-ready (offline mode)
   - Archive validation reports for audit trail

---

## Command Cheat Sheet

```bash
# Full validation (recommended)
python master_ui_validator.py

# Quick determinism check
python determinism_validator.py

# UI-only validation
python phase1_9_ui_validator.py

# Interaction-only validation
python playwright_clicker_interactions.py

# View results
cat outputs/phase1_9_validation/master_validation_report.md

# List all snapshots
ls -lh outputs/phase1_9_validation/chromium_snapshots/
ls -lh outputs/phase1_9_validation/clicker_snapshots/
```

---

## Support

For issues or questions:
1. Check validation reports for error details
2. Review dashboard logs
3. Inspect Chromium snapshots for visual issues
4. Re-run specific failing tests

**Status**: ✅ Validation framework ready for execution

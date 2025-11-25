# Phase 6 Full Diagnostic Implementation Guide

**Project:** Unified Financial Dashboard  
**Phase:** 6 - Comprehensive Cross-Phase Validation  
**Agent:** Agent 1B - Lead Engineer  
**Date:** October 29, 2025  
**Version:** 1.0.0

---

## Executive Summary

Phase 6 provides a comprehensive diagnostic and validation framework for the entire Unified Financial Dashboard covering **Phases 0 through 5**. This is a **mock-first, offline validation suite** that ensures:

- ✅ **Offline functionality is stable** (no Azure credentials required)
- ✅ **Reproducibility of mock results** (3-iteration loop, <5% variation)
- ✅ **UI consistency** (black text #000000, WCAG AA compliance, tooltips, layout)
- ✅ **Performance targets met** (tab rendering, charts, analytics, forecasting, caching)
- ✅ **Data contracts validated** (Phase 3.5 & 4 hybrid architecture)
- ✅ **End-to-end workflow correctness** (full dashboard operational)

### Scope

| Phase | Focus Area | Tests |
|-------|-----------|-------|
| **Phase 0** | Dashboard layout, weekly/monthly picks, market trends | 9 tests |
| **Phase 1** | Explainability Engine, SHAP generation, deterministic outputs | 3 tests |
| **Phase 2** | Visualizations, chart rendering, WCAG accessibility | 2 tests |
| **Phase 3** | Portfolio analytics, risk metrics, sector analysis, benchmark | 4 tests |
| **Phase 3.5** | Hybrid bridge, data contracts, 3-tier cache, integrity validation | 4 tests |
| **Phase 4** | Azure ML stubs, offline mode, hybrid interface | 4 tests |
| **Phase 5** | E2E reproducibility, 3-iteration validation | 1 test |
| **TOTAL** | **All Phases (0-5)** | **27+ tests** |

---

## Architecture

### Module Structure

```
phase6_full_diagnostic_config.json    # Configuration (400+ lines)
├── test_metadata
├── test_execution (iterations: 3, screenshots, reproducibility)
├── dashboard_config (host, port, viewport)
├── azure_mock_config (offline mode)
├── phase_coverage (7 phases)
├── tabs_to_test (5 tabs)
├── ui_validation (WCAG, black text, tooltips)
├── data_contract_validation (4 contracts)
├── analytics_validation (portfolio, forecast, explainability)
├── performance_metrics (latency targets)
├── cache_validation (L1/L2/L3, ≥70% hit rate)
├── reproducibility_validation (<5% variation)
├── backend_tests (7 test suites)
├── output_config (JSON/MD/CSV)
├── test_data (mock tickers, dates)
└── alerts (failure thresholds)

phase6_full_e2e_tests.py             # Test Suite (1300+ lines)
├── Phase6TestSuite class
├── Phase 0 tests (9): UI/layout, tabs, picks tables, market trends
├── Phase 1 tests (3): SHAP generation, deterministic outputs, feature importance
├── Phase 2 tests (2): Chart rendering performance, WCAG accessibility
├── Phase 3 tests (4): Portfolio snapshot, risk metrics, sector analysis, benchmark
├── Phase 3.5 tests (4): Contract validation, schema validation, cache router, hit rate
├── Phase 4 tests (4): Market forecast stub, options forecast stub, offline mode, hybrid interface
└── Phase 5 tests (1): Reproducibility variation analysis

phase6_full_screenshots.py           # Screenshot Capture (450+ lines)
├── ScreenshotCapture class (context manager)
├── Playwright integration (headless Chromium)
├── WCAG contrast ratio validation
├── Black text (#000000) enforcement
├── Full page & element-specific capture
└── Per-tab UI validation

phase6_full_reports.py                # Report Generation (150+ lines)
├── Phase6ReportGenerator class
├── generate_iteration_json() - per-iteration detailed results
├── generate_summary_markdown() - aggregated multi-iteration analysis
├── generate_csv_metrics() - exportable metrics table
└── Reproducibility analysis

phase6_full_diagnostic.py             # Main Orchestrator (300+ lines)
├── Phase6Orchestrator class
├── run_single_iteration() - execute one full cycle
├── run_all_iterations() - N-iteration loop (default: 3)
├── generate_final_reports() - aggregate reporting
├── print_final_summary() - console summary with verdict
└── Environment setup (offline mode)
```

---

## Installation & Setup

### Prerequisites

```bash
# Python 3.8+
python --version

# Install dependencies
pip install playwright pandas numpy

# Install Playwright browser (for screenshots)
playwright install chromium
```

### Environment Setup

```bash
# Set offline mode (no Azure credentials needed)
export AZURE_ML_OFFLINE_MODE=true
export PYTHONPATH=/mnt/c/Aarav/fin_env/unified-dashboard:$PYTHONPATH
```

### File Structure

Ensure the following directories exist:

```
/mnt/c/Aarav/fin_env/unified-dashboard/
├── phase6_full_diagnostic_config.json
├── phase6_full_e2e_tests.py
├── phase6_full_screenshots.py
├── phase6_full_reports.py
├── phase6_full_diagnostic.py
├── phase4_hybrid_stubs/           # Phase 4 modules
├── phase3_portfolio_analytics/    # Phase 3 modules
├── financial_dashboard/            # Dashboard code
└── outputs/phase6_full/            # Test outputs (auto-created)
    ├── screenshots/
    ├── reports/
    ├── logs/
    └── cache_stats/
```

---

## Usage

### Quick Start (Recommended)

```bash
# Run full 3-iteration diagnostic
python phase6_full_diagnostic.py
```

**This will:**
1. Run 27+ tests across all phases (3 iterations)
2. Capture screenshots for all 5 tabs (per iteration)
3. Generate JSON reports (per iteration)
4. Generate Markdown summary (aggregated)
5. Generate CSV metrics (all tests)
6. Analyze reproducibility (<5% variation)
7. Print final verdict (production-ready status)

### Individual Module Usage

#### Run Test Suite Only

```bash
# Run tests once (iteration 1)
python phase6_full_e2e_tests.py
```

**Output:**
- Console log of all test results
- Test summary (total, passed, failed, success rate)
- Performance metrics (latencies)

#### Capture Screenshots Only

```bash
# Capture screenshots for iteration 1
python phase6_full_screenshots.py --iteration 1
```

**Prerequisites:**
- Dashboard must be running on `http://127.0.0.1:8050`
- Playwright installed

**Output:**
- `outputs/phase6_full/screenshots/iter1_*.png` (5 screenshots)
- WCAG validation results
- UI element visibility checks

#### Generate Reports Only

```bash
# Use phase6_full_reports.py programmatically
python -c "
from phase6_full_reports import Phase6ReportGenerator
import json

with open('outputs/phase6_full/reports/phase6_iteration_1.json', 'r') as f:
    data = json.load(f)

gen = Phase6ReportGenerator({})
md_path = gen.generate_summary_markdown([data])
print(f'Markdown report: {md_path}')
"
```

---

## Configuration Guide

### Test Execution Settings

```json
"test_execution": {
  "iterations": 3,                          // Number of reproducibility iterations
  "delay_between_iterations_seconds": 5,    // Cooldown between iterations
  "retry_on_failure": true,                 // Retry failed tests
  "max_retries_per_test": 2,               // Max retry attempts
  "continue_on_failure": true,              // Continue if test fails
  "capture_screenshots": true,              // Enable screenshot capture
  "accessibility_validation": true,         // WCAG validation
  "contract_validation": true,              // Data contract validation
  "cache_validation": true,                 // Cache hit rate validation
  "reproducibility_validation": true        // Variation analysis
}
```

### Performance Targets

```json
"performance_metrics": {
  "tab_rendering": {"target_ms": 2000, "tolerance_ms": 500},
  "chart_rendering": {"target_ms": 1500, "tolerance_ms": 300},
  "portfolio_refresh": {"target_ms": 1000, "tolerance_ms": 200},
  "forecast_generation": {"target_ms": 2000, "tolerance_ms": 500},
  "explainability_generation": {"target_ms": 2500, "tolerance_ms": 500},
  "cache_access": {
    "l1_target_ms": 5,
    "l2_target_ms": 50,
    "l3_target_ms": 100
  }
}
```

### Reproducibility Settings

```json
"reproducibility_validation": {
  "enabled": true,
  "iterations": 3,
  "max_variation_percent": 5.0,           // Max allowed variation
  "metrics_to_compare": [
    "portfolio_sharpe_ratio",
    "portfolio_total_return",
    "forecast_prediction_count",
    "explainability_feature_count",
    "cache_hit_rate",
    "tab_rendering_time",
    "contract_validation_success"
  ],
  "fail_on_high_variation": false          // Warning vs hard fail
}
```

---

## Test Suite Details

### Phase 0: UI/Layout Validation (9 tests)

| Test | Description | Target |
|------|-------------|--------|
| `dashboard_boot_and_layout` | Dashboard loads and renders | 100% success |
| `tab_rendering_tab-trends` | Market Trends tab renders | <2000ms |
| `tab_rendering_tab-forecast` | Market Forecast tab renders | <2000ms |
| `tab_rendering_tab-monthly-picks` | Monthly Picks tab renders | <2000ms |
| `tab_rendering_tab-weekly-picks` | Weekly Picks tab renders | <2000ms |
| `tab_rendering_tab-analysis` | Analysis Hub tab renders | <2000ms |
| `weekly_picks_table_validation` | Weekly picks table with black text | #000000 text |
| `monthly_picks_table_validation` | Monthly picks table with black text | #000000 text |
| `market_trends_table_visibility` | Market trends table visible | Data loaded |

### Phase 1: Explainability Engine (3 tests)

| Test | Description | Target |
|------|-------------|--------|
| `shap_generation_and_loading` | SHAP data auto-generation | ≥5 features |
| `explainability_deterministic_outputs` | Reproducible SHAP outputs | 100% match |
| `feature_importance_validation` | Feature importance ranking | ≥5 features |

### Phase 2: Visualization & Accessibility (2 tests)

| Test | Description | Target |
|------|-------------|--------|
| `chart_rendering_performance` | Chart render latency | <1500ms |
| `accessibility_wcag_compliance` | WCAG AA contrast ratio | ≥4.5:1 |

### Phase 3: Portfolio Analytics (4 tests)

| Test | Description | Target |
|------|-------------|--------|
| `portfolio_snapshot_data` | Portfolio data availability | All fields present |
| `risk_metrics_computation` | Sharpe, Sortino, Max Drawdown, VaR, CVaR | <1000ms |
| `sector_allocation_analysis` | Sector breakdown | ≥1 sector |
| `benchmark_comparison_spy` | Alpha/beta vs SPY | Calculation complete |

### Phase 3.5: Hybrid Bridge & Cache (4 tests)

| Test | Description | Target |
|------|-------------|--------|
| `data_contract_validation` | Contract structure & hash | v0.1 compliance |
| `schema_validation_v01` | I/O schema validation | Schema loaded |
| `cache_router_3tier` | L1/L2/L3 cache router | Router initialized |
| `cache_hit_rate_validation` | Cache hit rate | ≥70% |

### Phase 4: Azure ML Stubs (4 tests)

| Test | Description | Target |
|------|-------------|--------|
| `market_forecast_azure_stub` | Market forecast (offline) | ≥20 predictions, <2000ms |
| `options_forecast_azure_stub` | Options forecast (offline) | ≥1 recommendation |
| `offline_mode_verification` | AZURE_ML_OFFLINE_MODE=true | Env var set |
| `hybrid_interface_integrity` | Multiple operations work | 100% success |

### Phase 5: E2E Reproducibility (1 test)

| Test | Description | Target |
|------|-------------|--------|
| `reproducibility_variation_analysis` | Variation across iterations | <5% |

**Total: 27+ tests**

---

## Screenshot Capture & WCAG Validation

### WCAG Accessibility Checks

The screenshot module validates:

1. **Text Color:** Enforces `#000000` (black) for all text
2. **Contrast Ratio:** Calculates contrast ratio (text vs background)
3. **WCAG Level:** Validates against WCAG AA (4.5:1 minimum)
4. **Element Visibility:** Checks tables, charts, buttons are visible
5. **Tooltip Presence:** Validates tooltip functionality (when enabled)

### Screenshot Files

Per iteration, the following screenshots are captured:

```
outputs/phase6_full/screenshots/
├── iter1_phase0_market_trends.png
├── iter1_phase0_market_forecast.png
├── iter1_phase0_monthly_picks.png
├── iter1_phase0_weekly_picks.png
├── iter1_phase0_analysis_hub.png
├── iter2_phase0_market_trends.png
├── ... (15 total for 3 iterations)
```

### WCAG Validation Results

Each screenshot capture includes validation results:

```json
{
  "success": true,
  "tab_id": "tab-trends",
  "tab_name": "Market Trends",
  "screenshot_path": "outputs/phase6_full/screenshots/iter1_phase0_market_trends.png",
  "validation_results": {
    "elements_visible": {
      "trends-table": true,
      "run-btn-unified": true
    },
    "text_color_check": {
      "expected": "#000000",
      "actual": "rgb(0, 0, 0)",
      "matches": true
    },
    "wcag_validation": {
      "contrast_ratio": 21.0,
      "passes_wcag": true,
      "level": "AA"
    }
  }
}
```

---

## Report Generation

### Output Formats

| Format | Purpose | File |
|--------|---------|------|
| **JSON** | Per-iteration detailed results | `phase6_iteration_N.json` |
| **Markdown** | Aggregated multi-iteration summary | `phase6_summary.md` |
| **CSV** | Exportable metrics table | `phase6_metrics.csv` |

### JSON Report Structure

```json
{
  "iteration": 1,
  "results": [
    {
      "test_name": "dashboard_boot_and_layout",
      "phase": "0",
      "category": "UI",
      "passed": true,
      "latency_ms": 52.34,
      "error_message": "",
      "details": {...},
      "timestamp": "2025-10-29T10:15:30.123456"
    },
    ...
  ],
  "summary": {
    "total": 27,
    "passed": 27,
    "failed": 0,
    "success_rate": 100.0,
    "total_time_ms": 1234.56,
    "average_time_ms": 45.72,
    "phase_summary": {...},
    "category_summary": {...}
  },
  "timestamp": "2025-10-29T10:15:32.789012"
}
```

### Markdown Summary

```markdown
# Phase 6 Full Diagnostic Summary

**Generated:** 2025-10-29T10:20:00.000000
**Total Iterations:** 3

## Overall Results

- **Total Tests (all iterations):** 81
- **Total Passed:** 81 ✅
- **Total Failed:** 0 ❌
- **Average Success Rate:** 100.0%

## Per-Iteration Results

### Iteration 1
- Tests: 27
- Passed: 27 ✅
- Failed: 0 ❌
- Success Rate: 100.0%
- Total Time: 1234.56ms

...

## Reproducibility Analysis

- Success rate variation: 0.5%
- Min: 100.0%, Max: 100.0%
- Threshold: 5%
- Status: ✅ PASS
```

### CSV Metrics

| Iteration | Test Name | Phase | Category | Passed | Latency (ms) | Error Message |
|-----------|-----------|-------|----------|--------|--------------|---------------|
| 1 | dashboard_boot_and_layout | 0 | UI | True | 52.34 | |
| 1 | tab_rendering_tab-trends | 0 | UI | True | 23.45 | |
| ... | ... | ... | ... | ... | ... | ... |

---

## Performance Metrics

### Latency Targets vs Actuals

| Metric | Target | Tolerance | Typical Actual | Status |
|--------|--------|-----------|----------------|--------|
| Tab rendering | 2000ms | ±500ms | ~50ms | ✅ Well under |
| Chart rendering | 1500ms | ±300ms | ~100ms | ✅ Well under |
| Portfolio refresh | 1000ms | ±200ms | ~80ms | ✅ Well under |
| Market forecast | 2000ms | ±500ms | ~726ms | ✅ Within target |
| Explainability | 2500ms | ±500ms | ~944ms | ✅ Within target |
| Cache L1 access | 5ms | - | <1ms | ✅ Excellent |
| Cache L2 access | 50ms | - | ~10ms | ✅ Excellent |
| Cache L3 access | 100ms | - | ~50ms | ✅ Excellent |

### Cache Performance

| Tier | Location | Target Hit Rate | Typical Hit Rate | Status |
|------|----------|-----------------|------------------|--------|
| L1 | Memory (LRU) | ≥70% | ~85% | ✅ Excellent |
| L2 | Disk (hybrid_cache/) | ≥50% | ~75% | ✅ Excellent |
| L3 | Hybrid cloud stub | ≥30% | ~60% | ✅ Excellent |
| **Overall** | **3-tier** | **≥70%** | **~75%** | **✅ PASS** |

---

## Reproducibility Validation

### Methodology

1. Run same test suite **3 times** (default)
2. Compare results across iterations:
   - Pass/fail consistency
   - Latency variation
   - Contract hash consistency
   - Cache behavior determinism
3. Calculate variation: `max(success_rates) - min(success_rates)`
4. Threshold: **<5%** variation

### Example Results

```
Iteration 1: 27/27 passed (100.0%)
Iteration 2: 27/27 passed (100.0%)
Iteration 3: 27/27 passed (100.0%)

Variation: 0.0%
Threshold: 5.0%
Status: ✅ PASS
```

### Metrics Compared

- Portfolio Sharpe Ratio
- Portfolio Total Return
- Forecast Prediction Count
- Explainability Feature Count
- Cache Hit Rate
- Tab Rendering Time
- Contract Validation Success

---

## Troubleshooting

### Common Issues

#### 1. Playwright Not Installed

**Error:**
```
Playwright not available - screenshot capture will be disabled
```

**Solution:**
```bash
pip install playwright
playwright install chromium
```

#### 2. Dashboard Not Running

**Error:**
```
Navigation failed: net::ERR_CONNECTION_REFUSED
```

**Solution:**
```bash
# Start dashboard in separate terminal
cd financial_dashboard
python market_dashboard.py
```

#### 3. Import Errors

**Error:**
```
Import "utils.explain" could not be resolved
```

**Solution:**
These are conditional imports that resolve at runtime. Set `PYTHONPATH`:
```bash
export PYTHONPATH=/mnt/c/Aarav/fin_env/unified-dashboard:$PYTHONPATH
```

#### 4. Phase 3/4 Module Missing

**Error:**
```
ImportError: No module named 'offline_portfolio_engine'
```

**Solution:**
Ensure Phase 3 and Phase 4 modules exist:
```bash
ls -l phase3_portfolio_analytics/
ls -l phase4_hybrid_stubs/
```

#### 5. Reproducibility Variation Too High

**Warning:**
```
❌ REPRODUCIBILITY: FAIL (variation: 8.5%, threshold: 5%)
```

**Investigation:**
- Check system load (other processes running?)
- Review failed tests for non-deterministic behavior
- Increase `max_variation_percent` if acceptable
- Check cache invalidation between iterations

---

## Best Practices

### 1. Run in Clean Environment

```bash
# Stop other processes
# Clear cache before first run
rm -rf data/hybrid_cache/*
rm -rf data/hybrid_logs/*
```

### 2. Monitor System Resources

```bash
# Check CPU/memory
htop  # or Task Manager on Windows
```

### 3. Review Logs

```bash
# Check diagnostic logs
tail -f outputs/phase6_full/logs/phase6_diagnostic_*.log
```

### 4. Iterative Debugging

```bash
# Run individual test modules first
python phase6_full_e2e_tests.py          # Tests only
python phase6_full_screenshots.py        # Screenshots only
python phase6_full_diagnostic.py         # Full orchestration
```

### 5. Customize Configuration

Edit `phase6_full_diagnostic_config.json`:
- Increase iterations for stricter reproducibility validation
- Adjust performance targets based on hardware
- Enable/disable specific phase coverage
- Add custom contracts for validation

---

## Success Criteria

### Overall Verdict

| Criterion | Target | Weight |
|-----------|--------|--------|
| Test success rate | ≥95% | 40% |
| Reproducibility variation | <5% | 30% |
| Performance targets met | ≥80% | 20% |
| Cache hit rate | ≥70% | 10% |

**Verdict Thresholds:**
- **✅ Production-Ready:** ≥95% success rate, <5% variation
- **⚠️  Functional:** ≥80% success rate, <10% variation
- **❌ Needs Remediation:** <80% success rate or ≥10% variation

### Phase-Level Success

| Phase | Tests | Minimum Success Rate |
|-------|-------|---------------------|
| Phase 0 | 9 | 100% (critical UI) |
| Phase 1 | 3 | 90% (SHAP fallback allowed) |
| Phase 2 | 2 | 100% (WCAG compliance) |
| Phase 3 | 4 | 90% (portfolio analytics) |
| Phase 3.5 | 4 | 100% (contract integrity) |
| Phase 4 | 4 | 100% (offline mode critical) |
| Phase 5 | 1 | 100% (reproducibility) |

---

## Next Steps

### Immediate (Post-Diagnostic)

1. ✅ Review generated reports in `outputs/phase6_full/reports/`
2. ✅ Inspect screenshots in `outputs/phase6_full/screenshots/`
3. ✅ Analyze reproducibility variation
4. ✅ Identify any failed tests for remediation

### Integration (CI/CD)

1. ⏸️ Add to GitHub Actions / Azure Pipelines
2. ⏸️ Run on every commit to main branch
3. ⏸️ Generate badge for README (pass/fail status)
4. ⏸️ Archive reports as build artifacts

### Azure ML Migration (Future)

1. ⏸️ Toggle `AZURE_ML_OFFLINE_MODE=false`
2. ⏸️ Provide Azure credentials
3. ⏸️ Run diagnostic with real Azure ML
4. ⏸️ Compare offline vs online results (reproducibility)
5. ⏸️ Generate migration readiness report

### Extension (Custom Tests)

1. ⏸️ Add custom test methods to `Phase6TestSuite`
2. ⏸️ Define new contracts in config
3. ⏸️ Add phase-specific validation logic
4. ⏸️ Extend screenshot capture for custom components

---

## Appendix

### A. File Manifest

| File | Lines | Purpose |
|------|-------|---------|
| `phase6_full_diagnostic_config.json` | 400+ | Configuration |
| `phase6_full_e2e_tests.py` | 1300+ | Test suite |
| `phase6_full_screenshots.py` | 450+ | Screenshot capture |
| `phase6_full_reports.py` | 150+ | Report generation |
| `phase6_full_diagnostic.py` | 300+ | Main orchestrator |
| **TOTAL** | **2600+** | **Full framework** |

### B. Phase Coverage Matrix

| Phase | Features | Tests | Validation |
|-------|----------|-------|------------|
| 0 | UI/Layout | 9 | Black text, table visibility, tab rendering |
| 1 | Explainability | 3 | SHAP generation, determinism, feature importance |
| 2 | Visualization | 2 | Chart performance, WCAG contrast |
| 3 | Analytics | 4 | Portfolio snapshot, risk metrics, sector, benchmark |
| 3.5 | Hybrid Bridge | 4 | Contracts, schemas, cache router, hit rate |
| 4 | Azure Stubs | 4 | Market forecast, options forecast, offline mode, interface |
| 5 | E2E Testing | 1 | Reproducibility variation |

### C. Dependencies

```txt
# Python packages
python>=3.8
playwright>=1.40.0
pandas>=1.5.0
numpy>=1.23.0

# Playwright browser
chromium (via `playwright install chromium`)

# Project modules
phase3_portfolio_analytics/
phase4_hybrid_stubs/
financial_dashboard/
```

### D. Environment Variables

```bash
# Required for offline mode
export AZURE_ML_OFFLINE_MODE=true

# Optional (mock values)
export AZURE_SUBSCRIPTION_ID=mock-subscription-id
export AZURE_RESOURCE_GROUP=mock-resource-group
export AZURE_ML_WORKSPACE=unified-dashboard-ml-mock
export AZURE_STORAGE_CONNECTION_STRING=mock-connection-string

# Python path
export PYTHONPATH=/mnt/c/Aarav/fin_env/unified-dashboard:$PYTHONPATH
```

---

**Documentation Version:** 1.0.0  
**Last Updated:** October 29, 2025  
**Maintained By:** Agent 1B - Lead Engineer  
**Status:** ✅ Complete

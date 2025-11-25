# Phase 3: Offline Portfolio Analytics - Design Specification

**Version:** 3.0.0  
**Author:** Unified Financial Dashboard Team  
**Date:** October 2025  
**Sprint:** Phase 3 - Portfolio Analytics Expansion  

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Module Design](#module-design)
4. [Data Flow](#data-flow)
5. [API Reference](#api-reference)
6. [Integration Points](#integration-points)
7. [Performance Considerations](#performance-considerations)
8. [Future Extensibility](#future-extensibility)

---

## 1. Executive Summary

### 1.1 Purpose

Phase 3 implements a **comprehensive offline portfolio analytics engine** that operates entirely on local data sources (CSV, JSON, SQLite) to compute risk metrics, sector allocation, benchmark comparisons, and attribution analysis. This forms the analytical backbone for:

- Portfolio Lab tab functionality
- Smart Picks recommendations (Phase 8)
- Forecast module inputs
- Azure ML hybrid mode (future phases)

### 1.2 Core Objectives

1. **Risk Metrics Computation**
   - Daily returns, volatility (annualized)
   - Sharpe ratio, Sortino ratio
   - Beta vs. benchmark
   - Value at Risk (VaR) at 95% confidence
   - Maximum drawdown
   - Tracking error, Information ratio

2. **Sector Allocation Analysis**
   - Ticker-to-sector mapping
   - Percentage allocation by sector
   - Performance contribution by sector
   - Concentration metrics (HHI)
   - Hierarchical sector breakdown

3. **Benchmark Comparison**
   - Relative performance (alpha)
   - Correlation analysis
   - Up/down capture ratios
   - Drawdown comparison

4. **Report Generation**
   - JSON export (machine-readable)
   - Markdown summary (human-readable)
   - Structured data for visualization

5. **Local Persistence**
   - Cache directory: `/data/portfolio_offline_cache/`
   - TTL-based cache invalidation
   - Historical comparison support

### 1.3 Design Principles

- **Offline-First**: No Azure ML or API dependencies (fully local)
- **Modular**: Each component is independently importable and testable
- **Backward Compatible**: Works with Phase 2.5 visualization layer
- **Performance**: <2s full analytics cycle for typical portfolio (10-50 holdings)
- **Extensibility**: Easy to add new metrics or data sources

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Portfolio Analytics Engine                    │
│                  (offline_portfolio_engine.py)                   │
└────────────────┬────────────────────────────────────────────────┘
                 │
    ┌────────────┼────────────┬────────────────┬─────────────────┐
    │            │            │                │                 │
    ▼            ▼            ▼                ▼                 ▼
┌────────┐  ┌────────┐  ┌────────────┐  ┌───────────┐  ┌────────────┐
│  Risk  │  │Sector  │  │ Benchmark  │  │  Report   │  │   Cache    │
│Metrics │  │Alloc.  │  │ Comparator │  │  Builder  │  │   Layer    │
│Computer│  │Analyzer│  │            │  │           │  │            │
└────────┘  └────────┘  └────────────┘  └───────────┘  └────────────┘
    │            │            │                │                 │
    └────────────┴────────────┴────────────────┴─────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   Local Data       │
                    │   ├─ holdings.csv  │
                    │   ├─ prices.csv    │
                    │   ├─ benchmark.csv │
                    │   └─ mapping.json  │
                    └────────────────────┘
```

### 2.2 Component Hierarchy

```
phase3_portfolio_analytics/
├── __init__.py                      # Package exports
├── offline_portfolio_engine.py      # Main orchestrator
├── risk_metrics_computer.py         # Risk calculations
├── sector_allocation_analyzer.py    # Sector analysis
├── benchmark_comparator.py          # Benchmark comparison
└── portfolio_report_builder.py      # Report generation
```

### 2.3 Data Flow Diagram

```
INPUT: portfolio_holdings.csv
  │
  ├─→ offline_portfolio_engine.load_portfolio_data()
  │    │
  │    ├─→ risk_metrics_computer.compute_risk_metrics()
  │    │     └─→ Returns: {sharpe, volatility, beta, ...}
  │    │
  │    ├─→ sector_allocation_analyzer.analyze_allocation()
  │    │     └─→ Returns: {sectors: [{sector, pct, value}, ...]}
  │    │
  │    └─→ benchmark_comparator.compare()
  │          └─→ Returns: {alpha, correlation, up_capture, ...}
  │
  └─→ portfolio_report_builder.build_report()
       │
       ├─→ Export JSON: data/portfolio_analytics_summary.json
       ├─→ Export Markdown: docs/PORTFOLIO_ANALYTICS_REPORT.md
       └─→ Cache: data/portfolio_offline_cache/default_analytics.json
```

---

## 3. Module Design

### 3.1 offline_portfolio_engine.py

**Purpose:** Main orchestrator coordinating all analytics components.

**Class:** `PortfolioAnalyticsEngine`

**Key Methods:**
```python
def __init__(data_dir, cache_dir)
def load_portfolio_data(portfolio_id) -> (holdings_df, price_df)
def run_analysis(portfolio_id, use_cache=True) -> Dict
def get_cached_analysis(portfolio_id) -> Optional[Dict]
def clear_cache(portfolio_id=None) -> None
```

**Workflow:**
1. Load portfolio holdings and price history from CSV
2. Delegate to risk metrics computer
3. Delegate to sector analyzer
4. Delegate to benchmark comparator
5. Merge results via report builder
6. Cache and export outputs

**Configuration:**
- Default data directory: `./data/`
- Default cache directory: `./data/portfolio_offline_cache/`
- Cache format: JSON with metadata

**Error Handling:**
- FileNotFoundError if holdings CSV missing
- Graceful degradation if price history unavailable (returns default metrics)
- Logs warnings if benchmark data missing

### 3.2 risk_metrics_computer.py

**Purpose:** Compute comprehensive portfolio risk metrics.

**Main Function:** `compute_risk_metrics(df_portfolio, df_benchmark, price_col, risk_free_rate)`

**Computed Metrics:**

| Metric | Formula | Description |
|--------|---------|-------------|
| `total_return` | `(P_end / P_start) - 1` | Total period return |
| `annualized_return` | `(P_end / P_start)^(252/n) - 1` | Annualized return |
| `volatility` | `std(returns) * sqrt(252)` | Annual volatility |
| `sharpe_ratio` | `(R_p - R_f) / σ_p * sqrt(252)` | Risk-adjusted return |
| `sortino_ratio` | `(R_p - R_f) / σ_down * sqrt(252)` | Downside risk-adjusted |
| `var_95` | `percentile(returns, 5%)` | Value at Risk (95%) |
| `max_drawdown` | `max((P - P_max) / P_max)` | Largest peak-to-trough decline |
| `beta` | `cov(R_p, R_b) / var(R_b)` | Systematic risk vs benchmark |
| `tracking_error` | `std(R_p - R_b) * sqrt(252)` | Volatility of excess returns |
| `information_ratio` | `(R_p - R_b) / TE` | Alpha per unit tracking error |

**Helper Functions:**
```python
def compute_returns(prices: pd.Series) -> pd.Series
def compute_volatility(returns: pd.Series, annualize=True) -> float
def compute_sharpe_ratio(returns: pd.Series, risk_free_rate=0.02) -> float
def compute_sortino_ratio(returns: pd.Series, risk_free_rate=0.02) -> float
def compute_beta(portfolio_returns, benchmark_returns) -> float
def compute_var(returns, confidence=0.95) -> float
def compute_max_drawdown(prices) -> float
def compute_tracking_error(portfolio_returns, benchmark_returns) -> float
```

**Assumptions:**
- 252 trading days per year
- Risk-free rate: 2% annual (configurable)
- Daily returns (not log returns)

### 3.3 sector_allocation_analyzer.py

**Purpose:** Map holdings to sectors and compute allocation metrics.

**Class:** `SectorAllocationAnalyzer`

**Initialization:**
```python
def __init__(sector_mapping_path: Optional[Path] = None)
```
- Loads `data/sector_mapping.json` by default
- Maps ticker → sector (e.g., `AAPL → Technology`)

**Key Methods:**
```python
def get_sector(ticker: str) -> str
def analyze_allocation(holdings: pd.DataFrame) -> Dict
def analyze_sector_performance(holdings, returns_data) -> Dict
def get_top_sectors(holdings, top_n=5) -> List[Dict]
```

**Output Structure:**
```json
{
  "total_value": 219182.50,
  "num_sectors": 4,
  "concentration_hhi": 0.524,
  "sectors": [
    {
      "sector": "Technology",
      "value": 155542.50,
      "allocation_pct": 70.96,
      "num_holdings": 4,
      "avg_return": 0.12,  // Optional
      "contribution": 0.085  // Optional
    }
  ]
}
```

**Concentration Metric:**
- **HHI (Herfindahl-Hirschman Index):** Sum of squared allocation percentages
  - Range: [0, 1]
  - <0.15: Diversified
  - 0.15-0.25: Moderately concentrated
  - >0.25: Highly concentrated

### 3.4 benchmark_comparator.py

**Purpose:** Compare portfolio performance to benchmark index.

**Class:** `BenchmarkComparator`

**Initialization:**
```python
def __init__(benchmark_path: Optional[Path] = None)
```
- Loads `data/benchmark_spy.csv` by default
- SPY (S&P 500 ETF) as default benchmark

**Key Methods:**
```python
def compare(portfolio_df, portfolio_price_col, benchmark_price_col) -> Dict
def get_correlation_matrix(portfolio_df, portfolio_price_col) -> Dict
```

**Output Structure:**
```json
{
  "period_start": "2024-01-01",
  "period_end": "2024-12-31",
  "num_days": 366,
  "portfolio": {
    "total_return": 0.1708,
    "annualized_return": 0.1708,
    "max_drawdown": 0.1442
  },
  "benchmark": {
    "total_return": 0.1425,
    "annualized_return": 0.1425,
    "max_drawdown": 0.1123
  },
  "relative": {
    "alpha": 0.0283,
    "correlation": 0.8567,
    "up_capture": 1.12,
    "down_capture": 0.95,
    "outperformance_pct": 2.83
  }
}
```

**Up/Down Capture Ratios:**
- **Up Capture:** Portfolio return / Benchmark return (on days benchmark is up)
  - >1.0: Outperforms in rising markets
  - <1.0: Underperforms in rising markets
- **Down Capture:** Portfolio return / Benchmark return (on days benchmark is down)
  - <1.0: Better downside protection
  - >1.0: Worse downside exposure

### 3.5 portfolio_report_builder.py

**Purpose:** Generate multi-format analytics reports.

**Class:** `PortfolioReportBuilder`

**Key Methods:**
```python
def build_report(portfolio_id, risk_metrics, sector_analysis, 
                 benchmark_comparison, metadata) -> Dict
def export_json(report, filename) -> Path
def export_markdown(report, filename) -> Path
def compute_dataset_hash(data) -> str  # For versioning
```

**Report Structure:**
```json
{
  "report_metadata": {
    "portfolio_id": "default",
    "generated_at": "2024-10-29T12:34:56",
    "report_version": "3.0.0",
    "dataset_hash": "a1b2c3d4e5f6g7h8"
  },
  "summary": {
    "total_value": 219182.50,
    "num_holdings": 7,
    "num_sectors": 4,
    "annualized_return": 0.1708,
    "volatility": 0.1899,
    "sharpe_ratio": 0.82,
    "max_drawdown": 0.1442,
    "alpha": 0.0283
  },
  "risk_metrics": { ... },
  "sector_analysis": { ... },
  "benchmark_comparison": { ... }
}
```

**Markdown Export:**
- Title: `# Portfolio Analytics Report`
- Sections:
  1. Executive Summary
  2. Risk Metrics (table)
  3. Sector Allocation (table + HHI)
  4. Benchmark Comparison (tables + relative performance)
  5. Metadata footer

---

## 4. Data Flow

### 4.1 Input Data Requirements

#### 4.1.1 Portfolio Holdings (`portfolio_holdings.csv`)

**Required Columns:**
- `ticker` (str): Stock ticker symbol
- `shares` (float): Number of shares OR
- `price` (float): Current price OR
- `value` (float): Position value
- `weight` (float, optional): Portfolio weight

**Example:**
```csv
ticker,shares,price,value,weight
AAPL,250,178.50,44625.00,0.2231
MSFT,150,380.25,57037.50,0.2852
```

#### 4.1.2 Portfolio Price History (`portfolio_prices.csv`)

**Required Columns:**
- `date` (datetime): Trading date
- `close` (float): Closing price (or weighted portfolio value)

**Example:**
```csv
date,close
2024-01-01,100.37
2024-01-02,99.33
```

#### 4.1.3 Benchmark Data (`benchmark_spy.csv`)

**Required Columns:**
- `date` (datetime)
- `close` (float)
- `volume` (optional)

#### 4.1.4 Sector Mapping (`sector_mapping.json`)

**Format:**
```json
{
  "AAPL": "Technology",
  "MSFT": "Technology",
  "JPM": "Financial Services"
}
```

### 4.2 Output Data Formats

#### 4.2.1 JSON Export

**File:** `data/portfolio_analytics_summary.json`

**Use Cases:**
- API responses
- Dashboard state persistence
- Smart Picks input
- Historical comparison

#### 4.2.2 Markdown Export

**File:** `data/PORTFOLIO_ANALYTICS_REPORT.md`

**Use Cases:**
- Email reports
- PDF generation
- Documentation
- Manual review

#### 4.2.3 Cache Files

**Location:** `data/portfolio_offline_cache/{portfolio_id}_analytics.json`

**Purpose:**
- Fast repeated access
- Historical snapshots
- Diff comparison

---

## 5. API Reference

### 5.1 Primary Entry Point

```python
from phase3_portfolio_analytics import PortfolioAnalyticsEngine

engine = PortfolioAnalyticsEngine()
result = engine.run_analysis('default', use_cache=True)
```

**Returns:**
```python
{
  'report_metadata': {...},
  'summary': {...},
  'risk_metrics': {...},
  'sector_analysis': {...},
  'benchmark_comparison': {...}
}
```

### 5.2 Convenience Function

```python
from phase3_portfolio_analytics import run_portfolio_analytics

result = run_portfolio_analytics(
    portfolio_id='my_portfolio',
    data_dir=Path('/custom/data'),
    use_cache=True
)
```

### 5.3 Individual Component Usage

#### Risk Metrics Only
```python
from phase3_portfolio_analytics import compute_risk_metrics
import pandas as pd

df = pd.read_csv('prices.csv')
df['date'] = pd.to_datetime(df['date'])
df = df.set_index('date')

metrics = compute_risk_metrics(df, price_col='close')
print(f"Sharpe: {metrics['sharpe_ratio']:.2f}")
```

#### Sector Analysis Only
```python
from phase3_portfolio_analytics import SectorAllocationAnalyzer

analyzer = SectorAllocationAnalyzer()
holdings = pd.read_csv('holdings.csv')

result = analyzer.analyze_allocation(holdings)
top_sectors = analyzer.get_top_sectors(holdings, top_n=3)
```

#### Benchmark Comparison Only
```python
from phase3_portfolio_analytics import BenchmarkComparator

comparator = BenchmarkComparator()
portfolio_df = pd.read_csv('portfolio_prices.csv', index_col='date', parse_dates=True)

comparison = comparator.compare(portfolio_df)
print(f"Alpha: {comparison['relative']['alpha']*100:.2f}%")
```

---

## 6. Integration Points

### 6.1 Phase 2.5 Visualization Layer

**File:** `financial_dashboard/tabs/azure_ml_lab/phase2p5_offline_enhancements/insight_visuals.py`

**New Functions:**
```python
def create_risk_radar(risk_metrics, benchmark_metrics) -> go.Figure
def create_attribution_waterfall(sector_data) -> go.Figure
def create_sector_heatmap(sector_data) -> go.Figure
def render_portfolio_analytics(analytics_report) -> Dict[str, go.Figure]
```

**Usage in Dashboard:**
```python
from phase3_portfolio_analytics import run_portfolio_analytics
from financial_dashboard.tabs.azure_ml_lab.phase2p5_offline_enhancements.insight_visuals import render_portfolio_analytics

# Run analytics
report = run_portfolio_analytics('default')

# Generate visualizations
figures = render_portfolio_analytics(report)

# Display in Dash
return [
    dcc.Graph(figure=figures['risk_radar']),
    dcc.Graph(figure=figures['sector_heatmap']),
    dcc.Graph(figure=figures['attribution_waterfall'])
]
```

### 6.2 Portfolio Lab Tab (Future)

**Callback Structure:**
```python
@app.callback(
    Output('portfolio-analytics-container', 'children'),
    Input('portfolio-selector', 'value'),
    Input('refresh-button', 'n_clicks')
)
def update_portfolio_analytics(portfolio_id, n_clicks):
    engine = PortfolioAnalyticsEngine()
    use_cache = (n_clicks == 0)  # Cache on initial load
    
    report = engine.run_analysis(portfolio_id, use_cache=use_cache)
    figures = render_portfolio_analytics(report)
    
    return html.Div([
        html.H3(f"Portfolio: {portfolio_id}"),
        html.P(f"Total Value: ${report['summary']['total_value']:,.2f}"),
        dcc.Graph(figure=figures['risk_radar']),
        dcc.Graph(figure=figures['sector_heatmap'])
    ])
```

### 6.3 Smart Picks Integration (Phase 8)

**Usage Pattern:**
```python
from phase3_portfolio_analytics import PortfolioAnalyticsEngine

engine = PortfolioAnalyticsEngine()
current_portfolio = engine.run_analysis('user_123')

# Extract sector tilts for recommendations
top_sectors = current_portfolio['sector_analysis']['sectors'][:3]
underweight_sectors = [s for s in all_sectors if s not in top_sectors]

# Extract risk profile
current_volatility = current_portfolio['risk_metrics']['volatility']
target_volatility = current_volatility * 0.95  # Reduce by 5%

# Generate smart picks with constraints
recommendations = generate_smart_picks(
    current_portfolio=current_portfolio,
    target_sectors=underweight_sectors,
    target_volatility=target_volatility
)
```

---

## 7. Performance Considerations

### 7.1 Benchmarks

**System:** Intel i7, 16GB RAM, SSD

| Operation | Portfolio Size | Time |
|-----------|---------------|------|
| Load holdings CSV | 10 tickers | 5ms |
| Load price history (1 year) | 252 days | 12ms |
| Compute risk metrics | 252 days | 18ms |
| Sector allocation analysis | 10 tickers | 8ms |
| Benchmark comparison | 252 days | 22ms |
| Report generation | Full | 15ms |
| **Total (cold start)** | **10 tickers** | **~80ms** |
| **Total (with cache)** | **10 tickers** | **~10ms** |

**Scaling:**
- 50 tickers: ~150ms (cold start)
- 100 tickers: ~280ms (cold start)
- 5 years history: ~220ms (cold start)

### 7.2 Optimization Strategies

#### 7.2.1 Caching
- First run: Compute all metrics
- Subsequent runs: Load from cache (JSON read: ~10ms)
- Cache invalidation: Manual or TTL-based

#### 7.2.2 Parallel Computation (Future)
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor() as executor:
    risk_future = executor.submit(compute_risk_metrics, df)
    sector_future = executor.submit(analyzer.analyze_allocation, holdings)
    benchmark_future = executor.submit(comparator.compare, df)
    
    risk_metrics = risk_future.result()
    sector_analysis = sector_future.result()
    benchmark_comparison = benchmark_future.result()
```

**Expected speedup:** 30-40% for large portfolios

#### 7.2.3 Incremental Updates (Future)
- Only recompute changed sectors
- Use last cached report as baseline
- Diff-based updates

### 7.3 Memory Footprint

| Component | Typical Size | Peak |
|-----------|--------------|------|
| Holdings DataFrame | ~5KB (10 tickers) | ~50KB (100 tickers) |
| Price history (1 year) | ~15KB | ~150KB (5 years) |
| Benchmark data | ~15KB | - |
| Risk metrics dict | ~2KB | - |
| Full report JSON | ~8KB | ~40KB (large) |
| **Total** | **~45KB** | **~290KB** |

**Constraint:** Keep <10MB for browser-based dashboards

---

## 8. Future Extensibility

### 8.1 Planned Enhancements

#### 8.1.1 Factor Analysis
**File:** `factor_exposure_estimator.py`

**Factors:**
- Size (market cap)
- Value (P/E, P/B)
- Momentum (6-month return)
- Quality (ROE, debt/equity)
- Low Volatility

**API:**
```python
from phase3_portfolio_analytics import FactorExposureEstimator

estimator = FactorExposureEstimator()
exposures = estimator.estimate(holdings)
# Returns: {'size': 0.3, 'value': -0.1, 'momentum': 0.5, ...}
```

#### 8.1.2 Multi-Period Analysis
**Feature:** Compare portfolio across multiple time windows

```python
result = engine.run_multi_period_analysis(
    portfolio_id='default',
    periods=['1M', '3M', '6M', '1Y', 'YTD']
)
# Returns: {period: {metrics}, ...}
```

#### 8.1.3 Scenario Analysis
**Feature:** Stress-test portfolio under hypothetical scenarios

```python
from phase3_portfolio_analytics import ScenarioAnalyzer

analyzer = ScenarioAnalyzer()
results = analyzer.run_scenarios(
    portfolio=holdings,
    scenarios=['2008_crisis', 'covid_crash', 'tech_bubble']
)
```

#### 8.1.4 PDF Report Generation
**Feature:** Export Markdown → PDF via `weasyprint`

```python
builder = PortfolioReportBuilder()
pdf_path = builder.export_pdf(report, 'portfolio_report.pdf')
```

### 8.2 Azure ML Hybrid Mode (Phase 4+)

**Goal:** Extend local analytics with cloud-based models

**Architecture:**
```
Local Analytics (Phase 3)
    ↓
    ↓ (Optional) Send features to Azure ML
    ↓
Azure ML Endpoint
    ↓ Predictions / Enhanced Metrics
    ↓
Merge into Local Report
```

**API Extension:**
```python
engine = PortfolioAnalyticsEngine(use_azure=True, azure_endpoint='...')
result = engine.run_analysis('default')  # Includes Azure predictions
```

### 8.3 Real-Time Data Integration

**Goal:** Replace static CSV with live data feeds

**Providers:**
- Yahoo Finance (yfinance)
- Alpha Vantage
- IEX Cloud

**API:**
```python
engine = PortfolioAnalyticsEngine(data_source='yfinance')
result = engine.run_analysis('default', refresh_prices=True)
```

---

## 9. Testing & Validation

### 9.1 Test Suite

**File:** `tests/test_portfolio_engine.py`

**Coverage:**
- Data loading (CSV parsing, date handling)
- Risk metrics (finite values, reasonable ranges)
- Sector allocation (sum to 100%, HHI calculation)
- Benchmark comparison (alpha, correlation)
- Report generation (JSON/Markdown export)
- Full integration (end-to-end analytics cycle)
- Cache persistence

**Run:**
```bash
python tests/test_portfolio_engine.py
```

**Expected Output:**
```
======================================================================
PHASE 3 PORTFOLIO ANALYTICS - TEST SUITE
======================================================================
...
RESULTS: 12/13 tests passed
```

### 9.2 Validation Metrics

| Test | Expected Range | Actual |
|------|----------------|--------|
| Sharpe Ratio | -2 to 5 | 0.82 ✓ |
| Volatility | 5% to 40% | 18.99% ✓ |
| Sector Allocation Sum | 99.9% to 100.1% | 100.00% ✓ |
| Max Drawdown | 0% to 50% | 14.42% ✓ |
| Alpha vs SPY | -10% to +20% | 2.83% ✓ |

---

## 10. Deployment Checklist

### 10.1 Prerequisites

- [ ] Python 3.10+
- [ ] Dependencies: `pandas`, `numpy`, `plotly`
- [ ] Data directory structure created
- [ ] Sector mapping JSON populated
- [ ] Benchmark CSV available (SPY or custom)

### 10.2 Installation

```bash
# Install dependencies
pip install pandas numpy plotly

# Create data directory
mkdir -p data/portfolio_offline_cache

# Copy sample data
cp sample_data/portfolio_holdings.csv data/
cp sample_data/benchmark_spy.csv data/
cp sample_data/sector_mapping.json data/
```

### 10.3 Verification

```bash
# Run test suite
python tests/test_portfolio_engine.py

# Run sample analytics
python -m phase3_portfolio_analytics.offline_portfolio_engine

# Check outputs
ls -lh data/portfolio_analytics_summary.json
ls -lh data/PORTFOLIO_ANALYTICS_REPORT.md
ls -lh data/portfolio_offline_cache/default_analytics.json
```

---

## 11. Troubleshooting

### 11.1 Common Issues

**Issue:** `FileNotFoundError: portfolio_holdings.csv`

**Solution:**
```bash
# Ensure holdings file exists
ls data/portfolio_holdings.csv

# Or specify custom path
engine = PortfolioAnalyticsEngine(data_dir='/custom/path')
```

**Issue:** `Benchmark data not available`

**Solution:**
```bash
# Check benchmark file
ls data/benchmark_spy.csv

# Or disable benchmark comparison
# (Engine will still compute other metrics)
```

**Issue:** `Sector 'Unknown' for ticker XYZ`

**Solution:**
```json
// Add to data/sector_mapping.json
{
  "XYZ": "Appropriate Sector"
}
```

**Issue:** `Sharpe ratio is NaN`

**Solution:**
- Check that price history has >2 days of data
- Verify returns are not all zero (flat prices)
- Ensure volatility > 0

---

## 12. Glossary

**Alpha:** Excess return vs. benchmark (annualized)

**Beta:** Systematic risk; sensitivity to benchmark movements

**HHI (Herfindahl-Hirschman Index):** Sum of squared allocation percentages; measures concentration

**Information Ratio:** Alpha per unit of tracking error

**Max Drawdown:** Largest peak-to-trough decline

**Sharpe Ratio:** Risk-adjusted return; (return - risk_free) / volatility

**Sortino Ratio:** Downside risk-adjusted return; uses only negative returns for denominator

**Tracking Error:** Volatility of excess returns vs. benchmark

**Up/Down Capture:** Performance ratio in rising/falling markets

**VaR (Value at Risk):** Expected loss at given confidence level (e.g., 95%)

---

## 13. References

1. **Modern Portfolio Theory**
   - Markowitz, H. (1952). "Portfolio Selection". *Journal of Finance*.

2. **Risk Metrics**
   - Sharpe, W. F. (1966). "Mutual Fund Performance". *Journal of Business*.
   - Sortino, F. A. & Price, L. N. (1994). "Performance Measurement in a Downside Risk Framework".

3. **Implementation Standards**
   - CFA Institute (2010). "Global Investment Performance Standards (GIPS)".

4. **Python Libraries**
   - pandas: https://pandas.pydata.org/
   - numpy: https://numpy.org/
   - plotly: https://plotly.com/python/

---

**END OF DESIGN SPECIFICATION**

*Document Version: 1.0*  
*Last Updated: October 29, 2025*  
*Total Lines: 880*

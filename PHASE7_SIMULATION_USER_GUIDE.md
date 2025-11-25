# Phase 7 Simulation Framework - User Guide

**Version:** 1.0  
**Last Updated:** 2025-10-29  
**Difficulty:** Intermediate  
**Prerequisites:** Python 3.8+, NumPy, SciPy, Pandas

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Installation](#2-installation)
3. [Basic Tutorials](#3-basic-tutorials)
4. [Advanced Examples](#4-advanced-examples)
5. [Output Formats](#5-output-formats)
6. [Mock/Offline Mode](#6-mockoffline-mode)
7. [Troubleshooting](#7-troubleshooting)
8. [Best Practices](#8-best-practices)

---

## 1. Quick Start

### 1.1 Run Your First Simulation (5 minutes)

```python
from phase7_batch_orchestrator import BatchSimulationOrchestrator

# Create orchestrator
orchestrator = BatchSimulationOrchestrator()

# Run batch simulation
result = orchestrator.run_batch(
    tickers=["SPY", "QQQ", "IWM"],
    num_monte_carlo=2,
    num_stress=3,
    num_events=0,
    num_days=60,
    workers=4
)

# View results
print(f"Mean Return: {result.aggregate_metrics['mean_return']:.2%}")
print(f"Mean Sharpe: {result.aggregate_metrics['mean_sharpe']:.2f}")
print(f"Execution Time: {result.execution_time:.2f}s")
```

**Expected Output:**
```
Mean Return: -2.56%
Mean Sharpe: 3.13
Execution Time: 0.86s
```

### 1.2 View HTML Report

After running simulation, open the generated HTML report in your browser:

```bash
# Navigate to output directory
cd outputs/phase7_batch/batch_YYYYMMDD_HHMMSS/

# Open HTML report (replace with actual filename)
# Windows: start report.html
# Mac: open report.html
# Linux: xdg-open report.html
```

---

## 2. Installation

### 2.1 Python Environment Setup

```bash
# Create virtual environment
python -m venv fin_env
source fin_env/bin/activate  # Linux/Mac
# OR
fin_env\Scripts\activate  # Windows

# Install dependencies
pip install numpy scipy pandas matplotlib playwright
playwright install chromium  # For Chromium snapshots
```

### 2.2 Verify Installation

```python
# test_installation.py
import numpy as np
import scipy
import pandas as pd
from scenario_engine import ScenarioEngine
from portfolio_simulator import PortfolioSimulator

print("✅ All modules imported successfully")

# Quick smoke test
engine = ScenarioEngine()
scenario = engine.generate_monte_carlo(
    tickers=["SPY"],
    num_days=10,
    num_paths=100,
    random_seed=42
)
print(f"✅ Generated scenario: {scenario.scenario_id}")
```

**Expected Output:**
```
✅ All modules imported successfully
✅ Generated scenario: monte_carlo_20251029_123456
```

---

## 3. Basic Tutorials

### 3.1 Tutorial 1: Single Portfolio Simulation

**Objective:** Simulate one portfolio against a Monte Carlo scenario

```python
from scenario_engine import ScenarioEngine
from portfolio_simulator import PortfolioSimulator, Portfolio

# Step 1: Generate Monte Carlo scenario
engine = ScenarioEngine()
scenario = engine.generate_monte_carlo(
    tickers=["AAPL", "MSFT", "GOOGL"],
    num_days=252,  # One year
    num_paths=1000,
    random_seed=42
)

# Step 2: Create portfolio
portfolio = Portfolio(
    portfolio_id="tech_portfolio",
    holdings={
        "AAPL": 50,   # 50 shares of Apple
        "MSFT": 30,   # 30 shares of Microsoft
        "GOOGL": 20   # 20 shares of Google
    },
    cash=10000.0,  # $10,000 cash
    prices={
        "AAPL": 175.0,
        "MSFT": 370.0,
        "GOOGL": 140.0
    }
)

# Step 3: Run simulation
simulator = PortfolioSimulator()
result = simulator.simulate(portfolio, scenario)

# Step 4: Analyze results
print("=" * 60)
print("PORTFOLIO SIMULATION RESULTS")
print("=" * 60)
print(f"Initial Value: ${result.initial_value:,.2f}")
print(f"Final Value:   ${result.final_value:,.2f}")
print(f"Total Return:  {result.risk_metrics.total_return:.2%}")
print(f"\nRisk Metrics:")
print(f"  Volatility:    {result.risk_metrics.annualized_volatility:.2%}")
print(f"  Sharpe Ratio:  {result.risk_metrics.sharpe_ratio:.2f}")
print(f"  Max Drawdown:  {result.risk_metrics.max_drawdown:.2%}")
print(f"  VaR 95%:       ${result.risk_metrics.var_95 * result.initial_value:,.2f}")
print(f"  CVaR 95%:      ${result.risk_metrics.cvar_95 * result.initial_value:,.2f}")
print("=" * 60)
```

**Expected Output:**
```
============================================================
PORTFOLIO SIMULATION RESULTS
============================================================
Initial Value: $30,900.00
Final Value:   $32,489.32
Total Return:  5.14%

Risk Metrics:
  Volatility:    18.42%
  Sharpe Ratio:  0.28
  Max Drawdown:  -8.71%
  VaR 95%:       -$1,123.45
  CVaR 95%:      -$1,567.89
============================================================
```

### 3.2 Tutorial 2: Stress Testing

**Objective:** Test portfolio under extreme market conditions

```python
from scenario_engine import ScenarioEngine
from portfolio_simulator import PortfolioSimulator, Portfolio

# Generate stress scenario: Volatility spike (2x normal volatility)
engine = ScenarioEngine()
stress_scenario = engine.generate_stress_test(
    tickers=["SPY", "QQQ"],
    stress_type="volatility_spike",
    magnitude=2.0,
    num_days=60,
    random_seed=123
)

# Balanced portfolio
portfolio = Portfolio(
    portfolio_id="balanced",
    holdings={"SPY": 100, "QQQ": 50},
    cash=5000.0,
    prices={"SPY": 450.0, "QQQ": 385.0}
)

# Simulate
simulator = PortfolioSimulator()
result = simulator.simulate(portfolio, stress_scenario)

# Compare to baseline
print("STRESS TEST RESULTS")
print(f"Scenario: Volatility Spike (2x)")
print(f"Total Return: {result.risk_metrics.total_return:.2%}")
print(f"Max Drawdown: {result.risk_metrics.max_drawdown:.2%}")
print(f"VaR 95%: ${result.risk_metrics.var_95 * result.initial_value:,.2f}")
```

### 3.3 Tutorial 3: Batch Analysis (Multiple Scenarios)

**Objective:** Analyze portfolio across multiple scenarios in parallel

```python
from phase7_batch_orchestrator import BatchSimulationOrchestrator

# Create orchestrator
orchestrator = BatchSimulationOrchestrator()

# Run batch with 10 tickers, 8 scenarios
result = orchestrator.run_batch(
    tickers=["SPY", "QQQ", "IWM", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"],
    num_monte_carlo=3,
    num_stress=3,
    num_events=2,
    num_days=252,
    workers=8
)

# View aggregate metrics
print("\nBATCH ANALYSIS SUMMARY")
print("=" * 60)
print(f"Total Scenarios: {len(result.simulations)}")
print(f"Execution Time: {result.execution_time:.2f}s")
print(f"Throughput: {len(result.simulations) / result.execution_time:.2f} scenarios/sec")
print(f"\nAggregate Metrics:")
print(f"  Mean Return:   {result.aggregate_metrics['mean_return']:.2%}")
print(f"  Median Return: {result.aggregate_metrics['median_return']:.2%}")
print(f"  Mean Sharpe:   {result.aggregate_metrics['mean_sharpe']:.2f}")
print(f"  Worst Drawdown: {result.aggregate_metrics['worst_drawdown']:.2%}")
print(f"\nBest Scenario: {result.best_scenario_id}")
print(f"Worst Scenario: {result.worst_scenario_id}")
print("=" * 60)
```

---

## 4. Advanced Examples

### 4.1 Example: Options Portfolio Analysis

```python
from batch_options_analysis import BatchOptionsAnalyzer
from options_risk_simulator import OptionContract
from scenario_engine import ScenarioEngine

# Create options portfolio
contracts = [
    OptionContract(
        ticker="SPY",
        strike=450.0,
        expiry_days=60,
        option_type="call",
        position="long",
        quantity=10,
        premium=5.50
    ),
    OptionContract(
        ticker="SPY",
        strike=440.0,
        expiry_days=60,
        option_type="put",
        position="short",
        quantity=10,
        premium=4.25
    )
]

# Generate scenario
engine = ScenarioEngine()
scenario = engine.generate_monte_carlo(
    tickers=["SPY"],
    num_days=60,
    random_seed=42
)

# Analyze options
analyzer = BatchOptionsAnalyzer()
result = analyzer.analyze(
    contracts=contracts,
    scenario=scenario,
    portfolio_id="iron_condor"
)

# View Greeks
print("PORTFOLIO GREEKS")
print(f"Net Delta: {result.portfolio_greeks_initial.delta:.2f} → {result.portfolio_greeks_final.delta:.2f}")
print(f"Net Gamma: {result.portfolio_greeks_initial.gamma:.4f}")
print(f"Net Vega:  {result.portfolio_greeks_initial.vega:.2f}")
print(f"Net Theta: {result.portfolio_greeks_initial.theta:.2f} (daily decay)")

# View risk metrics
print(f"\nPORTFOLIO RISK")
print(f"VaR 95%: ${result.var_95:,.2f}")
print(f"CVaR 95%: ${result.cvar_95:,.2f}")
```

### 4.2 Example: Custom Scenario Creation

```python
from scenario_engine import ScenarioEngine, ScenarioDefinition, ScenarioPath
import numpy as np
from datetime import datetime, timedelta

# Create custom scenario manually
dates = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30)]

# Custom price path (example: gradual decline followed by sharp recovery)
custom_prices = np.concatenate([
    np.linspace(100, 90, 20),  # Decline
    np.linspace(90, 105, 10)   # Recovery
])

custom_returns = np.diff(np.log(custom_prices))
custom_returns = np.concatenate([[0], custom_returns])  # Prepend 0 for first day

custom_path = ScenarioPath(
    ticker="CUSTOM",
    dates=dates,
    prices=custom_prices,
    returns=custom_returns,
    metadata={"description": "V-shaped recovery"}
)

custom_scenario = ScenarioDefinition(
    scenario_id="custom_recovery_20251029",
    scenario_type="custom",
    tickers=["CUSTOM"],
    paths={"CUSTOM": custom_path},
    num_days=30,
    random_seed=999,
    metadata={"created_by": "manual"}
)

# Use custom scenario in simulation
from portfolio_simulator import Portfolio, PortfolioSimulator

portfolio = Portfolio(
    portfolio_id="test",
    holdings={"CUSTOM": 100},
    cash=0.0,
    prices={"CUSTOM": 100.0}
)

simulator = PortfolioSimulator()
result = simulator.simulate(portfolio, custom_scenario)
print(f"Custom Scenario Return: {result.risk_metrics.total_return:.2%}")
```

### 4.3 Example: Reproducibility Testing

```python
from phase7_batch_orchestrator import BatchSimulationOrchestrator
import hashlib
import json

# Run same simulation 3 times with fixed seed
results = []
for iteration in range(3):
    orchestrator = BatchSimulationOrchestrator()
    result = orchestrator.run_batch(
        tickers=["SPY", "QQQ"],
        num_monte_carlo=2,
        num_stress=0,
        num_events=0,
        num_days=60,
        workers=2
    )
    results.append(result)

# Check reproducibility
print("REPRODUCIBILITY TEST")
for i, result in enumerate(results):
    mean_return = result.aggregate_metrics['mean_return']
    result_hash = hashlib.sha256(
        json.dumps(result.to_dict(), sort_keys=True).encode()
    ).hexdigest()[:16]
    print(f"Iteration {i+1}: Mean Return={mean_return:.4f}, Hash={result_hash}")

# Compute variation
mean_returns = [r.aggregate_metrics['mean_return'] for r in results]
variation = np.std(mean_returns) / np.mean(mean_returns) * 100
print(f"\nVariation: {variation:.4f}% (target: <1%)")
print("✅ REPRODUCIBLE" if variation < 1.0 else "❌ NOT REPRODUCIBLE")
```

---

## 5. Output Formats

### 5.1 JSON Export

```python
from simulation_report_builder import BatchReportBuilder

builder = BatchReportBuilder()
builder.generate_batch_summary_json(
    batch_id="my_analysis",
    results=results,
    execution_time=10.5,
    cache_hit_rate=0.3
)

# Output: outputs/phase7_batch/my_analysis/my_analysis_summary.json
```

**JSON Structure:**
```json
{
  "metadata": {
    "batch_id": "my_analysis",
    "timestamp": "2025-10-29T12:34:56",
    "num_scenarios": 5,
    "execution_time_seconds": 10.5
  },
  "aggregate_metrics": {
    "mean_return": 0.0515,
    "median_return": 0.0432,
    "mean_sharpe": 2.34,
    "worst_drawdown": -0.1823
  },
  "individual_results": [...]
}
```

### 5.2 CSV Export

```python
builder.generate_scenario_comparison_csv(results)

# Output: scenario_comparison.csv
```

**CSV Format:**
```csv
scenario_id,total_return,annualized_volatility,sharpe_ratio,sortino_ratio,var_95,cvar_95,max_drawdown
monte_carlo_001,0.0514,0.1842,0.28,0.35,-0.0364,-0.0507,-0.0871
monte_carlo_002,0.0321,0.1923,0.17,0.21,-0.0412,-0.0589,-0.1023
stress_vol_spike,-0.0832,0.3421,-0.24,-0.31,-0.0856,-0.1234,-0.2145
```

### 5.3 Markdown Report

```python
builder.generate_batch_markdown_report(
    batch_id="my_analysis",
    results=results,
    execution_time=10.5,
    cache_hit_rate=0.3
)

# Output: outputs/phase7_batch/my_analysis/my_analysis_report.md
```

**Markdown Preview:**
```markdown
# Batch Simulation Report: my_analysis

## Performance Summary
- Total Scenarios: 5
- Execution Time: 10.5s
- Cache Hit Rate: 30.0%

## Returns Distribution
| Scenario | Total Return | Sharpe Ratio |
|----------|--------------|--------------|
| monte_carlo_001 | 5.14% | 0.28 |
| monte_carlo_002 | 3.21% | 0.17 |
| stress_vol_spike | -8.32% | -0.24 |
```

### 5.4 HTML Interactive Report

```python
builder.generate_html_report(
    batch_id="my_analysis",
    results=results
)

# Output: outputs/phase7_batch/my_analysis/my_analysis_report.html
```

**Features:**
- 📊 Interactive Chart.js visualizations
- 📱 Responsive design (desktop/tablet/mobile)
- 🌐 Offline-capable (no external dependencies)
- 🎨 Color-coded metrics (green for positive, red for negative)

**Charts Included:**
1. Returns Distribution (Bar Chart)
2. Risk-Return Scatter Plot

---

## 6. Mock/Offline Mode

### 6.1 Default Behavior (Already Offline)

Phase 7 is **100% offline by default**. No external API calls are made.

**Synthetic Data Used:**
- **Prices:** $100 per share (all tickers)
- **Volatility:** 20% annualized
- **Correlation:** 0.5 (all pairs)
- **Risk-free rate:** 0% (for Sharpe calculation)

### 6.2 Using Historical Data (Optional)

If you have historical price data, you can override synthetic parameters:

```python
from scenario_engine import ScenarioEngine

engine = ScenarioEngine()

# Option 1: Provide volatility estimates
volatilities = {"SPY": 0.18, "QQQ": 0.25, "IWM": 0.22}
scenario = engine.generate_monte_carlo(
    tickers=["SPY", "QQQ", "IWM"],
    num_days=252,
    volatility_overrides=volatilities
)

# Option 2: Provide correlation matrix
import numpy as np
correlation_matrix = np.array([
    [1.0, 0.7, 0.6],  # SPY correlations
    [0.7, 1.0, 0.5],  # QQQ correlations
    [0.6, 0.5, 1.0]   # IWM correlations
])
scenario = engine.generate_monte_carlo(
    tickers=["SPY", "QQQ", "IWM"],
    num_days=252,
    correlation_matrix=correlation_matrix
)
```

### 6.3 Deterministic Testing

For unit tests or reproducibility checks, always use fixed seeds:

```python
# Always produces identical results
scenario = engine.generate_monte_carlo(
    tickers=["SPY"],
    num_days=100,
    random_seed=42  # Same seed = same output
)
```

---

## 7. Troubleshooting

### 7.1 Common Errors

**Error:** `ModuleNotFoundError: No module named 'scenario_engine'`

**Solution:**
```bash
# Make sure you're in the unified-dashboard directory
cd /path/to/unified-dashboard

# Run Python from the root directory
python -c "from scenario_engine import ScenarioEngine; print('✅ Import successful')"
```

---

**Error:** `MemoryError` when running large batch simulations

**Solution:**
```python
# Reduce number of Monte Carlo paths
scenario = engine.generate_monte_carlo(
    tickers=tickers,
    num_paths=500  # Instead of 1000
)

# Or reduce workers (less memory usage)
result = orchestrator.run_batch(
    tickers=tickers,
    workers=4  # Instead of 8
)
```

---

**Error:** Performance is slower than expected

**Solution:**
```python
# Check cache hit rate
print(f"Cache Hit Rate: {result.cache_hit_rate:.1%}")

# If 0%, scenarios are not being reused
# Use consistent random seeds:
scenario1 = engine.generate_monte_carlo(..., random_seed=42)
scenario2 = engine.generate_monte_carlo(..., random_seed=42)  # Cached!
```

---

### 7.2 Performance Tuning

**Slow simulations (>20s for 10 tickers)?**

1. **Reduce Monte Carlo paths:**
   ```python
   num_paths=500  # Instead of 1000 (50% speedup)
   ```

2. **Reduce simulation horizon:**
   ```python
   num_days=126  # 6 months instead of 252 days
   ```

3. **Increase workers:**
   ```python
   workers=8  # Use more CPU cores
   ```

4. **Enable scenario caching:**
   ```python
   # Use consistent seeds across runs
   for seed in [42, 43, 44]:  # Fixed seeds
       scenario = engine.generate_monte_carlo(..., random_seed=seed)
   ```

---

## 8. Best Practices

### 8.1 Scenario Design

✅ **DO:**
- Use 252 days for annual simulations (trading days)
- Use 1000 Monte Carlo paths for robust statistics
- Run multiple scenarios (3+ MC, 3+ stress)
- Use fixed seeds for reproducibility

❌ **DON'T:**
- Simulate >500 days (diminishing returns, slow)
- Use <100 MC paths (unreliable statistics)
- Mix random and fixed seeds in same analysis

### 8.2 Portfolio Construction

✅ **DO:**
- Include 5-10 tickers for diversification
- Balance stock/cash allocation
- Use realistic prices ($50-$500 per share)

❌ **DON'T:**
- Create portfolios with 1 ticker (no diversification)
- Use $0 prices (causes division errors)
- Mix currencies (assume all USD)

### 8.3 Report Generation

✅ **DO:**
- Generate HTML reports for stakeholders
- Use JSON for programmatic analysis
- Use CSV for Excel integration
- Archive reports by date/batch_id

❌ **DON'T:**
- Rely only on console output (hard to share)
- Overwrite reports (use unique batch_ids)

---

**End of User Guide**

**Next Steps:**
1. Try the Quick Start example
2. Run Tutorial 1-3
3. Generate your first HTML report
4. Customize scenarios for your portfolio

**Support:** See PHASE7_SIMULATION_IMPLEMENTATION.md for technical details.

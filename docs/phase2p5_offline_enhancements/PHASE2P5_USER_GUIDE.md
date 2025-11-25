# Phase 2.5 User Guide

**Offline Visualization, Optimization, and Explainability Expansion**

---

## Welcome to Phase 2.5!

This guide teaches you how to use the **Phase 2.5 offline enhancements** in the Unified Financial Dashboard. Whether you're a portfolio manager, data scientist, or developer, you'll learn to:

✅ **Generate rich, interactive visualizations** for feature importance  
✅ **Compare multiple tickers** to identify consensus vs. divergent drivers  
✅ **Interpret narrative explanations** powered by context-aware templates  
✅ **Leverage persistent caching** for faster repeat analyses  
✅ **Monitor performance metrics** to optimize workflows  

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Visualization Suite](#2-visualization-suite)
3. [Comparison Mode](#3-comparison-mode)
4. [Narrative Explanations](#4-narrative-explanations)
5. [Caching and Performance](#5-caching-and-performance)
6. [Troubleshooting](#6-troubleshooting)
7. [Best Practices](#7-best-practices)
8. [FAQ](#8-faq)

---

## 1. Quick Start

### 1.1 Installation Check

Ensure Plotly is installed (required for visualizations):

```bash
pip install plotly
```

If Plotly is unavailable, Phase 2.5 gracefully falls back to text-only explanations.

### 1.2 Your First Explanation

```python
from financial_dashboard.tabs.azure_ml_lab.explainability_engine import ExplainabilityEngine

# Initialize engine
engine = ExplainabilityEngine()

# Generate explanation
narrative = engine.generate_textual_rationale(
    ticker="AAPL",
    prediction_value=0.05,  # 5% expected return
    prediction_target='return',
    top_n=5,
    use_narrative_templates=True  # Enable Phase 2.5 templates
)

print(narrative)
```

**Output**:
```
**Prediction for AAPL:** Higher expected return of +5.00%.

**Key Contributing Factors:**

1. Momentum 20 exhibits strong bullish momentum, signaling accelerating upward 
   price movement that drives positive expected return expectations. *(35.2% contribution)*
2. Volatility 30 suggests compressed volatility, reducing risk but potentially 
   limiting expected return upside for growth-oriented positions. *(22.1% contribution)*
3. PE Ratio demonstrates robust fundamental health, with strong profitability 
   metrics supporting higher expected return forecasts. *(18.5% contribution)*
...
```

### 1.3 Your First Visualization

```python
from financial_dashboard.tabs.azure_ml_lab.phase2p5_offline_enhancements.insight_visuals import (
    create_feature_importance_bar
)

# Get feature importance
importance_df = engine.compute_feature_importance("AAPL", top_n=10)

# Create bar chart
fig = create_feature_importance_bar(
    importance_df,
    ticker="AAPL",
    title="AAPL Feature Importance",
    top_n=10
)

# Display in Jupyter or save to file
fig.show()  # Interactive plot in browser
# OR
fig.write_html("aapl_importance.html")
```

**Result**: Interactive horizontal bar chart with:
- Green bars for positive SHAP values (increase prediction)
- Red bars for negative SHAP values (decrease prediction)
- Black text labels for accessibility
- Hover tooltips with exact values

---

## 2. Visualization Suite

Phase 2.5 provides **5 chart types**, each optimized for different analysis needs.

### 2.1 Bar Chart (Classic)

**Best For**: Quick overview of top contributing features

**Code**:
```python
from financial_dashboard.tabs.azure_ml_lab.phase2p5_offline_enhancements.insight_visuals import (
    create_feature_importance_bar
)

fig = create_feature_importance_bar(
    importance_df,
    ticker="AAPL",
    title="Feature Importance for AAPL",
    top_n=10
)
fig.show()
```

**Interpretation**:
- **Longer bars** = More important features
- **Green** = Positive contribution (pushes prediction higher)
- **Red** = Negative contribution (pulls prediction lower)
- **Sorted** by absolute importance (most important at top)

**Example Use Case**: "Which feature has the biggest impact on AAPL's prediction?"

---

### 2.2 Waterfall Chart (Cumulative Flow)

**Best For**: Understanding how features combine to produce the final prediction

**Code**:
```python
from financial_dashboard.tabs.azure_ml_lab.phase2p5_offline_enhancements.insight_visuals import (
    create_waterfall_chart
)

fig = create_waterfall_chart(
    importance_df,
    ticker="AAPL",
    baseline_value=0.0,         # Starting point (e.g., 0% return)
    prediction_value=0.05,      # Final prediction (e.g., 5% return)
    title="AAPL Waterfall: From Baseline to Prediction",
    top_n=10
)
fig.show()
```

**Interpretation**:
- **Baseline** (leftmost bar): Starting prediction without features
- **Feature bars**: Incremental contributions (stacked left-to-right)
- **Prediction** (rightmost bar): Final prediction after all features
- **Flow direction**: Visualizes cumulative impact

**Example Use Case**: "How does each feature incrementally move the prediction from 0% to 5%?"

---

### 2.3 Heatmap (Multi-Ticker Correlation)

**Best For**: Comparing feature importance across multiple tickers

**Code**:
```python
from financial_dashboard.tabs.azure_ml_lab.phase2p5_offline_enhancements.insight_visuals import (
    create_feature_heatmap
)

# Generate importance for multiple tickers
tickers = ["AAPL", "GOOGL", "TSLA"]
importance_list = [
    engine.compute_feature_importance(ticker, top_n=10)
    for ticker in tickers
]

fig = create_feature_heatmap(
    importance_list,
    tickers=tickers,
    title="Cross-Ticker Feature Importance",
    top_n=10
)
fig.show()
```

**Interpretation**:
- **Rows**: Features (momentum, volatility, etc.)
- **Columns**: Tickers (AAPL, GOOGL, TSLA)
- **Cell Color**: Normalized importance (darker = more important)
- **Cell Value**: Absolute SHAP value
- **Patterns**:
  - Same color across row → Consensus feature (all tickers agree)
  - Varied colors → Ticker-specific feature

**Example Use Case**: "Is momentum important for all tech stocks, or just AAPL?"

---

### 2.4 Beeswarm Plot (Distribution)

**Best For**: Visualizing feature value distributions and outliers

**Code**:
```python
from financial_dashboard.tabs.azure_ml_lab.phase2p5_offline_enhancements.insight_visuals import (
    create_beeswarm_plot
)

fig = create_beeswarm_plot(
    importance_df,
    ticker="AAPL",
    title="AAPL Feature Distribution (Beeswarm)",
    top_n=10
)
fig.show()
```

**Interpretation**:
- **X-axis**: SHAP value (negative ← → positive)
- **Y-axis**: Feature name
- **Point size**: Proportional to importance
- **Jitter**: Spread prevents overlapping points
- **Clustering**: Tight cluster = consistent impact; spread = variable impact

**Example Use Case**: "Which features have the most variable contributions?"

---

### 2.5 Force Plot (Push/Pull Visualization)

**Best For**: Intuitive explanation of directional feature impact

**Code**:
```python
from financial_dashboard.tabs.azure_ml_lab.phase2p5_offline_enhancements.insight_visuals import (
    create_force_plot
)

fig = create_force_plot(
    importance_df,
    ticker="AAPL",
    baseline_value=0.0,
    prediction_value=0.05,
    title="AAPL Force Plot: Feature Push/Pull",
    top_n=10
)
fig.show()
```

**Interpretation**:
- **Baseline** (left): Starting prediction
- **Positive features** (right-pointing arrows): "Push" prediction higher
- **Negative features** (left-pointing arrows): "Pull" prediction lower
- **Prediction** (right): Final prediction after all forces
- **Arrow width**: Magnitude of impact

**Example Use Case**: "Explain to a non-technical stakeholder how features affect the prediction."

---

### 2.6 Choosing the Right Chart

| Chart Type | Best For | Audience | Complexity |
|------------|----------|----------|------------|
| **Bar** | Quick importance ranking | Technical + Non-technical | Low |
| **Waterfall** | Cumulative contribution flow | Technical (analysts) | Medium |
| **Heatmap** | Multi-ticker comparison | Portfolio managers | Medium |
| **Beeswarm** | Distribution analysis | Data scientists | High |
| **Force** | Intuitive push/pull explanation | Non-technical stakeholders | Low |

**Recommendation**: Start with **Bar** for exploration, use **Force** for presentations, use **Heatmap** for portfolio analysis.

---

## 3. Comparison Mode

### 3.1 Side-by-Side Comparison

**Purpose**: Visually compare feature importance across multiple tickers

**Code**:
```python
from financial_dashboard.tabs.azure_ml_lab.phase2p5_offline_enhancements.insight_comparator import (
    create_side_by_side_bars
)

# Prepare results for multiple tickers
tickers = ["AAPL", "GOOGL", "TSLA"]
results = {}
for ticker in tickers:
    results[ticker] = {
        'feature_importance': engine.compute_feature_importance(ticker, top_n=10),
        'prediction_value': 0.05,  # Example prediction
        'prediction_target': 'return'
    }

# Create side-by-side comparison
fig = create_side_by_side_bars(results, tickers, top_n=10)
fig.show()
```

**Interpretation**:
- **Subplots**: One per ticker (left-to-right)
- **Synchronized scales**: Y-axes use same range for fair comparison
- **Color consistency**: Same feature = same color across subplots
- **Key insights**:
  - **Tall bars in all subplots** → Consensus feature (important for all)
  - **Tall bar in one subplot only** → Ticker-specific driver

**Example Use Case**: "Which features drive returns across my entire tech portfolio?"

---

### 3.2 Differential Importance Analysis

**Purpose**: Identify ticker-specific vs. portfolio-wide features

**Code**:
```python
from financial_dashboard.tabs.azure_ml_lab.phase2p5_offline_enhancements.insight_comparator import (
    compute_differential_importance,
    create_differential_chart
)

# Compute differential importance
diff_df = compute_differential_importance(results, tickers, top_n=15)

print(diff_df.head(10))
# Output:
#            feature  mean_importance  std_importance  coefficient_of_variation  rank
# 0       sentiment           0.082           0.045                    0.549     1
# 1    momentum_20            0.128           0.065                    0.508     2
# 2  volatility_30            0.095           0.042                    0.442     3
# ...

# Visualize differential importance
fig = create_differential_chart(results, tickers, top_n=15)
fig.show()
```

**Interpretation**:
- **Coefficient of Variation (CV)**: `std / mean`
  - **High CV (>0.5)**: Feature is ticker-specific (varies widely)
  - **Low CV (<0.2)**: Feature is consensus (similar across tickers)
- **Use Case**:
  - **High CV features**: Require individual ticker analysis
  - **Low CV features**: Portfolio-level strategies apply

**Example**: If `sentiment` has CV=0.55, it means sentiment impact varies significantly across AAPL, GOOGL, TSLA → Need stock-specific sentiment analysis.

---

### 3.3 Consensus Ranking

**Purpose**: Aggregate feature importance across tickers using multiple methods

**Code**:
```python
from financial_dashboard.tabs.azure_ml_lab.phase2p5_offline_enhancements.insight_comparator import (
    compute_consensus_ranking,
    create_consensus_chart
)

# Compute consensus using 3 methods
consensus_mean_rank = compute_consensus_ranking(results, tickers, method='mean_rank')
consensus_mean_imp = compute_consensus_ranking(results, tickers, method='mean_importance')
consensus_top3 = compute_consensus_ranking(results, tickers, method='top3_frequency')

print("Mean Rank Consensus:")
print(consensus_mean_rank.head(5))
#            feature  consensus_score  rank
# 0    momentum_20             2.33     1
# 1         beta               3.67     2
# 2  volatility_30             4.00     3

# Visualize consensus
fig = create_consensus_chart(results, tickers, method='mean_importance', top_n=10)
fig.show()
```

**Methods Explained**:

| Method | Formula | Best For | Robustness |
|--------|---------|----------|------------|
| **mean_rank** | Avg of ranks (1, 2, 3, ...) | Equal weighting | High (outlier-resistant) |
| **mean_importance** | Avg of absolute SHAP values | Magnitude-aware | Medium (outlier-sensitive) |
| **top3_frequency** | Count of top-3 appearances | Binary threshold | Low (loses granularity) |

**Recommendation**: Use `mean_importance` for most cases; switch to `mean_rank` if outliers present.

---

### 3.4 Full Comparison Report

**Purpose**: Generate comprehensive JSON report for portfolio analysis

**Code**:
```python
from financial_dashboard.tabs.azure_ml_lab.phase2p5_offline_enhancements.insight_comparator import (
    generate_comparison_report
)
import json

report = generate_comparison_report(results, tickers)

# Save to file
with open("portfolio_comparison_report.json", "w") as f:
    json.dump(report, f, indent=2)

# Pretty-print summary
print(f"Tickers analyzed: {report['summary']['ticker_count']}")
print(f"Consensus features (top 5):")
for feat in report['consensus_features'][:5]:
    print(f"  - {feat['feature']}: {feat['mean_importance']:.3f}")
```

**Report Structure**:
```json
{
  "summary": {
    "ticker_count": 3,
    "total_features_analyzed": 30,
    "report_timestamp": "2025-01-13T15:30:00"
  },
  "individual_results": {
    "AAPL": { "top_5_features": [...] },
    "GOOGL": { "top_5_features": [...] },
    "TSLA": { "top_5_features": [...] }
  },
  "differential_analysis": {
    "high_variance_features": [...]  // Ticker-specific
  },
  "consensus_features": [...]  // Portfolio-wide
}
```

**Example Use Case**: "Generate daily portfolio report highlighting common drivers."

---

## 4. Narrative Explanations

### 4.1 Basic vs. Narrative Templates

**Phase 2 (Basic)**:
```
1. **Momentum 20** (35.2% importance): strongly increases predicted expected return
```

**Phase 2.5 (Narrative)**:
```
1. Momentum 20 exhibits strong bullish momentum, signaling accelerating upward 
   price movement that drives positive expected return expectations. *(35.2% contribution)*
```

**Improvement**: 3x richer context, financial terminology, directional clarity

---

### 4.2 Available Narrative Templates

Phase 2.5 includes **15 templates** covering diverse scenarios:

| Template | Trigger Features | Narrative Example |
|----------|------------------|-------------------|
| **Growth Momentum** | momentum, ma, rsi, macd | "Exhibits strong bullish momentum, signaling accelerating upward price movement..." |
| **Volatility Risk** | volatility, atr, bollinger | "Indicates elevated market volatility, creating favorable conditions for active strategies..." |
| **Fundamental Strength** | pe_ratio, roe, debt, earnings | "Demonstrates robust fundamental health, with strong profitability metrics..." |
| **Sentiment Catalyst** | sentiment, news, social, analyst | "Reflects positive market sentiment, driven by favorable news flow..." |
| **Factor Exposure** | beta, smb, hml, quality | "Shows favorable factor exposure, aligning with current market regime preferences..." |
| **Volume Liquidity** | volume, turnover, obv | "Signals strong trading activity and liquidity, supporting price discovery..." |
| **Macroeconomic Tailwind** | gdp, inflation, interest_rate | "Benefits from supportive macroeconomic conditions..." |
| **Defensive Quality** | (low vol + quality factors) | "Reflects defensive quality characteristics, providing stability..." |
| **Aggressive Growth** | (high momentum + beta) | "Signals aggressive growth potential, with high beta driving amplified upside..." |
| **Value Opportunity** | (low PE + fundamentals) | "Suggests attractive valuation, creating mean-reversion opportunity..." |
| **Risk-Adjusted Performance** | sharpe, sortino | "Demonstrates strong risk-adjusted returns..." |
| **Mean Reversion** | (overbought/oversold) | "Exhibits oversold conditions, suggesting mean-reversion potential..." |
| **Correlation Diversification** | (low correlation) | "Provides diversification benefits, enhancing portfolio efficiency..." |
| **Cyclical Positioning** | (sector rotation) | "Benefits from favorable cyclical positioning, with sector tailwinds..." |
| **Technical Breakout** | (support/resistance) | "Confirms technical breakout, clearing key resistance levels..." |

---

### 4.3 Customizing Template Usage

**Enable/Disable Narrative Templates**:
```python
# Use narrative templates (default)
narrative_rich = engine.generate_textual_rationale(
    ticker="AAPL",
    prediction_value=0.05,
    use_narrative_templates=True  # Rich narratives
)

# Revert to basic templates
narrative_basic = engine.generate_textual_rationale(
    ticker="AAPL",
    prediction_value=0.05,
    use_narrative_templates=False  # Simple bullet points
)
```

**When to Disable**:
- **Space-constrained UIs**: Basic templates are shorter
- **Low-latency requirements**: Narrative generation adds ~5ms
- **Non-financial audiences**: Basic templates avoid jargon

---

### 4.4 Interpreting Narrative Outputs

**Example Output**:
```
**Prediction for TSLA:** Higher volatility of 45.23%.

**Key Contributing Factors:**

1. Volatility 30 indicates elevated market volatility, creating favorable conditions 
   for active strategies but increasing volatility uncertainty. *(42.1% contribution)*
2. Beta shows favorable factor exposure, aligning with current market regime preferences 
   to enhance volatility. *(28.5% contribution)*
3. Sentiment Score reflects positive market sentiment, driven by favorable news flow 
   and analyst upgrades that boost volatility expectations. *(15.3% contribution)*
```

**Reading Guide**:
- **Prediction Header**: Target variable (return/volatility), magnitude, direction
- **Bullet Points**: Each feature's contribution with narrative explanation
- **Contribution %**: Absolute importance (sum of top features ≈ 100%)
- **Footer**: Total coverage of prediction confidence

---

## 5. Caching and Performance

### 5.1 Persistent Caching Basics

Phase 2.5 caches **explanation results** to disk for faster repeat analyses.

**How It Works**:
1. First request: Full computation (~800ms)
2. Cache write: Save result to disk (~2ms)
3. Subsequent requests: Read from cache (~5ms) → **160x faster**

**Default TTL**: 1 hour (configurable)

---

### 5.2 Using the Cache

**Manual Cache Control**:
```python
from financial_dashboard.tabs.azure_ml_lab.phase2p5_offline_enhancements.phase2p5_persistent_cache import (
    PersistentCache
)

# Initialize cache
cache = PersistentCache(ttl_seconds=3600)  # 1 hour TTL

# Store result
cache.set("AAPL_return_0.05_10", {"narrative": "...", "chart": "..."})

# Retrieve result
cached_result = cache.get("AAPL_return_0.05_10")

# Check if valid
if cache.has("AAPL_return_0.05_10"):
    result = cache.get("AAPL_return_0.05_10")
```

**Decorator Usage** (for functions):
```python
from financial_dashboard.tabs.azure_ml_lab.phase2p5_offline_enhancements.phase2p5_persistent_cache import (
    persistent_cache
)

@persistent_cache(ttl_seconds=3600)
def expensive_analysis(ticker, prediction_value):
    # Heavy computation here
    return result

# First call: computed and cached
result1 = expensive_analysis("AAPL", 0.05)

# Second call: retrieved from cache (160x faster)
result2 = expensive_analysis("AAPL", 0.05)
```

---

### 5.3 Cache Management

**View Cache Statistics**:
```python
stats = cache.get_stats()
print(f"Total entries: {stats['total_entries']}")
print(f"Valid entries: {stats['valid_entries']}")
print(f"Expired entries: {stats['expired_entries']}")
print(f"Cache size: {stats['total_size_mb']:.2f} MB")
```

**Cleanup Expired Entries**:
```python
deleted_count = cache.cleanup_expired()
print(f"Deleted {deleted_count} expired entries")
```

**Clear All Cache**:
```python
cache.clear_all()
print("Cache cleared!")
```

---

### 5.4 Performance Metrics

**Track Session Analytics**:
```python
from financial_dashboard.tabs.azure_ml_lab.phase2p5_offline_enhancements.phase2p5_metrics import (
    get_session_stats
)

stats = get_session_stats()
print(f"Explanations generated: {stats['explanation_count']}")
print(f"Cache hit rate: {stats['cache_hit_rate']:.1f}%")
print(f"Average compute time: {stats['avg_compute_time_ms']:.1f}ms")
print(f"Top tickers: {stats['top_tickers']}")
```

**Export Session Summary**:
```python
from financial_dashboard.tabs.azure_ml_lab.phase2p5_offline_enhancements.phase2p5_metrics import (
    export_session_summary
)

summary_path = export_session_summary()
print(f"Session summary saved to: {summary_path}")
```

---

## 6. Troubleshooting

### 6.1 Common Issues

#### **Issue**: Visualizations not rendering

**Symptom**: `TypeError: 'NoneType' object is not iterable`

**Cause**: Plotly not installed

**Solution**:
```bash
pip install plotly
```

**Fallback**: Set `use_narrative_templates=False` to get text-only explanations.

---

#### **Issue**: Cache not persisting across sessions

**Symptom**: Cache always shows 0 entries after restart

**Cause**: Cache directory deleted or moved

**Solution**:
```python
# Verify cache directory exists
cache = PersistentCache()
print(f"Cache dir: {cache.cache_dir}")
# Ensure directory has write permissions
```

---

#### **Issue**: Slow render times (>2 seconds)

**Symptom**: Charts take too long to generate

**Diagnosis**:
```python
from financial_dashboard.tabs.azure_ml_lab.phase2p5_offline_enhancements.phase2p5_performance_diagnostic import (
    run_all_diagnostics
)

results = run_all_diagnostics()
print(f"Average render time: {results['summary']['avg_render_time_ms']:.1f}ms")
```

**Solutions**:
1. **Reduce `top_n`**: Use fewer features (e.g., `top_n=5` instead of `top_n=15`)
2. **Enable caching**: Repeat analyses will be 160x faster
3. **Upgrade hardware**: Phase 2.5 is CPU-bound (Plotly rendering)

---

#### **Issue**: Heatmap shows all zeros

**Symptom**: Heatmap cells are blank or zero

**Cause**: Importance values not normalized properly

**Solution**:
```python
# Ensure importance_list contains valid DataFrames
for df in importance_list:
    print(df['shap_value'].sum())  # Should be non-zero
```

---

### 6.2 Logging and Diagnostics

**Enable Debug Logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now all Phase 2.5 operations will log detailed info
```

**Run Performance Diagnostics**:
```bash
cd financial_dashboard/tabs/azure_ml_lab/phase2p5_offline_enhancements/
python phase2p5_performance_diagnostic.py
# Output: phase2p5_performance_report.json
```

---

## 7. Best Practices

### 7.1 Visualization Best Practices

1. **Start with Bar Charts**: Simplest, fastest, most intuitive
2. **Use Waterfall for Presentations**: Stakeholders love cumulative flow
3. **Limit Heatmap Tickers**: Max 10 tickers for readability
4. **Beeswarm for Data Scientists**: Requires statistical literacy
5. **Force Plot for Non-Technical**: Intuitive push/pull metaphor

### 7.2 Comparison Mode Best Practices

1. **Group Similar Assets**: Compare AAPL, GOOGL, MSFT (tech), not AAPL, GLD, TLT (mixed)
2. **Use Differential Analysis First**: Identify ticker-specific vs. consensus features before diving deep
3. **Consensus Ranking for Portfolios**: Use `mean_importance` for equal-weighted portfolios
4. **Limit to 10 Tickers**: UI becomes cluttered beyond 10

### 7.3 Caching Best Practices

1. **Set Appropriate TTL**: 1 hour (default) for intraday, 24 hours for daily batch jobs
2. **Monitor Cache Hit Rate**: Target >60% for optimal performance
3. **Cleanup Regularly**: Run `cache.cleanup_expired()` daily if generating >1000 explanations
4. **Use HybridCache**: Best of both worlds (fast + durable)

### 7.4 Performance Best Practices

1. **Cache Aggressively**: Enable caching for repeat tickers
2. **Batch Requests**: Generate explanations in bulk, then cache all
3. **Reduce `top_n`**: 5-10 features are usually sufficient
4. **Monitor Metrics**: Track `avg_compute_time_ms` to detect regressions

---

## 8. FAQ

**Q: Can I export charts as images (PNG/SVG)?**  
A: Yes! Use `fig.write_image("chart.png")` (requires `kaleido` package: `pip install kaleido`)

**Q: What's the difference between `mean_rank` and `mean_importance` consensus?**  
A: `mean_rank` averages ranks (1, 2, 3, ...), `mean_importance` averages actual SHAP values. Use `mean_importance` for magnitude-aware ranking.

**Q: Can I customize narrative templates?**  
A: Not yet in Phase 2.5. Custom templates are planned for Phase 3.

**Q: How do I integrate Phase 2.5 with my existing dashboard?**  
A: Import Phase 2.5 modules into your dashboard callbacks. See Integration Guide (Section 10 of Implementation Report).

**Q: Does Phase 2.5 work without Plotly?**  
A: Yes! Narrative explanations work without Plotly. Only visualizations require it.

**Q: What's the cache invalidation strategy?**  
A: TTL-based (default: 1 hour). Entries expire automatically. Manual invalidation via `cache.delete(key)` or `cache.clear_all()`.

**Q: Can I use Phase 2.5 in production?**  
A: Yes, but Phase 2.5 uses mock SHAP values. For production, wait for Phase 3 (Azure Live SHAP Integration).

**Q: How do I report bugs or request features?**  
A: File an issue in the project repository with:
  1. Reproducible code example
  2. Expected behavior
  3. Actual behavior
  4. Phase 2.5 version (check file headers)

---

## Next Steps

✅ **Completed**: Phase 2.5 User Guide  
🔜 **Next**: Read **PHASE2P5_VISUALIZATION_GLOSSARY.md** for chart interpretation deep-dive  
🔜 **After That**: Await **Phase 3: Azure Live SHAP Integration**  

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-13  
**Author**: Autonomous Lead Software Engineer  
**Total Lines**: 750+ lines

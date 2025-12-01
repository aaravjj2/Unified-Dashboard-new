"""
Azure ML Lab - Explainability Engine (Phase 1 Local Intelligence)

This module provides SHAP-like local explainability for ML predictions.
Designed for offline/mock mode operation with deterministic outputs.

Core Features:
- Feature importance ranking (top N contributors)
- SHAP-like summary plots (matplotlib/plotly)
- Textual prediction rationales ("why this prediction?")
- Deterministic mock mode for testing without live ML

Phase 1 Scope: LOCAL SIMULATION ONLY
Phase 2: Caching layer + callback integration (ADDED)
Phase 3: Integration with real Azure ML SHAP outputs
"""

import logging
import json
import hashlib
import time
from functools import lru_cache
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd

# Plotting libraries (graceful fallback)
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("matplotlib not available - plots will be skipped")

try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logging.warning("plotly not available - interactive plots will be skipped")

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

# Feature groups for portfolio predictions
FEATURE_GROUPS = {
    'technical': [
        'momentum_20d', 'volatility_20d', 'sharpe_20d', 'rsi_14d', 
        'macd', 'bollinger_width', 'volume_spike'
    ],
    'fundamental': [
        'pe_ratio', 'market_cap', 'dividend_yield', 'roe', 
        'debt_to_equity', 'current_ratio', 'earnings_growth'
    ],
    'factors': [
        'market_beta', 'smb_exposure', 'hml_exposure', 
        'momentum_factor', 'quality_factor', 'low_vol_factor'
    ],
    'sentiment': [
        'news_sentiment', 'social_sentiment', 'analyst_rating', 
        'insider_buying', 'institutional_ownership'
    ]
}

ALL_FEATURES = [f for group in FEATURE_GROUPS.values() for f in group]

# Contribution templates for textual rationales
CONTRIBUTION_TEMPLATES = {
    'high_positive': "strongly increases predicted {target}",
    'medium_positive': "moderately increases predicted {target}",
    'low_positive': "slightly increases predicted {target}",
    'neutral': "has minimal impact on predicted {target}",
    'low_negative': "slightly decreases predicted {target}",
    'medium_negative': "moderately decreases predicted {target}",
    'high_negative': "strongly decreases predicted {target}"
}

# ============================================================================
# PHASE 2.5: NARRATIVE TEMPLATES FOR ENHANCED EXPLAINABILITY
# ============================================================================

# Feature type classifications for template selection
FEATURE_TYPE_PATTERNS = {
    'momentum': ['momentum', 'ma_', 'rsi', 'stochastic', 'macd', 'adx', 'trend'],
    'volatility': ['volatility', 'atr', 'bollinger', 'std', 'var', 'garch'],
    'fundamental': ['pe_ratio', 'pb_ratio', 'roe', 'debt', 'earnings', 'revenue', 'margin', 'fcf', 'dividend'],
    'sentiment': ['sentiment', 'news', 'social', 'analyst', 'rating', 'recommendation'],
    'factor': ['beta', 'smb', 'hml', 'momentum_factor', 'quality', 'value_factor', 'size'],
    'volume': ['volume', 'liquidity', 'turnover', 'obv', 'vwap'],
    'macroeconomic': ['gdp', 'inflation', 'interest_rate', 'unemployment', 'treasury', 'vix', 'market_return'],
}

# Narrative templates: 15 templates covering diverse scenarios
NARRATIVE_TEMPLATES = {
    'growth_momentum': {
        'positive': "{feat} exhibits strong bullish momentum, signaling accelerating upward price movement that drives positive {target} expectations.",
        'negative': "{feat} shows weakening momentum, indicating decelerating growth that pressures {target} downward."
    },
    'volatility_risk': {
        'positive': "{feat} indicates elevated market volatility, creating favorable conditions for active strategies but increasing {target} uncertainty.",
        'negative': "{feat} suggests compressed volatility, reducing risk but potentially limiting {target} upside for growth-oriented positions."
    },
    'fundamental_strength': {
        'positive': "{feat} demonstrates robust fundamental health, with strong profitability metrics supporting higher {target} forecasts.",
        'negative': "{feat} reveals fundamental weakness, with deteriorating margins or leverage constraining {target} potential."
    },
    'sentiment_catalyst': {
        'positive': "{feat} reflects positive market sentiment, driven by favorable news flow and analyst upgrades that boost {target} expectations.",
        'negative': "{feat} indicates negative sentiment headwinds, with adverse news or analyst downgrades weighing on {target} outlook."
    },
    'factor_exposure': {
        'positive': "{feat} shows favorable factor exposure, aligning with current market regime preferences to enhance {target}.",
        'negative': "{feat} exhibits unfavorable factor exposure, creating headwinds in the prevailing market environment that reduce {target}."
    },
    'volume_liquidity': {
        'positive': "{feat} signals strong trading activity and liquidity, supporting price discovery and improving {target} reliability.",
        'negative': "{feat} indicates thin liquidity conditions, introducing execution risk and wider {target} uncertainty."
    },
    'macroeconomic_tailwind': {
        'positive': "{feat} benefits from supportive macroeconomic conditions, with favorable rates or growth trends boosting {target}.",
        'negative': "{feat} faces macroeconomic headwinds, with tightening conditions or growth slowdown constraining {target}."
    },
    'defensive_quality': {
        'positive': "{feat} reflects defensive quality characteristics, providing stability and downside protection that supports {target} in uncertain markets.",
        'negative': "{feat} lacks defensive attributes, increasing vulnerability to market stress and downside {target} risk."
    },
    'aggressive_growth': {
        'positive': "{feat} signals aggressive growth potential, with high beta and momentum driving amplified {target} upside in risk-on environments.",
        'negative': "{feat} indicates excessive risk-taking, with high volatility and leverage amplifying downside {target} risk in risk-off conditions."
    },
    'value_opportunity': {
        'positive': "{feat} suggests attractive valuation, with low multiples and strong fundamentals creating mean-reversion {target} opportunity.",
        'negative': "{feat} indicates stretched valuation, with high multiples and weak fundamentals signaling {target} downside risk."
    },
    'risk_adjusted_performance': {
        'positive': "{feat} demonstrates strong risk-adjusted returns, with favorable Sharpe characteristics supporting sustainable {target} outlook.",
        'negative': "{feat} shows poor risk-adjusted performance, with volatile returns and drawdowns undermining {target} confidence."
    },
    'mean_reversion': {
        'positive': "{feat} exhibits oversold conditions, suggesting mean-reversion potential that could drive {target} recovery.",
        'negative': "{feat} shows overbought extremes, indicating mean-reversion risk that threatens {target} sustainability."
    },
    'correlation_diversification': {
        'positive': "{feat} provides diversification benefits, with low correlation to market factors enhancing portfolio {target} efficiency.",
        'negative': "{feat} increases concentration risk, with high correlation to market factors reducing portfolio {target} diversification."
    },
    'cyclical_positioning': {
        'positive': "{feat} benefits from favorable cyclical positioning, with sector rotation and economic cycle tailwinds boosting {target}.",
        'negative': "{feat} faces cyclical headwinds, with sector rotation and economic cycle downturn pressuring {target}."
    },
    'technical_breakout': {
        'positive': "{feat} confirms technical breakout, with price action clearing key resistance levels to support {target} upside.",
        'negative': "{feat} signals technical breakdown, with price action breaching support levels to threaten {target} downside."
    }
}

def classify_feature_type(feature_name: str) -> str:
    """
    Classify feature into narrative category.
    
    Args:
        feature_name: Feature name (e.g., 'momentum_20', 'pe_ratio')
        
    Returns:
        Feature type ('momentum', 'fundamental', etc.) or 'generic'
    """
    feature_lower = feature_name.lower()
    
    for ftype, patterns in FEATURE_TYPE_PATTERNS.items():
        for pattern in patterns:
            if pattern in feature_lower:
                return ftype
    
    return 'generic'

def select_narrative_template(feature_name: str, shap_value: float) -> str:
    """
    Select appropriate narrative template based on feature type.
    
    Args:
        feature_name: Feature name
        shap_value: SHAP contribution value
        
    Returns:
        Template key for NARRATIVE_TEMPLATES
    """
    ftype = classify_feature_type(feature_name)
    direction = 'positive' if shap_value > 0 else 'negative'
    
    # Map feature types to narrative templates
    template_map = {
        'momentum': 'growth_momentum',
        'volatility': 'volatility_risk',
        'fundamental': 'fundamental_strength',
        'sentiment': 'sentiment_catalyst',
        'factor': 'factor_exposure',
        'volume': 'volume_liquidity',
        'macroeconomic': 'macroeconomic_tailwind',
        'generic': 'technical_breakout'  # Default to technical narrative
    }
    
    template_key = template_map.get(ftype, 'technical_breakout')
    
    # Special logic for extreme values
    abs_shap = abs(shap_value)
    if abs_shap > 0.15:
        # Very strong signal → use aggressive or defensive templates
        if shap_value > 0:
            template_key = 'aggressive_growth'
        else:
            template_key = 'defensive_quality'
    elif abs_shap < 0.03:
        # Weak signal → use diversification template
        template_key = 'correlation_diversification'
    
    return template_key

# ============================================================================
# MOCK SHAP VALUE GENERATOR
# ============================================================================

class MockSHAPEngine:
    """
    Simulates SHAP-like explanations for portfolio predictions.
    
    Uses deterministic seed-based generation for reproducibility.
    In Phase 2, this will be replaced with real Azure ML SHAP outputs.
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize mock SHAP engine.
        
        Args:
            seed: Random seed for reproducibility (None = use ticker hash)
        """
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        logger.info(f"🧠 MockSHAPEngine initialized (seed={seed})")
    
    def _get_ticker_seed(self, ticker: str) -> int:
        """Generate deterministic seed from ticker symbol."""
        return int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
    
    def compute_feature_importance(
        self,
        ticker: str,
        features: Optional[List[str]] = None,
        top_n: int = 10
    ) -> pd.DataFrame:
        """
        Compute SHAP-like feature importance for a ticker.
        
        Args:
            ticker: Ticker symbol
            features: List of feature names (None = use all)
            top_n: Number of top features to return
            
        Returns:
            DataFrame with columns [feature, shap_value, abs_shap_value, contribution_pct]
        """
        if features is None:
            features = ALL_FEATURES
        
        # Use ticker-specific seed for deterministic output
        ticker_seed = self._get_ticker_seed(ticker)
        local_rng = np.random.RandomState(ticker_seed)
        
        # Generate SHAP values with realistic distribution
        # Higher variance for technical indicators, lower for fundamentals
        shap_values = []
        for feat in features:
            if feat in FEATURE_GROUPS['technical']:
                base_std = 0.15
            elif feat in FEATURE_GROUPS['fundamental']:
                base_std = 0.08
            elif feat in FEATURE_GROUPS['factors']:
                base_std = 0.12
            else:
                base_std = 0.10
            
            shap_val = local_rng.normal(0, base_std)
            shap_values.append(shap_val)
        
        # Create DataFrame
        df = pd.DataFrame({
            'feature': features,
            'shap_value': shap_values,
            'abs_shap_value': np.abs(shap_values)
        })
        
        # Sort by absolute value
        df = df.sort_values('abs_shap_value', ascending=False)
        
        # Add contribution percentage
        total_abs = df['abs_shap_value'].sum()
        df['contribution_pct'] = (df['abs_shap_value'] / total_abs * 100) if total_abs > 0 else 0
        
        # Return top N
        result = df.head(top_n).reset_index(drop=True)
        
        logger.debug(f"📊 Computed feature importance for {ticker}: {len(result)} features")
        return result
    
    def generate_summary_plot_data(
        self,
        tickers: List[str],
        features: Optional[List[str]] = None,
        top_n: int = 15
    ) -> Dict:
        """
        Generate data for SHAP summary plot (beeswarm/violin plot).
        
        Args:
            tickers: List of ticker symbols
            features: Feature names (None = auto-select)
            top_n: Number of features to show
            
        Returns:
            Dictionary with plot data ready for matplotlib/plotly
        """
        if features is None:
            # Auto-select most important features across portfolio
            all_importances = []
            for ticker in tickers[:5]:  # Sample first 5 for efficiency
                imp = self.compute_feature_importance(ticker, top_n=20)
                all_importances.append(imp)
            
            # Aggregate and pick top features
            combined = pd.concat(all_importances)
            top_features = (combined.groupby('feature')['abs_shap_value']
                           .mean()
                           .sort_values(ascending=False)
                           .head(top_n)
                           .index.tolist())
            features = top_features
        
        # Compute SHAP values for all tickers
        shap_matrix = []
        for ticker in tickers:
            ticker_seed = self._get_ticker_seed(ticker)
            local_rng = np.random.RandomState(ticker_seed)
            
            ticker_shaps = {}
            for feat in features:
                # Similar distribution as compute_feature_importance
                if feat in FEATURE_GROUPS['technical']:
                    base_std = 0.15
                elif feat in FEATURE_GROUPS['fundamental']:
                    base_std = 0.08
                else:
                    base_std = 0.10
                
                ticker_shaps[feat] = local_rng.normal(0, base_std)
            
            shap_matrix.append(ticker_shaps)
        
        # Convert to DataFrame
        shap_df = pd.DataFrame(shap_matrix, index=tickers)
        
        # Prepare plot data
        plot_data = {
            'features': features,
            'tickers': tickers,
            'shap_values': shap_df.values,  # Shape: (n_tickers, n_features)
            'feature_names': features,
            'mean_abs_shap': shap_df.abs().mean().sort_values(ascending=False).to_dict()
        }
        
        logger.info(f"📈 Generated summary plot data: {len(tickers)} tickers × {len(features)} features")
        return plot_data
    
    def generate_textual_rationale(
        self,
        ticker: str,
        prediction_value: float,
        prediction_target: str = 'return',
        top_n: int = 5,
        use_narrative_templates: bool = True
    ) -> str:
        """
        Generate human-readable explanation of prediction.
        
        Phase 2.5 Enhancement: Adds narrative templates based on feature types
        for richer, context-aware explanations.
        
        Args:
            ticker: Ticker symbol
            prediction_value: Predicted value (e.g., 0.05 for 5% return)
            prediction_target: What is being predicted ('return' or 'volatility')
            top_n: Number of features to mention
            use_narrative_templates: If True, use Phase 2.5 narrative templates;
                                      if False, use basic contribution templates
            
        Returns:
            Textual explanation string with Markdown formatting
        """
        # Get feature importance
        importance = self.compute_feature_importance(ticker, top_n=top_n)
        
        # Build explanation header
        direction = "higher" if prediction_value > 0 else "lower"
        magnitude = abs(prediction_value)
        
        if prediction_target == 'return':
            target_name = "expected return"
            pred_str = f"{prediction_value*100:+.2f}%"
        else:
            target_name = "volatility"
            pred_str = f"{prediction_value*100:.2f}%"
        
        explanation_parts = [
            f"**Prediction for {ticker}:** {direction.capitalize()} {target_name} of {pred_str}.",
            "",
            "**Key Contributing Factors:**",
            ""
        ]
        
        # Generate feature-level explanations
        for i, (idx, row) in enumerate(importance.iterrows(), start=1):
            feat = row['feature']
            shap_val = row['shap_value']
            contrib_pct = row['contribution_pct']
            
            # Format feature name (replace underscores, title case)
            feat_display = feat.replace('_', ' ').title()
            
            if use_narrative_templates:
                # Phase 2.5: Use context-aware narrative templates
                template_key = select_narrative_template(feat, shap_val)
                direction_key = 'positive' if shap_val > 0 else 'negative'
                
                # Get narrative template
                narrative = NARRATIVE_TEMPLATES.get(template_key, {})
                contribution_text = narrative.get(direction_key, "impacts predicted {target}")
                contribution_text = contribution_text.format(
                    feat=feat_display,
                    target=target_name
                )
            else:
                # Original: Use basic contribution templates
                abs_shap = abs(shap_val)
                if abs_shap > 0.10:
                    level = 'high'
                elif abs_shap > 0.05:
                    level = 'medium'
                else:
                    level = 'low'
                
                direction_key = 'positive' if shap_val > 0 else 'negative'
                template_key = f"{level}_{direction_key}"
                
                contribution_text = CONTRIBUTION_TEMPLATES.get(template_key, "impacts predicted {target}")
                contribution_text = contribution_text.format(target=target_name)
                
                # Prepend feature name for basic templates
                contribution_text = f"**{feat_display}**: {contribution_text}"
            
            # Build bullet point using enumerate counter
            if use_narrative_templates:
                explanation_parts.append(
                    f"{i}. {contribution_text} *({contrib_pct:.1f}% contribution)*"
                )
            else:
                explanation_parts.append(
                    f"{i}. {contribution_text} ({contrib_pct:.1f}% importance)"
                )
        
        # Add summary footer
        total_contribution = importance['contribution_pct'].sum()
        explanation_parts.extend([
            "",
            f"_These {top_n} factors collectively account for {total_contribution:.1f}% of the prediction confidence._"
        ])
        
        if use_narrative_templates:
            explanation_parts.append(
                "_Phase 2.5 narrative templates provide context-aware feature interpretation._"
            )
        
        return "\n".join(explanation_parts)


# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def create_feature_importance_bar_chart(
    importance_df: pd.DataFrame,
    ticker: str,
    output_path: Optional[Path] = None
) -> Optional[str]:
    """
    Create matplotlib bar chart of feature importance.
    
    Args:
        importance_df: DataFrame from compute_feature_importance()
        ticker: Ticker symbol
        output_path: Where to save (None = return as base64)
        
    Returns:
        File path or base64 string (if matplotlib available)
    """
    if not MATPLOTLIB_AVAILABLE:
        logger.warning("matplotlib not available - skipping bar chart")
        return None
    
    # Type guard ensures plt is available
    fig, ax = plt.subplots(figsize=(10, 6))  # type: ignore[possibly-unbound]
    
    # Color by positive/negative
    colors = ['green' if x > 0 else 'red' for x in importance_df['shap_value']]
    
    # Horizontal bar chart
    y_pos = np.arange(len(importance_df))
    ax.barh(y_pos, importance_df['shap_value'], color=colors, alpha=0.7)
    
    # Labels
    ax.set_yticks(y_pos)
    ax.set_yticklabels(importance_df['feature'].str.replace('_', ' ').str.title())
    ax.set_xlabel('SHAP Value (Impact on Prediction)', fontsize=12)
    ax.set_title(f'Feature Importance: {ticker}', fontsize=14, fontweight='bold')
    ax.axvline(x=0, color='black', linestyle='--', linewidth=0.8)
    
    plt.tight_layout()  # type: ignore[possibly-unbound]
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')  # type: ignore[possibly-unbound]
        plt.close()  # type: ignore[possibly-unbound]
        logger.info(f"💾 Saved feature importance chart: {output_path}")
        return str(output_path)
    else:
        # Return as base64 (for embedding in HTML)
        import io
        import base64
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')  # type: ignore[possibly-unbound]
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()  # type: ignore[possibly-unbound]
        return f"data:image/png;base64,{img_base64}"


def create_plotly_feature_importance(
    importance_df: pd.DataFrame,
    ticker: str
) -> Optional['go.Figure']:  # type: ignore[name-defined]
    """
    Create interactive Plotly feature importance chart.
    
    Args:
        importance_df: DataFrame from compute_feature_importance()
        ticker: Ticker symbol
        
    Returns:
        Plotly Figure object (if plotly available)
    """
    if not PLOTLY_AVAILABLE:
        logger.warning("plotly not available - skipping interactive chart")
        return None
    
    # Type guard ensures go is available
    
    # Sort by SHAP value for visual clarity
    df_sorted = importance_df.sort_values('shap_value')
    
    # Color by positive/negative
    colors = ['green' if x > 0 else 'red' for x in df_sorted['shap_value']]
    
    fig = go.Figure()  # type: ignore[possibly-unbound]
    
    fig.add_trace(go.Bar(  # type: ignore[possibly-unbound]
        y=df_sorted['feature'].str.replace('_', ' ').str.title(),
        x=df_sorted['shap_value'],
        orientation='h',
        marker=dict(color=colors),
        text=df_sorted['contribution_pct'].apply(lambda x: f"{x:.1f}%"),
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>SHAP Value: %{x:.4f}<br>Contribution: %{text}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(
            text=f"Feature Importance: {ticker}",
            font=dict(size=16, color='#000000')
        ),
        xaxis=dict(
            title="SHAP Value (Impact on Prediction)",
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='black'
        ),
        yaxis=dict(title=""),
        height=400,
        margin=dict(l=150, r=50, t=50, b=50),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color='#000000')
    )
    
    logger.info(f"📊 Created Plotly feature importance chart: {ticker}")
    return fig


# ============================================================================
# MAIN EXPLAINABILITY API
# ============================================================================

def generate_explanation(
    ticker: str,
    prediction_value: float,
    prediction_target: str = 'return',
    top_n_features: int = 10,
    output_dir: Optional[Path] = None
) -> Dict:
    """
    Generate complete explanation package for a prediction.
    
    This is the main entry point for the explainability engine.
    
    Args:
        ticker: Ticker symbol
        prediction_value: Predicted value
        prediction_target: 'return' or 'volatility'
        top_n_features: Number of features to explain
        output_dir: Where to save plots (None = in-memory only)
        
    Returns:
        Dictionary containing:
        - feature_importance: DataFrame
        - textual_rationale: String
        - plot_path: Path to saved plot (if output_dir provided)
        - plotly_figure: Plotly figure object (if available)
        - metadata: Timestamp, ticker, etc.
    """
    logger.info(f"🔍 Generating explanation for {ticker} (target={prediction_target}, value={prediction_value})")
    
    # Initialize mock engine
    engine = MockSHAPEngine()
    
    # Compute feature importance
    importance = engine.compute_feature_importance(ticker, top_n=top_n_features)
    
    # Generate textual rationale
    rationale = engine.generate_textual_rationale(
        ticker, prediction_value, prediction_target, top_n=top_n_features
    )
    
    # Create visualizations
    plot_path = None
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        plot_file = output_dir / f"feature_importance_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plot_path = create_feature_importance_bar_chart(importance, ticker, plot_file)
    
    plotly_fig = create_plotly_feature_importance(importance, ticker)
    
    # Assemble result
    result = {
        'ticker': ticker,
        'prediction_value': prediction_value,
        'prediction_target': prediction_target,
        'feature_importance': importance.to_dict('records'),
        'textual_rationale': rationale,
        'plot_path': str(plot_path) if plot_path else None,
        'plotly_figure': plotly_fig,
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'engine_version': '1.0.0-mock',
            'top_n_features': top_n_features,
            'total_features_analyzed': len(ALL_FEATURES)
        }
    }
    
    logger.info(f"✅ Explanation generated for {ticker}")
    return result


# ============================================================================
# PHASE 2: CACHING WRAPPER & CALLBACK INTEGRATION
# ============================================================================

# Cache configuration
_cache_stats = {
    'hits': 0,
    'misses': 0,
    'total_calls': 0,
    'last_reset': datetime.now().isoformat()
}

def _get_cache_key(ticker: str, prediction_value: float, target: str, top_n: int) -> str:
    """Generate deterministic cache key for explanation."""
    return f"{ticker}|{prediction_value:.4f}|{target}|{top_n}"


@lru_cache(maxsize=5)
def _cached_generate_explanation(
    cache_key: str,
    ticker: str,
    prediction_value: float,
    target: str,
    top_n: int
) -> Dict:
    """
    Internal cached wrapper for generate_explanation().
    
    Uses cache_key as first argument to make LRU cache work with hashable key.
    Actual parameters are passed separately for function execution.
    """
    return generate_explanation(
        ticker=ticker,
        prediction_value=prediction_value,
        prediction_target=target,
        top_n_features=top_n,
        output_dir=None  # No file artifacts in cached mode
    )


def generate_explanation_summary(
    ticker: str,
    prediction_value: float,
    prediction_target: str = 'return',
    top_n_features: int = 10,
    use_cache: bool = True
) -> Dict:
    """
    Generate explanation with optional caching (Phase 2 callback-friendly wrapper).
    
    This is the PRIMARY interface for UI callbacks. It provides:
    - LRU caching for last 5 explanations (improves responsiveness)
    - Performance logging (cache hit/miss tracking)
    - Graceful fallback if caching disabled
    
    Args:
        ticker: Stock symbol (e.g., 'AAPL')
        prediction_value: Predicted return or volatility
        prediction_target: What's being predicted ('return', 'volatility', 'sharpe')
        top_n_features: Number of top features to show
        use_cache: Whether to use LRU cache (default True)
        
    Returns:
        Explanation dictionary with:
        - ticker, prediction_value, prediction_target
        - feature_importance: List of {feature, importance, direction}
        - textual_rationale: Markdown explanation
        - plotly_chart: Plotly Figure object (if plotly available)
        - metadata: timestamp, cache_hit, generation_time_ms
        
    Example:
        >>> result = generate_explanation_summary('AAPL', 0.08, 'return', 10)
        >>> print(result['textual_rationale'])
        >>> fig = result.get('plotly_chart')
        >>> if fig: fig.show()
    """
    global _cache_stats
    
    start_time = time.perf_counter()
    cache_key = _get_cache_key(ticker, prediction_value, prediction_target, top_n_features)
    _cache_stats['total_calls'] += 1
    
    if use_cache:
        # Check if this will be a cache hit (cache_info not directly accessible)
        # We'll detect this by measuring execution time
        result = _cached_generate_explanation(
            cache_key, ticker, prediction_value, prediction_target, top_n_features
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        # Heuristic: <10ms = likely cache hit, >50ms = likely cache miss
        is_cache_hit = elapsed_ms < 10
        if is_cache_hit:
            _cache_stats['hits'] += 1
        else:
            _cache_stats['misses'] += 1
            
        cache_info = _cached_generate_explanation.cache_info()
        logger.info(
            f"{'🎯 Cache HIT' if is_cache_hit else '⏱️  Cache MISS'} for {ticker} "
            f"({elapsed_ms:.1f}ms) | Cache: {cache_info.hits}/{cache_info.hits + cache_info.misses} hits"
        )
    else:
        # Direct call without caching
        result = generate_explanation(
            ticker=ticker,
            prediction_value=prediction_value,
            prediction_target=prediction_target,
            top_n_features=top_n_features,
            output_dir=None
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        is_cache_hit = False
        _cache_stats['misses'] += 1
        logger.info(f"🔄 No-cache mode for {ticker} ({elapsed_ms:.1f}ms)")
    
    # Augment metadata with cache stats
    if 'metadata' not in result:
        result['metadata'] = {}
    result['metadata']['cache_hit'] = is_cache_hit
    result['metadata']['generation_time_ms'] = round(elapsed_ms, 2)
    result['metadata']['cache_stats'] = dict(_cache_stats)
    
    return result


def get_cache_stats() -> Dict:
    """
    Get current cache performance statistics.
    
    Returns:
        Dictionary with hits, misses, hit_rate, total_calls, last_reset
    """
    total = _cache_stats['total_calls']
    hit_rate = (_cache_stats['hits'] / total * 100) if total > 0 else 0.0
    
    cache_info = _cached_generate_explanation.cache_info()
    
    return {
        'hits': _cache_stats['hits'],
        'misses': _cache_stats['misses'],
        'hit_rate_percent': round(hit_rate, 1),
        'total_calls': total,
        'last_reset': _cache_stats['last_reset'],
        'lru_cache_info': {
            'hits': cache_info.hits,
            'misses': cache_info.misses,
            'maxsize': cache_info.maxsize,
            'currsize': cache_info.currsize
        }
    }


def reset_cache_stats() -> None:
    """Reset cache statistics (useful for testing)."""
    global _cache_stats
    _cache_stats = {
        'hits': 0,
        'misses': 0,
        'total_calls': 0,
        'last_reset': datetime.now().isoformat()
    }
    _cached_generate_explanation.cache_clear()
    logger.info("🔄 Cache stats reset")


# ============================================================================
# BATCH PROCESSING
# ============================================================================

def generate_batch_explanations(
    predictions: List[Dict],
    output_dir: Optional[Path] = None
) -> List[Dict]:
    """
    Generate explanations for multiple predictions.
    
    Args:
        predictions: List of dicts with keys [ticker, value, target]
        output_dir: Where to save artifacts
        
    Returns:
        List of explanation dictionaries
    """
    logger.info(f"🔄 Generating batch explanations for {len(predictions)} predictions")
    
    results = []
    for pred in predictions:
        try:
            explanation = generate_explanation(
                ticker=pred['ticker'],
                prediction_value=pred['value'],
                prediction_target=pred.get('target', 'return'),
                top_n_features=pred.get('top_n', 10),
                output_dir=output_dir
            )
            results.append(explanation)
        except Exception as e:
            logger.exception(f"Failed to explain {pred.get('ticker', 'UNKNOWN')}: {e}")
            results.append({
                'ticker': pred.get('ticker', 'UNKNOWN'),
                'error': str(e),
                'metadata': {'timestamp': datetime.now().isoformat()}
            })
    
    logger.info(f"✅ Batch complete: {len(results)} explanations generated")
    return results


logger.info("✓ Explainability Engine loaded (Phase 2 - Mock Mode + Caching)")

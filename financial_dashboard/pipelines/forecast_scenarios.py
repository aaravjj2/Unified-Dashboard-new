"""
pipelines/forecast_scenarios.py

Scenario analysis for market forecasts - test model predictions under different
macroeconomic conditions.

This pipeline:
1. Loads baseline forecast predictions
2. Accepts scenario parameters (VIX delta, treasury rates, oil price changes, etc.)
3. Applies deltas to relevant features
4. Reruns predictions with perturbed features
5. Computes scenario impact (winners/losers, ranking changes)
6. Saves scenario results for UI display

Usage:
    python pipelines/forecast_scenarios.py \\
        --baseline outputs/forecast_baseline.json \\
        --scenario vix_spike \\
        --vix_delta +10 \\
        --output outputs/forecast_scenario_vix_spike.json
    
    # Or with custom deltas
    python pipelines/forecast_scenarios.py \\
        --baseline outputs/forecast_baseline.json \\
        --scenario custom \\
        --vix_delta +5 \\
        --tnx_delta +0.5 \\
        --oil_delta -10 \\
        --output outputs/forecast_scenario_custom.json
"""

import os
import sys
import argparse
import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Add key names helper import
from financial_dashboard import key_names as KN

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Predefined Scenarios
# ============================================================================

PREDEFINED_SCENARIOS = {
    'vix_spike': {
        'name': 'VIX Spike (+10)',
        'description': 'Market volatility increases by 10 points',
        'deltas': {
            'vix': +10.0,
            'vix_30d': +8.0,
            'vix_60d': +6.0,
        }
    },
    'vix_calm': {
        'name': 'VIX Calm (-5)',
        'description': 'Market volatility decreases by 5 points',
        'deltas': {
            'vix': -5.0,
            'vix_30d': -4.0,
            'vix_60d': -3.0,
        }
    },
    'rates_up': {
        'name': 'Rates Up (+0.5%)',
        'description': '10Y treasury yields increase by 50 bps',
        'deltas': {
            'tnx': +0.5,
            'treasury_10y': +0.5,
            'rates_1m': +0.3,
            'rates_3m': +0.4,
        }
    },
    'rates_down': {
        'name': 'Rates Down (-0.5%)',
        'description': '10Y treasury yields decrease by 50 bps',
        'deltas': {
            'tnx': -0.5,
            'treasury_10y': -0.5,
            'rates_1m': -0.3,
            'rates_3m': -0.4,
        }
    },
    'oil_shock': {
        'name': 'Oil Shock (+20%)',
        'description': 'Oil prices increase by 20%',
        'deltas': {
            'oil_price': +20.0,  # Percentage change
            'energy_sector': +10.0,
        }
    },
    'oil_crash': {
        'name': 'Oil Crash (-30%)',
        'description': 'Oil prices decrease by 30%',
        'deltas': {
            'oil_price': -30.0,  # Percentage change
            'energy_sector': -15.0,
        }
    },
    'risk_on': {
        'name': 'Risk On',
        'description': 'Bullish macro environment',
        'deltas': {
            'vix': -5.0,
            'spy_momentum': +5.0,
            'qqq_momentum': +6.0,
            'credit_spreads': -0.2,
        }
    },
    'risk_off': {
        'name': 'Risk Off',
        'description': 'Bearish macro environment',
        'deltas': {
            'vix': +8.0,
            'spy_momentum': -5.0,
            'qqq_momentum': -6.0,
            'credit_spreads': +0.3,
        }
    },
}


# ============================================================================
# Feature Perturbation Logic
# ============================================================================

def apply_feature_deltas(
    features_df: pd.DataFrame,
    deltas: dict,
    mode: str = 'additive'
) -> pd.DataFrame:
    """
    Apply delta adjustments to feature columns.
    Uses canonical key matching from `financial_dashboard.key_names` to locate
    relevant columns robustly (handles many variants and aliases).
    """
    df = features_df.copy()

    for feature_pattern, delta in deltas.items():
        # Use canonical key matching first
        canonical = feature_pattern
        # If an alias was provided, map to canonical
        mapped = KN.map_column_to_canonical(str(feature_pattern))
        if mapped:
            canonical = mapped

        # Find matching columns via KN helpers
        matching_cols = KN.find_matching_columns(df.columns, canonical)

        # Fallback: try substring match if KN didn't find anything
        if not matching_cols:
            matching_cols = [
                col for col in df.columns
                if str(feature_pattern).lower() in col.lower()
            ]

        if not matching_cols:
            logger.warning(f"No columns found matching pattern/canonical: {feature_pattern} -> {canonical}")
            continue

        for col in matching_cols:
            try:
                if mode == 'additive':
                    df[col] = df[col] + delta
                elif mode == 'multiplicative':
                    # delta is percentage change
                    df[col] = df[col] * (1.0 + delta / 100.0)
                else:
                    raise ValueError(f"Invalid mode: {mode}")

                logger.info(
                    f"Applied {mode} delta to {col}: "
                    f"original mean={features_df[col].mean():.3f}, "
                    f"new mean={df[col].mean():.3f}"
                )
            except Exception as e:
                logger.error(f"Error applying delta to {col}: {e}")

    return df


def load_model_and_features(
    model_path: str,
    features_path: str
) -> tuple:
    """
    Load trained model and feature data.

    Returns:
        Tuple of (model, features_df, feature_names)
    """
    import joblib

    # Load model
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")

    model_obj = joblib.load(model_path)
    # If the loaded object is a pointer/dict (like weekly_model_latest), resolve
    if isinstance(model_obj, dict) and model_obj.get('path'):
        try:
            model_obj = joblib.load(model_obj.get('path'))
        except Exception:
            # try to fall back to whatever was stored
            pass

    model = model_obj
    logger.info(f"Loaded model from {model_path}")

    # Load features
    if not os.path.exists(features_path):
        raise FileNotFoundError(f"Features not found: {features_path}")

    if features_path.endswith('.parquet'):
        features_df = pd.read_parquet(features_path)
    elif features_path.endswith('.csv'):
        features_df = pd.read_csv(features_path)
    else:
        raise ValueError(f"Unsupported features format: {features_path}")

    # Extract feature names (try multiple attributes)
    feature_names = None
    try:
        if hasattr(model, 'feature_name_'):
            feature_names = list(model.feature_name_)
        elif hasattr(model, 'feature_names_in_'):
            feature_names = list(model.feature_names_in_)
    except Exception:
        feature_names = None

    # If we still don't have feature_names, infer numeric columns excluding common ids
    if not feature_names:
        exclude_cols = ['ticker', 'date', 'target', 'returns_1m', 'returns_1w']
        feature_names = [
            col for col in features_df.columns
            if col not in exclude_cols and pd.api.types.is_numeric_dtype(features_df[col])
        ]

    logger.info(f"Loaded features: {len(features_df)} rows, {len(feature_names)} features")

    return model, features_df, feature_names


def run_scenario_predictions(
    model,
    features_df: pd.DataFrame,
    feature_names: list,
    deltas: dict,
    mode: str = 'additive'
) -> pd.DataFrame:
    """
    Run predictions under scenario perturbations.

    Returns:
        DataFrame with columns [ticker, baseline_pred, scenario_pred, delta_pred, delta_pct]
    """
    # Apply feature deltas
    perturbed_features = apply_feature_deltas(features_df, deltas, mode)

    # Extract feature matrix
    X_baseline = features_df[feature_names].values
    X_scenario = perturbed_features[feature_names].values

    # Make predictions
    try:
        baseline_preds = model.predict(X_baseline)
    except Exception:
        # fallback: try to coerce to 1d numpy array
        baseline_preds = pd.Series(model.predict(X_baseline)).values
    try:
        scenario_preds = model.predict(X_scenario)
    except Exception:
        scenario_preds = pd.Series(model.predict(X_scenario)).values

    # Compute deltas
    delta_preds = scenario_preds - baseline_preds
    # safe percent change: avoid division by zero
    baseline_abs = np.abs(baseline_preds)
    eps = 1e-9
    with np.errstate(divide='ignore', invalid='ignore'):
        delta_pct = np.where(baseline_abs < eps, np.nan, (delta_preds / baseline_abs) * 100.0)

    # Build results DataFrame
    results = pd.DataFrame({
        'ticker': features_df['ticker'] if 'ticker' in features_df.columns else range(len(baseline_preds)),
        'baseline_pred': baseline_preds,
        'scenario_pred': scenario_preds,
        'delta_pred': delta_preds,
        'delta_pct': delta_pct,
    })

    # Add rankings
    results['baseline_rank'] = results['baseline_pred'].rank(ascending=False, method='min')
    results['scenario_rank'] = results['scenario_pred'].rank(ascending=False, method='min')
    results['rank_change'] = results['baseline_rank'] - results['scenario_rank']

    return results


# ============================================================================
# Analysis & Reporting
# ============================================================================

def compute_scenario_metrics(results_df: pd.DataFrame) -> dict:
    """
    Compute aggregate metrics for scenario analysis.
    
    Returns:
        Dict with summary statistics
    """
    metrics = {
        'n_tickers': len(results_df),
        'avg_delta_pred': float(results_df['delta_pred'].mean()),
        'median_delta_pred': float(results_df['delta_pred'].median()),
        'std_delta_pred': float(results_df['delta_pred'].std()),
        'max_winner': {
            'ticker': results_df.loc[results_df['delta_pred'].idxmax(), 'ticker'],
            'delta': float(results_df['delta_pred'].max()),
        },
        'max_loser': {
            'ticker': results_df.loc[results_df['delta_pred'].idxmin(), 'ticker'],
            'delta': float(results_df['delta_pred'].min()),
        },
        'biggest_rank_jump': {
            'ticker': results_df.loc[results_df['rank_change'].idxmax(), 'ticker'],
            'rank_change': int(results_df['rank_change'].max()),
        },
        'biggest_rank_drop': {
            'ticker': results_df.loc[results_df['rank_change'].idxmin(), 'ticker'],
            'rank_change': int(results_df['rank_change'].min()),
        },
    }
    
    # Top movers
    top_n = min(10, len(results_df))
    
    metrics['top_winners'] = results_df.nlargest(top_n, 'delta_pred')[
        ['ticker', 'baseline_pred', 'scenario_pred', 'delta_pred', 'rank_change']
    ].to_dict('records')
    
    metrics['top_losers'] = results_df.nsmallest(top_n, 'delta_pred')[
        ['ticker', 'baseline_pred', 'scenario_pred', 'delta_pred', 'rank_change']
    ].to_dict('records')
    
    return metrics


# ============================================================================
# Main Pipeline
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Run scenario analysis for market forecasts'
    )
    parser.add_argument(
        '--model',
        required=True,
        help='Path to trained model (.joblib or .pkl)'
    )
    parser.add_argument(
        '--features',
        required=True,
        help='Path to features DataFrame (.parquet or .csv)'
    )
    parser.add_argument(
        '--scenario',
        default='custom',
        help='Predefined scenario name or "custom" for manual deltas'
    )
    parser.add_argument(
        '--vix_delta',
        type=float,
        default=0.0,
        help='VIX delta (points)'
    )
    parser.add_argument(
        '--tnx_delta',
        type=float,
        default=0.0,
        help='10Y treasury delta (percentage points)'
    )
    parser.add_argument(
        '--oil_delta',
        type=float,
        default=0.0,
        help='Oil price delta (percent change)'
    )
    parser.add_argument(
        '--mode',
        default='additive',
        choices=['additive', 'multiplicative'],
        help='Delta application mode'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output path for scenario results (.json)'
    )
    
    args = parser.parse_args()
    
    # Determine deltas
    if args.scenario in PREDEFINED_SCENARIOS:
        scenario_config = PREDEFINED_SCENARIOS[args.scenario]
        deltas = scenario_config['deltas']
        scenario_name = scenario_config['name']
        scenario_desc = scenario_config['description']
        logger.info(f"Using predefined scenario: {scenario_name}")
    else:
        # Custom scenario from command-line args
        deltas = {}
        if args.vix_delta != 0:
            deltas['vix'] = args.vix_delta
        if args.tnx_delta != 0:
            deltas['tnx'] = args.tnx_delta
            deltas['treasury'] = args.tnx_delta
        if args.oil_delta != 0:
            deltas['oil'] = args.oil_delta
        
        scenario_name = 'Custom'
        scenario_desc = f"Custom scenario: VIX {args.vix_delta:+.1f}, TNX {args.tnx_delta:+.2f}, Oil {args.oil_delta:+.1f}%"
        logger.info(f"Using custom scenario: {scenario_desc}")
    
    if not deltas:
        logger.warning("No deltas specified! Results will match baseline.")
    
    # Load model and features
    logger.info("Loading model and features...")
    model, features_df, feature_names = load_model_and_features(
        args.model,
        args.features
    )
    
    # Run scenario predictions
    logger.info("Running scenario predictions...")
    results_df = run_scenario_predictions(
        model,
        features_df,
        feature_names,
        deltas,
        mode=args.mode
    )
    
    # Compute metrics
    logger.info("Computing scenario metrics...")
    metrics = compute_scenario_metrics(results_df)
    
    # Build output
    output = {
        'scenario': {
            'name': scenario_name,
            'description': scenario_desc,
            'deltas': deltas,
            'mode': args.mode,
        },
        'metadata': {
            'model': args.model,
            'features': args.features,
            'n_features': len(feature_names),
            'generated_at': datetime.now().isoformat(),
        },
        'metrics': metrics,
        'results': results_df.to_dict('records'),
    }
    
    # Save output
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    logger.info(f"Saved scenario results to {args.output}")
    
    # Print summary
    print("\n" + "="*80)
    print(f"SCENARIO ANALYSIS: {scenario_name}")
    print("="*80)
    print(f"Description: {scenario_desc}")
    print(f"\nTickers analyzed: {metrics['n_tickers']}")
    print(f"Average prediction delta: {metrics['avg_delta_pred']:.2%}")
    print(f"Median prediction delta: {metrics['median_delta_pred']:.2%}")
    
    print(f"\nBiggest Winner: {metrics['max_winner']['ticker']} "
          f"({metrics['max_winner']['delta']:+.2%})")
    print(f"Biggest Loser: {metrics['max_loser']['ticker']} "
          f"({metrics['max_loser']['delta']:+.2%})")
    
    print(f"\nTop 3 Winners:")
    for i, item in enumerate(metrics['top_winners'][:3], 1):
        print(f"  {i}. {item['ticker']}: {item['delta_pred']:+.2%} "
              f"(rank {item['rank_change']:+d})")
    
    print(f"\nTop 3 Losers:")
    for i, item in enumerate(metrics['top_losers'][:3], 1):
        print(f"  {i}. {item['ticker']}: {item['delta_pred']:+.2%} "
              f"(rank {item['rank_change']:+d})")
    
    print("="*80)


if __name__ == '__main__':
    main()

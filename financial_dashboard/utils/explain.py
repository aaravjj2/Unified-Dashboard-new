"""
utils/explain.py

SHAP-based model explainability utilities for monthly picks.

Functions:
- compute_shap_values: Compute SHAP values for predictions
- save_shap_explanations: Save SHAP values to JSON
- load_shap_explanations: Load SHAP values from JSON
- format_shap_for_ui: Format SHAP data for UI display
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import numpy as np

try:
    import shap
except (ImportError, AttributeError):
    shap = None
    logging.warning("SHAP library not installed or incompatible with current NumPy version. Explainability features will be disabled.")

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

EXPLAIN_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'explain')
os.makedirs(EXPLAIN_DIR, exist_ok=True)

TOP_N_FEATURES = 10  # Number of top features to save per pick


# ============================================================================
# SHAP Computation
# ============================================================================

def compute_shap_values(
    model: Any,
    features: np.ndarray,
    feature_names: List[str],
    model_type: str = 'tree'
) -> Optional[Dict]:
    """
    Compute SHAP values for a batch of predictions.
    
    Args:
        model: Trained model object (LightGBM, XGBoost, etc.)
        features: Feature matrix (n_samples x n_features)
        feature_names: List of feature names
        model_type: 'tree' for tree-based models, 'linear' for linear models
    
    Returns:
        Dict with SHAP values and base values, or None if SHAP unavailable
    """
    if shap is None:
        logger.warning("SHAP library unavailable - using sklearn feature importance fallback")
        return _compute_shap_values_fallback(model, features, feature_names)
    
    try:
        # Create appropriate explainer based on model type
        if model_type == 'tree':
            # TreeExplainer for tree-based models (LightGBM, XGBoost, RandomForest)
            explainer = shap.TreeExplainer(model)
        elif model_type == 'linear':
            # LinearExplainer for linear models
            explainer = shap.LinearExplainer(model, features)
        else:
            # KernelExplainer as fallback (slower but model-agnostic)
            logger.warning(f"Unknown model_type '{model_type}', using KernelExplainer (slow)")
            explainer = shap.KernelExplainer(model.predict, shap.sample(features, 100))
        
        # Compute SHAP values
        shap_values = explainer.shap_values(features)
        
        # Handle multi-output models (e.g., binary classification)
        if isinstance(shap_values, list):
            # For binary classification, use positive class
            shap_values = shap_values[1] if len(shap_values) == 2 else shap_values[0]
        
        # Get base value (expected value)
        if hasattr(explainer, 'expected_value'):
            base_value = explainer.expected_value
            if isinstance(base_value, (list, np.ndarray)):
                base_value = base_value[1] if len(base_value) == 2 else base_value[0]
        else:
            base_value = 0.0
        
        logger.info("✅ Computed SHAP values using SHAP library")
        return {
            'shap_values': shap_values,
            'base_value': base_value,
            'feature_names': feature_names
        }
    
    except Exception as e:
        logger.error(f"SHAP computation failed: {e}, falling back to sklearn")
        return _compute_shap_values_fallback(model, features, feature_names)


def _compute_shap_values_fallback(
    model: Any,
    features: np.ndarray,
    feature_names: List[str]
) -> Optional[Dict]:
    """
    Fallback SHAP computation using sklearn feature importances.
    
    When SHAP library is unavailable or fails, this creates SHAP-like
    explanations using feature importances from tree-based models.
    
    Args:
        model: Trained model with feature_importances_ attribute
        features: Feature matrix (n_samples x n_features)
        feature_names: List of feature names
    
    Returns:
        Dict with approximate SHAP values, or None if model unsupported
    """
    try:
        # Check if model has feature importances (tree-based models)
        if not hasattr(model, 'feature_importances_'):
            logger.error("Model does not support feature importances - cannot generate fallback SHAP")
            return None
        
        importances = model.feature_importances_
        
        # Generate predictions
        if hasattr(model, 'predict_proba'):
            predictions = model.predict_proba(features)
            if predictions.shape[1] == 2:
                predictions = predictions[:, 1]  # Binary classification: positive class
            else:
                predictions = predictions[:, 0]  # Multi-class: first class
        else:
            predictions = model.predict(features)
        
        # Approximate SHAP values: scale feature importances by prediction deviation
        base_value = float(np.mean(predictions))
        
        # For each sample, distribute the deviation from base across features proportional to importance
        shap_values = np.zeros((len(features), len(feature_names)))
        for i, pred in enumerate(predictions):
            deviation = pred - base_value
            # Distribute deviation proportionally to feature importances
            shap_values[i] = importances * deviation
        
        logger.info(f"✅ Computed fallback SHAP values using feature importances (approximation)")
        logger.info(f"   Base value: {base_value:.4f}, Predictions range: [{predictions.min():.4f}, {predictions.max():.4f}]")
        
        return {
            'shap_values': shap_values,
            'base_value': base_value,
            'feature_names': feature_names,
            'fallback_mode': True  # Flag to indicate this is an approximation
        }
    
    except Exception as e:
        logger.error(f"Fallback SHAP computation failed: {e}", exc_info=True)
        return None


# ============================================================================
# Explanation Persistence
# ============================================================================

def save_shap_explanations(
    shap_data: Dict,
    tickers: List[str],
    predictions: np.ndarray,
    date: Optional[str] = None
) -> str:
    """
    Save SHAP explanations to JSON file.
    
    Args:
        shap_data: Dict from compute_shap_values()
        tickers: List of ticker symbols
        predictions: Model predictions
        date: Date string (YYYYMMDD), defaults to today
    
    Returns:
        Path to saved file
    """
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    
    filename = f'picks_explain_{date}.json'
    filepath = os.path.join(EXPLAIN_DIR, filename)
    
    shap_values = shap_data['shap_values']
    base_value = shap_data['base_value']
    feature_names = shap_data['feature_names']
    
    # Build per-ticker explanations
    explanations = {}
    
    for i, ticker in enumerate(tickers):
        if i >= len(shap_values):
            continue
        
        # Get SHAP values for this ticker
        ticker_shap = shap_values[i]
        
        # Sort features by absolute SHAP value (importance)
        feature_importance = [(name, float(val)) for name, val in zip(feature_names, ticker_shap)]
        feature_importance.sort(key=lambda x: abs(x[1]), reverse=True)
        
        # Take top N features
        top_features = feature_importance[:TOP_N_FEATURES]
        
        # Validate: sum of SHAP values + base should ≈ prediction
        shap_sum = sum(ticker_shap)
        predicted = float(predictions[i]) if i < len(predictions) else None
        validation_diff = abs((base_value + shap_sum) - predicted) if predicted is not None else None
        
        explanations[ticker] = {
            'base_value': float(base_value),
            'prediction': predicted,
            'shap_sum': float(shap_sum),
            'validation_diff': float(validation_diff) if validation_diff is not None else None,
            'top_features': [
                {'feature': name, 'shap_value': val}
                for name, val in top_features
            ],
            'all_features': [
                {'feature': name, 'shap_value': float(val)}
                for name, val in zip(feature_names, ticker_shap)
            ]
        }
    
    # Save to JSON
    output = {
        'generated_at': datetime.now().isoformat(),
        'date': date,
        'model_type': 'tree',  # Could be parameterized
        'num_tickers': len(tickers),
        'num_features': len(feature_names),
        'explanations': explanations
    }
    
    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2)
    
    logger.info(f"Saved SHAP explanations to: {filepath}")
    return filepath


def load_shap_explanations(
    date: Optional[str] = None,
    tickers: Optional[List[str]] = None
) -> Optional[Dict]:
    """
    Load SHAP explanations from JSON file.
    Auto-generates missing SHAP data using get_or_generate_shap_data().
    
    Args:
        date: Date string (YYYYMMDD), defaults to most recent
        tickers: List of ticker symbols (for auto-generation if file missing)
    
    Returns:
        Dict with explanations or None if not found
    """
    if date:
        filename = f'picks_explain_{date}.json'
        filepath = os.path.join(EXPLAIN_DIR, filename)
    else:
        # Find most recent file
        files = [f for f in os.listdir(EXPLAIN_DIR) if f.startswith('picks_explain_') and f.endswith('.json')]
        if not files:
            logger.warning("No SHAP explanation files found - attempting auto-generation")
            return get_or_generate_shap_data(date, tickers=tickers)
        files.sort(reverse=True)
        filepath = os.path.join(EXPLAIN_DIR, files[0])
    
    if not os.path.exists(filepath):
        logger.warning(f"SHAP file not found: {filepath} - attempting auto-generation")
        return get_or_generate_shap_data(date, tickers=tickers)
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load SHAP explanations: {e}")
        return None


def get_or_generate_shap_data(
    date: Optional[str] = None,
    tickers: Optional[List[str]] = None,
    force_regenerate: bool = False
) -> Optional[Dict]:
    """
    Get SHAP data for date, auto-generating if missing.
    
    This is the primary entry point for SHAP data access. It will:
    1. Check if SHAP file exists for the date
    2. If not, attempt to load model and generate explanations
    3. Save generated explanations to disk
    4. Return the explanations dict
    
    PHASE 6 ENHANCEMENT: Supports full portfolio ticker list to generate
    SHAP explanations for all tickers, not just default 5.
    
    Args:
        date: Date string (YYYYMMDD), defaults to today
        tickers: List of ticker symbols to generate SHAP for (defaults to common stocks)
        force_regenerate: If True, regenerate even if file exists
    
    Returns:
        Dict with explanations or None if generation fails
    """
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    
    filename = f'picks_explain_{date}.json'
    filepath = os.path.join(EXPLAIN_DIR, filename)
    
    # Check if file already exists (unless force_regenerate)
    if os.path.exists(filepath) and not force_regenerate:
        try:
            with open(filepath, 'r') as f:
                existing_data = json.load(f)
                logger.info(f"✓ Loaded existing SHAP data: {filepath}")
                
                # PHASE 6: Check if existing data covers all requested tickers
                if tickers:
                    existing_tickers = set(existing_data.get('explanations', {}).keys())
                    requested_tickers = set([t.upper() for t in tickers])
                    missing_tickers = requested_tickers - existing_tickers
                    
                    if missing_tickers:
                        logger.warning(f"⚠️ Existing SHAP data missing {len(missing_tickers)} tickers: {missing_tickers}")
                        logger.info("Regenerating SHAP data to include all requested tickers...")
                        # Fall through to regeneration
                    else:
                        return existing_data
                else:
                    return existing_data
        except Exception as e:
            logger.warning(f"Failed to load existing SHAP file {filepath}: {e}")
    
    # File doesn't exist, is corrupted, or needs more tickers - generate new SHAP data
    ticker_info = f" for {len(tickers)} tickers" if tickers else ""
    logger.info(f"📊 Auto-generating SHAP explanations for date {date}{ticker_info}...")
    
    try:
        # Import model loader and data preparation utilities
        from utils.models import load_latest_model, get_mock_model
        from utils.data_prep import prepare_features_for_date
        
        # PHASE 6 FIX: Pass tickers to prepare_features_for_date
        features, feature_names, result_tickers = prepare_features_for_date(date, tickers=tickers)
        if features is None or len(features) == 0:
            logger.error(f"❌ No features available for date {date}")
            return _create_fallback_shap_data(date)
        
        if feature_names is None or result_tickers is None:
            logger.error(f"❌ Feature names or tickers missing for date {date}")
            return _create_fallback_shap_data(date)
        
        n_features = features.shape[1]
        logger.info(f"Prepared {len(features)} samples with {n_features} features each")
        logger.info(f"Tickers: {result_tickers}")
        
        # Load the trained model (try disk first, then mock with correct feature count)
        model = load_latest_model()
        if model is None:
            logger.warning(f"No trained model found on disk - using mock model with {n_features} features")
            model = get_mock_model(n_features=n_features)
        
        if model is None:
            logger.error("❌ No trained model or mock model available - cannot generate SHAP data")
            return _create_fallback_shap_data(date)
        
        # Generate predictions
        predictions = model.predict(features)
        
        # Compute SHAP values
        shap_data = compute_shap_values(
            model=model,
            features=features,
            feature_names=feature_names,
            model_type='tree'
        )
        
        if shap_data is None:
            logger.warning("⚠️ SHAP computation returned None - using fallback")
            return _create_fallback_shap_data(date)
        
        # Save SHAP explanations
        saved_path = save_shap_explanations(
            shap_data=shap_data,
            tickers=result_tickers,
            predictions=predictions,
            date=date
        )
        
        logger.info(f"✅ Generated new SHAP explanation for {date}: {saved_path}")
        logger.info(f"   Covered {len(result_tickers)} tickers with {n_features} features each")
        
        # Load and return the newly saved file
        with open(saved_path, 'r') as f:
            return json.load(f)
    
    except ImportError as e:
        logger.error(f"❌ Import error during SHAP generation: {e}")
        logger.info("💡 Hint: Ensure utils.models and utils.data_prep modules exist")
        return _create_fallback_shap_data(date)
    
    except Exception as e:
        logger.error(f"❌ Failed to auto-generate SHAP data: {e}", exc_info=True)
        return _create_fallback_shap_data(date)


def _create_fallback_shap_data(date: str) -> Dict:
    """
    Create minimal fallback SHAP data when generation fails.
    
    This ensures the UI doesn't crash when SHAP data is unavailable.
    
    Args:
        date: Date string (YYYYMMDD)
    
    Returns:
        Minimal dict with empty explanations
    """
    return {
        'generated_at': datetime.now().isoformat(),
        'date': date,
        'model_type': 'unavailable',
        'num_tickers': 0,
        'num_features': 0,
        'explanations': {},
        'status': 'fallback',
        'message': 'SHAP data unavailable - model or features not found'
    }


# ============================================================================
# UI Formatting
# ============================================================================

def format_shap_for_ui(ticker: str, date: Optional[str] = None) -> Optional[Dict]:
    """
    Format SHAP data for UI display.
    
    Args:
        ticker: Stock ticker symbol
        date: Date string (YYYYMMDD)
    
    Returns:
        Dict with formatted data for UI, or None if not found
    """
    data = load_shap_explanations(date)
    if not data or 'explanations' not in data:
        return None
    
    ticker_data = data['explanations'].get(ticker.upper())
    if not ticker_data:
        return None
    
    # Format for UI display
    return {
        'ticker': ticker,
        'prediction': ticker_data['prediction'],
        'base_value': ticker_data['base_value'],
        'top_features': ticker_data['top_features'],
        'validation': {
            'shap_sum': ticker_data['shap_sum'],
            'validation_diff': ticker_data['validation_diff'],
            'is_valid': abs(ticker_data['validation_diff']) < 0.01 if ticker_data['validation_diff'] is not None else True
        },
        'metadata': {
            'generated_at': data['generated_at'],
            'num_features_total': data['num_features']
        }
    }


def get_feature_groups(feature_names: List[str]) -> Dict[str, List[str]]:
    """
    Group features by category for organized display.
    
    Args:
        feature_names: List of all feature names
    
    Returns:
        Dict mapping category name to list of feature names
    """
    groups = {
        'Technical': [],
        'Momentum': [],
        'Volatility': [],
        'Volume': [],
        'Fundamental': [],
        'Relative Strength': [],
        'News/Sentiment': [],
        'Options': [],
        'Other': []
    }
    
    for name in feature_names:
        name_lower = name.lower()
        
        if any(x in name_lower for x in ['sma', 'ema', 'rsi', 'macd', 'bb_', 'stoch']):
            groups['Technical'].append(name)
        elif any(x in name_lower for x in ['mom', 'roc', 'momentum']):
            groups['Momentum'].append(name)
        elif any(x in name_lower for x in ['vol', 'atr', 'volatility']):
            groups['Volatility'].append(name)
        elif any(x in name_lower for x in ['volume', 'adv', 'vol_surge']):
            groups['Volume'].append(name)
        elif any(x in name_lower for x in ['pe', 'eps', 'revenue', 'earnings', 'profit']):
            groups['Fundamental'].append(name)
        elif any(x in name_lower for x in ['rel_', 'beta', 'corr']):
            groups['Relative Strength'].append(name)
        elif any(x in name_lower for x in ['news', 'sentiment', 'headline']):
            groups['News/Sentiment'].append(name)
        elif any(x in name_lower for x in ['option', 'iv', 'put_call']):
            groups['Options'].append(name)
        else:
            groups['Other'].append(name)
    
    # Remove empty groups
    return {k: v for k, v in groups.items() if v}


# ============================================================================
# Self-Test
# ============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("Testing explain.py module...\n")
    
    # Test 1: Check SHAP availability
    print("Test 1: SHAP availability")
    if shap:
        print(f"  ✓ SHAP version: {shap.__version__}")
    else:
        print("  ✗ SHAP not installed")
    print()
    
    # Test 2: Feature grouping
    print("Test 2: Feature grouping")
    test_features = [
        'sma_20', 'sma_50', 'rsi', 'macd_hist', 'bb_width',
        'momentum_12m', 'roc_3m', 'vol_60_ann', 'atr_14',
        'volume', 'avg_vol', 'vol_surge', 'pe_ratio', 'earnings_yield',
        'rel_strength', 'beta', 'news_sentiment', 'iv_rank', 'other_feature'
    ]
    groups = get_feature_groups(test_features)
    for group, features in groups.items():
        print(f"  {group}: {len(features)} features")
        if features:
            print(f"    {', '.join(features[:3])}{' ...' if len(features) > 3 else ''}")
    print()
    
    # Test 3: Mock SHAP data save/load
    print("Test 3: Mock SHAP data persistence")
    mock_shap_data = {
        'shap_values': np.random.randn(3, 5),  # 3 tickers, 5 features
        'base_value': 0.05,
        'feature_names': ['feat_1', 'feat_2', 'feat_3', 'feat_4', 'feat_5']
    }
    mock_tickers = ['AAPL', 'MSFT', 'GOOGL']
    mock_predictions = np.array([0.08, 0.06, 0.07])
    
    try:
        # Save
        test_date = '20250102'
        filepath = save_shap_explanations(mock_shap_data, mock_tickers, mock_predictions, test_date)
        print(f"  ✓ Saved to: {os.path.basename(filepath)}")
        
        # Load
        loaded = load_shap_explanations(test_date)
        if loaded:
            print(f"  ✓ Loaded {loaded['num_tickers']} explanations")
            
            # Format for UI
            ui_data = format_shap_for_ui('AAPL', test_date)
            if ui_data:
                print(f"  ✓ UI format for AAPL: {len(ui_data['top_features'])} top features")
                print(f"    Prediction: {ui_data['prediction']:.4f}")
                print(f"    Validation: {'✓' if ui_data['validation']['is_valid'] else '✗'}")
        
        # Cleanup test file
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"  ✓ Cleaned up test file")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    print()
    print("✅ Tests completed!")

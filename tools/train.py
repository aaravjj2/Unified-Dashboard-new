#!/usr/bin/env python3
"""
ML Training Driver Script
=========================
Phase 3 of ML Project Guide implementation.

Usage:
    python tools/train.py --config tools/train_config.yaml
    python tools/train.py --config tools/train_config.yaml --model xgboost
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import yaml
import pandas as pd
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ==============================================================================
# CONFIGURATION
# ==============================================================================

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config


# ==============================================================================
# DATA LOADING
# ==============================================================================

def load_data(config: Dict[str, Any]) -> pd.DataFrame:
    """Load and prepare training data."""
    from financial_dashboard.data.pipelines import build_snapshot, load_snapshot
    
    data_config = config['data']
    snapshot_name = f"train_{datetime.now().strftime('%Y%m%d')}"
    
    # Try to load existing snapshot
    snapshot_path = Path(data_config.get('snapshot_dir', 'data/snapshots')) / snapshot_name
    
    if snapshot_path.exists():
        logger.info(f"Loading snapshot from {snapshot_path}")
        return load_snapshot(snapshot_path).prices
    
    # Build new snapshot
    logger.info("Building new data snapshot")
    
    tickers = data_config.get('tickers', ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'])
    start_date = data_config.get('start_date', '2020-01-01')
    end_date = data_config.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    # Fetch data using yfinance
    try:
        import yfinance as yf
        
        all_data = []
        for ticker in tickers:
            logger.info(f"Fetching data for {ticker}")
            df = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
            if not df.empty:
                # Handle MultiIndex columns from yfinance
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df['ticker'] = ticker
                all_data.append(df)
        
        if all_data:
            data = pd.concat(all_data)
            logger.info(f"Loaded {len(data)} rows for {len(tickers)} tickers")
            return data
    except Exception as e:
        logger.warning(f"Could not fetch live data: {e}")
    
    # Generate synthetic data if no real data
    logger.info("Generating synthetic training data")
    return _generate_synthetic_data(tickers, start_date, end_date)


def _generate_synthetic_data(tickers: list, start_date: str, end_date: str) -> pd.DataFrame:
    """Generate synthetic OHLCV data for testing."""
    dates = pd.date_range(start_date, end_date, freq='B')
    
    all_data = []
    for ticker in tickers:
        np.random.seed(hash(ticker) % 2**32)
        n = len(dates)
        
        # Random walk prices
        returns = np.random.randn(n) * 0.02
        prices = 100 * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'Date': dates,
            'Open': prices * (1 + np.random.randn(n) * 0.005),
            'High': prices * (1 + np.abs(np.random.randn(n) * 0.01)),
            'Low': prices * (1 - np.abs(np.random.randn(n) * 0.01)),
            'Close': prices,
            'Adj Close': prices,
            'Volume': np.random.randint(1000000, 10000000, n),
            'ticker': ticker,
        })
        all_data.append(df)
    
    return pd.concat(all_data).set_index('Date')


# ==============================================================================
# FEATURE ENGINEERING
# ==============================================================================

def compute_features(data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """Compute all features."""
    from financial_dashboard.features.technical import compute_all_technical_features
    
    feature_config = config['features']
    
    all_features = []
    
    # Group by ticker
    grouped = data.groupby('ticker') if 'ticker' in data.columns else [(None, data)]
    
    for ticker, group in grouped:
        logger.info(f"Computing features for {ticker}")
        
        # Technical features
        if feature_config.get('technical', {}).get('enabled', True):
            tech_features = compute_all_technical_features(group)
            tech_features['ticker'] = ticker
            all_features.append(tech_features)
    
    if not all_features:
        logger.warning("No features computed")
        return pd.DataFrame()
    
    features = pd.concat(all_features)
    logger.info(f"Computed {len(features.columns)} features")
    
    return features


# ==============================================================================
# LABEL GENERATION
# ==============================================================================

def generate_labels(data: pd.DataFrame, config: Dict[str, Any]) -> pd.Series:
    """Generate training labels."""
    from financial_dashboard.models.labels import label_horizon_returns, label_multi_horizon, LabelType
    
    label_config = config.get('labels', {})
    target = label_config.get('target', 'return_5d')
    
    # Extract Close prices
    if 'Close' in data.columns:
        close = data['Close']
    elif 'Adj Close' in data.columns:
        close = data['Adj Close']
    else:
        close = data.iloc[:, 0]  # First column
    
    # Compute returns
    horizons = label_config.get('horizons', [5])
    
    if len(horizons) == 1:
        labels = label_horizon_returns(
            close,
            horizon_days=horizons[0],
            label_type=LabelType.TERNARY,
            threshold=label_config.get('threshold', 0.02),
        )
    else:
        labels = label_multi_horizon(close, horizons=horizons)
        labels = labels[f'label_{horizons[0]}d']
    
    logger.info(f"Generated labels with distribution:\n{labels.value_counts()}")
    
    return labels


# ==============================================================================
# TRAINING
# ==============================================================================

def train_model(
    X: pd.DataFrame,
    y: pd.Series,
    config: Dict[str, Any],
    model_type: str = 'xgboost',
) -> Tuple[Any, Dict[str, float]]:
    """Train a model."""
    model_config = config.get('model', {})
    
    # Simple time-based train/val/test split (70/15/15)
    n = len(X)
    train_end = int(n * 0.7)
    val_end = int(n * 0.85)
    
    X_train = X.iloc[:train_end]
    y_train = y.iloc[:train_end]
    X_val = X.iloc[train_end:val_end]
    y_val = y.iloc[train_end:val_end]
    X_test = X.iloc[val_end:]
    y_test = y.iloc[val_end:]
    
    logger.info(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    
    # Handle NaN values
    X_train = X_train.fillna(0)
    X_val = X_val.fillna(0)
    X_test = X_test.fillna(0)
    
    # Remove non-numeric columns
    numeric_cols = X_train.select_dtypes(include=[np.number]).columns
    X_train = X_train[numeric_cols]
    X_val = X_val[numeric_cols]
    X_test = X_test[numeric_cols]
    
    # Map labels to integers
    label_map = {label: i for i, label in enumerate(sorted(y.dropna().unique()))}
    y_train = y_train.map(label_map).fillna(-1).astype(int)
    y_val = y_val.map(label_map).fillna(-1).astype(int)
    y_test = y_test.map(label_map).fillna(-1).astype(int)
    
    # Filter out invalid labels
    valid_train = y_train >= 0
    valid_val = y_val >= 0
    valid_test = y_test >= 0
    
    X_train, y_train = X_train[valid_train], y_train[valid_train]
    X_val, y_val = X_val[valid_val], y_val[valid_val]
    X_test, y_test = X_test[valid_test], y_test[valid_test]
    
    # Train model
    if model_type == 'xgboost':
        model, metrics = _train_xgboost(X_train, y_train, X_val, y_val, X_test, y_test, model_config)
    elif model_type == 'lightgbm':
        model, metrics = _train_lightgbm(X_train, y_train, X_val, y_val, X_test, y_test, model_config)
    elif model_type == 'random_forest':
        model, metrics = _train_random_forest(X_train, y_train, X_val, y_val, X_test, y_test, model_config)
    else:
        raise ValueError(f"Unknown model type: {model_type}")
    
    # Add feature names to metrics
    metrics['features'] = list(X_train.columns)
    metrics['label_map'] = label_map
    
    return model, metrics


def _train_xgboost(X_train, y_train, X_val, y_val, X_test, y_test, config):
    """Train XGBoost model."""
    try:
        import xgboost as xgb
    except ImportError:
        logger.warning("XGBoost not installed, using sklearn")
        return _train_random_forest(X_train, y_train, X_val, y_val, X_test, y_test, config)
    
    xgb_config = config.get('xgboost', {})
    
    params = {
        'n_estimators': xgb_config.get('n_estimators', 100),
        'max_depth': xgb_config.get('max_depth', 6),
        'learning_rate': xgb_config.get('learning_rate', 0.1),
        'objective': 'multi:softprob',
        'num_class': len(y_train.unique()),
        'eval_metric': 'mlogloss',
        'random_state': 42,
    }
    
    model = xgb.XGBClassifier(**params)
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )
    
    # Evaluate
    train_acc = (model.predict(X_train) == y_train).mean()
    val_acc = (model.predict(X_val) == y_val).mean()
    test_acc = (model.predict(X_test) == y_test).mean()
    
    metrics = {
        'train_accuracy': float(train_acc),
        'val_accuracy': float(val_acc),
        'test_accuracy': float(test_acc),
        'model_type': 'xgboost',
    }
    
    logger.info(f"XGBoost - Train: {train_acc:.4f}, Val: {val_acc:.4f}, Test: {test_acc:.4f}")
    
    return model, metrics


def _train_lightgbm(X_train, y_train, X_val, y_val, X_test, y_test, config):
    """Train LightGBM model."""
    try:
        import lightgbm as lgb
    except ImportError:
        logger.warning("LightGBM not installed, using sklearn")
        return _train_random_forest(X_train, y_train, X_val, y_val, X_test, y_test, config)
    
    lgb_config = config.get('lightgbm', {})
    
    params = {
        'n_estimators': lgb_config.get('n_estimators', 100),
        'max_depth': lgb_config.get('max_depth', 6),
        'learning_rate': lgb_config.get('learning_rate', 0.1),
        'objective': 'multiclass',
        'num_class': len(y_train.unique()),
        'random_state': 42,
        'verbosity': -1,
    }
    
    model = lgb.LGBMClassifier(**params)
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
    )
    
    # Evaluate
    train_acc = (model.predict(X_train) == y_train).mean()
    val_acc = (model.predict(X_val) == y_val).mean()
    test_acc = (model.predict(X_test) == y_test).mean()
    
    metrics = {
        'train_accuracy': float(train_acc),
        'val_accuracy': float(val_acc),
        'test_accuracy': float(test_acc),
        'model_type': 'lightgbm',
    }
    
    logger.info(f"LightGBM - Train: {train_acc:.4f}, Val: {val_acc:.4f}, Test: {test_acc:.4f}")
    
    return model, metrics


def _train_random_forest(X_train, y_train, X_val, y_val, X_test, y_test, config):
    """Train Random Forest model (fallback)."""
    from sklearn.ensemble import RandomForestClassifier
    
    rf_config = config.get('random_forest', {})
    
    model = RandomForestClassifier(
        n_estimators=rf_config.get('n_estimators', 100),
        max_depth=rf_config.get('max_depth', 10),
        random_state=42,
        n_jobs=-1,
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate
    train_acc = (model.predict(X_train) == y_train).mean()
    val_acc = (model.predict(X_val) == y_val).mean()
    test_acc = (model.predict(X_test) == y_test).mean()
    
    metrics = {
        'train_accuracy': float(train_acc),
        'val_accuracy': float(val_acc),
        'test_accuracy': float(test_acc),
        'model_type': 'random_forest',
    }
    
    logger.info(f"RandomForest - Train: {train_acc:.4f}, Val: {val_acc:.4f}, Test: {test_acc:.4f}")
    
    return model, metrics


# ==============================================================================
# MODEL SAVING
# ==============================================================================

def save_model(model, metrics: Dict, config: Dict, output_dir: str = 'models/default'):
    """Save trained model and metadata."""
    import joblib
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save model
    model_path = output_path / 'model.joblib'
    joblib.dump(model, model_path)
    logger.info(f"Saved model to {model_path}")
    
    # Save manifest
    manifest = {
        'name': config.get('name', 'quant_model'),
        'version': config.get('version', '1.0.0'),
        'type': metrics.get('model_type', 'unknown'),
        'trained_at': datetime.now().isoformat(),
        'features': metrics.get('features', []),
        'target': config.get('labels', {}).get('target', 'return_5d'),
        'metrics': {k: v for k, v in metrics.items() if isinstance(v, (int, float))},
        'config': config,
    }
    
    manifest_path = output_path / 'model_manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"Saved manifest to {manifest_path}")
    
    return output_path


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description='Train ML models')
    parser.add_argument('--config', type=str, default='tools/train_config.yaml',
                       help='Path to config file')
    parser.add_argument('--model', type=str, default='xgboost',
                       choices=['xgboost', 'lightgbm', 'random_forest'],
                       help='Model type to train')
    parser.add_argument('--output', type=str, default='models/default',
                       help='Output directory for trained model')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run without saving model')
    
    args = parser.parse_args()
    
    # Load config
    logger.info(f"Loading config from {args.config}")
    config = load_config(args.config)
    
    # Load data
    logger.info("Loading data...")
    data = load_data(config)
    
    if data.empty:
        logger.error("No data loaded")
        return 1
    
    # Compute features
    logger.info("Computing features...")
    features = compute_features(data, config)
    
    if features.empty:
        logger.error("No features computed")
        return 1
    
    # Generate labels
    logger.info("Generating labels...")
    labels = generate_labels(data, config)
    
    # Align features and labels
    common_idx = features.index.intersection(labels.index)
    X = features.loc[common_idx]
    y = labels.loc[common_idx]
    
    logger.info(f"Training on {len(X)} samples with {len(X.columns)} features")
    
    # Train model
    logger.info(f"Training {args.model} model...")
    model, metrics = train_model(X, y, config, model_type=args.model)
    
    # Save model
    if not args.dry_run:
        save_model(model, metrics, config, args.output)
    
    # Print summary
    print("\n" + "="*60)
    print("TRAINING COMPLETE")
    print("="*60)
    print(f"Model Type: {metrics.get('model_type')}")
    print(f"Train Accuracy: {metrics.get('train_accuracy', 0):.4f}")
    print(f"Val Accuracy: {metrics.get('val_accuracy', 0):.4f}")
    print(f"Test Accuracy: {metrics.get('test_accuracy', 0):.4f}")
    print(f"Features: {len(metrics.get('features', []))}")
    print("="*60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
Research Lab Experiment Runner

Backend runner that executes a single experiment defined by config.yaml.
- Loads experiment config (tickers, features, model, date range)
- Uses time-series splitter for walk-forward cross-validation
- Trains model on each fold
- Generates out-of-fold (OOF) predictions
- Calculates performance metrics (Sharpe, IC, hit rate)
- Saves artifacts to experiments/{exp_id}/

Usage:
    python3 research/runner.py --exp-id exp_20250106_143522
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
import yaml
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
# seaborn is optional for plotting; runner should work without it
try:
    import seaborn as sns
    HAS_SEABORN = True
except Exception:
    HAS_SEABORN = False

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# data_loader is not required for the standalone runner; fallback to merged_data.csv
# or synthetic data generation is implemented below.

# Try importing model libraries
try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def load_config(exp_dir: str) -> dict:
    """Load experiment config.yaml"""
    config_path = Path(exp_dir) / 'config.yaml'
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    logger.info(f"Loaded config: {config['name']}")
    return config


def load_features(config: dict) -> pd.DataFrame:
    """Load feature data for experiment universe"""
    logger.info("Loading feature data...")
    
    # For now, load from merged_data.csv if available
    data_path = Path('data/merged_data.csv')
    if data_path.exists():
        df = pd.read_csv(data_path, parse_dates=['date'])
        logger.info(f"Loaded {len(df)} rows from merged_data.csv")
    else:
        # Fallback: generate synthetic data for demonstration
        logger.warning("merged_data.csv not found, generating synthetic data")
        df = _generate_synthetic_data(config)
    
    # Filter by date range
    start_date = pd.to_datetime(config.get('start_date', '2018-01-01'))
    end_date = pd.to_datetime(config.get('end_date', datetime.now().date()))
    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    
    logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
    return df


def _generate_synthetic_data(config: dict) -> pd.DataFrame:
    """Generate synthetic feature data for demonstration"""
    logger.warning("Using synthetic data for demonstration purposes")
    
    dates = pd.date_range(
        start=config.get('start_date', '2018-01-01'),
        end=config.get('end_date', datetime.now().date()),
        freq='W'
    )
    
    # Generate 100 synthetic tickers
    tickers = [f'TICK{i:03d}' for i in range(100)]
    
    records = []
    for date in dates:
        for ticker in tickers:
            record = {
                'date': date,
                'ticker': ticker,
                'ret_1m': np.random.randn() * 0.1,
                'ret_3m': np.random.randn() * 0.15,
                'ret_6m': np.random.randn() * 0.20,
                'rsi': np.random.uniform(20, 80),
                'macd': np.random.randn() * 0.02,
                'vol_60_ann': np.random.uniform(0.15, 0.40),
                'target_ret_1m_fwd': np.random.randn() * 0.1  # Forward return target
            }
            records.append(record)
    
    df = pd.DataFrame(records)
    logger.info(f"Generated {len(df)} synthetic records")
    return df


def build_feature_matrix(df: pd.DataFrame, feature_groups: list) -> tuple:
    """Build X, y matrices from selected feature groups"""
    feature_cols = []
    
    # Map feature groups to column patterns
    feature_map = {
        'momentum': ['ret_1m', 'ret_3m', 'ret_6m'],
        'technical': ['rsi', 'macd', 'vol_60_ann'],
        'sentiment': ['finbert_score', 'pca_text_1', 'pca_text_2'],
        'fundamental': ['pe_ratio', 'pb_ratio', 'roe'],
        'macro': ['vix', 'tnx', 'oil_price'],
        'size': ['mktcap', 'adv']
    }
    
    for group in feature_groups:
        if group in feature_map:
            feature_cols.extend(feature_map[group])
    
    # Filter to available columns
    available_features = [col for col in feature_cols if col in df.columns]
    
    if not available_features:
        raise ValueError(f"No features available from groups: {feature_groups}")
    
    logger.info(f"Selected features: {available_features}")
    
    # Build X, y
    X = df[available_features].copy()
    y = df['target_ret_1m_fwd'].copy() if 'target_ret_1m_fwd' in df.columns else df['ret_1m'].shift(-1)
    
    # Fill missing values
    X = X.fillna(X.median())
    y = y.fillna(0)
    
    return X, y, available_features


def time_series_split(df: pd.DataFrame, n_splits: int = 5) -> list:
    """Create time-series walk-forward splits"""
    dates = sorted(df['date'].unique())
    
    # Calculate split points
    total_dates = len(dates)
    fold_size = total_dates // (n_splits + 1)
    
    splits = []
    for i in range(n_splits):
        train_end_idx = fold_size * (i + 2)
        val_start_idx = fold_size * (i + 2)
        val_end_idx = min(fold_size * (i + 3), total_dates)
        
        if val_start_idx >= total_dates:
            break
        
        train_dates = dates[:train_end_idx]
        val_dates = dates[val_start_idx:val_end_idx]
        
        splits.append({
            'train_dates': train_dates,
            'val_dates': val_dates,
            'train_end': train_dates[-1],
            'val_end': val_dates[-1]
        })
    
    logger.info(f"Created {len(splits)} time-series folds")
    return splits


def train_model(X_train: pd.DataFrame, y_train: pd.Series, model_type: str) -> any:
    """Train a model"""
    if model_type == 'lgb' and HAS_LGB:
        logger.info("Training LightGBM model...")
        model = lgb.LGBMRegressor(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=5,
            num_leaves=31,
            random_state=42,
            n_jobs=-1,
            verbose=-1
        )
        model.fit(X_train, y_train)
        return model
    else:
        # Fallback: simple mean model for demonstration
        logger.warning(f"Model type '{model_type}' not available, using mean baseline")
        return {'type': 'mean', 'mean': y_train.mean()}


def predict(model: any, X: pd.DataFrame) -> np.ndarray:
    """Generate predictions"""
    if isinstance(model, dict) and model['type'] == 'mean':
        return np.full(len(X), model['mean'])
    else:
        return model.predict(X)


def calculate_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    """Calculate performance metrics"""
    # Information Coefficient (IC) - correlation between predictions and returns
    ic = np.corrcoef(y_true, y_pred)[0, 1]
    
    # Rank IC - Spearman correlation
    from scipy.stats import spearmanr
    rank_ic, _ = spearmanr(y_true, y_pred)
    
    # Hit rate - % of times sign is correct
    hit_rate = np.mean(np.sign(y_true) == np.sign(y_pred))
    
    # Sharpe ratio - assuming daily predictions
    returns = y_true * np.sign(y_pred)  # Simplified long/short strategy
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
    
    metrics = {
        'oof_ic': float(ic) if not np.isnan(ic) else 0.0,
        'rank_ic': float(rank_ic) if not np.isnan(rank_ic) else 0.0,
        'hit_rate': float(hit_rate),
        'sharpe': float(sharpe),
        'mean_return': float(returns.mean()),
        'volatility': float(returns.std())
    }
    
    logger.info(f"Metrics: IC={metrics['oof_ic']:.4f}, Sharpe={metrics['sharpe']:.2f}, Hit Rate={metrics['hit_rate']:.2%}")
    return metrics


def save_artifacts(exp_dir: Path, oof_df: pd.DataFrame, metrics: dict, 
                   feature_importance: dict, config: dict):
    """Save experiment artifacts"""
    logger.info(f"Saving artifacts to {exp_dir}...")
    
    # Save OOF predictions
    oof_df.to_csv(exp_dir / 'oof_preds.csv', index=False)
    logger.info(f"Saved OOF predictions: {len(oof_df)} rows")
    
    # Save metrics report
    report = {
        'experiment_id': exp_dir.name,
        'name': config['name'],
        'model': config['model'],
        'metrics': metrics,
        'config': config,
        'completed_at': datetime.now().isoformat()
    }
    
    with open(exp_dir / 'report.json', 'w') as f:
        json.dump(report, f, indent=2)
    logger.info("Saved report.json")
    
    # Save feature importance plot
    if feature_importance:
        plt.figure(figsize=(10, 6))
        features = list(feature_importance.keys())
        importances = list(feature_importance.values())
        
        plt.barh(features, importances)
        plt.xlabel('Importance')
        plt.title('Feature Importance')
        plt.tight_layout()
        plt.savefig(exp_dir / 'feature_importance.png', dpi=100, bbox_inches='tight')
        plt.close()
        logger.info("Saved feature_importance.png")


def run_experiment(exp_id: str):
    """Main experiment runner"""
    logger.info(f"Starting experiment: {exp_id}")
    
    exp_dir = Path('research/experiments') / exp_id
    if not exp_dir.exists():
        raise ValueError(f"Experiment directory not found: {exp_dir}")
    
    # Load config
    config = load_config(exp_dir)
    
    # Load features
    df = load_features(config)
    
    # Build feature matrix
    feature_groups = config.get('features', ['momentum', 'technical'])
    X, y, feature_cols = build_feature_matrix(df, feature_groups)
    
    # Add date and ticker back for splitting
    df_work = df[['date', 'ticker']].copy()
    df_work[feature_cols] = X
    df_work['target'] = y
    
    # Create time-series splits
    splits = time_series_split(df_work, n_splits=5)
    
    # Train on each fold and collect OOF predictions
    oof_predictions = []
    all_feature_importance = {}
    
    for fold_idx, split in enumerate(splits):
        logger.info(f"Fold {fold_idx + 1}/{len(splits)}: Train until {split['train_end']}, Val: {split['val_end']}")
        
        # Split data
        train_mask = df_work['date'].isin(split['train_dates'])
        val_mask = df_work['date'].isin(split['val_dates'])
        
        X_train = df_work.loc[train_mask, feature_cols]
        y_train = df_work.loc[train_mask, 'target']
        X_val = df_work.loc[val_mask, feature_cols]
        y_val = df_work.loc[val_mask, 'target']
        
        # Train model
        model = train_model(X_train, y_train, config['model'])
        
        # Predict on validation set
        y_pred = predict(model, X_val)
        
        # Store OOF predictions
        oof_fold = df_work.loc[val_mask, ['date', 'ticker']].copy()
        oof_fold['y_true'] = y_val.values
        oof_fold['y_pred'] = y_pred
        oof_fold['fold'] = fold_idx
        oof_predictions.append(oof_fold)
        
        # Accumulate feature importance
        if hasattr(model, 'feature_importances_'):
            for feat, imp in zip(feature_cols, model.feature_importances_):
                all_feature_importance[feat] = all_feature_importance.get(feat, 0) + imp
    
    # Combine all OOF predictions
    oof_df = pd.concat(oof_predictions, ignore_index=True)
    
    # Calculate overall metrics
    metrics = calculate_metrics(oof_df['y_true'], oof_df['y_pred'])
    
    # Average feature importance across folds
    if all_feature_importance:
        n_folds = len(splits)
        all_feature_importance = {k: v / n_folds for k, v in all_feature_importance.items()}
    
    # Save artifacts
    save_artifacts(exp_dir, oof_df, metrics, all_feature_importance, config)
    
    # Update cache with completed status
    _update_cache(exp_id, metrics)
    
    logger.info(f"✅ Experiment {exp_id} complete!")
    return metrics


def _update_cache(exp_id: str, metrics: dict):
    """Update research_experiments.json cache with results"""
    cache_file = Path('cache/research_experiments.json')
    
    try:
        with open(cache_file, 'r') as f:
            experiments = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning("Cache file not found")
        return
    
    # Find and update experiment
    for exp in experiments:
        if exp.get('exp_id') == exp_id:
            exp['status'] = 'completed'
            exp['oof_ic'] = metrics['oof_ic']
            exp['sharpe'] = metrics['sharpe']
            exp['hit_rate'] = metrics['hit_rate']
            exp['completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            break
    
    with open(cache_file, 'w') as f:
        json.dump(experiments, f, indent=2)
    
    logger.info("Updated cache with results")


def main():
    parser = argparse.ArgumentParser(description='Research Lab Experiment Runner')
    parser.add_argument('--exp-id', required=True, help='Experiment ID (e.g., exp_20250106_143522)')
    args = parser.parse_args()
    
    try:
        metrics = run_experiment(args.exp_id)
        print(f"\n✅ Experiment complete!")
        print(f"   IC: {metrics['oof_ic']:.4f}")
        print(f"   Sharpe: {metrics['sharpe']:.2f}")
        print(f"   Hit Rate: {metrics['hit_rate']:.2%}")
    except Exception as e:
        logger.error(f"Experiment failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

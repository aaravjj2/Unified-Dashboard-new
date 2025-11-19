"""
utils/snapshots.py

Feature snapshot utilities for reproducibility and audit trails.

Functions:
- save_feature_snapshot: Save complete feature vector for a ticker
- load_feature_snapshot: Load saved feature snapshot
- save_batch_snapshots: Save snapshots for multiple tickers
- validate_snapshot: Validate snapshot integrity
"""

import os
import json
import hashlib
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

SNAPSHOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'features_snapshots')
os.makedirs(SNAPSHOTS_DIR, exist_ok=True)


# ============================================================================
# Snapshot Creation
# ============================================================================

def save_feature_snapshot(
    ticker: str,
    features: Dict[str, Any],
    model_version: str,
    date: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> str:
    """
    Save feature snapshot for a single ticker.
    
    Args:
        ticker: Stock ticker symbol
        features: Dict of feature name -> value
        model_version: Model version identifier
        date: Date string (YYYYMMDD), defaults to today
        metadata: Optional additional metadata
    
    Returns:
        Path to saved snapshot file
    """
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    
    # Create date directory
    date_dir = os.path.join(SNAPSHOTS_DIR, date)
    os.makedirs(date_dir, exist_ok=True)
    
    # Convert numpy types to native Python types for JSON serialization
    features_clean = {}
    for key, value in features.items():
        if isinstance(value, (np.integer, np.floating)):
            features_clean[key] = float(value) if isinstance(value, np.floating) else int(value)
        elif isinstance(value, np.ndarray):
            features_clean[key] = value.tolist()
        elif value is None or isinstance(value, (str, int, float, bool)):
            features_clean[key] = value
        else:
            features_clean[key] = str(value)
    
    # Compute data hash for integrity checking
    feature_str = json.dumps(features_clean, sort_keys=True)
    data_hash = hashlib.sha256(feature_str.encode()).hexdigest()[:16]
    
    # Build snapshot
    snapshot = {
        'ticker': ticker,
        'date': date,
        'timestamp': datetime.now().isoformat(),
        'model_version': model_version,
        'data_hash': data_hash,
        'num_features': len(features_clean),
        'features': features_clean,
        'metadata': metadata or {}
    }
    
    # Save to file
    filename = f'{ticker}.json'
    filepath = os.path.join(date_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(snapshot, f, indent=2)
    
    logger.debug(f"Saved feature snapshot: {ticker} ({len(features_clean)} features)")
    return filepath


def save_batch_snapshots(
    tickers: List[str],
    features_matrix: np.ndarray,
    feature_names: List[str],
    model_version: str,
    date: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> List[str]:
    """
    Save feature snapshots for multiple tickers.
    
    Args:
        tickers: List of ticker symbols
        features_matrix: Feature matrix (n_tickers x n_features)
        feature_names: List of feature names
        model_version: Model version identifier
        date: Date string (YYYYMMDD)
        metadata: Optional additional metadata
    
    Returns:
        List of saved file paths
    """
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    
    saved_paths = []
    
    for i, ticker in enumerate(tickers):
        if i >= len(features_matrix):
            logger.warning(f"Skipping {ticker}: no features in matrix")
            continue
        
        # Extract features for this ticker
        ticker_features = features_matrix[i]
        features_dict = {
            name: float(value) for name, value in zip(feature_names, ticker_features)
        }
        
        # Add ticker-specific metadata
        ticker_metadata = metadata.copy() if metadata else {}
        ticker_metadata['batch_index'] = i
        
        try:
            path = save_feature_snapshot(
                ticker=ticker,
                features=features_dict,
                model_version=model_version,
                date=date,
                metadata=ticker_metadata
            )
            saved_paths.append(path)
        except Exception as e:
            logger.error(f"Failed to save snapshot for {ticker}: {e}")
    
    logger.info(f"Saved {len(saved_paths)} feature snapshots to {date}/")
    return saved_paths


# ============================================================================
# Snapshot Loading
# ============================================================================

def load_feature_snapshot(
    ticker: str,
    date: Optional[str] = None
) -> Optional[Dict]:
    """
    Load feature snapshot for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        date: Date string (YYYYMMDD), defaults to most recent
    
    Returns:
        Snapshot dict or None if not found
    """
    if date:
        filepath = os.path.join(SNAPSHOTS_DIR, date, f'{ticker}.json')
    else:
        # Find most recent snapshot
        dates = sorted([d for d in os.listdir(SNAPSHOTS_DIR) if os.path.isdir(os.path.join(SNAPSHOTS_DIR, d))], reverse=True)
        filepath = None
        for d in dates:
            candidate = os.path.join(SNAPSHOTS_DIR, d, f'{ticker}.json')
            if os.path.exists(candidate):
                filepath = candidate
                break
    
    if not filepath or not os.path.exists(filepath):
        logger.warning(f"Snapshot not found for {ticker} (date={date})")
        return None
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load snapshot: {e}")
        return None


def load_batch_snapshots(
    tickers: List[str],
    date: Optional[str] = None
) -> Dict[str, Optional[Dict]]:
    """
    Load snapshots for multiple tickers.
    
    Args:
        tickers: List of ticker symbols
        date: Date string (YYYYMMDD)
    
    Returns:
        Dict mapping ticker to snapshot (or None if not found)
    """
    return {ticker: load_feature_snapshot(ticker, date) for ticker in tickers}


# ============================================================================
# Validation
# ============================================================================

def validate_snapshot(snapshot: Dict, verbose: bool = False) -> bool:
    """
    Validate snapshot integrity.
    
    Args:
        snapshot: Snapshot dict
        verbose: Print validation details
    
    Returns:
        True if valid, False otherwise
    """
    required_keys = ['ticker', 'date', 'model_version', 'data_hash', 'features']
    
    # Check required keys
    for key in required_keys:
        if key not in snapshot:
            if verbose:
                logger.warning(f"Missing required key: {key}")
            return False
    
    # Recompute hash and compare
    features_clean = snapshot['features']
    feature_str = json.dumps(features_clean, sort_keys=True)
    computed_hash = hashlib.sha256(feature_str.encode()).hexdigest()[:16]
    
    if computed_hash != snapshot['data_hash']:
        if verbose:
            logger.warning(f"Hash mismatch: expected {snapshot['data_hash']}, got {computed_hash}")
        return False
    
    if verbose:
        logger.info(f"Snapshot valid: {snapshot['ticker']} ({snapshot['num_features']} features)")
    
    return True


def replay_prediction(
    snapshot: Dict,
    model: Any,
    feature_names: List[str]
) -> Optional[float]:
    """
    Replay prediction using saved snapshot.
    
    Args:
        snapshot: Feature snapshot
        model: Trained model object
        feature_names: Expected feature order for model
    
    Returns:
        Prediction value or None if replay failed
    """
    if not validate_snapshot(snapshot):
        logger.error("Snapshot validation failed")
        return None
    
    try:
        # Extract features in correct order
        features_dict = snapshot['features']
        features_array = np.array([features_dict.get(name, 0.0) for name in feature_names])
        
        # Reshape for single prediction
        features_array = features_array.reshape(1, -1)
        
        # Get prediction
        prediction = model.predict(features_array)[0]
        
        return float(prediction)
    
    except Exception as e:
        logger.error(f"Prediction replay failed: {e}")
        return None


# ============================================================================
# Utility Functions
# ============================================================================

def list_snapshot_dates() -> List[str]:
    """List all dates with saved snapshots."""
    return sorted([
        d for d in os.listdir(SNAPSHOTS_DIR)
        if os.path.isdir(os.path.join(SNAPSHOTS_DIR, d))
    ], reverse=True)


def count_snapshots(date: str) -> int:
    """Count number of snapshots for a given date."""
    date_dir = os.path.join(SNAPSHOTS_DIR, date)
    if not os.path.isdir(date_dir):
        return 0
    return len([f for f in os.listdir(date_dir) if f.endswith('.json')])


def get_snapshot_stats() -> Dict:
    """Get statistics about saved snapshots."""
    dates = list_snapshot_dates()
    
    stats = {
        'total_dates': len(dates),
        'dates': []
    }
    
    for date in dates:
        count = count_snapshots(date)
        stats['dates'].append({
            'date': date,
            'count': count
        })
    
    return stats


# ============================================================================
# Self-Test
# ============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("Testing snapshots.py module...\n")
    
    # Test 1: Save single snapshot
    print("Test 1: Save single snapshot")
    test_features = {
        'sma_20': 150.5,
        'sma_50': 145.2,
        'rsi': 65.3,
        'macd_hist': 0.45,
        'volume': 1500000,
        'volatility': 0.25
    }
    test_date = '20250102'
    
    try:
        path = save_feature_snapshot(
            ticker='AAPL',
            features=test_features,
            model_version='v1.0.0',
            date=test_date,
            metadata={'source': 'test'}
        )
        print(f"  ✓ Saved to: {os.path.relpath(path)}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    print()
    
    # Test 2: Load and validate
    print("Test 2: Load and validate snapshot")
    try:
        loaded = load_feature_snapshot('AAPL', test_date)
        if loaded:
            print(f"  ✓ Loaded {loaded['ticker']} with {loaded['num_features']} features")
            print(f"    Model version: {loaded['model_version']}")
            print(f"    Data hash: {loaded['data_hash']}")
            
            is_valid = validate_snapshot(loaded, verbose=True)
            print(f"  ✓ Validation: {'PASSED' if is_valid else 'FAILED'}")
        else:
            print("  ✗ Failed to load")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    print()
    
    # Test 3: Batch save
    print("Test 3: Batch snapshot save")
    test_tickers = ['MSFT', 'GOOGL', 'AMZN']
    test_matrix = np.random.randn(3, 4)  # 3 tickers, 4 features
    test_feature_names = ['feat_1', 'feat_2', 'feat_3', 'feat_4']
    
    try:
        paths = save_batch_snapshots(
            tickers=test_tickers,
            features_matrix=test_matrix,
            feature_names=test_feature_names,
            model_version='v1.0.0',
            date=test_date
        )
        print(f"  ✓ Saved {len(paths)} snapshots")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    print()
    
    # Test 4: Statistics
    print("Test 4: Snapshot statistics")
    try:
        stats = get_snapshot_stats()
        print(f"  Total dates: {stats['total_dates']}")
        for date_stat in stats['dates'][:3]:  # Show first 3
            print(f"    {date_stat['date']}: {date_stat['count']} snapshots")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    print()
    
    # Cleanup test files
    print("Cleanup: Removing test snapshots")
    test_dir = os.path.join(SNAPSHOTS_DIR, test_date)
    if os.path.exists(test_dir):
        import shutil
        shutil.rmtree(test_dir)
        print("  ✓ Cleaned up test directory")
    
    print()
    print("✅ Tests completed!")

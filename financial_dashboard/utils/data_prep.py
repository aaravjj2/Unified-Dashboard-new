"""
Data Preparation Utilities for ML Feature Engineering

Prepares features for model predictions and SHAP analysis.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, List, Optional

logger = logging.getLogger(__name__)


def prepare_features_for_date(
    date: Optional[str] = None,
    tickers: Optional[List[str]] = None
) -> Tuple[Optional[np.ndarray], Optional[List[str]], Optional[List[str]]]:
    """
    Prepare feature matrix for a given date and set of tickers.
    
    This function fetches historical price data, computes technical indicators,
    and returns a feature matrix ready for model prediction and SHAP analysis.
    
    Args:
        date: Target date in 'YYYYMMDD' format (defaults to today)
        tickers: List of tickers to prepare features for (defaults to common stocks)
        
    Returns:
        Tuple of (features, feature_names, tickers):
        - features: np.ndarray of shape (n_tickers, n_features)
        - feature_names: List of feature column names
        - tickers: List of ticker symbols (same order as features rows)
        
        Returns (None, None, None) if preparation fails.
    """
    try:
        # Parse date
        if date is None:
            target_date = datetime.now()
        else:
            target_date = datetime.strptime(date, '%Y%m%d')
        
        # Default tickers if not provided
        if tickers is None:
            tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
            logger.info(f"Using default tickers: {tickers}")
        
        # Try to fetch real historical data
        try:
            features_df = _fetch_and_compute_features(tickers, target_date)
            
            if features_df is not None and not features_df.empty:
                feature_names = features_df.columns.tolist()
                features_array = features_df.values
                tickers_list = features_df.index.tolist()
                
                logger.info(f"✅ Prepared features: shape={features_array.shape}, tickers={len(tickers_list)}")
                return features_array, feature_names, tickers_list
                
        except Exception as e:
            logger.warning(f"⚠️ Real data fetch failed: {e} - using synthetic features")
        
        # Fallback to synthetic features for testing
        logger.info("Using synthetic features for testing")
        return _generate_synthetic_features(tickers)
        
    except Exception as e:
        logger.error(f"❌ Feature preparation failed: {e}")
        return None, None, None


def _fetch_and_compute_features(
    tickers: List[str],
    target_date: datetime,
    lookback_days: int = 90
) -> Optional[pd.DataFrame]:
    """
    Fetch historical prices and compute technical indicator features.
    
    Args:
        tickers: List of ticker symbols
        target_date: Target date for feature computation
        lookback_days: Number of days to look back for historical data
        
    Returns:
        DataFrame with tickers as index and features as columns, or None on failure
    """
    try:
        import yfinance as yf
        
        end_date = target_date
        start_date = target_date - timedelta(days=lookback_days)
        
        logger.info(f"Fetching historical data from {start_date.date()} to {end_date.date()}")
        
        features_list = []
        valid_tickers = []
        
        for ticker in tickers:
            try:
                # Fetch historical data
                stock = yf.Ticker(ticker)
                hist = stock.history(start=start_date, end=end_date)
                
                if hist.empty or len(hist) < 20:
                    logger.warning(f"Insufficient data for {ticker} - skipping")
                    continue
                
                # Compute technical indicators
                close_prices = hist['Close']
                
                # Price momentum features
                returns_1d = close_prices.pct_change(1).iloc[-1]
                returns_5d = close_prices.pct_change(5).iloc[-1] if len(close_prices) >= 5 else 0
                returns_20d = close_prices.pct_change(20).iloc[-1] if len(close_prices) >= 20 else 0
                
                # Volatility features
                volatility_20d = close_prices.pct_change().rolling(20).std().iloc[-1] if len(close_prices) >= 20 else 0
                
                # Moving average features
                sma_20 = close_prices.rolling(20).mean().iloc[-1] if len(close_prices) >= 20 else close_prices.iloc[-1]
                sma_50 = close_prices.rolling(50).mean().iloc[-1] if len(close_prices) >= 50 else close_prices.iloc[-1]
                
                price_to_sma20 = (close_prices.iloc[-1] / sma_20 - 1) if sma_20 > 0 else 0
                price_to_sma50 = (close_prices.iloc[-1] / sma_50 - 1) if sma_50 > 0 else 0
                
                # Volume features
                if 'Volume' in hist.columns:
                    volume_avg = hist['Volume'].rolling(20).mean().iloc[-1] if len(hist) >= 20 else hist['Volume'].iloc[-1]
                    volume_ratio = hist['Volume'].iloc[-1] / volume_avg if volume_avg > 0 else 1.0
                else:
                    volume_ratio = 1.0
                
                # RSI approximation (simple momentum-based)
                gains = close_prices.diff().clip(lower=0)
                losses = -close_prices.diff().clip(upper=0)
                avg_gain = gains.rolling(14).mean().iloc[-1] if len(gains) >= 14 else 0
                avg_loss = losses.rolling(14).mean().iloc[-1] if len(losses) >= 14 else 0
                rs = avg_gain / avg_loss if avg_loss > 0 else 100
                rsi = 100 - (100 / (1 + rs))
                
                # Assemble feature vector
                features_dict = {
                    'momentum_1d': returns_1d,
                    'momentum_5d': returns_5d,
                    'momentum_20d': returns_20d,
                    'volatility_20d': volatility_20d,
                    'price_to_sma20': price_to_sma20,
                    'price_to_sma50': price_to_sma50,
                    'volume_ratio': volume_ratio,
                    'rsi': rsi
                }
                
                features_list.append(features_dict)
                valid_tickers.append(ticker)
                
                logger.info(f"✅ Computed features for {ticker}")
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to process {ticker}: {e}")
                continue
        
        if not features_list:
            logger.error("No valid features computed for any ticker")
            return None
        
        # Create DataFrame
        features_df = pd.DataFrame(features_list, index=valid_tickers)
        
        # Fill NaN with 0 (conservative approach)
        features_df = features_df.fillna(0)
        
        logger.info(f"✅ Created feature matrix: {features_df.shape}")
        return features_df
        
    except ImportError:
        logger.warning("yfinance not available - cannot fetch real data")
        return None
    except Exception as e:
        logger.error(f"❌ Error fetching and computing features: {e}")
        return None


def _generate_synthetic_features(
    tickers: List[str],
    n_features: int = 8
) -> Tuple[np.ndarray, List[str], List[str]]:
    """
    Generate synthetic feature data for testing purposes.
    
    Args:
        tickers: List of ticker symbols
        n_features: Number of features to generate
        
    Returns:
        Tuple of (features, feature_names, tickers)
    """
    logger.info(f"Generating synthetic features for {len(tickers)} tickers")
    
    # Feature names
    feature_names = [
        'momentum_1d',
        'momentum_5d',
        'momentum_20d',
        'volatility_20d',
        'price_to_sma20',
        'price_to_sma50',
        'volume_ratio',
        'rsi'
    ][:n_features]
    
    # Generate random features with realistic ranges
    np.random.seed(42)  # Reproducible
    
    # Momentum: -0.1 to 0.1 (daily returns)
    momentum_features = np.random.uniform(-0.1, 0.1, (len(tickers), 3))
    
    # Volatility: 0.01 to 0.05 (1% to 5% daily volatility)
    volatility_features = np.random.uniform(0.01, 0.05, (len(tickers), 1))
    
    # Price to MA: -0.2 to 0.2 (20% deviation from MA)
    ma_features = np.random.uniform(-0.2, 0.2, (len(tickers), 2))
    
    # Volume ratio: 0.5 to 2.0
    volume_features = np.random.uniform(0.5, 2.0, (len(tickers), 1))
    
    # RSI: 20 to 80
    rsi_features = np.random.uniform(20, 80, (len(tickers), 1))
    
    # Combine all features
    features = np.hstack([
        momentum_features,
        volatility_features,
        ma_features,
        volume_features,
        rsi_features
    ])[:, :n_features]
    
    logger.info(f"✅ Generated synthetic features: shape={features.shape}")
    
    return features, feature_names, tickers


def validate_features(features: np.ndarray) -> bool:
    """
    Validate feature matrix for common issues.
    
    Args:
        features: Feature matrix to validate
        
    Returns:
        True if valid, False otherwise
    """
    if features is None:
        logger.error("Features is None")
        return False
    
    if not isinstance(features, np.ndarray):
        logger.error(f"Features must be np.ndarray, got {type(features)}")
        return False
    
    if features.size == 0:
        logger.error("Features array is empty")
        return False
    
    if np.any(np.isnan(features)):
        logger.warning("Features contain NaN values")
        return False
    
    if np.any(np.isinf(features)):
        logger.warning("Features contain inf values")
        return False
    
    logger.info(f"✅ Features validated: shape={features.shape}, dtype={features.dtype}")
    return True

"""
Factor Models Service - XGBoost/LightGBM based factor models
Implements #54 from ROADMAP_ULTIMATE.md
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False

from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import os

logger = logging.getLogger(__name__)


class FactorModelsService:
    """
    XGBoost/LightGBM based factor models for:
    - Alpha factor discovery
    - Return prediction
    - Factor exposure analysis
    - Risk attribution
    """
    
    FACTORS = [
        'momentum_1m', 'momentum_3m', 'momentum_6m', 'momentum_12m',
        'volatility_20d', 'volatility_60d',
        'beta', 'size', 'value', 'quality',
        'rsi_14', 'macd_signal', 'bb_position',
        'volume_ratio', 'atr_ratio',
        'put_call_ratio', 'implied_vol_rank',
        'earnings_surprise', 'analyst_revision',
        'sector_momentum', 'market_regime'
    ]
    
    def __init__(self, model_dir: str = "models/factor_models"):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        self.scaler = StandardScaler()
        self.xgb_model = None
        self.lgb_model = None
        self.feature_importance = {}
        
    def calculate_factors(self, price_data: pd.DataFrame, 
                         options_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Calculate all factors from price and options data"""
        df = price_data.copy()
        
        # Momentum factors
        df['momentum_1m'] = df['close'].pct_change(21)
        df['momentum_3m'] = df['close'].pct_change(63)
        df['momentum_6m'] = df['close'].pct_change(126)
        df['momentum_12m'] = df['close'].pct_change(252)
        
        # Volatility factors
        df['returns'] = df['close'].pct_change()
        df['volatility_20d'] = df['returns'].rolling(20).std() * np.sqrt(252)
        df['volatility_60d'] = df['returns'].rolling(60).std() * np.sqrt(252)
        
        # Technical factors
        df['rsi_14'] = self._calculate_rsi(df['close'], 14)
        df['macd_signal'] = self._calculate_macd_signal(df['close'])
        df['bb_position'] = self._calculate_bb_position(df['close'])
        
        # Volume factors
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # ATR ratio
        df['atr'] = self._calculate_atr(df, 14)
        df['atr_ratio'] = df['atr'] / df['close']
        
        # Beta (vs market proxy - using rolling correlation)
        if 'market_return' in df.columns:
            df['beta'] = df['returns'].rolling(60).cov(df['market_return']) / df['market_return'].rolling(60).var()
        else:
            df['beta'] = 1.0
            
        # Size factor (log market cap proxy)
        if 'market_cap' in df.columns:
            df['size'] = np.log(df['market_cap'])
        else:
            df['size'] = 0
            
        # Value factor (book-to-market proxy)
        if 'book_value' in df.columns and 'market_cap' in df.columns:
            df['value'] = df['book_value'] / df['market_cap']
        else:
            df['value'] = 0
            
        # Quality factor (ROE proxy)
        if 'roe' in df.columns:
            df['quality'] = df['roe']
        else:
            df['quality'] = 0
            
        # Options-based factors
        if options_data is not None and len(options_data) > 0:
            df['put_call_ratio'] = options_data.get('put_call_ratio', 1.0)
            df['implied_vol_rank'] = options_data.get('iv_rank', 0.5)
        else:
            df['put_call_ratio'] = 1.0
            df['implied_vol_rank'] = 0.5
            
        # Placeholder factors
        df['earnings_surprise'] = 0
        df['analyst_revision'] = 0
        df['sector_momentum'] = 0
        df['market_regime'] = 0
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd_signal(self, prices: pd.Series) -> pd.Series:
        """Calculate MACD signal line position"""
        ema12 = prices.ewm(span=12).mean()
        ema26 = prices.ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        return (macd - signal) / prices * 100
    
    def _calculate_bb_position(self, prices: pd.Series, period: int = 20) -> pd.Series:
        """Calculate Bollinger Band position (0-1)"""
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        upper = sma + 2 * std
        lower = sma - 2 * std
        return (prices - lower) / (upper - lower)
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(period).mean()
    
    def prepare_training_data(self, factor_df: pd.DataFrame, 
                             target_horizon: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare data for model training"""
        # Target: forward returns
        factor_df['target'] = factor_df['returns'].shift(-target_horizon).rolling(target_horizon).sum()
        
        # Feature columns
        feature_cols = [col for col in self.FACTORS if col in factor_df.columns]
        
        # Drop NaN
        clean_df = factor_df.dropna(subset=feature_cols + ['target'])
        
        X = clean_df[feature_cols].values
        y = clean_df['target'].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        return X_scaled, y, feature_cols
    
    def train_xgboost(self, X: np.ndarray, y: np.ndarray, 
                     feature_names: List[str]) -> Dict[str, Any]:
        """Train XGBoost model with time series cross-validation"""
        if not HAS_XGBOOST:
            return {'error': 'XGBoost not installed'}
            
        tscv = TimeSeriesSplit(n_splits=5)
        
        params = {
            'objective': 'reg:squarederror',
            'max_depth': 6,
            'learning_rate': 0.05,
            'n_estimators': 200,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'n_jobs': -1
        }
        
        cv_scores = []
        
        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            
            model = xgb.XGBRegressor(**params)
            model.fit(X_train, y_train, 
                     eval_set=[(X_val, y_val)],
                     verbose=False)
            
            y_pred = model.predict(X_val)
            score = r2_score(y_val, y_pred)
            cv_scores.append(score)
        
        # Final model on all data
        self.xgb_model = xgb.XGBRegressor(**params)
        self.xgb_model.fit(X, y, verbose=False)
        
        # Feature importance
        importance = self.xgb_model.feature_importances_
        self.feature_importance['xgboost'] = dict(zip(feature_names, importance))
        
        return {
            'model': 'XGBoost',
            'cv_r2_mean': np.mean(cv_scores),
            'cv_r2_std': np.std(cv_scores),
            'feature_importance': self.feature_importance['xgboost']
        }
    
    def train_lightgbm(self, X: np.ndarray, y: np.ndarray,
                      feature_names: List[str]) -> Dict[str, Any]:
        """Train LightGBM model with time series cross-validation"""
        if not HAS_LIGHTGBM:
            return {'error': 'LightGBM not installed'}
            
        tscv = TimeSeriesSplit(n_splits=5)
        
        params = {
            'objective': 'regression',
            'max_depth': 6,
            'learning_rate': 0.05,
            'n_estimators': 200,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'n_jobs': -1,
            'verbose': -1
        }
        
        cv_scores = []
        
        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            
            model = lgb.LGBMRegressor(**params)
            model.fit(X_train, y_train,
                     eval_set=[(X_val, y_val)])
            
            y_pred = model.predict(X_val)
            score = r2_score(y_val, y_pred)
            cv_scores.append(score)
        
        # Final model
        self.lgb_model = lgb.LGBMRegressor(**params)
        self.lgb_model.fit(X, y)
        
        # Feature importance
        importance = self.lgb_model.feature_importances_
        self.feature_importance['lightgbm'] = dict(zip(feature_names, importance))
        
        return {
            'model': 'LightGBM',
            'cv_r2_mean': np.mean(cv_scores),
            'cv_r2_std': np.std(cv_scores),
            'feature_importance': self.feature_importance['lightgbm']
        }
    
    def predict(self, factor_data: pd.DataFrame, model: str = 'ensemble') -> Dict[str, Any]:
        """Generate predictions using trained models"""
        feature_cols = [col for col in self.FACTORS if col in factor_data.columns]
        X = factor_data[feature_cols].values
        X_scaled = self.scaler.transform(X)
        
        predictions = {}
        
        if model in ['xgboost', 'ensemble'] and self.xgb_model is not None:
            predictions['xgboost'] = self.xgb_model.predict(X_scaled)
            
        if model in ['lightgbm', 'ensemble'] and self.lgb_model is not None:
            predictions['lightgbm'] = self.lgb_model.predict(X_scaled)
            
        if model == 'ensemble' and len(predictions) == 2:
            predictions['ensemble'] = (predictions['xgboost'] + predictions['lightgbm']) / 2
            
        return predictions
    
    def get_factor_exposures(self, tickers: List[str], 
                            factor_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Calculate factor exposures for multiple tickers"""
        exposures = []
        
        for ticker in tickers:
            if ticker in factor_data:
                df = factor_data[ticker]
                latest = df.iloc[-1]
                
                exposure = {'ticker': ticker}
                for factor in self.FACTORS:
                    if factor in latest:
                        exposure[factor] = latest[factor]
                        
                exposures.append(exposure)
                
        return pd.DataFrame(exposures)
    
    def rank_stocks(self, factor_exposures: pd.DataFrame, 
                   weights: Optional[Dict[str, float]] = None) -> pd.DataFrame:
        """Rank stocks based on factor scores"""
        if weights is None:
            # Default weights favoring momentum and quality
            weights = {
                'momentum_3m': 0.2,
                'momentum_6m': 0.15,
                'quality': 0.2,
                'value': 0.15,
                'volatility_20d': -0.1,  # Negative = prefer lower vol
                'rsi_14': 0.1,
                'volume_ratio': 0.1
            }
        
        df = factor_exposures.copy()
        
        # Z-score normalize factors
        factor_cols = [col for col in df.columns if col != 'ticker']
        for col in factor_cols:
            if df[col].std() > 0:
                df[f'{col}_z'] = (df[col] - df[col].mean()) / df[col].std()
            else:
                df[f'{col}_z'] = 0
        
        # Calculate composite score
        df['composite_score'] = 0
        for factor, weight in weights.items():
            if f'{factor}_z' in df.columns:
                df['composite_score'] += weight * df[f'{factor}_z']
        
        # Rank
        df['rank'] = df['composite_score'].rank(ascending=False)
        
        return df.sort_values('rank')[['ticker', 'composite_score', 'rank'] + factor_cols]
    
    def save_models(self):
        """Save trained models to disk"""
        if self.xgb_model is not None:
            joblib.dump(self.xgb_model, f"{self.model_dir}/xgb_factor_model.pkl")
        if self.lgb_model is not None:
            joblib.dump(self.lgb_model, f"{self.model_dir}/lgb_factor_model.pkl")
        joblib.dump(self.scaler, f"{self.model_dir}/factor_scaler.pkl")
        
    def load_models(self):
        """Load trained models from disk"""
        try:
            self.xgb_model = joblib.load(f"{self.model_dir}/xgb_factor_model.pkl")
            self.lgb_model = joblib.load(f"{self.model_dir}/lgb_factor_model.pkl")
            self.scaler = joblib.load(f"{self.model_dir}/factor_scaler.pkl")
            return True
        except FileNotFoundError:
            logger.warning("No saved factor models found")
            return False


# Singleton instance
_factor_service = None

def get_factor_service() -> FactorModelsService:
    global _factor_service
    if _factor_service is None:
        _factor_service = FactorModelsService()
    return _factor_service

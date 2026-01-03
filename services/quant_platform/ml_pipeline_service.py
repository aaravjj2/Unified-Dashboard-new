"""
ML Pipeline Service - Roadmap Items 401-460
Machine learning models and pipelines for quantitative finance
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import Ridge, Lasso
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.cluster import KMeans
from scipy import stats
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ModelResult:
    """Model training result"""
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    feature_importance: Dict[str, float]
    predictions: np.ndarray = None

@dataclass
class FeatureSet:
    """Feature engineering result"""
    features: pd.DataFrame
    feature_names: List[str]
    target: pd.Series
    scaler: Any = None

@dataclass
class RegimeState:
    """Market regime state"""
    regime_id: int
    regime_name: str
    probability: float
    characteristics: Dict[str, float]

class FeatureEngineering:
    """Feature engineering pipeline - Items 433-445"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []
        
    def create_return_features(self, prices: pd.Series, 
                               periods: List[int] = [1, 5, 10, 20, 60]) -> pd.DataFrame:
        """Create return-based features - Item 433"""
        features = pd.DataFrame(index=prices.index)
        
        for p in periods:
            features[f'return_{p}d'] = prices.pct_change(p)
            features[f'return_{p}d_rank'] = features[f'return_{p}d'].rolling(60).apply(
                lambda x: stats.percentileofscore(x.dropna(), x.iloc[-1]) / 100 if len(x.dropna()) > 0 else 0.5
            )
        
        return features
    
    def create_volatility_features(self, prices: pd.Series,
                                   windows: List[int] = [5, 10, 20, 60]) -> pd.DataFrame:
        """Create volatility features - Item 433"""
        features = pd.DataFrame(index=prices.index)
        returns = prices.pct_change()
        
        for w in windows:
            features[f'volatility_{w}d'] = returns.rolling(w).std() * np.sqrt(252)
            features[f'volatility_{w}d_rank'] = features[f'volatility_{w}d'].rolling(120).apply(
                lambda x: stats.percentileofscore(x.dropna(), x.iloc[-1]) / 100 if len(x.dropna()) > 0 else 0.5
            )
        
        # Volatility regime
        features['vol_regime'] = (features['volatility_20d'] > features['volatility_60d']).astype(int)
        
        return features
    
    def create_momentum_features(self, prices: pd.Series) -> pd.DataFrame:
        """Create momentum features - Item 433"""
        features = pd.DataFrame(index=prices.index)
        
        # Price momentum
        features['momentum_10d'] = prices / prices.shift(10) - 1
        features['momentum_20d'] = prices / prices.shift(20) - 1
        features['momentum_60d'] = prices / prices.shift(60) - 1
        
        # Momentum acceleration
        features['momentum_accel'] = features['momentum_10d'] - features['momentum_10d'].shift(10)
        
        # RSI
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        features['rsi_14'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = prices.ewm(span=12).mean()
        ema26 = prices.ewm(span=26).mean()
        features['macd'] = ema12 - ema26
        features['macd_signal'] = features['macd'].ewm(span=9).mean()
        features['macd_histogram'] = features['macd'] - features['macd_signal']
        
        return features
    
    def create_mean_reversion_features(self, prices: pd.Series) -> pd.DataFrame:
        """Create mean reversion features - Item 433"""
        features = pd.DataFrame(index=prices.index)
        
        for w in [10, 20, 50]:
            ma = prices.rolling(w).mean()
            features[f'distance_ma_{w}'] = (prices - ma) / ma
            features[f'zscore_{w}'] = (prices - ma) / prices.rolling(w).std()
        
        # Bollinger Bands
        ma20 = prices.rolling(20).mean()
        std20 = prices.rolling(20).std()
        features['bb_upper'] = (prices - (ma20 + 2 * std20)) / (4 * std20)
        features['bb_lower'] = (prices - (ma20 - 2 * std20)) / (4 * std20)
        features['bb_width'] = (4 * std20) / ma20
        
        return features
    
    def create_all_features(self, prices: pd.Series, 
                           target_horizon: int = 5) -> FeatureSet:
        """Create complete feature set"""
        # Create all features
        return_features = self.create_return_features(prices)
        vol_features = self.create_volatility_features(prices)
        momentum_features = self.create_momentum_features(prices)
        mr_features = self.create_mean_reversion_features(prices)
        
        # Combine
        features = pd.concat([return_features, vol_features, momentum_features, mr_features], axis=1)
        
        # Create target
        future_return = prices.shift(-target_horizon) / prices - 1
        target = (future_return > 0).astype(int)  # Binary classification
        
        # Clean
        features = features.dropna()
        target = target.loc[features.index]
        
        valid_idx = target.notna()
        features = features.loc[valid_idx]
        target = target.loc[valid_idx]
        
        # Scale
        features_scaled = pd.DataFrame(
            self.scaler.fit_transform(features),
            index=features.index,
            columns=features.columns
        )
        
        self.feature_names = list(features.columns)
        
        return FeatureSet(
            features=features_scaled,
            feature_names=self.feature_names,
            target=target,
            scaler=self.scaler
        )

class TimeSeriesCV:
    """Time series cross-validation - Items 428-432"""
    
    def __init__(self, n_splits: int = 5, gap: int = 5):
        self.n_splits = n_splits
        self.gap = gap
        self.tscv = TimeSeriesSplit(n_splits=n_splits, gap=gap)
        
    def split(self, X: pd.DataFrame) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Get train/test splits"""
        return list(self.tscv.split(X))
    
    def purged_kfold(self, X: pd.DataFrame, embargo_pct: float = 0.01) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Purged K-Fold with embargo - Item 430"""
        n_samples = len(X)
        embargo_size = int(n_samples * embargo_pct)
        
        splits = []
        fold_size = n_samples // self.n_splits
        
        for i in range(self.n_splits):
            test_start = i * fold_size
            test_end = (i + 1) * fold_size if i < self.n_splits - 1 else n_samples
            
            test_idx = np.arange(test_start, test_end)
            
            # Training excludes test + embargo period
            train_idx = np.concatenate([
                np.arange(0, max(0, test_start - embargo_size)),
                np.arange(min(n_samples, test_end + embargo_size), n_samples)
            ])
            
            if len(train_idx) > 0:
                splits.append((train_idx, test_idx))
        
        return splits

class EnsembleModels:
    """Ensemble machine learning models - Items 413-423"""
    
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.results: Dict[str, ModelResult] = {}
        
    def train_random_forest(self, X_train: pd.DataFrame, y_train: pd.Series,
                           n_estimators: int = 100) -> ModelResult:
        """Train Random Forest - Item 416"""
        model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=10,
            min_samples_split=20,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)
        self.models['random_forest'] = model
        
        return self._evaluate_model(model, X_train, y_train, 'RandomForest')
    
    def train_gradient_boosting(self, X_train: pd.DataFrame, y_train: pd.Series,
                                n_estimators: int = 100) -> ModelResult:
        """Train Gradient Boosting - Item 418"""
        model = GradientBoostingClassifier(
            n_estimators=n_estimators,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        
        model.fit(X_train, y_train)
        self.models['gradient_boosting'] = model
        
        return self._evaluate_model(model, X_train, y_train, 'GradientBoosting')
    
    def _evaluate_model(self, model: Any, X: pd.DataFrame, y: pd.Series,
                       name: str) -> ModelResult:
        """Evaluate model performance"""
        predictions = model.predict(X)
        
        # Feature importance
        if hasattr(model, 'feature_importances_'):
            importance = dict(zip(X.columns, model.feature_importances_))
        else:
            importance = {}
        
        result = ModelResult(
            model_name=name,
            accuracy=accuracy_score(y, predictions),
            precision=precision_score(y, predictions, zero_division=0),
            recall=recall_score(y, predictions, zero_division=0),
            f1=f1_score(y, predictions, zero_division=0),
            feature_importance=importance,
            predictions=predictions
        )
        
        self.results[name] = result
        return result
    
    def predict_ensemble(self, X: pd.DataFrame, weights: Dict[str, float] = None) -> np.ndarray:
        """Ensemble prediction - Item 420"""
        if not self.models:
            return np.zeros(len(X))
        
        if weights is None:
            weights = {name: 1.0 / len(self.models) for name in self.models}
        
        predictions = np.zeros(len(X))
        
        for name, model in self.models.items():
            weight = weights.get(name, 0)
            pred_proba = model.predict_proba(X)[:, 1] if hasattr(model, 'predict_proba') else model.predict(X)
            predictions += weight * pred_proba
        
        return (predictions > 0.5).astype(int)

class RegimeDetection:
    """Market regime detection - Items 446-452"""
    
    def __init__(self, n_regimes: int = 3):
        self.n_regimes = n_regimes
        self.kmeans = KMeans(n_clusters=n_regimes, random_state=42)
        self.regime_names = ['Low Vol', 'Normal', 'High Vol']
        
    def detect_regimes(self, returns: pd.Series, 
                       volatility: pd.Series) -> pd.DataFrame:
        """Detect market regimes using clustering - Item 446"""
        # Create regime features
        features = pd.DataFrame({
            'return': returns.rolling(20).mean(),
            'volatility': volatility,
            'vol_of_vol': volatility.rolling(20).std()
        }).dropna()
        
        # Standardize
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # Cluster
        self.kmeans.fit(features_scaled)
        
        # Assign regime labels
        regimes = pd.Series(self.kmeans.labels_, index=features.index)
        
        # Order regimes by average volatility
        regime_vols = features.groupby(regimes)['volatility'].mean()
        regime_order = regime_vols.sort_values().index
        regime_map = {old: new for new, old in enumerate(regime_order)}
        regimes = regimes.map(regime_map)
        
        return pd.DataFrame({
            'regime': regimes,
            'regime_name': regimes.map({0: 'Low Vol', 1: 'Normal', 2: 'High Vol'})
        })
    
    def get_regime_stats(self, returns: pd.Series, 
                        regimes: pd.Series) -> Dict[int, Dict[str, float]]:
        """Get statistics for each regime"""
        stats_dict = {}
        
        # Convert to numpy for easier indexing
        returns_arr = returns.values
        regimes_arr = regimes.values
        
        for regime in np.unique(regimes_arr):
            mask = regimes_arr == regime
            regime_returns = returns_arr[mask]
            vol = np.std(regime_returns) * np.sqrt(252)
            mean_ret = np.mean(regime_returns) * 252
            stats_dict[int(regime)] = {
                'mean_return': float(mean_ret),
                'volatility': float(vol),
                'sharpe': float(mean_ret / vol) if vol > 0 else 0.0,
                'frequency': float(np.sum(mask) / len(returns_arr))
            }
        
        return stats_dict

class AnomalyDetection:
    """Anomaly detection for market data - Items 453-457"""
    
    def __init__(self, contamination: float = 0.05):
        self.contamination = contamination
        
    def zscore_anomalies(self, data: pd.Series, threshold: float = 3.0) -> pd.Series:
        """Z-score based anomaly detection - Item 453"""
        zscore = (data - data.mean()) / data.std()
        return abs(zscore) > threshold
    
    def rolling_zscore_anomalies(self, data: pd.Series, window: int = 60,
                                 threshold: float = 3.0) -> pd.Series:
        """Rolling Z-score anomalies"""
        rolling_mean = data.rolling(window).mean()
        rolling_std = data.rolling(window).std()
        zscore = (data - rolling_mean) / rolling_std
        return abs(zscore) > threshold
    
    def iqr_anomalies(self, data: pd.Series, multiplier: float = 1.5) -> pd.Series:
        """IQR based anomaly detection"""
        q1 = data.quantile(0.25)
        q3 = data.quantile(0.75)
        iqr = q3 - q1
        
        lower = q1 - multiplier * iqr
        upper = q3 + multiplier * iqr
        
        return (data < lower) | (data > upper)

class MLPipelineService:
    """Main ML pipeline service - Items 401-460"""
    
    def __init__(self):
        self.feature_engineer = FeatureEngineering()
        self.cv = TimeSeriesCV(n_splits=5)
        self.ensemble = EnsembleModels()
        self.regime_detector = RegimeDetection()
        self.anomaly_detector = AnomalyDetection()
        
    def train_prediction_model(self, prices: pd.Series,
                              target_horizon: int = 5) -> Dict[str, ModelResult]:
        """Train full prediction pipeline"""
        # Create features
        feature_set = self.feature_engineer.create_all_features(prices, target_horizon)
        
        # Split data
        train_size = int(len(feature_set.features) * 0.8)
        X_train = feature_set.features.iloc[:train_size]
        y_train = feature_set.target.iloc[:train_size]
        X_test = feature_set.features.iloc[train_size:]
        y_test = feature_set.target.iloc[train_size:]
        
        # Train models
        rf_result = self.ensemble.train_random_forest(X_train, y_train)
        gb_result = self.ensemble.train_gradient_boosting(X_train, y_train)
        
        # Test predictions
        test_predictions = self.ensemble.predict_ensemble(X_test)
        
        test_result = ModelResult(
            model_name='Ensemble_Test',
            accuracy=accuracy_score(y_test, test_predictions),
            precision=precision_score(y_test, test_predictions, zero_division=0),
            recall=recall_score(y_test, test_predictions, zero_division=0),
            f1=f1_score(y_test, test_predictions, zero_division=0),
            feature_importance={},
            predictions=test_predictions
        )
        
        return {
            'random_forest': rf_result,
            'gradient_boosting': gb_result,
            'ensemble_test': test_result
        }
    
    def detect_market_regime(self, prices: pd.Series) -> Dict[str, Any]:
        """Detect current market regime"""
        returns = prices.pct_change().dropna()
        volatility = returns.rolling(20).std() * np.sqrt(252)
        volatility = volatility.dropna()
        
        # Align returns and volatility
        common_idx = returns.index.intersection(volatility.index)
        returns = returns.loc[common_idx]
        volatility = volatility.loc[common_idx]
        
        regimes = self.regime_detector.detect_regimes(returns, volatility)
        # Reset indices to align
        returns_aligned = returns.reset_index(drop=True)
        regimes_aligned = regimes['regime'].reset_index(drop=True)
        stats = self.regime_detector.get_regime_stats(returns_aligned, regimes_aligned)
        
        current_regime = regimes.iloc[-1]['regime'] if len(regimes) > 0 else 1
        current_regime_name = regimes.iloc[-1]['regime_name'] if len(regimes) > 0 else 'Normal'
        
        return {
            'current_regime': int(current_regime),
            'current_regime_name': current_regime_name,
            'regime_stats': stats,
            'regime_history': regimes.tail(20).to_dict()
        }
    
    def detect_anomalies(self, data: pd.Series) -> Dict[str, Any]:
        """Detect anomalies in data"""
        zscore_anomalies = self.anomaly_detector.zscore_anomalies(data)
        rolling_anomalies = self.anomaly_detector.rolling_zscore_anomalies(data)
        iqr_anomalies = self.anomaly_detector.iqr_anomalies(data)
        
        return {
            'zscore_anomalies': zscore_anomalies.sum(),
            'rolling_anomalies': rolling_anomalies.sum(),
            'iqr_anomalies': iqr_anomalies.sum(),
            'anomaly_dates': data[zscore_anomalies | rolling_anomalies].index.tolist()[-10:]
        }
    
    def generate_sample_analysis(self) -> Dict[str, Any]:
        """Generate sample analysis for testing"""
        np.random.seed(42)
        
        # Generate synthetic price data
        n_periods = 500
        
        # Price with trend and volatility regimes
        trend = np.cumsum(np.random.normal(0.0003, 0.001, n_periods))
        noise = np.random.normal(0, 0.02, n_periods)
        
        prices = pd.Series(
            100 * np.exp(trend + np.cumsum(noise)),
            index=pd.date_range(end=pd.Timestamp.now(), periods=n_periods, freq='D')
        )
        
        # Train models
        model_results = self.train_prediction_model(prices)
        
        # Detect regimes
        regime_analysis = self.detect_market_regime(prices)
        
        # Detect anomalies
        returns = prices.pct_change().dropna()
        anomaly_analysis = self.detect_anomalies(returns)
        
        return {
            'data_points': n_periods,
            'model_results': {
                name: {
                    'accuracy': result.accuracy,
                    'precision': result.precision,
                    'recall': result.recall,
                    'f1': result.f1,
                    'top_features': dict(sorted(
                        result.feature_importance.items(), 
                        key=lambda x: -x[1]
                    )[:5]) if result.feature_importance else {}
                }
                for name, result in model_results.items()
            },
            'regime_analysis': regime_analysis,
            'anomaly_analysis': anomaly_analysis
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            'models_trained': len(self.ensemble.models),
            'features_created': len(self.feature_engineer.feature_names),
            'cv_splits': self.cv.n_splits
        }


if __name__ == "__main__":
    # Test the service
    service = MLPipelineService()
    
    print("ML Pipeline Service Test")
    print("=" * 50)
    
    # Generate sample analysis
    analysis = service.generate_sample_analysis()
    
    print(f"\nData Points: {analysis['data_points']}")
    
    print("\nModel Results:")
    for name, result in analysis['model_results'].items():
        print(f"\n  {name}:")
        print(f"    Accuracy: {result['accuracy']:.2%}")
        print(f"    Precision: {result['precision']:.2%}")
        print(f"    F1 Score: {result['f1']:.2%}")
        if result['top_features']:
            print("    Top Features:")
            for feat, imp in list(result['top_features'].items())[:3]:
                print(f"      {feat}: {imp:.4f}")
    
    print("\nRegime Analysis:")
    regime = analysis['regime_analysis']
    print(f"  Current Regime: {regime['current_regime_name']}")
    
    print("\nAnomaly Analysis:")
    anomalies = analysis['anomaly_analysis']
    print(f"  Z-Score Anomalies: {anomalies['zscore_anomalies']}")
    print(f"  Rolling Anomalies: {anomalies['rolling_anomalies']}")
    print(f"  IQR Anomalies: {anomalies['iqr_anomalies']}")
    
    print(f"\nService Stats: {service.get_stats()}")
    
    print("\n✅ ML Pipeline Service operational - Items 401-460")

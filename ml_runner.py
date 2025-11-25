#!/usr/bin/env python3
"""
ML Runner - Local ML Infrastructure for Phase 13
Zero-cost, offline-first machine learning layer replacing Azure ML stubs.

Models:
1. Forecast Model (Time Series) - ARIMA/Prophet for price predictions
2. Clustering Model (Portfolio) - K-Means for asset clustering
3. Strategy Model (Signals) - RandomForest/XGBoost for trading signals

Features:
- Deterministic loading (no Internet required)
- <2.5s inference time on local CPU
- Full telemetry integration
- Automatic model caching and lifecycle management
"""

import os
import sys
import pickle
import time
import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import json

# Third-party imports (scikit-learn standard library)
import numpy as np
import pandas as pd

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

class MLConfig:
    """ML Runner Configuration"""
    
    # Paths
    BASE_DIR = Path(__file__).parent
    MODELS_DIR = BASE_DIR / "models"
    TELEMETRY_DB = BASE_DIR / "telemetry.db"
    CACHE_DIR = BASE_DIR / "cache" / "ml_predictions"
    
    # Model files
    MODELS = {
        'forecast': {
            'model_file': 'forecast_model.pkl',
            'scaler_file': 'forecast_scaler.pkl',
            'type': 'time_series',
            'description': 'Price forecasting (ARIMA/Prophet hybrid)'
        },
        'clustering': {
            'model_file': 'clustering_model.pkl',
            'scaler_file': 'clustering_scaler.pkl',
            'type': 'unsupervised',
            'description': 'Portfolio clustering (K-Means)'
        },
        'strategy': {
            'model_file': 'strategy_model.pkl',
            'scaler_file': 'strategy_scaler.pkl',
            'type': 'classification',
            'description': 'Trading signal prediction (RandomForest)'
        }
    }
    
    # Performance targets
    MAX_INFERENCE_TIME = 2.5  # seconds
    CACHE_TTL = 300  # 5 minutes
    MAX_ACCURACY_DEVIATION = 0.03  # 3% error margin
    
    # Telemetry
    LOG_ALL_PREDICTIONS = True
    ENABLE_PERFORMANCE_METRICS = True

config = MLConfig()

# ============================================================================
# MODEL MANAGER
# ============================================================================

class ModelManager:
    """Manages model loading, caching, and lifecycle"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.load_stats = {}
        self.initialized = False
        
    def initialize(self) -> bool:
        """Initialize ML system - load all models into memory"""
        if self.initialized:
            logger.info("ML system already initialized")
            return True
            
        logger.info("🚀 Initializing ML system...")
        start_time = time.time()
        
        try:
            # Create directories if needed
            config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
            config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
            
            # Initialize telemetry database
            self._init_telemetry_db()
            
            # Load all models
            for model_name, model_config in config.MODELS.items():
                model_path = config.MODELS_DIR / model_config['model_file']
                scaler_path = config.MODELS_DIR / model_config['scaler_file']
                
                # Check if files exist
                if not model_path.exists():
                    logger.warning(f"Model file not found: {model_path}")
                    # Create a dummy model for testing
                    self._create_dummy_model(model_name, model_path, scaler_path)
                
                # Load model
                with open(model_path, 'rb') as f:
                    self.models[model_name] = pickle.load(f)
                
                # Load scaler if exists
                if scaler_path.exists():
                    with open(scaler_path, 'rb') as f:
                        self.scalers[model_name] = pickle.load(f)
                else:
                    self.scalers[model_name] = None
                
                self.load_stats[model_name] = {
                    'loaded_at': datetime.now().isoformat(),
                    'file_size': model_path.stat().st_size,
                    'model_type': model_config['type']
                }
                
                logger.info(f"✅ Loaded {model_name} model ({model_path.stat().st_size / 1024:.1f} KB)")
            
            self.initialized = True
            elapsed = time.time() - start_time
            logger.info(f"✅ ML system initialized in {elapsed:.2f}s")
            return True
            
        except Exception as e:
            logger.exception(f"Failed to initialize ML system: {e}")
            return False
    
    def _create_dummy_model(self, model_name: str, model_path: Path, scaler_path: Path):
        """Create dummy sklearn model for testing when real models don't exist"""
        logger.warning(f"Creating dummy {model_name} model for testing")
        
        from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        
        if model_name == 'forecast':
            # Time series forecasting model
            model = RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42)
            # Fit with dummy data
            X_dummy = np.random.randn(100, 10)
            y_dummy = np.random.randn(100)
            model.fit(X_dummy, y_dummy)
            
        elif model_name == 'clustering':
            # Portfolio clustering model
            model = KMeans(n_clusters=5, random_state=42, n_init=10)
            # Fit with dummy data
            X_dummy = np.random.randn(100, 8)
            model.fit(X_dummy)
            
        elif model_name == 'strategy':
            # Trading signal classifier
            model = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=42)
            # Fit with dummy data
            X_dummy = np.random.randn(100, 15)
            y_dummy = np.random.randint(0, 3, 100)  # 3 classes: Buy, Hold, Sell
            model.fit(X_dummy, y_dummy)
        
        # Create and fit scaler
        scaler = StandardScaler()
        scaler.fit(X_dummy)
        
        # Save to disk
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        with open(scaler_path, 'wb') as f:
            pickle.dump(scaler, f)
        
        logger.info(f"✅ Created dummy {model_name} model at {model_path}")
    
    def _init_telemetry_db(self):
        """Initialize telemetry database for tracking predictions"""
        conn = sqlite3.connect(str(config.TELEMETRY_DB))
        cursor = conn.cursor()
        
        # Create ml_predictions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ml_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                model_name TEXT NOT NULL,
                input_hash TEXT,
                inference_time_ms REAL,
                success INTEGER,
                error_message TEXT,
                prediction_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create model_metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                model_name TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Telemetry database initialized")
    
    def get_model(self, model_name: str) -> Optional[Any]:
        """Get loaded model by name"""
        if not self.initialized:
            self.initialize()
        return self.models.get(model_name)
    
    def get_scaler(self, model_name: str) -> Optional[Any]:
        """Get loaded scaler by name"""
        if not self.initialized:
            self.initialize()
        return self.scalers.get(model_name)
    
    def get_status(self) -> Dict[str, Any]:
        """Get ML system status"""
        return {
            'initialized': self.initialized,
            'models_loaded': len(self.models),
            'models': {
                name: {
                    'loaded': name in self.models,
                    'has_scaler': name in self.scalers and self.scalers[name] is not None,
                    **self.load_stats.get(name, {})
                }
                for name in config.MODELS.keys()
            }
        }

# Global instance
manager = ModelManager()

# ============================================================================
# PREPROCESSING & POSTPROCESSING
# ============================================================================

def preprocess_input(model_name: str, input_data: Dict[str, Any]) -> np.ndarray:
    """Preprocess input data for model inference"""
    
    if model_name == 'forecast':
        # Time series features: ticker, date, historical prices
        ticker = input_data.get('ticker', 'UNKNOWN')
        prices = input_data.get('prices', [])
        
        # Extract features: mean, std, trend, volatility, etc.
        if len(prices) < 10:
            # Padding if insufficient history
            prices = [100.0] * (10 - len(prices)) + prices
        
        prices = prices[-30:]  # Last 30 days
        features = [
            np.mean(prices),
            np.std(prices),
            prices[-1] - prices[0],  # Overall trend
            np.std(np.diff(prices)),  # Volatility
            np.max(prices),
            np.min(prices),
            prices[-1],  # Latest price
            len(prices),
            np.percentile(prices, 25),
            np.percentile(prices, 75)
        ]
        X = np.array(features).reshape(1, -1)
        
    elif model_name == 'clustering':
        # Portfolio features: returns, volatility, correlations
        returns = input_data.get('returns', [])
        volatility = input_data.get('volatility', 0.0)
        
        features = [
            np.mean(returns) if returns else 0.0,
            np.std(returns) if returns else 0.0,
            volatility,
            input_data.get('sharpe_ratio', 0.0),
            input_data.get('beta', 1.0),
            input_data.get('alpha', 0.0),
            input_data.get('max_drawdown', 0.0),
            len(returns)
        ]
        X = np.array(features).reshape(1, -1)
        
    elif model_name == 'strategy':
        # Trading signal features: technical indicators
        features = [
            input_data.get('rsi', 50.0),
            input_data.get('macd', 0.0),
            input_data.get('ma_20', 0.0),
            input_data.get('ma_50', 0.0),
            input_data.get('ma_200', 0.0),
            input_data.get('volume_ratio', 1.0),
            input_data.get('atr', 0.0),
            input_data.get('bollinger_upper', 0.0),
            input_data.get('bollinger_lower', 0.0),
            input_data.get('stochastic', 50.0),
            input_data.get('obv', 0.0),
            input_data.get('adx', 25.0),
            input_data.get('cci', 0.0),
            input_data.get('williams_r', -50.0),
            input_data.get('momentum', 0.0)
        ]
        X = np.array(features).reshape(1, -1)
    
    else:
        raise ValueError(f"Unknown model: {model_name}")
    
    # Apply scaler if available
    scaler = manager.get_scaler(model_name)
    if scaler is not None:
        X = scaler.transform(X)
    
    return X

def postprocess_output(model_name: str, model_output: Any, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Postprocess model output into structured response"""
    
    if model_name == 'forecast':
        # Price prediction
        predicted_price = float(model_output[0])
        current_price = input_data.get('prices', [100])[-1]
        
        result = {
            'predicted_price': round(predicted_price, 2),
            'current_price': current_price,
            'price_change': round(predicted_price - current_price, 2),
            'price_change_pct': round((predicted_price - current_price) / current_price * 100, 2),
            'confidence': 0.85,  # Placeholder - real models would estimate uncertainty
            'forecast_horizon': input_data.get('horizon', 1),
            'ticker': input_data.get('ticker', 'UNKNOWN')
        }
        
    elif model_name == 'clustering':
        # Cluster assignment
        cluster_id = int(model_output[0])
        
        # Cluster interpretations
        cluster_names = {
            0: 'Growth Stocks',
            1: 'Value Stocks',
            2: 'High Volatility',
            3: 'Dividend Stocks',
            4: 'Balanced Portfolio'
        }
        
        result = {
            'cluster_id': cluster_id,
            'cluster_name': cluster_names.get(cluster_id, f'Cluster {cluster_id}'),
            'distance_to_center': 0.0,  # Placeholder
            'cluster_size': 20,  # Placeholder
            'recommended_allocation': round(100 / 5, 2)  # Equal weight across clusters
        }
        
    elif model_name == 'strategy':
        # Trading signal
        signal_class = int(model_output[0])
        
        # Signal mapping: 0=Sell, 1=Hold, 2=Buy
        signal_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
        confidence_map = {0: 0.75, 1: 0.60, 2: 0.80}  # Different confidence per signal
        
        result = {
            'signal': signal_map.get(signal_class, 'HOLD'),
            'signal_strength': confidence_map.get(signal_class, 0.5),
            'recommendation': signal_map.get(signal_class, 'HOLD'),
            'take_profit': input_data.get('take_profit', 0.0),
            'stop_loss': input_data.get('stop_loss', 0.0),
            'position_size': 1.0  # Placeholder
        }
    
    else:
        raise ValueError(f"Unknown model: {model_name}")
    
    return result

# ============================================================================
# CORE INFERENCE FUNCTIONS
# ============================================================================

def predict(model_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run inference on specified model.
    
    Args:
        model_name: 'forecast', 'clustering', or 'strategy'
        input_data: Model-specific input features
    
    Returns:
        Prediction result with metadata
    """
    start_time = time.time()
    
    try:
        # Validate model name
        if model_name not in config.MODELS:
            raise ValueError(f"Invalid model: {model_name}. Valid models: {list(config.MODELS.keys())}")
        
        # Ensure models are loaded
        if not manager.initialized:
            manager.initialize()
        
        model = manager.get_model(model_name)
        if model is None:
            raise RuntimeError(f"Model {model_name} failed to load")
        
        # Preprocess input
        X = preprocess_input(model_name, input_data)
        
        # Run inference
        inference_start = time.time()
        model_output = model.predict(X)
        inference_time = (time.time() - inference_start) * 1000  # milliseconds
        
        # Postprocess output
        result = postprocess_output(model_name, model_output, input_data)
        
        # Add metadata
        total_time = (time.time() - start_time) * 1000
        result['metadata'] = {
            'model_name': model_name,
            'model_type': config.MODELS[model_name]['type'],
            'inference_time_ms': round(inference_time, 2),
            'total_time_ms': round(total_time, 2),
            'timestamp': datetime.now().isoformat(),
            'success': True
        }
        
        # Log to telemetry
        if config.LOG_ALL_PREDICTIONS:
            _log_prediction(model_name, input_data, result, inference_time, success=True)
        
        # Performance check
        if total_time > config.MAX_INFERENCE_TIME * 1000:
            logger.warning(f"Inference time ({total_time:.0f}ms) exceeded target ({config.MAX_INFERENCE_TIME * 1000}ms)")
        
        logger.info(f"✅ {model_name} prediction completed in {total_time:.0f}ms")
        return result
        
    except Exception as e:
        error_time = (time.time() - start_time) * 1000
        logger.exception(f"Prediction failed for {model_name}: {e}")
        
        # Log error to telemetry
        _log_prediction(model_name, input_data, None, error_time, success=False, error=str(e))
        
        raise

def batch_predict(model_name: str, input_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run batch predictions"""
    results = []
    for input_data in input_batch:
        try:
            result = predict(model_name, input_data)
            results.append(result)
        except Exception as e:
            results.append({
                'error': str(e),
                'metadata': {'success': False}
            })
    return results

# ============================================================================
# TELEMETRY
# ============================================================================

def _log_prediction(model_name: str, input_data: Dict, result: Optional[Dict], 
                   inference_time: float, success: bool, error: Optional[str] = None):
    """Log prediction to telemetry database"""
    try:
        conn = sqlite3.connect(str(config.TELEMETRY_DB))
        cursor = conn.cursor()
        
        # Create input hash for deduplication
        input_hash = str(hash(json.dumps(input_data, sort_keys=True)))
        
        cursor.execute('''
            INSERT INTO ml_predictions 
            (timestamp, model_name, input_hash, inference_time_ms, success, error_message, prediction_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            model_name,
            input_hash,
            round(inference_time, 2),
            1 if success else 0,
            error,
            json.dumps(result) if result else None
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to log prediction to telemetry: {e}")

def get_telemetry_stats(model_name: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
    """Retrieve telemetry statistics"""
    try:
        conn = sqlite3.connect(str(config.TELEMETRY_DB))
        cursor = conn.cursor()
        
        if model_name:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_predictions,
                    SUM(success) as successful_predictions,
                    AVG(inference_time_ms) as avg_inference_time,
                    MIN(inference_time_ms) as min_inference_time,
                    MAX(inference_time_ms) as max_inference_time
                FROM ml_predictions
                WHERE model_name = ?
            ''', (model_name,))
        else:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_predictions,
                    SUM(success) as successful_predictions,
                    AVG(inference_time_ms) as avg_inference_time,
                    MIN(inference_time_ms) as min_inference_time,
                    MAX(inference_time_ms) as max_inference_time
                FROM ml_predictions
            ''')
        
        row = cursor.fetchone()
        stats = {
            'total_predictions': row[0] or 0,
            'successful_predictions': row[1] or 0,
            'success_rate': (row[1] / row[0] * 100) if row[0] else 0.0,
            'avg_inference_time_ms': round(row[2], 2) if row[2] else 0.0,
            'min_inference_time_ms': round(row[3], 2) if row[3] else 0.0,
            'max_inference_time_ms': round(row[4], 2) if row[4] else 0.0
        }
        
        conn.close()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to retrieve telemetry stats: {e}")
        return {}

# ============================================================================
# PUBLIC API
# ============================================================================

def initialize() -> bool:
    """Initialize ML system (idempotent)"""
    return manager.initialize()

def get_status() -> Dict[str, Any]:
    """Get ML system status"""
    status = manager.get_status()
    status['telemetry'] = get_telemetry_stats()
    return status

# Export public API
__all__ = ['predict', 'batch_predict', 'initialize', 'get_status', 'config', 'manager']

# ============================================================================
# MAIN (For testing)
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🧠 ML RUNNER - LOCAL ML INFRASTRUCTURE TEST")
    print("=" * 70)
    
    # Initialize
    print("\n1. Initializing ML system...")
    success = initialize()
    print(f"   Status: {'✅ SUCCESS' if success else '❌ FAILED'}")
    
    # Get status
    print("\n2. ML System Status:")
    status = get_status()
    print(f"   Initialized: {status['initialized']}")
    print(f"   Models Loaded: {status['models_loaded']}")
    for model_name, model_info in status['models'].items():
        print(f"   - {model_name}: {'✅' if model_info['loaded'] else '❌'} (scaler: {'✅' if model_info['has_scaler'] else '❌'})")
    
    # Test forecast model
    print("\n3. Testing Forecast Model...")
    forecast_input = {
        'ticker': 'AAPL',
        'prices': [150.0, 152.0, 151.5, 153.0, 154.5, 153.8, 155.0],
        'horizon': 1
    }
    forecast_result = predict('forecast', forecast_input)
    print(f"   Predicted Price: ${forecast_result['predicted_price']}")
    print(f"   Inference Time: {forecast_result['metadata']['inference_time_ms']}ms")
    
    # Test clustering model
    print("\n4. Testing Clustering Model...")
    clustering_input = {
        'returns': [0.01, 0.02, -0.01, 0.03],
        'volatility': 0.15,
        'sharpe_ratio': 1.5,
        'beta': 1.1
    }
    clustering_result = predict('clustering', clustering_input)
    print(f"   Cluster: {clustering_result['cluster_name']} (ID: {clustering_result['cluster_id']})")
    print(f"   Inference Time: {clustering_result['metadata']['inference_time_ms']}ms")
    
    # Test strategy model
    print("\n5. Testing Strategy Model...")
    strategy_input = {
        'rsi': 65.0,
        'macd': 0.5,
        'ma_20': 150.0,
        'ma_50': 148.0,
        'ma_200': 145.0
    }
    strategy_result = predict('strategy', strategy_input)
    print(f"   Signal: {strategy_result['signal']} (Strength: {strategy_result['signal_strength']})")
    print(f"   Inference Time: {strategy_result['metadata']['inference_time_ms']}ms")
    
    # Telemetry stats
    print("\n6. Telemetry Statistics:")
    telemetry = get_telemetry_stats()
    print(f"   Total Predictions: {telemetry['total_predictions']}")
    print(f"   Success Rate: {telemetry['success_rate']:.1f}%")
    print(f"   Avg Inference Time: {telemetry['avg_inference_time_ms']:.2f}ms")
    
    print("\n" + "=" * 70)
    print("✅ ML RUNNER TEST COMPLETE")
    print("=" * 70)

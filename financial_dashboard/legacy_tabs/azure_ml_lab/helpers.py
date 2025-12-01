"""
Azure ML Lab - Helper Functions

Utility functions for data preprocessing, feature engineering, prediction caching,
and synthetic data generation for ML workflows.

Phase 3 Scaffold - All functions are placeholders/mock implementations.
Phase 4: Real Azure ML integration with mock fallback.
Phase 5: Real data integration (Home Lab, yfinance, Fama-French factors).
"""

import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests

from financial_dashboard.utils.azure_guard import guard as enforce_azure_guard

logger = logging.getLogger(__name__)

# Import Azure ML config (Phase 4)
try:
    from .azure_ml_config import azure_ml_config, test_azure_ml_connection
    AZURE_ML_AVAILABLE = True
    logger.info("✅ Azure ML config loaded")
except ImportError as e:
    logger.warning(f"⚠️ Azure ML config not available: {e}")
    AZURE_ML_AVAILABLE = False
    azure_ml_config = None

# Try to import yfinance for real market data (Phase 5)
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
    logger.info("✅ yfinance loaded for real market data")
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("⚠️ yfinance not available - using mock market data")

# ============================================================================
# REAL DATA INTEGRATION (PHASE 5)
# ============================================================================

def get_portfolio_from_home_lab() -> Dict:
    """
    Import portfolio data from Home Lab dynamically.
    
    Phase 5: Real data integration with Home Lab.
    Uses dynamic import to avoid circular dependencies.
    
    Returns:
        dict: Portfolio summary from Home Lab
    """
    logger.info("📂 Importing portfolio data from Home Lab")
    
    try:
        # Dynamic import to avoid circular dependency
        from importlib import import_module
        home_helpers = import_module('financial_dashboard.tabs.home_lab.helpers')
        
        portfolio_data = home_helpers.get_portfolio_summary()
        
        logger.info(f"✅ Imported {portfolio_data.get('total_positions', 0)} positions from Home Lab (source: {portfolio_data.get('source', 'unknown')})")
        
        return portfolio_data
    
    except Exception as e:
        logger.error(f"❌ Error importing from Home Lab: {e}")
        logger.warning("⚠️ Falling back to mock portfolio")
        
        # Fallback to mock data
        return {
            'total_positions': 0,
            'total_value': 0.0,
            'positions': [],
            'source': 'mock_fallback',
            'error': str(e)
        }


def fetch_market_data_yfinance(tickers: List[str], period: str = "1y") -> pd.DataFrame:
    """
    Fetch real market data from Yahoo Finance.
    
    Phase 5: Real market data integration.
    
    Args:
        tickers: List of ticker symbols
        period: Data period (1mo, 3mo, 6mo, 1y, 2y, 5y)
    
    Returns:
        pd.DataFrame: Historical price data with columns [ticker, date, open, high, low, close, volume, returns]
    """
    logger.info(f"📊 Fetching market data for {len(tickers)} tickers (period: {period})")
    
    if not YFINANCE_AVAILABLE:
        logger.warning("⚠️ yfinance not available - returning empty DataFrame")
        return pd.DataFrame()
    
    try:
        # Download data for all tickers
        data = yf.download(tickers, period=period, group_by='ticker', auto_adjust=True, progress=False)
        
        # Process into long format
        dfs = []
        for ticker in tickers:
            try:
                if len(tickers) == 1:
                    ticker_data = data
                else:
                    ticker_data = data[ticker]
                
                df = ticker_data.reset_index()
                df['ticker'] = ticker
                df['returns'] = df['Close'].pct_change()
                
                dfs.append(df)
            except Exception as e:
                logger.warning(f"⚠️ Error processing {ticker}: {e}")
                continue
        
        if dfs:
            combined_df = pd.concat(dfs, ignore_index=True)
            logger.info(f"✅ Fetched {len(combined_df)} data points for {len(dfs)} tickers")
            return combined_df
        else:
            logger.warning("⚠️ No market data fetched")
            return pd.DataFrame()
    
    except Exception as e:
        logger.error(f"❌ Error fetching market data: {e}")
        return pd.DataFrame()


def fetch_fama_french_factors(start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch Fama-French factor data.
    
    Phase 5: Real factor data integration.
    
    NOTE: For production, integrate with Kenneth French data library or Attribution Lab cache.
    Current implementation returns mock factors as placeholder.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    
    Returns:
        pd.DataFrame: Factor returns with columns [date, Mkt-RF, SMB, HML, RF, RMW, CMA]
    """
    logger.info(f"📈 Fetching Fama-French factors (start: {start_date}, end: {end_date})")
    
    try:
        # TODO Phase 5: Integrate with real Fama-French data source
        # Options:
        # 1. Kenneth French data library (pandas_datareader)
        # 2. Attribution Lab cache (if already downloaded)
        # 3. Local CSV files
        
        # Placeholder: Generate mock factor data
        if start_date and end_date:
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
        else:
            dates = pd.date_range(end=datetime.now(), periods=252, freq='D')
        
        np.random.seed(42)
        factors_df = pd.DataFrame({
            'date': dates,
            'Mkt-RF': np.random.normal(0.0004, 0.012, len(dates)),  # ~10% annual
            'SMB': np.random.normal(0.0001, 0.005, len(dates)),
            'HML': np.random.normal(0.0001, 0.005, len(dates)),
            'RMW': np.random.normal(0.0002, 0.004, len(dates)),
            'CMA': np.random.normal(0.0001, 0.003, len(dates)),
            'RF': np.full(len(dates), 0.0001)  # ~2.5% risk-free rate
        })
        
        logger.info(f"✅ Generated {len(factors_df)} days of Fama-French factors (MOCK DATA)")
        return factors_df
    
    except Exception as e:
        logger.error(f"❌ Error fetching Fama-French factors: {e}")
        return pd.DataFrame()


# ============================================================================
# AZURE ML API CALLS (PHASE 20A - ENHANCED WITH OBSERVABILITY)
# ============================================================================

# Import observability layer
try:
    from .ml_observability import track_ml_operation, log_metric, log_timing, capture_exception
    OBSERVABILITY_AVAILABLE = True
    logger.info("✅ Observability layer loaded")
except ImportError:
    logger.warning("⚠️ Observability layer not available")
    OBSERVABILITY_AVAILABLE = False
    # Define no-op decorators if observability not available
    def track_ml_operation(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def log_metric(*args, **kwargs): pass
    def log_timing(*args, **kwargs): pass
    def capture_exception(*args, **kwargs): pass


@track_ml_operation('ml.endpoint.call', tags={'operation': 'azure_ml_prediction'})
def call_azure_ml_endpoint(
    features_df: pd.DataFrame,
    model_type: str = "ensemble",
    horizon_days: int = 5,
    config_override: Optional[Dict] = None
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Call Azure ML endpoint for real predictions (Phase 20A).
    
    Enhanced with:
    - Full observability (Sentry exceptions, Datadog/Prometheus metrics)
    - Latency tracking
    - Graceful fallback with telemetry
    - Detailed error context
    
    This function attempts to call the real Azure ML endpoint. If unavailable
    or if mock mode is enabled, it falls back to generate_mock_predictions().
    
    Args:
        features_df: Preprocessed feature matrix (from preprocess_portfolio_data)
        model_type: Model type selection ("ensemble", "lstm", "xgboost", "linear")
        horizon_days: Prediction horizon in days (1, 5, 21, 63)
        config_override: Optional config overrides (for testing)
    
    Returns:
        tuple: (predictions_dict or None, error_message or None)
    """
    import time
    start_time = time.time()
    
    logger.info(f"📡 Calling Azure ML endpoint (model: {model_type}, horizon: {horizon_days}d)")
    
    # Emit call counter metric
    log_metric('ml.endpoint.call.count', 1, tags={'model_type': model_type, 'horizon_days': str(horizon_days)})

    try:
        enforce_azure_guard(
            action="azure_ml_lab.call_endpoint",
            metadata={'model_type': model_type, 'horizon_days': horizon_days}
        )
    except RuntimeError as guard_error:
        logger.warning("Azure ML usage blocked: %s", guard_error)
        log_metric('ml.endpoint.blocked', 1, tags={'model_type': model_type, 'horizon_days': str(horizon_days)})
        mock_result = generate_mock_predictions(features_df, model_type, horizon_days)
        latency_ms = (time.time() - start_time) * 1000
        mock_result['fallback_reason'] = 'azure_disabled'
        mock_result['latency_ms'] = latency_ms
        log_timing('ml.endpoint.latency.ms', latency_ms, tags={'source': 'azure_block', 'model_type': model_type, 'status': 'blocked'})
        return mock_result, str(guard_error)
    
    # Check if Azure ML is available and configured
    if not AZURE_ML_AVAILABLE or not azure_ml_config or not azure_ml_config.is_configured():
        logger.warning("⚠️ Azure ML not configured - falling back to mock predictions")
        log_metric('ml.endpoint.fallback', 1, tags={'reason': 'not_configured', 'model_type': model_type})
        mock_result = generate_mock_predictions(features_df, model_type, horizon_days)
        mock_result['fallback_reason'] = 'azure_ml_not_configured'
        latency_ms = (time.time() - start_time) * 1000
        mock_result['latency_ms'] = latency_ms
        log_timing('ml.endpoint.latency.ms', latency_ms, tags={'source': 'mock_fallback', 'model_type': model_type})
        return mock_result, None
    
    # Check if mock mode is explicitly enabled
    if azure_ml_config.use_mock_fallback:
        logger.info("📊 Mock mode enabled - using mock predictions")
        log_metric('ml.endpoint.fallback', 1, tags={'reason': 'mock_mode_enabled', 'model_type': model_type})
        mock_result = generate_mock_predictions(features_df, model_type, horizon_days)
        mock_result['fallback_reason'] = 'mock_mode_enabled'
        latency_ms = (time.time() - start_time) * 1000
        mock_result['latency_ms'] = latency_ms
        log_timing('ml.endpoint.latency.ms', latency_ms, tags={'source': 'mock_fallback', 'model_type': model_type})
        return mock_result, None
    
    try:
        # Prepare payload for Azure ML endpoint
        payload = {
            'model_type': model_type,
            'horizon_days': horizon_days,
            'features': features_df.to_dict('records'),
            'timestamp': datetime.now().isoformat()
        }
        
        # Method 1: REST API call (if endpoint URL and API key available)
        if azure_ml_config.endpoint_url and azure_ml_config.api_key:
            logger.info(f"🌐 Calling REST endpoint: {azure_ml_config.endpoint_url}")
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {azure_ml_config.api_key}'
            }
            
            response = requests.post(
                azure_ml_config.endpoint_url,
                json=payload,
                headers=headers,
                timeout=30  # 30 second timeout
            )
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Successfully received predictions from Azure ML endpoint")
                
                # Emit success metrics
                log_metric('ml.endpoint.success', 1, tags={'source': 'rest_api', 'model_type': model_type})
                log_timing('ml.endpoint.latency.ms', latency_ms, tags={'source': 'azure_ml_rest_api', 'model_type': model_type, 'status': 'success'})
                log_metric('ml.endpoint.prediction_count', len(result.get('predictions', [])), tags={'model_type': model_type})
                
                # Standardize response format
                standardized_result = {
                    'predictions': result.get('predictions', []),
                    'model_type': model_type,
                    'horizon_days': horizon_days,
                    'overall_confidence': result.get('confidence', 0.0),
                    'timestamp': datetime.now().isoformat(),
                    'status': 'success',
                    'source': 'azure_ml_rest_api',
                    'latency_ms': latency_ms
                }
                
                return standardized_result, None
            else:
                error_msg = f"Azure ML endpoint returned {response.status_code}: {response.text}"
                logger.error(f"❌ {error_msg}")
                
                # Emit error metrics
                log_metric('ml.endpoint.error', 1, tags={'source': 'rest_api', 'model_type': model_type, 'status_code': str(response.status_code)})
                log_timing('ml.endpoint.latency.ms', latency_ms, tags={'source': 'azure_ml_rest_api', 'model_type': model_type, 'status': 'error'})
                
                # Capture exception context
                if OBSERVABILITY_AVAILABLE:
                    capture_exception(
                        Exception(error_msg),
                        context={'operation': 'azure_ml_endpoint', 'model_type': model_type, 'status_code': response.status_code}
                    )
                
                # Fallback to mock
                logger.warning("⚠️ Falling back to mock predictions")
                log_metric('ml.endpoint.fallback', 1, tags={'reason': f'status_{response.status_code}', 'model_type': model_type})
                mock_result = generate_mock_predictions(features_df, model_type, horizon_days)
                mock_result['fallback_reason'] = f'endpoint_error_{response.status_code}'
                mock_result['latency_ms'] = latency_ms
                return mock_result, error_msg
        
        # Method 2: Azure ML SDK (if ml_client available)
        try:
            from azure.ai.ml import MLClient
            from .azure_ml_config import authenticate_azure_ml
            
            ml_client, auth_error = authenticate_azure_ml(azure_ml_config)
            
            if ml_client is None:
                raise Exception(f"Authentication failed: {auth_error}")
            
            logger.info(f"🔐 Authenticated to Azure ML workspace")
            
            # Get endpoint
            endpoint = ml_client.online_endpoints.get(name=azure_ml_config.endpoint_name)
            
            # Invoke endpoint
            response = endpoint.invoke(
                request_file=None,
                request_data=json.dumps(payload)
            )
            
            result = json.loads(response)
            logger.info("✅ Successfully received predictions from Azure ML SDK")
            
            standardized_result = {
                'predictions': result.get('predictions', []),
                'model_type': model_type,
                'horizon_days': horizon_days,
                'overall_confidence': result.get('confidence', 0.0),
                'timestamp': datetime.now().isoformat(),
                'status': 'success',
                'source': 'azure_ml_sdk'
            }
            
            return standardized_result, None
        
        except ImportError:
            logger.warning("Azure ML SDK not available, trying REST API only")
            raise Exception("Azure ML SDK not installed")
    
    except requests.exceptions.Timeout:
        error_msg = "Azure ML endpoint timeout (>30s)"
        logger.error(f"❌ {error_msg}")
        latency_ms = (time.time() - start_time) * 1000
        
        # Emit timeout metrics
        log_metric('ml.endpoint.timeout', 1, tags={'model_type': model_type})
        log_timing('ml.endpoint.latency.ms', latency_ms, tags={'source': 'azure_ml_rest_api', 'model_type': model_type, 'status': 'timeout'})
        
        # Capture exception
        if OBSERVABILITY_AVAILABLE:
            capture_exception(
                Exception(error_msg),
                context={'operation': 'azure_ml_endpoint', 'model_type': model_type, 'timeout_seconds': 30}
            )
        
        log_metric('ml.endpoint.fallback', 1, tags={'reason': 'timeout', 'model_type': model_type})
        mock_result = generate_mock_predictions(features_df, model_type, horizon_days)
        mock_result['fallback_reason'] = 'endpoint_timeout'
        mock_result['latency_ms'] = latency_ms
        return mock_result, error_msg
    
    except Exception as e:
        error_msg = f"Azure ML API call failed: {e}"
        logger.error(f"❌ {error_msg}")
        latency_ms = (time.time() - start_time) * 1000
        
        # Emit error metrics
        log_metric('ml.endpoint.error', 1, tags={'model_type': model_type, 'error_type': type(e).__name__})
        log_timing('ml.endpoint.latency.ms', latency_ms, tags={'source': 'azure_ml_rest_api', 'model_type': model_type, 'status': 'error'})
        
        # Capture exception with full context
        if OBSERVABILITY_AVAILABLE:
            capture_exception(
                e,
                context={
                    'operation': 'azure_ml_endpoint',
                    'model_type': model_type,
                    'horizon_days': horizon_days,
                    'features_count': len(features_df),
                    'latency_ms': latency_ms
                }
            )
        
        # Always fallback to mock on any error
        logger.warning("⚠️ Falling back to mock predictions")
        log_metric('ml.endpoint.fallback', 1, tags={'reason': 'api_error', 'model_type': model_type})
        mock_result = generate_mock_predictions(features_df, model_type, horizon_days)
        mock_result['fallback_reason'] = 'api_error'
        mock_result['error_details'] = str(e)
        mock_result['latency_ms'] = latency_ms
        return mock_result, error_msg


# ============================================================================
# DATA PREPROCESSING
# ============================================================================

def preprocess_portfolio_data(portfolio_data: Optional[Dict] = None, use_real_data: bool = True) -> pd.DataFrame:
    """
    Preprocess portfolio data for ML model consumption.
    
    Phase 5: Enhanced with real data integration from Home Lab and yfinance.
    
    Args:
        portfolio_data: Optional dict from home_lab.helpers.get_portfolio_summary()
                       If None and use_real_data=True, will fetch from Home Lab
        use_real_data: If True, fetch from Home Lab; if False, use provided data
    
    Returns:
        pd.DataFrame: Preprocessed feature matrix with engineered features
    """
    logger.info("📊 Preprocessing portfolio data for ML pipeline")
    
    try:
        # Phase 5: Fetch real data from Home Lab if not provided
        if portfolio_data is None and use_real_data:
            logger.info("📥 Fetching portfolio data from Home Lab...")
            portfolio_data = get_portfolio_from_home_lab()
        
        if portfolio_data is None or not portfolio_data:
            logger.warning("No portfolio data available, returning empty DataFrame")
            return pd.DataFrame()
        
        positions = portfolio_data.get('positions', [])
        
        if not positions:
            logger.warning("No positions found, returning empty DataFrame")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(positions)
        
        # Phase 5: Enhanced feature engineering
        logger.info("🔧 Engineering features from portfolio positions...")
        
        # Basic features
        df['market_value_normalized'] = df['market_value'] / df['market_value'].sum()
        df['abs_daily_change'] = df['daily_change_pct'].abs()
        
        # Fetch historical data for tickers (if yfinance available)
        if YFINANCE_AVAILABLE and 'ticker' in df.columns:
            tickers = df['ticker'].unique().tolist()
            logger.info(f"📊 Fetching historical data for {len(tickers)} tickers...")
            
            market_data = fetch_market_data_yfinance(tickers, period="3mo")
            
            if not market_data.empty:
                # Calculate momentum features
                for ticker in tickers:
                    ticker_data = market_data[market_data['ticker'] == ticker]
                    
                    if len(ticker_data) >= 20:
                        returns = ticker_data['returns'].dropna()
                        
                        # Add features to portfolio dataframe
                        mask = df['ticker'] == ticker
                        df.loc[mask, 'momentum_20d'] = returns.tail(20).mean()
                        df.loc[mask, 'volatility_20d'] = returns.tail(20).std() * np.sqrt(252)
                        df.loc[mask, 'sharpe_20d'] = (returns.tail(20).mean() * 252) / (returns.tail(20).std() * np.sqrt(252) + 1e-6)
                
                logger.info("✅ Added momentum and volatility features from historical data")
            else:
                logger.warning("⚠️ No historical data fetched - using basic features only")
        
        # Fill NaN values with 0 for ML model compatibility
        df = df.fillna(0)
        
        logger.info(f"✅ Preprocessed {len(df)} positions with {len(df.columns)} features")
        
        return df
    
    except Exception as e:
        logger.error(f"Error preprocessing portfolio data: {e}")
        return pd.DataFrame()


def preprocess_market_factors(factor_data: Optional[Dict] = None, use_real_data: bool = True, lookback_days: int = 252) -> pd.DataFrame:
    """
    Preprocess market factor data (Fama-French, volatility, sentiment).
    
    Phase 5: Enhanced with real Fama-French factor data integration.
    
    Args:
        factor_data: Optional dict with market factors
        use_real_data: If True, fetch real Fama-French factors
        lookback_days: Number of days of factor data to fetch
    
    Returns:
        pd.DataFrame: Preprocessed factor matrix with rolling statistics
    """
    logger.info("📈 Preprocessing market factor data")
    
    try:
        # Phase 5: Fetch real Fama-French factors if requested
        if use_real_data:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
            
            factors_df = fetch_fama_french_factors(start_date, end_date)
            
            if not factors_df.empty:
                # Calculate rolling statistics
                factors_df['mkt_rf_20d'] = factors_df['Mkt-RF'].rolling(20).mean()
                factors_df['mkt_rf_vol'] = factors_df['Mkt-RF'].rolling(20).std() * np.sqrt(252)
                
                # Latest factor values (for single-row predictions)
                latest_factors = {
                    'mkt_rf': factors_df['Mkt-RF'].iloc[-1],
                    'smb': factors_df['SMB'].iloc[-1],
                    'hml': factors_df['HML'].iloc[-1],
                    'rmw': factors_df['RMW'].iloc[-1],
                    'cma': factors_df['CMA'].iloc[-1],
                    'rf': factors_df['RF'].iloc[-1],
                    'mkt_rf_20d_avg': factors_df['mkt_rf_20d'].iloc[-1],
                    'mkt_volatility': factors_df['mkt_rf_vol'].iloc[-1]
                }
                
                result_df = pd.DataFrame([latest_factors])
                logger.info(f"✅ Preprocessed {len(result_df.columns)} real Fama-French factors")
                return result_df
        
        # Fallback to mock factors (if use_real_data=False or if fetching failed)
        if factor_data:
            df = pd.DataFrame([factor_data])
        else:
            # Generate mock factors
            factors = {
                'mkt_rf': 0.05,
                'smb': 0.02,
                'hml': -0.01,
                'rmw': 0.03,
                'cma': 0.01,
                'rf': 0.025,
                'mkt_rf_20d_avg': 0.048,
                'mkt_volatility': 0.18
            }
            df = pd.DataFrame([factors])
        
        logger.info(f"✅ Preprocessed {len(df.columns)} market factors (mock/provided data)")
        return df
    
    except Exception as e:
        logger.error(f"Error preprocessing market factors: {e}")
        return pd.DataFrame()


def engineer_features(df: pd.DataFrame, lookback_days: int = 30) -> pd.DataFrame:
    """
    Engineer ML features from raw time series data.
    
    TODO (Phase 4):
    - Technical indicators (RSI, MACD, Bollinger Bands)
    - Statistical features (skewness, kurtosis, autocorrelation)
    - Cross-sectional features (sector momentum, industry trends)
    - Sentiment features (news, social media)
    
    Args:
        df: Raw time series data
        lookback_days: Feature calculation window
    
    Returns:
        pd.DataFrame: Engineered feature matrix
    """
    logger.info(f"🔧 Engineering features with {lookback_days}-day lookback")
    
    try:
        # TODO: Real feature engineering
        # Placeholder: add mock features
        df_features = df.copy()
        
        if 'daily_change_pct' in df.columns:
            df_features['momentum_5d'] = df['daily_change_pct'].rolling(5).mean()
            df_features['volatility_10d'] = df['daily_change_pct'].rolling(10).std()
        
        logger.info(f"✅ Engineered {len(df_features.columns)} total features")
        
        return df_features
    
    except Exception as e:
        logger.error(f"Error engineering features: {e}")
        return df


# ============================================================================
# PREDICTION GENERATION (MOCK)
# ============================================================================

def generate_mock_predictions(
    portfolio_df: pd.DataFrame,
    model_type: str = "ensemble",
    horizon_days: int = 5
) -> Dict:
    """
    Generate mock ML predictions for testing/development.
    
    TODO (Phase 4):
    - Replace with real Azure ML endpoint calls
    - Implement model selection logic (LSTM, XGBoost, ensemble)
    - Add confidence intervals
    - Include SHAP values for interpretability
    
    Args:
        portfolio_df: Preprocessed portfolio data
        model_type: ML model type ("ensemble", "lstm", "xgboost")
        horizon_days: Prediction horizon
    
    Returns:
        Dict: Predictions with metadata
    """
    logger.info(f"🤖 Generating mock predictions (model: {model_type}, horizon: {horizon_days}d)")
    
    try:
        if portfolio_df.empty:
            logger.warning("Empty portfolio, returning null predictions")
            return {
                'predictions': [],
                'model_type': model_type,
                'horizon_days': horizon_days,
                'confidence': 0.0,
                'timestamp': datetime.now().isoformat(),
                'status': 'no_data'
            }
        
        # Mock predictions (Phase 3 scaffold + Phase 20B: Add features and SHAP values)
        predictions = []
        for idx, row in portfolio_df.iterrows():
            ticker = row.get('ticker', f'TICKER_{idx}')
            
            # Generate random return prediction
            base_return = np.random.normal(0.02, 0.05)
            # PHASE 17B+: Higher confidence range (0.75-0.95) to ensure visibility in UI
            confidence = np.random.uniform(0.75, 0.95)
            
            # PHASE 20B: Add mock features and SHAP values for feature importance analysis
            mock_features = {
                'momentum_5d': np.random.uniform(-0.05, 0.05),
                'momentum_20d': np.random.uniform(-0.1, 0.1),
                'volatility_30d': np.random.uniform(0.01, 0.05),
                'volume_ratio': np.random.uniform(0.5, 2.0),
                'rsi_14': np.random.uniform(30, 70),
                'macd': np.random.uniform(-0.02, 0.02),
                'sentiment_score': np.random.uniform(-1, 1),
                'market_beta': np.random.uniform(0.5, 1.5)
            }
            
            mock_shap_values = {
                'momentum_5d': np.random.uniform(-0.01, 0.01),
                'momentum_20d': np.random.uniform(-0.015, 0.015),
                'volatility_30d': np.random.uniform(-0.008, 0.008),
                'volume_ratio': np.random.uniform(-0.005, 0.005),
                'rsi_14': np.random.uniform(-0.012, 0.012),
                'macd': np.random.uniform(-0.01, 0.01),
                'sentiment_score': np.random.uniform(-0.02, 0.02),
                'market_beta': np.random.uniform(-0.01, 0.01)
            }
            
            predictions.append({
                'ticker': ticker,
                'predicted_return': base_return,
                'confidence': confidence,
                'lower_bound': base_return - 0.03,
                'upper_bound': base_return + 0.03,
                'horizon_days': horizon_days,
                'features': mock_features,
                'shap_values': mock_shap_values
            })
        
        result = {
            'predictions': predictions,
            'model_type': model_type,
            'horizon_days': horizon_days,
            'overall_confidence': np.mean([p['confidence'] for p in predictions]),
            'timestamp': datetime.now().isoformat(),
            'status': 'mock_success',
            'note': 'Phase 3 scaffold - mock predictions only'
        }
        
        logger.info(f"✅ Generated {len(predictions)} mock predictions")
        
        return result
    
    except Exception as e:
        logger.error(f"Error generating predictions: {e}")
        return {
            'predictions': [],
            'model_type': model_type,
            'status': 'error',
            'error': str(e)
        }


def generate_strategy_simulation(
    portfolio_df: pd.DataFrame,
    strategy_config: Dict
) -> Dict:
    """
    Simulate strategy performance using ML predictions.
    
    TODO (Phase 4):
    - Integrate with Strategy Lab backtest engine
    - Add realistic transaction costs
    - Include market impact modeling
    - Compute risk-adjusted metrics
    
    Args:
        portfolio_df: Portfolio data
        strategy_config: Strategy parameters
    
    Returns:
        Dict: Simulation results
    """
    logger.info("📊 Running strategy simulation (mock)")
    
    try:
        # Mock simulation results
        simulation = {
            'total_return': np.random.uniform(0.08, 0.18),
            'sharpe_ratio': np.random.uniform(1.2, 2.5),
            'max_drawdown': np.random.uniform(-0.15, -0.05),
            'win_rate': np.random.uniform(0.52, 0.68),
            'trades': int(np.random.uniform(50, 150)),
            'turnover': np.random.uniform(0.3, 0.8),
            'daily_returns': list(np.random.normal(0.001, 0.02, 252)),
            'timestamp': datetime.now().isoformat(),
            'status': 'mock_success'
        }
        
        logger.info("✅ Strategy simulation complete (mock data)")
        
        return simulation
    
    except Exception as e:
        logger.error(f"Error in strategy simulation: {e}")
        return {'status': 'error', 'error': str(e)}


# ============================================================================
# PREDICTION CACHING
# ============================================================================

def cache_predictions(predictions: Dict, cache_key: str = "latest") -> bool:
    """
    Cache ML predictions to disk for quick retrieval.
    
    TODO (Phase 4):
    - Add versioning
    - Implement cache expiration
    - Support multiple cache backends (Redis, S3)
    
    Args:
        predictions: Prediction dictionary
        cache_key: Cache identifier
    
    Returns:
        bool: Success status
    """
    try:
        cache_dir = Path(__file__).parent.parent.parent / "cache" / "ml_predictions"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        cache_file = cache_dir / f"{cache_key}.json"
        
        with open(cache_file, 'w') as f:
            json.dump(predictions, f, indent=2)
        
        logger.info(f"✅ Cached predictions to: {cache_file}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error caching predictions: {e}")
        return False


def load_cached_predictions(cache_key: str = "latest") -> Optional[Dict]:
    """
    Load cached predictions from disk.
    
    Args:
        cache_key: Cache identifier
    
    Returns:
        Dict or None: Cached predictions if available
    """
    try:
        cache_dir = Path(__file__).parent.parent.parent / "cache" / "ml_predictions"
        cache_file = cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            logger.info(f"No cached predictions found: {cache_key}")
            return None
        
        with open(cache_file, 'r') as f:
            predictions = json.load(f)
        
        logger.info(f"✅ Loaded cached predictions: {cache_key}")
        
        return predictions
    
    except Exception as e:
        logger.error(f"Error loading cached predictions: {e}")
        return None


# ============================================================================
# DATA INGESTION FROM OTHER TABS
# ============================================================================

def ingest_portfolio_data() -> Dict:
    """
    Ingest portfolio data from Home Lab for ML processing.
    
    TODO (Phase 4):
    - Real-time data updates
    - Historical data fetching
    - Data validation
    
    Returns:
        Dict: Portfolio summary data
    """
    logger.info("📥 Ingesting portfolio data from Home Lab")
    
    try:
        # Import dynamically to avoid circular dependencies
        from ..home_lab.helpers import get_portfolio_summary
        
        portfolio_data = get_portfolio_summary()
        logger.info(f"✅ Ingested portfolio: {portfolio_data.get('total_positions', 0)} positions")
        
        return portfolio_data
    
    except Exception as e:
        logger.error(f"Error ingesting portfolio data: {e}")
        return {}


def ingest_market_forecast_data() -> Dict:
    """
    Ingest market forecast data for ML feature engineering.
    
    TODO (Phase 4):
    - Connect to Market Forecast tab data sources
    - Extract volatility predictions
    - Include sentiment scores
    
    Returns:
        Dict: Market forecast data
    """
    logger.info("📥 Ingesting market forecast data")
    
    try:
        # TODO: Real integration with Market Forecast tab
        # Placeholder mock data
        forecast_data = {
            'sp500_forecast': 0.05,
            'volatility_forecast': 0.18,
            'sentiment_score': 0.65,
            'regime': 'normal',
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info("✅ Ingested market forecast data (mock)")
        
        return forecast_data
    
    except Exception as e:
        logger.error(f"Error ingesting market forecast: {e}")
        return {}


# ============================================================================
# DIAGNOSTICS
# ============================================================================

def get_ml_diagnostics() -> Dict:
    """
    Get diagnostic information about ML lab status.
    
    Returns:
        Dict: Diagnostic metrics
    """
    logger.info("🔍 Running ML lab diagnostics")
    
    try:
        diagnostics = {
            'status': 'scaffold_mode',
            'version': '1.0.0',
            'last_prediction': 'N/A',
            'cache_status': 'available',
            'model_loaded': False,
            'azure_connection': 'not_configured',
            'data_sources': {
                'portfolio': 'connected',
                'market_forecast': 'mock',
                'factors': 'mock'
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Check cache directory
        cache_dir = Path(__file__).parent.parent.parent / "cache" / "ml_predictions"
        if cache_dir.exists():
            cached_files = list(cache_dir.glob("*.json"))
            diagnostics['cached_predictions'] = len(cached_files)
        else:
            diagnostics['cached_predictions'] = 0
        
        logger.info("✅ Diagnostics complete")
        
        return diagnostics
    
    except Exception as e:
        logger.error(f"Error in diagnostics: {e}")
        return {'status': 'error', 'error': str(e)}


# ============================================================================
# MOCK DATA GENERATION
# ============================================================================

def generate_mock_historical_data(
    ticker: str,
    days: int = 252
) -> pd.DataFrame:
    """
    Generate mock historical price data for testing.
    
    Args:
        ticker: Stock ticker
        days: Number of days to generate
    
    Returns:
        pd.DataFrame: Mock price data
    """
    logger.info(f"📊 Generating {days} days of mock data for {ticker}")
    
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # Random walk with drift
    returns = np.random.normal(0.0005, 0.02, days)
    prices = 100 * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        'date': dates,
        'ticker': ticker,
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, days),
        'returns': returns
    })
    
    return df


def generate_mock_factor_data(days: int = 252) -> pd.DataFrame:
    """
    Generate mock Fama-French factor data.
    
    Args:
        days: Number of days
    
    Returns:
        pd.DataFrame: Mock factor returns
    """
    logger.info(f"📊 Generating {days} days of mock factor data")
    
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    df = pd.DataFrame({
        'date': dates,
        'mkt_rf': np.random.normal(0.0004, 0.01, days),
        'smb': np.random.normal(0.0001, 0.005, days),
        'hml': np.random.normal(0.0001, 0.005, days),
        'rmw': np.random.normal(0.0001, 0.004, days),
        'cma': np.random.normal(0.0001, 0.004, days)
    })
    
    return df


logger.info("✓ Azure ML Lab helpers loaded (Phase 3 Scaffold)")

"""
Azure ML Lab - Database Layer

PostgreSQL persistence for ML predictions, metrics, and model insights.
Phase 20A: Full database integration with observability.
"""

import logging
import psycopg2
import psycopg2.extras
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import json
import os
import numpy as np

logger = logging.getLogger(__name__)


def sanitize_for_db(value: Any) -> Any:
    """Convert numpy types to Python native types for PostgreSQL."""
    if isinstance(value, (np.integer, np.floating)):
        return float(value)
    elif isinstance(value, np.ndarray):
        return value.tolist()
    elif isinstance(value, dict):
        return {k: sanitize_for_db(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [sanitize_for_db(item) for item in value]
    return value

# Database connection from environment
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    # Construct from individual params
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres_db')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'dashboard_user')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'newpassword')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'financial_dashboard')
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# ============================================================================
# SCHEMA INITIALIZATION
# ============================================================================

def initialize_ml_schema() -> bool:
    """
    Initialize PostgreSQL schema for Azure ML predictions and metrics.
    
    Creates tables:
    - ml_predictions: Individual ticker predictions
    - ml_prediction_runs: Batch prediction metadata
    - ml_model_metrics: Model performance tracking
    - ml_insights: Cached insights and analysis
    
    Returns:
        bool: Success status
    """
    logger.info("🗄️ Initializing Azure ML database schema...")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Table 1: ML Prediction Runs (batch metadata)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ml_prediction_runs (
                run_id SERIAL PRIMARY KEY,
                model_type VARCHAR(50) NOT NULL,
                horizon_days INTEGER NOT NULL,
                num_predictions INTEGER NOT NULL,
                overall_confidence FLOAT,
                confidence_threshold FLOAT,
                prediction_target VARCHAR(50),
                universe VARCHAR(100),
                status VARCHAR(50) NOT NULL,
                source VARCHAR(50) NOT NULL,  -- 'azure_ml_rest_api', 'azure_ml_sdk', 'mock_fallback'
                fallback_reason VARCHAR(255),
                error_message TEXT,
                latency_ms FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB
            )
        """)
        
        # Table 2: ML Predictions (individual ticker predictions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ml_predictions (
                prediction_id SERIAL PRIMARY KEY,
                run_id INTEGER REFERENCES ml_prediction_runs(run_id) ON DELETE CASCADE,
                ticker VARCHAR(20) NOT NULL,
                predicted_return FLOAT NOT NULL,
                confidence FLOAT NOT NULL,
                lower_bound FLOAT,
                upper_bound FLOAT,
                horizon_days INTEGER NOT NULL,
                features JSONB,
                shap_values JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table 3: ML Model Metrics (performance tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ml_model_metrics (
                metric_id SERIAL PRIMARY KEY,
                model_type VARCHAR(50) NOT NULL,
                metric_name VARCHAR(100) NOT NULL,
                metric_value FLOAT NOT NULL,
                evaluation_date DATE NOT NULL,
                horizon_days INTEGER,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table 4: ML Insights (cached analysis)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ml_insights (
                insight_id SERIAL PRIMARY KEY,
                run_id INTEGER REFERENCES ml_prediction_runs(run_id) ON DELETE CASCADE,
                insight_type VARCHAR(50) NOT NULL,  -- 'summary', 'top_picks', 'risk_analysis'
                insight_data JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ml_pred_runs_created ON ml_prediction_runs(created_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ml_pred_ticker ON ml_predictions(ticker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ml_pred_run_id ON ml_predictions(run_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ml_metrics_model ON ml_model_metrics(model_type, evaluation_date DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ml_insights_type ON ml_insights(insight_type, created_at DESC)")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("✅ Azure ML database schema initialized successfully")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error initializing ML schema: {e}")
        return False


# ============================================================================
# PREDICTION PERSISTENCE
# ============================================================================

def save_prediction_run(
    model_type: str,
    horizon_days: int,
    predictions: List[Dict],
    overall_confidence: float,
    confidence_threshold: float,
    prediction_target: str,
    universe: str,
    status: str,
    source: str,
    fallback_reason: Optional[str] = None,
    error_message: Optional[str] = None,
    latency_ms: Optional[float] = None,
    metadata: Optional[Dict] = None
) -> Optional[int]:
    """
    Save ML prediction run to database.
    
    Args:
        model_type: Model used (ensemble, lstm, xgboost, etc.)
        horizon_days: Prediction horizon
        predictions: List of prediction dicts
        overall_confidence: Aggregate confidence score
        confidence_threshold: Filtering threshold
        prediction_target: Target metric (return, volatility, etc.)
        universe: Stock universe used
        status: Run status (success, error, partial)
        source: Data source (azure_ml_rest_api, mock_fallback, etc.)
        fallback_reason: Reason for fallback (if applicable)
        error_message: Error details (if applicable)
        latency_ms: API call latency in milliseconds
        metadata: Additional metadata
    
    Returns:
        int: run_id if successful, None otherwise
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Insert prediction run (sanitize numpy types)
        cursor.execute("""
            INSERT INTO ml_prediction_runs (
                model_type, horizon_days, num_predictions, overall_confidence,
                confidence_threshold, prediction_target, universe, status, source,
                fallback_reason, error_message, latency_ms, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING run_id
        """, (
            model_type,
            horizon_days,
            len(predictions),
            float(overall_confidence) if overall_confidence is not None else 0.0,
            float(confidence_threshold) if confidence_threshold is not None else 0.0,
            prediction_target,
            universe,
            status,
            source,
            fallback_reason,
            error_message,
            float(latency_ms) if latency_ms is not None else None,
            json.dumps(sanitize_for_db(metadata)) if metadata else None
        ))
        
        run_id = cursor.fetchone()[0]
        
        # Insert individual predictions (sanitize numpy types)
        for pred in predictions:
            cursor.execute("""
                INSERT INTO ml_predictions (
                    run_id, ticker, predicted_return, confidence,
                    lower_bound, upper_bound, horizon_days, features, shap_values
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                run_id,
                pred.get('ticker'),
                float(pred.get('predicted_return', 0)) if pred.get('predicted_return') is not None else 0.0,
                float(pred.get('confidence', 0)) if pred.get('confidence') is not None else 0.0,
                float(pred.get('lower_bound', 0)) if pred.get('lower_bound') is not None else None,
                float(pred.get('upper_bound', 0)) if pred.get('upper_bound') is not None else None,
                pred.get('horizon_days', horizon_days),
                json.dumps(sanitize_for_db(pred.get('features'))) if pred.get('features') else None,
                json.dumps(sanitize_for_db(pred.get('shap_values'))) if pred.get('shap_values') else None
            ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Saved prediction run {run_id} with {len(predictions)} predictions to database")
        return run_id
    
    except Exception as e:
        logger.error(f"❌ Error saving prediction run: {e}")
        return None


def get_latest_predictions(limit: int = 100) -> List[Dict]:
    """
    Fetch latest predictions from database.
    
    Args:
        limit: Maximum number of predictions to return
    
    Returns:
        List[Dict]: Latest predictions with metadata
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute("""
            SELECT 
                p.prediction_id,
                p.ticker,
                p.predicted_return,
                p.confidence,
                p.lower_bound,
                p.upper_bound,
                p.horizon_days,
                p.created_at,
                r.model_type,
                r.source,
                r.run_id
            FROM ml_predictions p
            JOIN ml_prediction_runs r ON p.run_id = r.run_id
            ORDER BY p.created_at DESC
            LIMIT %s
        """, (limit,))
        
        predictions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Fetched {len(predictions)} latest predictions from database")
        return [dict(pred) for pred in predictions]
    
    except Exception as e:
        logger.error(f"❌ Error fetching predictions: {e}")
        return []


def get_prediction_run(run_id: int) -> Optional[Dict]:
    """
    Fetch a specific prediction run with all predictions.
    
    Args:
        run_id: Run ID to fetch
    
    Returns:
        Dict: Prediction run data with predictions list
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Fetch run metadata
        cursor.execute("SELECT * FROM ml_prediction_runs WHERE run_id = %s", (run_id,))
        run = cursor.fetchone()
        
        if not run:
            logger.warning(f"Run {run_id} not found")
            return None
        
        # Fetch predictions for this run
        cursor.execute("SELECT * FROM ml_predictions WHERE run_id = %s ORDER BY confidence DESC", (run_id,))
        predictions = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        result = dict(run)
        result['predictions'] = [dict(pred) for pred in predictions]
        
        logger.info(f"✅ Fetched run {run_id} with {len(predictions)} predictions")
        return result
    
    except Exception as e:
        logger.error(f"❌ Error fetching prediction run: {e}")
        return None


# ============================================================================
# MODEL METRICS
# ============================================================================

def save_model_metrics(
    model_type: str,
    metrics: Dict[str, float],
    evaluation_date: datetime,
    horizon_days: Optional[int] = None,
    metadata: Optional[Dict] = None
) -> bool:
    """
    Save model performance metrics to database.
    
    Args:
        model_type: Model identifier
        metrics: Dict of metric_name -> metric_value
        evaluation_date: Date of evaluation
        horizon_days: Prediction horizon (optional)
        metadata: Additional metadata
    
    Returns:
        bool: Success status
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        for metric_name, metric_value in metrics.items():
            cursor.execute("""
                INSERT INTO ml_model_metrics (
                    model_type, metric_name, metric_value, evaluation_date,
                    horizon_days, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                model_type,
                metric_name,
                metric_value,
                evaluation_date,
                horizon_days,
                json.dumps(metadata) if metadata else None
            ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Saved {len(metrics)} metrics for model {model_type}")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error saving model metrics: {e}")
        return False


def get_model_metrics(model_type: str, limit: int = 50) -> List[Dict]:
    """
    Fetch latest model metrics from database.
    
    Args:
        model_type: Model identifier
        limit: Maximum number of metrics to return
    
    Returns:
        List[Dict]: Model metrics
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute("""
            SELECT * FROM ml_model_metrics
            WHERE model_type = %s
            ORDER BY evaluation_date DESC, created_at DESC
            LIMIT %s
        """, (model_type, limit))
        
        metrics = cursor.fetchall()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Fetched {len(metrics)} metrics for model {model_type}")
        return [dict(metric) for metric in metrics]
    
    except Exception as e:
        logger.error(f"❌ Error fetching model metrics: {e}")
        return []


# ============================================================================
# INSIGHTS PERSISTENCE
# ============================================================================

def save_insight(run_id: int, insight_type: str, insight_data: Dict) -> bool:
    """
    Save insight to database.
    
    Args:
        run_id: Associated prediction run ID
        insight_type: Type of insight (summary, top_picks, risk_analysis)
        insight_data: Insight data dictionary
    
    Returns:
        bool: Success status
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO ml_insights (run_id, insight_type, insight_data)
            VALUES (%s, %s, %s)
        """, (run_id, insight_type, json.dumps(insight_data)))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Saved insight type '{insight_type}' for run {run_id}")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error saving insight: {e}")
        return False


def get_insights(run_id: Optional[int] = None, insight_type: Optional[str] = None, limit: int = 10) -> List[Dict]:
    """
    Fetch insights from database.
    
    Args:
        run_id: Filter by run ID (optional)
        insight_type: Filter by insight type (optional)
        limit: Maximum number of insights to return
    
    Returns:
        List[Dict]: Insights
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        query = "SELECT * FROM ml_insights WHERE 1=1"
        params = []
        
        if run_id:
            query += " AND run_id = %s"
            params.append(run_id)
        
        if insight_type:
            query += " AND insight_type = %s"
            params.append(insight_type)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        insights = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Fetched {len(insights)} insights")
        return [dict(insight) for insight in insights]
    
    except Exception as e:
        logger.error(f"❌ Error fetching insights: {e}")
        return []


def get_feature_importance(run_id: Optional[int] = None, limit: int = 20) -> List[Dict]:
    """
    Get feature importance from predictions SHAP values or compute from features.
    Phase 20B: Extract feature importance for Model Insights tab.
    
    Args:
        run_id: Specific run ID (optional, defaults to latest)
        limit: Max features to return
    
    Returns:
        List[Dict]: Feature importance scores
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # If no run_id specified, get latest
        if not run_id:
            cursor.execute("SELECT MAX(run_id) FROM ml_predictions")
            result = cursor.fetchone()
            run_id = result['max'] if result else None
        
        if not run_id:
            logger.warning("No predictions found for feature importance")
            return []
        
        # Get SHAP values or features from predictions
        cursor.execute("""
            SELECT ticker, features, shap_values, confidence
            FROM ml_predictions
            WHERE run_id = %s AND (features IS NOT NULL OR shap_values IS NOT NULL)
            ORDER BY confidence DESC
        """, (run_id,))
        
        predictions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not predictions:
            logger.warning(f"No feature data found for run_id={run_id}")
            return []
        
        # Aggregate feature importance across predictions
        feature_scores = {}
        
        for pred in predictions:
            # Try SHAP values first
            if pred['shap_values']:
                shap_data = pred['shap_values'] if isinstance(pred['shap_values'], dict) else {}
                for feature, value in shap_data.items():
                    if feature not in feature_scores:
                        feature_scores[feature] = {'sum': 0, 'count': 0, 'values': []}
                    feature_scores[feature]['sum'] += abs(float(value))
                    feature_scores[feature]['count'] += 1
                    feature_scores[feature]['values'].append(float(value))
            
            # Fallback to features if no SHAP
            elif pred['features']:
                features_data = pred['features'] if isinstance(pred['features'], dict) else {}
                for feature, value in features_data.items():
                    if feature not in feature_scores:
                        feature_scores[feature] = {'sum': 0, 'count': 0, 'values': []}
                    feature_scores[feature]['sum'] += abs(float(value)) * 0.5  # Lower weight for raw features
                    feature_scores[feature]['count'] += 1
                    feature_scores[feature]['values'].append(float(value))
        
        # Compute average importance
        result = []
        for feature, data in feature_scores.items():
            avg_importance = data['sum'] / data['count'] if data['count'] > 0 else 0
            result.append({
                'feature': feature,
                'importance': avg_importance,
                'count': data['count'],
                'mean_value': sum(data['values']) / len(data['values']) if data['values'] else 0
            })
        
        # Sort by importance and limit
        result.sort(key=lambda x: x['importance'], reverse=True)
        
        logger.info(f"✅ Computed feature importance for run_id={run_id}: {len(result[:limit])} features")
        return result[:limit]
    
    except Exception as e:
        logger.error(f"❌ Error getting feature importance: {e}")
        return []


def compute_risk_metrics(run_id: Optional[int] = None) -> Dict:
    """
    Compute risk analysis metrics from predictions.
    Phase 20B: Volatility, VaR, Sharpe ratio, concentration risk.
    
    Args:
        run_id: Specific run ID (optional, defaults to latest)
    
    Returns:
        Dict: Risk metrics
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # If no run_id specified, get latest
        if not run_id:
            cursor.execute("SELECT MAX(run_id) FROM ml_predictions")
            result = cursor.fetchone()
            run_id = result['max'] if result else None
        
        if not run_id:
            return {'error': 'No predictions found'}
        
        # Get predictions
        cursor.execute("""
            SELECT ticker, predicted_return, confidence, 
                   lower_bound, upper_bound
            FROM ml_predictions
            WHERE run_id = %s
            ORDER BY confidence DESC
        """, (run_id,))
        
        predictions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not predictions:
            return {'error': f'No predictions for run_id={run_id}'}
        
        # Compute metrics
        import numpy as np
        
        returns = [p['predicted_return'] for p in predictions]
        confidences = [p['confidence'] for p in predictions]
        
        # Portfolio-level metrics
        avg_return = np.mean(returns)
        volatility = np.std(returns)
        sharpe = avg_return / volatility if volatility > 0 else 0
        
        # Value at Risk (95% confidence)
        var_95 = np.percentile(returns, 5)
        
        # Max drawdown (predicted)
        max_loss = min(returns)
        max_gain = max(returns)
        
        # Concentration risk (HHI of abs returns)
        abs_returns = [abs(r) for r in returns]
        total = sum(abs_returns)
        shares = [r/total for r in abs_returns] if total > 0 else [0] * len(abs_returns)
        hhi = sum([s**2 for s in shares])
        
        # Confidence-weighted metrics
        weights = [c / sum(confidences) for c in confidences]
        weighted_return = sum([r * w for r, w in zip(returns, weights)])
        
        result = {
            'run_id': run_id,
            'num_predictions': len(predictions),
            'avg_return': float(avg_return),
            'volatility': float(volatility),
            'sharpe_ratio': float(sharpe),
            'var_95': float(var_95),
            'max_loss': float(max_loss),
            'max_gain': float(max_gain),
            'concentration_hhi': float(hhi),
            'weighted_return': float(weighted_return),
            'avg_confidence': float(np.mean(confidences))
        }
        
        logger.info(f"✅ Computed risk metrics for run_id={run_id}")
        return result
    
    except Exception as e:
        logger.error(f"❌ Error computing risk metrics: {e}")
        return {'error': str(e)}


logger.info("✓ Azure ML database layer loaded (Phase 20A + 20B extensions)")

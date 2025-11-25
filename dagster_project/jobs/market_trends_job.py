"""
Market Trends Pipeline Job

Dagster job for orchestrating the market trends ML pipeline:
1. Fetch market data (from Finnhub/Polygon/Alpaca)
2. Clean and validate data
3. Engineer features
4. Train ML model
5. Evaluate model performance
"""

from dagster import op, job, OpExecutionContext, Out, In, DynamicOut, DynamicOutput
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


@op(
    description="Fetch market data from multiple sources with fallback",
    out=Out(Dict[str, Any])
)
def fetch_market_data_op(context: OpExecutionContext) -> Dict[str, Any]:
    """
    Fetch market data using unified ingestion layer
    """
    from data_ingestion.ingest_market_data import fetch_market_data
    
    # Default tickers (can be parameterized via config)
    tickers = context.op_config.get('tickers', ['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN'])
    period = context.op_config.get('period', '3mo')
    
    context.log.info(f"Fetching data for {len(tickers)} tickers: {tickers}")
    
    result = fetch_market_data(tickers, period)
    
    if result['success']:
        context.log.info(f"✅ Fetched data from {result['source']} for {len(result['data'])} tickers")
    else:
        context.log.error(f"❌ Failed to fetch data: {result['errors']}")
    
    return result


@op(
    description="Clean and validate market data",
    ins={"raw_data": In(Dict[str, Any])},
    out=Out(List[Dict[str, Any]])
)
def clean_data_op(context: OpExecutionContext, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Clean and validate market data
    """
    if not raw_data.get('success'):
        context.log.error("No data to clean (fetch failed)")
        return []
    
    data = raw_data.get('data', [])
    
    # Filter out tickers with insufficient data
    cleaned = []
    for ticker_data in data:
        historical = ticker_data.get('historical', {})
        
        # Check data format and extract length
        if 'c' in historical:  # Finnhub
            data_length = len(historical.get('c', []))
        elif 'results' in historical:  # Polygon
            data_length = len(historical.get('results', []))
        elif 'bars' in historical:  # Alpaca
            data_length = len(historical.get('bars', []))
        else:
            data_length = 0
        
        if data_length >= 20:  # Need at least 20 days for features
            cleaned.append(ticker_data)
        else:
            context.log.warning(f"Skipping {ticker_data.get('ticker')}: only {data_length} days")
    
    context.log.info(f"✅ Cleaned data: {len(cleaned)}/{len(data)} tickers valid")
    
    return cleaned


@op(
    description="Train ML model for market trend prediction with registry integration",
    ins={"clean_data": In(List[Dict[str, Any]])},
    out=Out(Dict[str, Any])
)
def train_model_op(context: OpExecutionContext, clean_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Train RandomForest model using new registry-based training
    """
    # Import from new ml module
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    from ml.train_model import train_market_trends_model
    
    if len(clean_data) == 0:
        context.log.error("No data available for training")
        return {'success': False, 'error': 'No training data'}
    
    context.log.info(f"Training model with {len(clean_data)} tickers")
    
    try:
        result = train_market_trends_model(
            clean_data, 
            model_name="market_trend_rf",
            register=True
        )
        
        if result is not None:
            model, metrics = result
            context.log.info("✅ Model trained and registered successfully")
            context.log.info(f"📊 Metrics: accuracy={metrics['accuracy']:.4f}, f1={metrics['f1']:.4f}")
            return {
                'success': True,
                'metrics': metrics,
                'model': 'saved_to_registry'
            }
        else:
            context.log.error("❌ Model training failed")
            return {'success': False, 'error': 'Training failed'}
    
    except Exception as e:
        context.log.error(f"❌ Training error: {e}")
        import traceback
        context.log.error(traceback.format_exc())
        return {'success': False, 'error': str(e)}


@op(
    description="Evaluate trained model and log metrics from registry",
    ins={"training_result": In(Dict[str, Any])},
    out=Out(Dict[str, Any])
)
def evaluate_model_op(context: OpExecutionContext, training_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load latest model from registry and log comprehensive metrics
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    from ml.model_registry import get_latest_model, compare_models
    
    if not training_result.get('success'):
        context.log.error("Cannot evaluate: training failed")
        return {'success': False}
    
    try:
        # Get latest model from registry
        latest = get_latest_model("market_trend_rf")
        
        if latest is None:
            context.log.error("No models found in registry")
            return {'success': False}
        
        context.log.info(f"📊 Model Evaluation:")
        context.log.info(f"  Name: {latest['model_name']}")
        context.log.info(f"  Version: {latest['version']}")
        context.log.info(f"  Timestamp: {latest['timestamp']}")
        context.log.info(f"  Commit: {latest['source_commit']}")
        context.log.info(f"  Metrics:")
        
        metrics = latest.get('metrics', {})
        for metric, value in metrics.items():
            if isinstance(value, (int, float)):
                context.log.info(f"    {metric}: {value:.4f}")
            else:
                context.log.info(f"    {metric}: {value}")
        
        # Compare with previous versions
        all_versions = compare_models("market_trend_rf", metric_key="accuracy")
        if len(all_versions) > 1:
            context.log.info(f"📈 Model Comparison ({len(all_versions)} versions):")
            for i, version in enumerate(all_versions[:3]):  # Top 3
                acc = version.get('metrics', {}).get('accuracy', 0)
                context.log.info(f"  {i+1}. {version['version']}: accuracy={acc:.4f}")
        
        return {
            'success': True,
            'version': latest['version'],
            'metrics': metrics
        }
    
    except Exception as e:
        context.log.error(f"❌ Evaluation error: {e}")
        import traceback
        context.log.error(traceback.format_exc())
        return {'success': False, 'error': str(e)}


@op(
    description="Monitor model performance for drift detection",
    out=Out(Dict[str, Any])
)
def monitor_model_performance_op(context: OpExecutionContext) -> Dict[str, Any]:
    """
    Run model monitoring to detect performance drift
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    from workflows.sensors.model_monitoring_sensor import monitor_model_performance
    
    try:
        context.log.info("Running model performance monitoring...")
        result = monitor_model_performance(model_name="market_trend_rf")
        
        context.log.info(f"📊 Monitoring Result:")
        context.log.info(f"  Model: {result['model_name']} {result['model_version']}")
        context.log.info(f"  Baseline Accuracy: {result['baseline_accuracy']:.4f}")
        context.log.info(f"  Current Accuracy: {result['current_accuracy']:.4f}")
        context.log.info(f"  Accuracy Drop: {result['accuracy_drop']:.4f}")
        context.log.info(f"  Max KS Drift: {result['max_ks_statistic']:.4f}")
        context.log.info(f"  Status: {result['status']}")
        
        if result['status'] == 'alert':
            context.log.warning("⚠️ Model performance alert detected!")
        else:
            context.log.info("✅ Model performance is healthy")
        
        return result
    
    except Exception as e:
        context.log.error(f"❌ Monitoring error: {e}")
        import traceback
        context.log.error(traceback.format_exc())
        return {'success': False, 'error': str(e)}


@job(
    description="Market Trends ML Pipeline: Fetch → Clean → Train → Evaluate → Monitor",
    config={
        "ops": {
            "fetch_market_data_op": {
                "config": {
                    "tickers": ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "AMD"],
                    "period": "3mo"
                }
            }
        }
    }
)
def market_trends_pipeline():
    """
    Complete pipeline for market trends ML model with monitoring
    """
    raw_data = fetch_market_data_op()
    clean_data = clean_data_op(raw_data)
    training_result = train_model_op(clean_data)
    evaluation = evaluate_model_op(training_result)
    monitor_model_performance_op()

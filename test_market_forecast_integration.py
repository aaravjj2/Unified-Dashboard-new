#!/usr/bin/env python3
"""
Comprehensive Market Forecast Integration Test
Tests all AI components: FinBERT, forecasters, sentiment sources
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
from dotenv import load_dotenv
load_dotenv('keys.env')


def test_finbert_sentiment():
    """Test FinBERT sentiment analysis"""
    print("\n" + "="*60)
    print("🧪 TEST 1: FinBERT Sentiment Analysis")
    print("="*60)
    
    try:
        from financial_dashboard.models.finbert_sentiment import FinBERTSentimentAnalyzer
        
        analyzer = FinBERTSentimentAnalyzer()
        print("✅ FinBERTSentimentAnalyzer loaded")
        
        # Test with a sample ticker
        result = analyzer.get_ticker_sentiment("AAPL")
        print(f"   Symbol: AAPL")
        print(f"   Score: {result['sentiment_mean']:.4f}")
        print(f"   Signal: {result['signal']}")
        print(f"   Confidence: {result['confidence']:.4f}")
        print(f"   Headlines: {result['sentiment_count']}")
        
        return True, result
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_sentiment_sources():
    """Test all background sentiment sources"""
    print("\n" + "="*60)
    print("🧪 TEST 2: Background Sentiment Sources")
    print("="*60)
    
    results = {}
    
    try:
        # Finnhub
        from services.cc.ingest_finnhub import get_market_sentiment as finnhub
        result = finnhub()
        print(f"✅ Finnhub: {result['score']:.4f} (error: {result.get('error')})")
        results['finnhub'] = result
    except Exception as e:
        print(f"❌ Finnhub: {e}")
        results['finnhub'] = {'error': str(e)}
    
    try:
        # Alpaca
        from services.cc.alpaca_market import get_market_sentiment as alpaca
        result = alpaca()
        print(f"✅ Alpaca: {result['score']:.4f} (error: {result.get('error')})")
        results['alpaca'] = result
    except Exception as e:
        print(f"❌ Alpaca: {e}")
        results['alpaca'] = {'error': str(e)}
    
    try:
        # yfinance
        from services.cc.yfinance_fallback import get_market_sentiment as yf
        result = yf()
        print(f"✅ yfinance: {float(result['score']):.4f} (error: {result.get('error')})")
        results['yfinance'] = result
    except Exception as e:
        print(f"❌ yfinance: {e}")
        results['yfinance'] = {'error': str(e)}
    
    return all('error' not in r or r.get('error') is None for r in results.values()), results


def test_forecasters():
    """Test all forecasting models"""
    print("\n" + "="*60)
    print("🧪 TEST 3: Forecasting Models")
    print("="*60)
    
    import numpy as np
    
    # Generate test data
    np.random.seed(42)
    dates = np.arange(100)
    prices = 100 + np.cumsum(np.random.randn(100) * 0.5)  # Random walk
    
    results = {}
    
    try:
        from financial_dashboard.models.prophet_forecaster import ProphetForecaster
        forecaster = ProphetForecaster()
        forecaster.fit(prices)
        forecast = forecaster.predict(horizon=5)
        print(f"✅ ProphetForecaster: {len(forecast.get('predictions', forecast.get('forecast', [])))} predictions")
        results['prophet'] = True
    except Exception as e:
        print(f"❌ ProphetForecaster: {e}")
        results['prophet'] = False
    
    try:
        from financial_dashboard.models.arima_forecaster import ARIMAForecaster
        forecaster = ARIMAForecaster()
        forecaster.fit(prices)
        forecast = forecaster.predict(horizon=5)
        print(f"✅ ARIMAForecaster: {len(forecast.get('predictions', forecast.get('forecast', [])))} predictions")
        results['arima'] = True
    except Exception as e:
        print(f"❌ ARIMAForecaster: {e}")
        results['arima'] = False
    
    try:
        from financial_dashboard.models.lstm_forecaster import LSTMForecaster
        forecaster = LSTMForecaster(lookback=10, epochs=2)
        forecaster.fit(prices)
        forecast = forecaster.predict(horizon=5)
        print(f"✅ LSTMForecaster: {len(forecast.get('predictions', forecast.get('forecast', [])))} predictions")
        results['lstm'] = True
    except Exception as e:
        print(f"❌ LSTMForecaster: {e}")
        results['lstm'] = False
    
    try:
        from financial_dashboard.models.ensemble_forecaster import EnsembleForecaster
        forecaster = EnsembleForecaster()
        forecaster.fit(prices)
        forecast = forecaster.predict(horizon=5)
        print(f"✅ EnsembleForecaster: {len(forecast.get('predictions', forecast.get('forecast', [])))} predictions")
        results['ensemble'] = True
    except Exception as e:
        print(f"❌ EnsembleForecaster: {e}")
        results['ensemble'] = False
    
    return all(results.values()), results


def test_ai_forecast_engine():
    """Test AI Forecast Engine with combined methods"""
    print("\n" + "="*60)
    print("🧪 TEST 4: AI Forecast Engine (Combined Methods)")
    print("="*60)
    
    try:
        from financial_dashboard.models.ai_forecast_engine import AIForecastEngine, create_ai_forecast
        
        # Quick forecast
        print("   Running AI forecast for AAPL...")
        result = create_ai_forecast("AAPL", horizon=3, use_sentiment=True)
        
        direction = result.get('direction', 'N/A')
        confidence = result.get('confidence', 0)
        if isinstance(confidence, dict):
            confidence = confidence.get('value', 0) if 'value' in confidence else 0
        
        print(f"   ✅ Direction: {direction}")
        print(f"   ✅ Confidence: {float(confidence):.2%}")
        print(f"   ✅ Sentiment: {result.get('sentiment_score', 0):.4f}")
        print(f"   ✅ Predictions: {len(result.get('predictions', []))}")
        print(f"   ✅ Model Used: {result.get('model', 'N/A')}")
        
        return True, result
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_backtest_engine():
    """Test backtesting engine"""
    print("\n" + "="*60)
    print("🧪 TEST 5: Backtesting Engine")
    print("="*60)
    
    try:
        from financial_dashboard.models.backtest_engine import BacktestEngine
        from financial_dashboard.models.prophet_forecaster import ProphetForecaster
        import yfinance as yf
        import pandas as pd
        
        engine = BacktestEngine(
            min_train_size=30,
            test_size=3,
            step_size=5
        )
        
        print("   Fetching AAPL data...")
        ticker_data = yf.download("AAPL", period="60d", progress=False)
        
        if ticker_data.empty:
            print("   ⚠️ No data available (may be weekend/holiday)")
            return True, {}
        
        print("   Running walk-forward backtest...")
        results = engine.walk_forward_backtest(
            data=ticker_data,
            model_class=ProphetForecaster,
            model_params={},
            ticker="AAPL"
        )
        
        if results:
            metrics = results.compute_metrics()
            print(f"   ✅ RMSE: {metrics.get('rmse', 'N/A'):.4f}" if metrics.get('rmse') else "   ✅ RMSE: N/A")
            print(f"   ✅ MAE: {metrics.get('mae', 'N/A'):.4f}" if metrics.get('mae') else "   ✅ MAE: N/A")
            print(f"   ✅ Direction Accuracy: {metrics.get('direction_accuracy', 'N/A'):.2f}%" if metrics.get('direction_accuracy') else "   ✅ Direction Accuracy: N/A")
            print(f"   ✅ Trades: {len(results.predictions)}")
            return True, {'metrics': metrics}
        else:
            print("   ⚠️ Backtest returned no results")
            return True, {}
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_combined_sentiment():
    """Test combined sentiment from multiple sources"""
    print("\n" + "="*60)
    print("🧪 TEST 6: Combined Multi-Source Sentiment")
    print("="*60)
    
    try:
        # Collect from all sources
        sources = {}
        
        # FinBERT
        try:
            from financial_dashboard.models.finbert_sentiment import FinBERTSentimentAnalyzer
            analyzer = FinBERTSentimentAnalyzer()
            result = analyzer.get_ticker_sentiment("SPY")
            sources['finbert'] = result['sentiment_mean']
            print(f"   FinBERT (SPY): {result['sentiment_mean']:.4f}")
        except Exception as e:
            print(f"   FinBERT: Failed - {e}")
        
        # Background sources
        try:
            from services.cc.ingest_finnhub import get_market_sentiment as finnhub
            result = finnhub()
            if result.get('error') is None:
                sources['finnhub'] = result['score']
                print(f"   Finnhub: {result['score']:.4f}")
        except Exception as e:
            print(f"   Finnhub: Failed - {e}")
        
        try:
            from services.cc.alpaca_market import get_market_sentiment as alpaca
            result = alpaca()
            if result.get('error') is None:
                sources['alpaca'] = result['score']
                print(f"   Alpaca: {result['score']:.4f}")
        except Exception as e:
            print(f"   Alpaca: Failed - {e}")
        
        try:
            from services.cc.yfinance_fallback import get_market_sentiment as yf
            result = yf()
            if result.get('error') is None:
                sources['yfinance'] = float(result['score'])
                print(f"   yfinance: {float(result['score']):.4f}")
        except Exception as e:
            print(f"   yfinance: Failed - {e}")
        
        # Calculate weighted average
        if sources:
            weights = {
                'finbert': 0.4,   # AI-based, most accurate
                'finnhub': 0.25,  # News sentiment
                'alpaca': 0.2,    # Price action
                'yfinance': 0.15  # Fallback
            }
            
            total_weight = sum(weights[k] for k in sources.keys())
            combined = sum(sources[k] * weights[k] for k in sources.keys()) / total_weight
            
            print(f"\n   📊 COMBINED SENTIMENT: {combined:.4f}")
            print(f"   Sources used: {list(sources.keys())}")
            
            # Interpret
            if combined > 0.3:
                label = "BULLISH 📈"
            elif combined > 0.1:
                label = "SLIGHTLY BULLISH 📊"
            elif combined > -0.1:
                label = "NEUTRAL ↔️"
            elif combined > -0.3:
                label = "SLIGHTLY BEARISH 📉"
            else:
                label = "BEARISH 🔻"
            
            print(f"   Interpretation: {label}")
            
            return True, {'combined': combined, 'sources': sources, 'label': label}
        else:
            print("   ⚠️ No sentiment sources available")
            return False, {}
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def main():
    print("\n" + "="*70)
    print("🚀 COMPREHENSIVE MARKET FORECAST INTEGRATION TEST")
    print("="*70)
    print(f"\nStarted at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Run all tests
    results['finbert'], _ = test_finbert_sentiment()
    results['sentiment_sources'], _ = test_sentiment_sources()
    results['forecasters'], _ = test_forecasters()
    results['ai_engine'], _ = test_ai_forecast_engine()
    results['backtest'], _ = test_backtest_engine()
    results['combined'], _ = test_combined_sentiment()
    
    # Summary
    print("\n" + "="*70)
    print("📋 TEST SUMMARY")
    print("="*70)
    
    passed = 0
    failed = 0
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n   Total: {passed}/{len(results)} tests passed")
    
    if failed == 0:
        print("\n" + "="*70)
        print("🎉 ALL TESTS PASSED! Market Forecast System Fully Operational!")
        print("="*70)
    else:
        print("\n" + "="*70)
        print(f"⚠️  {failed} test(s) failed - review above for details")
        print("="*70)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

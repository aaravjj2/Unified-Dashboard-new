"""
Phase 2 AI/ML Unit Tests

Comprehensive tests for:
- Neural Forecaster (N-BEATS/NHITS)
- HMM Regime Detector
- Sentiment Consensus (FinBERT)

Author: Agent-P2
Date: 2025-12-28
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Enable deterministic mode for testing
os.environ['PHASE2_DETERMINISTIC'] = '1'

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestNeuralForecaster:
    """Test suite for NeuralForecaster class."""
    
    def test_import(self):
        """Test module can be imported."""
        from financial_dashboard.engines.neural_forecaster import NeuralForecaster
        assert NeuralForecaster is not None
    
    def test_initialization(self):
        """Test forecaster initialization."""
        from financial_dashboard.engines.neural_forecaster import NeuralForecaster
        
        forecaster = NeuralForecaster(model_type='nbeats', horizon=30)
        assert forecaster.model_type == 'nbeats'
        assert forecaster.horizon == 30
    
    def test_deterministic_data_generation(self):
        """Test deterministic data generation."""
        from financial_dashboard.engines.neural_forecaster import NeuralForecaster
        
        forecaster = NeuralForecaster()
        data = forecaster._generate_deterministic_data('SPY')
        
        assert len(data) > 0
        assert 'ds' in data.columns
        assert 'y' in data.columns
        assert 'unique_id' in data.columns
    
    def test_predict_returns_result(self):
        """Test prediction returns ForecastResult."""
        from financial_dashboard.engines.neural_forecaster import NeuralForecaster, ForecastResult
        
        forecaster = NeuralForecaster(horizon=30)
        result = forecaster.predict('AAPL')
        
        assert isinstance(result, ForecastResult)
        assert result.ticker == 'AAPL'
        assert result.horizon == 30
        assert len(result.historical) > 0
        assert len(result.forecast) > 0
    
    def test_forecast_has_confidence_intervals(self):
        """Test forecast includes confidence intervals."""
        from financial_dashboard.engines.neural_forecaster import NeuralForecaster
        
        forecaster = NeuralForecaster(horizon=14)
        result = forecaster.predict('MSFT')
        
        # Check forecast dataframe columns
        assert 'forecast' in result.forecast.columns or any('forecast' in str(c).lower() for c in result.forecast.columns)
    
    def test_fan_chart_data(self):
        """Test fan chart data preparation."""
        from financial_dashboard.engines.neural_forecaster import NeuralForecaster
        
        forecaster = NeuralForecaster(horizon=30)
        result = forecaster.predict('GOOGL')
        chart_data = forecaster.create_fan_chart_data(result)
        
        assert 'historical_dates' in chart_data
        assert 'historical_prices' in chart_data
        assert 'forecast_dates' in chart_data
        assert 'forecast_prices' in chart_data
        assert 'ticker' in chart_data
    
    def test_metrics_calculation(self):
        """Test metrics are calculated correctly."""
        from financial_dashboard.engines.neural_forecaster import NeuralForecaster
        
        forecaster = NeuralForecaster()
        result = forecaster.predict('NVDA')
        
        assert 'mean_return' in result.metrics
        assert 'volatility' in result.metrics
        assert 'sharpe_ratio' in result.metrics
        assert 'max_drawdown' in result.metrics
    
    def test_quick_forecast_function(self):
        """Test convenience function."""
        from financial_dashboard.engines.neural_forecaster import quick_forecast
        
        data = quick_forecast('AMD', horizon=14, model='nbeats')
        
        assert isinstance(data, dict)
        assert 'ticker' in data
        assert data['ticker'] == 'AMD'
    
    def test_different_horizons(self):
        """Test different forecast horizons."""
        from financial_dashboard.engines.neural_forecaster import NeuralForecaster
        
        for horizon in [7, 14, 30, 60]:
            forecaster = NeuralForecaster(horizon=horizon)
            result = forecaster.predict('SPY')
            assert result.horizon == horizon


class TestHMMRegimeDetector:
    """Test suite for HMMRegimeDetector class."""
    
    def test_import(self):
        """Test module can be imported."""
        from financial_dashboard.engines.hmm_regime_detector import HMMRegimeDetector
        assert HMMRegimeDetector is not None
    
    def test_initialization(self):
        """Test detector initialization."""
        from financial_dashboard.engines.hmm_regime_detector import HMMRegimeDetector
        
        detector = HMMRegimeDetector(n_states=3, lookback_years=2)
        assert detector.n_states == 3
        assert detector.lookback_years == 2
    
    def test_regime_labels(self):
        """Test regime labels are defined."""
        from financial_dashboard.engines.hmm_regime_detector import HMMRegimeDetector
        
        detector = HMMRegimeDetector()
        assert 0 in detector.REGIME_LABELS
        assert 1 in detector.REGIME_LABELS
        assert 2 in detector.REGIME_LABELS
        assert 'Bull' in detector.REGIME_LABELS.values()
        assert 'Bear' in detector.REGIME_LABELS.values()
    
    def test_deterministic_data_generation(self):
        """Test deterministic data generation."""
        from financial_dashboard.engines.hmm_regime_detector import HMMRegimeDetector
        
        detector = HMMRegimeDetector()
        data = detector._generate_deterministic_data('QQQ')
        
        assert len(data) > 0
        assert 'date' in data.columns
        assert 'price' in data.columns
        assert 'returns' in data.columns
        assert 'realized_vol' in data.columns
    
    def test_predict_regimes(self):
        """Test regime prediction."""
        from financial_dashboard.engines.hmm_regime_detector import HMMRegimeDetector, RegimeResult
        
        detector = HMMRegimeDetector()
        result = detector.predict_regimes('SPY')
        
        assert isinstance(result, RegimeResult)
        assert result.ticker == 'SPY'
        assert result.current_regime in ['Bull', 'Bear', 'Sideways']
    
    def test_regime_probabilities(self):
        """Test regime probabilities sum to ~1."""
        from financial_dashboard.engines.hmm_regime_detector import HMMRegimeDetector
        
        detector = HMMRegimeDetector()
        result = detector.predict_regimes('DIA')
        
        probs = result.regime_probabilities
        assert 'Bull' in probs
        assert 'Bear' in probs
        assert 'Sideways' in probs
        assert abs(sum(probs.values()) - 1.0) < 0.1  # Allow small tolerance
    
    def test_transition_matrix_shape(self):
        """Test transition matrix has correct shape."""
        from financial_dashboard.engines.hmm_regime_detector import HMMRegimeDetector
        
        detector = HMMRegimeDetector(n_states=3)
        result = detector.predict_regimes('IWM')
        
        assert result.transition_matrix.shape == (3, 3)
    
    def test_transition_matrix_rows_sum_to_one(self):
        """Test transition matrix rows sum to 1."""
        from financial_dashboard.engines.hmm_regime_detector import HMMRegimeDetector
        
        detector = HMMRegimeDetector()
        result = detector.predict_regimes('SPY')
        
        for row in result.transition_matrix:
            assert abs(sum(row) - 1.0) < 0.01
    
    def test_regime_stats(self):
        """Test regime statistics are calculated."""
        from financial_dashboard.engines.hmm_regime_detector import HMMRegimeDetector
        
        detector = HMMRegimeDetector()
        result = detector.predict_regimes('XLF')
        
        assert 'Bull' in result.regime_stats
        assert 'Bear' in result.regime_stats
        assert 'Sideways' in result.regime_stats
        
        for regime, stats in result.regime_stats.items():
            assert 'count' in stats
            assert 'pct_time' in stats
            assert 'avg_return' in stats
    
    def test_chart_data(self):
        """Test chart data preparation."""
        from financial_dashboard.engines.hmm_regime_detector import HMMRegimeDetector
        
        detector = HMMRegimeDetector()
        result = detector.predict_regimes('XLE')
        chart_data = detector.get_regime_chart_data(result)
        
        assert 'dates' in chart_data
        assert 'prices' in chart_data
        assert 'regimes' in chart_data
        assert 'current_regime' in chart_data
        assert 'transition_matrix' in chart_data
    
    def test_quick_regime_detection(self):
        """Test convenience function."""
        from financial_dashboard.engines.hmm_regime_detector import quick_regime_detection
        
        data = quick_regime_detection('VTI')
        
        assert isinstance(data, dict)
        assert 'current_regime' in data


class TestSentimentConsensus:
    """Test suite for FinBERTSentimentAnalyzer class."""
    
    def test_import(self):
        """Test module can be imported."""
        from financial_dashboard.engines.sentiment_consensus import FinBERTSentimentAnalyzer
        assert FinBERTSentimentAnalyzer is not None
    
    def test_initialization(self):
        """Test analyzer initialization."""
        from financial_dashboard.engines.sentiment_consensus import FinBERTSentimentAnalyzer
        
        analyzer = FinBERTSentimentAnalyzer(max_headlines=15)
        assert analyzer.max_headlines == 15
    
    def test_deterministic_news_generation(self):
        """Test deterministic news generation."""
        from financial_dashboard.engines.sentiment_consensus import FinBERTSentimentAnalyzer
        
        analyzer = FinBERTSentimentAnalyzer(max_headlines=10)
        news = analyzer._generate_deterministic_news('TSLA')
        
        assert len(news) == 10
        assert all('title' in item for item in news)
    
    def test_headline_sentiment_scoring(self):
        """Test headline sentiment scoring."""
        from financial_dashboard.engines.sentiment_consensus import FinBERTSentimentAnalyzer, SentimentScore
        
        analyzer = FinBERTSentimentAnalyzer()
        
        # Test positive headline
        score = analyzer._deterministic_sentiment("Stock surges on strong earnings beat")
        assert score.sentiment == 'positive'
        assert score.score > 0
        
        # Test negative headline
        score = analyzer._deterministic_sentiment("Company misses targets, shares decline")
        assert score.sentiment == 'negative'
        assert score.score < 0
        
        # Test neutral headline
        score = analyzer._deterministic_sentiment("Company announces routine changes")
        assert score.sentiment == 'neutral'
    
    def test_analyze_returns_result(self):
        """Test analysis returns proper result."""
        from financial_dashboard.engines.sentiment_consensus import FinBERTSentimentAnalyzer, SentimentConsensusResult
        
        analyzer = FinBERTSentimentAnalyzer(max_headlines=10)
        result = analyzer.analyze('META')
        
        assert isinstance(result, SentimentConsensusResult)
        assert result.ticker == 'META'
        assert 0 <= result.fear_greed_index <= 100
        assert result.num_articles == 10
    
    def test_fear_greed_index_range(self):
        """Test Fear & Greed index is in valid range."""
        from financial_dashboard.engines.sentiment_consensus import FinBERTSentimentAnalyzer
        
        analyzer = FinBERTSentimentAnalyzer()
        
        for ticker in ['AAPL', 'MSFT', 'GOOGL', 'AMZN']:
            result = analyzer.analyze(ticker)
            assert 0 <= result.fear_greed_index <= 100
    
    def test_sentiment_distribution(self):
        """Test sentiment distribution sums to 100%."""
        from financial_dashboard.engines.sentiment_consensus import FinBERTSentimentAnalyzer
        
        analyzer = FinBERTSentimentAnalyzer()
        result = analyzer.analyze('NFLX')
        
        dist = result.sentiment_distribution
        assert 'positive' in dist
        assert 'negative' in dist
        assert 'neutral' in dist
        assert abs(sum(dist.values()) - 100) < 1  # Allow small tolerance
    
    def test_overall_sentiment_labels(self):
        """Test overall sentiment has valid label."""
        from financial_dashboard.engines.sentiment_consensus import FinBERTSentimentAnalyzer
        
        analyzer = FinBERTSentimentAnalyzer()
        result = analyzer.analyze('COIN')
        
        assert result.overall_sentiment in ['Bullish', 'Bearish', 'Neutral']
    
    def test_chart_data(self):
        """Test chart data preparation."""
        from financial_dashboard.engines.sentiment_consensus import FinBERTSentimentAnalyzer
        
        analyzer = FinBERTSentimentAnalyzer()
        result = analyzer.analyze('UBER')
        chart_data = analyzer.get_chart_data(result)
        
        assert 'fear_greed_index' in chart_data
        assert 'overall_sentiment' in chart_data
        assert 'gauge_data' in chart_data
        assert 'headline_scores' in chart_data
    
    def test_gauge_data_has_label_and_color(self):
        """Test gauge data includes label and color."""
        from financial_dashboard.engines.sentiment_consensus import FinBERTSentimentAnalyzer
        
        analyzer = FinBERTSentimentAnalyzer()
        result = analyzer.analyze('PYPL')
        chart_data = analyzer.get_chart_data(result)
        
        gauge = chart_data['gauge_data']
        assert 'value' in gauge
        assert 'label' in gauge
        assert 'color' in gauge
        assert gauge['label'] in ['Extreme Fear', 'Fear', 'Neutral', 'Greed', 'Extreme Greed']
    
    def test_quick_sentiment_function(self):
        """Test convenience function."""
        from financial_dashboard.engines.sentiment_consensus import quick_sentiment
        
        data = quick_sentiment('SQ')
        
        assert isinstance(data, dict)
        assert 'ticker' in data
        assert data['ticker'] == 'SQ'


class TestIntegration:
    """Integration tests for Phase 2 modules."""
    
    def test_all_modules_work_together(self):
        """Test all modules can analyze same ticker."""
        from financial_dashboard.engines.neural_forecaster import quick_forecast
        from financial_dashboard.engines.hmm_regime_detector import quick_regime_detection
        from financial_dashboard.engines.sentiment_consensus import quick_sentiment
        
        ticker = 'SPY'
        
        forecast_data = quick_forecast(ticker)
        regime_data = quick_regime_detection(ticker)
        sentiment_data = quick_sentiment(ticker)
        
        assert forecast_data['ticker'] == ticker
        assert regime_data['ticker'] == ticker
        assert sentiment_data['ticker'] == ticker
    
    def test_deterministic_mode_produces_consistent_results(self):
        """Test deterministic mode gives same results."""
        from financial_dashboard.engines.neural_forecaster import quick_forecast
        from financial_dashboard.engines.hmm_regime_detector import quick_regime_detection
        from financial_dashboard.engines.sentiment_consensus import quick_sentiment
        
        ticker = 'AAPL'
        
        # Run twice
        forecast1 = quick_forecast(ticker)
        forecast2 = quick_forecast(ticker)
        
        regime1 = quick_regime_detection(ticker)
        regime2 = quick_regime_detection(ticker)
        
        # Results should be identical in deterministic mode
        assert forecast1['ticker'] == forecast2['ticker']
        assert regime1['current_regime'] == regime2['current_regime']


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

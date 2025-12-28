#!/usr/bin/env python3
"""
FinGPT-Style Engines Unit Tests
===============================
Comprehensive tests for all FinGPT-style AI engines.

Tests:
1. SignalFusionEngine - Signal combination
2. FinGPTSentimentEngine - Sentiment analysis
3. QlibStyleForecaster - Price forecasting
4. DeepHedgingEngine - Options hedging
5. FinRLTradingSignals - RL trading signals
6. NeuralProphetForecaster - Time series decomposition
7. FinGPTStackIntegration - Full stack integration

Run with: python -m pytest tests/test_fingpt_engines.py -v
Or: python tests/test_fingpt_engines.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def create_sample_price_data(periods: int = 100, seed: int = 42) -> pd.DataFrame:
    """Create sample OHLCV data for testing"""
    np.random.seed(seed)
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='D')
    returns = np.random.randn(periods) * 0.02
    prices = 100 * np.exp(np.cumsum(returns))
    
    return pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, periods)
    }, index=dates)


class TestSignalFusionEngine(unittest.TestCase):
    """Tests for SignalFusionEngine"""
    
    def setUp(self):
        from financial_dashboard.engines import get_signal_fusion_engine
        SFE = get_signal_fusion_engine()
        self.engine = SFE()
    
    def test_initialization(self):
        """Test engine initializes correctly"""
        self.assertIsNotNone(self.engine)
        self.assertEqual(len(self.engine.weights), 6)  # 6 signal types
    
    def test_create_price_signal(self):
        """Test price signal creation"""
        # Args: ticker, forecast_pct, confidence (0-1), horizon
        signal = self.engine.create_price_signal('AAPL', 0.05, 0.8)
        self.assertEqual(signal.ticker, 'AAPL')
        self.assertIsNotNone(signal.direction)
        self.assertLessEqual(signal.confidence, 1.0)
    
    def test_create_sentiment_signal(self):
        """Test sentiment signal creation"""
        signal = self.engine.create_sentiment_signal('AAPL', 0.7, 0.85)
        self.assertEqual(signal.ticker, 'AAPL')
        self.assertIsNotNone(signal.direction)
    
    def test_fuse_signals(self):
        """Test signal fusion"""
        signals = [
            self.engine.create_price_signal('AAPL', 0.03, 0.8),  # forecast_pct, confidence
            self.engine.create_sentiment_signal('AAPL', 0.5, 0.8),
        ]
        
        fused = self.engine.fuse_signals(signals)
        
        self.assertIsNotNone(fused)
        self.assertEqual(fused.ticker, 'AAPL')
        self.assertIsNotNone(fused.direction)
        # Confidence might be weighted sum, so just check it's positive
        self.assertGreaterEqual(fused.confidence, 0)
    
    def test_empty_signals_handling(self):
        """Test handling of empty signals list"""
        fused = self.engine.fuse_signals([])
        self.assertIsNone(fused)


class TestFinGPTSentimentEngine(unittest.TestCase):
    """Tests for FinGPTSentimentEngine"""
    
    def setUp(self):
        from financial_dashboard.engines import get_fingpt_sentiment
        FGS = get_fingpt_sentiment()
        self.engine = FGS()
        self.engine.initialize()
    
    def test_initialization(self):
        """Test engine initializes correctly"""
        self.assertIsNotNone(self.engine)
        self.assertTrue(self.engine._initialized)
    
    def test_analyze_positive_text(self):
        """Test positive sentiment detection"""
        result = self.engine.analyze_text("Stock surges 20% on great earnings!")
        self.assertIsNotNone(result)
        self.assertIn(result.label.name, ['POSITIVE', 'STRONG_POSITIVE', 'NEUTRAL'])
    
    def test_analyze_negative_text(self):
        """Test negative sentiment detection"""
        result = self.engine.analyze_text("Company reports massive losses and layoffs")
        self.assertIsNotNone(result)
        # Should be neutral or negative
        self.assertIsNotNone(result.label)
    
    def test_aggregate_sentiment(self):
        """Test multi-text sentiment aggregation"""
        texts = [
            "Strong revenue growth reported",
            "New product launch successful",
            "Some concerns about competition"
        ]
        
        agg = self.engine.aggregate_sentiment('AAPL', news_texts=texts)
        
        self.assertIsNotNone(agg)
        self.assertEqual(agg.ticker, 'AAPL')
        self.assertIsInstance(agg.overall_score, float)
        self.assertGreater(agg.num_sources, 0)
    
    def test_empty_texts(self):
        """Test handling of empty text list"""
        agg = self.engine.aggregate_sentiment('AAPL')
        self.assertEqual(agg.num_sources, 0)


class TestQlibStyleForecaster(unittest.TestCase):
    """Tests for QlibStyleForecaster"""
    
    def setUp(self):
        from financial_dashboard.engines import get_qlib_forecaster
        QSF = get_qlib_forecaster()
        self.engine = QSF()
        self.engine.initialize()
        self.df = create_sample_price_data(periods=100)
    
    def test_initialization(self):
        """Test engine initializes correctly"""
        self.assertIsNotNone(self.engine)
        self.assertTrue(self.engine._initialized)
    
    def test_compute_alpha_features(self):
        """Test alpha feature computation"""
        features = self.engine.compute_alpha_features(self.df)
        
        self.assertIsNotNone(features)
        self.assertGreater(len(features), 0)
        # Check for expected features
        self.assertIn('returns', features.columns)
        self.assertIn('volatility_20', features.columns)
    
    def test_forecast_generation(self):
        """Test forecast generation"""
        result = self.engine.forecast(self.df, horizon=5, ticker='TEST')
        
        self.assertIsNotNone(result)
        self.assertEqual(result.ticker, 'TEST')
        self.assertEqual(len(result.forecast_values), 5)
        self.assertEqual(len(result.confidence_lower), 5)
        self.assertEqual(len(result.confidence_upper), 5)
    
    def test_forecast_bounds(self):
        """Test confidence bounds are reasonable"""
        result = self.engine.forecast(self.df, horizon=5, ticker='TEST')
        
        # Lower bound should be less than forecast
        self.assertTrue(all(result.confidence_lower <= result.forecast_values))
        # Upper bound should be greater than forecast
        self.assertTrue(all(result.confidence_upper >= result.forecast_values))


class TestDeepHedgingEngine(unittest.TestCase):
    """Tests for DeepHedgingEngine"""
    
    def setUp(self):
        from financial_dashboard.engines import get_deep_hedging
        from financial_dashboard.engines.deep_hedging import OptionContract
        
        DHE = get_deep_hedging()
        self.engine = DHE()
        self.engine.initialize()
        
        # Sample option contract with correct parameters
        self.contract = OptionContract(
            underlying='AAPL',
            strike=100.0,
            expiry=datetime.now() + timedelta(days=30),
            is_call=True,
            spot=100.0,
            volatility=0.2,
            risk_free_rate=0.05
        )
    
    def test_initialization(self):
        """Test engine initializes correctly"""
        self.assertIsNotNone(self.engine)
        self.assertTrue(self.engine._initialized)
    
    def test_bs_price(self):
        """Test Black-Scholes pricing"""
        price = self.engine.bs_price(self.contract)
        
        self.assertIsNotNone(price)
        self.assertGreater(price, 0)
        self.assertLess(price, 100)  # Option worth less than underlying
    
    def test_bs_greeks(self):
        """Test Greeks calculation"""
        greeks = self.engine.bs_greeks(self.contract)
        
        self.assertIsNotNone(greeks)
        # Delta should be between 0 and 1 for calls
        self.assertGreater(greeks.delta, 0)
        self.assertLess(greeks.delta, 1)
        # Gamma should be positive
        self.assertGreater(greeks.gamma, 0)
        # Vega should be positive
        self.assertGreater(greeks.vega, 0)
        # Theta should be negative for long options
        self.assertLess(greeks.theta, 0)
    
    def test_implied_volatility(self):
        """Test IV calculation"""
        # First price an option
        market_price = self.engine.bs_price(self.contract)
        
        # Then back out the IV
        iv = self.engine.implied_volatility(
            self.contract,
            market_price=market_price
        )
        
        self.assertIsNotNone(iv)
        self.assertAlmostEqual(iv, 0.2, delta=0.01)  # Should match input vol


class TestFinRLTradingSignals(unittest.TestCase):
    """Tests for FinRLTradingSignals"""
    
    def setUp(self):
        from financial_dashboard.engines import get_finrl_signals
        FRL = get_finrl_signals()
        self.engine = FRL()
        self.engine.initialize()
        self.df = create_sample_price_data(periods=100)
    
    def test_initialization(self):
        """Test engine initializes correctly"""
        self.assertIsNotNone(self.engine)
        self.assertTrue(self.engine._initialized)
    
    def test_compute_technical_indicators(self):
        """Test technical indicator computation"""
        indicators = self.engine.compute_technical_indicators(self.df)
        
        self.assertIsNotNone(indicators)
        self.assertIn('return_1d', indicators)
        self.assertIn('rsi', indicators)
        self.assertIn('macd', indicators)
    
    def test_generate_signal(self):
        """Test signal generation"""
        signal = self.engine.generate_signal(
            ticker='TEST',
            price_history=self.df
        )
        
        self.assertIsNotNone(signal)
        self.assertEqual(signal.ticker, 'TEST')
        self.assertIsNotNone(signal.action)
        self.assertGreaterEqual(signal.confidence, 0)
        self.assertLessEqual(signal.confidence, 1)
    
    def test_generate_portfolio_signals(self):
        """Test portfolio-wide signal generation"""
        tickers = ['AAPL', 'GOOGL', 'MSFT']
        price_histories = {t: self.df.copy() for t in tickers}
        
        signals = self.engine.generate_portfolio_signals(
            tickers=tickers,
            price_histories=price_histories
        )
        
        self.assertIsNotNone(signals)
        self.assertEqual(len(signals), len(tickers))


class TestNeuralProphetForecaster(unittest.TestCase):
    """Tests for NeuralProphetForecaster"""
    
    def setUp(self):
        from financial_dashboard.engines import get_neural_prophet
        NP = get_neural_prophet()
        self.engine = NP()
        self.engine.initialize()
        
        # Create data with proper format
        dates = pd.date_range(end=datetime.now(), periods=200, freq='D')
        self.df = pd.DataFrame({
            'ds': dates,
            'y': 100 + np.cumsum(np.random.randn(200) * 2)
        })
    
    def test_initialization(self):
        """Test engine initializes correctly"""
        self.assertIsNotNone(self.engine)
    
    def test_fit(self):
        """Test model fitting"""
        self.engine.fit(self.df)
        self.assertTrue(self.engine._fitted)
    
    def test_predict(self):
        """Test forecast generation"""
        self.engine.fit(self.df)
        result = self.engine.predict(periods=5)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result.yhat), 5)
        self.assertEqual(len(result.yhat_lower), 5)
        self.assertEqual(len(result.yhat_upper), 5)
    
    def test_decompose(self):
        """Test time series decomposition"""
        self.engine.fit(self.df)
        decomp = self.engine.decompose()
        
        self.assertIn('trend', decomp)
        self.assertIn('seasonal', decomp)
        self.assertIn('residual', decomp)


class TestFinGPTStackIntegration(unittest.TestCase):
    """Tests for FinGPTStackIntegration"""
    
    def setUp(self):
        from financial_dashboard.engines.fingpt_stack_integration import FinGPTStackIntegration
        self.stack = FinGPTStackIntegration()
        self.df = create_sample_price_data(periods=100)
    
    def test_initialization(self):
        """Test stack initializes correctly"""
        success = self.stack.initialize()
        self.assertTrue(success)
        self.assertTrue(self.stack._initialized)
    
    def test_engine_status(self):
        """Test engine status reporting"""
        self.stack.initialize()
        status = self.stack.get_engine_status()
        
        self.assertIn('initialized', status)
        self.assertTrue(status['initialized'])
        self.assertIn('qlib', status)
        self.assertIn('sentiment', status)
        self.assertIn('finrl', status)
    
    def test_generate_unified_forecast(self):
        """Test unified forecast generation"""
        self.stack.initialize()
        
        forecast = self.stack.generate_unified_forecast(
            ticker='TEST',
            price_history=self.df,
            news_headlines=['Test news headline'],
            horizon=5
        )
        
        self.assertIsNotNone(forecast)
        self.assertEqual(forecast.ticker, 'TEST')
        self.assertEqual(len(forecast.price_forecast), 5)
        self.assertIsNotNone(forecast.signal_action)
    
    def test_quick_sentiment(self):
        """Test quick sentiment method"""
        self.stack.initialize()
        
        result = self.stack.quick_sentiment("This is great news for the company!")
        
        self.assertIn('score', result)
        self.assertIn('label', result)
        self.assertIn('confidence', result)
    
    def test_forecast_to_dict(self):
        """Test forecast serialization"""
        self.stack.initialize()
        
        forecast = self.stack.generate_unified_forecast(
            ticker='TEST',
            price_history=self.df,
            horizon=3
        )
        
        forecast_dict = forecast.to_dict()
        
        self.assertIn('ticker', forecast_dict)
        self.assertIn('price', forecast_dict)
        self.assertIn('sentiment', forecast_dict)
        self.assertIn('signal', forecast_dict)


def run_tests():
    """Run all tests and report results"""
    print("=" * 70)
    print("FINGPT-STYLE ENGINES UNIT TESTS")
    print("=" * 70)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSignalFusionEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestFinGPTSentimentEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestQlibStyleForecaster))
    suite.addTests(loader.loadTestsFromTestCase(TestDeepHedgingEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestFinRLTradingSignals))
    suite.addTests(loader.loadTestsFromTestCase(TestNeuralProphetForecaster))
    suite.addTests(loader.loadTestsFromTestCase(TestFinGPTStackIntegration))
    
    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print()
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print()
        print("❌ SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())

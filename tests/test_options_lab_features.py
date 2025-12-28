"""
Comprehensive Test Suite for Options Lab Features
=================================================
Tests all new implementations:
- Options Analytics
- Sentiment Service
- Strategy Executor
- Alpaca Data Loader
"""

import os
import sys
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestOptionsAnalytics(unittest.TestCase):
    """Test options analytics module."""
    
    def test_iv_rank_at_high(self):
        """Test IV Rank when IV is at 52-week high."""
        from financial_dashboard.tabs.options_lab.options_analytics import calculate_iv_rank
        iv_history = [20, 22, 25, 18, 30, 28, 24]
        current_iv = 30  # At high
        rank = calculate_iv_rank(current_iv, iv_history)
        self.assertEqual(rank, 100.0)
    
    def test_iv_rank_at_low(self):
        """Test IV Rank when IV is at 52-week low."""
        from financial_dashboard.tabs.options_lab.options_analytics import calculate_iv_rank
        iv_history = [20, 22, 25, 18, 30, 28, 24]
        current_iv = 18  # At low
        rank = calculate_iv_rank(current_iv, iv_history)
        self.assertEqual(rank, 0.0)
    
    def test_iv_rank_midpoint(self):
        """Test IV Rank at midpoint."""
        from financial_dashboard.tabs.options_lab.options_analytics import calculate_iv_rank
        iv_history = [20, 30]
        current_iv = 25  # Midpoint
        rank = calculate_iv_rank(current_iv, iv_history)
        self.assertEqual(rank, 50.0)
    
    def test_iv_percentile(self):
        """Test IV Percentile calculation."""
        from financial_dashboard.tabs.options_lab.options_analytics import calculate_iv_percentile
        iv_history = [10, 20, 30, 40, 50]
        current_iv = 35
        percentile = calculate_iv_percentile(current_iv, iv_history)
        # 35 is greater than 10, 20, 30 (3 values) = 60%
        self.assertEqual(percentile, 60.0)
    
    def test_max_pain_calculation(self):
        """Test max pain calculator."""
        from financial_dashboard.tabs.options_lab.options_analytics import calculate_max_pain
        calls_df = pd.DataFrame({
            'strike': [100, 105, 110, 115, 120],
            'openInterest': [500, 1000, 1500, 800, 300]
        })
        puts_df = pd.DataFrame({
            'strike': [100, 105, 110, 115, 120],
            'openInterest': [300, 800, 1200, 1000, 500]
        })
        
        result = calculate_max_pain(calls_df, puts_df)
        
        self.assertIn('max_pain_strike', result)
        self.assertIn('total_pain', result)
        self.assertIsInstance(result['max_pain_strike'], (int, float))
    
    def test_expected_move(self):
        """Test expected move calculation."""
        from financial_dashboard.tabs.options_lab.options_analytics import calculate_expected_move
        result = calculate_expected_move(
            spot=150.0,
            atm_call_price=4.50,
            atm_put_price=4.30,
            days_to_expiry=30
        )
        
        self.assertIn('expected_move_dollars', result)
        self.assertIn('expected_move_percent', result)
        self.assertIn('upper_bound', result)
        self.assertIn('lower_bound', result)
        self.assertEqual(result['probability_range'], '68%')
        
        # Verify bounds make sense
        self.assertGreater(result['upper_bound'], 150.0)
        self.assertLess(result['lower_bound'], 150.0)
    
    def test_put_call_ratio(self):
        """Test put/call ratio calculation."""
        from financial_dashboard.tabs.options_lab.options_analytics import calculate_put_call_ratio
        calls_df = pd.DataFrame({
            'strike': [100, 105, 110],
            'volume': [1000, 2000, 1500],
            'openInterest': [5000, 8000, 6000]
        })
        puts_df = pd.DataFrame({
            'strike': [100, 105, 110],
            'volume': [800, 1500, 1200],
            'openInterest': [4000, 6000, 5000]
        })
        
        result = calculate_put_call_ratio(calls_df, puts_df)
        
        self.assertIn('volume_ratio', result)
        self.assertIn('oi_ratio', result)
        self.assertIn('interpretation', result)
        
        # Total put volume = 3500, call volume = 4500, ratio = 0.78
        self.assertAlmostEqual(result['volume_ratio'], 0.78, places=2)
    
    def test_historical_volatility(self):
        """Test HV calculation."""
        from financial_dashboard.tabs.options_lab.options_analytics import calculate_historical_volatility
        # Generate random walk prices
        np.random.seed(42)
        prices = [100]
        for _ in range(30):
            prices.append(prices[-1] * (1 + np.random.normal(0, 0.02)))
        
        hv = calculate_historical_volatility(prices, window=20)
        
        self.assertIsInstance(hv, float)
        self.assertGreater(hv, 0)
        self.assertLess(hv, 200)  # Reasonable range for annualized vol
    
    def test_iv_vs_hv_analysis(self):
        """Test IV vs HV analysis."""
        from financial_dashboard.tabs.options_lab.options_analytics import get_iv_vs_hv_analysis
        result = get_iv_vs_hv_analysis(
            current_iv=35.0,
            hv_20=25.0,
            hv_30=26.0
        )
        
        self.assertIn('iv_premium', result)
        self.assertIn('recommendation', result)
        self.assertIn('signal', result)
        
        # IV is 35, HV avg is 25.5, premium is ~37% - should be SELL
        self.assertEqual(result['signal'], 'SELL')
    
    def test_kelly_criterion(self):
        """Test Kelly criterion calculation."""
        from financial_dashboard.tabs.options_lab.options_analytics import calculate_kelly_criterion
        kelly = calculate_kelly_criterion(
            win_rate=0.6,
            avg_win=100,
            avg_loss=80
        )
        
        self.assertIsInstance(kelly, float)
        self.assertGreaterEqual(kelly, 0)
        self.assertLessEqual(kelly, 0.25)  # Capped at 25%


class TestSentimentService(unittest.TestCase):
    """Test unified sentiment service."""
    
    def test_positive_sentiment(self):
        """Test positive sentiment detection."""
        from financial_dashboard.services.unified_sentiment_service import analyze_text_sentiment
        text = "Stock surges to record high on strong earnings beat"
        result = analyze_text_sentiment(text)
        
        self.assertEqual(result['sentiment'], 'positive')
        self.assertGreater(result['score'], 0)
    
    def test_negative_sentiment(self):
        """Test negative sentiment detection."""
        from financial_dashboard.services.unified_sentiment_service import analyze_text_sentiment
        text = "Market crashes as recession fears and bearish outlook dominate"
        result = analyze_text_sentiment(text)
        
        self.assertEqual(result['sentiment'], 'negative')
        self.assertLess(result['score'], 0)
    
    def test_neutral_sentiment(self):
        """Test neutral sentiment detection."""
        from financial_dashboard.services.unified_sentiment_service import analyze_text_sentiment
        text = "Company announces regular quarterly meeting"
        result = analyze_text_sentiment(text)
        
        self.assertEqual(result['sentiment'], 'neutral')
    
    def test_aggregated_sentiment(self):
        """Test aggregated headlines sentiment."""
        from financial_dashboard.services.unified_sentiment_service import analyze_headlines_sentiment
        headlines = [
            "Stock gains 5% on upgrade",
            "Analyst downgrades to sell",
            "Company reports flat earnings",
            "CEO announces new product launch",
            "Revenue misses estimates"
        ]
        
        result = analyze_headlines_sentiment(headlines)
        
        self.assertIn('overall_sentiment', result)
        self.assertIn('overall_score', result)
        self.assertIn('positive_count', result)
        self.assertIn('negative_count', result)
        self.assertIn('neutral_count', result)
        self.assertEqual(result['analyzed_count'], 5)
    
    def test_empty_headlines(self):
        """Test with empty headlines list."""
        from financial_dashboard.services.unified_sentiment_service import analyze_headlines_sentiment
        result = analyze_headlines_sentiment([])
        
        self.assertEqual(result['overall_sentiment'], 'neutral')
        self.assertEqual(result['analyzed_count'], 0)


class TestStrategyBuilder(unittest.TestCase):
    """Test strategy builder."""
    
    def setUp(self):
        from financial_dashboard.tabs.options_lab.strategy_executor import (
            StrategyBuilder,
            OrderSide,
            OptionType
        )
        self.builder = StrategyBuilder()
        self.OrderSide = OrderSide
        self.OptionType = OptionType
    
    def test_occ_symbol_call(self):
        """Test OCC symbol generation for calls."""
        symbol = self.builder.build_occ_symbol(
            underlying='SPY',
            expiration='2025-01-19',
            option_type='call',
            strike=450
        )
        # Format: SPY250119C00450000
        self.assertEqual(symbol, 'SPY250119C00450000')
    
    def test_occ_symbol_put(self):
        """Test OCC symbol generation for puts."""
        symbol = self.builder.build_occ_symbol(
            underlying='AAPL',
            expiration='2025-02-21',
            option_type='put',
            strike=175.5
        )
        # Format: AAPL250221P00175500
        self.assertEqual(symbol, 'AAPL250221P00175500')
    
    def test_covered_call_strategy(self):
        """Test covered call strategy building."""
        strategy = self.builder.covered_call(
            underlying='SPY',
            spot=450.0,
            call_strike=460.0,
            expiration='2025-01-19',
            call_premium=3.00
        )
        
        self.assertEqual(strategy.strategy_name, 'Covered Call')
        self.assertEqual(len(strategy.legs), 1)
        self.assertEqual(strategy.legs[0].side, self.OrderSide.SELL)
        self.assertEqual(strategy.legs[0].option_type, self.OptionType.CALL)
        self.assertGreater(strategy.max_profit, 0)
    
    def test_cash_secured_put_strategy(self):
        """Test cash-secured put strategy building."""
        strategy = self.builder.cash_secured_put(
            underlying='AAPL',
            spot=175.0,
            put_strike=170.0,
            expiration='2025-01-19',
            put_premium=2.50
        )
        
        self.assertEqual(strategy.strategy_name, 'Cash-Secured Put')
        self.assertEqual(len(strategy.legs), 1)
        self.assertEqual(strategy.legs[0].side, self.OrderSide.SELL)
        self.assertEqual(strategy.legs[0].option_type, self.OptionType.PUT)
    
    def test_bull_call_spread(self):
        """Test bull call spread strategy."""
        strategy = self.builder.bull_call_spread(
            underlying='MSFT',
            spot=400.0,
            long_strike=395.0,
            short_strike=410.0,
            expiration='2025-01-19',
            net_debit=5.00
        )
        
        self.assertEqual(strategy.strategy_name, 'Bull Call Spread')
        self.assertEqual(len(strategy.legs), 2)
        
        # Verify we have one buy and one sell
        sides = [leg.side for leg in strategy.legs]
        self.assertIn(self.OrderSide.BUY, sides)
        self.assertIn(self.OrderSide.SELL, sides)
    
    def test_iron_condor(self):
        """Test iron condor strategy."""
        strategy = self.builder.iron_condor(
            underlying='SPY',
            spot=450.0,
            put_short=440.0,
            put_long=435.0,
            call_short=460.0,
            call_long=465.0,
            expiration='2025-01-19',
            net_credit=2.00
        )
        
        self.assertEqual(strategy.strategy_name, 'Iron Condor')
        self.assertEqual(len(strategy.legs), 4)
        
        # Verify 2 buys and 2 sells
        buy_count = sum(1 for leg in strategy.legs if leg.side == self.OrderSide.BUY)
        sell_count = sum(1 for leg in strategy.legs if leg.side == self.OrderSide.SELL)
        self.assertEqual(buy_count, 2)
        self.assertEqual(sell_count, 2)
    
    def test_straddle_long(self):
        """Test long straddle strategy."""
        strategy = self.builder.straddle(
            underlying='TSLA',
            spot=250.0,
            strike=250.0,
            expiration='2025-01-19',
            is_long=True,
            total_premium=20.0
        )
        
        self.assertEqual(strategy.strategy_name, 'Long Straddle')
        self.assertEqual(len(strategy.legs), 2)
        
        # Both legs should be BUY
        for leg in strategy.legs:
            self.assertEqual(leg.side, self.OrderSide.BUY)
    
    def test_straddle_short(self):
        """Test short straddle strategy."""
        strategy = self.builder.straddle(
            underlying='TSLA',
            spot=250.0,
            strike=250.0,
            expiration='2025-01-19',
            is_long=False,
            total_premium=20.0
        )
        
        self.assertEqual(strategy.strategy_name, 'Short Straddle')
        
        # Both legs should be SELL
        for leg in strategy.legs:
            self.assertEqual(leg.side, self.OrderSide.SELL)


class TestAlpacaDataLoader(unittest.TestCase):
    """Test Alpaca data loader."""
    
    def test_client_configuration_check(self):
        """Test client knows if configured."""
        from financial_dashboard.tabs.options_lab.alpaca_data_loader import AlpacaOptionsClient
        client = AlpacaOptionsClient()
        is_configured = client.is_configured()
        self.assertIsInstance(is_configured, bool)
    
    def test_mock_chain_generation(self):
        """Test mock chain generation."""
        from financial_dashboard.tabs.options_lab.alpaca_data_loader import _generate_mock_chain
        chain = _generate_mock_chain('TEST')
        
        self.assertEqual(chain['ticker'], 'TEST')
        self.assertIn('spot_price', chain)
        self.assertIn('expirations', chain)
        self.assertIn('calls', chain)
        self.assertIn('puts', chain)
        
        # Verify DataFrames
        self.assertIsInstance(chain['calls'], pd.DataFrame)
        self.assertIsInstance(chain['puts'], pd.DataFrame)
        self.assertFalse(chain['calls'].empty)
        self.assertFalse(chain['puts'].empty)
    
    def test_mock_chain_has_required_columns(self):
        """Test mock chain has all required columns."""
        from financial_dashboard.tabs.options_lab.alpaca_data_loader import _generate_mock_chain
        chain = _generate_mock_chain('SPY')
        calls = chain['calls']
        
        required_columns = ['strike', 'expiration', 'lastPrice', 'bid', 'ask', 
                          'volume', 'openInterest', 'impliedVolatility', 
                          'delta', 'gamma', 'theta', 'vega']
        
        for col in required_columns:
            self.assertIn(col, calls.columns, f"Missing column: {col}")
    
    def test_chain_enrichment(self):
        """Test chain data enrichment."""
        from financial_dashboard.tabs.options_lab.alpaca_data_loader import _enrich_chain_data
        df = pd.DataFrame({
            'strike': [145, 150, 155],
            'lastPrice': [7.0, 4.0, 2.0],
            'impliedVolatility': [0.25, 0.25, 0.25]
        })
        
        enriched = _enrich_chain_data(df, spot_price=150.0, option_type='call')
        
        self.assertIn('moneyness', enriched.columns)
        self.assertIn('intrinsic', enriched.columns)
        self.assertIn('status', enriched.columns)
    
    def test_greeks_calculation(self):
        """Test Greeks calculation."""
        from financial_dashboard.tabs.options_lab.alpaca_data_loader import _calculate_greeks
        df = pd.DataFrame({
            'strike': [145, 150, 155],
            'impliedVolatility': [0.25, 0.25, 0.25],
            'expiration': ['2025-02-21', '2025-02-21', '2025-02-21']
        })
        
        with_greeks = _calculate_greeks(df, spot=150.0, option_type='call')
        
        self.assertIn('delta', with_greeks.columns)
        self.assertIn('gamma', with_greeks.columns)
        self.assertIn('theta', with_greeks.columns)
        self.assertIn('vega', with_greeks.columns)
        
        # ITM call should have delta > 0.5
        itm_delta = with_greeks[with_greeks['strike'] == 145]['delta'].values[0]
        self.assertGreater(itm_delta, 0.5)
        
        # OTM call should have delta < 0.5
        otm_delta = with_greeks[with_greeks['strike'] == 155]['delta'].values[0]
        self.assertLess(otm_delta, 0.5)


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple modules."""
    
    def test_analytics_with_mock_chain(self):
        """Test analytics functions work with mock chain data."""
        from financial_dashboard.tabs.options_lab.alpaca_data_loader import _generate_mock_chain
        from financial_dashboard.tabs.options_lab.options_analytics import (
            calculate_max_pain,
            calculate_put_call_ratio
        )
        
        chain = _generate_mock_chain('SPY')
        
        max_pain = calculate_max_pain(chain['calls'], chain['puts'])
        self.assertIn('max_pain_strike', max_pain)
        
        pcr = calculate_put_call_ratio(chain['calls'], chain['puts'])
        self.assertIn('volume_ratio', pcr)
    
    def test_sentiment_with_strategy_recommendation(self):
        """Test sentiment service with strategy recommendations."""
        from financial_dashboard.services.unified_sentiment_service import analyze_text_sentiment
        from financial_dashboard.tabs.options_lab.strategy_executor import StrategyBuilder
        
        # Simulate sentiment analysis
        sentiment = analyze_text_sentiment("Stock surges on strong earnings, bullish outlook")
        
        # Based on positive sentiment, build bullish strategy
        builder = StrategyBuilder()
        if sentiment['sentiment'] == 'positive':
            strategy = builder.bull_call_spread(
                underlying='SPY',
                spot=450.0,
                long_strike=445.0,
                short_strike=460.0,
                expiration='2025-01-19'
            )
            self.assertEqual(strategy.strategy_name, 'Bull Call Spread')


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestOptionsAnalytics))
    suite.addTests(loader.loadTestsFromTestCase(TestSentimentService))
    suite.addTests(loader.loadTestsFromTestCase(TestStrategyBuilder))
    suite.addTests(loader.loadTestsFromTestCase(TestAlpacaDataLoader))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

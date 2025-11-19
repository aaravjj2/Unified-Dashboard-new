"""
Sprint 3: Options Trading System Core Engine & Backtesting Tests
Tests for strategy engine, covered call screener, and backtester.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from strategies.base_strategy import BaseStrategy
from strategies.covered_call_screener import CoveredCallScreener
from backtester import Backtester, BacktestResult


class TestBaseStrategy:
    """Tests for base strategy interface."""
    
    def test_base_strategy_imports(self):
        """Test that BaseStrategy can be imported."""
        from strategies.base_strategy import BaseStrategy
        assert BaseStrategy is not None
    
    def test_strategy_validation(self):
        """Test signal validation."""
        # Create a minimal concrete strategy for testing
        class TestStrategy(BaseStrategy):
            def generate_signals(self, data):
                return []
        
        strategy = TestStrategy("Test", {})
        
        # Valid signal
        valid_signal = {
            'action': 'buy',
            'symbol': 'SPY251024C00450000',
            'quantity': 1,
            'reason': 'Test signal'
        }
        assert strategy.validate_signal(valid_signal) is True
        
        # Invalid - missing field
        invalid_signal = {
            'action': 'buy',
            'symbol': 'SPY251024C00450000'
        }
        assert strategy.validate_signal(invalid_signal) is False
        
        # Invalid - bad action
        invalid_action = {
            'action': 'hold',
            'symbol': 'SPY251024C00450000',
            'quantity': 1,
            'reason': 'Test'
        }
        assert strategy.validate_signal(invalid_action) is False


class TestCoveredCallScreener:
    """Tests for covered call screener strategy."""
    
    def test_covered_call_screener_imports(self):
        """Test that CoveredCallScreener can be imported."""
        from strategies.covered_call_screener import CoveredCallScreener
        assert CoveredCallScreener is not None
    
    def test_strategy_initialization(self):
        """Test strategy initializes with config."""
        config = {
            'min_stock_price': 20.0,
            'max_stock_price': 300.0,
            'target_delta': 0.30,
            'min_premium': 1.0
        }
        strategy = CoveredCallScreener(config=config)
        
        assert strategy.name == "Covered Call Screener"
        assert strategy.min_stock_price == 20.0
        assert strategy.target_delta == 0.30
    
    def test_generate_signals_valid_data(self):
        """Test signal generation with valid market data."""
        strategy = CoveredCallScreener(config={
            'min_stock_price': 20.0,
            'max_stock_price': 500.0,
            'target_delta': 0.30,
            'min_premium': 0.50,
            'min_volume': 10000
        })
        
        # Create mock market data
        market_data = {
            'symbol': 'AAPL',
            'current_price': 175.0,
            'volume': 50000000,
            'options_chain': {
                'calls': [
                    {
                        'strike': 180.0,
                        'expiration': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                        'delta': 0.30,
                        'bid': 2.50,
                        'ask': 2.60,
                        'last': 2.55,
                        'volume': 500,
                        'open_interest': 1000,
                        'symbol': 'AAPL251115C00180000'
                    },
                    {
                        'strike': 185.0,
                        'expiration': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                        'delta': 0.25,
                        'bid': 1.80,
                        'ask': 1.90,
                        'last': 1.85,
                        'volume': 300,
                        'open_interest': 800,
                        'symbol': 'AAPL251115C00185000'
                    }
                ]
            }
        }
        
        signals = strategy.generate_signals(market_data)
        
        assert len(signals) > 0, "Strategy should generate at least one signal"
        
        # Validate first signal
        signal = signals[0]
        assert signal['action'] == 'sell', "Covered call should be a sell action"
        assert 'symbol' in signal
        assert signal['quantity'] > 0
        assert 'reason' in signal
        assert 'metadata' in signal
        
        # Check metadata
        metadata = signal['metadata']
        assert 'strike' in metadata
        assert 'premium' in metadata
        assert 'days_to_expiration' in metadata
    
    def test_generate_signals_filters_low_price_stocks(self):
        """Test that strategy filters out stocks below min price."""
        strategy = CoveredCallScreener(config={
            'min_stock_price': 50.0,
            'max_stock_price': 500.0
        })
        
        # Stock below minimum
        market_data = {
            'symbol': 'PENNY',
            'current_price': 5.0,
            'volume': 100000,
            'options_chain': {'calls': []}
        }
        
        signals = strategy.generate_signals(market_data)
        assert len(signals) == 0, "Should not generate signals for low-price stocks"
    
    def test_generate_signals_filters_low_volume(self):
        """Test that strategy filters out low volume stocks."""
        strategy = CoveredCallScreener(config={
            'min_volume': 100000
        })
        
        # Low volume stock
        market_data = {
            'symbol': 'LOWVOL',
            'current_price': 100.0,
            'volume': 10000,  # Below threshold
            'options_chain': {'calls': []}
        }
        
        signals = strategy.generate_signals(market_data)
        assert len(signals) == 0, "Should not generate signals for low volume stocks"
    
    def test_get_status(self):
        """Test strategy status reporting."""
        config = {
            'target_delta': 0.35,
            'min_premium': 2.0
        }
        strategy = CoveredCallScreener(config=config)
        
        status = strategy.get_status()
        
        assert status['name'] == "Covered Call Screener"
        assert status['enabled'] is True
        assert 'parameters' in status
        assert status['parameters']['target_delta'] == 0.35


class TestBacktester:
    """Tests for backtesting engine."""
    
    def test_backtester_imports(self):
        """Test that Backtester can be imported."""
        from backtester import Backtester, BacktestResult
        assert Backtester is not None
        assert BacktestResult is not None
    
    def test_backtester_initialization(self):
        """Test backtester initializes correctly."""
        backtester = Backtester(
            initial_capital=10000.0,
            commission_per_contract=0.65,
            slippage_pct=0.01
        )
        
        assert backtester.initial_capital == 10000.0
        assert backtester.commission_per_contract == 0.65
        assert backtester.capital == 10000.0
    
    def test_backtest_result_to_dict(self):
        """Test BacktestResult serialization."""
        result = BacktestResult()
        result.total_pnl = 500.0
        result.num_trades = 10
        result.win_rate = 60.0
        
        result_dict = result.to_dict()
        
        assert result_dict['total_pnl'] == 500.0
        assert result_dict['num_trades'] == 10
        assert result_dict['win_rate'] == 60.0
    
    def test_synthetic_options_generation(self):
        """Test synthetic options chain generation."""
        backtester = Backtester(initial_capital=10000.0)
        
        options_chain = backtester._generate_synthetic_options(
            symbol='SPY',
            stock_price=450.0,
            date=datetime(2024, 10, 15)
        )
        
        assert 'calls' in options_chain
        assert 'puts' in options_chain
        assert len(options_chain['calls']) > 0
        assert len(options_chain['puts']) > 0
        
        # Check call structure
        call = options_chain['calls'][0]
        assert 'strike' in call
        assert 'expiration' in call
        assert 'bid' in call
        assert 'ask' in call
        assert 'delta' in call
    
    def test_simple_backtest_execution(self):
        """Test running a simple backtest with mock data."""
        # Create a simple test strategy that always buys
        class AlwaysBuyStrategy(BaseStrategy):
            def generate_signals(self, data):
                # Only buy once per symbol
                if not hasattr(self, '_bought'):
                    self._bought = True
                    
                    # Find a call option from the chain
                    calls = data.get('options_chain', {}).get('calls', [])
                    if calls:
                        option = calls[0]
                        return [{
                            'action': 'buy',
                            'symbol': option['symbol'],
                            'quantity': 1,
                            'reason': 'Test buy signal'
                        }]
                return []
        
        strategy = AlwaysBuyStrategy("Test Strategy", {})
        
        # Create simple market data (5 trading days)
        dates = pd.date_range(start='2024-10-01', periods=5, freq='D')
        market_data = pd.DataFrame({
            'date': dates,
            'symbol': 'SPY',
            'close': [450.0, 451.0, 452.0, 453.0, 454.0],
            'volume': [1000000] * 5
        })
        
        # Run backtest
        backtester = Backtester(initial_capital=10000.0)
        result = backtester.run(strategy, market_data)
        
        # Assertions
        assert result is not None
        assert isinstance(result, BacktestResult)
        assert result.initial_capital == 10000.0
        assert result.num_days == 5
        
        # Should have executed at least one trade
        # (May be 0 if position wasn't closed, or >0 if closed at expiration)
        assert len(backtester.daily_snapshots) == 5
    
    def test_backtest_with_covered_call_strategy(self):
        """Test backtesting with actual CoveredCallScreener strategy."""
        strategy = CoveredCallScreener(config={
            'min_stock_price': 100.0,
            'max_stock_price': 500.0,
            'target_delta': 0.30,
            'min_premium': 0.50,
            'min_volume': 10000
        })
        
        # Create market data
        dates = pd.date_range(start='2024-10-01', periods=10, freq='D')
        market_data = pd.DataFrame({
            'date': dates,
            'symbol': 'AAPL',
            'close': np.linspace(175.0, 180.0, 10),  # Upward trend
            'volume': [50000000] * 10
        })
        
        # Run backtest
        backtester = Backtester(initial_capital=10000.0)
        result = backtester.run(strategy, market_data)
        
        # Assertions
        assert result is not None
        assert result.initial_capital == 10000.0
        assert result.final_capital > 0  # Should have capital remaining
        assert result.num_days == 10
        
        # Result should be serializable
        result_dict = result.to_dict()
        assert 'total_pnl' in result_dict
        assert 'win_rate' in result_dict
    
    def test_backtest_calculates_metrics(self):
        """Test that backtest calculates all expected metrics."""
        # Create strategy that generates predictable trades
        class SimpleStrategy(BaseStrategy):
            def __init__(self):
                super().__init__("Simple", {})
                self.trade_count = 0
            
            def generate_signals(self, data):
                # Generate 3 trades total
                if self.trade_count < 3:
                    self.trade_count += 1
                    calls = data.get('options_chain', {}).get('calls', [])
                    if calls:
                        return [{
                            'action': 'buy',
                            'symbol': calls[0]['symbol'],
                            'quantity': 1,
                            'reason': 'Test'
                        }]
                return []
        
        strategy = SimpleStrategy()
        
        # Create market data (30 days for positions to expire)
        dates = pd.date_range(start='2024-10-01', periods=40, freq='D')
        market_data = pd.DataFrame({
            'date': dates,
            'symbol': 'SPY',
            'close': np.random.uniform(450, 460, 40),
            'volume': [1000000] * 40
        })
        
        backtester = Backtester(initial_capital=10000.0)
        result = backtester.run(strategy, market_data)
        
        # Check that all metrics are calculated
        assert hasattr(result, 'total_pnl')
        assert hasattr(result, 'total_return_pct')
        assert hasattr(result, 'win_rate')
        assert hasattr(result, 'num_trades')
        assert hasattr(result, 'max_drawdown')
        
        # Result dict should contain all fields
        result_dict = result.to_dict()
        assert 'total_pnl' in result_dict
        assert 'win_rate' in result_dict
        assert 'sharpe_ratio' in result_dict
        assert 'max_drawdown' in result_dict
        assert 'num_wins' in result_dict
        assert 'num_losses' in result_dict


class TestStrategyBacktestIntegration:
    """Integration tests combining strategy and backtester."""
    
    def test_end_to_end_covered_call_backtest(self):
        """Complete end-to-end test of covered call strategy backtest."""
        # Configure strategy
        strategy = CoveredCallScreener(config={
            'min_stock_price': 100.0,
            'max_stock_price': 500.0,
            'target_delta': 0.30,
            'min_premium': 0.50,
            'min_volume': 100000,
            'days_to_expiration_min': 7,
            'days_to_expiration_max': 45
        })
        
        # Create realistic market data (3 months)
        dates = pd.date_range(start='2024-07-01', periods=60, freq='B')  # Business days
        
        # Simulate stock price with some volatility
        np.random.seed(42)
        prices = 175.0 + np.cumsum(np.random.randn(60) * 2)
        prices = np.clip(prices, 150, 200)  # Keep in reasonable range
        
        market_data = pd.DataFrame({
            'date': dates,
            'symbol': 'AAPL',
            'close': prices,
            'volume': np.random.randint(40000000, 60000000, 60)
        })
        
        # Run backtest
        backtester = Backtester(
            initial_capital=50000.0,
            commission_per_contract=0.65,
            slippage_pct=0.01
        )
        
        result = backtester.run(strategy, market_data)
        
        # Comprehensive assertions
        assert result.initial_capital == 50000.0
        assert result.num_days == 60
        
        # Should complete without errors
        result_dict = result.to_dict()
        assert 'total_pnl' in result_dict
        assert 'num_trades' in result_dict
        
        # P&L can be positive or negative, but should be calculated
        assert isinstance(result.total_pnl, (int, float))
        
        # If trades were made, check trade details
        if result.num_trades > 0:
            assert len(result.trades) > 0
            first_trade = result.trades[0]
            assert 'entry_date' in first_trade
            assert 'exit_date' in first_trade
            assert 'pnl' in first_trade
            
            # Win rate should be between 0 and 100
            assert 0 <= result.win_rate <= 100
    
    def test_backtest_respects_capital_limits(self):
        """Test that backtester respects capital constraints."""
        # Strategy that tries to buy many contracts
        class AggressiveStrategy(BaseStrategy):
            def generate_signals(self, data):
                calls = data.get('options_chain', {}).get('calls', [])
                if calls:
                    # Try to buy 100 contracts (should be limited by capital)
                    return [{
                        'action': 'buy',
                        'symbol': calls[0]['symbol'],
                        'quantity': 100,
                        'reason': 'Aggressive buy'
                    }]
                return []
        
        strategy = AggressiveStrategy("Aggressive", {})
        
        # Small capital
        backtester = Backtester(initial_capital=1000.0)
        
        dates = pd.date_range(start='2024-10-01', periods=5, freq='D')
        market_data = pd.DataFrame({
            'date': dates,
            'symbol': 'SPY',
            'close': [450.0] * 5,
            'volume': [1000000] * 5
        })
        
        result = backtester.run(strategy, market_data)
        
        # Should not go negative
        assert result.final_capital >= 0
        
        # Should not have bought 100 contracts (not enough capital)
        total_quantity = sum([abs(pos['quantity']) for pos in backtester.positions])
        assert total_quantity < 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

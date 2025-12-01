"""
Test Suite for Sprint 1: Strategy Proving Ground

Comprehensive unit tests for all three trading strategies:
1. Income Generator (Iron Condor)
2. Trend Follower (Bull Call Spread)
3. Volatility Hedge (Bear Put Spread)

Each strategy is tested for:
- Signal generation with valid entry conditions
- Signal generation with invalid entry conditions (no signal)
- Exit condition logic (profit target, stop loss, custom triggers)
- Edge cases and error handling
"""

import pytest
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime, timedelta

from strategies.income_generator_strategy import IncomeGeneratorStrategy
from strategies.trend_follower_strategy import TrendFollowerStrategy
from strategies.volatility_hedge_strategy import VolatilityHedgeStrategy


# ===========================
# FIXTURES: Mock Data Helpers
# ===========================

@pytest.fixture
def mock_options_chain():
    """Create mock options chain with various strikes and deltas."""
    base_price = 450.0
    strikes = np.arange(base_price - 30, base_price + 40, 5)
    
    options = []
    for strike in strikes:
        # Call deltas (positive, higher for lower strikes)
        call_delta = max(5, min(95, 50 + (base_price - strike) * 1.5))
        options.append({
            'type': 'call',
            'strike': float(strike),
            'delta': call_delta,
            'mark': max(0.5, abs(base_price - strike) * 0.1),
            'dte': 45
        })
        
        # Put deltas (negative, more negative for higher strikes)
        put_delta = -max(5, min(95, 50 + (strike - base_price) * 1.5))
        options.append({
            'type': 'put',
            'strike': float(strike),
            'delta': put_delta,
            'mark': max(0.5, abs(strike - base_price) * 0.1),
            'dte': 45
        })
    
    return options


@pytest.fixture
def mock_historical_prices():
    """Create mock historical price data with MA crossover."""
    dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
    
    # Create prices with uptrend for MA crossover
    base_price = 440.0
    prices = [base_price + i * 0.3 + np.random.randn() * 2 for i in range(60)]
    
    df = pd.DataFrame({
        'date': dates,
        'close': prices
    })
    
    return df


@pytest.fixture
def income_strategy():
    """Create Income Generator Strategy instance."""
    return IncomeGeneratorStrategy(
        symbols=['SPY', 'QQQ'],
        iv_rank_threshold=30,
        target_dte=45,
        strike_delta=15,
        spread_width=5
    )


@pytest.fixture
def trend_strategy():
    """Create Trend Follower Strategy instance."""
    return TrendFollowerStrategy(
        symbols=['SPY', 'QQQ'],
        short_ma_period=20,
        long_ma_period=50,
        min_dte=30,
        max_dte=60,
        long_leg_delta=40,
        short_leg_delta=20
    )


@pytest.fixture
def volatility_strategy():
    """Create Volatility Hedge Strategy instance."""
    return VolatilityHedgeStrategy(
        symbols=['VXX', 'UVXY'],
        vix_entry_threshold=15,
        vix_exit_spike=30,
        min_dte=30,
        max_dte=60
    )


# ===================================
# INCOME GENERATOR STRATEGY TESTS
# ===================================

def test_income_generator_high_iv_signal(income_strategy, mock_options_chain):
    """Test that Income Generator creates Iron Condor signal when IV Rank > 30."""
    data = {
        'SPY': {
            'quote': {'c': 450.0},
            'iv_rank': 35.5,  # Above threshold
            'options_chain': mock_options_chain
        }
    }
    
    signals = income_strategy.generate_signals(data)
    
    # Should generate 1 signal for SPY
    assert len(signals) == 1
    signal = signals[0]
    
    # Validate signal structure
    assert signal['action'] == 'OPEN_IRON_CONDOR'
    assert signal['symbol'] == 'SPY'
    assert signal['strategy_type'] == 'iron_condor'
    assert len(signal['legs']) == 4
    
    # Validate Iron Condor structure (2 shorts, 2 longs)
    actions = [leg['action'] for leg in signal['legs']]
    assert actions.count('sell') == 2
    assert actions.count('buy') == 2
    
    # Validate entry criteria
    assert signal['entry_criteria']['iv_rank'] == 35.5
    assert signal['entry_criteria']['iv_rank_threshold'] == 30


def test_income_generator_low_iv_no_signal(income_strategy, mock_options_chain):
    """Test that Income Generator does NOT create signal when IV Rank < 30."""
    data = {
        'SPY': {
            'quote': {'c': 450.0},
            'iv_rank': 25.0,  # Below threshold
            'options_chain': mock_options_chain
        }
    }
    
    signals = income_strategy.generate_signals(data)
    
    # Should NOT generate any signals
    assert len(signals) == 0


def test_income_generator_exit_profit_target(income_strategy):
    """Test that Income Generator exits at 50% profit target."""
    position = {
        'symbol': 'SPY',
        'entry_credit': 2.00,
        'current_value': 1.00,
        'pnl_pct': 50.0  # 50% profit
    }
    
    exit_decision = income_strategy.check_exit_conditions(position, {})
    
    assert exit_decision['action'] == 'CLOSE'
    assert 'Profit target' in exit_decision['reason']


def test_income_generator_exit_stop_loss(income_strategy):
    """Test that Income Generator exits at -100% stop loss."""
    position = {
        'symbol': 'SPY',
        'entry_credit': 2.00,
        'current_value': 4.00,
        'pnl_pct': -100.0  # 100% loss
    }
    
    exit_decision = income_strategy.check_exit_conditions(position, {})
    
    assert exit_decision['action'] == 'CLOSE'
    assert 'Stop loss' in exit_decision['reason']


def test_income_generator_exit_time_decay(income_strategy):
    """Test that Income Generator exits when DTE < 21."""
    position = {
        'symbol': 'SPY',
        'dte': 18,  # Less than 21
        'pnl_pct': 10.0
    }
    
    exit_decision = income_strategy.check_exit_conditions(position, {})
    
    assert exit_decision['action'] == 'CLOSE'
    assert 'DTE' in exit_decision['reason']


# ==================================
# TREND FOLLOWER STRATEGY TESTS
# ==================================

def test_trend_follower_ma_crossover_signal(trend_strategy, mock_options_chain, 
                                             mock_historical_prices):
    """Test that Trend Follower creates Bull Call Spread on MA crossover."""
    # Calculate MAs showing golden cross
    ma_20 = mock_historical_prices['close'].rolling(20).mean().iloc[-1]
    ma_50 = mock_historical_prices['close'].rolling(50).mean().iloc[-1]
    
    data = {
        'SPY': {
            'quote': {'c': 450.0},
            'ma_20': ma_20,
            'ma_50': ma_50 - 1.0,  # 20 SMA above 50 SMA
            'ma_crossover': True,  # Explicit crossover flag
            'historical_prices': mock_historical_prices,
            'options_chain': mock_options_chain
        }
    }
    
    signals = trend_strategy.generate_signals(data)
    
    # Should generate 1 signal for SPY
    assert len(signals) == 1
    signal = signals[0]
    
    # Validate signal structure
    assert signal['action'] == 'OPEN_BULL_CALL_SPREAD'
    assert signal['symbol'] == 'SPY'
    assert signal['strategy_type'] == 'bull_call_spread'
    assert len(signal['legs']) == 2
    
    # Validate Bull Call Spread structure (1 buy, 1 sell)
    assert signal['legs'][0]['action'] == 'buy'
    assert signal['legs'][0]['type'] == 'call'
    assert signal['legs'][1]['action'] == 'sell'
    assert signal['legs'][1]['type'] == 'call'
    
    # Validate strikes (buy lower, sell higher)
    assert signal['legs'][0]['strike'] < signal['legs'][1]['strike']
    
    # Validate entry criteria
    assert signal['entry_criteria']['crossover_confirmed'] is True


def test_trend_follower_no_crossover_no_signal(trend_strategy, mock_options_chain,
                                                 mock_historical_prices):
    """Test that Trend Follower does NOT create signal without MA crossover."""
    data = {
        'SPY': {
            'quote': {'c': 450.0},
            'ma_20': 448.0,
            'ma_50': 452.0,  # 20 SMA below 50 SMA
            'ma_crossover': False,
            'historical_prices': mock_historical_prices,
            'options_chain': mock_options_chain
        }
    }
    
    signals = trend_strategy.generate_signals(data)
    
    # Should NOT generate any signals
    assert len(signals) == 0


def test_trend_follower_exit_profit_target(trend_strategy):
    """Test that Trend Follower exits at 100% profit target."""
    position = {
        'symbol': 'SPY',
        'entry_debit': 5.00,
        'current_value': 10.00,
        'pnl_pct': 100.0  # 100% profit
    }
    
    market_data = {
        'SPY': {'ma_20': 450, 'ma_50': 445}  # Still in uptrend
    }
    
    exit_decision = trend_strategy.check_exit_conditions(position, market_data)
    
    assert exit_decision['action'] == 'CLOSE'
    assert 'Profit target' in exit_decision['reason']


def test_trend_follower_exit_stop_loss(trend_strategy):
    """Test that Trend Follower exits at -50% stop loss."""
    position = {
        'symbol': 'SPY',
        'entry_debit': 5.00,
        'current_value': 2.50,
        'pnl_pct': -50.0  # 50% loss
    }
    
    market_data = {
        'SPY': {'ma_20': 450, 'ma_50': 445}
    }
    
    exit_decision = trend_strategy.check_exit_conditions(position, market_data)
    
    assert exit_decision['action'] == 'CLOSE'
    assert 'Stop loss' in exit_decision['reason']


def test_trend_follower_exit_death_cross(trend_strategy):
    """Test that Trend Follower exits on Death Cross (20 SMA < 50 SMA)."""
    position = {
        'symbol': 'SPY',
        'pnl_pct': 20.0  # Small profit, but trend reversing
    }
    
    market_data = {
        'SPY': {
            'ma_20': 445.0,
            'ma_50': 448.0  # Death Cross: 20 SMA dropped below 50 SMA
        }
    }
    
    exit_decision = trend_strategy.check_exit_conditions(position, market_data)
    
    assert exit_decision['action'] == 'CLOSE'
    assert 'Trend reversal' in exit_decision['reason'] or 'Death Cross' in exit_decision['reason']


# ===================================
# VOLATILITY HEDGE STRATEGY TESTS
# ===================================

def test_volatility_hedge_low_vix_signal(volatility_strategy, mock_options_chain):
    """Test that Volatility Hedge creates Bear Put Spread when VIX < 15."""
    data = {
        'VXX': {
            'quote': {'c': 18.5},
            'options_chain': mock_options_chain
        },
        'MARKET': {
            'vix': 12.3  # Low VIX
        }
    }
    
    signals = volatility_strategy.generate_signals(data)
    
    # Should generate 1 signal for VXX
    assert len(signals) == 1
    signal = signals[0]
    
    # Validate signal structure
    assert signal['action'] == 'OPEN_BEAR_PUT_SPREAD'
    assert signal['symbol'] == 'VXX'
    assert signal['strategy_type'] == 'bear_put_spread'
    assert len(signal['legs']) == 2
    
    # Validate Bear Put Spread structure (1 buy, 1 sell)
    assert signal['legs'][0]['action'] == 'buy'
    assert signal['legs'][0]['type'] == 'put'
    assert signal['legs'][1]['action'] == 'sell'
    assert signal['legs'][1]['type'] == 'put'
    
    # Validate strikes (buy higher, sell lower)
    assert signal['legs'][0]['strike'] > signal['legs'][1]['strike']
    
    # Validate entry criteria
    assert signal['entry_criteria']['vix_level'] == 12.3
    assert signal['entry_criteria']['low_volatility_confirmed'] is True


def test_volatility_hedge_high_vix_no_signal(volatility_strategy, mock_options_chain):
    """Test that Volatility Hedge does NOT create signal when VIX >= 15."""
    data = {
        'VXX': {
            'quote': {'c': 18.5},
            'options_chain': mock_options_chain
        },
        'MARKET': {
            'vix': 18.5  # High VIX
        }
    }
    
    signals = volatility_strategy.generate_signals(data)
    
    # Should NOT generate any signals
    assert len(signals) == 0


def test_volatility_hedge_exit_profit_target(volatility_strategy):
    """Test that Volatility Hedge exits at 200% profit target."""
    position = {
        'symbol': 'VXX',
        'entry_debit': 1.00,
        'current_value': 3.00,
        'pnl_pct': 200.0  # 200% profit (volatility spike)
    }
    
    market_data = {'MARKET': {'vix': 25.0}}
    
    exit_decision = volatility_strategy.check_exit_conditions(position, market_data)
    
    assert exit_decision['action'] == 'CLOSE'
    assert 'Profit target' in exit_decision['reason']


def test_volatility_hedge_exit_stop_loss(volatility_strategy):
    """Test that Volatility Hedge exits at -75% stop loss."""
    position = {
        'symbol': 'VXX',
        'entry_debit': 1.00,
        'current_value': 0.25,
        'pnl_pct': -75.0  # 75% loss
    }
    
    market_data = {'MARKET': {'vix': 12.0}}
    
    exit_decision = volatility_strategy.check_exit_conditions(position, market_data)
    
    assert exit_decision['action'] == 'CLOSE'
    assert 'Stop loss' in exit_decision['reason']


def test_volatility_hedge_exit_vix_spike(volatility_strategy):
    """Test that Volatility Hedge exits when VIX spikes above 30."""
    position = {
        'symbol': 'VXX',
        'pnl_pct': 150.0  # Strong profit, but VIX spiked
    }
    
    market_data = {'MARKET': {'vix': 32.5}}  # VIX spike
    
    exit_decision = volatility_strategy.check_exit_conditions(position, market_data)
    
    assert exit_decision['action'] == 'CLOSE'
    assert 'VIX spike' in exit_decision['reason']


# ===================================
# EDGE CASES & ERROR HANDLING TESTS
# ===================================

def test_income_generator_missing_options_chain(income_strategy):
    """Test graceful handling of missing options chain."""
    data = {
        'SPY': {
            'quote': {'c': 450.0},
            'iv_rank': 40.0,
            'options_chain': []  # Empty chain
        }
    }
    
    signals = income_strategy.generate_signals(data)
    assert len(signals) == 0


def test_trend_follower_insufficient_historical_data(trend_strategy):
    """Test graceful handling of insufficient historical data."""
    short_history = pd.DataFrame({
        'close': [450.0, 451.0, 452.0]  # Only 3 days
    })
    
    data = {
        'SPY': {
            'quote': {'c': 450.0},
            'historical_prices': short_history,
            'options_chain': []
        }
    }
    
    signals = trend_strategy.generate_signals(data)
    assert len(signals) == 0


def test_volatility_hedge_missing_vix(volatility_strategy, mock_options_chain):
    """Test graceful handling of missing VIX data."""
    data = {
        'VXX': {
            'quote': {'c': 18.5},
            'options_chain': mock_options_chain
        }
        # No VIX data provided
    }
    
    signals = volatility_strategy.generate_signals(data)
    # Should not generate signals without VIX data
    assert len(signals) == 0


def test_exit_hold_decision(income_strategy):
    """Test that strategies return HOLD when no exit condition is met."""
    position = {
        'symbol': 'SPY',
        'pnl_pct': 10.0,  # Small profit, no exit trigger
        'dte': 30
    }
    
    exit_decision = income_strategy.check_exit_conditions(position, {})
    
    assert exit_decision['action'] == 'HOLD'
    assert exit_decision['reason'] is None


# ===================================
# INTEGRATION TESTS
# ===================================

def test_all_strategies_instantiate():
    """Test that all three strategies can be instantiated without errors."""
    income = IncomeGeneratorStrategy()
    trend = TrendFollowerStrategy()
    volatility = VolatilityHedgeStrategy()
    
    assert income is not None
    assert trend is not None
    assert volatility is not None


def test_multiple_symbols_scanning(income_strategy, mock_options_chain):
    """Test that strategies can scan multiple symbols simultaneously."""
    data = {
        'SPY': {
            'quote': {'c': 450.0},
            'iv_rank': 35.0,
            'options_chain': mock_options_chain
        },
        'QQQ': {
            'quote': {'c': 380.0},
            'iv_rank': 38.0,
            'options_chain': mock_options_chain
        }
    }
    
    signals = income_strategy.generate_signals(data)
    
    # Should generate signals for both symbols
    assert len(signals) == 2
    symbols = [s['symbol'] for s in signals]
    assert 'SPY' in symbols
    assert 'QQQ' in symbols


if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main([__file__, '-v', '-s'])

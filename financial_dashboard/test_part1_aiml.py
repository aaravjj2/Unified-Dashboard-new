"""
Comprehensive Test Suite for Part 1: AI/ML Integration
=======================================================

Tests for:
1. DeepLSTMForecaster - Model building, training, prediction
2. TechnicalFeatureEngine - Feature computation and validation
3. StockTradingEnv - Environment mechanics and state/action spaces
4. PPOAgent - Actor-Critic network and training

Run with: pytest test_part1_aiml.py -v
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# TEST DATA FIXTURES
# ============================================================

@pytest.fixture
def sample_price_data():
    """Generate sample price data for testing."""
    np.random.seed(42)
    n_days = 200
    
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='D')
    
    # Generate realistic price movement
    returns = np.random.normal(0.0005, 0.02, n_days)
    prices = 100 * np.cumprod(1 + returns)
    
    # Add volume
    volume = np.random.randint(1000000, 5000000, n_days)
    
    df = pd.DataFrame({
        'ds': dates,
        'date': dates,
        'y': prices,
        'close': prices,
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, n_days)),
        'high': prices * (1 + np.random.uniform(0, 0.02, n_days)),
        'low': prices * (1 - np.random.uniform(0, 0.02, n_days)),
        'volume': volume
    })
    
    return df


@pytest.fixture
def sample_ohlcv_data():
    """Generate OHLCV data for technical indicators."""
    np.random.seed(42)
    n_days = 300
    
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='D')
    
    # Generate prices with trend and noise
    trend = np.linspace(0, 50, n_days)
    noise = np.cumsum(np.random.normal(0, 2, n_days))
    close = 100 + trend + noise
    
    # Generate OHLC
    daily_range = np.abs(np.random.normal(0, 2, n_days))
    open_prices = close + np.random.uniform(-1, 1, n_days)
    high = np.maximum(close, open_prices) + daily_range
    low = np.minimum(close, open_prices) - daily_range
    volume = np.random.randint(500000, 2000000, n_days)
    
    return pd.DataFrame({
        'ds': dates,
        'date': dates,
        'open': open_prices,
        'high': high,
        'low': low,
        'close': close,
        'y': close,
        'volume': volume
    })


# ============================================================
# DEEP LSTM FORECASTER TESTS
# ============================================================

class TestDeepLSTMForecaster:
    """Tests for DeepLSTMForecaster."""
    
    def test_import(self):
        """Test that DeepLSTMForecaster can be imported."""
        from financial_dashboard.models.deep_lstm_forecaster import DeepLSTMForecaster
        assert DeepLSTMForecaster is not None
    
    def test_initialization(self):
        """Test DeepLSTMForecaster initialization with various configs."""
        from financial_dashboard.models.deep_lstm_forecaster import DeepLSTMForecaster
        
        # Default initialization
        model = DeepLSTMForecaster()
        assert model.lookback == 60
        assert model.lstm_units == [25, 10]
        assert model.use_attention == True
        
        # Custom initialization
        model = DeepLSTMForecaster(
            lookback=30,
            lstm_units=[50, 25],
            use_attention=False,
            dropout=0.3
        )
        assert model.lookback == 30
        assert model.lstm_units == [50, 25]
        assert model.use_attention == False
        assert model.dropout == 0.3
    
    def test_feature_computation(self, sample_price_data):
        """Test that features are computed correctly."""
        from financial_dashboard.models.deep_lstm_forecaster import DeepLSTMForecaster
        
        model = DeepLSTMForecaster(lookback=30)
        features = model._compute_features(sample_price_data)
        
        assert features is not None
        assert len(features) == len(sample_price_data)
        assert features.shape[1] > 5  # Should have multiple features
        assert not np.isnan(features).any(), "Features contain NaN values"
        assert not np.isinf(features).any(), "Features contain inf values"
    
    def test_rsi_computation(self, sample_price_data):
        """Test RSI calculation."""
        from financial_dashboard.models.deep_lstm_forecaster import DeepLSTMForecaster
        
        model = DeepLSTMForecaster()
        rsi = model._compute_rsi(sample_price_data['close'], period=14)
        
        # RSI should be bounded [0, 100]
        valid_rsi = rsi.dropna()
        assert (valid_rsi >= 0).all(), "RSI should be >= 0"
        assert (valid_rsi <= 100).all(), "RSI should be <= 100"
    
    def test_sequence_creation(self, sample_price_data):
        """Test sequence creation for training."""
        from financial_dashboard.models.deep_lstm_forecaster import DeepLSTMForecaster
        
        model = DeepLSTMForecaster(lookback=30, use_embeddings=True)
        
        # Initialize scalers
        model.feature_scaler = None
        
        inputs, y_price, y_confidence = model.create_sequences(sample_price_data, ticker='AAPL')
        
        # Check shapes
        assert len(inputs) == 3, "Should have 3 inputs with embeddings"
        assert inputs[0].shape[1] == 30, "Sequence length should be lookback"
        assert len(y_price) == len(y_confidence), "Labels should have same length"
        assert len(y_price) == len(sample_price_data) - 30, "Should have n-lookback samples"
    
    def test_fit_statistical_fallback(self, sample_price_data):
        """Test fitting with statistical fallback (no TF)."""
        from financial_dashboard.models.deep_lstm_forecaster import DeepLSTMForecaster, TF_AVAILABLE
        
        model = DeepLSTMForecaster(lookback=30, epochs=1)
        model.fit(sample_price_data)
        
        assert model.fitted == True
        assert model.data is not None
    
    def test_predict_statistical_fallback(self, sample_price_data):
        """Test prediction with statistical fallback."""
        from financial_dashboard.models.deep_lstm_forecaster import DeepLSTMForecaster
        
        model = DeepLSTMForecaster(lookback=30)
        model.fit(sample_price_data)
        
        predictions = model._predict_statistical(horizon=5)
        
        assert 'forecast' in predictions
        assert 'lower' in predictions
        assert 'upper' in predictions
        assert len(predictions['forecast']) == 5
        assert len(predictions['lower']) == 5
        assert len(predictions['upper']) == 5
        
        # Lower should be less than forecast, upper should be greater
        for i in range(5):
            assert predictions['lower'][i] <= predictions['forecast'][i]
            assert predictions['upper'][i] >= predictions['forecast'][i]
    
    def test_predict_interface(self, sample_price_data):
        """Test the main predict interface."""
        from financial_dashboard.models.deep_lstm_forecaster import DeepLSTMForecaster
        
        model = DeepLSTMForecaster(lookback=30)
        model.fit(sample_price_data)
        
        result = model.predict(horizon=5)
        
        assert isinstance(result, dict)
        assert 'forecast' in result
        assert len(result['forecast']) == 5
    
    def test_convenience_function(self):
        """Test the create_deep_lstm convenience function."""
        from financial_dashboard.models.deep_lstm_forecaster import create_deep_lstm
        
        model = create_deep_lstm(lookback=45, use_attention=False)
        
        assert model.lookback == 45
        assert model.use_attention == False
        assert model.lstm_units == [25, 10]


# ============================================================
# TECHNICAL FEATURE ENGINE TESTS
# ============================================================

class TestTechnicalFeatureEngine:
    """Tests for TechnicalFeatureEngine."""
    
    def test_import(self):
        """Test that TechnicalFeatureEngine can be imported."""
        from financial_dashboard.features.technical_engine import TechnicalFeatureEngine
        assert TechnicalFeatureEngine is not None
    
    def test_initialization(self, sample_ohlcv_data):
        """Test initialization with various data formats."""
        from financial_dashboard.features.technical_engine import TechnicalFeatureEngine
        
        # With OHLCV data
        engine = TechnicalFeatureEngine(sample_ohlcv_data)
        assert 'close' in engine.df.columns
        assert 'open' in engine.df.columns
        
        # With only close/y column
        simple_df = pd.DataFrame({'y': np.random.randn(100)})
        engine2 = TechnicalFeatureEngine(simple_df)
        assert 'close' in engine2.df.columns
    
    def test_compute_all_features(self, sample_ohlcv_data):
        """Test computing all features."""
        from financial_dashboard.features.technical_engine import TechnicalFeatureEngine
        
        engine = TechnicalFeatureEngine(sample_ohlcv_data)
        result = engine.compute_all()
        
        # Check that features were added
        assert len(result.columns) > 10, "Should have many feature columns"
        
        # Check for NaN values
        feature_cols = engine.get_feature_names()
        for col in feature_cols:
            nan_count = result[col].isna().sum()
            assert nan_count == 0, f"Column {col} has {nan_count} NaN values"
        
        # Check for inf values
        for col in feature_cols:
            inf_count = np.isinf(result[col]).sum()
            assert inf_count == 0, f"Column {col} has {inf_count} inf values"
    
    def test_sma_computation(self, sample_ohlcv_data):
        """Test SMA indicator computation."""
        from financial_dashboard.features.technical_engine import TechnicalFeatureEngine
        
        engine = TechnicalFeatureEngine(sample_ohlcv_data)
        engine._add_sma([5, 20])
        
        # SMA should exist
        assert 'sma_5' in engine.df.columns
        assert 'sma_20' in engine.df.columns
        assert 'sma_5_ratio' in engine.df.columns
        
        # SMA should be close to price (ratio near 1)
        valid_ratio = engine.df['sma_5_ratio'].dropna()
        assert (valid_ratio > 0.5).all() and (valid_ratio < 2.0).all()
    
    def test_rsi_computation(self, sample_ohlcv_data):
        """Test RSI indicator computation."""
        from financial_dashboard.features.technical_engine import TechnicalFeatureEngine
        
        engine = TechnicalFeatureEngine(sample_ohlcv_data)
        engine._add_rsi([14])
        
        assert 'rsi_14' in engine.df.columns
        assert 'rsi_14_oversold' in engine.df.columns
        assert 'rsi_14_overbought' in engine.df.columns
        
        # RSI should be bounded [0, 100]
        rsi = engine.df['rsi_14'].dropna()
        assert (rsi >= 0).all() and (rsi <= 100).all()
    
    def test_macd_computation(self, sample_ohlcv_data):
        """Test MACD indicator computation."""
        from financial_dashboard.features.technical_engine import TechnicalFeatureEngine
        
        engine = TechnicalFeatureEngine(sample_ohlcv_data)
        engine._add_macd()
        
        assert 'macd' in engine.df.columns
        assert 'macd_signal' in engine.df.columns
        assert 'macd_histogram' in engine.df.columns
        
        # Histogram should be macd - signal
        diff = engine.df['macd'] - engine.df['macd_signal'] - engine.df['macd_histogram']
        assert np.abs(diff.dropna()).max() < 1e-10
    
    def test_bollinger_bands(self, sample_ohlcv_data):
        """Test Bollinger Bands computation."""
        from financial_dashboard.features.technical_engine import TechnicalFeatureEngine
        
        engine = TechnicalFeatureEngine(sample_ohlcv_data)
        engine._add_bollinger_bands()
        
        assert 'bb_upper' in engine.df.columns
        assert 'bb_lower' in engine.df.columns
        assert 'bb_middle' in engine.df.columns
        
        # Upper > Middle > Lower
        valid_idx = ~(engine.df['bb_upper'].isna() | engine.df['bb_lower'].isna())
        assert (engine.df.loc[valid_idx, 'bb_upper'] >= engine.df.loc[valid_idx, 'bb_middle']).all()
        assert (engine.df.loc[valid_idx, 'bb_middle'] >= engine.df.loc[valid_idx, 'bb_lower']).all()
    
    def test_atr_computation(self, sample_ohlcv_data):
        """Test ATR computation."""
        from financial_dashboard.features.technical_engine import TechnicalFeatureEngine
        
        engine = TechnicalFeatureEngine(sample_ohlcv_data)
        engine._add_atr()
        
        assert 'atr' in engine.df.columns
        assert 'atr_pct' in engine.df.columns
        
        # ATR should be positive
        atr = engine.df['atr'].dropna()
        assert (atr >= 0).all()
    
    def test_price_patterns(self, sample_ohlcv_data):
        """Test price pattern features."""
        from financial_dashboard.features.technical_engine import TechnicalFeatureEngine
        
        engine = TechnicalFeatureEngine(sample_ohlcv_data)
        engine._add_price_patterns()
        
        assert 'return_1d' in engine.df.columns
        assert 'volatility_20d' in engine.df.columns
        assert 'momentum_5' in engine.df.columns
    
    def test_get_feature_names(self, sample_ohlcv_data):
        """Test getting feature names."""
        from financial_dashboard.features.technical_engine import TechnicalFeatureEngine
        
        engine = TechnicalFeatureEngine(sample_ohlcv_data)
        engine.compute_all()
        
        names = engine.get_feature_names()
        
        assert isinstance(names, list)
        assert len(names) > 0
        assert 'close' not in names  # Original columns excluded
        assert 'open' not in names
    
    def test_get_features_array(self, sample_ohlcv_data):
        """Test getting features as array."""
        from financial_dashboard.features.technical_engine import TechnicalFeatureEngine
        
        engine = TechnicalFeatureEngine(sample_ohlcv_data)
        engine.compute_all()
        
        arr = engine.get_features_array()
        names = engine.get_feature_names()
        
        assert arr.shape == (len(sample_ohlcv_data), len(names))
        assert not np.isnan(arr).any()
    
    def test_convenience_function(self, sample_ohlcv_data):
        """Test convenience function."""
        from financial_dashboard.features.technical_engine import compute_features_for_training
        
        features, names = compute_features_for_training(sample_ohlcv_data)
        
        assert features.shape[0] == len(sample_ohlcv_data)
        assert len(names) == features.shape[1]


# ============================================================
# STOCK TRADING ENVIRONMENT TESTS
# ============================================================

class TestStockTradingEnv:
    """Tests for StockTradingEnv."""
    
    def test_import(self):
        """Test that StockTradingEnv can be imported."""
        from financial_dashboard.rl.trading_env import StockTradingEnv
        assert StockTradingEnv is not None
    
    def test_initialization(self, sample_ohlcv_data):
        """Test environment initialization."""
        from financial_dashboard.rl.trading_env import StockTradingEnv
        
        env = StockTradingEnv(
            df=sample_ohlcv_data,
            stock_dim=1,
            initial_amount=100000
        )
        
        assert env.initial_amount == 100000
        assert env.stock_dim == 1
        assert env.action_space is not None
        assert env.observation_space is not None
    
    def test_action_space(self, sample_ohlcv_data):
        """Test action space properties."""
        from financial_dashboard.rl.trading_env import StockTradingEnv
        
        env = StockTradingEnv(df=sample_ohlcv_data, stock_dim=3)
        
        assert env.action_space.shape == (3,)
        assert env.action_space.low[0] == -1.0
        assert env.action_space.high[0] == 1.0
    
    def test_observation_space(self, sample_ohlcv_data):
        """Test observation space properties."""
        from financial_dashboard.rl.trading_env import StockTradingEnv
        
        env = StockTradingEnv(
            df=sample_ohlcv_data,
            stock_dim=1,
            tech_indicator_list=['rsi_14']
        )
        
        # State: cash(1) + prices(1) + holdings(1) + tech(1) = 4
        assert env.observation_space.shape[0] >= 4
    
    def test_reset(self, sample_ohlcv_data):
        """Test environment reset."""
        from financial_dashboard.rl.trading_env import StockTradingEnv
        
        env = StockTradingEnv(df=sample_ohlcv_data, stock_dim=1)
        
        state, info = env.reset()
        
        assert state is not None
        assert len(state) == env.observation_space.shape[0]
        assert info['total_asset'] == env.initial_amount
        assert info['cash'] == env.initial_amount
        assert env.day == 0
    
    def test_step_hold(self, sample_ohlcv_data):
        """Test step with hold action."""
        from financial_dashboard.rl.trading_env import StockTradingEnv
        
        env = StockTradingEnv(df=sample_ohlcv_data, stock_dim=1)
        env.reset()
        
        # Hold action (0)
        action = np.array([0.0])
        state, reward, done, truncated, info = env.step(action)
        
        assert state is not None
        assert isinstance(reward, float)
        assert info['trades'] == 0  # No trades for hold
        assert info['cash'] == env.initial_amount  # Cash unchanged
    
    def test_step_buy(self, sample_ohlcv_data):
        """Test step with buy action."""
        from financial_dashboard.rl.trading_env import StockTradingEnv
        
        env = StockTradingEnv(
            df=sample_ohlcv_data,
            stock_dim=1,
            hmax=10
        )
        env.reset()
        
        # Buy action
        action = np.array([1.0])  # Max buy
        state, reward, done, truncated, info = env.step(action)
        
        assert info['trades'] >= 1, "Should have executed a trade"
        assert info['cash'] < env.initial_amount, "Cash should decrease after buy"
        assert env.holdings[0] > 0, "Should hold some shares"
    
    def test_step_sell(self, sample_ohlcv_data):
        """Test step with sell action after buy."""
        from financial_dashboard.rl.trading_env import StockTradingEnv
        
        env = StockTradingEnv(
            df=sample_ohlcv_data,
            stock_dim=1,
            hmax=10
        )
        env.reset()
        
        # First buy
        env.step(np.array([1.0]))
        holdings_after_buy = env.holdings[0]
        
        # Then sell
        action = np.array([-1.0])  # Max sell
        state, reward, done, truncated, info = env.step(action)
        
        assert env.holdings[0] < holdings_after_buy, "Should have sold some shares"
    
    def test_episode_completion(self, sample_ohlcv_data):
        """Test running a full episode."""
        from financial_dashboard.rl.trading_env import StockTradingEnv
        
        # Use smaller dataset for faster test
        small_data = sample_ohlcv_data.head(50).copy()
        
        env = StockTradingEnv(df=small_data, stock_dim=1)
        state, _ = env.reset()
        
        done = False
        steps = 0
        max_steps = 100  # Safety limit
        
        while not done and steps < max_steps:
            action = env.action_space.sample()
            state, reward, done, truncated, info = env.step(action)
            steps += 1
        
        assert done or steps == max_steps, "Episode should complete"
        assert len(env.asset_memory) > 1, "Should have asset history"
    
    def test_portfolio_stats(self, sample_ohlcv_data):
        """Test portfolio statistics computation."""
        from financial_dashboard.rl.trading_env import StockTradingEnv
        
        small_data = sample_ohlcv_data.head(30).copy()
        env = StockTradingEnv(df=small_data, stock_dim=1)
        env.reset()
        
        # Run a few steps
        for _ in range(10):
            action = env.action_space.sample()
            state, reward, done, _, _ = env.step(action)
            if done:
                break
        
        stats = env.get_portfolio_stats()
        
        assert 'total_return' in stats
        assert 'sharpe_ratio' in stats
        assert 'max_drawdown' in stats
    
    def test_transaction_costs(self, sample_ohlcv_data):
        """Test that transaction costs are applied."""
        from financial_dashboard.rl.trading_env import StockTradingEnv
        
        env = StockTradingEnv(
            df=sample_ohlcv_data,
            stock_dim=1,
            transaction_cost_pct=0.01,  # 1% fee
            hmax=10
        )
        env.reset()
        
        initial_cash = env.cash
        
        # Buy
        env.step(np.array([1.0]))
        
        # Check that cost includes transaction fee
        shares = env.holdings[0]
        price = env._get_prices()[0]
        
        # Cash spent should be > shares * price (due to fee)
        cash_spent = initial_cash - env.cash
        expected_min = shares * price * 1.01  # With 1% fee
        
        assert cash_spent >= expected_min * 0.99, "Transaction cost should be applied"
    
    def test_create_trading_env_convenience(self, sample_ohlcv_data):
        """Test convenience function."""
        from financial_dashboard.rl.trading_env import create_trading_env
        
        env = create_trading_env(sample_ohlcv_data)
        
        assert env is not None
        assert hasattr(env, 'reset')
        assert hasattr(env, 'step')


# ============================================================
# PPO AGENT TESTS
# ============================================================

class TestPPOAgent:
    """Tests for PPOAgent."""
    
    def test_import(self):
        """Test that PPOAgent can be imported."""
        from financial_dashboard.rl.ppo_agent import PPOAgent, TORCH_AVAILABLE
        assert PPOAgent is not None or not TORCH_AVAILABLE
    
    @pytest.mark.skipif(
        not __import__('financial_dashboard.rl.ppo_agent', fromlist=['TORCH_AVAILABLE']).TORCH_AVAILABLE,
        reason="PyTorch not available"
    )
    def test_initialization(self):
        """Test PPO agent initialization."""
        from financial_dashboard.rl.ppo_agent import PPOAgent
        
        agent = PPOAgent(
            state_dim=10,
            action_dim=3,
            lr=1e-3
        )
        
        assert agent.state_dim == 10
        assert agent.action_dim == 3
        assert agent.ac is not None
    
    @pytest.mark.skipif(
        not __import__('financial_dashboard.rl.ppo_agent', fromlist=['TORCH_AVAILABLE']).TORCH_AVAILABLE,
        reason="PyTorch not available"
    )
    def test_act(self):
        """Test action selection."""
        from financial_dashboard.rl.ppo_agent import PPOAgent
        import torch
        
        agent = PPOAgent(state_dim=10, action_dim=3)
        
        state = np.random.randn(10).astype(np.float32)
        action, log_prob, value = agent.act(state)
        
        assert action.shape == (3,)
        # log_prob and value can be numpy floats or native floats
        assert np.isscalar(log_prob) or isinstance(log_prob, (float, np.floating))
        assert np.isscalar(value) or isinstance(value, (float, np.floating))
        
        # Actions should be bounded [-1, 1]
        assert (action >= -1).all() and (action <= 1).all()
    
    @pytest.mark.skipif(
        not __import__('financial_dashboard.rl.ppo_agent', fromlist=['TORCH_AVAILABLE']).TORCH_AVAILABLE,
        reason="PyTorch not available"
    )
    def test_deterministic_action(self):
        """Test deterministic action selection."""
        from financial_dashboard.rl.ppo_agent import PPOAgent
        
        agent = PPOAgent(state_dim=10, action_dim=3)
        
        state = np.random.randn(10).astype(np.float32)
        
        # Get deterministic action twice
        action1, _, _ = agent.act(state, deterministic=True)
        action2, _, _ = agent.act(state, deterministic=True)
        
        # Should be identical
        np.testing.assert_array_almost_equal(action1, action2)
    
    @pytest.mark.skipif(
        not __import__('financial_dashboard.rl.ppo_agent', fromlist=['TORCH_AVAILABLE']).TORCH_AVAILABLE,
        reason="PyTorch not available"
    )
    def test_store_transition(self):
        """Test storing transitions in buffer."""
        from financial_dashboard.rl.ppo_agent import PPOAgent
        
        agent = PPOAgent(state_dim=10, action_dim=3)
        
        # Store some transitions
        for _ in range(5):
            state = np.random.randn(10).astype(np.float32)
            action = np.random.randn(3).astype(np.float32)
            agent.store_transition(state, action, 0.1, 1.0, 0.5, False)
        
        assert len(agent.buffer) == 5
    
    @pytest.mark.skipif(
        not __import__('financial_dashboard.rl.ppo_agent', fromlist=['TORCH_AVAILABLE']).TORCH_AVAILABLE,
        reason="PyTorch not available"
    )
    def test_compute_gae(self):
        """Test GAE computation."""
        from financial_dashboard.rl.ppo_agent import PPOAgent
        
        agent = PPOAgent(state_dim=10, action_dim=3)
        
        rewards = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
        values = np.array([0.5, 0.6, 0.7, 0.8, 0.9])
        dones = np.array([False, False, False, False, True])
        last_value = 0.0
        
        returns, advantages = agent.compute_gae(rewards, values, dones, last_value)
        
        assert returns.shape == rewards.shape
        assert advantages.shape == rewards.shape
        
        # Returns should be positive for positive rewards
        assert (returns > 0).all()
    
    @pytest.mark.skipif(
        not __import__('financial_dashboard.rl.ppo_agent', fromlist=['TORCH_AVAILABLE']).TORCH_AVAILABLE,
        reason="PyTorch not available"
    )
    def test_update_with_data(self):
        """Test PPO update with collected data."""
        from financial_dashboard.rl.ppo_agent import PPOAgent
        
        agent = PPOAgent(
            state_dim=10,
            action_dim=3,
            n_epochs=2,
            batch_size=16
        )
        
        # Collect some transitions
        for _ in range(64):
            state = np.random.randn(10).astype(np.float32)
            action, log_prob, value = agent.act(state)
            reward = np.random.randn()
            done = np.random.random() < 0.1
            agent.store_transition(state, action, log_prob, reward, value, done)
        
        # Update
        metrics = agent.update()
        
        assert 'policy_loss' in metrics
        assert 'value_loss' in metrics
        assert 'entropy' in metrics
        
        # Buffer should be cleared after update
        assert len(agent.buffer) == 0
    
    @pytest.mark.skipif(
        not __import__('financial_dashboard.rl.ppo_agent', fromlist=['TORCH_AVAILABLE']).TORCH_AVAILABLE,
        reason="PyTorch not available"
    )
    def test_rollout_buffer(self):
        """Test RolloutBuffer functionality."""
        from financial_dashboard.rl.ppo_agent import RolloutBuffer
        
        buffer = RolloutBuffer()
        
        # Add data
        for i in range(10):
            buffer.add(
                state=np.random.randn(5),
                action=np.random.randn(2),
                log_prob=0.1,
                reward=1.0,
                value=0.5,
                done=i == 9
            )
        
        assert len(buffer) == 10
        
        # Get data
        states, actions, log_probs, rewards, values, dones = buffer.get()
        
        assert states.shape == (10, 5)
        assert actions.shape == (10, 2)
        assert rewards.shape == (10,)
        
        # Clear
        buffer.clear()
        assert len(buffer) == 0


# ============================================================
# INTEGRATION TESTS
# ============================================================

class TestIntegration:
    """Integration tests combining multiple components."""
    
    def test_feature_engine_with_env(self, sample_ohlcv_data):
        """Test using feature engine with trading environment."""
        from financial_dashboard.features.technical_engine import TechnicalFeatureEngine
        from financial_dashboard.rl.trading_env import StockTradingEnv
        
        # Compute features
        engine = TechnicalFeatureEngine(sample_ohlcv_data)
        df_with_features = engine.compute_all()
        
        # Create environment with technical indicators
        tech_cols = ['rsi_14', 'macd', 'sma_20_ratio']
        available_tech = [c for c in tech_cols if c in df_with_features.columns]
        
        env = StockTradingEnv(
            df=df_with_features,
            stock_dim=1,
            tech_indicator_list=available_tech
        )
        
        state, _ = env.reset()
        
        assert state is not None
        assert len(state) == env.observation_space.shape[0]
    
    @pytest.mark.skipif(
        not __import__('financial_dashboard.rl.ppo_agent', fromlist=['TORCH_AVAILABLE']).TORCH_AVAILABLE,
        reason="PyTorch not available"
    )
    def test_ppo_with_trading_env(self, sample_ohlcv_data):
        """Test PPO agent with trading environment."""
        from financial_dashboard.rl.trading_env import StockTradingEnv
        from financial_dashboard.rl.ppo_agent import PPOAgent
        
        # Create environment
        env = StockTradingEnv(
            df=sample_ohlcv_data.head(50),
            stock_dim=1,
            initial_amount=10000
        )
        
        # Create agent
        state, _ = env.reset()
        agent = PPOAgent(
            state_dim=len(state),
            action_dim=1
        )
        
        # Run a few steps
        total_reward = 0
        for _ in range(10):
            action, log_prob, value = agent.act(state)
            next_state, reward, done, _, _ = env.step(action)
            agent.store_transition(state, action, log_prob, reward, value, done)
            total_reward += reward
            state = next_state
            if done:
                break
        
        assert agent.total_steps == 10 or done
    
    def test_deep_lstm_with_features(self, sample_ohlcv_data):
        """Test DeepLSTM using computed features."""
        from financial_dashboard.models.deep_lstm_forecaster import DeepLSTMForecaster
        from financial_dashboard.features.technical_engine import TechnicalFeatureEngine
        
        # First compute features to validate data
        engine = TechnicalFeatureEngine(sample_ohlcv_data)
        df_with_features = engine.compute_all()
        
        # Then fit LSTM
        model = DeepLSTMForecaster(lookback=30, epochs=1)
        model.fit(df_with_features)
        
        # Predict
        result = model.predict(horizon=5)
        
        assert 'forecast' in result
        assert len(result['forecast']) == 5


# ============================================================
# MAIN TEST RUNNER
# ============================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

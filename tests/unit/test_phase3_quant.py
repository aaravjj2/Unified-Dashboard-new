"""
Phase 3 Unit Tests

Tests for:
- RL Trading Agent
- QLib Factor Engine
- Deep Hedging Engine

Run with: PHASE3_DETERMINISTIC=1 pytest tests/unit/test_phase3_quant.py -v

Author: Agent-P3
Date: December 28, 2025
"""

import os
import sys
import pytest
import numpy as np
from datetime import datetime, timedelta

# Set deterministic mode
os.environ['PHASE3_DETERMINISTIC'] = '1'

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


# ========== RL Trading Agent Tests ==========

class TestRLTradingAgent:
    """Tests for RL Trading Agent module."""
    
    def test_01_import(self):
        """Test module imports."""
        from financial_dashboard.engines.rl_trading_agent import (
            RLTradingAgent,
            TradingEnvironment,
            TradingAction,
            RLAgentResult,
            get_rl_trading_agent
        )
        assert RLTradingAgent is not None
        assert TradingEnvironment is not None
    
    def test_02_environment_creation(self):
        """Test trading environment creation."""
        from financial_dashboard.engines.rl_trading_agent import TradingEnvironment
        
        prices = np.linspace(100, 110, 100)
        env = TradingEnvironment(prices)
        
        obs = env.reset()
        assert obs.shape == (6,)
        assert env.cash == 100000.0
        assert env.shares == 0
    
    def test_03_environment_step(self):
        """Test environment step function."""
        from financial_dashboard.engines.rl_trading_agent import TradingEnvironment, TradingAction
        
        prices = np.linspace(100, 110, 100)
        env = TradingEnvironment(prices)
        env.reset()
        
        # Buy action
        obs, reward, done, info = env.step(TradingAction.BUY.value)
        assert obs.shape == (6,)
        assert info['shares'] > 0
        assert not done
    
    def test_04_environment_metrics(self):
        """Test environment metrics calculation."""
        from financial_dashboard.engines.rl_trading_agent import TradingEnvironment
        
        prices = np.linspace(100, 110, 100)
        env = TradingEnvironment(prices)
        env.reset()
        
        # Run some steps
        for _ in range(50):
            env.step(0)  # Hold
        
        metrics = env.get_metrics()
        assert 'total_return' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics
    
    def test_05_agent_creation(self):
        """Test agent creation with different algorithms."""
        from financial_dashboard.engines.rl_trading_agent import RLTradingAgent
        
        for algo in ['PPO', 'A2C', 'DQN']:
            agent = RLTradingAgent(algo)
            assert agent.algorithm == algo
    
    def test_06_agent_training(self):
        """Test agent training."""
        from financial_dashboard.engines.rl_trading_agent import get_rl_trading_agent
        
        agent = get_rl_trading_agent('PPO')
        result = agent.train('SPY', episodes=10)
        
        assert result.ticker == 'SPY'
        assert result.algorithm == 'PPO'
        assert len(result.equity_curve) > 0
        assert result.training_episodes == 10
    
    def test_07_agent_predict(self):
        """Test agent action prediction."""
        from financial_dashboard.engines.rl_trading_agent import get_rl_trading_agent
        
        agent = get_rl_trading_agent('PPO')
        state = np.array([0.05, 0.03, 0.10, 0.25, 0.5, 0.5])
        
        action, confidence = agent.predict_action(state)
        assert action in [0, 1, 2]
        assert 0 <= confidence <= 1
    
    def test_08_action_probabilities(self):
        """Test action probability distribution."""
        from financial_dashboard.engines.rl_trading_agent import get_rl_trading_agent
        
        agent = get_rl_trading_agent('PPO')
        state = np.array([0.05, 0.03, 0.10, 0.25, 0.5, 0.5])
        
        probs = agent.get_action_probabilities(state)
        assert 'hold' in probs
        assert 'buy' in probs
        assert 'sell' in probs
        assert abs(sum(probs.values()) - 1.0) < 0.01
    
    def test_09_chart_data(self):
        """Test chart data generation."""
        from financial_dashboard.engines.rl_trading_agent import get_rl_trading_agent
        
        agent = get_rl_trading_agent('PPO')
        result = agent.train('AAPL', episodes=10)
        chart_data = agent.get_chart_data(result)
        
        assert 'equity_curve' in chart_data
        assert 'buy_markers' in chart_data
        assert 'sell_markers' in chart_data
        assert 'action_distribution' in chart_data
        assert 'metrics' in chart_data
    
    def test_10_singleton_pattern(self):
        """Test singleton pattern."""
        from financial_dashboard.engines.rl_trading_agent import get_rl_trading_agent
        
        agent1 = get_rl_trading_agent('PPO')
        agent2 = get_rl_trading_agent('PPO')
        assert agent1 is agent2


# ========== QLib Factor Engine Tests ==========

class TestQLibFactorEngine:
    """Tests for QLib Factor Engine module."""
    
    def test_11_import(self):
        """Test module imports."""
        from financial_dashboard.engines.qlib_factor_engine import (
            QLibEngine,
            FactorCalculator,
            AlphaGenerator,
            FactorType,
            FactorScore,
            get_qlib_engine
        )
        assert QLibEngine is not None
        assert FactorCalculator is not None
    
    def test_12_factor_calculator_creation(self):
        """Test factor calculator creation."""
        from financial_dashboard.engines.qlib_factor_engine import FactorCalculator
        
        calc = FactorCalculator()
        assert calc is not None
    
    def test_13_momentum_factor(self):
        """Test momentum factor calculation."""
        from financial_dashboard.engines.qlib_factor_engine import FactorCalculator
        
        calc = FactorCalculator()
        factor = calc.calculate_momentum('AAPL')
        
        assert factor.name == 'momentum'
        assert isinstance(factor.raw_value, float)
        assert isinstance(factor.z_score, float)
        assert 0 <= factor.percentile <= 100
        assert factor.signal in ['bullish', 'bearish', 'neutral']
    
    def test_14_volatility_factor(self):
        """Test volatility factor calculation."""
        from financial_dashboard.engines.qlib_factor_engine import FactorCalculator
        
        calc = FactorCalculator()
        factor = calc.calculate_volatility('AAPL')
        
        assert factor.name == 'volatility'
        assert factor.raw_value > 0  # Volatility is always positive
    
    def test_15_value_factor(self):
        """Test value factor calculation."""
        from financial_dashboard.engines.qlib_factor_engine import FactorCalculator
        
        calc = FactorCalculator()
        factor = calc.calculate_value('AAPL')
        
        assert factor.name == 'value'
        assert factor.raw_value > 0  # P/E is positive
    
    def test_16_quality_factor(self):
        """Test quality factor calculation."""
        from financial_dashboard.engines.qlib_factor_engine import FactorCalculator
        
        calc = FactorCalculator()
        factor = calc.calculate_quality('AAPL')
        
        assert factor.name == 'quality'
    
    def test_17_size_factor(self):
        """Test size factor calculation."""
        from financial_dashboard.engines.qlib_factor_engine import FactorCalculator
        
        calc = FactorCalculator()
        factor = calc.calculate_size('AAPL')
        
        assert factor.name == 'size'
        assert factor.raw_value > 0  # Market cap is positive
    
    def test_18_all_factors(self):
        """Test calculating all factors."""
        from financial_dashboard.engines.qlib_factor_engine import FactorCalculator
        
        calc = FactorCalculator()
        factors = calc.calculate_all_factors('MSFT')
        
        assert len(factors) == 5
        factor_names = {f.name for f in factors}
        assert 'momentum' in factor_names
        assert 'volatility' in factor_names
        assert 'value' in factor_names
        assert 'quality' in factor_names
        assert 'size' in factor_names
    
    def test_19_alpha_generator(self):
        """Test alpha signal generation."""
        from financial_dashboard.engines.qlib_factor_engine import AlphaGenerator
        
        gen = AlphaGenerator()
        signal = gen.generate_alpha('GOOGL')
        
        assert signal.ticker == 'GOOGL'
        assert -1 <= signal.alpha_score <= 1
        assert signal.direction in ['long', 'short', 'neutral']
        assert 0 <= signal.confidence <= 1
        assert len(signal.factors) == 5
    
    def test_20_universe_ranking(self):
        """Test ranking a universe of stocks."""
        from financial_dashboard.engines.qlib_factor_engine import AlphaGenerator
        
        gen = AlphaGenerator()
        tickers = ['AAPL', 'MSFT', 'GOOGL']
        ranked = gen.rank_universe(tickers)
        
        assert len(ranked) == 3
        # Should be sorted by alpha descending
        for i in range(len(ranked) - 1):
            assert ranked[i].alpha_score >= ranked[i+1].alpha_score
    
    def test_21_qlib_engine_analyze(self):
        """Test full QLib analysis."""
        from financial_dashboard.engines.qlib_factor_engine import get_qlib_engine
        
        engine = get_qlib_engine()
        result = engine.analyze('NVDA')
        
        assert result.ticker == 'NVDA'
        assert len(result.alpha_signals) > 0
        assert len(result.factor_exposures) > 0
        assert result.recommended_action in ['BUY', 'SELL', 'HOLD']
    
    def test_22_chart_data(self):
        """Test chart data generation."""
        from financial_dashboard.engines.qlib_factor_engine import get_qlib_engine
        
        engine = get_qlib_engine()
        result = engine.analyze('AMZN')
        chart_data = engine.get_chart_data(result)
        
        assert 'exposure_bar' in chart_data
        assert 'radar_data' in chart_data
        assert 'alpha_gauge' in chart_data
        assert 'metrics' in chart_data
        assert 'factor_details' in chart_data
    
    def test_23_singleton_pattern(self):
        """Test singleton pattern."""
        from financial_dashboard.engines.qlib_factor_engine import get_qlib_engine
        
        engine1 = get_qlib_engine()
        engine2 = get_qlib_engine()
        assert engine1 is engine2


# ========== Deep Hedging Engine Tests ==========

class TestDeepHedgingEngine:
    """Tests for Deep Hedging Engine module."""
    
    def test_24_import(self):
        """Test module imports."""
        from financial_dashboard.engines.deep_hedging import (
            DeepHedgingEngine,
            DeepHedger,
            BlackScholesHedger,
            DeepHedgeResult,
            get_deep_hedging_engine
        )
        assert DeepHedgingEngine is not None
        assert DeepHedger is not None
    
    def test_25_bs_hedger_creation(self):
        """Test Black-Scholes hedger creation."""
        from financial_dashboard.engines.deep_hedging import BlackScholesHedger
        
        hedger = BlackScholesHedger()
        assert hedger.rf == 0.05
    
    def test_26_bs_delta_calculation(self):
        """Test BS delta calculation."""
        from financial_dashboard.engines.deep_hedging import BlackScholesHedger
        
        hedger = BlackScholesHedger()
        
        # ATM call
        delta = hedger.calculate_delta(100, 100, 0.25, 0.20, is_call=True)
        assert 0.4 < delta < 0.7  # ATM delta is around 0.5
        
        # Deep ITM call
        delta_itm = hedger.calculate_delta(120, 100, 0.25, 0.20, is_call=True)
        assert delta_itm > delta  # ITM has higher delta
        
        # Deep OTM call
        delta_otm = hedger.calculate_delta(80, 100, 0.25, 0.20, is_call=True)
        assert delta_otm < delta  # OTM has lower delta
    
    def test_27_bs_gamma_calculation(self):
        """Test BS gamma calculation."""
        from financial_dashboard.engines.deep_hedging import BlackScholesHedger
        
        hedger = BlackScholesHedger()
        gamma = hedger.calculate_gamma(100, 100, 0.25, 0.20)
        
        assert gamma > 0  # Gamma is always positive
        
        # ATM has highest gamma
        gamma_otm = hedger.calculate_gamma(80, 100, 0.25, 0.20)
        assert gamma > gamma_otm
    
    def test_28_deep_hedger_creation(self):
        """Test deep hedger creation."""
        from financial_dashboard.engines.deep_hedging import DeepHedger
        
        hedger = DeepHedger(hidden_units=64)
        assert hedger.hidden_units == 64
        assert hedger.weights is not None
    
    def test_29_deep_hedger_predict(self):
        """Test deep hedger delta prediction."""
        from financial_dashboard.engines.deep_hedging import DeepHedger
        
        hedger = DeepHedger()
        delta = hedger.predict_delta(100, 100, 0.25, 0.20, 0.5)
        
        assert 0 <= delta <= 1  # Delta bounded by sigmoid
    
    def test_30_deep_hedger_training(self):
        """Test deep hedger training."""
        from financial_dashboard.engines.deep_hedging import DeepHedger
        
        np.random.seed(42)
        paths = 100 + 10 * np.random.randn(100, 31).cumsum(axis=1)
        paths = np.maximum(paths, 50)  # Ensure positive prices
        
        hedger = DeepHedger()
        hedger.train(paths, strike=100, maturity=30/365, volatility=0.25, epochs=10)
        
        assert hedger._trained
    
    def test_31_hedge_comparison(self):
        """Test full hedge comparison."""
        from financial_dashboard.engines.deep_hedging import get_deep_hedging_engine
        
        engine = get_deep_hedging_engine()
        result = engine.run_hedge_comparison(
            ticker='SPY',
            maturity_days=30,
            n_paths=100
        )
        
        assert result.ticker == 'SPY'
        assert result.maturity_days == 30
        assert len(result.deep_deltas) > 0
        assert len(result.bs_deltas) > 0
        assert len(result.spot_path) > 0
    
    def test_32_hedge_metrics(self):
        """Test hedge metrics calculation."""
        from financial_dashboard.engines.deep_hedging import get_deep_hedging_engine
        
        engine = get_deep_hedging_engine()
        result = engine.run_hedge_comparison('AAPL', n_paths=100)
        
        assert isinstance(result.deep_hedge_pnl, float)
        assert isinstance(result.bs_hedge_pnl, float)
        assert result.deep_hedge_std >= 0
        assert result.bs_hedge_std >= 0
    
    def test_33_chart_data(self):
        """Test chart data generation."""
        from financial_dashboard.engines.deep_hedging import get_deep_hedging_engine
        
        engine = get_deep_hedging_engine()
        result = engine.run_hedge_comparison('MSFT', n_paths=100)
        chart_data = engine.get_chart_data(result)
        
        assert 'delta_chart' in chart_data
        assert 'spot_chart' in chart_data
        assert 'pnl_chart' in chart_data
        assert 'cost_comparison' in chart_data
        assert 'metrics' in chart_data
    
    def test_34_singleton_pattern(self):
        """Test singleton pattern."""
        from financial_dashboard.engines.deep_hedging import get_deep_hedging_engine
        
        engine1 = get_deep_hedging_engine()
        engine2 = get_deep_hedging_engine()
        assert engine1 is engine2


# ========== Integration Tests ==========

class TestPhase3Integration:
    """Integration tests for Phase 3 modules."""
    
    def test_35_all_modules_import(self):
        """Test all Phase 3 modules can be imported."""
        from financial_dashboard.engines.rl_trading_agent import get_rl_trading_agent
        from financial_dashboard.engines.qlib_factor_engine import get_qlib_engine
        from financial_dashboard.engines.deep_hedging import get_deep_hedging_engine
        
        assert get_rl_trading_agent is not None
        assert get_qlib_engine is not None
        assert get_deep_hedging_engine is not None
    
    def test_36_cross_module_workflow(self):
        """Test using multiple modules together."""
        from financial_dashboard.engines.qlib_factor_engine import get_qlib_engine
        from financial_dashboard.engines.rl_trading_agent import get_rl_trading_agent
        
        # Get factor recommendation
        qlib = get_qlib_engine()
        factor_result = qlib.analyze('SPY')
        
        # Use factor result to inform RL agent
        if factor_result.recommended_action == 'BUY':
            agent = get_rl_trading_agent('PPO')
            rl_result = agent.train('SPY', episodes=10)
            assert rl_result is not None
    
    def test_37_deterministic_mode(self):
        """Test deterministic mode produces consistent results."""
        os.environ['PHASE3_DETERMINISTIC'] = '1'
        
        from financial_dashboard.engines.rl_trading_agent import get_rl_trading_agent
        
        # Reset singleton
        import financial_dashboard.engines.rl_trading_agent as rl_module
        rl_module._rl_agent_instance = None
        
        agent1 = get_rl_trading_agent('PPO')
        result1 = agent1.train('SPY', episodes=10)
        
        # Reset and retrain
        rl_module._rl_agent_instance = None
        agent2 = get_rl_trading_agent('PPO')
        result2 = agent2.train('SPY', episodes=10)
        
        # Results should be identical in deterministic mode
        assert result1.total_return == result2.total_return
        assert result1.sharpe_ratio == result2.sharpe_ratio
    
    def test_38_performance_benchmark(self):
        """Test performance benchmark."""
        import time
        
        from financial_dashboard.engines.qlib_factor_engine import get_qlib_engine
        
        engine = get_qlib_engine()
        
        start = time.time()
        for ticker in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']:
            engine.analyze(ticker)
        elapsed = time.time() - start
        
        print(f"\nPerformance: 5 factor analyses in {elapsed:.2f}s")
        assert elapsed < 30  # Should complete in under 30 seconds


# ========== Main Runner ==========

if __name__ == '__main__':
    # Run all tests
    os.environ['PHASE3_DETERMINISTIC'] = '1'
    
    # Track results
    passed = 0
    failed = 0
    errors = 0
    
    test_classes = [
        TestRLTradingAgent,
        TestQLibFactorEngine,
        TestDeepHedgingEngine,
        TestPhase3Integration
    ]
    
    print("=" * 70)
    print("PHASE 3 UNIT TESTS")
    print("=" * 70)
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}")
        print("-" * 50)
        
        instance = test_class()
        
        # Get all test methods
        methods = [m for m in dir(instance) if m.startswith('test_')]
        methods.sort()
        
        for method_name in methods:
            method = getattr(instance, method_name)
            try:
                method()
                print(f"  ✅ {method_name}")
                passed += 1
            except AssertionError as e:
                print(f"  ❌ {method_name}: {str(e)[:50]}")
                failed += 1
            except Exception as e:
                print(f"  ⚠️ {method_name}: {type(e).__name__}: {str(e)[:50]}")
                errors += 1
    
    # Summary
    total = passed + failed + errors
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Errors: {errors} ⚠️")
    print(f"Pass Rate: {passed/total*100:.1f}%")
    print("=" * 70)
    
    sys.exit(0 if failed + errors == 0 else 1)

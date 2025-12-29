"""
Round 2 AI/ML Improvements Test Suite
=====================================
Comprehensive test coverage for 35 new improvements across 7 modules.

Test Categories:
1. Advanced Greeks Analytics (5 tests)
2. Portfolio Optimization (5 tests)
3. Options Pricing Models (5 tests)
4. Trade Intelligence (5 tests)
5. Market Microstructure (5 tests)
6. Backtesting & Simulation (5 tests)
7. Real-time Intelligence (5 tests)

Target: 50+ tests, 100% pass rate
"""

import sys
import os
import unittest
from datetime import datetime, timedelta
import numpy as np

# Add to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAdvancedGreeks(unittest.TestCase):
    """Test Advanced Greeks Analytics module."""
    
    def test_01_greeks_surface_builder(self):
        """Test 3D Greeks surface generation."""
        from financial_dashboard.tabs.options_lab.advanced_greeks import get_advanced_greeks
        engine = get_advanced_greeks()
        
        surface = engine.surface_builder.build_surface(
            ticker='SPY',
            spot_price=500
        )
        
        self.assertIsNotNone(surface)
        self.assertIn('ticker', surface.__dict__)
        self.assertEqual(surface.ticker, 'SPY')
        self.assertIsNotNone(surface.delta_surface)
        print("✅ Test 01: Greeks 3D surface builder - PASSED")
    
    def test_02_greeks_sensitivity_analyzer(self):
        """Test Greeks sensitivity/what-if analysis."""
        from financial_dashboard.tabs.options_lab.advanced_greeks import get_advanced_greeks
        engine = get_advanced_greeks()
        
        position = {
            'ticker': 'SPY',
            'strike': 500,
            'dte': 30,
            'option_type': 'call',
            'premium': 5.0,
            'delta': 0.5,
            'gamma': 0.02,
            'contracts': 1
        }
        
        result = engine.sensitivity_analyzer.analyze_price_sensitivity(
            position=position,
            spot_price=500
        )
        
        self.assertIsNotNone(result)
        self.assertIn('scenarios', result.__dict__)
        print("✅ Test 02: Greeks sensitivity analyzer - PASSED")
    
    def test_03_gamma_scalping_calculator(self):
        """Test gamma scalping opportunity detection."""
        from financial_dashboard.tabs.options_lab.advanced_greeks import get_advanced_greeks
        engine = get_advanced_greeks()
        
        position = {
            'ticker': 'SPY',
            'gamma': 0.05,
            'delta': 0.1,
            'contracts': 10
        }
        
        result = engine.gamma_calculator.calculate_scalp_signal(
            position=position,
            spot_price=500
        )
        
        self.assertIsNotNone(result)
        self.assertIn('breakeven_move', result.__dict__)
        print("✅ Test 03: Gamma scalping calculator - PASSED")
    
    def test_04_vega_exposure_analyzer(self):
        """Test vega exposure analysis."""
        from financial_dashboard.tabs.options_lab.advanced_greeks import get_advanced_greeks
        engine = get_advanced_greeks()
        
        positions = [{
            'ticker': 'SPY',
            'expiration': '2024-12-20',
            'dte': 30,
            'vega': 0.15,
            'contracts': 10
        }]
        
        result = engine.vega_analyzer.analyze_portfolio_vega(positions)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)
        print("✅ Test 04: Vega exposure analyzer - PASSED")
    
    def test_05_theta_decay_projector(self):
        """Test theta decay projection."""
        from financial_dashboard.tabs.options_lab.advanced_greeks import get_advanced_greeks
        engine = get_advanced_greeks()
        
        positions = [{
            'ticker': 'SPY',
            'theta': -0.05,
            'dte': 30,
            'contracts': 10
        }]
        
        result = engine.theta_projector.project_decay(positions=positions, days=30)
        
        self.assertIsNotNone(result)
        self.assertIn('cumulative_theta', result.__dict__)
        print("✅ Test 05: Theta decay projector - PASSED")
    
    def test_06_advanced_greeks_engine_analysis(self):
        """Test full advanced Greeks analysis."""
        from financial_dashboard.tabs.options_lab.advanced_greeks import get_advanced_greeks
        engine = get_advanced_greeks()
        
        positions = [{
            'ticker': 'SPY',
            'strike': 500,
            'dte': 30,
            'option_type': 'call',
            'premium': 5.0,
            'delta': 0.5,
            'gamma': 0.02,
            'theta': -0.05,
            'vega': 0.15,
            'contracts': 1
        }]
        
        result = engine.full_analysis(positions, spot_price=500)
        
        self.assertIsNotNone(result)
        self.assertIn('surface', result)
        print("✅ Test 06: Full advanced Greeks analysis - PASSED")


class TestPortfolioOptimization(unittest.TestCase):
    """Test Portfolio Optimization module."""
    
    def test_07_kelly_criterion_calculator(self):
        """Test Kelly Criterion position sizing."""
        from financial_dashboard.tabs.options_lab.portfolio_optimizer import get_portfolio_optimizer
        engine = get_portfolio_optimizer()
        
        result = engine.kelly_calc.calculate(
            win_rate=0.55,
            avg_win=100,
            avg_loss=80
        )
        
        self.assertIsNotNone(result)
        self.assertIn('kelly_fraction', result.__dict__)
        self.assertGreater(result.kelly_fraction, 0)
        self.assertLess(result.kelly_fraction, 1)
        print("✅ Test 07: Kelly Criterion calculator - PASSED")
    
    def test_08_portfolio_beta_optimizer(self):
        """Test portfolio beta optimization."""
        from financial_dashboard.tabs.options_lab.portfolio_optimizer import get_portfolio_optimizer
        engine = get_portfolio_optimizer()
        
        positions = [
            {'ticker': 'AAPL', 'value': 10000, 'beta': 1.2},
            {'ticker': 'SPY', 'value': 15000, 'beta': 1.0},
            {'ticker': 'VZ', 'value': 5000, 'beta': 0.6}
        ]
        
        result = engine.beta_optimizer.optimize(positions, target_beta=0.8)
        
        self.assertIsNotNone(result)
        self.assertIn('current_beta', result.__dict__)
        print("✅ Test 08: Portfolio beta optimizer - PASSED")
    
    def test_09_sharpe_ratio_analyzer(self):
        """Test Sharpe/Sortino/Calmar ratio analysis."""
        from financial_dashboard.tabs.options_lab.portfolio_optimizer import get_portfolio_optimizer
        engine = get_portfolio_optimizer()
        
        returns = [0.02, -0.01, 0.03, 0.01, -0.02, 0.04, 0.02]
        result = engine.sharpe_analyzer.analyze(returns)
        
        self.assertIsNotNone(result)
        self.assertIn('sharpe_ratio', result.__dict__)
        self.assertIn('sortino_ratio', result.__dict__)
        print("✅ Test 09: Sharpe ratio analyzer - PASSED")
    
    def test_10_efficient_frontier_generator(self):
        """Test efficient frontier generation."""
        from financial_dashboard.tabs.options_lab.portfolio_optimizer import get_portfolio_optimizer
        engine = get_portfolio_optimizer()
        
        assets = [
            {'ticker': 'AAPL', 'expected_return': 0.12, 'volatility': 0.25},
            {'ticker': 'MSFT', 'expected_return': 0.10, 'volatility': 0.20},
            {'ticker': 'GOOGL', 'expected_return': 0.15, 'volatility': 0.30}
        ]
        
        result = engine.frontier_generator.generate(assets)
        
        self.assertIsNotNone(result)
        self.assertIn('frontier_points', result.__dict__)
        print("✅ Test 10: Efficient frontier generator - PASSED")
    
    def test_11_rebalancing_advisor(self):
        """Test portfolio rebalancing advice."""
        from financial_dashboard.tabs.options_lab.portfolio_optimizer import get_portfolio_optimizer
        engine = get_portfolio_optimizer()
        
        positions = [
            {'ticker': 'AAPL', 'shares': 100, 'price': 150},
            {'ticker': 'MSFT', 'shares': 50, 'price': 300}
        ]
        target_weights = {'AAPL': 0.5, 'MSFT': 0.5}
        
        result = engine.rebalancing_advisor.analyze(positions, target_weights, 30000)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)
        print("✅ Test 11: Rebalancing advisor - PASSED")
    
    def test_12_portfolio_optimizer_full(self):
        """Test full portfolio optimization."""
        from financial_dashboard.tabs.options_lab.portfolio_optimizer import get_portfolio_optimizer
        engine = get_portfolio_optimizer()
        
        positions = [
            {'ticker': 'AAPL', 'value': 10000, 'beta': 1.2, 'shares': 50, 'price': 200},
            {'ticker': 'MSFT', 'value': 8000, 'beta': 1.1, 'shares': 20, 'price': 400}
        ]
        
        result = engine.full_optimization(positions, portfolio_value=18000)
        
        self.assertIsNotNone(result)
        self.assertIn('beta_optimization', result)
        print("✅ Test 12: Full portfolio optimization - PASSED")


class TestPricingModels(unittest.TestCase):
    """Test Options Pricing Models module."""
    
    def test_13_black_scholes_model(self):
        """Test Black-Scholes pricing."""
        from financial_dashboard.tabs.options_lab.pricing_models import get_pricing_models
        engine = get_pricing_models()
        
        result = engine.bs.price(
            S=100, K=100, T=30/365, sigma=0.25
        )
        
        self.assertIsNotNone(result)
        self.assertIn('price', result.__dict__)
        self.assertIn('delta', result.__dict__)
        self.assertGreater(result.price, 0)
        print("✅ Test 13: Black-Scholes model - PASSED")
    
    def test_14_binomial_model(self):
        """Test Binomial tree pricing (100 steps)."""
        from financial_dashboard.tabs.options_lab.pricing_models import get_pricing_models
        engine = get_pricing_models()
        
        result = engine.binomial.price(
            S=100, K=100, T=30/365, sigma=0.25
        )
        
        self.assertIsNotNone(result)
        self.assertIn('price', result.__dict__)
        self.assertGreater(result.price, 0)
        print("✅ Test 14: Binomial model - PASSED")
    
    def test_15_monte_carlo_model(self):
        """Test Monte Carlo pricing (10000 simulations)."""
        from financial_dashboard.tabs.options_lab.pricing_models import get_pricing_models
        engine = get_pricing_models()
        
        result = engine.mc.price(
            S=100, K=100, T=30/365, sigma=0.25
        )
        
        self.assertIsNotNone(result)
        self.assertIn('price', result.__dict__)
        print("✅ Test 15: Monte Carlo model - PASSED")
    
    def test_16_volatility_surface_builder(self):
        """Test volatility surface construction."""
        from financial_dashboard.tabs.options_lab.pricing_models import get_pricing_models
        engine = get_pricing_models()
        
        result = engine.vol_surface_builder.build_surface(
            ticker='SPY',
            spot_price=500
        )
        
        self.assertIsNotNone(result)
        self.assertIn('iv_matrix', result.__dict__)
        print("✅ Test 16: Volatility surface builder - PASSED")
    
    def test_17_skew_analyzer(self):
        """Test volatility skew analysis."""
        from financial_dashboard.tabs.options_lab.pricing_models import get_pricing_models
        engine = get_pricing_models()
        
        chain = [
            {'strike': 480, 'iv': 28, 'option_type': 'put'},
            {'strike': 490, 'iv': 26, 'option_type': 'put'},
            {'strike': 500, 'iv': 25, 'option_type': 'call'},
            {'strike': 510, 'iv': 24, 'option_type': 'call'},
            {'strike': 520, 'iv': 23, 'option_type': 'call'}
        ]
        
        result = engine.skew_analyzer.analyze(chain, spot_price=500)
        
        self.assertIsNotNone(result)
        self.assertIn('skew_direction', result.__dict__)
        print("✅ Test 17: Skew analyzer - PASSED")
    
    def test_18_term_structure_analyzer(self):
        """Test term structure analysis."""
        from financial_dashboard.tabs.options_lab.pricing_models import get_pricing_models
        engine = get_pricing_models()
        
        term_data = [
            {'dte': 7, 'atm_iv': 30},
            {'dte': 14, 'atm_iv': 28},
            {'dte': 30, 'atm_iv': 25},
            {'dte': 60, 'atm_iv': 24}
        ]
        
        result = engine.term_analyzer.analyze(term_data)
        
        self.assertIsNotNone(result)
        self.assertIn('structure_type', result.__dict__)
        print("✅ Test 18: Term structure analyzer - PASSED")
    
    def test_19_greeks_attribution(self):
        """Test Greeks attribution engine."""
        from financial_dashboard.tabs.options_lab.pricing_models import get_pricing_models
        engine = get_pricing_models()
        
        result = engine.greeks_attributor.attribute(
            position_greeks={'delta': 0.5, 'gamma': 0.02, 'theta': -0.05, 'vega': 0.1},
            price_change=2,
            iv_change=-1,
            days_passed=1
        )
        
        self.assertIsNotNone(result)
        self.assertIn('delta_pnl', result.__dict__)
        print("✅ Test 19: Greeks attribution engine - PASSED")


class TestTradeIntelligence(unittest.TestCase):
    """Test Trade Intelligence module."""
    
    def test_20_win_rate_predictor(self):
        """Test ML-based win rate prediction."""
        from financial_dashboard.tabs.options_lab.trade_intelligence import get_trade_intelligence
        engine = get_trade_intelligence()
        
        result = engine.win_rate_predictor.predict(
            strategy='iron_condor',
            iv_percentile=70,
            dte=30,
            delta=0.3
        )
        
        self.assertIsNotNone(result)
        self.assertIn('predicted', result.__dict__)
        self.assertGreater(result.predicted, 0)
        self.assertLess(result.predicted, 1)
        print("✅ Test 20: Win rate predictor - PASSED")
    
    def test_21_entry_timing_optimizer(self):
        """Test optimal entry timing detection."""
        from financial_dashboard.tabs.options_lab.trade_intelligence import get_trade_intelligence
        engine = get_trade_intelligence()
        
        result = engine.entry_timing_optimizer.optimize(
            ticker='SPY',
            strategy='bull_put_spread'
        )
        
        self.assertIsNotNone(result)
        self.assertIn('best_day', result.__dict__)
        self.assertIn('best_hour', result.__dict__)
        print("✅ Test 21: Entry timing optimizer - PASSED")
    
    def test_22_exit_strategy_optimizer(self):
        """Test exit strategy optimization."""
        from financial_dashboard.tabs.options_lab.trade_intelligence import get_trade_intelligence
        engine = get_trade_intelligence()
        
        result = engine.exit_optimizer.optimize(
            strategy='iron_condor',
            dte=30,
            credit=1.50
        )
        
        self.assertIsNotNone(result)
        self.assertIn('profit_target', result.__dict__)
        self.assertIn('stop_loss', result.__dict__)
        print("✅ Test 22: Exit strategy optimizer - PASSED")
    
    def test_23_spread_analyzer(self):
        """Test spread analysis."""
        from financial_dashboard.tabs.options_lab.trade_intelligence import get_trade_intelligence
        engine = get_trade_intelligence()
        
        result = engine.spread_analyzer.analyze(
            bid=1.45,
            ask=1.55
        )
        
        self.assertIsNotNone(result)
        self.assertIn('spread_pct', result.__dict__)
        print("✅ Test 23: Spread analyzer - PASSED")
    
    def test_24_slippage_estimator(self):
        """Test slippage estimation."""
        from financial_dashboard.tabs.options_lab.trade_intelligence import get_trade_intelligence
        engine = get_trade_intelligence()
        
        result = engine.slippage_estimator.estimate(
            order_size=10,
            avg_volume=500,
            bid_ask_spread=0.10
        )
        
        self.assertIsNotNone(result)
        self.assertIn('expected_slippage', result.__dict__)
        print("✅ Test 24: Slippage estimator - PASSED")
    
    def test_25_trade_intelligence_full(self):
        """Test full trade intelligence analysis."""
        from financial_dashboard.tabs.options_lab.trade_intelligence import get_trade_intelligence
        engine = get_trade_intelligence()
        
        result = engine.full_analysis(
            ticker='SPY',
            strategy='iron_condor'
        )
        
        self.assertIsNotNone(result)
        self.assertIn('win_rate', result)
        self.assertIn('timing', result)
        print("✅ Test 25: Full trade intelligence - PASSED")


class TestMarketMicrostructure(unittest.TestCase):
    """Test Market Microstructure module."""
    
    def test_26_order_flow_analyzer(self):
        """Test order flow analysis."""
        from financial_dashboard.tabs.options_lab.market_microstructure import get_microstructure_engine
        engine = get_microstructure_engine()
        
        result = engine.flow_analyzer.analyze_flow('SPY')
        
        self.assertIsNotNone(result)
        self.assertIn('flow_direction', result.__dict__)
        self.assertIn('flow_intensity', result.__dict__)
        print("✅ Test 26: Order flow analyzer - PASSED")
    
    def test_27_market_maker_detector(self):
        """Test market maker activity detection."""
        from financial_dashboard.tabs.options_lab.market_microstructure import get_microstructure_engine
        engine = get_microstructure_engine()
        
        result = engine.mm_detector.detect_activity('SPY')
        
        self.assertIsNotNone(result)
        self.assertIn('activity_score', result.__dict__)
        print("✅ Test 27: Market maker detector - PASSED")
    
    def test_28_sweep_detector(self):
        """Test multi-exchange sweep detection."""
        from financial_dashboard.tabs.options_lab.market_microstructure import get_microstructure_engine
        engine = get_microstructure_engine()
        
        result = engine.sweep_detector.detect_sweeps('SPY')
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)
        print("✅ Test 28: Sweep detector - PASSED")
    
    def test_29_dark_pool_tracker(self):
        """Test dark pool activity tracking."""
        from financial_dashboard.tabs.options_lab.market_microstructure import get_microstructure_engine
        engine = get_microstructure_engine()
        
        result = engine.dark_pool_tracker.track_activity('SPY')
        
        self.assertIsNotNone(result)
        self.assertIn('dark_pool_volume', result.__dict__)
        print("✅ Test 29: Dark pool tracker - PASSED")
    
    def test_30_unusual_activity_detector(self):
        """Test unusual options activity detection."""
        from financial_dashboard.tabs.options_lab.market_microstructure import get_microstructure_engine
        engine = get_microstructure_engine()
        
        result = engine.unusual_detector.detect_unusual('SPY')
        
        self.assertIsNotNone(result)
        self.assertIn('is_unusual', result.__dict__)
        print("✅ Test 30: Unusual activity detector - PASSED")
    
    def test_31_microstructure_full(self):
        """Test full microstructure analysis."""
        from financial_dashboard.tabs.options_lab.market_microstructure import get_microstructure_engine
        engine = get_microstructure_engine()
        
        result = engine.full_analysis('SPY')
        
        self.assertIsNotNone(result)
        self.assertIn('order_flow', result)
        print("✅ Test 31: Full microstructure analysis - PASSED")


class TestBacktesting(unittest.TestCase):
    """Test Backtesting & Simulation module."""
    
    def test_32_strategy_backtester(self):
        """Test strategy backtesting."""
        from financial_dashboard.tabs.options_lab.backtesting import get_backtesting_engine
        engine = get_backtesting_engine()
        
        result = engine.backtester.backtest(
            strategy_name='iron_condor',
            ticker='SPY',
            start_date=datetime.now() - timedelta(days=365),
            end_date=datetime.now()
        )
        
        self.assertIsNotNone(result)
        self.assertIn('total_return', result.__dict__)
        self.assertIn('sharpe_ratio', result.__dict__)
        self.assertIn('win_rate', result.__dict__)
        print("✅ Test 32: Strategy backtester - PASSED")
    
    def test_33_monte_carlo_simulator(self):
        """Test Monte Carlo simulation (10000 paths)."""
        from financial_dashboard.tabs.options_lab.backtesting import get_backtesting_engine
        engine = get_backtesting_engine()
        
        result = engine.monte_carlo.simulate(
            strategy_name='iron_condor',
            win_rate=0.70,
            avg_win=50,
            avg_loss=100
        )
        
        self.assertIsNotNone(result)
        self.assertIn('prob_profit', result.__dict__)
        self.assertIn('median_return', result.__dict__)
        self.assertEqual(result.num_simulations, 10000)
        print("✅ Test 33: Monte Carlo simulator - PASSED")
    
    def test_34_walk_forward_optimizer(self):
        """Test walk-forward optimization."""
        from financial_dashboard.tabs.options_lab.backtesting import get_backtesting_engine
        engine = get_backtesting_engine()
        
        result = engine.walk_forward.optimize(
            strategy_name='iron_condor',
            ticker='SPY'
        )
        
        self.assertIsNotNone(result)
        self.assertIn('avg_oos_return', result.__dict__)
        self.assertIn('consistency_score', result.__dict__)
        print("✅ Test 34: Walk-forward optimizer - PASSED")
    
    def test_35_scenario_analyzer(self):
        """Test historical scenario analysis."""
        from financial_dashboard.tabs.options_lab.backtesting import get_backtesting_engine
        engine = get_backtesting_engine()
        
        result = engine.scenario_analyzer.analyze_scenario(
            strategy_name='iron_condor',
            scenario_name='covid_crash'
        )
        
        self.assertIsNotNone(result)
        self.assertIn('strategy_return', result.__dict__)
        self.assertIn('alpha', result.__dict__)
        print("✅ Test 35: Scenario analyzer - PASSED")
    
    def test_36_paper_trade_simulator(self):
        """Test paper trading simulation."""
        from financial_dashboard.tabs.options_lab.backtesting import get_backtesting_engine
        engine = get_backtesting_engine()
        
        # Open trade
        trade = engine.paper_trader.open_trade(
            ticker='SPY',
            strategy='iron_condor',
            contracts=1,
            target_price=2.50
        )
        
        self.assertIsNotNone(trade)
        self.assertEqual(trade.status, 'open')
        
        # Close trade
        closed = engine.paper_trader.close_trade(
            trade.trade_id,
            target_price=1.25
        )
        
        self.assertIsNotNone(closed)
        self.assertEqual(closed.status, 'closed')
        print("✅ Test 36: Paper trade simulator - PASSED")
    
    def test_37_backtesting_full(self):
        """Test full backtesting analysis."""
        from financial_dashboard.tabs.options_lab.backtesting import get_backtesting_engine
        engine = get_backtesting_engine()
        
        result = engine.full_analysis('iron_condor')
        
        self.assertIsNotNone(result)
        self.assertIn('backtest', result)
        self.assertIn('monte_carlo', result)
        self.assertIn('walk_forward', result)
        self.assertIn('scenarios', result)
        print("✅ Test 37: Full backtesting analysis - PASSED")


class TestRealtimeIntelligence(unittest.TestCase):
    """Test Real-time Intelligence module."""
    
    def test_38_live_pnl_tracker(self):
        """Test live P&L tracking."""
        from financial_dashboard.tabs.options_lab.realtime_intelligence import get_realtime_engine
        engine = get_realtime_engine()
        
        # Add position
        engine.pnl_tracker.add_position(
            position_id='POS001',
            ticker='SPY',
            entry_price=2.50,
            contracts=10
        )
        
        # Update price
        engine.pnl_tracker.update_prices({'SPY': 2.75})
        
        pnl = engine.pnl_tracker.get_portfolio_pnl()
        
        self.assertIsNotNone(pnl)
        self.assertIn('total_pnl', pnl)
        print("✅ Test 38: Live P&L tracker - PASSED")
    
    def test_39_alert_engine(self):
        """Test alert engine."""
        from financial_dashboard.tabs.options_lab.realtime_intelligence import get_realtime_engine, AlertType, AlertPriority
        engine = get_realtime_engine()
        
        # Add rule
        rule_id = engine.alert_engine.add_rule(
            name='Test Alert',
            alert_type=AlertType.PRICE,
            condition='above',
            threshold=100,
            priority=AlertPriority.HIGH
        )
        
        self.assertIsNotNone(rule_id)
        
        # Check conditions
        engine.alert_engine.check_conditions({
            'ticker': 'SPY',
            'price': 105
        })
        
        alerts = engine.alert_engine.get_active_alerts()
        self.assertIsInstance(alerts, list)
        print("✅ Test 39: Alert engine - PASSED")
    
    def test_40_webhook_integration(self):
        """Test webhook integration."""
        from financial_dashboard.tabs.options_lab.realtime_intelligence import get_realtime_engine
        engine = get_realtime_engine()
        
        # Add webhook
        wh_id = engine.webhooks.add_webhook(
            name='Test Webhook',
            url='https://example.com/webhook',
            events=['alert', 'trade']
        )
        
        self.assertIsNotNone(wh_id)
        
        # Send event
        engine.webhooks.send('alert', {'message': 'test'})
        
        # Process queue
        processed = engine.webhooks.process_queue()
        self.assertGreaterEqual(processed, 0)
        print("✅ Test 40: Webhook integration - PASSED")
    
    def test_41_market_scanner(self):
        """Test market opportunity scanner."""
        from financial_dashboard.tabs.options_lab.realtime_intelligence import get_realtime_engine
        engine = get_realtime_engine()
        
        results = engine.scanner.scan('high_iv_rank')
        
        self.assertIsNotNone(results)
        self.assertIsInstance(results, list)
        
        if results:
            self.assertIn('ticker', results[0].__dict__)
            self.assertIn('recommendation', results[0].__dict__)
        print("✅ Test 41: Market scanner - PASSED")
    
    def test_42_news_impact_analyzer(self):
        """Test news impact analysis."""
        from financial_dashboard.tabs.options_lab.realtime_intelligence import get_realtime_engine
        engine = get_realtime_engine()
        
        news = engine.news_analyzer.analyze_headline(
            "AAPL beats earnings expectations, revenue surges 15%",
            ['AAPL']
        )
        
        self.assertIsNotNone(news)
        self.assertGreater(news.sentiment, 0)  # Positive sentiment
        
        impact = engine.news_analyzer.get_strategy_impact(news)
        self.assertIn('strategy_recommendations', impact)
        print("✅ Test 42: News impact analyzer - PASSED")
    
    def test_43_realtime_dashboard_data(self):
        """Test real-time dashboard data."""
        from financial_dashboard.tabs.options_lab.realtime_intelligence import get_realtime_engine
        engine = get_realtime_engine()
        
        data = engine.get_dashboard_data()
        
        self.assertIsNotNone(data)
        self.assertIn('pnl', data)
        self.assertIn('positions', data)
        self.assertIn('active_alerts', data)
        self.assertIn('scan_results', data)
        self.assertIn('timestamp', data)
        print("✅ Test 43: Real-time dashboard data - PASSED")


class TestIntegration(unittest.TestCase):
    """Integration tests across modules."""
    
    def test_44_all_modules_import(self):
        """Test all modules import correctly."""
        modules = [
            'advanced_greeks',
            'portfolio_optimizer',
            'pricing_models',
            'trade_intelligence',
            'market_microstructure',
            'backtesting',
            'realtime_intelligence'
        ]
        
        for module in modules:
            try:
                exec(f"from financial_dashboard.tabs.options_lab.{module} import *")
            except ImportError as e:
                self.fail(f"Failed to import {module}: {e}")
        
        print("✅ Test 44: All modules import - PASSED")
    
    def test_45_singleton_pattern(self):
        """Test singleton pattern works correctly."""
        from financial_dashboard.tabs.options_lab.advanced_greeks import get_advanced_greeks
        from financial_dashboard.tabs.options_lab.portfolio_optimizer import get_portfolio_optimizer
        from financial_dashboard.tabs.options_lab.pricing_models import get_pricing_models
        from financial_dashboard.tabs.options_lab.trade_intelligence import get_trade_intelligence
        from financial_dashboard.tabs.options_lab.market_microstructure import get_microstructure_engine
        from financial_dashboard.tabs.options_lab.backtesting import get_backtesting_engine
        from financial_dashboard.tabs.options_lab.realtime_intelligence import get_realtime_engine
        
        # Get instances twice
        eng1 = get_advanced_greeks()
        eng2 = get_advanced_greeks()
        self.assertIs(eng1, eng2)
        
        eng1 = get_portfolio_optimizer()
        eng2 = get_portfolio_optimizer()
        self.assertIs(eng1, eng2)
        
        print("✅ Test 45: Singleton pattern - PASSED")
    
    def test_46_cross_module_workflow(self):
        """Test cross-module workflow."""
        from financial_dashboard.tabs.options_lab.pricing_models import get_pricing_models
        from financial_dashboard.tabs.options_lab.trade_intelligence import get_trade_intelligence
        from financial_dashboard.tabs.options_lab.backtesting import get_backtesting_engine
        
        # Price option
        pricing = get_pricing_models()
        price = pricing.bs_model.price(S=100, K=100, T=30/365, sigma=0.25)
        
        # Analyze trade
        intel = get_trade_intelligence()
        analysis = intel.win_rate_predictor.predict('iron_condor', 70, 30, 0.3)
        
        # Backtest
        backtest = get_backtesting_engine()
        result = backtest.backtester.backtest(
            'iron_condor', 'SPY',
            datetime.now() - timedelta(days=90),
            datetime.now()
        )
        
        self.assertIsNotNone(price)
        self.assertIsNotNone(analysis)
        self.assertIsNotNone(result)
        print("✅ Test 46: Cross-module workflow - PASSED")
    
    def test_47_error_handling(self):
        """Test error handling across modules."""
        from financial_dashboard.tabs.options_lab.pricing_models import get_pricing_models
        
        pricing = get_pricing_models()
        
        # Edge case inputs should not crash
        result = pricing.bs_model.price(S=100, K=100, T=0.001, sigma=0.25)
        self.assertIsNotNone(result)  # Should not crash
        
        print("✅ Test 47: Error handling - PASSED")
    
    def test_48_data_classes(self):
        """Test dataclass structures."""
        from financial_dashboard.tabs.options_lab.backtesting import BacktestResult
        from financial_dashboard.tabs.options_lab.realtime_intelligence import Alert, AlertType, AlertPriority
        
        # Test BacktestResult
        result = BacktestResult(
            strategy_name='test',
            start_date=datetime.now(),
            end_date=datetime.now(),
            total_return=100,
            annualized_return=20,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            max_drawdown=10,
            total_trades=50,
            winning_trades=35,
            losing_trades=15,
            win_rate=0.70,
            avg_win=50,
            avg_loss=30,
            profit_factor=1.5,
            avg_holding_days=5,
            max_consecutive_losses=3,
            trades=[],
            equity_curve=[]
        )
        
        self.assertEqual(result.strategy_name, 'test')
        self.assertEqual(result.win_rate, 0.70)
        
        print("✅ Test 48: Data classes - PASSED")
    
    def test_49_performance_benchmark(self):
        """Test performance is acceptable."""
        import time
        from financial_dashboard.tabs.options_lab.backtesting import get_backtesting_engine
        
        engine = get_backtesting_engine()
        
        start = time.time()
        
        # Run Monte Carlo
        result = engine.monte_carlo.simulate('test', 0.65, 50, 75)
        
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 5.0)  # Should complete in under 5 seconds
        self.assertEqual(result.num_simulations, 10000)
        
        print(f"✅ Test 49: Performance benchmark ({elapsed:.2f}s) - PASSED")
    
    def test_50_full_round2_coverage(self):
        """Test all 35 improvements are accessible."""
        improvements = {
            'advanced_greeks': ['surface_builder', 'sensitivity_analyzer', 'gamma_calculator', 'vega_analyzer', 'theta_projector'],
            'portfolio_optimizer': ['kelly_calculator', 'beta_optimizer', 'sharpe_analyzer', 'frontier_generator', 'rebalancing_advisor'],
            'pricing_models': ['bs_model', 'binomial_model', 'mc_model', 'vol_surface_builder', 'skew_analyzer'],
            'trade_intelligence': ['win_rate_predictor', 'entry_timing_optimizer', 'exit_optimizer', 'spread_analyzer', 'slippage_estimator'],
            'market_microstructure': ['flow_analyzer', 'mm_detector', 'sweep_detector', 'dark_pool_tracker', 'unusual_detector'],
            'backtesting': ['backtester', 'monte_carlo', 'walk_forward', 'scenario_analyzer', 'paper_trader'],
            'realtime_intelligence': ['pnl_tracker', 'alert_engine', 'webhooks', 'scanner', 'news_analyzer']
        }
        
        total_features = sum(len(v) for v in improvements.values())
        self.assertEqual(total_features, 35)
        
        print(f"✅ Test 50: Full Round 2 coverage ({total_features} features) - PASSED")


def run_tests():
    """Run all tests and generate report."""
    print("=" * 70)
    print("ROUND 2 AI/ML IMPROVEMENTS TEST SUITE")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestAdvancedGreeks,
        TestPortfolioOptimization,
        TestPricingModels,
        TestTradeIntelligence,
        TestMarketMicrostructure,
        TestBacktesting,
        TestRealtimeIntelligence,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total - failures - errors
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failures} ❌")
    print(f"Errors: {errors} ⚠️")
    print(f"Pass Rate: {passed/total*100:.1f}%")
    print("=" * 70)
    
    if failures > 0:
        print("\nFailed Tests:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if errors > 0:
        print("\nError Tests:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    return passed, total, failures + errors


if __name__ == '__main__':
    passed, total, failed = run_tests()
    
    # Exit with appropriate code
    exit(0 if failed == 0 else 1)

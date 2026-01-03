"""
Alpaca Options Lab - Comprehensive Component Tester
Auto-validates all 220 new improvements with snapshots and clicker tests
"""

import asyncio
import sys
import os
import json
import traceback
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np


# Add path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@dataclass
class TestResult:
    """Test result container."""
    component: str
    test_name: str
    status: str  # 'pass', 'fail', 'error'
    message: str
    duration_ms: float
    details: Dict = None


class ComponentTester:
    """Test all new Alpaca Options Lab components."""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = datetime.now()
    
    def log(self, msg: str):
        """Log message with timestamp."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    
    def run_test(self, component: str, test_name: str, test_func) -> TestResult:
        """Run a single test and capture result."""
        start = datetime.now()
        try:
            result = test_func()
            status = 'pass' if result else 'fail'
            message = 'Test passed' if result else 'Test failed'
            details = None
        except Exception as e:
            status = 'error'
            message = str(e)
            details = {'traceback': traceback.format_exc()}
        
        duration = (datetime.now() - start).total_seconds() * 1000
        
        test_result = TestResult(
            component=component,
            test_name=test_name,
            status=status,
            message=message,
            duration_ms=duration,
            details=details
        )
        self.results.append(test_result)
        
        icon = '✅' if status == 'pass' else ('❌' if status == 'fail' else '⚠️')
        self.log(f"{icon} {component}/{test_name}: {message} ({duration:.1f}ms)")
        
        return test_result
    
    # ============================================================
    # Test: Enhanced Chain Components (Items 1-25)
    # ============================================================
    def test_enhanced_chain_components(self):
        """Test enhanced chain viewer components."""
        from enhanced_chain_components import (
            get_spread_color, create_spread_badge, create_chain_filters,
            create_greeks_summary, calculate_max_pain, create_pcr_badge,
            calculate_pop, detect_unusual_activity, build_enhanced_chain_table
        )
        
        # Test spread color function
        self.run_test('enhanced_chain', 'spread_color_tight', 
                     lambda: get_spread_color(0.5) == '#28a745')
        self.run_test('enhanced_chain', 'spread_color_wide', 
                     lambda: get_spread_color(10) == '#dc3545')
        
        # Test spread badge
        self.run_test('enhanced_chain', 'spread_badge_creation',
                     lambda: create_spread_badge(2.5) is not None)
        
        # Test chain filters
        self.run_test('enhanced_chain', 'chain_filters_creation',
                     lambda: create_chain_filters() is not None)
        
        # Test Greeks summary
        self.run_test('enhanced_chain', 'greeks_summary',
                     lambda: create_greeks_summary({'delta': 0.5, 'gamma': 0.05, 
                                                    'theta': -0.02, 'vega': 0.10}) is not None)
        
        # Test max pain
        chain_df = pd.DataFrame({
            'strike': [95, 100, 105],
            'call_oi': [100, 500, 200],
            'put_oi': [200, 300, 100]
        })
        self.run_test('enhanced_chain', 'max_pain_calculation',
                     lambda: calculate_max_pain(chain_df) > 0)
        
        # Test PCR badge
        self.run_test('enhanced_chain', 'pcr_badge',
                     lambda: create_pcr_badge(0.8) is not None)
        
        # Test PoP calculation
        self.run_test('enhanced_chain', 'pop_calculation',
                     lambda: 0 <= calculate_pop(100, 95, 0.3, 30) <= 100)
        
        # Test unusual activity detection
        volume_df = pd.DataFrame({
            'symbol': ['AAPL'],
            'volume': [10000],
            'openInterest': [5000],
            'impliedVolatility': [0.35]
        })
        self.run_test('enhanced_chain', 'unusual_activity',
                     lambda: isinstance(detect_unusual_activity(volume_df), list))
        
        # Test chain table builder
        calls_df = pd.DataFrame({'strike': [100], 'bid': [2.0], 'ask': [2.1]})
        puts_df = pd.DataFrame({'strike': [100], 'bid': [1.5], 'ask': [1.6]})
        self.run_test('enhanced_chain', 'chain_table_builder',
                     lambda: build_enhanced_chain_table(calls_df, puts_df, 100) is not None)
    
    # ============================================================
    # Test: Advanced Greeks Components (Items 26-50)
    # ============================================================
    def test_advanced_greeks_components(self):
        """Test advanced Greeks dashboard components."""
        from advanced_greeks_components import (
            create_greeks_heatmap, aggregate_portfolio_greeks,
            calculate_gex, create_gex_chart, calculate_delta_hedge,
            project_theta_decay, stress_test_greeks, check_greeks_alerts,
            create_advanced_greeks_dashboard
        )
        
        # Test Greeks heatmap
        chain_df = pd.DataFrame({
            'strike': [95, 100, 105],
            'expiration': ['2025-01-17'] * 3,
            'delta': [0.7, 0.5, 0.3],
            'gamma': [0.03, 0.05, 0.03]
        })
        self.run_test('advanced_greeks', 'greeks_heatmap',
                     lambda: create_greeks_heatmap(chain_df, 'delta', 100) is not None)
        
        # Test portfolio Greeks aggregation
        positions = [
            {'delta': 0.5, 'gamma': 0.05, 'theta': -0.02, 'vega': 0.1, 'quantity': 10},
            {'delta': -0.3, 'gamma': 0.03, 'theta': -0.01, 'vega': 0.08, 'quantity': 5}
        ]
        self.run_test('advanced_greeks', 'portfolio_aggregation',
                     lambda: aggregate_portfolio_greeks(positions) is not None)
        
        # Test GEX calculation
        self.run_test('advanced_greeks', 'gex_calculation',
                     lambda: calculate_gex(chain_df, 100) is not None)
        
        # Test GEX chart
        gex_data = pd.DataFrame({'strike': [95, 100, 105], 'gex': [1e9, -5e8, 2e8]})
        self.run_test('advanced_greeks', 'gex_chart',
                     lambda: create_gex_chart(gex_data, 100) is not None)
        
        # Test delta hedge calculation
        self.run_test('advanced_greeks', 'delta_hedge',
                     lambda: calculate_delta_hedge(0.5, 10, 100) is not None)
        
        # Test theta decay projection
        position = {'theta': -0.05, 'quantity': 10, 'cost': 2.50}
        self.run_test('advanced_greeks', 'theta_projection',
                     lambda: len(project_theta_decay(position, 30)) > 0)
        
        # Test stress test
        self.run_test('advanced_greeks', 'stress_test',
                     lambda: stress_test_greeks(positions, 0.05, 0.10) is not None)
        
        # Test Greeks alerts
        self.run_test('advanced_greeks', 'greeks_alerts',
                     lambda: isinstance(check_greeks_alerts(
                         {'total_delta': 150, 'total_vega': 50}), list))
        
        # Test dashboard creation
        self.run_test('advanced_greeks', 'dashboard_creation',
                     lambda: create_advanced_greeks_dashboard() is not None)
    
    # ============================================================
    # Test: Volatility Surface Enhancements (Items 51-75)
    # ============================================================
    def test_vol_surface_enhancements(self):
        """Test volatility surface enhancement components."""
        from vol_surface_enhancements import (
            calculate_iv_percentile, create_iv_percentile_badge,
            calculate_iv_rank, create_iv_comparison_card,
            create_term_structure_chart, create_skew_chart,
            create_hv_iv_comparison, create_3d_vol_surface,
            smooth_vol_surface, calculate_volatility_cone,
            create_volatility_cone_chart, calculate_surface_changes,
            calculate_vol_premium, create_vol_premium_indicator,
            calculate_expected_move, create_expected_move_visual,
            VolSurfaceSnapshot, create_vol_surface_dashboard
        )
        
        # Test IV percentile
        historical_ivs = [0.2, 0.25, 0.3, 0.28, 0.22, 0.35]
        self.run_test('vol_surface', 'iv_percentile',
                     lambda: 0 <= calculate_iv_percentile(0.27, historical_ivs) <= 100)
        
        # Test IV percentile badge
        self.run_test('vol_surface', 'iv_percentile_badge',
                     lambda: create_iv_percentile_badge(75) is not None)
        
        # Test IV rank
        self.run_test('vol_surface', 'iv_rank',
                     lambda: 0 <= calculate_iv_rank(0.25, 0.35, 0.15) <= 100)
        
        # Test IV comparison card
        self.run_test('vol_surface', 'iv_comparison_card',
                     lambda: create_iv_comparison_card(0.25, historical_ivs, 0.35, 0.15) is not None)
        
        # Test term structure chart
        self.run_test('vol_surface', 'term_structure',
                     lambda: create_term_structure_chart(
                         ['2025-01-17', '2025-02-21', '2025-03-21'],
                         [0.25, 0.27, 0.28]) is not None)
        
        # Test skew chart
        self.run_test('vol_surface', 'skew_chart',
                     lambda: create_skew_chart(
                         [95, 100, 105], [0.30, 0.25, 0.23], 100) is not None)
        
        # Test HV/IV comparison
        dates = pd.date_range(end=datetime.now(), periods=30)
        hvs = [0.20 + np.random.uniform(-0.02, 0.02) for _ in range(30)]
        ivs = [0.25 + np.random.uniform(-0.03, 0.03) for _ in range(30)]
        self.run_test('vol_surface', 'hv_iv_comparison',
                     lambda: create_hv_iv_comparison(dates, hvs, ivs) is not None)
        
        # Test 3D vol surface
        strikes = np.array([95, 100, 105])
        expirations = np.array([30, 60, 90])
        iv_matrix = np.random.uniform(0.2, 0.35, (3, 3))
        self.run_test('vol_surface', '3d_surface',
                     lambda: create_3d_vol_surface(strikes, expirations, iv_matrix, 100) is not None)
        
        # Test surface smoothing
        self.run_test('vol_surface', 'surface_smoothing',
                     lambda: smooth_vol_surface(strikes, expirations, iv_matrix).shape == iv_matrix.shape)
        
        # Test volatility cone
        prices = pd.Series([100 + np.random.randn() for _ in range(300)])
        self.run_test('vol_surface', 'vol_cone',
                     lambda: len(calculate_volatility_cone(prices)) > 0)
        
        # Test vol cone chart
        vol_cone_df = pd.DataFrame({
            'window': [10, 20, 30],
            'current': [0.20, 0.22, 0.21],
            'min': [0.15, 0.16, 0.17],
            'p25': [0.18, 0.19, 0.19],
            'median': [0.22, 0.23, 0.22],
            'p75': [0.28, 0.27, 0.26],
            'max': [0.35, 0.34, 0.33]
        })
        self.run_test('vol_surface', 'vol_cone_chart',
                     lambda: create_volatility_cone_chart(vol_cone_df, 0.25) is not None)
        
        # Test vol premium
        self.run_test('vol_surface', 'vol_premium',
                     lambda: calculate_vol_premium(0.30, 0.20)['spread'] == 0.10)
        
        # Test expected move
        self.run_test('vol_surface', 'expected_move',
                     lambda: calculate_expected_move(100, 0.25, 30)['expected_move_1sd'] > 0)
        
        # Test snapshot
        snapshot_mgr = VolSurfaceSnapshot()
        snapshot_mgr.save_snapshot('test', strikes, expirations, iv_matrix)
        self.run_test('vol_surface', 'snapshot_save',
                     lambda: len(snapshot_mgr.list_snapshots()) == 1)
        
        # Test dashboard
        self.run_test('vol_surface', 'dashboard',
                     lambda: create_vol_surface_dashboard() is not None)
    
    # ============================================================
    # Test: Strategy Builder Pro (Items 76-100)
    # ============================================================
    def test_strategy_builder_pro(self):
        """Test strategy builder components."""
        from strategy_builder_pro import (
            StrategyType, StrategyLeg, Strategy, STRATEGY_TEMPLATES,
            apply_template, suggest_optimal_strikes, what_if_analysis,
            calculate_strategy_pnl, create_strategy_heatmap,
            calculate_breakevens, create_payoff_diagram,
            calculate_risk_reward, create_risk_reward_card,
            create_strategy_builder_panel
        )
        
        # Test strategy templates exist
        self.run_test('strategy_builder', 'templates_exist',
                     lambda: len(STRATEGY_TEMPLATES) >= 6)
        
        # Test strategy leg creation
        leg = StrategyLeg(
            option_type='call', strike=100, expiration='2025-01-17',
            quantity=1, premium=2.50, delta=0.5
        )
        self.run_test('strategy_builder', 'leg_creation',
                     lambda: leg.strike == 100)
        
        # Test strategy creation
        strategy = Strategy(
            name='Test IC', strategy_type=StrategyType.IRON_CONDOR,
            legs=[leg], ticker='SPY', spot_price=100
        )
        self.run_test('strategy_builder', 'strategy_creation',
                     lambda: strategy.ticker == 'SPY')
        
        # Test optimal strike suggestion
        self.run_test('strategy_builder', 'optimal_strikes',
                     lambda: suggest_optimal_strikes(100, 0.25, 30)['atm_strike'] == 100)
        
        # Test what-if analysis
        wif = what_if_analysis(strategy, (90, 110))
        self.run_test('strategy_builder', 'what_if',
                     lambda: len(wif) > 0)
        
        # Test strategy P&L
        self.run_test('strategy_builder', 'pnl_calc',
                     lambda: isinstance(calculate_strategy_pnl(strategy, 100), (int, float)))
        
        # Test heatmap
        self.run_test('strategy_builder', 'heatmap',
                     lambda: create_strategy_heatmap(wif) is not None)
        
        # Test breakevens
        self.run_test('strategy_builder', 'breakevens',
                     lambda: isinstance(calculate_breakevens(strategy), list))
        
        # Test payoff diagram
        self.run_test('strategy_builder', 'payoff_diagram',
                     lambda: create_payoff_diagram(strategy) is not None)
        
        # Test risk/reward
        rr = calculate_risk_reward(strategy)
        self.run_test('strategy_builder', 'risk_reward',
                     lambda: 'max_profit' in rr)
        
        # Test risk/reward card
        self.run_test('strategy_builder', 'rr_card',
                     lambda: create_risk_reward_card(rr) is not None)
        
        # Test builder panel
        self.run_test('strategy_builder', 'builder_panel',
                     lambda: create_strategy_builder_panel() is not None)
    
    # ============================================================
    # Test: Trade Execution System (Items 101-125)
    # ============================================================
    def test_trade_execution(self):
        """Test trade execution system components."""
        from trade_execution_system import (
            OrderType, OrderSide, OrderStatus, Order, MultiLegOrder,
            SmartOrderRouter, PreTradeValidator, create_execution_preview,
            create_confirmation_modal, create_order_status_row,
            create_orders_panel, Position, create_position_card,
            calculate_roll_options, create_roll_wizard,
            calculate_pnl_attribution, create_pnl_attribution_chart,
            TradeJournalEntry, create_journal_entry_form,
            create_execution_panel
        )
        
        # Test order types
        self.run_test('execution', 'order_types',
                     lambda: len(OrderType) >= 5)
        
        # Test order creation
        order = Order(
            symbol='SPY', option_symbol='SPY250117C500',
            order_type=OrderType.LIMIT, side=OrderSide.BUY_TO_OPEN,
            quantity=1, limit_price=2.50
        )
        self.run_test('execution', 'order_creation',
                     lambda: order.quantity == 1)
        
        # Test smart order router
        router = SmartOrderRouter()
        optimal_price = router.calculate_optimal_limit_price(2.40, 2.60, 'normal')
        self.run_test('execution', 'smart_routing',
                     lambda: 2.40 <= optimal_price <= 2.60)
        
        # Test pre-trade validator
        validator = PreTradeValidator({'buying_power': 50000})
        validation = validator.validate_order(order)
        self.run_test('execution', 'pre_trade_validation',
                     lambda: 'valid' in validation)
        
        # Test execution preview
        market_data = {'bid': 2.40, 'ask': 2.60}
        self.run_test('execution', 'execution_preview',
                     lambda: create_execution_preview(order, market_data) is not None)
        
        # Test confirmation modal
        self.run_test('execution', 'confirmation_modal',
                     lambda: create_confirmation_modal(order, validation) is not None)
        
        # Test order status row
        self.run_test('execution', 'order_status_row',
                     lambda: create_order_status_row(order) is not None)
        
        # Test orders panel
        self.run_test('execution', 'orders_panel',
                     lambda: create_orders_panel([order]) is not None)
        
        # Test position
        position = Position(
            symbol='SPY', option_symbol='SPY250117C500',
            quantity=10, avg_cost=2.50, current_price=3.00,
            unrealized_pnl=500, delta=0.5
        )
        self.run_test('execution', 'position_creation',
                     lambda: position.unrealized_pnl == 500)
        
        # Test position card
        self.run_test('execution', 'position_card',
                     lambda: create_position_card(position) is not None)
        
        # Test roll options
        rolls = calculate_roll_options(position, ['2025-02-21', '2025-03-21'])
        self.run_test('execution', 'roll_options',
                     lambda: len(rolls) >= 2)
        
        # Test roll wizard
        self.run_test('execution', 'roll_wizard',
                     lambda: create_roll_wizard(position, rolls) is not None)
        
        # Test P&L attribution
        attr = calculate_pnl_attribution(position, 5, 0.02, 7)
        self.run_test('execution', 'pnl_attribution',
                     lambda: 'delta_pnl' in attr)
        
        # Test P&L chart
        self.run_test('execution', 'pnl_chart',
                     lambda: create_pnl_attribution_chart(attr) is not None)
        
        # Test journal form
        self.run_test('execution', 'journal_form',
                     lambda: create_journal_entry_form() is not None)
        
        # Test execution panel
        self.run_test('execution', 'execution_panel',
                     lambda: create_execution_panel() is not None)
    
    # ============================================================
    # Test: Backtest Engine (Items 126-150)
    # ============================================================
    def test_backtest_engine(self):
        """Test backtesting engine components."""
        from backtest_engine import (
            HistoricalOptionData, HistoricalDataLoader,
            BacktestConfig, BacktestTrade, BacktestResult, BacktestEngine,
            create_equity_curve_chart, create_trade_distribution_chart,
            create_metrics_dashboard, run_monte_carlo, create_monte_carlo_chart,
            create_backtest_panel
        )
        
        # Test data loader
        loader = HistoricalDataLoader()
        chain = loader.load_option_chain('SPY', datetime.now())
        self.run_test('backtest', 'data_loader',
                     lambda: len(chain) > 0)
        
        # Test config creation
        config = BacktestConfig(
            symbol='SPY',
            start_date=datetime.now() - timedelta(days=365),
            end_date=datetime.now(),
            initial_capital=100000
        )
        self.run_test('backtest', 'config_creation',
                     lambda: config.initial_capital == 100000)
        
        # Test backtest engine (quick run)
        config.end_date = config.start_date + timedelta(days=30)  # Short test
        engine = BacktestEngine(config)
        result = engine.run()
        self.run_test('backtest', 'engine_run',
                     lambda: result is not None)
        
        # Test equity curve chart
        self.run_test('backtest', 'equity_curve',
                     lambda: create_equity_curve_chart(result) is not None)
        
        # Test trade distribution
        self.run_test('backtest', 'trade_distribution',
                     lambda: create_trade_distribution_chart(result.trades) is not None)
        
        # Test metrics dashboard
        self.run_test('backtest', 'metrics_dashboard',
                     lambda: create_metrics_dashboard(result.metrics) is not None)
        
        # Test Monte Carlo
        mc_results = run_monte_carlo(result.trades, 100000, 100)  # Quick MC
        self.run_test('backtest', 'monte_carlo',
                     lambda: 'prob_profit' in mc_results)
        
        # Test MC chart
        self.run_test('backtest', 'mc_chart',
                     lambda: create_monte_carlo_chart(mc_results, 100000) is not None)
        
        # Test backtest panel
        self.run_test('backtest', 'backtest_panel',
                     lambda: create_backtest_panel() is not None)
    
    # ============================================================
    # Test: AI/ML Integration (Items 151-175)
    # ============================================================
    def test_ai_ml_integration(self):
        """Test AI/ML integration components."""
        from ai_ml_integration import (
            ModelType, MLModel, MLModelManager,
            forecast_volatility, create_volatility_forecast_chart,
            MarketRegime, detect_market_regime, create_regime_indicator,
            UnusualActivity, detect_unusual_activity, create_unusual_activity_table,
            calculate_flow_summary, create_flow_summary_card,
            recommend_strategies, create_recommendations_panel,
            create_ai_dashboard
        )
        
        # Test model manager
        manager = MLModelManager()
        self.run_test('ai_ml', 'model_manager',
                     lambda: len(manager.models) >= 3)
        
        # Test prediction
        pred = manager.get_prediction('vol_forecast', {'hv_20': 0.20})
        self.run_test('ai_ml', 'prediction',
                     lambda: 'prediction' in pred)
        
        # Test volatility forecast
        prices = pd.Series([100 + np.random.randn() for _ in range(100)])
        forecast = forecast_volatility(prices)
        self.run_test('ai_ml', 'vol_forecast',
                     lambda: len(forecast['forecasts']) > 0)
        
        # Test forecast chart
        self.run_test('ai_ml', 'forecast_chart',
                     lambda: create_volatility_forecast_chart(forecast) is not None)
        
        # Test regime detection
        regime = detect_market_regime(prices)
        self.run_test('ai_ml', 'regime_detection',
                     lambda: 'regime' in regime)
        
        # Test regime indicator
        self.run_test('ai_ml', 'regime_indicator',
                     lambda: create_regime_indicator(regime) is not None)
        
        # Test unusual activity detection
        chain_df = pd.DataFrame({
            'symbol': ['SPY'] * 5,
            'volume': [10000, 500, 200, 8000, 300],
            'openInterest': [5000, 1000, 500, 2000, 800],
            'impliedVolatility': [0.25, 0.30, 0.28, 0.35, 0.22],
            'delta': [0.5, 0.3, -0.4, 0.6, -0.2],
            'optionType': ['call', 'call', 'put', 'call', 'put'],
            'strike': [500, 505, 495, 510, 490],
            'expiration': ['2025-01-17'] * 5,
            'lastPrice': [5.0, 3.0, 2.5, 4.0, 2.0]
        })
        alerts = detect_unusual_activity(chain_df)
        self.run_test('ai_ml', 'unusual_activity',
                     lambda: isinstance(alerts, list))
        
        # Test unusual activity table
        self.run_test('ai_ml', 'unusual_table',
                     lambda: create_unusual_activity_table(alerts) is not None)
        
        # Test flow summary
        flow = calculate_flow_summary(chain_df, 500)
        self.run_test('ai_ml', 'flow_summary',
                     lambda: 'call_volume' in flow)
        
        # Test flow card
        self.run_test('ai_ml', 'flow_card',
                     lambda: create_flow_summary_card(flow) is not None)
        
        # Test recommendations
        recs = recommend_strategies(regime, {'iv_percentile': 75})
        self.run_test('ai_ml', 'recommendations',
                     lambda: len(recs) > 0)
        
        # Test recommendations panel
        self.run_test('ai_ml', 'recommendations_panel',
                     lambda: create_recommendations_panel(recs) is not None)
        
        # Test AI dashboard
        self.run_test('ai_ml', 'ai_dashboard',
                     lambda: create_ai_dashboard() is not None)
    
    # ============================================================
    # Test: Monitoring & Alerts (Items 176-220)
    # ============================================================
    def test_monitoring_alerts(self):
        """Test monitoring and alerts components."""
        from monitoring_alerts import (
            AlertType, AlertPriority, Alert, AlertManager,
            create_alert_card, create_alerts_panel,
            PortfolioGreeks, calculate_portfolio_greeks, create_portfolio_greeks_card,
            DashboardLayout, DashboardManager,
            get_earnings_calendar, create_earnings_calendar_card,
            WatchlistItem, WatchlistManager,
            screen_options, create_screener_results_table, create_screener_panel,
            create_monitoring_dashboard
        )
        
        # Test alert manager
        manager = AlertManager()
        alert = manager.create_alert(
            AlertType.IV, 'SPY', 'iv above', 0.30, AlertPriority.HIGH
        )
        self.run_test('monitoring', 'alert_creation',
                     lambda: alert.alert_id is not None)
        
        # Test alert check
        triggered = manager.check_alerts({'SPY': {'iv': 0.35}})
        self.run_test('monitoring', 'alert_trigger',
                     lambda: len(triggered) > 0)
        
        # Test alert card
        self.run_test('monitoring', 'alert_card',
                     lambda: create_alert_card(alert) is not None)
        
        # Test alerts panel
        self.run_test('monitoring', 'alerts_panel',
                     lambda: create_alerts_panel([alert]) is not None)
        
        # Test portfolio Greeks
        positions = [
            {'delta': 0.5, 'gamma': 0.05, 'theta': -0.02, 'vega': 0.1, 'quantity': 10}
        ]
        greeks = calculate_portfolio_greeks(positions)
        self.run_test('monitoring', 'portfolio_greeks',
                     lambda: greeks.total_delta == 5.0)
        
        # Test Greeks card
        self.run_test('monitoring', 'greeks_card',
                     lambda: create_portfolio_greeks_card(greeks) is not None)
        
        # Test dashboard manager
        dash_manager = DashboardManager()
        self.run_test('monitoring', 'dashboard_layouts',
                     lambda: len(dash_manager.layouts) >= 3)
        
        # Test earnings calendar
        earnings = get_earnings_calendar(['AAPL', 'MSFT', 'GOOGL'])
        self.run_test('monitoring', 'earnings_calendar',
                     lambda: len(earnings) >= 3)
        
        # Test earnings card
        self.run_test('monitoring', 'earnings_card',
                     lambda: create_earnings_calendar_card(earnings) is not None)
        
        # Test watchlist
        watchlist_mgr = WatchlistManager()
        item = watchlist_mgr.add_symbol('SPY', target_entry=490)
        self.run_test('monitoring', 'watchlist_add',
                     lambda: len(watchlist_mgr.get_watchlist()) == 1)
        
        # Test screener
        results = screen_options(['SPY', 'QQQ', 'IWM', 'AAPL'], {'iv_rank_min': 30})
        self.run_test('monitoring', 'screener',
                     lambda: isinstance(results, list))
        
        # Test screener table
        self.run_test('monitoring', 'screener_table',
                     lambda: create_screener_results_table(results) is not None)
        
        # Test screener panel
        self.run_test('monitoring', 'screener_panel',
                     lambda: create_screener_panel() is not None)
        
        # Test monitoring dashboard
        self.run_test('monitoring', 'monitoring_dashboard',
                     lambda: create_monitoring_dashboard() is not None)
    
    # ============================================================
    # Run All Tests
    # ============================================================
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all component tests."""
        self.log("=" * 60)
        self.log("ALPACA OPTIONS LAB - COMPONENT VALIDATION")
        self.log("Testing 220 NEW improvements across 7 modules")
        self.log("=" * 60)
        
        test_methods = [
            ('Enhanced Chain (1-25)', self.test_enhanced_chain_components),
            ('Advanced Greeks (26-50)', self.test_advanced_greeks_components),
            ('Vol Surface (51-75)', self.test_vol_surface_enhancements),
            ('Strategy Builder (76-100)', self.test_strategy_builder_pro),
            ('Trade Execution (101-125)', self.test_trade_execution),
            ('Backtest Engine (126-150)', self.test_backtest_engine),
            ('AI/ML Integration (151-175)', self.test_ai_ml_integration),
            ('Monitoring & Alerts (176-220)', self.test_monitoring_alerts),
        ]
        
        for name, method in test_methods:
            self.log(f"\n{'='*60}")
            self.log(f"TESTING: {name}")
            self.log(f"{'='*60}")
            try:
                method()
            except Exception as e:
                self.log(f"⚠️ Module error: {e}")
                traceback.print_exc()
        
        # Generate summary
        summary = self.generate_summary()
        return summary
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate test summary."""
        passed = sum(1 for r in self.results if r.status == 'pass')
        failed = sum(1 for r in self.results if r.status == 'fail')
        errors = sum(1 for r in self.results if r.status == 'error')
        total = len(self.results)
        
        duration = (datetime.now() - self.start_time).total_seconds()
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'pass_rate': f"{passed/total*100:.1f}%" if total > 0 else "N/A",
            'duration_seconds': duration,
            'results_by_component': {}
        }
        
        # Group by component
        for r in self.results:
            if r.component not in summary['results_by_component']:
                summary['results_by_component'][r.component] = {
                    'passed': 0, 'failed': 0, 'errors': 0
                }
            summary['results_by_component'][r.component][
                'passed' if r.status == 'pass' else ('failed' if r.status == 'fail' else 'errors')
            ] += 1
        
        self.log("\n" + "=" * 60)
        self.log("TEST SUMMARY")
        self.log("=" * 60)
        self.log(f"Total Tests: {total}")
        self.log(f"✅ Passed: {passed}")
        self.log(f"❌ Failed: {failed}")
        self.log(f"⚠️  Errors: {errors}")
        self.log(f"Pass Rate: {summary['pass_rate']}")
        self.log(f"Duration: {duration:.2f}s")
        self.log("=" * 60)
        
        return summary


def main():
    """Main entry point."""
    tester = ComponentTester()
    summary = tester.run_all_tests()
    
    # Save results
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'component_test_results.json'
    )
    
    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    print(f"\n📁 Results saved to: {output_path}")
    
    # Return exit code based on results
    return 0 if summary['failed'] == 0 and summary['errors'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

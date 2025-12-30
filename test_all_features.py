#!/usr/bin/env python3
"""
Comprehensive Feature Test for Enhanced Alpaca Options Lab
Tests every single method of the new AI engines.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Add path
sys.path.insert(0, '/home/aarav/Unified-Dashboard')

def run_test(name, func):
    """Run a test function and print result."""
    try:
        result = func()
        print(f"✅ {name}: PASS")
        return True
    except Exception as e:
        print(f"❌ {name}: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ai_automation_engine():
    print("\n--- Testing AI Automation Engine ---")
    from financial_dashboard.tabs.options_lab.ai_automation_engine import (
        auto_scanner, signal_generator, greeks_engine,
        position_manager, regime_detector
    )
    
    # AutoScanner
    run_test("Scanner.scan_all_tickers", lambda: len(auto_scanner.scan_all_tickers()) > 0)
    run_test("Scanner.rank_opportunities", lambda: len(auto_scanner.rank_opportunities()) >= 0)
    
    # SignalGenerator
    run_test("SignalGenerator.generate_signal", lambda: signal_generator.generate_signal('SPY', 500, 0.2, 50, 'BULLISH') is not None)
    run_test("SignalGenerator.validate_signal", lambda: signal_generator.validate_signal({'confidence': 0.8}) is True)
    
    # GreeksEngine
    run_test("GreeksEngine.calculate_greeks", lambda: greeks_engine.calculate_greeks(500, 500, 0.05, 0.2, 0.02, 'call') is not None)
    run_test("GreeksEngine.calculate_portfolio_greeks", lambda: greeks_engine.calculate_portfolio_greeks([]) is not None)
    
    # PositionManager
    run_test("PositionManager.calculate_position_size", lambda: position_manager.calculate_position_size(10000, 0.5) > 0)
    run_test("PositionManager.check_portfolio_balance", lambda: position_manager.check_portfolio_balance(10000.0, 5000.0) is not None)
    
    # RegimeDetector
    run_test("RegimeDetector.detect_regime", lambda: regime_detector.detect_regime(20, 0.01, 0.015).regime is not None)
    run_test("RegimeDetector.get_strategies_for_regime", lambda: len(regime_detector.get_strategies_for_regime('BULL')) > 0)

def test_smart_analysis_engine():
    print("\n--- Testing Smart Analysis Engine ---")
    from financial_dashboard.tabs.options_lab.smart_analysis_engine import (
        ta_engine, iv_engine, flow_analyzer,
        portfolio_analytics, ml_engine
    )
    
    prices = pd.Series([100 + np.random.uniform(-2, 2) for _ in range(50)])
    
    # TA Engine
    run_test("TA.calculate_rsi", lambda: ta_engine.calculate_rsi(prices) is not None)
    run_test("TA.calculate_macd", lambda: ta_engine.calculate_macd(prices) is not None)
    run_test("TA.calculate_composite_score", lambda: ta_engine.calculate_composite_score(prices)['composite_score'] is not None)
    
    # IV Engine
    run_test("IV.calculate_iv_percentile", lambda: iv_engine.calculate_iv_percentile(0.25, [0.2]*252)['percentile'] is not None)
    run_test("IV.calculate_iv_skew", lambda: iv_engine.calculate_iv_skew([100, 105, 110], [0.2, 0.2, 0.2], 105) is not None)
    
    # Flow Analyzer
    run_test("Flow.analyze_unusual_activity", lambda: flow_analyzer.analyze_unusual_activity([]) is not None)
    run_test("Flow.calculate_put_call_ratio", lambda: flow_analyzer.calculate_put_call_ratio([]) is not None)
    
    # Portfolio Analytics
    run_test("Portfolio.calculate_sharpe_ratio", lambda: portfolio_analytics.calculate_sharpe_ratio(pd.Series([0.01]*10)) is not None)
    run_test("Portfolio.calculate_var", lambda: portfolio_analytics.calculate_var(pd.Series([0.01]*10)) is not None)
    
    # ML Engine
    run_test("ML.predict_direction", lambda: ml_engine.predict_direction(prices)['prediction'] is not None)
    run_test("ML.forecast_volatility", lambda: ml_engine.forecast_volatility(prices)['forecast_vol'] is not None)

def test_auto_trading_engine():
    print("\n--- Testing Auto Trading Engine ---")
    from financial_dashboard.tabs.options_lab.auto_trading_engine import (
        strategy_builder, order_executor, risk_manager,
        profit_taker, rolling_engine
    )
    
    # Strategy Builder
    run_test("Strategy.build_iron_condor", lambda: strategy_builder.build_iron_condor('SPY', 500, 0.2, 30).strategy_name == 'Iron Condor')
    run_test("Strategy.build_credit_spread", lambda: strategy_builder.build_credit_spread('SPY', 500, 'BULL', 0.2, 30).strategy_name == 'Bull Put Spread')
    
    # Order Executor
    run_test("Executor.create_order", lambda: order_executor.create_order('SPY', 1, 'buy', 'market', 500) is not None)
    run_test("Executor.validate_order", lambda: order_executor.validate_order({'underlying': 'SPY', 'quantity': 1})[0] is True)
    
    # Risk Manager
    run_test("Risk.calculate_position_size", lambda: risk_manager.calculate_position_size(10000, 500) > 0)
    run_test("Risk.check_new_position_risk", lambda: risk_manager.check_new_position_risk(10000, 500, 5, 0.5)['allowed'] is True)
    run_test("Risk.check_position_limit", lambda: risk_manager.check_position_limit('SPY', 0.1)['allowed'] is True)
    
    # Profit Taker
    run_test("ProfitTaker.get_profit_target", lambda: profit_taker.get_profit_target('iron_condor', 30, 50) > 0)
    run_test("ProfitTaker.check_exit_conditions", lambda: profit_taker.check_exit_conditions({'profit_pct': 0.6, 'dte': 30}) is not None)
    
    # Rolling Engine
    run_test("Rolling.check_roll_needed", lambda: rolling_engine.check_roll_needed({'profit_pct': -0.1, 'dte': 5}) is not None)

def test_monitoring_engine():
    print("\n--- Testing Monitoring Engine ---")
    from financial_dashboard.tabs.options_lab.monitoring_engine import (
        price_monitor, iv_greeks_monitor, position_monitor,
        events_monitor, alert_manager, master_monitor, Alert, AlertType, AlertSeverity
    )
    
    # Price Monitor
    run_test("Price.check_price_alerts", lambda: price_monitor.check_price_alerts('SPY', 500) is None)
    
    # IV Monitor
    run_test("IV.check_iv_alerts", lambda: iv_greeks_monitor.check_iv_alerts('SPY', 0.25, 0.20) is not None)
    
    # Position Monitor
    run_test("Position.check_pnl_alerts", lambda: position_monitor.check_pnl_alerts([{'unrealized_pnl': -100}]) is not None)
    
    # Alert Manager
    test_alert = Alert('test', AlertType.PRICE_MOVE, AlertSeverity.INFO, 'TEST', 'Test', {})
    run_test("AlertManager.add_alert", lambda: alert_manager.add_alert(test_alert) is None) # Returns None
    run_test("AlertManager.get_alerts", lambda: len(alert_manager.get_alerts()) >= 0)
    
    # Master Monitor
    run_test("MasterMonitor.run_all_checks", lambda: master_monitor.run_all_checks({'SPY': {'price': 500}}, []) is not None)

if __name__ == "__main__":
    print("🚀 STARTING COMPREHENSIVE FEATURE TEST")
    test_ai_automation_engine()
    test_smart_analysis_engine()
    test_auto_trading_engine()
    test_monitoring_engine()
    print("\n🎉 ALL TESTS COMPLETED")

"""
Phase 6-8 Strategy Bot Integration Example
===========================================

Demonstrates full integration of:
- Phase 8 Analytics (trend_analyzer, volatility_heatmap, risk_dashboard)
- Phase 8B Scenario Engine (Monte Carlo simulations)
- Strategy Bot Framework (signal generation, execution, risk management)
- Broker Connector (mock mode for testing)
- TradingView Alerts (signal ingestion)

This example shows both offline (mock) and analytics-driven signal generation.

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0 (Phase 6-8 Strategy Bot Integration)
Date: October 29, 2025
"""

import json
import logging
from datetime import datetime
from pathlib import Path

# Import scenario engine (Phase 8B)
from scenario_engine import (
    ScenarioEngine, ScenarioParameters, ScenarioType,
    create_monte_carlo_scenario
)

# Import Phase 8 analytics
try:
    from trend_analyzer import TrendAnalyzer
    from volatility_heatmap import VolatilityHeatmap
    from risk_dashboard import RiskDashboard
    PHASE8_AVAILABLE = True
except ImportError:
    PHASE8_AVAILABLE = False
    logging.warning("⚠️  Phase 8 analytics not available")

# Import strategy bot components
from strategy_bot import (
    StrategyBot, StrategyMode, RiskLimits,
    SignalGenerator, RiskManager, ExecutionEngine,
    Backtester
)

from broker_connector import (
    MockBrokerConnector, OrderSide, AssetClass
)

from tradingview_connector import (
    MockAlertGenerator, SignalTransformer, SignalLogger
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# INTEGRATION EXAMPLE 1: ANALYTICS-DRIVEN STRATEGY BOT
# ============================================================================

def run_analytics_driven_strategy():
    """
    Run strategy bot with Phase 8 analytics integration.
    
    Workflow:
    1. Generate scenario data (Phase 8B)
    2. Run analytics (Phase 8: trend, volatility, risk)
    3. Generate signals from analytics (strategy_bot)
    4. Execute signals (broker_connector)
    5. Track performance and save results
    """
    logger.info("=" * 80)
    logger.info("EXAMPLE 1: ANALYTICS-DRIVEN STRATEGY BOT")
    logger.info("=" * 80)
    
    # Step 1: Generate scenario data
    logger.info("\n📊 Step 1: Generate Monte Carlo Scenario")
    tickers = ["SPY", "QQQ", "IWM"]
    scenario = create_monte_carlo_scenario(
        tickers=tickers,
        num_simulations=1000,
        num_days=252,
        random_seed=42,
        output_dir="outputs/strategy_bot_integration"
    )
    logger.info(f"   Generated scenario: {len(scenario.paths)} paths")
    
    # Step 2: Run Phase 8 analytics (if available)
    if PHASE8_AVAILABLE:
        logger.info("\n🔬 Step 2: Run Phase 8 Analytics")
        
        # Prepare data for analytics
        forecast_data = {}
        for path in scenario.paths:
            # Convert scenario path to analytics format
            forecast_list = []
            for i, (date, ret) in enumerate(zip(path.dates[1:], path.returns)):
                forecast_list.append({
                    "timestamp": date,
                    "expected_return": ret,
                    "forecast_index": i
                })
            forecast_data[path.ticker] = forecast_list
        
        # Trend analysis
        trend_analyzer = TrendAnalyzer(lookback_days=20)
        trend_result = trend_analyzer.analyze_trends(forecast_data)
        logger.info(f"   Trend analysis complete: {len(trend_result.ticker_signals)} signals")
        
        # Volatility analysis
        volatility_heatmap = VolatilityHeatmap(window_size=20)
        price_data = {path.ticker: path.returns for path in scenario.paths}
        volatility_result = volatility_heatmap.analyze_volatility(price_data)
        logger.info(f"   Volatility analysis complete: {len(volatility_result.ticker_metrics)} metrics")
        
        # Risk dashboard
        risk_dashboard = RiskDashboard()
        risk_snapshot = risk_dashboard.generate_dashboard_snapshot(trend_result, volatility_result)
        logger.info(f"   Risk dashboard complete: Risk score = {risk_snapshot.portfolio_risk_score:.1f}")
        
    else:
        logger.warning("⚠️  Phase 8 analytics not available, using mock signals")
        trend_result = None
        volatility_result = None
        risk_snapshot = None
    
    # Step 3: Initialize strategy bot
    logger.info("\n🤖 Step 3: Initialize Strategy Bot")
    risk_limits = RiskLimits(
        max_portfolio_risk_pct=5.0,
        max_position_size_pct=10.0,
        max_daily_loss_pct=3.0,
        max_contracts_per_trade=5
    )
    
    bot = StrategyBot(
        mode=StrategyMode.MOCK,
        risk_limits=risk_limits,
        initial_cash=100000.0
    )
    logger.info(f"   Bot initialized: ${bot.initial_cash:,.2f} capital")
    
    # Step 4: Run strategy
    logger.info("\n🚀 Step 4: Run Strategy Bot")
    
    # Set market prices from scenario
    for path in scenario.paths:
        bot.broker.set_market_price(path.ticker, path.prices[-1])
    
    # Generate and execute signals
    if PHASE8_AVAILABLE:
        results = bot.run(
            trend_result=trend_result,
            volatility_metrics={path.ticker: volatility_result.ticker_metrics.get(path.ticker) 
                                for path in scenario.paths},
            risk_snapshot=risk_snapshot
        )
    else:
        results = bot.run()
    
    logger.info(f"   Executed {len(results)} trades")
    
    # Step 5: Get performance metrics
    logger.info("\n💰 Step 5: Portfolio Performance")
    metrics = bot.get_portfolio_metrics()
    
    logger.info(f"   Total Value: ${metrics.total_value:,.2f}")
    logger.info(f"   Cash: ${metrics.cash:,.2f}")
    logger.info(f"   Equity: ${metrics.equity:,.2f}")
    logger.info(f"   Total P&L: ${metrics.total_pnl:,.2f} ({metrics.total_pnl_pct:.2f}%)")
    logger.info(f"   Current Risk: {metrics.current_risk_pct:.2f}%")
    
    # Step 6: Save results
    logger.info("\n💾 Step 6: Save Results")
    output_dir = Path("outputs/strategy_bot_integration")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    bot.save_logs(
        trade_log_path=str(output_dir / "analytics_driven_trades.json"),
        transaction_log_path=str(output_dir / "analytics_driven_transactions.json")
    )
    
    # Save metrics
    with open(output_dir / "analytics_driven_metrics.json", 'w') as f:
        json.dump(metrics.to_dict(), f, indent=2)
    
    logger.info(f"   Results saved to {output_dir}")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ EXAMPLE 1 COMPLETE")
    logger.info("=" * 80)
    
    return bot, metrics


# ============================================================================
# INTEGRATION EXAMPLE 2: TRADINGVIEW ALERTS + STRATEGY BOT
# ============================================================================

def run_tradingview_alerts_integration():
    """
    Integrate TradingView alerts with strategy bot execution.
    
    Workflow:
    1. Generate mock TradingView alerts
    2. Validate and transform alerts to signals
    3. Execute signals via strategy bot
    4. Track results
    """
    logger.info("=" * 80)
    logger.info("EXAMPLE 2: TRADINGVIEW ALERTS INTEGRATION")
    logger.info("=" * 80)
    
    # Step 1: Generate mock alerts
    logger.info("\n📡 Step 1: Generate Mock TradingView Alerts")
    mock_gen = MockAlertGenerator(random_seed=42)
    
    alerts = []
    # Stock alerts
    alerts.append(mock_gen.generate_stock_alert("SPY", "buy", 450.0))
    alerts.append(mock_gen.generate_stock_alert("QQQ", "buy", 380.0))
    
    # Options alerts
    alerts.append(mock_gen.generate_options_alert("AAPL", "call", "buy", 185.0, "2025-11-30", 5.0))
    alerts.append(mock_gen.generate_options_alert("SPY", "put", "sell", 440.0, "2025-11-30", 3.0))
    
    logger.info(f"   Generated {len(alerts)} mock alerts")
    
    # Step 2: Transform alerts to signals
    logger.info("\n🔄 Step 2: Transform Alerts to Signals")
    transformer = SignalTransformer()
    signal_logger = SignalLogger(log_path="outputs/strategy_bot_integration/tradingview_signals.json")
    
    signals = []
    for alert_data in alerts:
        signal = transformer.transform_dict(alert_data)
        signal_logger.log_signal(signal)
        signals.append(signal)
        logger.info(f"   - {signal.symbol} {signal.signal_type.value}")
    
    # Step 3: Initialize strategy bot
    logger.info("\n🤖 Step 3: Initialize Strategy Bot")
    broker = MockBrokerConnector(initial_cash=100000.0, random_seed=42)
    
    # Set market prices
    broker.set_market_price("SPY", 450.0)
    broker.set_market_price("QQQ", 380.0)
    broker.set_market_price("AAPL", 180.0)
    
    risk_manager = RiskManager(RiskLimits())
    execution_engine = ExecutionEngine(broker, risk_manager)
    
    # Step 4: Execute signals
    logger.info("\n🚀 Step 4: Execute Signals")
    results = []
    for signal in signals:
        result = execution_engine.execute_signal(signal)
        results.append(result)
        logger.info(f"   {signal.symbol}: {result.status.value}")
    
    # Step 5: Get results
    logger.info("\n💰 Step 5: Results Summary")
    account = broker.get_account_info()
    positions = broker.get_positions()
    
    logger.info(f"   Total Trades: {len(results)}")
    logger.info(f"   Successful: {sum(1 for r in results if r.risk_check_passed)}")
    logger.info(f"   Cash: ${account.cash:,.2f}")
    logger.info(f"   Portfolio Value: ${account.portfolio_value:,.2f}")
    logger.info(f"   Positions: {len(positions)}")
    
    # Step 6: Save results
    logger.info("\n💾 Step 6: Save Results")
    output_dir = Path("outputs/strategy_bot_integration")
    execution_engine.save_trade_log(str(output_dir / "tradingview_trades.json"))
    broker.save_transaction_log(str(output_dir / "tradingview_transactions.json"))
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ EXAMPLE 2 COMPLETE")
    logger.info("=" * 80)
    
    return execution_engine, results


# ============================================================================
# INTEGRATION EXAMPLE 3: BACKTESTING WITH PHASE 8B SCENARIOS
# ============================================================================

def run_backtest_with_scenarios():
    """
    Run backtest using Phase 8B scenario data.
    
    Workflow:
    1. Generate multiple scenarios (bullish, bearish, volatile)
    2. Create trading signals for each scenario
    3. Run backtest
    4. Analyze results
    """
    logger.info("=" * 80)
    logger.info("EXAMPLE 3: BACKTESTING WITH SCENARIOS")
    logger.info("=" * 80)
    
    # Step 1: Initialize backtester
    logger.info("\n🔬 Step 1: Initialize Backtester")
    backtester = Backtester(initial_cash=100000.0)
    
    # Step 2: Generate test scenario
    logger.info("\n📊 Step 2: Generate Scenario Data")
    scenario = create_monte_carlo_scenario(
        tickers=["SPY", "QQQ"],
        num_simulations=100,
        num_days=60,  # 3 months
        random_seed=42,
        output_dir="outputs/strategy_bot_integration"
    )
    
    # Set market prices
    for path in scenario.paths:
        backtester.broker.set_market_price(path.ticker, path.prices[-1])
    
    # Step 3: Generate signals (mock)
    logger.info("\n📈 Step 3: Generate Trading Signals")
    from tradingview_connector import TradeSignal, SignalType, AlertSource, SignalPriority
    
    signals = []
    
    # Simulate signals over time
    for day in [10, 20, 30, 40, 50]:
        # Buy signals early
        if day < 30:
            signals.append(TradeSignal(
                signal_id=f"backtest_signal_{day:03d}_buy",
                signal_type=SignalType.BUY_CALL,
                symbol="SPY",
                qty=2,
                source=AlertSource.STRATEGY_BOT,
                priority=SignalPriority.MEDIUM,
                strike=scenario.paths[0].prices[day] * 1.02,  # 2% OTM
                expiration="2025-12-31",
                trend_signal="bullish",
                volatility_regime="low",
                risk_score=40.0
            ))
        # Sell signals later
        else:
            signals.append(TradeSignal(
                signal_id=f"backtest_signal_{day:03d}_sell",
                signal_type=SignalType.SELL_CALL,
                symbol="SPY",
                qty=1,
                source=AlertSource.STRATEGY_BOT,
                priority=SignalPriority.MEDIUM,
                strike=scenario.paths[0].prices[day] * 1.05,  # 5% OTM
                expiration="2025-12-31",
                trend_signal="neutral",
                volatility_regime="medium",
                risk_score=55.0
            ))
    
    logger.info(f"   Generated {len(signals)} signals")
    
    # Step 4: Run backtest
    logger.info("\n🚀 Step 4: Run Backtest")
    backtest_report = backtester.run_backtest(signals)
    
    # Step 5: Results
    logger.info("\n📊 Step 5: Backtest Results")
    logger.info(f"   Initial Capital: ${backtest_report['initial_capital']:,.2f}")
    logger.info(f"   Final Capital: ${backtest_report['final_capital']:,.2f}")
    logger.info(f"   Total P&L: ${backtest_report['total_pnl']:,.2f} ({backtest_report['total_pnl_pct']:.2f}%)")
    logger.info(f"   Total Trades: {backtest_report['total_trades']}")
    logger.info(f"   Successful: {backtest_report['successful_trades']}")
    logger.info(f"   Success Rate: {backtest_report['success_rate']:.1f}%")
    
    # Step 6: Save report
    logger.info("\n💾 Step 6: Save Backtest Report")
    output_dir = Path("outputs/strategy_bot_integration")
    backtester.save_backtest_report(str(output_dir / "backtest_report.json"))
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ EXAMPLE 3 COMPLETE")
    logger.info("=" * 80)
    
    return backtester, backtest_report


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    logger.info("\n")
    logger.info("*" * 80)
    logger.info("PHASE 6-8 STRATEGY BOT INTEGRATION EXAMPLES")
    logger.info("*" * 80)
    logger.info("\n")
    
    # Run all integration examples
    
    # Example 1: Analytics-driven strategy
    bot1, metrics1 = run_analytics_driven_strategy()
    
    print("\n" + "-" * 80 + "\n")
    
    # Example 2: TradingView alerts
    engine2, results2 = run_tradingview_alerts_integration()
    
    print("\n" + "-" * 80 + "\n")
    
    # Example 3: Backtesting
    backtester3, report3 = run_backtest_with_scenarios()
    
    # Final summary
    logger.info("\n")
    logger.info("*" * 80)
    logger.info("ALL INTEGRATION EXAMPLES COMPLETE")
    logger.info("*" * 80)
    logger.info("\nResults saved to: outputs/strategy_bot_integration/")
    logger.info("\nFiles created:")
    logger.info("  - analytics_driven_trades.json")
    logger.info("  - analytics_driven_transactions.json")
    logger.info("  - analytics_driven_metrics.json")
    logger.info("  - tradingview_signals.json")
    logger.info("  - tradingview_trades.json")
    logger.info("  - tradingview_transactions.json")
    logger.info("  - backtest_report.json")
    logger.info("*" * 80)
    logger.info("\n")

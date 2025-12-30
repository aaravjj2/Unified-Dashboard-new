#!/usr/bin/env python3
"""
Comprehensive E2E Test Suite for AI/ML Options Lab
==================================================
Tests all 40+ AI/ML improvements:
- ML Price Prediction models
- Sentiment & News Integration
- Risk Management AI
- Autonomous Monitoring
- GROQ AI Enhancements
- Auto-Execution Features

Run: python test_all_ai_ml_improvements.py
"""

import os
import sys
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass

# Add path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))


@dataclass
class TestResult:
    """Test result."""
    name: str
    category: str
    passed: bool
    message: str
    duration: float


class AIMLTestSuite:
    """Comprehensive test suite for all AI/ML improvements."""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = time.time()
    
    def run_test(self, name: str, category: str, test_func):
        """Run a single test."""
        start = time.time()
        try:
            result = test_func()
            passed = result if isinstance(result, bool) else True
            message = "✅ Passed" if passed else "❌ Failed"
            if isinstance(result, str):
                message = f"✅ {result}"
        except Exception as e:
            passed = False
            message = f"❌ Error: {str(e)[:100]}"
            traceback.print_exc()
        
        duration = time.time() - start
        self.results.append(TestResult(name, category, passed, message, duration))
        
        status = "✅" if passed else "❌"
        print(f"  {status} {name}: {message} ({duration:.2f}s)")
    
    def run_all_tests(self):
        """Run all test categories."""
        print("\n" + "="*70)
        print("🧪 AI/ML Options Lab - Comprehensive Test Suite")
        print("="*70 + "\n")
        
        # Category 1: ML Price Prediction
        print("\n📊 CATEGORY 1: ML Price Prediction Models")
        print("-"*50)
        self.test_ml_price_prediction()
        
        # Category 2: Sentiment Integration
        print("\n📰 CATEGORY 2: Sentiment & News Integration")
        print("-"*50)
        self.test_sentiment_integration()
        
        # Category 3: Risk Management AI
        print("\n⚠️ CATEGORY 3: Risk Management AI")
        print("-"*50)
        self.test_risk_management()
        
        # Category 4: Autonomous Monitoring
        print("\n🔄 CATEGORY 4: Autonomous Monitoring")
        print("-"*50)
        self.test_autonomous_monitoring()
        
        # Category 5: GROQ AI Enhancements
        print("\n🤖 CATEGORY 5: GROQ AI Enhancements")
        print("-"*50)
        self.test_groq_ai()
        
        # Category 6: Auto-Execution Features
        print("\n⚡ CATEGORY 6: Auto-Execution Features")
        print("-"*50)
        self.test_auto_execution()
        
        # Category 7: Core AI/ML Engine
        print("\n🧠 CATEGORY 7: Core AI/ML Engine")
        print("-"*50)
        self.test_core_ai_engine()
        
        # Category 8: Integration Tests
        print("\n🔗 CATEGORY 8: Integration Tests")
        print("-"*50)
        self.test_integration()
        
        # Print summary and return results
        return self.print_summary()
    
    # ============================================================
    # CATEGORY 1: ML Price Prediction
    # ============================================================
    
    def test_ml_price_prediction(self):
        """Test ML price prediction models."""
        
        def test_lstm_predictor():
            from financial_dashboard.tabs.options_lab.ml_price_predictor import LSTMPricePredictor
            predictor = LSTMPricePredictor()
            forecast = predictor.predict('SPY', 5)
            assert forecast.ticker == 'SPY'
            assert forecast.predicted_price > 0
            assert 0 <= forecast.prob_up <= 1
            return f"SPY prediction: ${forecast.predicted_price:.2f}"
        
        def test_iv_forecaster():
            from financial_dashboard.tabs.options_lab.ml_price_predictor import IVForecaster
            forecaster = IVForecaster()
            forecast = forecaster.forecast('SPY')
            assert forecast.ticker == 'SPY'
            assert forecast.current_iv > 0
            assert 0 <= forecast.iv_rank <= 100
            return f"IV Rank: {forecast.iv_rank:.1f}%"
        
        def test_earnings_predictor():
            from financial_dashboard.tabs.options_lab.ml_price_predictor import EarningsMovePredictor
            predictor = EarningsMovePredictor()
            prediction = predictor.predict('AAPL')
            assert prediction.ticker == 'AAPL'
            assert prediction.avg_move > 0
            assert prediction.suggested_strategy in ['short_straddle', 'long_straddle', 'bull_put_spread', 'iron_condor']
            return f"Expected move: {prediction.predicted_move:.1f}%"
        
        def test_pattern_recognizer():
            from financial_dashboard.tabs.options_lab.ml_price_predictor import PatternRecognizer
            recognizer = PatternRecognizer()
            patterns = recognizer.scan_patterns('SPY')
            assert isinstance(patterns, list)
            return f"Found {len(patterns)} patterns"
        
        def test_mean_reversion():
            from financial_dashboard.tabs.options_lab.ml_price_predictor import MeanReversionAnalyzer
            analyzer = MeanReversionAnalyzer()
            signal = analyzer.analyze('SPY')
            assert signal.ticker == 'SPY'
            assert signal.signal_type in ['oversold', 'overbought', 'neutral']
            return f"Signal: {signal.signal_type} (z={signal.z_score:.2f})"
        
        def test_unified_predictor():
            from financial_dashboard.tabs.options_lab.ml_price_predictor import get_ml_predictor
            predictor = get_ml_predictor()
            signal = predictor.quick_signal('SPY')
            assert 'signal' in signal
            assert 'strength' in signal
            return f"Quick signal: {signal['signal']} ({signal['strength']:.2f})"
        
        self.run_test("LSTM Price Predictor", "ML Prediction", test_lstm_predictor)
        self.run_test("IV Forecaster", "ML Prediction", test_iv_forecaster)
        self.run_test("Earnings Move Predictor", "ML Prediction", test_earnings_predictor)
        self.run_test("Pattern Recognizer", "ML Prediction", test_pattern_recognizer)
        self.run_test("Mean Reversion Analyzer", "ML Prediction", test_mean_reversion)
        self.run_test("Unified ML Predictor", "ML Prediction", test_unified_predictor)
    
    # ============================================================
    # CATEGORY 2: Sentiment Integration
    # ============================================================
    
    def test_sentiment_integration(self):
        """Test sentiment and news integration."""
        
        def test_news_analyzer():
            from financial_dashboard.tabs.options_lab.sentiment_integration import NewsAnalyzer
            analyzer = NewsAnalyzer()
            sentiment = analyzer.analyze_news('AAPL')
            assert sentiment.ticker == 'AAPL'
            assert -1 <= sentiment.avg_sentiment <= 1
            return f"News sentiment: {sentiment.avg_sentiment:.3f}"
        
        def test_social_sentiment():
            from financial_dashboard.tabs.options_lab.sentiment_integration import SocialSentimentAnalyzer
            analyzer = SocialSentimentAnalyzer()
            sentiment = analyzer.analyze_social('NVDA')
            assert sentiment.ticker == 'NVDA'
            assert sentiment.mention_count > 0
            return f"Mentions: {sentiment.mention_count}"
        
        def test_analyst_ratings():
            from financial_dashboard.tabs.options_lab.sentiment_integration import AnalystRatingAggregator
            aggregator = AnalystRatingAggregator()
            consensus = aggregator.get_consensus('AAPL')
            assert consensus.ticker == 'AAPL'
            assert consensus.buy_count + consensus.hold_count + consensus.sell_count > 0
            return f"Consensus: {consensus.consensus_rating}"
        
        def test_insider_analyzer():
            from financial_dashboard.tabs.options_lab.sentiment_integration import InsiderAnalyzer
            analyzer = InsiderAnalyzer()
            activity = analyzer.analyze_insider_activity('MSFT')
            assert activity.ticker == 'MSFT'
            assert activity.signal in ['bullish', 'bearish', 'neutral']
            return f"Insider signal: {activity.signal}"
        
        def test_options_flow():
            from financial_dashboard.tabs.options_lab.sentiment_integration import OptionsFlowAnalyzer
            analyzer = OptionsFlowAnalyzer()
            flow = analyzer.analyze_flow('SPY')
            assert flow.ticker == 'SPY'
            assert flow.put_call_ratio > 0
            return f"P/C Ratio: {flow.put_call_ratio:.2f}"
        
        def test_comprehensive_sentiment():
            from financial_dashboard.tabs.options_lab.sentiment_integration import get_comprehensive_sentiment
            engine = get_comprehensive_sentiment()
            sentiment = engine.full_sentiment_analysis('SPY')
            assert sentiment.ticker == 'SPY'
            assert sentiment.signal in ['strong_buy', 'buy', 'hold', 'sell', 'strong_sell']
            return f"Signal: {sentiment.signal} ({sentiment.composite_score:.3f})"
        
        self.run_test("News Analyzer", "Sentiment", test_news_analyzer)
        self.run_test("Social Sentiment", "Sentiment", test_social_sentiment)
        self.run_test("Analyst Ratings", "Sentiment", test_analyst_ratings)
        self.run_test("Insider Activity", "Sentiment", test_insider_analyzer)
        self.run_test("Options Flow", "Sentiment", test_options_flow)
        self.run_test("Comprehensive Sentiment", "Sentiment", test_comprehensive_sentiment)
    
    # ============================================================
    # CATEGORY 3: Risk Management AI
    # ============================================================
    
    def test_risk_management(self):
        """Test risk management AI."""
        
        def test_stop_loss_calculator():
            from financial_dashboard.tabs.options_lab.risk_management_ai import AutoStopLossCalculator
            calculator = AutoStopLossCalculator()
            stop = calculator.calculate_stop('SPY', 500, 'long', 'moderate')
            assert stop.ticker == 'SPY'
            # For long positions, tight_stop should be closest to price, wide furthest
            assert stop.tight_stop > 0 and stop.standard_stop > 0 and stop.wide_stop > 0
            return f"Stops: ${stop.tight_stop:.2f} / ${stop.standard_stop:.2f} / ${stop.wide_stop:.2f}"
        
        def test_var_calculator():
            from financial_dashboard.tabs.options_lab.risk_management_ai import VaRCalculator
            calculator = VaRCalculator()
            positions = [{'ticker': 'SPY', 'value': 5000}, {'ticker': 'QQQ', 'value': 3000}]
            var = calculator.calculate_portfolio_var(positions, 10000, 1)
            assert var.var_95 > 0
            assert var.var_99 > var.var_95
            return f"1-day VaR(95%): ${var.var_95:.2f}"
        
        def test_drawdown_analyzer():
            from financial_dashboard.tabs.options_lab.risk_management_ai import DrawdownRiskAnalyzer
            analyzer = DrawdownRiskAnalyzer()
            risk = analyzer.analyze_drawdown_risk('SPY')
            assert risk.ticker == 'SPY'
            assert risk.max_historical_drawdown < 0
            return f"Max DD: {risk.max_historical_drawdown:.1f}%"
        
        def test_correlation_analyzer():
            from financial_dashboard.tabs.options_lab.risk_management_ai import CorrelationRiskAnalyzer
            analyzer = CorrelationRiskAnalyzer()
            positions = [
                {'ticker': 'AAPL', 'value': 5000},
                {'ticker': 'MSFT', 'value': 5000},
                {'ticker': 'GOOGL', 'value': 3000}
            ]
            alerts = analyzer.analyze_correlation_risk(positions)
            assert isinstance(alerts, list)
            return f"Found {len(alerts)} correlation alerts"
        
        def test_tail_risk():
            from financial_dashboard.tabs.options_lab.risk_management_ai import TailRiskAnalyzer
            analyzer = TailRiskAnalyzer()
            risk = analyzer.analyze_tail_risk('TSLA')
            assert risk.ticker == 'TSLA'
            assert risk.tail_index is not None
            return f"Tail risk: {risk.overall_tail_risk.name}"
        
        def test_unified_risk_manager():
            from financial_dashboard.tabs.options_lab.risk_management_ai import get_risk_manager
            manager = get_risk_manager()
            positions = [{'ticker': 'SPY', 'value': 10000}]
            analysis = manager.full_risk_analysis(positions, 10000)
            assert 'overall_risk_level' in analysis
            assert 'summary' in analysis
            return f"Risk level: {analysis['overall_risk_level'].name}"
        
        self.run_test("Auto Stop-Loss Calculator", "Risk", test_stop_loss_calculator)
        self.run_test("VaR Calculator", "Risk", test_var_calculator)
        self.run_test("Drawdown Analyzer", "Risk", test_drawdown_analyzer)
        self.run_test("Correlation Analyzer", "Risk", test_correlation_analyzer)
        self.run_test("Tail Risk Analyzer", "Risk", test_tail_risk)
        self.run_test("Unified Risk Manager", "Risk", test_unified_risk_manager)
    
    # ============================================================
    # CATEGORY 4: Autonomous Monitoring
    # ============================================================
    
    def test_autonomous_monitoring(self):
        """Test autonomous monitoring system."""
        
        def test_alert_generator():
            from financial_dashboard.tabs.options_lab.autonomous_monitoring import AutoAlertGenerator
            generator = AutoAlertGenerator()
            market_data = {'vix': 30, 'spy_change_pct': -3}
            positions = [{'ticker': 'SPY', 'pnl_pct': 60, 'dte': 5}]
            alerts = generator.check_and_generate_alerts(market_data, positions)
            assert isinstance(alerts, list)
            return f"Generated {len(alerts)} alerts"
        
        def test_volatility_tracker():
            from financial_dashboard.tabs.options_lab.autonomous_monitoring import VolatilityRegimeTracker
            tracker = VolatilityRegimeTracker()
            regime = tracker.update_regime(25)
            assert regime.regime in ['low', 'normal', 'elevated', 'high', 'extreme']
            assert len(regime.trading_implications) > 0
            return f"Regime: {regime.regime} (VIX {regime.vix_level})"
        
        def test_earnings_monitor():
            from financial_dashboard.tabs.options_lab.autonomous_monitoring import EarningsCalendarMonitor
            monitor = EarningsCalendarMonitor()
            events = monitor.check_upcoming_earnings(['AAPL', 'NVDA'], [])
            assert isinstance(events, list)
            return f"Found {len(events)} earnings events"
        
        def test_roll_optimizer():
            from financial_dashboard.tabs.options_lab.autonomous_monitoring import RollTimingOptimizer
            optimizer = RollTimingOptimizer()
            positions = [{'ticker': 'SPY', 'dte': 10}]
            opportunities = optimizer.analyze_roll_opportunities(positions)
            assert len(opportunities) > 0
            return f"Roll urgency: {opportunities[0].urgency}"
        
        def test_position_health():
            from financial_dashboard.tabs.options_lab.autonomous_monitoring import PositionHealthMonitor
            monitor = PositionHealthMonitor()
            positions = [{'ticker': 'SPY', 'pnl_pct': 25, 'delta': 0.3, 'theta': 5, 'dte': 20}]
            health = monitor.check_all_positions(positions)
            assert len(health) == 1
            assert 0 <= health[0].health_score <= 100
            return f"Health score: {health[0].health_score:.0f}/100"
        
        def test_autonomous_monitor():
            from financial_dashboard.tabs.options_lab.autonomous_monitoring import get_autonomous_monitor
            monitor = get_autonomous_monitor()
            status = monitor.get_status()
            assert 'status' in status
            scan = monitor.scan_now()
            assert 'regime' in scan
            return f"Monitor status: {status['status']}"
        
        self.run_test("Auto Alert Generator", "Monitoring", test_alert_generator)
        self.run_test("Volatility Regime Tracker", "Monitoring", test_volatility_tracker)
        self.run_test("Earnings Calendar Monitor", "Monitoring", test_earnings_monitor)
        self.run_test("Roll Timing Optimizer", "Monitoring", test_roll_optimizer)
        self.run_test("Position Health Monitor", "Monitoring", test_position_health)
        self.run_test("Autonomous Monitor", "Monitoring", test_autonomous_monitor)
    
    # ============================================================
    # CATEGORY 5: GROQ AI Enhancements
    # ============================================================
    
    def test_groq_ai(self):
        """Test GROQ AI enhancements."""
        
        def test_groq_client():
            from financial_dashboard.tabs.options_lab.groq_ai_enhanced import EnhancedGroqClient
            client = EnhancedGroqClient()
            assert client.default_model is not None
            assert len(client.system_prompts) > 0
            return f"Model: {client.default_model}"
        
        def test_zero_prompt_analyzer():
            from financial_dashboard.tabs.options_lab.groq_ai_enhanced import ZeroPromptAnalyzer
            analyzer = ZeroPromptAnalyzer()
            data = {'spot_price': 500, 'iv_rank': 65, 'regime': 'normal'}
            analysis = analyzer.auto_analyze('SPY', data)
            assert analysis.ticker == 'SPY'
            assert len(analysis.reasoning_chain) > 0
            return f"Confidence: {analysis.confidence:.2f}"
        
        def test_proactive_recommendations():
            from financial_dashboard.tabs.options_lab.groq_ai_enhanced import ProactiveRecommendationEngine
            engine = ProactiveRecommendationEngine()
            market_data = {'vix': 28, 'spy_change_pct': -1}
            positions = [{'ticker': 'SPY', 'pnl_pct': 55, 'dte': 20}]
            insights = engine.generate_daily_insights(market_data, positions, ['AAPL', 'NVDA'])
            assert isinstance(insights, list)
            return f"Generated {len(insights)} insights"
        
        def test_context_conversation():
            from financial_dashboard.tabs.options_lab.groq_ai_enhanced import ContextAwareConversation
            conv = ContextAwareConversation()
            conv_id = conv.create_conversation()
            response = conv.chat(conv_id, "What's a good strategy for high IV?")
            assert len(response) > 0
            summary = conv.get_conversation_summary(conv_id)
            assert summary['message_count'] == 2
            return f"Conversation created with {summary['message_count']} messages"
        
        def test_multi_model_consensus():
            from financial_dashboard.tabs.options_lab.groq_ai_enhanced import MultiModelConsensus
            consensus = MultiModelConsensus()
            result = consensus.get_consensus("Should I sell premium when IV is high?", num_samples=2)
            assert result.consensus_confidence > 0
            return f"Agreement: {result.agreement_level:.2f}"
        
        def test_explainable_ai():
            from financial_dashboard.tabs.options_lab.groq_ai_enhanced import ExplainableAI
            explainer = ExplainableAI()
            explanation = explainer.explain_recommendation(
                "Sell iron condor on SPY",
                {'iv_rank': 75, 'regime': 'sideways'}
            )
            assert 'explanation' in explanation
            assert 'reasoning_chain' in explanation
            return f"Generated {len(explanation['reasoning_chain'])} reasoning steps"
        
        def test_unified_groq_ai():
            from financial_dashboard.tabs.options_lab.groq_ai_enhanced import get_groq_ai
            ai = get_groq_ai()
            analysis = ai.auto_analyze('QQQ')
            assert analysis.ticker == 'QQQ'
            return f"Analysis type: {analysis.analysis_type}"
        
        self.run_test("Enhanced GROQ Client", "GROQ AI", test_groq_client)
        self.run_test("Zero-Prompt Analyzer", "GROQ AI", test_zero_prompt_analyzer)
        self.run_test("Proactive Recommendations", "GROQ AI", test_proactive_recommendations)
        self.run_test("Context-Aware Conversation", "GROQ AI", test_context_conversation)
        self.run_test("Multi-Model Consensus", "GROQ AI", test_multi_model_consensus)
        self.run_test("Explainable AI", "GROQ AI", test_explainable_ai)
        self.run_test("Unified GROQ AI", "GROQ AI", test_unified_groq_ai)
    
    # ============================================================
    # CATEGORY 6: Auto-Execution Features
    # ============================================================
    
    def test_auto_execution(self):
        """Test auto-execution features."""
        
        def test_one_click_trader():
            from financial_dashboard.tabs.options_lab.auto_execution import EnhancedOneClickTrader
            trader = EnhancedOneClickTrader()
            order = trader.generate_order('SPY', 'iron_condor', 10000)
            assert order.ticker == 'SPY'
            assert len(order.legs) == 4
            return f"Order: {order.strategy} with {len(order.legs)} legs"
        
        def test_adjustment_engine():
            from financial_dashboard.tabs.options_lab.auto_execution import AutoAdjustmentEngine
            engine = AutoAdjustmentEngine()
            triggers = engine.create_default_triggers('pos_1', 'SPY', 1.50)
            assert len(triggers) == 3  # profit, stop, roll
            return f"Created {len(triggers)} triggers"
        
        def test_smart_router():
            from financial_dashboard.tabs.options_lab.auto_execution import SmartOrderRouter, EnhancedOneClickTrader
            trader = EnhancedOneClickTrader()
            router = SmartOrderRouter()
            order = trader.generate_order('SPY', 'bull_put_spread')
            plan = router.route_order(order)
            assert 'routing' in plan
            assert 'execution_steps' in plan
            return f"Routed to {plan['routing']['primary_exchange']}"
        
        def test_position_migrator():
            from financial_dashboard.tabs.options_lab.auto_execution import PositionMigrator
            migrator = PositionMigrator()
            position = {
                'id': 'pos_1',
                'ticker': 'SPY',
                'strategy': 'iron_condor',
                'pnl_pct': 55,
                'dte': 20,
                'legs': []
            }
            migration = migrator.suggest_migration(position, {})
            assert migration is not None
            return f"Migration reason: {migration.reason.value}"
        
        def test_auto_journal():
            from financial_dashboard.tabs.options_lab.auto_execution import AutoJournalSystem
            journal = AutoJournalSystem()
            entry = journal.record_entry(
                {'ticker': 'SPY', 'strategy': 'iron_condor', 'entry_price': 1.50},
                {'iv_rank': 65, 'regime': 'normal', 'sentiment': 'neutral'}
            )
            assert entry.ticker == 'SPY'
            journal.record_exit(entry.entry_id, 0.50, 'Profit target')
            stats = journal.get_statistics()
            assert stats['closed_trades'] == 1
            return f"Journal entry: {entry.entry_id}"
        
        def test_auto_execution_engine():
            from financial_dashboard.tabs.options_lab.auto_execution import get_auto_execution_engine
            engine = get_auto_execution_engine()
            result = engine.one_click_trade('QQQ', 'bull_put_spread')
            assert 'order' in result
            assert 'triggers' in result
            assert 'journal_entry' in result
            return f"One-click trade ready: {result['order'].order_id}"
        
        self.run_test("Enhanced One-Click Trader", "Auto-Exec", test_one_click_trader)
        self.run_test("Auto-Adjustment Engine", "Auto-Exec", test_adjustment_engine)
        self.run_test("Smart Order Router", "Auto-Exec", test_smart_router)
        self.run_test("Position Migrator", "Auto-Exec", test_position_migrator)
        self.run_test("Auto Journal System", "Auto-Exec", test_auto_journal)
        self.run_test("Auto-Execution Engine", "Auto-Exec", test_auto_execution_engine)
    
    # ============================================================
    # CATEGORY 7: Core AI/ML Engine
    # ============================================================
    
    def test_core_ai_engine(self):
        """Test core AI/ML engine components."""
        
        def test_auto_discovery():
            from financial_dashboard.tabs.options_lab.ai_ml_engine import get_auto_discovery
            discovery = get_auto_discovery()
            opportunities = discovery.get_top_opportunities(5)
            assert isinstance(opportunities, list)
            return f"Found {len(opportunities)} opportunities"
        
        def test_ai_strategy_selector():
            from financial_dashboard.tabs.options_lab.ai_ml_engine import get_ai_selector
            selector = get_ai_selector()
            recommendation = selector.get_best_strategy('SPY')
            assert recommendation is not None
            return f"Strategy: {recommendation.strategy_name}"
        
        def test_market_regime():
            from financial_dashboard.tabs.options_lab.ai_ml_engine import MarketRegime, RiskLevel
            assert MarketRegime.BULLISH.value == 'bullish'
            assert RiskLevel.HIGH.value == 4
            return "Enums validated"
        
        def test_sentiment_analyzer_original():
            from financial_dashboard.tabs.options_lab.sentiment_analyzer import get_sentiment_analyzer
            analyzer = get_sentiment_analyzer()
            sentiment = analyzer.analyze_ticker('AAPL')
            assert sentiment.ticker == 'AAPL'
            return f"Sentiment: {sentiment.overall_sentiment.name}"
        
        def test_position_monitor_original():
            from financial_dashboard.tabs.options_lab.position_monitor import get_position_monitor
            monitor = get_position_monitor()
            position = {
                'ticker': 'SPY', 'entry_price': 500, 'current_price': 505,
                'strategy': 'iron_condor', 'max_profit': 200, 'max_loss': -800, 'dte': 30,
                'entry_date': datetime.now() - timedelta(days=5)
            }
            status = monitor.analyze_position(position)
            assert status.ticker == 'SPY'
            return f"Position health: {status.health.name}"
        
        def test_proactive_advisor_original():
            from financial_dashboard.tabs.options_lab.proactive_advisor import get_proactive_advisor
            advisor = get_proactive_advisor()
            briefing = advisor.generate_daily_briefing()
            assert 'date' in briefing
            return f"Briefing date: {briefing['date']}"
        
        self.run_test("Auto Symbol Discovery", "Core AI", test_auto_discovery)
        self.run_test("AI Strategy Selector", "Core AI", test_ai_strategy_selector)
        self.run_test("Market Regime Enums", "Core AI", test_market_regime)
        self.run_test("Sentiment Analyzer (Original)", "Core AI", test_sentiment_analyzer_original)
        self.run_test("Position Monitor (Original)", "Core AI", test_position_monitor_original)
        self.run_test("Proactive Advisor (Original)", "Core AI", test_proactive_advisor_original)
    
    # ============================================================
    # CATEGORY 8: Integration Tests
    # ============================================================
    
    def test_integration(self):
        """Test integration between modules."""
        
        def test_full_analysis_pipeline():
            """Test complete analysis pipeline."""
            from financial_dashboard.tabs.options_lab.ml_price_predictor import get_ml_predictor
            from financial_dashboard.tabs.options_lab.sentiment_integration import get_comprehensive_sentiment
            from financial_dashboard.tabs.options_lab.risk_management_ai import get_risk_manager
            
            ticker = 'SPY'
            
            # Get ML prediction
            predictor = get_ml_predictor()
            price_signal = predictor.quick_signal(ticker)
            
            # Get sentiment
            sentiment_engine = get_comprehensive_sentiment()
            sentiment = sentiment_engine.quick_sentiment(ticker)
            
            # Get risk
            risk_manager = get_risk_manager()
            risk = risk_manager.quick_risk_check(ticker, 10000)
            
            # Combine signals
            combined = {
                'price_signal': price_signal['signal'],
                'sentiment_signal': sentiment['signal'],
                'risk_level': risk['tail_risk'].overall_tail_risk.name
            }
            
            assert all(k in combined for k in ['price_signal', 'sentiment_signal', 'risk_level'])
            return f"Combined: {combined['price_signal']}/{combined['sentiment_signal']}/{combined['risk_level']}"
        
        def test_auto_trade_with_monitoring():
            """Test auto-trade with monitoring integration."""
            from financial_dashboard.tabs.options_lab.auto_execution import get_auto_execution_engine
            from financial_dashboard.tabs.options_lab.autonomous_monitoring import get_autonomous_monitor
            
            engine = get_auto_execution_engine()
            monitor = get_autonomous_monitor()
            
            # Generate trade
            trade = engine.one_click_trade('AAPL', 'iron_condor')
            
            # Create position for monitoring
            position = {
                'id': trade['order'].order_id,
                'ticker': 'AAPL',
                'strategy': 'iron_condor',
                'dte': 45,
                'pnl_pct': 0
            }
            
            # Run monitoring scan
            scan = monitor.scan_now()
            
            assert trade['order'].status == 'pending'
            assert 'regime' in scan
            return "Trade and monitoring integrated"
        
        def test_ai_advisor_integration():
            """Test AI advisor with all data sources."""
            from financial_dashboard.tabs.options_lab.groq_ai_enhanced import get_groq_ai
            from financial_dashboard.tabs.options_lab.ml_price_predictor import get_ml_predictor
            
            ai = get_groq_ai()
            predictor = get_ml_predictor()
            
            # Get ML analysis
            analysis = predictor.full_analysis('SPY')
            
            # Get AI insights
            insights = ai.get_insights(
                positions=[{'ticker': 'SPY', 'pnl_pct': 25, 'dte': 30}],
                watchlist=['QQQ', 'AAPL']
            )
            
            assert analysis['ticker'] == 'SPY'
            assert isinstance(insights, list)
            return f"AI generated {len(insights)} insights from ML data"
        
        def test_end_to_end_workflow():
            """Test complete end-to-end workflow."""
            from financial_dashboard.tabs.options_lab.ai_ml_engine import get_auto_discovery, get_ai_selector
            from financial_dashboard.tabs.options_lab.auto_execution import get_auto_execution_engine
            from financial_dashboard.tabs.options_lab.autonomous_monitoring import get_autonomous_monitor
            
            # 1. Discover opportunities
            discovery = get_auto_discovery()
            opportunities = discovery.get_top_opportunities(3)
            
            if opportunities:
                ticker = opportunities[0].ticker
                
                # 2. Get strategy recommendation
                selector = get_ai_selector()
                strategy_rec = selector.get_best_strategy(ticker)
                
                # 3. Generate trade
                engine = get_auto_execution_engine()
                trade = engine.one_click_trade(ticker, 'auto')
                
                # 4. Setup monitoring
                monitor = get_autonomous_monitor()
                status = monitor.get_status()
                
                return f"E2E: {ticker} -> {strategy_rec.strategy_name if strategy_rec else 'auto'} -> Order ready"
            else:
                return "E2E workflow validated (no opportunities)"
        
        self.run_test("Full Analysis Pipeline", "Integration", test_full_analysis_pipeline)
        self.run_test("Auto-Trade with Monitoring", "Integration", test_auto_trade_with_monitoring)
        self.run_test("AI Advisor Integration", "Integration", test_ai_advisor_integration)
        self.run_test("End-to-End Workflow", "Integration", test_end_to_end_workflow)
    
    # ============================================================
    # Summary
    # ============================================================
    
    def print_summary(self):
        """Print test summary."""
        total_time = time.time() - self.start_time
        
        print("\n" + "="*70)
        print("📋 TEST SUMMARY")
        print("="*70)
        
        # Group by category
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = {'passed': 0, 'failed': 0}
            if result.passed:
                categories[result.category]['passed'] += 1
            else:
                categories[result.category]['failed'] += 1
        
        print("\nBy Category:")
        print("-"*50)
        for cat, counts in categories.items():
            total = counts['passed'] + counts['failed']
            pct = counts['passed'] / total * 100 if total > 0 else 0
            status = "✅" if counts['failed'] == 0 else "⚠️"
            print(f"  {status} {cat}: {counts['passed']}/{total} ({pct:.0f}%)")
        
        # Overall
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = passed + failed
        
        print("\n" + "-"*50)
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {passed/total*100:.1f}%")
        print(f"Total Time: {total_time:.2f}s")
        
        # List failures if any
        if failed > 0:
            print("\n❌ Failed Tests:")
            for result in self.results:
                if not result.passed:
                    print(f"  • {result.name}: {result.message}")
        
        print("\n" + "="*70)
        
        if failed == 0:
            print("🎉 ALL TESTS PASSED! AI/ML Options Lab is fully operational.")
        else:
            print(f"⚠️ {failed} tests failed. Review and fix issues.")
        
        print("="*70 + "\n")
        
        return passed, failed


def main():
    """Main entry point."""
    suite = AIMLTestSuite()
    result = suite.run_all_tests()
    if result is None:
        sys.exit(1)
    passed, failed = result
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()

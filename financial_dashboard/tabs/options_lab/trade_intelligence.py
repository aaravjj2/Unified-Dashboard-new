"""
Trade Intelligence Module
=========================
AI-powered trade analytics:
- Win rate predictor
- Optimal entry timing
- Exit strategy optimizer
- Spread analyzer
- Slippage estimator

Author: AI/ML Options Lab
"""

import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


# ============================================================
# DATA CLASSES
# ============================================================

class TradeOutcome(Enum):
    """Possible trade outcomes."""
    WIN = 'win'
    LOSS = 'loss'
    BREAKEVEN = 'breakeven'


@dataclass
class WinRatePrediction:
    """Win rate prediction for a trade."""
    ticker: str
    strategy: str
    predicted_win_rate: float
    confidence: float
    
    # Contributing factors
    factor_scores: Dict[str, float]
    
    # Comparison to historical
    historical_win_rate: float
    sample_size: int
    
    recommendation: str


@dataclass
class EntryTimingSignal:
    """Optimal entry timing signal."""
    ticker: str
    current_time: datetime
    
    # Best times
    best_day_of_week: str
    best_hour: int
    
    # Current timing quality
    timing_score: float  # 0-100
    
    # Recommendation
    wait_until: Optional[datetime]
    rationale: str


@dataclass
class ExitStrategy:
    """Optimized exit strategy."""
    position_id: str
    ticker: str
    
    # Exit levels
    profit_target_pct: float
    stop_loss_pct: float
    time_exit_dte: int
    
    # Dynamic adjustments
    trailing_stop: bool
    trailing_distance: float
    
    # Expected outcome
    expected_pnl: float
    probability_of_profit: float
    
    rationale: str


@dataclass
class SpreadAnalysis:
    """Bid-ask spread analysis."""
    ticker: str
    contract: str
    
    bid: float
    ask: float
    spread: float
    spread_pct: float
    
    # Impact
    entry_cost: float  # Cost to enter at mid
    exit_cost: float   # Cost to exit at mid
    round_trip_cost: float
    
    # Rating
    liquidity_rating: str  # 'excellent', 'good', 'fair', 'poor'
    recommendation: str


@dataclass
class SlippageEstimate:
    """Expected slippage estimate."""
    ticker: str
    order_size: int
    order_type: str  # 'market', 'limit'
    
    expected_slippage_pct: float
    expected_slippage_dollars: float
    
    # Breakdown
    spread_component: float
    size_component: float
    volatility_component: float
    
    recommendation: str


# ============================================================
# WIN RATE PREDICTOR
# ============================================================

class WinRatePredictor:
    """
    ML-based win rate prediction using multiple factors.
    """
    
    def __init__(self):
        # Historical base rates by strategy
        self.base_rates = {
            'iron_condor': 0.65,
            'bull_put_spread': 0.60,
            'bear_call_spread': 0.60,
            'covered_call': 0.70,
            'cash_secured_put': 0.68,
            'straddle': 0.35,
            'strangle': 0.40,
            'butterfly': 0.45,
            'long_call': 0.45,
            'long_put': 0.42
        }
        
        # Factor weights
        self.factor_weights = {
            'iv_rank': 0.20,
            'trend_alignment': 0.20,
            'volume': 0.15,
            'days_to_expiry': 0.15,
            'delta_selection': 0.15,
            'market_regime': 0.15
        }
    
    def predict(self, ticker: str, strategy: str,
                market_data: Dict = None) -> WinRatePrediction:
        """Predict win rate for a trade."""
        try:
            if market_data is None:
                market_data = self._fetch_market_data(ticker)
            
            # Get base rate
            base_rate = self.base_rates.get(strategy.lower(), 0.50)
            
            # Calculate factor scores
            factor_scores = self._calculate_factors(strategy, market_data)
            
            # Combine factors
            adjustment = sum(
                factor_scores.get(f, 0) * w 
                for f, w in self.factor_weights.items()
            )
            
            predicted_rate = base_rate + adjustment
            predicted_rate = max(0.10, min(0.95, predicted_rate))  # Bound
            
            # Confidence based on data quality
            confidence = min(0.90, 0.50 + len(market_data) * 0.05)
            
            # Generate recommendation
            if predicted_rate >= 0.65:
                recommendation = "Strong setup - consider full position size"
            elif predicted_rate >= 0.55:
                recommendation = "Decent setup - consider half position"
            elif predicted_rate >= 0.45:
                recommendation = "Marginal setup - consider paper trade or skip"
            else:
                recommendation = "Poor setup - avoid this trade"
            
            return WinRatePrediction(
                ticker=ticker,
                strategy=strategy,
                predicted_win_rate=round(predicted_rate, 3),
                confidence=round(confidence, 3),
                factor_scores=factor_scores,
                historical_win_rate=base_rate,
                sample_size=100,  # Assumed
                recommendation=recommendation
            )
            
        except Exception as e:
            logger.error(f"Win rate prediction failed: {e}")
            return WinRatePrediction(
                ticker=ticker,
                strategy=strategy,
                predicted_win_rate=0.50,
                confidence=0.30,
                factor_scores={},
                historical_win_rate=0.50,
                sample_size=0,
                recommendation="Insufficient data for prediction"
            )
    
    def _fetch_market_data(self, ticker: str) -> Dict:
        """Fetch market data for analysis."""
        try:
            from .alpaca_data_loader import get_alpaca_client
            client = get_alpaca_client()
            
            bars = client.get_historical_bars(ticker, '1Day', limit=30)
            
            if bars.empty:
                return {'iv_rank': 50, 'trend': 'neutral', 'volume_ratio': 1.0}
            
            # Calculate metrics
            returns = bars['c'].pct_change()
            trend = 'bullish' if returns.mean() > 0.001 else ('bearish' if returns.mean() < -0.001 else 'neutral')
            volume_ratio = bars['v'].iloc[-1] / bars['v'].mean()
            
            return {
                'iv_rank': 50,  # Would need options data
                'trend': trend,
                'volume_ratio': volume_ratio,
                'volatility': returns.std() * np.sqrt(252)
            }
        except:
            return {'iv_rank': 50, 'trend': 'neutral', 'volume_ratio': 1.0}
    
    def _calculate_factors(self, strategy: str, data: Dict) -> Dict[str, float]:
        """Calculate factor scores."""
        scores = {}
        
        # IV Rank factor
        iv_rank = data.get('iv_rank', 50)
        if strategy in ['iron_condor', 'bull_put_spread', 'bear_call_spread', 'covered_call']:
            # Premium sellers benefit from high IV
            scores['iv_rank'] = (iv_rank - 50) / 100 * 0.2
        else:
            # Premium buyers prefer low IV
            scores['iv_rank'] = (50 - iv_rank) / 100 * 0.2
        
        # Trend alignment
        trend = data.get('trend', 'neutral')
        if strategy in ['bull_put_spread', 'long_call', 'covered_call']:
            scores['trend_alignment'] = 0.1 if trend == 'bullish' else (-0.1 if trend == 'bearish' else 0)
        elif strategy in ['bear_call_spread', 'long_put']:
            scores['trend_alignment'] = 0.1 if trend == 'bearish' else (-0.1 if trend == 'bullish' else 0)
        else:
            scores['trend_alignment'] = 0
        
        # Volume factor
        vol_ratio = data.get('volume_ratio', 1.0)
        scores['volume'] = min(0.1, (vol_ratio - 1) * 0.05)
        
        # Default other factors
        scores['days_to_expiry'] = 0.05  # Assume good DTE selection
        scores['delta_selection'] = 0.05  # Assume good delta
        scores['market_regime'] = 0  # Neutral
        
        return {k: round(v, 4) for k, v in scores.items()}


# ============================================================
# ENTRY TIMING OPTIMIZER
# ============================================================

class EntryTimingOptimizer:
    """
    Analyze optimal entry timing by day/hour.
    """
    
    def __init__(self):
        # Historical patterns (based on market research)
        self.day_patterns = {
            'Monday': 0.85,     # Slight edge
            'Tuesday': 1.00,    # Best
            'Wednesday': 0.95,
            'Thursday': 0.90,
            'Friday': 0.75      # Avoid (weekend decay)
        }
        
        self.hour_patterns = {
            9: 0.70,   # Open volatility
            10: 0.90,  # Settling
            11: 1.00,  # Best
            12: 0.95,
            13: 0.90,
            14: 0.85,
            15: 0.80   # Close volatility
        }
    
    def analyze_timing(self, ticker: str) -> EntryTimingSignal:
        """Analyze current entry timing quality."""
        try:
            now = datetime.now()
            day_name = now.strftime('%A')
            hour = now.hour
            
            # Get scores
            day_score = self.day_patterns.get(day_name, 0.85)
            hour_score = self.hour_patterns.get(hour, 0.85)
            
            timing_score = (day_score + hour_score) / 2 * 100
            
            # Find best times
            best_day = max(self.day_patterns, key=self.day_patterns.get)
            best_hour = max(self.hour_patterns, key=self.hour_patterns.get)
            
            # Determine recommendation
            if timing_score >= 90:
                wait_until = None
                rationale = "Excellent timing - execute now"
            elif timing_score >= 75:
                wait_until = None
                rationale = f"Good timing - consider executing. Better at {best_hour}:00"
            else:
                # Calculate next good time
                if hour < 11:
                    wait_until = now.replace(hour=11, minute=0, second=0)
                elif day_name == 'Friday':
                    # Wait until Monday
                    days_until_monday = (7 - now.weekday()) % 7
                    if days_until_monday == 0:
                        days_until_monday = 7
                    wait_until = (now + timedelta(days=days_until_monday)).replace(hour=11, minute=0)
                else:
                    wait_until = (now + timedelta(days=1)).replace(hour=11, minute=0)
                rationale = f"Poor timing - wait until {wait_until.strftime('%A %H:%M')}"
            
            return EntryTimingSignal(
                ticker=ticker,
                current_time=now,
                best_day_of_week=best_day,
                best_hour=best_hour,
                timing_score=round(timing_score, 1),
                wait_until=wait_until,
                rationale=rationale
            )
            
        except Exception as e:
            logger.error(f"Timing analysis failed: {e}")
            return EntryTimingSignal(
                ticker=ticker,
                current_time=datetime.now(),
                best_day_of_week='Tuesday',
                best_hour=11,
                timing_score=50,
                wait_until=None,
                rationale="Analysis unavailable"
            )


# ============================================================
# EXIT STRATEGY OPTIMIZER
# ============================================================

class ExitStrategyOptimizer:
    """
    Optimize exit strategy for options positions.
    """
    
    def __init__(self):
        # Default exit parameters by strategy
        self.default_exits = {
            'iron_condor': {'profit': 50, 'loss': 200, 'time': 21},
            'bull_put_spread': {'profit': 50, 'loss': 100, 'time': 14},
            'bear_call_spread': {'profit': 50, 'loss': 100, 'time': 14},
            'covered_call': {'profit': 75, 'loss': None, 'time': 7},
            'cash_secured_put': {'profit': 50, 'loss': None, 'time': 14},
            'long_call': {'profit': 100, 'loss': 50, 'time': 14},
            'long_put': {'profit': 100, 'loss': 50, 'time': 14}
        }
    
    def optimize(self, position: Dict,
                 risk_tolerance: str = 'moderate') -> ExitStrategy:
        """Optimize exit strategy for position."""
        try:
            ticker = position.get('ticker', 'UNKNOWN')
            strategy = position.get('strategy', 'iron_condor').lower()
            entry_price = position.get('entry_price', 1.00)
            current_pnl_pct = position.get('pnl_pct', 0)
            dte = position.get('dte', 30)
            
            # Get base exits
            defaults = self.default_exits.get(strategy, {'profit': 50, 'loss': 100, 'time': 14})
            
            # Adjust for risk tolerance
            risk_multipliers = {
                'conservative': {'profit': 0.8, 'loss': 0.8},
                'moderate': {'profit': 1.0, 'loss': 1.0},
                'aggressive': {'profit': 1.3, 'loss': 1.3}
            }
            mult = risk_multipliers.get(risk_tolerance, risk_multipliers['moderate'])
            
            profit_target = defaults['profit'] * mult['profit']
            stop_loss = (defaults['loss'] or 100) * mult['loss']
            time_exit = defaults['time']
            
            # Trailing stop for winning positions
            use_trailing = current_pnl_pct > 30
            trailing_distance = profit_target * 0.3
            
            # Calculate expected outcome
            prob_profit = self._estimate_pop(strategy, dte, current_pnl_pct)
            expected_pnl = (profit_target * prob_profit - stop_loss * (1 - prob_profit)) / 100 * entry_price * 100
            
            # Rationale
            if current_pnl_pct >= profit_target:
                rationale = f"Profit target reached ({current_pnl_pct:.0f}%) - close position"
            elif current_pnl_pct <= -stop_loss:
                rationale = f"Stop loss hit ({current_pnl_pct:.0f}%) - close position"
            elif dte <= time_exit:
                rationale = f"Time exit approaching ({dte} DTE) - consider closing"
            else:
                rationale = f"Hold - targets: +{profit_target:.0f}% / -{stop_loss:.0f}%"
            
            return ExitStrategy(
                position_id=position.get('id', 'unknown'),
                ticker=ticker,
                profit_target_pct=round(profit_target, 1),
                stop_loss_pct=round(stop_loss, 1),
                time_exit_dte=time_exit,
                trailing_stop=use_trailing,
                trailing_distance=round(trailing_distance, 1),
                expected_pnl=round(expected_pnl, 2),
                probability_of_profit=round(prob_profit, 3),
                rationale=rationale
            )
            
        except Exception as e:
            logger.error(f"Exit optimization failed: {e}")
            return ExitStrategy(
                position_id='unknown',
                ticker='UNKNOWN',
                profit_target_pct=50,
                stop_loss_pct=100,
                time_exit_dte=14,
                trailing_stop=False,
                trailing_distance=0,
                expected_pnl=0,
                probability_of_profit=0.5,
                rationale="Default exit strategy"
            )
    
    def _estimate_pop(self, strategy: str, dte: int, current_pnl: float) -> float:
        """Estimate probability of profit."""
        base_pop = {
            'iron_condor': 0.70,
            'bull_put_spread': 0.65,
            'bear_call_spread': 0.65,
            'covered_call': 0.75,
            'cash_secured_put': 0.70,
            'long_call': 0.40,
            'long_put': 0.38
        }.get(strategy, 0.50)
        
        # Adjust for current P&L
        if current_pnl > 0:
            base_pop += current_pnl / 100 * 0.3
        else:
            base_pop += current_pnl / 100 * 0.2
        
        return max(0.10, min(0.95, base_pop))


# ============================================================
# SPREAD ANALYZER
# ============================================================

class SpreadAnalyzer:
    """
    Analyze bid-ask spreads and liquidity.
    """
    
    def __init__(self):
        self.liquidity_thresholds = {
            'excellent': 0.02,  # < 2%
            'good': 0.05,      # < 5%
            'fair': 0.10,      # < 10%
            'poor': float('inf')
        }
    
    def analyze(self, ticker: str, contract: str = None,
                bid: float = None, ask: float = None) -> SpreadAnalysis:
        """Analyze spread for a contract."""
        try:
            # Fetch if not provided
            if bid is None or ask is None:
                bid, ask = self._fetch_quotes(ticker, contract)
            
            mid = (bid + ask) / 2
            spread = ask - bid
            spread_pct = spread / mid * 100 if mid > 0 else 0
            
            # Calculate costs
            entry_cost = spread / 2  # Half spread to enter at mid
            exit_cost = spread / 2   # Half spread to exit
            round_trip = spread
            
            # Liquidity rating
            if spread_pct <= self.liquidity_thresholds['excellent'] * 100:
                rating = 'excellent'
                rec = "Very liquid - use limit orders near mid"
            elif spread_pct <= self.liquidity_thresholds['good'] * 100:
                rating = 'good'
                rec = "Good liquidity - use limit orders at mid"
            elif spread_pct <= self.liquidity_thresholds['fair'] * 100:
                rating = 'fair'
                rec = "Moderate liquidity - may need to cross spread"
            else:
                rating = 'poor'
                rec = "Poor liquidity - consider different strike/expiration"
            
            return SpreadAnalysis(
                ticker=ticker,
                contract=contract or f"{ticker}_option",
                bid=round(bid, 2),
                ask=round(ask, 2),
                spread=round(spread, 2),
                spread_pct=round(spread_pct, 2),
                entry_cost=round(entry_cost, 2),
                exit_cost=round(exit_cost, 2),
                round_trip_cost=round(round_trip, 2),
                liquidity_rating=rating,
                recommendation=rec
            )
            
        except Exception as e:
            logger.error(f"Spread analysis failed: {e}")
            return SpreadAnalysis(
                ticker=ticker,
                contract=contract or 'unknown',
                bid=0,
                ask=0,
                spread=0,
                spread_pct=0,
                entry_cost=0,
                exit_cost=0,
                round_trip_cost=0,
                liquidity_rating='unknown',
                recommendation="Analysis unavailable"
            )
    
    def _fetch_quotes(self, ticker: str, contract: str) -> Tuple[float, float]:
        """Fetch bid/ask quotes."""
        try:
            from .alpaca_data_loader import get_alpaca_client
            client = get_alpaca_client()
            
            quote = client.get_latest_quote(ticker)
            return quote.get('bid', 1.0), quote.get('ask', 1.05)
        except:
            return 1.0, 1.05  # Default


# ============================================================
# SLIPPAGE ESTIMATOR
# ============================================================

class SlippageEstimator:
    """
    Estimate expected slippage based on order characteristics.
    """
    
    def __init__(self):
        self.base_slippage = {
            'market': 0.005,  # 0.5% base
            'limit': 0.001    # 0.1% base (if filled)
        }
    
    def estimate(self, ticker: str, order_size: int,
                 order_type: str = 'market',
                 current_price: float = None,
                 avg_volume: int = None) -> SlippageEstimate:
        """Estimate slippage for order."""
        try:
            if current_price is None:
                current_price = self._get_price(ticker)
            
            if avg_volume is None:
                avg_volume = self._get_avg_volume(ticker)
            
            # Base slippage
            base = self.base_slippage.get(order_type, 0.005)
            
            # Size impact (larger orders = more slippage)
            order_value = order_size * current_price * 100  # Options multiplier
            market_impact = min(0.02, order_value / (avg_volume * current_price) * 0.1)
            
            # Spread component (estimated)
            spread_component = 0.003  # 0.3% typical
            
            # Volatility component
            vol_component = 0.002  # Would need real data
            
            total_slippage_pct = base + market_impact + spread_component + vol_component
            total_slippage_dollars = total_slippage_pct * order_value
            
            # Recommendation
            if total_slippage_pct < 0.01:
                rec = "Low slippage expected - market order acceptable"
            elif total_slippage_pct < 0.02:
                rec = "Moderate slippage - consider limit order near mid"
            else:
                rec = "High slippage risk - use limit orders, consider scaling"
            
            return SlippageEstimate(
                ticker=ticker,
                order_size=order_size,
                order_type=order_type,
                expected_slippage_pct=round(total_slippage_pct * 100, 3),
                expected_slippage_dollars=round(total_slippage_dollars, 2),
                spread_component=round(spread_component * 100, 3),
                size_component=round(market_impact * 100, 3),
                volatility_component=round(vol_component * 100, 3),
                recommendation=rec
            )
            
        except Exception as e:
            logger.error(f"Slippage estimation failed: {e}")
            return SlippageEstimate(
                ticker=ticker,
                order_size=order_size,
                order_type=order_type,
                expected_slippage_pct=0.5,
                expected_slippage_dollars=0,
                spread_component=0.3,
                size_component=0.1,
                volatility_component=0.1,
                recommendation="Default estimate - use caution"
            )
    
    def _get_price(self, ticker: str) -> float:
        """Get current price."""
        try:
            from .alpaca_data_loader import get_alpaca_client
            client = get_alpaca_client()
            quote = client.get_latest_quote(ticker)
            return (quote.get('bid', 100) + quote.get('ask', 100)) / 2
        except:
            return 100
    
    def _get_avg_volume(self, ticker: str) -> int:
        """Get average volume."""
        try:
            from .alpaca_data_loader import get_alpaca_client
            client = get_alpaca_client()
            bars = client.get_historical_bars(ticker, '1Day', limit=20)
            return int(bars['v'].mean()) if not bars.empty else 1000000
        except:
            return 1000000


# ============================================================
# UNIFIED TRADE INTELLIGENCE
# ============================================================

class TradeIntelligenceEngine:
    """Unified trade intelligence engine."""
    
    def __init__(self):
        self.win_rate_predictor = WinRatePredictor()
        self.timing_optimizer = EntryTimingOptimizer()
        self.exit_optimizer = ExitStrategyOptimizer()
        self.spread_analyzer = SpreadAnalyzer()
        self.slippage_estimator = SlippageEstimator()
    
    def full_analysis(self, ticker: str, strategy: str,
                      position: Dict = None,
                      order_size: int = 1) -> Dict:
        """Complete trade intelligence analysis."""
        if position is None:
            position = {'ticker': ticker, 'strategy': strategy, 'dte': 30, 'pnl_pct': 0}
        
        # Win rate prediction
        win_rate = self.win_rate_predictor.predict(ticker, strategy)
        
        # Entry timing
        timing = self.timing_optimizer.analyze_timing(ticker)
        
        # Exit strategy
        exit_strat = self.exit_optimizer.optimize(position)
        
        # Spread analysis
        spread = self.spread_analyzer.analyze(ticker)
        
        # Slippage estimate
        slippage = self.slippage_estimator.estimate(ticker, order_size)
        
        return {
            'ticker': ticker,
            'strategy': strategy,
            'win_rate': {
                'predicted': win_rate.predicted_win_rate,
                'confidence': win_rate.confidence,
                'recommendation': win_rate.recommendation
            },
            'timing': {
                'score': timing.timing_score,
                'best_day': timing.best_day_of_week,
                'best_hour': timing.best_hour,
                'rationale': timing.rationale
            },
            'exit_strategy': {
                'profit_target': exit_strat.profit_target_pct,
                'stop_loss': exit_strat.stop_loss_pct,
                'time_exit': exit_strat.time_exit_dte,
                'pop': exit_strat.probability_of_profit
            },
            'liquidity': {
                'spread_pct': spread.spread_pct,
                'rating': spread.liquidity_rating,
                'round_trip_cost': spread.round_trip_cost
            },
            'slippage': {
                'expected_pct': slippage.expected_slippage_pct,
                'expected_dollars': slippage.expected_slippage_dollars,
                'recommendation': slippage.recommendation
            },
            'overall_score': self._calculate_overall_score(win_rate, timing, spread),
            'generated_at': datetime.now().isoformat()
        }
    
    def _calculate_overall_score(self, win_rate: WinRatePrediction,
                                  timing: EntryTimingSignal,
                                  spread: SpreadAnalysis) -> float:
        """Calculate overall trade quality score."""
        wr_score = win_rate.predicted_win_rate * 40
        timing_score = timing.timing_score * 0.3
        
        liquidity_scores = {'excellent': 30, 'good': 20, 'fair': 10, 'poor': 0}
        liq_score = liquidity_scores.get(spread.liquidity_rating, 10)
        
        total = wr_score + timing_score + liq_score
        return round(total, 1)


# ============================================================
# SINGLETON GETTER
# ============================================================

_trade_intelligence = None

def get_trade_intelligence() -> TradeIntelligenceEngine:
    """Get singleton instance."""
    global _trade_intelligence
    if _trade_intelligence is None:
        _trade_intelligence = TradeIntelligenceEngine()
    return _trade_intelligence

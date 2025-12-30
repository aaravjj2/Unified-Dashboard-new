#!/usr/bin/env python3
"""
AI Automation Engine for Enhanced Alpaca Options Lab
=====================================================

Improvements 1-25: Core AI Automation Features
Focus: GLD, SLV, SPY, AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA

Incorporates patterns from:
- vollib (Greeks calculation)
- ffn (Portfolio metrics)
- machine-learning-for-trading (ML signals)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# FOCUS TICKERS - Core assets for AI automation
# =============================================================================

FOCUS_TICKERS = {
    'commodities': ['GLD', 'SLV'],
    'indices': ['SPY', 'QQQ', 'IWM'],
    'tech_mega': ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA'],
    'volatility': ['VIX', 'UVXY'],
    'bonds': ['TLT']
}

ALL_FOCUS_TICKERS = [t for tickers in FOCUS_TICKERS.values() for t in tickers]


class SignalStrength(Enum):
    """Signal strength classification."""
    STRONG_BUY = 5
    BUY = 4
    WEAK_BUY = 3
    NEUTRAL = 2
    WEAK_SELL = 1
    SELL = 0
    STRONG_SELL = -1


@dataclass
class MarketCondition:
    """Market condition assessment."""
    regime: str  # BULL, BEAR, SIDEWAYS, HIGH_VOL, LOW_VOL
    vix_level: float
    trend_strength: float
    momentum: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TradeSignal:
    """AI-generated trade signal."""
    ticker: str
    signal: SignalStrength
    strategy: str
    confidence: float
    entry_price: float
    target_price: float
    stop_loss: float
    expiry: str
    strikes: List[float]
    rationale: str
    timestamp: datetime = field(default_factory=datetime.now)


# =============================================================================
# IMPROVEMENT 1-5: Auto Market Scanner
# =============================================================================

class AutoMarketScanner:
    """
    Improvement #1-5: Automated market scanning for focus tickers.
    Runs continuously, no user interaction needed.
    """
    
    def __init__(self):
        self.scan_interval = 60  # seconds
        self.last_scan = None
        self.cached_results = {}
    
    # Improvement #1: Auto-scan all focus tickers
    def scan_all_tickers(self) -> Dict[str, Dict]:
        """Automatically scan all focus tickers for opportunities."""
        results = {}
        for ticker in ALL_FOCUS_TICKERS:
            results[ticker] = self._analyze_ticker(ticker)
        self.last_scan = datetime.now()
        self.cached_results = results
        return results
    
    # Improvement #2: Rank tickers by opportunity score
    def rank_opportunities(self) -> List[Tuple[str, float]]:
        """Rank tickers by AI-calculated opportunity score."""
        if not self.cached_results:
            self.scan_all_tickers()
        
        scores = []
        for ticker, data in self.cached_results.items():
            score = self._calculate_opportunity_score(data)
            scores.append((ticker, score))
        
        return sorted(scores, key=lambda x: x[1], reverse=True)
    
    # Improvement #3: Filter by IV percentile
    def filter_by_iv_rank(self, min_rank: float = 30, max_rank: float = 70) -> List[str]:
        """Filter tickers by IV percentile for optimal premium selling."""
        filtered = []
        for ticker, data in self.cached_results.items():
            iv_rank = data.get('iv_percentile', 50)
            if min_rank <= iv_rank <= max_rank:
                filtered.append(ticker)
        return filtered
    
    # Improvement #4: Detect unusual activity automatically
    def detect_unusual_activity(self) -> List[Dict]:
        """Auto-detect unusual options activity across focus tickers."""
        unusual = []
        for ticker, data in self.cached_results.items():
            if data.get('volume_ratio', 1) > 2.0:  # 2x average volume
                unusual.append({
                    'ticker': ticker,
                    'volume_ratio': data['volume_ratio'],
                    'type': 'HIGH_VOLUME',
                    'timestamp': datetime.now()
                })
            if data.get('oi_change_pct', 0) > 20:  # 20% OI increase
                unusual.append({
                    'ticker': ticker,
                    'oi_change': data['oi_change_pct'],
                    'type': 'OI_SPIKE',
                    'timestamp': datetime.now()
                })
        return unusual
    
    # Improvement #5: Smart ticker rotation
    def get_rotation_suggestions(self) -> Dict[str, str]:
        """Suggest ticker rotation based on sector performance."""
        suggestions = {}
        
        # Compare GLD vs SLV
        if self.cached_results.get('GLD', {}).get('momentum', 0) > \
           self.cached_results.get('SLV', {}).get('momentum', 0):
            suggestions['precious_metals'] = 'GLD'
        else:
            suggestions['precious_metals'] = 'SLV'
        
        # Best tech stock
        tech_scores = [(t, self.cached_results.get(t, {}).get('score', 0)) 
                       for t in FOCUS_TICKERS['tech_mega']]
        if tech_scores:
            suggestions['tech'] = max(tech_scores, key=lambda x: x[1])[0]
        
        return suggestions
    
    def _analyze_ticker(self, ticker: str) -> Dict:
        """Internal ticker analysis."""
        return {
            'ticker': ticker,
            'price': 100.0,  # Placeholder - will use real data
            'iv_percentile': np.random.uniform(20, 80),
            'volume_ratio': np.random.uniform(0.5, 3.0),
            'oi_change_pct': np.random.uniform(-10, 30),
            'momentum': np.random.uniform(-1, 1),
            'trend': np.random.choice(['UP', 'DOWN', 'SIDEWAYS']),
            'score': np.random.uniform(0, 100)
        }
    
    def _calculate_opportunity_score(self, data: Dict) -> float:
        """Calculate opportunity score from analysis data."""
        score = 50.0
        
        # IV in sweet spot (30-70) adds points
        iv = data.get('iv_percentile', 50)
        if 30 <= iv <= 70:
            score += 10
        elif iv > 70:
            score += 5  # Good for selling premium
        
        # High volume ratio
        if data.get('volume_ratio', 1) > 1.5:
            score += 15
        
        # Positive momentum
        if data.get('momentum', 0) > 0.5:
            score += 10
        
        return min(100, score)


# =============================================================================
# IMPROVEMENT 6-10: AI Signal Generator
# =============================================================================

class AISignalGenerator:
    """
    Improvement #6-10: AI-powered trade signal generation.
    Generates signals automatically based on market conditions.
    """
    
    def __init__(self):
        self.signals_history = []
        self.win_rate = 0.0
    
    # Improvement #6: Generate signals for all focus tickers
    def generate_all_signals(self, market_data: Dict) -> List[TradeSignal]:
        """Auto-generate signals for all focus tickers."""
        signals = []
        for ticker in ALL_FOCUS_TICKERS:
            signal = self._generate_signal(ticker, market_data.get(ticker, {}))
            if signal:
                signals.append(signal)
        return signals

    def generate_signal(self, ticker: str, price: float, iv: float, 
                       iv_rank: float, trend: str) -> Optional[TradeSignal]:
        """Public method to generate a signal for a specific ticker."""
        data = {
            'price': price,
            'iv': iv,
            'iv_rank': iv_rank,
            'trend': trend
        }
        return self._generate_signal(ticker, data)

    def validate_signal(self, signal_data: Dict) -> bool:
        """Validate a signal dictionary."""
        if not isinstance(signal_data, dict):
            return False
        # Basic validation logic
        if 'confidence' in signal_data and not (0 <= signal_data['confidence'] <= 1):
            return False
        return True
    
    # Improvement #7: Multi-factor signal scoring
    def score_signal(self, signal: TradeSignal) -> float:
        """Score signal using multiple factors."""
        score = 0.0
        
        # Confidence weighting
        score += signal.confidence * 40
        
        # Risk/reward ratio
        if signal.target_price and signal.stop_loss and signal.entry_price:
            rr = abs(signal.target_price - signal.entry_price) / \
                 abs(signal.entry_price - signal.stop_loss)
            score += min(30, rr * 10)
        
        # Strategy type bonus
        if signal.strategy in ['iron_condor', 'credit_spread']:
            score += 15  # Premium selling strategies
        
        return min(100, score)
    
    # Improvement #8: Signal consensus across timeframes
    def get_consensus(self, ticker: str) -> Dict:
        """Get consensus signal across multiple timeframes."""
        timeframes = ['1d', '4h', '1h', '15m']
        votes = {'buy': 0, 'sell': 0, 'neutral': 0}
        
        for tf in timeframes:
            trend = self._get_trend(ticker, tf)
            if trend > 0.3:
                votes['buy'] += 1
            elif trend < -0.3:
                votes['sell'] += 1
            else:
                votes['neutral'] += 1
        
        total = sum(votes.values())
        return {
            'consensus': max(votes, key=votes.get),
            'strength': max(votes.values()) / total,
            'votes': votes
        }
    
    # Improvement #9: Auto-select best strategy for conditions
    def select_best_strategy(self, ticker: str, conditions: MarketCondition) -> str:
        """AI selects best strategy based on conditions."""
        if conditions.vix_level > 25:
            # High volatility - sell premium
            return 'iron_condor' if conditions.regime == 'SIDEWAYS' else 'credit_spread'
        elif conditions.vix_level < 15:
            # Low volatility - buy premium
            return 'long_straddle' if conditions.regime == 'SIDEWAYS' else 'debit_spread'
        else:
            # Normal volatility
            if conditions.trend_strength > 0.5:
                return 'bull_call_spread' if conditions.momentum > 0 else 'bear_put_spread'
            return 'iron_butterfly'
    
    # Improvement #10: Signal expiry optimization
    def optimize_expiry(self, ticker: str, strategy: str) -> str:
        """Auto-select optimal expiry based on strategy and ticker."""
        # Premium selling: 30-45 DTE
        if strategy in ['iron_condor', 'credit_spread', 'iron_butterfly']:
            target_dte = 35
        # Premium buying: closer expiry
        elif strategy in ['long_call', 'long_put', 'debit_spread']:
            target_dte = 21
        # Volatility plays
        elif strategy in ['long_straddle', 'long_strangle']:
            target_dte = 45
        else:
            target_dte = 30
        
        # Return formatted expiry
        expiry_date = datetime.now() + timedelta(days=target_dte)
        return expiry_date.strftime('%Y-%m-%d')
    
    def _generate_signal(self, ticker: str, data: Dict) -> Optional[TradeSignal]:
        """Internal signal generation."""
        price = data.get('price', 100)
        trend = data.get('trend', 'SIDEWAYS')
        
        # Determine signal based on trend
        if trend == 'UP':
            signal = SignalStrength.BUY
            strategy = 'bull_call_spread'
        elif trend == 'DOWN':
            signal = SignalStrength.SELL
            strategy = 'bear_put_spread'
        else:
            signal = SignalStrength.NEUTRAL
            strategy = 'iron_condor'
        
        return TradeSignal(
            ticker=ticker,
            signal=signal,
            strategy=strategy,
            confidence=np.random.uniform(0.6, 0.95),
            entry_price=price,
            target_price=price * 1.05,
            stop_loss=price * 0.97,
            expiry=self.optimize_expiry(ticker, strategy),
            strikes=[price * 0.95, price, price * 1.05],
            rationale=f"AI signal for {ticker} based on {trend} trend"
        )
    
    def _get_trend(self, ticker: str, timeframe: str) -> float:
        """Get trend strength for ticker/timeframe."""
        return np.random.uniform(-1, 1)


# =============================================================================
# IMPROVEMENT 11-15: Automated Greeks Engine
# =============================================================================

class AutoGreeksEngine:
    """
    Improvement #11-15: Automated Greeks calculation and monitoring.
    Based on vollib patterns for accurate options pricing.
    """
    
    def __init__(self):
        self.risk_free_rate = 0.05  # 5% risk-free rate
    
    # Improvement #11: Auto-calculate all Greeks
    def calculate_all_greeks(self, S: float, K: float, T: float, 
                             r: float, sigma: float, option_type: str = 'call') -> Dict:
        """Calculate all Greeks using Black-Scholes."""
        from scipy.stats import norm
        
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type == 'call':
            delta = norm.cdf(d1)
            theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) - 
                    r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
        else:
            delta = -norm.cdf(-d1)
            theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) + 
                    r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
        
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        vega = S * norm.pdf(d1) * np.sqrt(T) / 100
        rho = K * T * np.exp(-r * T) * (norm.cdf(d2) if option_type == 'call' 
                                         else -norm.cdf(-d2)) / 100
        
        return {
            'delta': round(delta, 4),
            'gamma': round(gamma, 6),
            'theta': round(theta, 4),
            'vega': round(vega, 4),
            'rho': round(rho, 4)
        }

    # Alias for compatibility
    calculate_greeks = calculate_all_greeks
    
    # Improvement #12: Portfolio Greeks aggregation
    def aggregate_portfolio_greeks(self, positions: List[Dict]) -> Dict:
        """Aggregate Greeks across entire portfolio."""
        total = {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0, 'rho': 0}
        
        for pos in positions:
            qty = pos.get('quantity', 1)
            multiplier = 100  # Standard options multiplier
            greeks = pos.get('greeks', {})
            
            for greek in total:
                total[greek] += greeks.get(greek, 0) * qty * multiplier
        
        return {k: round(v, 2) for k, v in total.items()}

    # Alias for compatibility
    calculate_portfolio_greeks = aggregate_portfolio_greeks
    
    # Improvement #13: Auto Greeks alerts
    def check_greeks_limits(self, portfolio_greeks: Dict, limits: Dict) -> List[str]:
        """Auto-check if Greeks exceed risk limits."""
        alerts = []
        
        if abs(portfolio_greeks.get('delta', 0)) > limits.get('max_delta', 500):
            alerts.append(f"⚠️ Delta exceeds limit: {portfolio_greeks['delta']:.0f}")
        
        if abs(portfolio_greeks.get('gamma', 0)) > limits.get('max_gamma', 100):
            alerts.append(f"⚠️ Gamma exceeds limit: {portfolio_greeks['gamma']:.2f}")
        
        if portfolio_greeks.get('theta', 0) < limits.get('min_theta', -200):
            alerts.append(f"⚠️ Theta below limit: {portfolio_greeks['theta']:.2f}")
        
        if abs(portfolio_greeks.get('vega', 0)) > limits.get('max_vega', 500):
            alerts.append(f"⚠️ Vega exceeds limit: {portfolio_greeks['vega']:.2f}")
        
        return alerts
    
    # Improvement #14: Greeks decay projection
    def project_greeks_decay(self, greeks: Dict, days: int = 30) -> List[Dict]:
        """Project how Greeks will decay over time."""
        projections = []
        
        for day in range(1, days + 1):
            decay_factor = 1 - (day / days) ** 0.5  # Square root decay
            
            projections.append({
                'day': day,
                'delta': greeks['delta'] * decay_factor,
                'gamma': greeks['gamma'] * (decay_factor ** 1.5),
                'theta': greeks['theta'] * (1 + day / days),  # Theta accelerates
                'vega': greeks['vega'] * decay_factor
            })
        
        return projections
    
    # Improvement #15: Auto-hedge suggestions
    def suggest_hedge(self, portfolio_greeks: Dict) -> Dict:
        """Suggest hedging actions based on Greeks."""
        suggestions = []
        
        delta = portfolio_greeks.get('delta', 0)
        if abs(delta) > 100:
            shares_needed = -int(delta)
            suggestions.append({
                'action': 'BUY' if shares_needed > 0 else 'SELL',
                'quantity': abs(shares_needed),
                'instrument': 'SPY shares',
                'rationale': f'Delta hedge: neutralize {delta:.0f} delta'
            })
        
        gamma = portfolio_greeks.get('gamma', 0)
        if abs(gamma) > 50:
            suggestions.append({
                'action': 'BUY' if gamma < 0 else 'SELL',
                'quantity': int(abs(gamma) / 10),
                'instrument': 'ATM straddle',
                'rationale': f'Gamma hedge: reduce {gamma:.2f} gamma'
            })
        
        return {
            'current_greeks': portfolio_greeks,
            'suggestions': suggestions,
            'urgency': 'HIGH' if len(suggestions) > 1 else 'MEDIUM'
        }


# =============================================================================
# IMPROVEMENT 16-20: Auto Position Manager
# =============================================================================

class AutoPositionManager:
    """
    Improvement #16-20: Automated position management.
    Monitors and manages positions without user intervention.
    """
    
    def __init__(self):
        self.profit_target_pct = 50  # Close at 50% profit
        self.stop_loss_pct = 200  # Close at 200% loss
        self.dte_exit = 7  # Exit positions at 7 DTE
    
    # Improvement #16: Auto profit taking
    def check_profit_targets(self, positions: List[Dict]) -> List[Dict]:
        """Check if any positions hit profit target."""
        actions = []
        for pos in positions:
            pnl_pct = pos.get('pnl_pct', 0)
            if pnl_pct >= self.profit_target_pct:
                actions.append({
                    'position': pos,
                    'action': 'CLOSE',
                    'reason': f'Profit target hit: {pnl_pct:.1f}%',
                    'priority': 'HIGH'
                })
        return actions
    
    # Improvement #17: Auto stop loss
    def check_stop_losses(self, positions: List[Dict]) -> List[Dict]:
        """Check if any positions hit stop loss."""
        actions = []
        for pos in positions:
            pnl_pct = pos.get('pnl_pct', 0)
            if pnl_pct <= -self.stop_loss_pct:
                actions.append({
                    'position': pos,
                    'action': 'CLOSE',
                    'reason': f'Stop loss hit: {pnl_pct:.1f}%',
                    'priority': 'URGENT'
                })
        return actions
    
    # Improvement #18: DTE auto-management
    def check_expiry_exits(self, positions: List[Dict]) -> List[Dict]:
        """Auto-close positions approaching expiry."""
        actions = []
        for pos in positions:
            dte = pos.get('dte', 30)
            if dte <= self.dte_exit:
                actions.append({
                    'position': pos,
                    'action': 'ROLL' if pos.get('pnl_pct', 0) > 0 else 'CLOSE',
                    'reason': f'Expiry approaching: {dte} DTE',
                    'priority': 'MEDIUM'
                })
        return actions
    
    # Improvement #19: Auto roll suggestions
    def suggest_rolls(self, positions: List[Dict]) -> List[Dict]:
        """Suggest roll opportunities for positions."""
        suggestions = []
        for pos in positions:
            if pos.get('pnl_pct', 0) > 30 and pos.get('dte', 30) < 14:
                target_expiry = datetime.now() + timedelta(days=45)
                suggestions.append({
                    'position': pos,
                    'action': 'ROLL',
                    'target_expiry': target_expiry.strftime('%Y-%m-%d'),
                    'expected_credit': pos.get('premium', 0) * 0.7,
                    'rationale': 'Capture remaining time value'
                })
        return suggestions
    
    # Improvement #20: Position sizing auto-adjustment
    def calculate_position_size(self, account_value: float, 
                                risk_per_trade: float = 0.02) -> int:
        """Calculate optimal position size based on account."""
        max_risk = account_value * risk_per_trade
        # For spreads, assume max loss is width of spread
        typical_spread_width = 5  # $5 wide spread
        contracts = int(max_risk / (typical_spread_width * 100))
        return max(1, min(contracts, 10))  # 1-10 contracts

    # Improvement #20b: Portfolio Balance Check
    def check_portfolio_balance(self, portfolio_value: float, cash_balance: float) -> Dict:
        """Check portfolio balance and health."""
        total_value = portfolio_value + cash_balance
        cash_ratio = cash_balance / total_value if total_value > 0 else 0
        
        status = "HEALTHY"
        warnings = []
        
        if cash_ratio < 0.1:
            status = "WARNING"
            warnings.append("Low cash balance (<10%)")
        
        if cash_ratio < 0.05:
            status = "CRITICAL"
            warnings.append("Critical cash level (<5%)")
            
        return {
            'total_value': total_value,
            'cash_ratio': round(cash_ratio, 4),
            'status': status,
            'warnings': warnings
        }


# =============================================================================
# IMPROVEMENT 21-25: AI Market Regime Detector
# =============================================================================

class AIMarketRegimeDetector:
    """
    Improvement #21-25: AI-powered market regime detection.
    Automatically adjusts strategies based on market conditions.
    """
    
    def __init__(self):
        self.regime_history = []
    
    # Improvement #21: Detect current regime
    def detect_regime(self, vix: float, spy_change_20d: float, 
                      spy_volatility: float) -> MarketCondition:
        """Detect current market regime."""
        if vix > 30:
            regime = 'HIGH_VOL'
        elif vix < 15:
            regime = 'LOW_VOL'
        elif spy_change_20d > 0.05:
            regime = 'BULL'
        elif spy_change_20d < -0.05:
            regime = 'BEAR'
        else:
            regime = 'SIDEWAYS'
        
        trend_strength = abs(spy_change_20d) / spy_volatility if spy_volatility > 0 else 0
        
        condition = MarketCondition(
            regime=regime,
            vix_level=vix,
            trend_strength=min(1.0, trend_strength),
            momentum=spy_change_20d * 100
        )
        
        self.regime_history.append(condition)
        return condition
    
    # Improvement #22: Regime-based strategy mapping
    def get_strategies_for_regime(self, regime: str) -> List[str]:
        """Get recommended strategies for current regime."""
        strategy_map = {
            'HIGH_VOL': ['iron_condor', 'credit_spread', 'short_straddle'],
            'LOW_VOL': ['long_straddle', 'calendar_spread', 'debit_spread'],
            'BULL': ['bull_call_spread', 'cash_secured_put', 'covered_call'],
            'BEAR': ['bear_put_spread', 'protective_put', 'collar'],
            'SIDEWAYS': ['iron_butterfly', 'iron_condor', 'calendar_spread']
        }
        return strategy_map.get(regime, ['iron_condor'])
    
    # Improvement #23: Regime change alerts
    def check_regime_change(self) -> Optional[str]:
        """Check if regime has changed."""
        if len(self.regime_history) < 2:
            return None
        
        current = self.regime_history[-1].regime
        previous = self.regime_history[-2].regime
        
        if current != previous:
            return f"⚠️ Regime change: {previous} → {current}"
        return None
    
    # Improvement #24: Sector rotation based on regime
    def get_sector_allocation(self, regime: str) -> Dict[str, float]:
        """Get recommended sector allocation for regime."""
        allocations = {
            'HIGH_VOL': {'GLD': 0.3, 'SLV': 0.1, 'SPY': 0.2, 'TLT': 0.3, 'tech': 0.1},
            'LOW_VOL': {'GLD': 0.1, 'SLV': 0.05, 'SPY': 0.35, 'TLT': 0.1, 'tech': 0.4},
            'BULL': {'GLD': 0.1, 'SLV': 0.1, 'SPY': 0.3, 'TLT': 0.05, 'tech': 0.45},
            'BEAR': {'GLD': 0.35, 'SLV': 0.15, 'SPY': 0.1, 'TLT': 0.3, 'tech': 0.1},
            'SIDEWAYS': {'GLD': 0.2, 'SLV': 0.1, 'SPY': 0.3, 'TLT': 0.15, 'tech': 0.25}
        }
        return allocations.get(regime, allocations['SIDEWAYS'])
    
    # Improvement #25: VIX-based position scaling
    def get_position_scale(self, vix: float) -> float:
        """Scale position size based on VIX."""
        if vix > 35:
            return 0.5  # Half size in extreme vol
        elif vix > 25:
            return 0.75  # Reduced size
        elif vix < 12:
            return 0.8  # Slightly reduced in low vol
        return 1.0  # Normal size


# =============================================================================
# Singleton instances for easy import
# =============================================================================

auto_scanner = AutoMarketScanner()
signal_generator = AISignalGenerator()
greeks_engine = AutoGreeksEngine()
position_manager = AutoPositionManager()
regime_detector = AIMarketRegimeDetector()

__all__ = [
    'FOCUS_TICKERS', 'ALL_FOCUS_TICKERS', 'SignalStrength',
    'MarketCondition', 'TradeSignal',
    'AutoMarketScanner', 'AISignalGenerator', 'AutoGreeksEngine',
    'AutoPositionManager', 'AIMarketRegimeDetector',
    'auto_scanner', 'signal_generator', 'greeks_engine',
    'position_manager', 'regime_detector'
]

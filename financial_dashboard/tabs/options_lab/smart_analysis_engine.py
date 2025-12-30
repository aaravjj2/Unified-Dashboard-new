#!/usr/bin/env python3
"""
Smart Analysis Engine for Enhanced Alpaca Options Lab
======================================================

Improvements 26-50: Advanced AI Analysis Features
Focus: GLD, SLV, SPY + Tech Stocks

Incorporates patterns from:
- ffn (Portfolio metrics, Sharpe, Sortino)
- pandas-ta (Technical indicators)
- machine-learning-for-trading (ML models)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

# Import focus tickers from automation engine
try:
    from .ai_automation_engine import ALL_FOCUS_TICKERS, FOCUS_TICKERS
except ImportError:
    ALL_FOCUS_TICKERS = ['GLD', 'SLV', 'SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA']
    FOCUS_TICKERS = {'commodities': ['GLD', 'SLV'], 'tech_mega': ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA']}


# =============================================================================
# IMPROVEMENT 26-30: Technical Analysis Engine
# =============================================================================

class TechnicalAnalysisEngine:
    """
    Improvement #26-30: Automated technical analysis.
    Generates TA signals without user interaction.
    """
    
    # Improvement #26: Multi-indicator composite score
    def calculate_composite_score(self, prices: pd.Series) -> Dict:
        """Calculate composite TA score from multiple indicators."""
        signals = {
            'rsi': self._rsi_signal(prices),
            'macd': self._macd_signal(prices),
            'bollinger': self._bollinger_signal(prices),
            'sma_cross': self._sma_cross_signal(prices),
            'momentum': self._momentum_signal(prices)
        }
        
        # Weight each signal
        weights = {'rsi': 0.2, 'macd': 0.25, 'bollinger': 0.2, 'sma_cross': 0.2, 'momentum': 0.15}
        composite = sum(signals[k] * weights[k] for k in signals)
        
        return {
            'composite_score': round(composite, 2),
            'signal': 'BUY' if composite > 0.3 else 'SELL' if composite < -0.3 else 'NEUTRAL',
            'individual_signals': signals,
            'confidence': abs(composite)
        }
    
    # Improvement #27: Auto support/resistance detection
    def find_support_resistance(self, prices: pd.Series, window: int = 20) -> Dict:
        """Auto-detect key support and resistance levels."""
        if len(prices) < window:
            return {'support': [], 'resistance': []}
        
        # Find local minima (support)
        support_levels = []
        resistance_levels = []
        
        for i in range(window, len(prices) - window):
            window_slice = prices.iloc[i-window:i+window]
            if prices.iloc[i] == window_slice.min():
                support_levels.append(prices.iloc[i])
            if prices.iloc[i] == window_slice.max():
                resistance_levels.append(prices.iloc[i])
        
        # Cluster nearby levels
        support = self._cluster_levels(support_levels)
        resistance = self._cluster_levels(resistance_levels)
        
        return {
            'support': sorted(support)[:3],  # Top 3 support levels
            'resistance': sorted(resistance, reverse=True)[:3],
            'current_price': prices.iloc[-1],
            'nearest_support': min(support, key=lambda x: abs(x - prices.iloc[-1])) if support else None,
            'nearest_resistance': min(resistance, key=lambda x: abs(x - prices.iloc[-1])) if resistance else None
        }
    
    # Improvement #28: Trend strength indicator
    def calculate_trend_strength(self, prices: pd.Series) -> Dict:
        """Calculate ADX-like trend strength."""
        if len(prices) < 20:
            return {'strength': 0, 'direction': 'NEUTRAL'}
        
        # Simple trend strength based on price movement consistency
        changes = prices.pct_change().dropna()
        positive_days = (changes > 0).sum()
        total_days = len(changes)
        
        direction_ratio = positive_days / total_days
        magnitude = abs(prices.iloc[-1] / prices.iloc[0] - 1)
        
        strength = magnitude * abs(direction_ratio - 0.5) * 2
        
        return {
            'strength': round(min(1.0, strength * 10), 2),
            'direction': 'UP' if direction_ratio > 0.55 else 'DOWN' if direction_ratio < 0.45 else 'NEUTRAL',
            'consistency': round(abs(direction_ratio - 0.5) * 2, 2),
            'magnitude': round(magnitude * 100, 2)
        }
    
    # Improvement #29: Volume analysis
    def analyze_volume(self, prices: pd.Series, volumes: pd.Series) -> Dict:
        """Analyze volume patterns for confirmation."""
        if len(volumes) < 20:
            return {'signal': 'NEUTRAL', 'ratio': 1.0}
        
        avg_volume = volumes.rolling(20).mean().iloc[-1]
        current_volume = volumes.iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        price_change = prices.iloc[-1] / prices.iloc[-2] - 1
        
        # Volume confirmation
        if volume_ratio > 1.5 and price_change > 0:
            signal = 'STRONG_BUY'
        elif volume_ratio > 1.5 and price_change < 0:
            signal = 'STRONG_SELL'
        elif volume_ratio < 0.5:
            signal = 'WEAK_TREND'
        else:
            signal = 'NEUTRAL'
        
        return {
            'signal': signal,
            'ratio': round(volume_ratio, 2),
            'avg_volume': int(avg_volume),
            'current_volume': int(current_volume),
            'confirms_trend': volume_ratio > 1.2
        }
    
    # Improvement #30: Divergence detection
    def detect_divergence(self, prices: pd.Series) -> Dict:
        """Detect price/indicator divergence."""
        if len(prices) < 30:
            return {'divergence': None}
        
        # Calculate RSI for divergence check
        rsi = self._calculate_rsi(prices)
        
        # Check for divergence in last 10 periods
        price_trend = prices.iloc[-10:].iloc[-1] > prices.iloc[-10:].iloc[0]
        rsi_trend = rsi.iloc[-10:].iloc[-1] > rsi.iloc[-10:].iloc[0]
        
        if price_trend and not rsi_trend:
            divergence = 'BEARISH'  # Price up, RSI down
        elif not price_trend and rsi_trend:
            divergence = 'BULLISH'  # Price down, RSI up
        else:
            divergence = None
        
        return {
            'divergence': divergence,
            'price_trend': 'UP' if price_trend else 'DOWN',
            'rsi_trend': 'UP' if rsi_trend else 'DOWN',
            'signal_strength': 'STRONG' if divergence else 'NONE'
        }
    
    def _rsi_signal(self, prices: pd.Series) -> float:
        """RSI-based signal (-1 to 1)."""
        rsi = self._calculate_rsi(prices)
        if len(rsi) == 0:
            return 0
        current_rsi = rsi.iloc[-1]
        if current_rsi < 30:
            return 1.0  # Oversold - buy
        elif current_rsi > 70:
            return -1.0  # Overbought - sell
        return (50 - current_rsi) / 50
    
    def _macd_signal(self, prices: pd.Series) -> float:
        """MACD-based signal."""
        if len(prices) < 26:
            return 0
        ema12 = prices.ewm(span=12).mean()
        ema26 = prices.ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        
        if macd.iloc[-1] > signal.iloc[-1]:
            return min(1.0, (macd.iloc[-1] - signal.iloc[-1]) / prices.iloc[-1] * 100)
        return max(-1.0, (macd.iloc[-1] - signal.iloc[-1]) / prices.iloc[-1] * 100)
    
    def _bollinger_signal(self, prices: pd.Series) -> float:
        """Bollinger Bands signal."""
        if len(prices) < 20:
            return 0
        sma = prices.rolling(20).mean()
        std = prices.rolling(20).std()
        upper = sma + 2 * std
        lower = sma - 2 * std
        
        current = prices.iloc[-1]
        if current < lower.iloc[-1]:
            return 1.0  # Below lower band - buy
        elif current > upper.iloc[-1]:
            return -1.0  # Above upper band - sell
        return 0
    
    def _sma_cross_signal(self, prices: pd.Series) -> float:
        """SMA crossover signal."""
        if len(prices) < 50:
            return 0
        sma20 = prices.rolling(20).mean()
        sma50 = prices.rolling(50).mean()
        
        if sma20.iloc[-1] > sma50.iloc[-1]:
            return 0.5
        return -0.5
    
    def _momentum_signal(self, prices: pd.Series) -> float:
        """Momentum signal."""
        if len(prices) < 10:
            return 0
        momentum = prices.iloc[-1] / prices.iloc[-10] - 1
        return max(-1, min(1, momentum * 10))
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _cluster_levels(self, levels: List[float], threshold: float = 0.02) -> List[float]:
        """Cluster nearby price levels."""
        if not levels:
            return []
        
        levels = sorted(levels)
        clustered = [levels[0]]
        
        for level in levels[1:]:
            if abs(level - clustered[-1]) / clustered[-1] > threshold:
                clustered.append(level)
        
        return clustered

    # Compatibility Wrappers
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI (Public Wrapper)."""
        return self._calculate_rsi(prices, period)

    def calculate_macd(self, prices: pd.Series) -> Dict:
        """Calculate MACD values."""
        if len(prices) < 26:
            return {'macd': 0, 'signal': 0, 'hist': 0}
        ema12 = prices.ewm(span=12).mean()
        ema26 = prices.ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        hist = macd - signal
        return {
            'macd': macd.iloc[-1],
            'signal': signal.iloc[-1],
            'hist': hist.iloc[-1]
        }


# =============================================================================
# IMPROVEMENT 31-35: IV Analysis Engine
# =============================================================================

class IVAnalysisEngine:
    """
    Improvement #31-35: Implied Volatility analysis.
    Automated IV analytics for options trading.
    """
    
    # Improvement #31: IV percentile calculation
    def calculate_iv_percentile(self, current_iv: float, 
                                historical_ivs: List[float]) -> Dict:
        """Calculate IV percentile vs history."""
        if not historical_ivs:
            return {'percentile': 50, 'rank': 'NORMAL'}
        
        sorted_ivs = sorted(historical_ivs)
        percentile = sum(1 for iv in sorted_ivs if iv < current_iv) / len(sorted_ivs) * 100
        
        if percentile > 80:
            rank = 'VERY_HIGH'
            recommendation = 'SELL_PREMIUM'
        elif percentile > 60:
            rank = 'HIGH'
            recommendation = 'SELL_PREMIUM'
        elif percentile < 20:
            rank = 'VERY_LOW'
            recommendation = 'BUY_PREMIUM'
        elif percentile < 40:
            rank = 'LOW'
            recommendation = 'BUY_PREMIUM'
        else:
            rank = 'NORMAL'
            recommendation = 'NEUTRAL'
        
        return {
            'percentile': round(percentile, 1),
            'rank': rank,
            'recommendation': recommendation,
            'current_iv': current_iv,
            'historical_mean': np.mean(historical_ivs),
            'historical_std': np.std(historical_ivs)
        }
    
    # Improvement #32: IV term structure analysis
    def analyze_term_structure(self, expirations: List[str], 
                               ivs: List[float]) -> Dict:
        """Analyze IV term structure."""
        if len(expirations) < 2:
            return {'structure': 'INSUFFICIENT_DATA'}
        
        # Calculate slope
        slope = (ivs[-1] - ivs[0]) / len(ivs)
        
        if slope > 0.01:
            structure = 'CONTANGO'
            strategy = 'Calendar spreads favorable'
        elif slope < -0.01:
            structure = 'BACKWARDATION'
            strategy = 'Front-month premium high'
        else:
            structure = 'FLAT'
            strategy = 'Normal term structure'
        
        return {
            'structure': structure,
            'slope': round(slope, 4),
            'front_iv': ivs[0],
            'back_iv': ivs[-1],
            'strategy_implication': strategy
        }
    
    # Improvement #33: IV skew analysis
    def analyze_skew(self, strikes: List[float], ivs: List[float], 
                     atm_strike: float) -> Dict:
        """Analyze IV skew across strikes."""
        if len(strikes) < 3:
            return {'skew': 'INSUFFICIENT_DATA'}
        
        # Find ATM IV
        atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - atm_strike))
        atm_iv = ivs[atm_idx]
        
        # Calculate put and call wing IVs
        otm_put_ivs = [iv for s, iv in zip(strikes, ivs) if s < atm_strike]
        otm_call_ivs = [iv for s, iv in zip(strikes, ivs) if s > atm_strike]
        
        put_skew = np.mean(otm_put_ivs) - atm_iv if otm_put_ivs else 0
        call_skew = np.mean(otm_call_ivs) - atm_iv if otm_call_ivs else 0
        
        if put_skew > 0.05:
            skew_type = 'PUT_SKEW'
            interpretation = 'Market pricing downside protection'
        elif call_skew > 0.03:
            skew_type = 'CALL_SKEW'
            interpretation = 'Unusual - possible squeeze setup'
        else:
            skew_type = 'NORMAL'
            interpretation = 'Standard volatility smile'
        
        return {
            'skew_type': skew_type,
            'put_skew': round(put_skew, 4),
            'call_skew': round(call_skew, 4),
            'atm_iv': round(atm_iv, 4),
            'interpretation': interpretation
        }

    # Alias for compatibility
    calculate_iv_skew = analyze_skew
    
    # Improvement #34: IV crush prediction
    def predict_iv_crush(self, current_iv: float, event_date: str,
                         historical_crush: List[float]) -> Dict:
        """Predict IV crush after event (earnings, etc.)."""
        if not historical_crush:
            expected_crush = 0.3  # Default 30% crush
        else:
            expected_crush = np.mean(historical_crush)
        
        expected_iv_after = current_iv * (1 - expected_crush)
        
        return {
            'current_iv': current_iv,
            'expected_crush_pct': round(expected_crush * 100, 1),
            'expected_iv_after': round(expected_iv_after, 4),
            'event_date': event_date,
            'strategy': 'SELL_PREMIUM_BEFORE' if current_iv > 0.4 else 'WAIT',
            'confidence': min(0.9, len(historical_crush) / 10)
        }
    
    # Improvement #35: Cross-asset IV comparison
    def compare_iv_across_assets(self, iv_data: Dict[str, float]) -> Dict:
        """Compare IV levels across focus assets."""
        comparisons = []
        
        for ticker, iv in iv_data.items():
            comparisons.append({
                'ticker': ticker,
                'iv': iv,
                'rank': self._rank_iv(iv)
            })
        
        # Sort by IV
        comparisons.sort(key=lambda x: x['iv'], reverse=True)
        
        return {
            'highest_iv': comparisons[0] if comparisons else None,
            'lowest_iv': comparisons[-1] if comparisons else None,
            'rankings': comparisons,
            'best_sell_premium': comparisons[0]['ticker'] if comparisons else None,
            'best_buy_premium': comparisons[-1]['ticker'] if comparisons else None
        }
    
    def _rank_iv(self, iv: float) -> str:
        """Rank IV level."""
        if iv > 0.5:
            return 'VERY_HIGH'
        elif iv > 0.35:
            return 'HIGH'
        elif iv > 0.2:
            return 'NORMAL'
        elif iv > 0.1:
            return 'LOW'
        return 'VERY_LOW'


# =============================================================================
# IMPROVEMENT 36-40: Options Flow Analysis
# =============================================================================

class OptionsFlowAnalyzer:
    """
    Improvement #36-40: Automated options flow analysis.
    Detects smart money and unusual activity.
    """
    
    # Improvement #36: Smart money detection
    def detect_smart_money(self, trade: Dict) -> Dict:
        """Detect if trade is likely smart money."""
        indicators = []
        confidence = 0.5
        
        # Large premium
        if trade.get('premium', 0) > 100000:
            indicators.append('LARGE_PREMIUM')
            confidence += 0.15
        
        # Opening trade (new position)
        if trade.get('open_interest_change', 0) > 0:
            indicators.append('OPENING_TRADE')
            confidence += 0.1
        
        # Sweep (multiple exchanges)
        if trade.get('exchange_count', 1) > 2:
            indicators.append('SWEEP')
            confidence += 0.15
        
        # Above ask (aggressive)
        if trade.get('price') and trade.get('ask'):
            if trade['price'] >= trade['ask']:
                indicators.append('ABOVE_ASK')
                confidence += 0.1
        
        return {
            'is_smart_money': confidence > 0.7,
            'confidence': min(0.95, confidence),
            'indicators': indicators,
            'ticker': trade.get('ticker'),
            'direction': 'BULLISH' if trade.get('side') == 'buy' else 'BEARISH'
        }
    
    # Improvement #37: Flow aggregation by ticker
    def aggregate_flow(self, trades: List[Dict], ticker: str) -> Dict:
        """Aggregate options flow for ticker."""
        call_volume = sum(t.get('volume', 0) for t in trades 
                        if t.get('ticker') == ticker and t.get('type') == 'call')
        put_volume = sum(t.get('volume', 0) for t in trades 
                        if t.get('ticker') == ticker and t.get('type') == 'put')
        
        call_premium = sum(t.get('premium', 0) for t in trades 
                         if t.get('ticker') == ticker and t.get('type') == 'call')
        put_premium = sum(t.get('premium', 0) for t in trades 
                        if t.get('ticker') == ticker and t.get('type') == 'put')
        
        pcr_volume = put_volume / call_volume if call_volume > 0 else 1.0
        pcr_premium = put_premium / call_premium if call_premium > 0 else 1.0
        
        if pcr_volume < 0.7 and pcr_premium < 0.7:
            sentiment = 'VERY_BULLISH'
        elif pcr_volume < 0.9:
            sentiment = 'BULLISH'
        elif pcr_volume > 1.3 and pcr_premium > 1.3:
            sentiment = 'VERY_BEARISH'
        elif pcr_volume > 1.1:
            sentiment = 'BEARISH'
        else:
            sentiment = 'NEUTRAL'
        
        return {
            'ticker': ticker,
            'call_volume': call_volume,
            'put_volume': put_volume,
            'call_premium': call_premium,
            'put_premium': put_premium,
            'pcr_volume': round(pcr_volume, 2),
            'pcr_premium': round(pcr_premium, 2),
            'sentiment': sentiment
        }
    
    # Improvement #38: Unusual activity alerts
    def find_unusual_activity(self, trades: List[Dict]) -> List[Dict]:
        """Find unusual options activity."""
        unusual = []
        
        for trade in trades:
            score = 0
            reasons = []
            
            # Volume vs OI ratio
            vol_oi_ratio = trade.get('volume', 0) / max(1, trade.get('open_interest', 1))
            if vol_oi_ratio > 2:
                score += 30
                reasons.append(f'High Vol/OI: {vol_oi_ratio:.1f}x')
            
            # Large premium
            if trade.get('premium', 0) > 500000:
                score += 40
                reasons.append(f'Large Premium: ${trade["premium"]:,.0f}')
            elif trade.get('premium', 0) > 100000:
                score += 20
                reasons.append(f'Notable Premium: ${trade["premium"]:,.0f}')
            
            # Near expiry large trade
            if trade.get('dte', 30) < 7 and trade.get('premium', 0) > 50000:
                score += 25
                reasons.append('Near-expiry large trade')
            
            if score >= 40:
                unusual.append({
                    'trade': trade,
                    'score': score,
                    'reasons': reasons,
                    'alert_level': 'HIGH' if score >= 60 else 'MEDIUM'
                })
        
        return sorted(unusual, key=lambda x: x['score'], reverse=True)

    # Alias for compatibility
    analyze_unusual_activity = find_unusual_activity

    def calculate_put_call_ratio(self, trades: List[Dict]) -> Dict:
        """Calculate Put/Call Ratios."""
        call_vol = sum(t.get('volume', 0) for t in trades if t.get('type') == 'call')
        put_vol = sum(t.get('volume', 0) for t in trades if t.get('type') == 'put')
        
        call_prem = sum(t.get('premium', 0) for t in trades if t.get('type') == 'call')
        put_prem = sum(t.get('premium', 0) for t in trades if t.get('type') == 'put')
        
        return {
            'volume_pcr': put_vol / call_vol if call_vol > 0 else 1.0,
            'premium_pcr': put_prem / call_prem if call_prem > 0 else 1.0
        }
    
    # Improvement #39: Dark pool print detection
    def detect_dark_pool(self, trade: Dict) -> Dict:
        """Detect if trade is likely dark pool."""
        indicators = []
        
        # Large size, single print
        if trade.get('size', 0) > 1000:
            indicators.append('LARGE_BLOCK')
        
        # Between bid-ask
        if trade.get('bid') and trade.get('ask') and trade.get('price'):
            mid = (trade['bid'] + trade['ask']) / 2
            if abs(trade['price'] - mid) < (trade['ask'] - trade['bid']) * 0.1:
                indicators.append('AT_MIDPOINT')
        
        is_dark_pool = len(indicators) >= 1 and trade.get('size', 0) > 500
        
        return {
            'is_dark_pool': is_dark_pool,
            'indicators': indicators,
            'size': trade.get('size'),
            'significance': 'HIGH' if is_dark_pool and trade.get('size', 0) > 2000 else 'MEDIUM'
        }
    
    # Improvement #40: Sector flow comparison
    def compare_sector_flow(self, all_flow: Dict[str, Dict]) -> Dict:
        """Compare flow across sectors."""
        sector_sentiment = {}
        
        # Commodities (GLD, SLV)
        commodity_flow = [all_flow.get(t, {}) for t in FOCUS_TICKERS.get('commodities', [])]
        sector_sentiment['commodities'] = self._average_sentiment(commodity_flow)
        
        # Tech
        tech_flow = [all_flow.get(t, {}) for t in FOCUS_TICKERS.get('tech_mega', [])]
        sector_sentiment['tech'] = self._average_sentiment(tech_flow)
        
        # Find best sector
        best_sector = max(sector_sentiment, key=lambda k: sector_sentiment[k].get('score', 0))
        
        return {
            'sector_sentiment': sector_sentiment,
            'best_sector': best_sector,
            'recommendation': f'Focus on {best_sector}'
        }
    
    def _average_sentiment(self, flows: List[Dict]) -> Dict:
        """Calculate average sentiment from flows."""
        if not flows:
            return {'sentiment': 'NEUTRAL', 'score': 50}
        
        scores = []
        for flow in flows:
            sentiment = flow.get('sentiment', 'NEUTRAL')
            score_map = {'VERY_BULLISH': 90, 'BULLISH': 70, 'NEUTRAL': 50, 
                        'BEARISH': 30, 'VERY_BEARISH': 10}
            scores.append(score_map.get(sentiment, 50))
        
        avg_score = np.mean(scores)
        if avg_score > 70:
            sentiment = 'BULLISH'
        elif avg_score < 30:
            sentiment = 'BEARISH'
        else:
            sentiment = 'NEUTRAL'
        
        return {'sentiment': sentiment, 'score': avg_score}


# =============================================================================
# IMPROVEMENT 41-45: Portfolio Analytics
# =============================================================================

class PortfolioAnalytics:
    """
    Improvement #41-45: Portfolio-level analytics.
    Based on ffn library patterns.
    """
    
    # Improvement #41: Sharpe ratio calculation
    def calculate_sharpe(self, returns: pd.Series, risk_free_rate: float = 0.05) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) < 2:
            return 0.0
        
        excess_returns = returns - risk_free_rate / 252  # Daily risk-free rate
        return np.sqrt(252) * excess_returns.mean() / excess_returns.std()

    # Alias for compatibility
    calculate_sharpe_ratio = calculate_sharpe
    
    # Improvement #42: Sortino ratio
    def calculate_sortino(self, returns: pd.Series, risk_free_rate: float = 0.05) -> float:
        """Calculate Sortino ratio (downside deviation)."""
        if len(returns) < 2:
            return 0.0
        
        excess_returns = returns - risk_free_rate / 252
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else returns.std()
        
        return np.sqrt(252) * excess_returns.mean() / downside_std
    
    # Improvement #43: Maximum drawdown
    def calculate_max_drawdown(self, prices: pd.Series) -> Dict:
        """Calculate maximum drawdown."""
        if len(prices) < 2:
            return {'max_drawdown': 0, 'duration': 0}
        
        cumulative = (1 + prices.pct_change()).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        
        max_dd = drawdown.min()
        max_dd_idx = drawdown.idxmin()
        
        # Find duration
        peak_idx = cumulative[:max_dd_idx].idxmax()
        
        return {
            'max_drawdown': round(max_dd * 100, 2),
            'peak_date': str(peak_idx),
            'trough_date': str(max_dd_idx),
            'recovery_needed': round((1 / (1 + max_dd) - 1) * 100, 2)
        }
    
    # Improvement #44: Value at Risk (VaR)
    def calculate_var(self, returns: pd.Series, confidence: float = 0.95) -> Dict:
        """Calculate Value at Risk."""
        if len(returns) < 30:
            return {'var': 0, 'confidence': confidence}
        
        var = np.percentile(returns, (1 - confidence) * 100)
        cvar = returns[returns <= var].mean()  # Conditional VaR
        
        return {
            'var': round(var * 100, 2),
            'cvar': round(cvar * 100, 2),
            'confidence': confidence,
            'interpretation': f'{confidence*100:.0f}% chance daily loss won\'t exceed {abs(var)*100:.2f}%'
        }
    
    # Improvement #45: Correlation matrix
    def calculate_correlations(self, price_data: Dict[str, pd.Series]) -> pd.DataFrame:
        """Calculate correlation matrix for focus tickers."""
        df = pd.DataFrame(price_data)
        returns = df.pct_change().dropna()
        return returns.corr().round(3)


# =============================================================================
# IMPROVEMENT 46-50: ML Prediction Engine
# =============================================================================

class MLPredictionEngine:
    """
    Improvement #46-50: Machine learning predictions.
    Automated ML-based price and volatility predictions.
    """
    
    def __init__(self):
        self.models = {}
    
    # Improvement #46: Price direction prediction
    def predict_direction(self, prices: pd.Series, periods: int = 5) -> Dict:
        """Predict price direction using simple ML."""
        if len(prices) < 50:
            return {'prediction': 'NEUTRAL', 'confidence': 0.5}
        
        # Feature engineering
        returns = prices.pct_change()
        ma5 = prices.rolling(5).mean()
        ma20 = prices.rolling(20).mean()
        
        # Simple rule-based "ML"
        recent_trend = (prices.iloc[-1] > ma5.iloc[-1]) and (ma5.iloc[-1] > ma20.iloc[-1])
        momentum = returns.iloc[-5:].mean()
        
        if recent_trend and momentum > 0:
            prediction = 'UP'
            confidence = min(0.8, 0.5 + abs(momentum) * 10)
        elif not recent_trend and momentum < 0:
            prediction = 'DOWN'
            confidence = min(0.8, 0.5 + abs(momentum) * 10)
        else:
            prediction = 'NEUTRAL'
            confidence = 0.5
        
        return {
            'prediction': prediction,
            'confidence': round(confidence, 2),
            'time_horizon': f'{periods} days',
            'factors': ['trend', 'momentum', 'ma_crossover']
        }
    
    # Improvement #47: Volatility forecast
    def forecast_volatility(self, prices: pd.Series, days_ahead: int = 5) -> Dict:
        """Forecast future volatility."""
        if len(prices) < 30:
            return {'forecast': 0.2, 'confidence': 0.3}
        
        returns = prices.pct_change().dropna()
        
        # GARCH-like simple forecast
        current_vol = returns.std() * np.sqrt(252)
        vol_of_vol = returns.rolling(20).std().std()
        
        # Mean reversion assumption
        long_term_vol = 0.2  # 20% long-term average
        forecast = current_vol * 0.7 + long_term_vol * 0.3
        
        return {
            'current_vol': round(current_vol, 4),
            'forecast_vol': round(forecast, 4),
            'days_ahead': days_ahead,
            'direction': 'INCREASING' if forecast > current_vol else 'DECREASING',
            'confidence': round(0.6 - vol_of_vol, 2)
        }
    
    # Improvement #48: Expected move calculation
    def calculate_expected_move(self, price: float, iv: float, dte: int) -> Dict:
        """Calculate expected move based on IV."""
        # Expected move = Price * IV * sqrt(DTE/365)
        expected_move_pct = iv * np.sqrt(dte / 365)
        expected_move_dollars = price * expected_move_pct
        
        return {
            'expected_move_pct': round(expected_move_pct * 100, 2),
            'expected_move_dollars': round(expected_move_dollars, 2),
            'upper_bound': round(price + expected_move_dollars, 2),
            'lower_bound': round(price - expected_move_dollars, 2),
            'one_std_range': f'{price - expected_move_dollars:.2f} - {price + expected_move_dollars:.2f}'
        }
    
    # Improvement #49: Trend prediction ensemble
    def ensemble_prediction(self, prices: pd.Series) -> Dict:
        """Ensemble of multiple prediction methods."""
        predictions = []
        
        # Method 1: MA crossover
        ma_pred = self._ma_prediction(prices)
        predictions.append(ma_pred)
        
        # Method 2: Momentum
        mom_pred = self._momentum_prediction(prices)
        predictions.append(mom_pred)
        
        # Method 3: Mean reversion
        mr_pred = self._mean_reversion_prediction(prices)
        predictions.append(mr_pred)
        
        # Ensemble vote
        up_votes = sum(1 for p in predictions if p == 'UP')
        down_votes = sum(1 for p in predictions if p == 'DOWN')
        
        if up_votes > down_votes:
            final = 'UP'
            confidence = up_votes / len(predictions)
        elif down_votes > up_votes:
            final = 'DOWN'
            confidence = down_votes / len(predictions)
        else:
            final = 'NEUTRAL'
            confidence = 0.5
        
        return {
            'prediction': final,
            'confidence': round(confidence, 2),
            'individual_predictions': {
                'ma_crossover': predictions[0],
                'momentum': predictions[1],
                'mean_reversion': predictions[2]
            }
        }
    
    # Improvement #50: Auto-generate trade ideas
    def generate_trade_ideas(self, ticker: str, analysis: Dict) -> List[Dict]:
        """Auto-generate trade ideas based on analysis."""
        ideas = []
        
        direction = analysis.get('direction', 'NEUTRAL')
        iv_rank = analysis.get('iv_rank', 50)
        confidence = analysis.get('confidence', 0.5)
        
        if direction == 'UP' and confidence > 0.6:
            ideas.append({
                'strategy': 'Bull Call Spread',
                'rationale': f'Bullish outlook with {confidence:.0%} confidence',
                'risk_level': 'MODERATE'
            })
            if iv_rank > 60:
                ideas.append({
                    'strategy': 'Cash Secured Put',
                    'rationale': f'High IV rank ({iv_rank}%) + bullish = sell puts',
                    'risk_level': 'MODERATE'
                })
        
        elif direction == 'DOWN' and confidence > 0.6:
            ideas.append({
                'strategy': 'Bear Put Spread',
                'rationale': f'Bearish outlook with {confidence:.0%} confidence',
                'risk_level': 'MODERATE'
            })
        
        if iv_rank > 70:
            ideas.append({
                'strategy': 'Iron Condor',
                'rationale': f'Very high IV rank ({iv_rank}%) - sell premium',
                'risk_level': 'LOW'
            })
        
        return ideas
    
    def _ma_prediction(self, prices: pd.Series) -> str:
        """MA-based prediction."""
        if len(prices) < 50:
            return 'NEUTRAL'
        ma5 = prices.rolling(5).mean().iloc[-1]
        ma20 = prices.rolling(20).mean().iloc[-1]
        return 'UP' if ma5 > ma20 else 'DOWN'
    
    def _momentum_prediction(self, prices: pd.Series) -> str:
        """Momentum-based prediction."""
        if len(prices) < 10:
            return 'NEUTRAL'
        mom = prices.iloc[-1] / prices.iloc[-10] - 1
        return 'UP' if mom > 0.02 else 'DOWN' if mom < -0.02 else 'NEUTRAL'
    
    def _mean_reversion_prediction(self, prices: pd.Series) -> str:
        """Mean reversion prediction."""
        if len(prices) < 20:
            return 'NEUTRAL'
        ma20 = prices.rolling(20).mean().iloc[-1]
        deviation = (prices.iloc[-1] - ma20) / ma20
        return 'DOWN' if deviation > 0.03 else 'UP' if deviation < -0.03 else 'NEUTRAL'


# =============================================================================
# Singleton instances
# =============================================================================

ta_engine = TechnicalAnalysisEngine()
iv_engine = IVAnalysisEngine()
flow_analyzer = OptionsFlowAnalyzer()
portfolio_analytics = PortfolioAnalytics()
ml_engine = MLPredictionEngine()

__all__ = [
    'TechnicalAnalysisEngine', 'IVAnalysisEngine', 'OptionsFlowAnalyzer',
    'PortfolioAnalytics', 'MLPredictionEngine',
    'ta_engine', 'iv_engine', 'flow_analyzer', 'portfolio_analytics', 'ml_engine'
]

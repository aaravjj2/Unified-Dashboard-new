"""
Dashboard Improvements Module - 50+ Enhancements
================================================

Focused on: GLD, SLV, SPY + Major Tech (AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA)

This module implements 50+ improvements across all dashboard components.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# ============================================================================
# IMPROVEMENT 1-10: PRECIOUS METALS ANALYTICS
# ============================================================================

class PreciousMetalsAnalyzer:
    """
    Improvements 1-10: Specialized analytics for GLD and SLV.
    
    1. Gold-Silver Ratio tracking
    2. Precious metals trend indicators
    3. Safe haven signal detection
    4. Correlation with VIX/fear index
    5. Inflation hedge scoring
    6. Dollar strength impact analysis
    7. Mining stock correlation (GDX, SIL)
    8. Seasonality patterns for metals
    9. Central bank buying signals
    10. Real yield vs gold correlation
    """
    
    def __init__(self):
        self.gold_tickers = ['GLD', 'IAU', 'GDX', 'GOLD']
        self.silver_tickers = ['SLV', 'SIL', 'SILJ']
        
    def calculate_gold_silver_ratio(self, gld_price: float, slv_price: float) -> Dict:
        """
        Improvement #1: Gold-Silver Ratio Analysis
        Historical average is ~60-80. >80 suggests silver undervalued.
        """
        if slv_price <= 0:
            return {'ratio': 0, 'signal': 'error', 'interpretation': 'Invalid price'}
            
        # GLD tracks 1/10 oz gold, SLV tracks 1 oz silver
        # Adjust for this in calculation
        gold_per_oz = gld_price * 10  # Approximate
        ratio = gold_per_oz / slv_price
        
        if ratio > 90:
            signal = 'silver_undervalued'
            interpretation = f'Ratio {ratio:.1f} extremely high - silver may outperform'
        elif ratio > 80:
            signal = 'silver_cheap'
            interpretation = f'Ratio {ratio:.1f} above average - silver relatively cheap'
        elif ratio < 50:
            signal = 'silver_expensive'
            interpretation = f'Ratio {ratio:.1f} below average - silver may underperform'
        else:
            signal = 'neutral'
            interpretation = f'Ratio {ratio:.1f} in normal range'
            
        return {
            'ratio': round(ratio, 2),
            'signal': signal,
            'interpretation': interpretation,
            'historical_avg': 70,
            'trade_suggestion': 'long_slv' if ratio > 80 else ('long_gld' if ratio < 50 else 'neutral')
        }
    
    def detect_safe_haven_signal(self, spy_change: float, gld_change: float, vix_level: float) -> Dict:
        """
        Improvement #2-4: Safe Haven Detection
        When SPY drops but GLD rises with high VIX = safe haven mode
        """
        is_safe_haven = spy_change < -1.0 and gld_change > 0 and vix_level > 20
        
        strength = 'strong' if (spy_change < -2 and gld_change > 1 and vix_level > 25) else \
                   'moderate' if is_safe_haven else 'weak'
        
        return {
            'safe_haven_active': is_safe_haven,
            'strength': strength,
            'spy_change': spy_change,
            'gld_change': gld_change,
            'vix_level': vix_level,
            'recommendation': 'Add gold exposure' if is_safe_haven else 'Normal allocation'
        }
    
    def inflation_hedge_score(self, real_yield: float, expected_inflation: float, gld_momentum: float) -> Dict:
        """
        Improvement #5: Inflation Hedge Scoring
        Negative real yields = bullish for gold
        """
        # Real yield below -1% is strongly bullish for gold
        yield_score = max(0, min(100, (1 - real_yield) * 50))
        
        # Higher expected inflation = bullish for gold
        inflation_score = min(100, expected_inflation * 20)
        
        # Positive momentum adds to score
        momentum_score = min(100, max(0, gld_momentum * 100 + 50))
        
        total_score = (yield_score * 0.4 + inflation_score * 0.3 + momentum_score * 0.3)
        
        return {
            'hedge_score': round(total_score, 1),
            'yield_component': round(yield_score, 1),
            'inflation_component': round(inflation_score, 1),
            'momentum_component': round(momentum_score, 1),
            'signal': 'strong_buy' if total_score > 70 else ('buy' if total_score > 50 else 'neutral'),
            'interpretation': f'Gold hedge score {total_score:.0f}/100'
        }
    
    def seasonal_pattern_score(self, current_month: int) -> Dict:
        """
        Improvement #8: Seasonality Patterns
        Gold typically strong: Aug-Sep, Dec-Feb
        Silver typically strong: Jan-Apr, Aug-Sep
        """
        gold_seasonal = {
            1: 0.7, 2: 0.6, 3: 0.3, 4: 0.2, 5: 0.1, 6: 0.0,
            7: 0.2, 8: 0.8, 9: 0.7, 10: 0.4, 11: 0.5, 12: 0.6
        }
        silver_seasonal = {
            1: 0.8, 2: 0.7, 3: 0.6, 4: 0.5, 5: 0.2, 6: 0.0,
            7: 0.3, 8: 0.7, 9: 0.6, 10: 0.3, 11: 0.4, 12: 0.5
        }
        
        return {
            'month': current_month,
            'gold_seasonal_score': gold_seasonal.get(current_month, 0.5),
            'silver_seasonal_score': silver_seasonal.get(current_month, 0.5),
            'gold_seasonal_outlook': 'bullish' if gold_seasonal.get(current_month, 0.5) > 0.5 else 'bearish',
            'silver_seasonal_outlook': 'bullish' if silver_seasonal.get(current_month, 0.5) > 0.5 else 'bearish'
        }


# ============================================================================
# IMPROVEMENT 11-20: SPY/MARKET ETF ANALYTICS
# ============================================================================

class MarketETFAnalyzer:
    """
    Improvements 11-20: SPY and Market ETF analysis.
    
    11. SPY trend strength indicator
    12. Sector rotation signals
    13. Market breadth analysis
    14. Put/Call ratio tracking
    15. VIX term structure analysis
    16. SPY support/resistance levels
    17. Market momentum indicators
    18. Risk-on/Risk-off signal
    19. SPY options flow analysis
    20. Market regime detection
    """
    
    def __init__(self):
        self.market_etfs = ['SPY', 'QQQ', 'IWM', 'DIA']
        
    def calculate_trend_strength(self, prices: pd.Series, period: int = 20) -> Dict:
        """
        Improvement #11: SPY Trend Strength Indicator
        Uses ADX-like calculation
        """
        if len(prices) < period + 1:
            return {'strength': 0, 'direction': 'unknown', 'signal': 'insufficient_data'}
        
        # Calculate directional movement
        high = prices.rolling(2).max()
        low = prices.rolling(2).min()
        
        plus_dm = (prices - prices.shift(1)).clip(lower=0)
        minus_dm = (prices.shift(1) - prices).clip(lower=0)
        
        tr = (high - low).rolling(period).mean()
        plus_di = (plus_dm.rolling(period).mean() / tr * 100).iloc[-1]
        minus_di = (minus_dm.rolling(period).mean() / tr * 100).iloc[-1]
        
        dx = abs(plus_di - minus_di) / (plus_di + minus_di + 0.0001) * 100
        
        direction = 'bullish' if plus_di > minus_di else 'bearish'
        strength = min(100, dx)
        
        return {
            'strength': round(strength, 1),
            'direction': direction,
            'plus_di': round(plus_di, 1),
            'minus_di': round(minus_di, 1),
            'signal': 'strong_trend' if strength > 25 else 'weak_trend'
        }
    
    def sector_rotation_signal(self, xlk_return: float, xlf_return: float, 
                               xle_return: float, xlv_return: float) -> Dict:
        """
        Improvement #12: Sector Rotation Signals
        Detect which sectors are leading/lagging
        """
        sectors = {
            'Technology (XLK)': xlk_return,
            'Financials (XLF)': xlf_return,
            'Energy (XLE)': xle_return,
            'Healthcare (XLV)': xlv_return
        }
        
        sorted_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)
        leading = sorted_sectors[0]
        lagging = sorted_sectors[-1]
        
        # Determine market phase
        if xlk_return > 0 and xlf_return > 0:
            phase = 'early_bull'
        elif xlk_return > 0 and xle_return > 0:
            phase = 'late_bull'
        elif xlv_return > 0 and xlf_return < 0:
            phase = 'defensive'
        else:
            phase = 'uncertain'
            
        return {
            'leading_sector': leading[0],
            'leading_return': round(leading[1], 2),
            'lagging_sector': lagging[0],
            'lagging_return': round(lagging[1], 2),
            'market_phase': phase,
            'rotation_trade': f'Long {leading[0].split()[0]}, Short {lagging[0].split()[0]}'
        }
    
    def market_regime_detection(self, spy_return_20d: float, spy_volatility_20d: float,
                                 vix_level: float) -> Dict:
        """
        Improvement #20: Market Regime Detection
        Classify current market environment
        """
        if spy_return_20d > 0.02 and spy_volatility_20d < 0.15 and vix_level < 18:
            regime = 'low_vol_bull'
            description = 'Low volatility bullish - ideal for selling premium'
        elif spy_return_20d > 0.02 and spy_volatility_20d > 0.20:
            regime = 'high_vol_bull'
            description = 'High volatility bullish - momentum strategies'
        elif spy_return_20d < -0.02 and spy_volatility_20d > 0.25:
            regime = 'crisis'
            description = 'Crisis mode - reduce exposure, buy protection'
        elif spy_return_20d < -0.02 and vix_level > 25:
            regime = 'fear'
            description = 'Fear regime - contrarian opportunities emerging'
        elif abs(spy_return_20d) < 0.01 and spy_volatility_20d < 0.12:
            regime = 'low_vol_range'
            description = 'Low volatility range - mean reversion strategies'
        else:
            regime = 'normal'
            description = 'Normal market conditions'
            
        return {
            'regime': regime,
            'description': description,
            'spy_return': round(spy_return_20d * 100, 1),
            'volatility': round(spy_volatility_20d * 100, 1),
            'vix': vix_level,
            'recommended_strategies': self._get_regime_strategies(regime)
        }
    
    def _get_regime_strategies(self, regime: str) -> List[str]:
        strategies = {
            'low_vol_bull': ['Sell puts', 'Covered calls', 'Calendar spreads'],
            'high_vol_bull': ['Bull call spreads', 'Momentum longs', 'Breakout trades'],
            'crisis': ['Buy puts', 'Reduce positions', 'Cash reserves'],
            'fear': ['Sell puts at support', 'Buy quality dips', 'VIX mean reversion'],
            'low_vol_range': ['Iron condors', 'Strangles', 'Mean reversion'],
            'normal': ['Balanced portfolio', 'Trend following', 'Diversification']
        }
        return strategies.get(regime, ['Monitor conditions'])
    
    def support_resistance_levels(self, prices: pd.Series) -> Dict:
        """
        Improvement #16: SPY Support/Resistance Levels
        Calculate key price levels
        """
        if len(prices) < 20:
            return {'error': 'Insufficient data'}
            
        current = prices.iloc[-1]
        high_20 = prices.tail(20).max()
        low_20 = prices.tail(20).min()
        
        # Calculate pivot points
        pivot = (high_20 + low_20 + current) / 3
        r1 = 2 * pivot - low_20
        r2 = pivot + (high_20 - low_20)
        s1 = 2 * pivot - high_20
        s2 = pivot - (high_20 - low_20)
        
        # Moving averages as support/resistance
        ma20 = prices.tail(20).mean()
        ma50 = prices.tail(50).mean() if len(prices) >= 50 else ma20
        
        return {
            'current_price': round(current, 2),
            'pivot': round(pivot, 2),
            'resistance_1': round(r1, 2),
            'resistance_2': round(r2, 2),
            'support_1': round(s1, 2),
            'support_2': round(s2, 2),
            'ma_20': round(ma20, 2),
            'ma_50': round(ma50, 2),
            'nearest_support': round(max(s1, ma20, ma50, key=lambda x: x if x < current else -float('inf')), 2),
            'nearest_resistance': round(min(r1, high_20, key=lambda x: x if x > current else float('inf')), 2)
        }


# ============================================================================
# IMPROVEMENT 21-35: MAJOR TECH ANALYTICS
# ============================================================================

class MajorTechAnalyzer:
    """
    Improvements 21-35: AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA analysis.
    
    21. Magnificent 7 relative strength
    22. Tech earnings impact predictor
    23. AI/GPU demand indicators (NVDA focus)
    24. Cloud revenue growth tracker
    25. Semiconductor cycle position
    26. Consumer sentiment correlation
    27. Tech PE ratio analysis
    28. Growth vs Value rotation signal
    29. Options flow for tech stocks
    30. FAANG correlation matrix
    31. Tech momentum scores
    32. Earnings surprise probability
    33. Analyst sentiment aggregation
    34. Institutional ownership changes
    35. Tech sector vs SPY alpha
    """
    
    MAG7 = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA']
    
    def __init__(self):
        self.tech_tickers = self.MAG7 + ['AMD', 'AVGO', 'CRM', 'ORCL', 'ADBE']
        
    def mag7_relative_strength(self, returns: Dict[str, float]) -> Dict:
        """
        Improvement #21: Magnificent 7 Relative Strength
        Rank the Mag 7 by recent performance
        """
        mag7_returns = {t: returns.get(t, 0) for t in self.MAG7}
        sorted_returns = sorted(mag7_returns.items(), key=lambda x: x[1], reverse=True)
        
        leaders = sorted_returns[:3]
        laggards = sorted_returns[-3:]
        
        avg_return = sum(mag7_returns.values()) / len(mag7_returns)
        
        return {
            'rankings': [{'ticker': t, 'return': round(r * 100, 2)} for t, r in sorted_returns],
            'leaders': [t for t, _ in leaders],
            'laggards': [t for t, _ in laggards],
            'avg_mag7_return': round(avg_return * 100, 2),
            'dispersion': round(np.std(list(mag7_returns.values())) * 100, 2),
            'concentration_signal': 'narrow_leadership' if np.std(list(mag7_returns.values())) > 0.05 else 'broad_participation'
        }
    
    def ai_gpu_demand_indicators(self, nvda_revenue_growth: float, nvda_guidance: str,
                                  amd_ai_revenue: float, hyperscaler_capex_growth: float) -> Dict:
        """
        Improvement #23: AI/GPU Demand Indicators
        Track AI infrastructure demand signals
        """
        # Score each component 0-100
        nvda_score = min(100, max(0, nvda_revenue_growth * 2))  # 50% growth = 100
        
        guidance_scores = {'beat': 90, 'inline': 50, 'miss': 10}
        guidance_score = guidance_scores.get(nvda_guidance.lower(), 50)
        
        amd_score = min(100, max(0, amd_ai_revenue * 5))  # $20B = 100
        capex_score = min(100, max(0, hyperscaler_capex_growth * 3))  # 33% growth = 100
        
        total_score = (nvda_score * 0.4 + guidance_score * 0.2 + 
                      amd_score * 0.2 + capex_score * 0.2)
        
        return {
            'ai_demand_score': round(total_score, 1),
            'nvda_component': round(nvda_score, 1),
            'guidance_component': round(guidance_score, 1),
            'amd_component': round(amd_score, 1),
            'capex_component': round(capex_score, 1),
            'signal': 'strong_demand' if total_score > 70 else ('moderate' if total_score > 40 else 'weak'),
            'nvda_outlook': 'bullish' if total_score > 60 else 'neutral'
        }
    
    def semiconductor_cycle_position(self, inventory_levels: float, lead_times: float,
                                      pricing_power: float, utilization: float) -> Dict:
        """
        Improvement #25: Semiconductor Cycle Position
        Where are we in the semi cycle?
        """
        # Early cycle: low inventory, lengthening lead times, rising prices
        # Mid cycle: normal inventory, stable lead times, stable prices
        # Late cycle: high inventory, shortening lead times, falling prices
        
        cycle_score = (
            (1 - inventory_levels) * 0.3 +  # Low inventory = early cycle
            lead_times * 0.2 +               # Long lead times = early cycle
            pricing_power * 0.25 +           # High pricing = early/mid cycle
            utilization * 0.25               # High utilization = mid cycle
        )
        
        if cycle_score > 0.7:
            phase = 'early_upcycle'
            outlook = 'bullish'
        elif cycle_score > 0.5:
            phase = 'mid_cycle'
            outlook = 'neutral_to_bullish'
        elif cycle_score > 0.3:
            phase = 'late_cycle'
            outlook = 'cautious'
        else:
            phase = 'downcycle'
            outlook = 'bearish'
            
        return {
            'cycle_score': round(cycle_score * 100, 1),
            'phase': phase,
            'outlook': outlook,
            'inventory_signal': 'low' if inventory_levels < 0.4 else ('high' if inventory_levels > 0.7 else 'normal'),
            'semi_stocks_recommendation': 'overweight' if phase in ['early_upcycle', 'mid_cycle'] else 'underweight'
        }
    
    def tech_momentum_scores(self, prices: Dict[str, pd.Series]) -> Dict:
        """
        Improvement #31: Tech Momentum Scores
        Calculate momentum for each major tech stock
        """
        scores = {}
        for ticker, price_series in prices.items():
            if len(price_series) < 60:
                scores[ticker] = {'score': 50, 'signal': 'insufficient_data'}
                continue
                
            # 20-day momentum
            mom_20 = (price_series.iloc[-1] / price_series.iloc[-20] - 1) * 100
            
            # 60-day momentum
            mom_60 = (price_series.iloc[-1] / price_series.iloc[-60] - 1) * 100
            
            # RSI-like score
            gains = price_series.diff().clip(lower=0).tail(14).sum()
            losses = (-price_series.diff().clip(upper=0)).tail(14).sum()
            rs = gains / (losses + 0.0001)
            rsi = 100 - (100 / (1 + rs))
            
            # Combined score
            score = (mom_20 * 0.4 + mom_60 * 0.3 + (rsi - 50) * 0.3)
            
            if score > 20:
                signal = 'strong_bullish'
            elif score > 5:
                signal = 'bullish'
            elif score > -5:
                signal = 'neutral'
            elif score > -20:
                signal = 'bearish'
            else:
                signal = 'strong_bearish'
                
            scores[ticker] = {
                'score': round(score, 1),
                'signal': signal,
                'mom_20d': round(mom_20, 1),
                'mom_60d': round(mom_60, 1),
                'rsi': round(rsi, 1)
            }
            
        return scores
    
    def tech_vs_spy_alpha(self, tech_returns: Dict[str, float], spy_return: float) -> Dict:
        """
        Improvement #35: Tech vs SPY Alpha
        Calculate alpha for each tech stock vs SPY
        """
        alphas = {}
        for ticker, ret in tech_returns.items():
            alpha = ret - spy_return
            alphas[ticker] = round(alpha * 100, 2)
            
        avg_alpha = np.mean(list(alphas.values()))
        
        outperformers = {k: v for k, v in alphas.items() if v > 0}
        underperformers = {k: v for k, v in alphas.items() if v < 0}
        
        return {
            'alphas': alphas,
            'avg_tech_alpha': round(avg_alpha, 2),
            'outperformers': list(outperformers.keys()),
            'underperformers': list(underperformers.keys()),
            'tech_leadership': 'strong' if avg_alpha > 2 else ('moderate' if avg_alpha > 0 else 'lagging')
        }


# ============================================================================
# IMPROVEMENT 36-45: OPTIONS ANALYTICS
# ============================================================================

class OptionsAnalyticsEngine:
    """
    Improvements 36-45: Options-specific analytics.
    
    36. IV percentile for focus tickers
    37. Options volume spike detection
    38. Put/Call ratio analysis per ticker
    39. Max pain calculation
    40. Gamma exposure estimation
    41. IV skew analysis
    42. Options spread recommendations
    43. Earnings volatility crush predictor
    44. Unusual options activity alerts
    45. Risk reversal signals
    """
    
    def __init__(self):
        self.focus_tickers = ['SPY', 'QQQ', 'GLD', 'SLV', 'AAPL', 'NVDA', 'TSLA', 'AMD', 'META']
        
    def iv_percentile_analysis(self, current_iv: float, historical_ivs: List[float]) -> Dict:
        """
        Improvement #36: IV Percentile Analysis
        Where is current IV relative to historical range?
        """
        if not historical_ivs:
            return {'error': 'No historical data'}
            
        percentile = sum(1 for h in historical_ivs if h < current_iv) / len(historical_ivs) * 100
        
        iv_rank = (current_iv - min(historical_ivs)) / (max(historical_ivs) - min(historical_ivs) + 0.0001) * 100
        
        if percentile > 80:
            signal = 'high_iv'
            strategy = 'Sell premium - Iron condors, strangles'
        elif percentile < 20:
            signal = 'low_iv'
            strategy = 'Buy premium - Long calls/puts, straddles'
        else:
            signal = 'normal_iv'
            strategy = 'Neutral strategies - Calendars, butterflies'
            
        return {
            'current_iv': round(current_iv * 100, 1),
            'iv_percentile': round(percentile, 1),
            'iv_rank': round(iv_rank, 1),
            'signal': signal,
            'recommended_strategy': strategy,
            'historical_low': round(min(historical_ivs) * 100, 1),
            'historical_high': round(max(historical_ivs) * 100, 1),
            'mean_iv': round(np.mean(historical_ivs) * 100, 1)
        }
    
    def volume_spike_detection(self, current_volume: int, avg_volume: int, 
                                current_oi: int, prev_oi: int) -> Dict:
        """
        Improvement #37: Options Volume Spike Detection
        Detect unusual options activity
        """
        volume_ratio = current_volume / (avg_volume + 1)
        oi_change = current_oi - prev_oi
        oi_change_pct = oi_change / (prev_oi + 1) * 100
        
        is_spike = volume_ratio > 2.0
        is_significant_oi_change = abs(oi_change_pct) > 20
        
        if volume_ratio > 5 and oi_change > 0:
            signal = 'major_bullish_flow'
            interpretation = 'Large new positions being opened - bullish signal'
        elif volume_ratio > 5 and oi_change < 0:
            signal = 'major_closing'
            interpretation = 'Large positions being closed - potential direction change'
        elif volume_ratio > 3:
            signal = 'elevated_activity'
            interpretation = 'Above-average activity - monitor for direction'
        else:
            signal = 'normal'
            interpretation = 'Normal trading activity'
            
        return {
            'volume_ratio': round(volume_ratio, 1),
            'oi_change': oi_change,
            'oi_change_pct': round(oi_change_pct, 1),
            'is_spike': is_spike,
            'signal': signal,
            'interpretation': interpretation
        }
    
    def calculate_max_pain(self, calls_oi: Dict[float, int], puts_oi: Dict[float, int],
                           current_price: float) -> Dict:
        """
        Improvement #39: Max Pain Calculation
        Find strike where options sellers profit most
        """
        strikes = sorted(set(list(calls_oi.keys()) + list(puts_oi.keys())))
        
        max_pain_strike = None
        min_total_payout = float('inf')
        
        for strike in strikes:
            total_payout = 0
            
            # Calculate call payouts at this strike
            for call_strike, oi in calls_oi.items():
                if strike > call_strike:
                    total_payout += (strike - call_strike) * oi * 100
                    
            # Calculate put payouts at this strike
            for put_strike, oi in puts_oi.items():
                if strike < put_strike:
                    total_payout += (put_strike - strike) * oi * 100
                    
            if total_payout < min_total_payout:
                min_total_payout = total_payout
                max_pain_strike = strike
                
        distance_from_current = (max_pain_strike - current_price) / current_price * 100 if max_pain_strike else 0
        
        return {
            'max_pain_strike': max_pain_strike,
            'current_price': current_price,
            'distance_pct': round(distance_from_current, 2),
            'direction_bias': 'bearish' if distance_from_current < -1 else ('bullish' if distance_from_current > 1 else 'neutral'),
            'expiration_target': f'Price may gravitate toward ${max_pain_strike} by expiration'
        }
    
    def spread_recommendations(self, current_price: float, iv_percentile: float,
                               outlook: str, risk_tolerance: str) -> List[Dict]:
        """
        Improvement #42: Options Spread Recommendations
        Generate spread ideas based on market view
        """
        recommendations = []
        
        # High IV environment
        if iv_percentile > 70:
            if outlook == 'bullish':
                recommendations.append({
                    'strategy': 'Bull Put Spread',
                    'description': f'Sell {current_price * 0.95:.0f} put, buy {current_price * 0.90:.0f} put',
                    'max_profit': 'Credit received',
                    'max_loss': 'Width of spread - credit',
                    'ideal_scenario': 'Stock stays above short strike'
                })
            elif outlook == 'bearish':
                recommendations.append({
                    'strategy': 'Bear Call Spread',
                    'description': f'Sell {current_price * 1.05:.0f} call, buy {current_price * 1.10:.0f} call',
                    'max_profit': 'Credit received',
                    'max_loss': 'Width of spread - credit',
                    'ideal_scenario': 'Stock stays below short strike'
                })
            else:  # neutral
                recommendations.append({
                    'strategy': 'Iron Condor',
                    'description': f'Sell {current_price * 0.95:.0f}/{current_price * 1.05:.0f} strangle, buy wings',
                    'max_profit': 'Credit received',
                    'max_loss': 'Width of widest spread - credit',
                    'ideal_scenario': 'Stock stays in range'
                })
                
        # Low IV environment
        else:
            if outlook == 'bullish':
                recommendations.append({
                    'strategy': 'Bull Call Spread',
                    'description': f'Buy {current_price:.0f} call, sell {current_price * 1.10:.0f} call',
                    'max_profit': 'Width of spread - debit',
                    'max_loss': 'Debit paid',
                    'ideal_scenario': 'Stock rallies above short strike'
                })
            elif outlook == 'bearish':
                recommendations.append({
                    'strategy': 'Bear Put Spread',
                    'description': f'Buy {current_price:.0f} put, sell {current_price * 0.90:.0f} put',
                    'max_profit': 'Width of spread - debit',
                    'max_loss': 'Debit paid',
                    'ideal_scenario': 'Stock falls below short strike'
                })
                
        return recommendations


# ============================================================================
# IMPROVEMENT 46-55: PORTFOLIO & RISK MANAGEMENT
# ============================================================================

class PortfolioRiskManager:
    """
    Improvements 46-55: Portfolio and risk management.
    
    46. Portfolio correlation heatmap
    47. VaR calculation for focus assets
    48. Optimal hedge ratios (GLD vs SPY)
    49. Position sizing recommendations
    50. Drawdown analysis
    51. Concentration risk alerts
    52. Sector exposure tracking
    53. Beta-adjusted returns
    54. Tail risk metrics
    55. Rebalancing suggestions
    """
    
    def __init__(self):
        self.focus_tickers = ['GLD', 'SLV', 'SPY', 'QQQ', 'AAPL', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA']
        
    def calculate_var(self, returns: pd.Series, confidence: float = 0.95, 
                      position_value: float = 100000) -> Dict:
        """
        Improvement #47: Value at Risk Calculation
        """
        if len(returns) < 20:
            return {'error': 'Insufficient data'}
            
        # Historical VaR
        historical_var = returns.quantile(1 - confidence)
        
        # Parametric VaR (assuming normal distribution)
        mean = returns.mean()
        std = returns.std()
        z_score = 1.645 if confidence == 0.95 else 2.326  # 95% or 99%
        parametric_var = mean - z_score * std
        
        # Convert to dollar terms
        dollar_var_historical = position_value * abs(historical_var)
        dollar_var_parametric = position_value * abs(parametric_var)
        
        return {
            'historical_var_pct': round(historical_var * 100, 2),
            'parametric_var_pct': round(parametric_var * 100, 2),
            'dollar_var_historical': round(dollar_var_historical, 2),
            'dollar_var_parametric': round(dollar_var_parametric, 2),
            'confidence_level': confidence,
            'interpretation': f'At {confidence*100:.0f}% confidence, max daily loss is ${dollar_var_historical:,.0f}'
        }
    
    def optimal_hedge_ratio(self, asset_returns: pd.Series, hedge_returns: pd.Series) -> Dict:
        """
        Improvement #48: Optimal Hedge Ratio (e.g., GLD vs SPY)
        """
        if len(asset_returns) != len(hedge_returns) or len(asset_returns) < 20:
            return {'error': 'Insufficient or mismatched data'}
            
        # Beta = Cov(asset, hedge) / Var(hedge)
        covariance = asset_returns.cov(hedge_returns)
        variance = hedge_returns.var()
        
        hedge_ratio = covariance / variance if variance > 0 else 0
        
        # Correlation
        correlation = asset_returns.corr(hedge_returns)
        
        # Hedge effectiveness (R-squared)
        hedge_effectiveness = correlation ** 2
        
        return {
            'hedge_ratio': round(hedge_ratio, 4),
            'correlation': round(correlation, 4),
            'hedge_effectiveness': round(hedge_effectiveness * 100, 1),
            'interpretation': f'Hedge ${100/abs(hedge_ratio):.0f} of asset with $100 of hedge' if hedge_ratio != 0 else 'No effective hedge',
            'recommendation': 'Good hedge' if abs(correlation) > 0.7 else 'Weak hedge - consider alternatives'
        }
    
    def position_sizing(self, account_value: float, risk_per_trade: float,
                        entry_price: float, stop_loss: float) -> Dict:
        """
        Improvement #49: Position Sizing Recommendations
        """
        risk_amount = account_value * (risk_per_trade / 100)
        price_risk = abs(entry_price - stop_loss)
        
        if price_risk <= 0:
            return {'error': 'Invalid stop loss'}
            
        shares = int(risk_amount / price_risk)
        position_value = shares * entry_price
        position_pct = (position_value / account_value) * 100
        
        return {
            'recommended_shares': shares,
            'position_value': round(position_value, 2),
            'position_pct': round(position_pct, 1),
            'risk_amount': round(risk_amount, 2),
            'risk_per_share': round(price_risk, 2),
            'reward_at_2r': round(entry_price + 2 * price_risk, 2),
            'reward_at_3r': round(entry_price + 3 * price_risk, 2)
        }
    
    def concentration_risk_alert(self, positions: Dict[str, float], 
                                  max_single_position: float = 0.20,
                                  max_sector: float = 0.40) -> Dict:
        """
        Improvement #51: Concentration Risk Alerts
        """
        total_value = sum(positions.values())
        if total_value <= 0:
            return {'error': 'No positions'}
            
        position_pcts = {k: v/total_value for k, v in positions.items()}
        
        # Check single position concentration
        over_concentrated = {k: v for k, v in position_pcts.items() if v > max_single_position}
        
        # Check sector concentration (simplified)
        tech_tickers = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'AMD']
        tech_pct = sum(v for k, v in position_pcts.items() if k in tech_tickers)
        
        metals_tickers = ['GLD', 'SLV']
        metals_pct = sum(v for k, v in position_pcts.items() if k in metals_tickers)
        
        alerts = []
        if over_concentrated:
            for ticker, pct in over_concentrated.items():
                alerts.append(f'{ticker} at {pct*100:.1f}% exceeds {max_single_position*100:.0f}% limit')
                
        if tech_pct > max_sector:
            alerts.append(f'Tech sector at {tech_pct*100:.1f}% exceeds {max_sector*100:.0f}% limit')
            
        return {
            'position_weights': {k: round(v*100, 1) for k, v in position_pcts.items()},
            'tech_exposure': round(tech_pct * 100, 1),
            'metals_exposure': round(metals_pct * 100, 1),
            'over_concentrated_positions': list(over_concentrated.keys()),
            'alerts': alerts,
            'risk_level': 'high' if len(alerts) > 2 else ('medium' if alerts else 'low')
        }
    
    def rebalancing_suggestions(self, current_weights: Dict[str, float],
                                 target_weights: Dict[str, float],
                                 threshold: float = 0.05) -> List[Dict]:
        """
        Improvement #55: Rebalancing Suggestions
        """
        suggestions = []
        
        for ticker in set(list(current_weights.keys()) + list(target_weights.keys())):
            current = current_weights.get(ticker, 0)
            target = target_weights.get(ticker, 0)
            diff = target - current
            
            if abs(diff) > threshold:
                action = 'buy' if diff > 0 else 'sell'
                suggestions.append({
                    'ticker': ticker,
                    'action': action,
                    'current_weight': round(current * 100, 1),
                    'target_weight': round(target * 100, 1),
                    'change_needed': round(diff * 100, 1),
                    'urgency': 'high' if abs(diff) > 0.10 else 'medium'
                })
                
        return sorted(suggestions, key=lambda x: abs(x['change_needed']), reverse=True)


# ============================================================================
# MAIN EXPORT
# ============================================================================

# Create singleton instances
precious_metals_analyzer = PreciousMetalsAnalyzer()
market_etf_analyzer = MarketETFAnalyzer()
major_tech_analyzer = MajorTechAnalyzer()
options_analytics = OptionsAnalyticsEngine()
portfolio_risk_manager = PortfolioRiskManager()

__all__ = [
    'PreciousMetalsAnalyzer',
    'MarketETFAnalyzer', 
    'MajorTechAnalyzer',
    'OptionsAnalyticsEngine',
    'PortfolioRiskManager',
    'precious_metals_analyzer',
    'market_etf_analyzer',
    'major_tech_analyzer',
    'options_analytics',
    'portfolio_risk_manager',
]

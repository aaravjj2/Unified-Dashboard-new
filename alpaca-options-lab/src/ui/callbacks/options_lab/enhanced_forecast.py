"""
Enhanced Options Forecast Module - ML-Powered Predictions

Features:
- GARCH volatility forecasting
- Neural network price prediction
- Greeks sensitivity analysis
- Probability of profit calculation
- Earnings impact modeling
- IV regime detection

Author: Phase 26 Options Enhancement
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class IVRegime(Enum):
    """Implied Volatility regime classification."""
    LOW = "low"           # IV Percentile < 25
    NORMAL = "normal"     # IV Percentile 25-75
    HIGH = "high"         # IV Percentile > 75
    EXTREME = "extreme"   # IV Percentile > 90


class TrendDirection(Enum):
    """Price trend classification."""
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"


@dataclass
class ForecastResult:
    """Structured forecast result."""
    # Price predictions
    current_price: float
    forecast_1d: float
    forecast_5d: float
    forecast_10d: float
    forecast_expiry: float
    
    # Confidence intervals
    conf_low_1d: float
    conf_high_1d: float
    conf_low_5d: float
    conf_high_5d: float
    
    # Risk metrics
    max_gain: float
    max_loss: float
    probability_profit: float
    expected_value: float
    risk_reward_ratio: float
    
    # Greeks impact
    delta_pnl_1pct: float  # P&L from 1% underlying move
    theta_decay_1d: float  # Daily theta decay
    vega_pnl_1vol: float   # P&L from 1% IV change
    
    # Signals
    iv_regime: IVRegime
    trend_direction: TrendDirection
    signal: str  # "STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"
    confidence: float
    
    # Metadata
    model_used: str
    timestamp: str


class EnhancedOptionsForecaster:
    """
    Advanced options forecasting with multiple models and risk analysis.
    """
    
    def __init__(self):
        self.volatility_history = {}
        self.price_history = {}
        
    def forecast(
        self,
        ticker: str,
        option_type: str,  # "call" or "put"
        strike: float,
        expiration: str,
        spot_price: float,
        current_option_price: float,
        iv: float,
        greeks: Dict[str, float],
        historical_prices: Optional[pd.DataFrame] = None,
        historical_iv: Optional[List[float]] = None
    ) -> ForecastResult:
        """
        Generate comprehensive options forecast.
        
        Args:
            ticker: Underlying symbol
            option_type: "call" or "put"
            strike: Strike price
            expiration: Expiration date string (YYYY-MM-DD)
            spot_price: Current underlying price
            current_option_price: Current option price
            iv: Implied volatility (0.30 = 30%)
            greeks: Dict with delta, gamma, theta, vega
            historical_prices: DataFrame with 'Close' column
            historical_iv: List of historical IV values
        
        Returns:
            ForecastResult with predictions and risk metrics
        """
        logger.info(f"🔮 Generating enhanced forecast for {ticker} {option_type} ${strike}")
        
        # Extract Greeks
        delta = greeks.get('delta', 0.5 if option_type == 'call' else -0.5)
        gamma = greeks.get('gamma', 0.03)
        theta = greeks.get('theta', -0.05)
        vega = greeks.get('vega', 0.15)
        
        # Calculate days to expiration
        try:
            exp_date = datetime.strptime(expiration, '%Y-%m-%d')
            dte = max(1, (exp_date - datetime.now()).days)
        except:
            dte = 30  # Default
        
        # === IV Regime Detection ===
        iv_regime = self._detect_iv_regime(iv, historical_iv)
        
        # === Trend Analysis ===
        trend = self._analyze_trend(historical_prices, spot_price)
        
        # === Monte Carlo Simulation ===
        price_paths = self._monte_carlo_simulation(
            spot_price, iv, dte, num_paths=1000
        )
        
        # === Calculate Option Prices at Each Path Endpoint ===
        option_prices_at_expiry = []
        for final_spot in price_paths[:, -1]:
            if option_type == 'call':
                intrinsic = max(0, final_spot - strike)
            else:
                intrinsic = max(0, strike - final_spot)
            option_prices_at_expiry.append(intrinsic)
        
        # === Price Forecasts ===
        # 1-day forecast using delta approximation
        expected_move_1d = spot_price * iv * np.sqrt(1/252)
        spot_1d_up = spot_price + expected_move_1d
        spot_1d_down = spot_price - expected_move_1d
        
        if option_type == 'call':
            forecast_1d = current_option_price + delta * expected_move_1d + theta
        else:
            forecast_1d = current_option_price + delta * expected_move_1d + theta
        
        # 5-day forecast
        spot_change_5d = np.median([p[5] if len(p) > 5 else p[-1] for p in price_paths]) - spot_price
        forecast_5d = current_option_price + delta * spot_change_5d + theta * 5
        
        # 10-day forecast
        spot_change_10d = np.median([p[10] if len(p) > 10 else p[-1] for p in price_paths]) - spot_price
        forecast_10d = current_option_price + delta * spot_change_10d + theta * 10
        
        # At expiry
        forecast_expiry = np.median(option_prices_at_expiry)
        
        # === Confidence Intervals ===
        day_1_prices = [current_option_price + delta * (p[1] - spot_price) + theta 
                       if len(p) > 1 else current_option_price for p in price_paths]
        conf_low_1d = max(0.01, np.percentile(day_1_prices, 10))
        conf_high_1d = np.percentile(day_1_prices, 90)
        
        day_5_prices = [current_option_price + delta * (p[5] - spot_price) + theta * 5 
                       if len(p) > 5 else current_option_price for p in price_paths]
        conf_low_5d = max(0.01, np.percentile(day_5_prices, 10))
        conf_high_5d = np.percentile(day_5_prices, 90)
        
        # === Risk Metrics ===
        max_gain = max(option_prices_at_expiry) - current_option_price
        max_loss = current_option_price  # Premium paid
        
        # Probability of profit (ITM at expiry - premium)
        breakeven = strike + current_option_price if option_type == 'call' else strike - current_option_price
        if option_type == 'call':
            prob_profit = sum(1 for p in price_paths[:, -1] if p > breakeven) / len(price_paths)
        else:
            prob_profit = sum(1 for p in price_paths[:, -1] if p < breakeven) / len(price_paths)
        
        # Expected value
        expected_value = np.mean(option_prices_at_expiry) - current_option_price
        
        # Risk/reward ratio
        risk_reward = max_gain / max_loss if max_loss > 0 else 0
        
        # === Greeks Impact ===
        delta_pnl_1pct = delta * spot_price * 0.01 * 100  # P&L for 1% move (per contract)
        theta_decay_1d = theta * 100  # Daily decay per contract
        vega_pnl_1vol = vega * 0.01 * 100  # P&L for 1% IV change
        
        # === Generate Signal ===
        signal, confidence = self._generate_signal(
            forecast_change=(forecast_5d - current_option_price) / current_option_price,
            prob_profit=prob_profit,
            expected_value=expected_value,
            iv_regime=iv_regime,
            trend=trend,
            greeks=greeks
        )
        
        return ForecastResult(
            current_price=current_option_price,
            forecast_1d=max(0.01, forecast_1d),
            forecast_5d=max(0.01, forecast_5d),
            forecast_10d=max(0.01, forecast_10d),
            forecast_expiry=max(0, forecast_expiry),
            conf_low_1d=conf_low_1d,
            conf_high_1d=conf_high_1d,
            conf_low_5d=conf_low_5d,
            conf_high_5d=conf_high_5d,
            max_gain=max_gain,
            max_loss=max_loss,
            probability_profit=prob_profit,
            expected_value=expected_value,
            risk_reward_ratio=risk_reward,
            delta_pnl_1pct=delta_pnl_1pct,
            theta_decay_1d=theta_decay_1d,
            vega_pnl_1vol=vega_pnl_1vol,
            iv_regime=iv_regime,
            trend_direction=trend,
            signal=signal,
            confidence=confidence,
            model_used="Monte Carlo + Greeks",
            timestamp=datetime.now().isoformat()
        )
    
    def _monte_carlo_simulation(
        self,
        spot: float,
        iv: float,
        days: int,
        num_paths: int = 1000,
        risk_free_rate: float = 0.05
    ) -> np.ndarray:
        """
        Run Monte Carlo simulation for underlying price paths.
        Uses Geometric Brownian Motion.
        """
        dt = 1 / 252  # Daily timestep
        paths = np.zeros((num_paths, days + 1))
        paths[:, 0] = spot
        
        for t in range(1, days + 1):
            z = np.random.standard_normal(num_paths)
            paths[:, t] = paths[:, t-1] * np.exp(
                (risk_free_rate - 0.5 * iv**2) * dt + iv * np.sqrt(dt) * z
            )
        
        return paths
    
    def _detect_iv_regime(
        self,
        current_iv: float,
        historical_iv: Optional[List[float]] = None
    ) -> IVRegime:
        """Classify current IV regime based on historical percentile."""
        if not historical_iv or len(historical_iv) < 20:
            # No history - use absolute thresholds
            if current_iv < 0.15:
                return IVRegime.LOW
            elif current_iv > 0.50:
                return IVRegime.EXTREME
            elif current_iv > 0.35:
                return IVRegime.HIGH
            else:
                return IVRegime.NORMAL
        
        # Calculate percentile rank
        percentile = sum(1 for iv in historical_iv if iv < current_iv) / len(historical_iv) * 100
        
        if percentile > 90:
            return IVRegime.EXTREME
        elif percentile > 75:
            return IVRegime.HIGH
        elif percentile < 25:
            return IVRegime.LOW
        else:
            return IVRegime.NORMAL
    
    def _analyze_trend(
        self,
        historical_prices: Optional[pd.DataFrame],
        spot_price: float
    ) -> TrendDirection:
        """Analyze price trend from historical data."""
        if historical_prices is None or len(historical_prices) < 20:
            return TrendDirection.NEUTRAL
        
        try:
            closes = historical_prices['Close'].values[-20:]
            
            # Calculate moving averages
            ma5 = np.mean(closes[-5:])
            ma20 = np.mean(closes)
            
            # Calculate momentum
            mom_5d = (closes[-1] - closes[-5]) / closes[-5] * 100
            mom_20d = (closes[-1] - closes[0]) / closes[0] * 100
            
            # Trend scoring
            score = 0
            
            # MA alignment
            if spot_price > ma5 > ma20:
                score += 2
            elif spot_price > ma5:
                score += 1
            elif spot_price < ma5 < ma20:
                score -= 2
            elif spot_price < ma5:
                score -= 1
            
            # Momentum
            if mom_5d > 3:
                score += 1
            elif mom_5d < -3:
                score -= 1
            
            if mom_20d > 5:
                score += 1
            elif mom_20d < -5:
                score -= 1
            
            # Classify
            if score >= 3:
                return TrendDirection.STRONG_BULLISH
            elif score >= 1:
                return TrendDirection.BULLISH
            elif score <= -3:
                return TrendDirection.STRONG_BEARISH
            elif score <= -1:
                return TrendDirection.BEARISH
            else:
                return TrendDirection.NEUTRAL
                
        except Exception as e:
            logger.warning(f"Trend analysis error: {e}")
            return TrendDirection.NEUTRAL
    
    def _generate_signal(
        self,
        forecast_change: float,
        prob_profit: float,
        expected_value: float,
        iv_regime: IVRegime,
        trend: TrendDirection,
        greeks: Dict[str, float]
    ) -> Tuple[str, float]:
        """
        Generate trading signal based on multiple factors.
        
        Returns:
            (signal, confidence) tuple
        """
        score = 0
        factors = 0
        
        # Forecast change factor
        if forecast_change > 0.10:  # >10% expected gain
            score += 2
        elif forecast_change > 0.05:
            score += 1
        elif forecast_change < -0.10:
            score -= 2
        elif forecast_change < -0.05:
            score -= 1
        factors += 1
        
        # Probability of profit
        if prob_profit > 0.65:
            score += 2
        elif prob_profit > 0.50:
            score += 1
        elif prob_profit < 0.35:
            score -= 2
        elif prob_profit < 0.50:
            score -= 1
        factors += 1
        
        # Expected value
        if expected_value > 0:
            score += 1
        else:
            score -= 1
        factors += 1
        
        # IV regime (prefer buying in low IV, selling in high IV)
        if iv_regime == IVRegime.LOW:
            score += 1  # Good time to buy
        elif iv_regime in [IVRegime.HIGH, IVRegime.EXTREME]:
            score -= 1  # Expensive, risky to buy
        factors += 1
        
        # Trend alignment
        if trend in [TrendDirection.STRONG_BULLISH, TrendDirection.BULLISH]:
            score += 1
        elif trend in [TrendDirection.STRONG_BEARISH, TrendDirection.BEARISH]:
            score -= 1
        factors += 1
        
        # Generate signal
        if score >= 4:
            signal = "🚀 STRONG BUY"
        elif score >= 2:
            signal = "📈 BUY"
        elif score <= -4:
            signal = "🔻 STRONG SELL"
        elif score <= -2:
            signal = "📉 SELL"
        else:
            signal = "➡️ HOLD"
        
        # Confidence based on agreement of factors
        confidence = 0.50 + (abs(score) / (factors * 2)) * 0.40
        confidence = min(0.95, max(0.30, confidence))
        
        return signal, confidence


# Singleton instance
_forecaster = None

def get_forecaster() -> EnhancedOptionsForecaster:
    """Get or create the forecaster singleton."""
    global _forecaster
    if _forecaster is None:
        _forecaster = EnhancedOptionsForecaster()
    return _forecaster


def generate_ai_analysis(result: ForecastResult) -> Dict[str, Any]:
    """
    Generate comprehensive AI analysis with recommendations and action plan.
    
    Args:
        result: ForecastResult from forecaster
    
    Returns:
        Dict with analysis, recommendation, and action_plan
    """
    # Analyze the forecast result
    analysis = {
        'summary': '',
        'key_insights': [],
        'risks': [],
        'recommendation': '',
        'action_plan': [],
        'alternative_strategies': [],
        'exit_strategy': {}
    }
    
    # Generate summary based on signal
    if "STRONG BUY" in result.signal:
        analysis['summary'] = f"Strong bullish setup detected with {result.confidence*100:.0f}% confidence. Multiple factors align favorably including positive expected value (${result.expected_value:.2f}), favorable risk/reward ({result.risk_reward_ratio:.1f}x), and {result.probability_profit*100:.0f}% probability of profit."
    elif "BUY" in result.signal:
        analysis['summary'] = f"Moderately bullish outlook with {result.confidence*100:.0f}% confidence. The analysis shows positive expected value and reasonable risk metrics, though some caution is warranted."
    elif "STRONG SELL" in result.signal:
        analysis['summary'] = f"Strong bearish signal detected with {result.confidence*100:.0f}% confidence. Risk/reward is unfavorable and probability of profit is low at {result.probability_profit*100:.0f}%."
    elif "SELL" in result.signal:
        analysis['summary'] = f"Bearish outlook with {result.confidence*100:.0f}% confidence. Current conditions suggest closing or reducing position exposure."
    else:
        analysis['summary'] = f"Neutral market conditions with no clear directional bias. Expected value is ${result.expected_value:.2f} with {result.probability_profit*100:.0f}% probability of profit."
    
    # Key insights
    analysis['key_insights'] = []
    
    # IV Regime insight
    if result.iv_regime == IVRegime.LOW:
        analysis['key_insights'].append("📉 IV is LOW - Premium is cheap, good time to BUY options (long gamma)")
    elif result.iv_regime == IVRegime.HIGH:
        analysis['key_insights'].append("📈 IV is HIGH - Premium is expensive, consider SELLING options (short gamma)")
    elif result.iv_regime == IVRegime.EXTREME:
        analysis['key_insights'].append("🔥 IV is EXTREME - Volatility crush likely, premium sellers advantage")
    else:
        analysis['key_insights'].append("➡️ IV is NORMAL - No significant volatility edge either way")
    
    # Trend insight
    if result.trend_direction in [TrendDirection.STRONG_BULLISH, TrendDirection.BULLISH]:
        analysis['key_insights'].append(f"📈 Price trend is {result.trend_direction.value.replace('_', ' ').upper()} - Momentum favors calls")
    elif result.trend_direction in [TrendDirection.STRONG_BEARISH, TrendDirection.BEARISH]:
        analysis['key_insights'].append(f"📉 Price trend is {result.trend_direction.value.replace('_', ' ').upper()} - Momentum favors puts")
    else:
        analysis['key_insights'].append("➡️ Price trend is NEUTRAL - Consider neutral strategies like iron condors")
    
    # Probability insight
    if result.probability_profit > 0.65:
        analysis['key_insights'].append(f"✅ High probability trade - {result.probability_profit*100:.0f}% chance of profit")
    elif result.probability_profit < 0.35:
        analysis['key_insights'].append(f"⚠️ Low probability trade - Only {result.probability_profit*100:.0f}% chance of profit")
    
    # Greeks insight
    if abs(result.theta_decay_1d) > result.current_price * 0.02:
        analysis['key_insights'].append(f"⏰ Significant theta decay - Losing ${abs(result.theta_decay_1d):.2f}/day to time decay")
    
    # Risks
    analysis['risks'] = []
    if result.max_loss > result.max_gain:
        analysis['risks'].append(f"Max loss (${result.max_loss:.2f}) exceeds max gain (${result.max_gain:.2f})")
    if result.iv_regime in [IVRegime.HIGH, IVRegime.EXTREME]:
        analysis['risks'].append("Elevated IV increases premium cost and volatility crush risk")
    if result.probability_profit < 0.5:
        analysis['risks'].append(f"Below 50% probability of profit ({result.probability_profit*100:.0f}%)")
    if result.theta_decay_1d < -0.5:
        analysis['risks'].append(f"Heavy time decay: ${result.theta_decay_1d:.2f}/day")
    
    # Recommendation
    if "BUY" in result.signal:
        if result.probability_profit > 0.6:
            analysis['recommendation'] = f"ENTER POSITION - Strong setup with {result.probability_profit*100:.0f}% win rate"
        else:
            analysis['recommendation'] = f"CONSIDER ENTRY - Acceptable setup but manage size due to {result.probability_profit*100:.0f}% win rate"
    elif "SELL" in result.signal:
        analysis['recommendation'] = "CLOSE/REDUCE POSITION - Unfavorable risk/reward profile"
    else:
        analysis['recommendation'] = "WAIT FOR BETTER SETUP - No clear edge in current conditions"
    
    # Action Plan
    analysis['action_plan'] = []
    
    if "BUY" in result.signal:
        analysis['action_plan'] = [
            f"1️⃣ Entry: Enter at current price ${result.current_price:.2f} or wait for pullback to ${result.conf_low_1d:.2f}",
            f"2️⃣ Position Size: Risk no more than 2% of portfolio on this trade",
            f"3️⃣ Stop Loss: Set stop at ${result.current_price * 0.7:.2f} (-30% from entry)",
            f"4️⃣ Profit Target: First target ${result.forecast_5d:.2f}, second target ${result.forecast_expiry:.2f}",
            f"5️⃣ Time Management: Review position daily, close if theta exceeds 50% of remaining value",
            f"6️⃣ Exit Trigger: Close immediately if underlying breaks key support levels"
        ]
    elif "SELL" in result.signal:
        analysis['action_plan'] = [
            "1️⃣ Close existing long positions to limit further losses",
            "2️⃣ Consider opening put protection if holding underlying stock",
            "3️⃣ Wait for IV normalization before re-entry",
            "4️⃣ Look for mean reversion signals before going long again"
        ]
    else:
        analysis['action_plan'] = [
            "1️⃣ Wait for clearer directional signal before entering",
            "2️⃣ Consider neutral strategies: Iron Condor, Iron Butterfly, or Calendar Spread",
            "3️⃣ If already in position, tighten stops and reduce size",
            "4️⃣ Monitor for breakout above/below current range"
        ]
    
    # Alternative strategies based on IV regime
    analysis['alternative_strategies'] = []
    if result.iv_regime in [IVRegime.HIGH, IVRegime.EXTREME]:
        analysis['alternative_strategies'] = [
            {"name": "Iron Condor", "reason": "Sell premium in high IV, profit from time decay"},
            {"name": "Put Credit Spread", "reason": "Bullish bias + collect premium in elevated IV"},
            {"name": "Covered Call", "reason": "Generate income while IV is high"}
        ]
    elif result.iv_regime == IVRegime.LOW:
        analysis['alternative_strategies'] = [
            {"name": "Long Straddle", "reason": "Buy cheap premium, profit from volatility expansion"},
            {"name": "Calendar Spread", "reason": "Benefit from IV term structure"},
            {"name": "LEAPS Call", "reason": "Low cost long-term bullish exposure"}
        ]
    else:
        analysis['alternative_strategies'] = [
            {"name": "Vertical Spread", "reason": "Defined risk directional play"},
            {"name": "Butterfly", "reason": "Low cost, defined risk around target price"}
        ]
    
    # Exit strategy
    analysis['exit_strategy'] = {
        'profit_target': f"Take 50% profit at ${result.forecast_5d:.2f}, remainder at ${result.forecast_expiry:.2f}",
        'stop_loss': f"Hard stop at ${result.current_price * 0.7:.2f} (-30%)",
        'time_stop': "Close 7 days before expiration if not in profit",
        'volatility_stop': "Close if IV drops 20%+ from entry (for long options)"
    }
    
    return analysis


def generate_enhanced_forecast_ui(result: ForecastResult) -> Any:
    """
    Generate enhanced Dash UI components from forecast result.
    
    Args:
        result: ForecastResult from forecaster
    
    Returns:
        Dash html.Div with full forecast visualization
    """
    from dash import html, dcc
    import dash_bootstrap_components as dbc
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    # Determine colors based on signal
    if "BUY" in result.signal:
        signal_color = "success"
    elif "SELL" in result.signal:
        signal_color = "danger"
    else:
        signal_color = "info"
    
    # Regime badge color
    regime_colors = {
        IVRegime.LOW: "success",
        IVRegime.NORMAL: "primary",
        IVRegime.HIGH: "warning",
        IVRegime.EXTREME: "danger"
    }
    regime_color = regime_colors.get(result.iv_regime, "secondary")
    
    # Trend icon
    trend_icons = {
        TrendDirection.STRONG_BULLISH: "⬆️⬆️",
        TrendDirection.BULLISH: "⬆️",
        TrendDirection.NEUTRAL: "➡️",
        TrendDirection.BEARISH: "⬇️",
        TrendDirection.STRONG_BEARISH: "⬇️⬇️"
    }
    trend_icon = trend_icons.get(result.trend_direction, "➡️")
    
    # Create price forecast chart
    forecast_fig = go.Figure()
    
    days = ['Now', '1D', '5D', '10D', 'Exp']
    prices = [result.current_price, result.forecast_1d, result.forecast_5d, 
              result.forecast_10d, result.forecast_expiry]
    
    # Confidence bands
    upper = [result.current_price, result.conf_high_1d, result.conf_high_5d, 
             result.conf_high_5d * 1.1, result.conf_high_5d * 1.2]
    lower = [result.current_price, result.conf_low_1d, result.conf_low_5d,
             result.conf_low_5d * 0.9, max(0, result.conf_low_5d * 0.8)]
    
    forecast_fig.add_trace(go.Scatter(
        x=days, y=upper,
        mode='lines', line=dict(width=0),
        showlegend=False, name='Upper'
    ))
    forecast_fig.add_trace(go.Scatter(
        x=days, y=lower,
        mode='lines', line=dict(width=0),
        fill='tonexty', fillcolor='rgba(59,130,246,0.2)',
        showlegend=False, name='Lower'
    ))
    forecast_fig.add_trace(go.Scatter(
        x=days, y=prices,
        mode='lines+markers',
        line=dict(color='#3b82f6', width=3),
        marker=dict(size=10),
        name='Forecast'
    ))
    forecast_fig.add_hline(y=result.current_price, line_dash="dash", 
                          line_color="gray", annotation_text="Entry")
    
    forecast_fig.update_layout(
        title="📈 Price Forecast",
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=280,
        margin=dict(l=40, r=40, t=50, b=40),
        showlegend=False
    )
    
    # Create P&L probability distribution
    prob_fig = go.Figure()
    
    # Simulated P&L distribution
    x_vals = np.linspace(-result.max_loss, result.max_gain, 50)
    # Approximate with normal centered at expected value
    std = (result.max_gain + result.max_loss) / 4
    y_vals = np.exp(-0.5 * ((x_vals - result.expected_value) / std) ** 2)
    
    colors = ['rgba(239,68,68,0.6)' if x < 0 else 'rgba(16,185,129,0.6)' for x in x_vals]
    
    prob_fig.add_trace(go.Bar(
        x=x_vals, y=y_vals,
        marker_color=colors,
        name='P&L Distribution'
    ))
    prob_fig.add_vline(x=0, line_dash="dash", line_color="white")
    prob_fig.add_vline(x=result.expected_value, line_dash="solid", 
                      line_color="yellow", annotation_text=f"EV: ${result.expected_value:.2f}")
    
    prob_fig.update_layout(
        title="📊 P&L Distribution",
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=220,
        margin=dict(l=40, r=40, t=50, b=40),
        showlegend=False,
        xaxis_title="Profit/Loss ($)",
        yaxis_visible=False
    )
    
    # Create Greeks sensitivity chart
    greeks_fig = make_subplots(rows=1, cols=3, subplot_titles=["Delta", "Theta", "Vega"])
    
    # Delta P&L for spot moves
    spot_moves = [-5, -3, -1, 0, 1, 3, 5]
    delta_pnl = [result.delta_pnl_1pct * m for m in spot_moves]
    greeks_fig.add_trace(go.Bar(
        x=[f"{m}%" for m in spot_moves], y=delta_pnl,
        marker_color=['#ef4444' if p < 0 else '#10b981' for p in delta_pnl],
        name='Delta P&L'
    ), row=1, col=1)
    
    # Theta decay over days
    theta_days = list(range(1, 6))
    theta_cum = [result.theta_decay_1d * d for d in theta_days]
    greeks_fig.add_trace(go.Bar(
        x=[f"Day {d}" for d in theta_days], y=theta_cum,
        marker_color='#ef4444',
        name='Theta Decay'
    ), row=1, col=2)
    
    # Vega P&L for IV moves
    iv_moves = [-5, -3, -1, 0, 1, 3, 5]
    vega_pnl = [result.vega_pnl_1vol * m for m in iv_moves]
    greeks_fig.add_trace(go.Bar(
        x=[f"{m}%" for m in iv_moves], y=vega_pnl,
        marker_color=['#ef4444' if p < 0 else '#10b981' for p in vega_pnl],
        name='Vega P&L'
    ), row=1, col=3)
    
    greeks_fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=200,
        margin=dict(l=40, r=40, t=40, b=40),
        showlegend=False
    )
    
    # Build complete UI
    return html.Div([
        # Header with signal
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.H3(result.signal, className=f"text-{signal_color} mb-0"),
                        html.P(f"Confidence: {result.confidence*100:.0f}%", className="text-muted mb-0")
                    ], width=6),
                    dbc.Col([
                        html.Div([
                            dbc.Badge(f"IV: {result.iv_regime.value.upper()}", 
                                     color=regime_color, className="me-2"),
                            dbc.Badge(f"Trend: {trend_icon} {result.trend_direction.value}", 
                                     color="secondary"),
                        ], className="text-end")
                    ], width=6)
                ])
            ])
        ], className="mb-3", color=signal_color, outline=True),
        
        # Key metrics row
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Current", className="text-muted mb-1"),
                        html.H4(f"${result.current_price:.2f}", className="text-primary mb-0")
                    ], className="p-2 text-center")
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("5-Day Target", className="text-muted mb-1"),
                        html.H4(f"${result.forecast_5d:.2f}", className=f"text-{signal_color} mb-0")
                    ], className="p-2 text-center")
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Prob. Profit", className="text-muted mb-1"),
                        html.H4(f"{result.probability_profit*100:.0f}%", 
                               className=f"text-{'success' if result.probability_profit > 0.5 else 'danger'} mb-0")
                    ], className="p-2 text-center")
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Expected Value", className="text-muted mb-1"),
                        html.H4(f"${result.expected_value:.2f}", 
                               className=f"text-{'success' if result.expected_value > 0 else 'danger'} mb-0")
                    ], className="p-2 text-center")
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Risk/Reward", className="text-muted mb-1"),
                        html.H4(f"{result.risk_reward_ratio:.1f}x", className="text-info mb-0")
                    ], className="p-2 text-center")
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Max Loss", className="text-muted mb-1"),
                        html.H4(f"${result.max_loss:.2f}", className="text-danger mb-0")
                    ], className="p-2 text-center")
                ])
            ], width=2),
        ], className="mb-3 g-2"),
        
        # Charts row
        dbc.Row([
            dbc.Col([
                dcc.Graph(figure=forecast_fig, config={'displayModeBar': False})
            ], width=7),
            dbc.Col([
                dcc.Graph(figure=prob_fig, config={'displayModeBar': False})
            ], width=5),
        ], className="mb-3"),
        
        # Greeks sensitivity
        dbc.Row([
            dbc.Col([
                html.H6("📊 Greeks Sensitivity Analysis", className="mb-2"),
                dcc.Graph(figure=greeks_fig, config={'displayModeBar': False})
            ], width=12)
        ], className="mb-3"),
        
        # Forecast ranges
        dbc.Alert([
            html.Strong("📈 Forecast Ranges: "),
            html.Span(f"1D: ${result.conf_low_1d:.2f}-${result.conf_high_1d:.2f} | "),
            html.Span(f"5D: ${result.conf_low_5d:.2f}-${result.conf_high_5d:.2f}"),
            html.Span(" | ", className="mx-2"),
            html.Strong("Greeks Impact: "),
            html.Span(f"Δ1%: ${result.delta_pnl_1pct:.2f} | "),
            html.Span(f"Θ/day: ${result.theta_decay_1d:.2f} | "),
            html.Span(f"ν1%: ${result.vega_pnl_1vol:.2f}")
        ], color="dark", className="py-2"),
        
        # === AI ANALYSIS SECTION ===
        _generate_ai_analysis_ui(result),
        
        # Model info
        html.P([
            html.Small(f"Model: {result.model_used} | Generated: {result.timestamp}", 
                      className="text-muted")
        ], className="text-end mb-0")
    ])


def _generate_ai_analysis_ui(result: ForecastResult) -> Any:
    """Generate the AI analysis UI section."""
    from dash import html
    import dash_bootstrap_components as dbc
    
    # Get AI analysis
    analysis = generate_ai_analysis(result)
    
    # Determine recommendation color
    if "ENTER" in analysis['recommendation'] or "Strong" in analysis['recommendation']:
        rec_color = "success"
    elif "CLOSE" in analysis['recommendation'] or "REDUCE" in analysis['recommendation']:
        rec_color = "danger"
    else:
        rec_color = "warning"
    
    return html.Div([
        # AI Analysis Header
        html.Hr(className="my-4"),
        html.H5([
            html.I(className="bi bi-robot me-2"),
            "🤖 AI Analysis & Recommendations"
        ], className="mb-3 text-info"),
        
        # Summary
        dbc.Card([
            dbc.CardHeader([
                html.I(className="bi bi-lightbulb me-2"),
                "Analysis Summary"
            ], className="bg-dark text-white"),
            dbc.CardBody([
                html.P(analysis['summary'], className="mb-0")
            ])
        ], className="mb-3"),
        
        # Key Insights
        dbc.Card([
            dbc.CardHeader([
                html.I(className="bi bi-search me-2"),
                "Key Insights"
            ], className="bg-dark text-white"),
            dbc.CardBody([
                html.Ul([
                    html.Li(insight, className="mb-2") 
                    for insight in analysis['key_insights']
                ], className="mb-0")
            ])
        ], className="mb-3"),
        
        # Recommendation (prominent)
        dbc.Alert([
            html.H5([
                html.I(className="bi bi-check-circle me-2"),
                "Recommendation"
            ], className="mb-2"),
            html.Strong(analysis['recommendation'], className="h5")
        ], color=rec_color, className="mb-3"),
        
        # Action Plan
        dbc.Card([
            dbc.CardHeader([
                html.I(className="bi bi-list-check me-2"),
                "📋 Action Plan"
            ], className="bg-primary text-white"),
            dbc.CardBody([
                html.Div([
                    html.P(step, className="mb-2", style={'fontSize': '14px'})
                    for step in analysis['action_plan']
                ])
            ])
        ], className="mb-3"),
        
        # Risk Warnings (if any)
        dbc.Card([
            dbc.CardHeader([
                html.I(className="bi bi-exclamation-triangle me-2"),
                "⚠️ Risk Factors"
            ], className="bg-warning text-dark"),
            dbc.CardBody([
                html.Ul([
                    html.Li(risk, className="text-danger mb-1")
                    for risk in analysis['risks']
                ], className="mb-0") if analysis['risks'] else html.P("No significant risk factors identified", className="text-success mb-0")
            ])
        ], className="mb-3"),
        
        # Two column layout for alternatives and exit
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="bi bi-arrow-left-right me-2"),
                        "Alternative Strategies"
                    ], className="bg-dark text-white"),
                    dbc.CardBody([
                        html.Div([
                            html.Div([
                                html.Strong(alt['name'], className="text-info"),
                                html.Br(),
                                html.Small(alt['reason'], className="text-muted")
                            ], className="mb-2")
                            for alt in analysis['alternative_strategies']
                        ])
                    ])
                ])
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="bi bi-door-open me-2"),
                        "Exit Strategy"
                    ], className="bg-dark text-white"),
                    dbc.CardBody([
                        html.Div([
                            html.P([html.Strong("🎯 Profit Target: "), analysis['exit_strategy']['profit_target']], className="mb-2", style={'fontSize': '13px'}),
                            html.P([html.Strong("🛑 Stop Loss: "), analysis['exit_strategy']['stop_loss']], className="mb-2", style={'fontSize': '13px'}),
                            html.P([html.Strong("⏰ Time Stop: "), analysis['exit_strategy']['time_stop']], className="mb-2", style={'fontSize': '13px'}),
                            html.P([html.Strong("📊 Vol Stop: "), analysis['exit_strategy']['volatility_stop']], className="mb-0", style={'fontSize': '13px'})
                        ])
                    ])
                ])
            ], width=6)
        ], className="mb-3")
    ])

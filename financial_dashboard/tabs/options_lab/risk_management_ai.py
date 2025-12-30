"""
AI Risk Management System
=========================
Comprehensive AI-powered risk management including:
- Auto stop-loss calculation
- Portfolio VaR prediction
- Drawdown risk scoring
- Correlation risk alerts
- Black swan detection
- Tail risk assessment

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

logger = logging.getLogger(__name__)


# ============================================================
# DATA CLASSES
# ============================================================

class RiskLevel(Enum):
    """Risk severity levels."""
    MINIMAL = 1
    LOW = 2
    MODERATE = 3
    HIGH = 4
    EXTREME = 5


@dataclass
class StopLossRecommendation:
    """AI-generated stop loss recommendation."""
    ticker: str
    current_price: float
    entry_price: float
    position_type: str  # 'long' or 'short'
    
    # Stop levels
    tight_stop: float
    standard_stop: float
    wide_stop: float
    
    # Corresponding risk amounts
    tight_risk_pct: float
    standard_risk_pct: float
    wide_risk_pct: float
    
    # AI reasoning
    recommended_stop: float
    rationale: str
    confidence: float
    
    # Trailing stop suggestion
    use_trailing: bool
    trailing_distance: float


@dataclass
class VaRPrediction:
    """Value at Risk prediction."""
    portfolio_value: float
    time_horizon_days: int
    
    # VaR at different confidence levels
    var_95: float  # 95% confidence
    var_99: float  # 99% confidence
    
    # Conditional VaR (Expected Shortfall)
    cvar_95: float
    cvar_99: float
    
    # Component VaR by position
    component_var: Dict[str, float]
    
    # Risk attribution
    risk_attribution: Dict[str, float]
    
    # Stress scenarios
    stress_scenarios: Dict[str, float]
    
    model_confidence: float
    generated_at: datetime


@dataclass
class DrawdownRisk:
    """Drawdown risk assessment."""
    ticker: str
    current_drawdown: float  # Current % from peak
    max_historical_drawdown: float
    avg_drawdown: float
    
    # Predictions
    predicted_max_drawdown: float
    recovery_time_estimate: int  # days
    
    # Probabilities
    prob_5pct_drawdown: float
    prob_10pct_drawdown: float
    prob_20pct_drawdown: float
    
    risk_level: RiskLevel
    recommendation: str


@dataclass
class CorrelationAlert:
    """Correlation risk alert."""
    alert_type: str  # 'high_correlation', 'concentration', 'sector_risk'
    positions_affected: List[str]
    correlation_value: float
    
    risk_description: str
    suggested_action: str
    urgency: str  # 'low', 'medium', 'high'


@dataclass
class TailRiskAssessment:
    """Black swan / tail risk assessment."""
    ticker: str
    
    # Tail statistics
    left_tail_risk: float  # Probability of extreme down move
    right_tail_risk: float  # Probability of extreme up move
    tail_index: float  # Fat-tail indicator
    
    # Historical extreme events
    worst_1d_return: float
    worst_5d_return: float
    worst_20d_return: float
    
    # Current risk signals
    risk_signals: List[str]
    overall_tail_risk: RiskLevel
    
    # Hedging suggestion
    hedge_recommendation: str
    hedge_cost_estimate: float


# ============================================================
# STOP LOSS CALCULATOR
# ============================================================

class AutoStopLossCalculator:
    """
    AI-powered stop loss calculator that automatically
    determines optimal stop levels based on volatility,
    support/resistance, and risk tolerance.
    """
    
    def __init__(self):
        self.atr_multipliers = {
            'tight': 1.5,
            'standard': 2.5,
            'wide': 4.0
        }
    
    def calculate_stop(self, ticker: str, entry_price: float,
                       position_type: str = 'long',
                       risk_tolerance: str = 'moderate') -> StopLossRecommendation:
        """Calculate optimal stop loss levels."""
        try:
            from .alpaca_data_loader import get_alpaca_client
            
            client = get_alpaca_client()
            bars = client.get_historical_bars(ticker, '1Day', limit=60)
            
            if bars.empty:
                return self._fallback_stop(ticker, entry_price, position_type)
            
            current_price = bars['c'].iloc[-1]
            
            # Calculate ATR
            tr = np.maximum(
                bars['h'] - bars['l'],
                np.maximum(
                    abs(bars['h'] - bars['c'].shift(1)),
                    abs(bars['l'] - bars['c'].shift(1))
                )
            )
            atr = tr.rolling(14).mean().iloc[-1]
            
            # Find support/resistance levels
            support = self._find_support(bars)
            resistance = self._find_resistance(bars)
            
            # Calculate stop levels
            if position_type == 'long':
                tight_stop = current_price - atr * self.atr_multipliers['tight']
                standard_stop = current_price - atr * self.atr_multipliers['standard']
                wide_stop = current_price - atr * self.atr_multipliers['wide']
                
                # Consider support level
                if support and support < current_price:
                    # Place stop below support
                    support_stop = support * 0.98
                    if standard_stop > support_stop:
                        standard_stop = support_stop
            else:
                tight_stop = current_price + atr * self.atr_multipliers['tight']
                standard_stop = current_price + atr * self.atr_multipliers['standard']
                wide_stop = current_price + atr * self.atr_multipliers['wide']
                
                if resistance and resistance > current_price:
                    resistance_stop = resistance * 1.02
                    if standard_stop < resistance_stop:
                        standard_stop = resistance_stop
            
            # Calculate risk percentages
            tight_risk = abs(current_price - tight_stop) / entry_price * 100
            standard_risk = abs(current_price - standard_stop) / entry_price * 100
            wide_risk = abs(current_price - wide_stop) / entry_price * 100
            
            # Determine recommended stop based on risk tolerance
            risk_map = {
                'conservative': tight_stop,
                'moderate': standard_stop,
                'aggressive': wide_stop
            }
            recommended = risk_map.get(risk_tolerance, standard_stop)
            
            # Trailing stop recommendation
            vol = bars['c'].pct_change().std()
            use_trailing = vol > 0.02  # High volatility = trailing stop
            trailing_distance = atr * 2
            
            # Generate rationale
            rationale = self._generate_rationale(
                ticker, current_price, recommended, atr, support, 
                position_type, risk_tolerance
            )
            
            return StopLossRecommendation(
                ticker=ticker,
                current_price=round(current_price, 2),
                entry_price=round(entry_price, 2),
                position_type=position_type,
                tight_stop=round(tight_stop, 2),
                standard_stop=round(standard_stop, 2),
                wide_stop=round(wide_stop, 2),
                tight_risk_pct=round(tight_risk, 2),
                standard_risk_pct=round(standard_risk, 2),
                wide_risk_pct=round(wide_risk, 2),
                recommended_stop=round(recommended, 2),
                rationale=rationale,
                confidence=0.75,
                use_trailing=use_trailing,
                trailing_distance=round(trailing_distance, 2)
            )
            
        except Exception as e:
            logger.error(f"Stop loss calculation failed: {e}")
            return self._fallback_stop(ticker, entry_price, position_type)
    
    def _find_support(self, bars: pd.DataFrame) -> Optional[float]:
        """Find nearest support level."""
        lows = bars['l'].values
        pivots = []
        
        for i in range(2, len(lows) - 2):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                pivots.append(lows[i])
        
        current = bars['c'].iloc[-1]
        below = [p for p in pivots if p < current]
        
        if below:
            return max(below)
        return None
    
    def _find_resistance(self, bars: pd.DataFrame) -> Optional[float]:
        """Find nearest resistance level."""
        highs = bars['h'].values
        pivots = []
        
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                pivots.append(highs[i])
        
        current = bars['c'].iloc[-1]
        above = [p for p in pivots if p > current]
        
        if above:
            return min(above)
        return None
    
    def _generate_rationale(self, ticker: str, current: float, stop: float,
                           atr: float, support: Optional[float],
                           position_type: str, risk_tolerance: str) -> str:
        """Generate rationale for stop placement."""
        parts = [f"Stop calculated for {position_type} position in {ticker}:"]
        
        risk_pct = abs(current - stop) / current * 100
        parts.append(f"• Risk: {risk_pct:.1f}% from current price ${current:.2f}")
        parts.append(f"• ATR-based volatility: ${atr:.2f} (14-day)")
        
        if support and position_type == 'long':
            parts.append(f"• Key support level: ${support:.2f}")
        
        parts.append(f"• Risk tolerance: {risk_tolerance.title()}")
        
        return "\n".join(parts)
    
    def _fallback_stop(self, ticker: str, entry: float, 
                       position_type: str) -> StopLossRecommendation:
        """Fallback when data unavailable."""
        mult = -1 if position_type == 'long' else 1
        return StopLossRecommendation(
            ticker=ticker,
            current_price=entry,
            entry_price=entry,
            position_type=position_type,
            tight_stop=entry * (1 + mult * 0.02),
            standard_stop=entry * (1 + mult * 0.05),
            wide_stop=entry * (1 + mult * 0.10),
            tight_risk_pct=2.0,
            standard_risk_pct=5.0,
            wide_risk_pct=10.0,
            recommended_stop=entry * (1 + mult * 0.05),
            rationale="Fallback calculation - using default percentages",
            confidence=0.3,
            use_trailing=False,
            trailing_distance=entry * 0.03
        )


# ============================================================
# VALUE AT RISK CALCULATOR
# ============================================================

class VaRCalculator:
    """
    Portfolio Value at Risk calculator using multiple methods:
    - Historical VaR
    - Parametric VaR
    - Monte Carlo VaR
    """
    
    def __init__(self):
        self.confidence_levels = [0.95, 0.99]
        self.monte_carlo_sims = 10000
    
    def calculate_portfolio_var(self, positions: List[Dict],
                                portfolio_value: float,
                                horizon_days: int = 1) -> VaRPrediction:
        """
        Calculate VaR for a portfolio.
        
        Args:
            positions: List of {'ticker': str, 'value': float, 'type': str}
            portfolio_value: Total portfolio value
            horizon_days: Time horizon in days
        """
        try:
            returns_data = {}
            weights = {}
            
            # Get historical returns for each position
            from .alpaca_data_loader import get_alpaca_client
            client = get_alpaca_client()
            
            for pos in positions:
                ticker = pos['ticker']
                weight = pos['value'] / portfolio_value
                weights[ticker] = weight
                
                bars = client.get_historical_bars(ticker, '1Day', limit=252)
                if not bars.empty:
                    returns_data[ticker] = np.log(bars['c'] / bars['c'].shift(1)).dropna().values
            
            if not returns_data:
                return self._fallback_var(portfolio_value, horizon_days)
            
            # Align returns
            min_len = min(len(r) for r in returns_data.values())
            aligned_returns = np.array([returns_data[t][-min_len:] for t in returns_data])
            weight_array = np.array([weights[t] for t in returns_data])
            
            # Portfolio returns
            portfolio_returns = np.dot(weight_array, aligned_returns)
            
            # Historical VaR
            var_95_hist = -np.percentile(portfolio_returns, 5) * portfolio_value * np.sqrt(horizon_days)
            var_99_hist = -np.percentile(portfolio_returns, 1) * portfolio_value * np.sqrt(horizon_days)
            
            # Parametric VaR (assuming normal)
            mean = portfolio_returns.mean()
            std = portfolio_returns.std()
            var_95_param = (-mean + 1.645 * std) * portfolio_value * np.sqrt(horizon_days)
            var_99_param = (-mean + 2.326 * std) * portfolio_value * np.sqrt(horizon_days)
            
            # Use average of methods
            var_95 = (var_95_hist + var_95_param) / 2
            var_99 = (var_99_hist + var_99_param) / 2
            
            # CVaR (Expected Shortfall)
            tail_95 = portfolio_returns[portfolio_returns < np.percentile(portfolio_returns, 5)]
            tail_99 = portfolio_returns[portfolio_returns < np.percentile(portfolio_returns, 1)]
            
            cvar_95 = -tail_95.mean() * portfolio_value * np.sqrt(horizon_days) if len(tail_95) > 0 else var_95 * 1.2
            cvar_99 = -tail_99.mean() * portfolio_value * np.sqrt(horizon_days) if len(tail_99) > 0 else var_99 * 1.2
            
            # Component VaR
            component_var = {}
            for ticker in returns_data:
                pos_returns = returns_data[ticker][-min_len:]
                pos_var = -np.percentile(pos_returns, 5) * weights[ticker] * portfolio_value
                component_var[ticker] = round(pos_var, 2)
            
            # Risk attribution (as percentage)
            total_component = sum(component_var.values())
            risk_attribution = {
                k: round(v / total_component * 100, 1) if total_component > 0 else 0 
                for k, v in component_var.items()
            }
            
            # Stress scenarios
            stress_scenarios = {
                '2008 Financial Crisis (-40%)': portfolio_value * 0.40,
                '2020 COVID Crash (-30%)': portfolio_value * 0.30,
                'Flash Crash (-10%)': portfolio_value * 0.10,
                '3-Sigma Event': var_99 * 1.5
            }
            
            return VaRPrediction(
                portfolio_value=portfolio_value,
                time_horizon_days=horizon_days,
                var_95=round(var_95, 2),
                var_99=round(var_99, 2),
                cvar_95=round(cvar_95, 2),
                cvar_99=round(cvar_99, 2),
                component_var=component_var,
                risk_attribution=risk_attribution,
                stress_scenarios={k: round(v, 2) for k, v in stress_scenarios.items()},
                model_confidence=0.75,
                generated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"VaR calculation failed: {e}")
            return self._fallback_var(portfolio_value, horizon_days)
    
    def _fallback_var(self, portfolio_value: float, horizon_days: int) -> VaRPrediction:
        """Fallback VaR calculation."""
        # Assume 1% daily volatility
        daily_var = portfolio_value * 0.01 * 1.645
        
        return VaRPrediction(
            portfolio_value=portfolio_value,
            time_horizon_days=horizon_days,
            var_95=round(daily_var * np.sqrt(horizon_days), 2),
            var_99=round(daily_var * 1.4 * np.sqrt(horizon_days), 2),
            cvar_95=round(daily_var * 1.2 * np.sqrt(horizon_days), 2),
            cvar_99=round(daily_var * 1.6 * np.sqrt(horizon_days), 2),
            component_var={},
            risk_attribution={},
            stress_scenarios={'Default Stress': portfolio_value * 0.20},
            model_confidence=0.3,
            generated_at=datetime.now()
        )


# ============================================================
# DRAWDOWN RISK ANALYZER
# ============================================================

class DrawdownRiskAnalyzer:
    """Analyzes and predicts drawdown risk."""
    
    def analyze_drawdown_risk(self, ticker: str) -> DrawdownRisk:
        """Analyze drawdown risk for a ticker."""
        try:
            from .alpaca_data_loader import get_alpaca_client
            
            client = get_alpaca_client()
            bars = client.get_historical_bars(ticker, '1Day', limit=252)
            
            if bars.empty:
                return self._fallback_drawdown(ticker)
            
            close = bars['c'].values
            
            # Calculate drawdowns
            peak = np.maximum.accumulate(close)
            drawdowns = (close - peak) / peak * 100
            
            current_dd = drawdowns[-1]
            max_dd = drawdowns.min()
            avg_dd = drawdowns[drawdowns < 0].mean() if any(drawdowns < 0) else 0
            
            # Volatility-based prediction
            returns = np.log(close[1:] / close[:-1])
            vol = returns.std() * np.sqrt(252)
            
            # Predict max drawdown based on volatility
            # Using rule of thumb: max DD ~ 2 * annual vol
            predicted_max_dd = -vol * 2 * 100
            
            # Recovery time (historical average)
            recovery_times = []
            in_dd = False
            dd_start = 0
            for i, dd in enumerate(drawdowns):
                if dd < -0.05 and not in_dd:  # 5% drawdown threshold
                    in_dd = True
                    dd_start = i
                elif dd >= 0 and in_dd:
                    in_dd = False
                    recovery_times.append(i - dd_start)
            
            avg_recovery = int(np.mean(recovery_times)) if recovery_times else 30
            
            # Probabilities based on historical data
            prob_5 = sum(1 for d in drawdowns if d < -5) / len(drawdowns)
            prob_10 = sum(1 for d in drawdowns if d < -10) / len(drawdowns)
            prob_20 = sum(1 for d in drawdowns if d < -20) / len(drawdowns)
            
            # Risk level
            if current_dd < -15:
                risk_level = RiskLevel.EXTREME
                recommendation = "Consider reducing position size or hedging"
            elif current_dd < -10:
                risk_level = RiskLevel.HIGH
                recommendation = "Monitor closely, prepare exit strategy"
            elif current_dd < -5:
                risk_level = RiskLevel.MODERATE
                recommendation = "Normal volatility, maintain position"
            else:
                risk_level = RiskLevel.LOW
                recommendation = "Position healthy, no action needed"
            
            return DrawdownRisk(
                ticker=ticker,
                current_drawdown=round(current_dd, 2),
                max_historical_drawdown=round(max_dd, 2),
                avg_drawdown=round(avg_dd, 2),
                predicted_max_drawdown=round(predicted_max_dd, 2),
                recovery_time_estimate=avg_recovery,
                prob_5pct_drawdown=round(prob_5, 3),
                prob_10pct_drawdown=round(prob_10, 3),
                prob_20pct_drawdown=round(prob_20, 3),
                risk_level=risk_level,
                recommendation=recommendation
            )
            
        except Exception as e:
            logger.error(f"Drawdown analysis failed: {e}")
            return self._fallback_drawdown(ticker)
    
    def _fallback_drawdown(self, ticker: str) -> DrawdownRisk:
        """Fallback drawdown analysis."""
        return DrawdownRisk(
            ticker=ticker,
            current_drawdown=0.0,
            max_historical_drawdown=-20.0,
            avg_drawdown=-5.0,
            predicted_max_drawdown=-25.0,
            recovery_time_estimate=30,
            prob_5pct_drawdown=0.15,
            prob_10pct_drawdown=0.05,
            prob_20pct_drawdown=0.02,
            risk_level=RiskLevel.MODERATE,
            recommendation="Using default estimates"
        )


# ============================================================
# CORRELATION RISK ANALYZER
# ============================================================

class CorrelationRiskAnalyzer:
    """Analyzes correlation risk in portfolios."""
    
    def __init__(self):
        self.correlation_threshold = 0.7  # High correlation warning
        self.concentration_threshold = 0.3  # Single position > 30%
    
    def analyze_correlation_risk(self, positions: List[Dict]) -> List[CorrelationAlert]:
        """
        Analyze correlation risk in portfolio.
        
        Args:
            positions: List of {'ticker': str, 'value': float}
        """
        alerts = []
        
        if len(positions) < 2:
            return alerts
        
        try:
            from .alpaca_data_loader import get_alpaca_client
            client = get_alpaca_client()
            
            # Get returns for all positions
            returns_data = {}
            for pos in positions:
                ticker = pos['ticker']
                bars = client.get_historical_bars(ticker, '1Day', limit=60)
                if not bars.empty:
                    returns_data[ticker] = np.log(bars['c'] / bars['c'].shift(1)).dropna().values
            
            # Build correlation matrix
            tickers = list(returns_data.keys())
            if len(tickers) < 2:
                return alerts
            
            # Align lengths
            min_len = min(len(r) for r in returns_data.values())
            returns_matrix = np.array([returns_data[t][-min_len:] for t in tickers])
            
            # Calculate correlations
            corr_matrix = np.corrcoef(returns_matrix)
            
            # Check for high correlations
            for i in range(len(tickers)):
                for j in range(i + 1, len(tickers)):
                    corr = corr_matrix[i, j]
                    if abs(corr) > self.correlation_threshold:
                        alerts.append(CorrelationAlert(
                            alert_type='high_correlation',
                            positions_affected=[tickers[i], tickers[j]],
                            correlation_value=round(corr, 3),
                            risk_description=f"High correlation ({corr:.0%}) between {tickers[i]} and {tickers[j]} increases portfolio risk",
                            suggested_action=f"Consider reducing one position or adding uncorrelated assets",
                            urgency='medium' if corr > 0.8 else 'low'
                        ))
            
            # Check concentration
            total_value = sum(p['value'] for p in positions)
            for pos in positions:
                weight = pos['value'] / total_value if total_value > 0 else 0
                if weight > self.concentration_threshold:
                    alerts.append(CorrelationAlert(
                        alert_type='concentration',
                        positions_affected=[pos['ticker']],
                        correlation_value=round(weight, 3),
                        risk_description=f"{pos['ticker']} represents {weight:.0%} of portfolio - concentration risk",
                        suggested_action="Diversify by reducing position or adding other assets",
                        urgency='high' if weight > 0.5 else 'medium'
                    ))
            
            # Sector concentration (simplified)
            tech_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'AMD', 'CRM', 'INTC']
            tech_weight = sum(p['value'] for p in positions if p['ticker'] in tech_stocks) / total_value if total_value > 0 else 0
            
            if tech_weight > 0.5:
                tech_tickers = [p['ticker'] for p in positions if p['ticker'] in tech_stocks]
                alerts.append(CorrelationAlert(
                    alert_type='sector_risk',
                    positions_affected=tech_tickers,
                    correlation_value=round(tech_weight, 3),
                    risk_description=f"Technology sector exposure is {tech_weight:.0%} - sector concentration risk",
                    suggested_action="Add positions in other sectors for diversification",
                    urgency='medium'
                ))
            
        except Exception as e:
            logger.error(f"Correlation analysis failed: {e}")
        
        return alerts


# ============================================================
# TAIL RISK ANALYZER (BLACK SWAN DETECTOR)
# ============================================================

class TailRiskAnalyzer:
    """
    Black swan / tail risk detection and assessment.
    Identifies potential extreme events and suggests hedges.
    """
    
    def analyze_tail_risk(self, ticker: str) -> TailRiskAssessment:
        """Analyze tail risk for a ticker."""
        try:
            from .alpaca_data_loader import get_alpaca_client
            
            client = get_alpaca_client()
            bars = client.get_historical_bars(ticker, '1Day', limit=252)
            
            if bars.empty:
                return self._fallback_tail(ticker)
            
            returns = np.log(bars['c'] / bars['c'].shift(1)).dropna().values
            
            # Tail statistics
            left_percentile_1 = np.percentile(returns, 1)
            right_percentile_99 = np.percentile(returns, 99)
            
            # Calculate tail probabilities (probability of > 2 sigma move)
            std = returns.std()
            left_tail_risk = sum(1 for r in returns if r < -2*std) / len(returns)
            right_tail_risk = sum(1 for r in returns if r > 2*std) / len(returns)
            
            # Tail index (kurtosis - higher = fatter tails)
            kurtosis = ((returns - returns.mean())**4).mean() / std**4
            tail_index = kurtosis - 3  # Excess kurtosis
            
            # Worst returns
            worst_1d = returns.min() * 100
            
            # Calculate 5-day and 20-day returns
            close = bars['c'].values
            returns_5d = (close[5:] - close[:-5]) / close[:-5]
            returns_20d = (close[20:] - close[:-20]) / close[:-20]
            
            worst_5d = returns_5d.min() * 100 if len(returns_5d) > 0 else worst_1d * 2
            worst_20d = returns_20d.min() * 100 if len(returns_20d) > 0 else worst_1d * 3
            
            # Risk signals
            signals = []
            if tail_index > 2:
                signals.append("Fat-tailed distribution detected")
            if left_tail_risk > 0.03:
                signals.append("Higher than normal large down move probability")
            if std * np.sqrt(252) > 0.4:
                signals.append("High annualized volatility")
            
            # VIX proxy check (for market-wide tail risk)
            vol_regime = std * np.sqrt(252)
            if vol_regime > 0.3:
                signals.append("Elevated volatility regime")
            
            # Overall risk level
            if tail_index > 3 or left_tail_risk > 0.05:
                risk_level = RiskLevel.EXTREME
            elif tail_index > 2 or left_tail_risk > 0.03:
                risk_level = RiskLevel.HIGH
            elif tail_index > 1 or left_tail_risk > 0.02:
                risk_level = RiskLevel.MODERATE
            else:
                risk_level = RiskLevel.LOW
            
            # Hedge recommendation
            if risk_level in [RiskLevel.HIGH, RiskLevel.EXTREME]:
                hedge_rec = f"Consider buying OTM puts (10-15% below current) for tail risk protection"
                hedge_cost = 0.02 * 100  # Rough estimate: 2% of position
            elif risk_level == RiskLevel.MODERATE:
                hedge_rec = "Monitor closely; consider collar strategy if position is large"
                hedge_cost = 0.01 * 100
            else:
                hedge_rec = "No immediate hedge needed; standard position sizing sufficient"
                hedge_cost = 0.0
            
            return TailRiskAssessment(
                ticker=ticker,
                left_tail_risk=round(left_tail_risk, 4),
                right_tail_risk=round(right_tail_risk, 4),
                tail_index=round(tail_index, 2),
                worst_1d_return=round(worst_1d, 2),
                worst_5d_return=round(worst_5d, 2),
                worst_20d_return=round(worst_20d, 2),
                risk_signals=signals,
                overall_tail_risk=risk_level,
                hedge_recommendation=hedge_rec,
                hedge_cost_estimate=round(hedge_cost, 2)
            )
            
        except Exception as e:
            logger.error(f"Tail risk analysis failed: {e}")
            return self._fallback_tail(ticker)
    
    def _fallback_tail(self, ticker: str) -> TailRiskAssessment:
        """Fallback tail risk assessment."""
        return TailRiskAssessment(
            ticker=ticker,
            left_tail_risk=0.025,
            right_tail_risk=0.025,
            tail_index=1.0,
            worst_1d_return=-5.0,
            worst_5d_return=-10.0,
            worst_20d_return=-15.0,
            risk_signals=["Using default estimates"],
            overall_tail_risk=RiskLevel.MODERATE,
            hedge_recommendation="Monitor position with standard risk management",
            hedge_cost_estimate=1.0
        )


# ============================================================
# UNIFIED RISK MANAGER
# ============================================================

class UnifiedRiskManager:
    """
    Unified interface for all risk management functions.
    Provides comprehensive portfolio risk analysis.
    """
    
    def __init__(self):
        self.stop_calculator = AutoStopLossCalculator()
        self.var_calculator = VaRCalculator()
        self.drawdown_analyzer = DrawdownRiskAnalyzer()
        self.correlation_analyzer = CorrelationRiskAnalyzer()
        self.tail_analyzer = TailRiskAnalyzer()
    
    def full_risk_analysis(self, positions: List[Dict], 
                          portfolio_value: float) -> Dict:
        """Run comprehensive risk analysis on portfolio."""
        results = {
            'timestamp': datetime.now().isoformat(),
            'portfolio_value': portfolio_value,
            'position_count': len(positions),
            'var': None,
            'drawdown_risks': {},
            'correlation_alerts': [],
            'tail_risks': {},
            'stop_recommendations': {},
            'overall_risk_level': RiskLevel.MODERATE,
            'summary': ''
        }
        
        # VaR
        results['var'] = self.var_calculator.calculate_portfolio_var(
            positions, portfolio_value, 1
        )
        
        # Per-position analysis
        for pos in positions:
            ticker = pos['ticker']
            
            # Drawdown
            results['drawdown_risks'][ticker] = self.drawdown_analyzer.analyze_drawdown_risk(ticker)
            
            # Tail risk
            results['tail_risks'][ticker] = self.tail_analyzer.analyze_tail_risk(ticker)
            
            # Stop loss
            entry = pos.get('entry_price', pos['value'] / pos.get('quantity', 1))
            results['stop_recommendations'][ticker] = self.stop_calculator.calculate_stop(
                ticker, entry, 'long'
            )
        
        # Correlation
        results['correlation_alerts'] = self.correlation_analyzer.analyze_correlation_risk(positions)
        
        # Overall risk level
        risk_scores = []
        for dd in results['drawdown_risks'].values():
            risk_scores.append(dd.risk_level.value)
        for tr in results['tail_risks'].values():
            risk_scores.append(tr.overall_tail_risk.value)
        
        avg_risk = np.mean(risk_scores) if risk_scores else 3
        if avg_risk >= 4:
            results['overall_risk_level'] = RiskLevel.EXTREME
        elif avg_risk >= 3.5:
            results['overall_risk_level'] = RiskLevel.HIGH
        elif avg_risk >= 2.5:
            results['overall_risk_level'] = RiskLevel.MODERATE
        else:
            results['overall_risk_level'] = RiskLevel.LOW
        
        # Generate summary
        results['summary'] = self._generate_summary(results)
        
        return results
    
    def quick_risk_check(self, ticker: str, position_value: float) -> Dict:
        """Quick risk check for a single position."""
        return {
            'ticker': ticker,
            'value': position_value,
            'drawdown': self.drawdown_analyzer.analyze_drawdown_risk(ticker),
            'tail_risk': self.tail_analyzer.analyze_tail_risk(ticker),
            'stop_loss': self.stop_calculator.calculate_stop(ticker, position_value, 'long')
        }
    
    def _generate_summary(self, results: Dict) -> str:
        """Generate human-readable risk summary."""
        parts = ["📊 Portfolio Risk Summary"]
        parts.append(f"Overall Risk Level: {results['overall_risk_level'].name}")
        parts.append("")
        
        if results['var']:
            var = results['var']
            parts.append(f"📈 Value at Risk (1-day):")
            parts.append(f"  • 95% VaR: ${var.var_95:,.0f}")
            parts.append(f"  • 99% VaR: ${var.var_99:,.0f}")
        
        if results['correlation_alerts']:
            parts.append("")
            parts.append(f"⚠️ {len(results['correlation_alerts'])} Correlation Alert(s)")
            for alert in results['correlation_alerts'][:3]:
                parts.append(f"  • {alert.risk_description}")
        
        # Count high-risk positions
        high_risk = sum(1 for tr in results['tail_risks'].values() 
                       if tr.overall_tail_risk.value >= 4)
        if high_risk > 0:
            parts.append("")
            parts.append(f"🔴 {high_risk} position(s) with elevated tail risk")
        
        return "\n".join(parts)


# ============================================================
# SINGLETONS
# ============================================================

_risk_manager = None

def get_risk_manager() -> UnifiedRiskManager:
    """Get singleton risk manager."""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = UnifiedRiskManager()
    return _risk_manager

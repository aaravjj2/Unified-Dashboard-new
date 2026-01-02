"""
Advanced Greeks Analytics Module
================================
Advanced visualization and analysis of options Greeks:
- Greeks surface visualization (3D)
- Greeks sensitivity analysis
- Gamma scalping calculator
- Vega exposure heatmap
- Theta decay projector

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
from scipy.stats import norm
from scipy.interpolate import griddata
import math

logger = logging.getLogger(__name__)


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class GreeksSurfacePoint:
    """Single point on Greeks surface."""
    strike: float
    dte: int
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    iv: float


@dataclass
class GreeksSurface:
    """Complete Greeks surface data."""
    ticker: str
    spot_price: float
    strikes: List[float]
    expirations: List[int]  # DTEs
    
    # 2D grids (strike x expiration)
    delta_surface: np.ndarray
    gamma_surface: np.ndarray
    theta_surface: np.ndarray
    vega_surface: np.ndarray
    iv_surface: np.ndarray
    
    generated_at: datetime


@dataclass
class SensitivityResult:
    """Result of sensitivity analysis."""
    ticker: str
    base_price: float
    scenarios: List[Dict]  # price_change, new_pnl, new_delta, etc.
    breakeven_up: float
    breakeven_down: float
    max_profit_price: float
    max_loss_price: float


@dataclass
class GammaScalpSignal:
    """Gamma scalping signal."""
    ticker: str
    current_price: float
    position_gamma: float
    hedge_threshold: float  # Delta threshold to trigger hedge
    shares_to_trade: int
    direction: str  # 'buy' or 'sell'
    expected_profit: float
    breakeven_move: float


@dataclass
class VegaExposure:
    """Vega exposure by expiration."""
    expiration: str
    dte: int
    total_vega: float
    vega_dollars: float  # Vega * 100 * position size
    positions: List[str]
    risk_level: str  # 'low', 'moderate', 'high'


@dataclass
class ThetaProjection:
    """Theta decay projection."""
    ticker: str
    dates: List[str]
    cumulative_theta: List[float]
    daily_theta: List[float]
    weekend_decay: float
    total_decay_30d: float


# ============================================================
# GREEKS SURFACE BUILDER
# ============================================================

class GreeksSurfaceBuilder:
    """
    Build 3D Greeks surfaces across strikes and expirations.
    Useful for visualizing option behavior patterns.
    """
    
    def __init__(self):
        self.risk_free_rate = 0.05
    
    def build_surface(self, ticker: str, spot_price: float,
                      chain_data: List[Dict] = None) -> GreeksSurface:
        """Build complete Greeks surface."""
        try:
            # Get options chain
            if chain_data is None:
                chain_data = self._fetch_chain(ticker)
            
            if not chain_data:
                return self._generate_synthetic_surface(ticker, spot_price)
            
            # Extract unique strikes and expirations
            strikes = sorted(set(c['strike'] for c in chain_data))
            expirations = sorted(set(c['dte'] for c in chain_data))
            
            # Initialize surfaces
            n_strikes = len(strikes)
            n_exp = len(expirations)
            
            delta_surf = np.zeros((n_strikes, n_exp))
            gamma_surf = np.zeros((n_strikes, n_exp))
            theta_surf = np.zeros((n_strikes, n_exp))
            vega_surf = np.zeros((n_strikes, n_exp))
            iv_surf = np.zeros((n_strikes, n_exp))
            
            # Build lookup
            chain_lookup = {}
            for c in chain_data:
                key = (c['strike'], c['dte'])
                chain_lookup[key] = c
            
            # Fill surfaces
            for i, strike in enumerate(strikes):
                for j, dte in enumerate(expirations):
                    key = (strike, dte)
                    if key in chain_lookup:
                        c = chain_lookup[key]
                        delta_surf[i, j] = c.get('delta', 0)
                        gamma_surf[i, j] = c.get('gamma', 0)
                        theta_surf[i, j] = c.get('theta', 0)
                        vega_surf[i, j] = c.get('vega', 0)
                        iv_surf[i, j] = c.get('iv', 0.25)
                    else:
                        # Interpolate or calculate
                        greeks = self._calculate_greeks(
                            spot_price, strike, dte, 0.25, 'call'
                        )
                        delta_surf[i, j] = greeks['delta']
                        gamma_surf[i, j] = greeks['gamma']
                        theta_surf[i, j] = greeks['theta']
                        vega_surf[i, j] = greeks['vega']
                        iv_surf[i, j] = 0.25
            
            return GreeksSurface(
                ticker=ticker,
                spot_price=spot_price,
                strikes=strikes,
                expirations=expirations,
                delta_surface=delta_surf,
                gamma_surface=gamma_surf,
                theta_surface=theta_surf,
                vega_surface=vega_surf,
                iv_surface=iv_surf,
                generated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Surface build failed: {e}")
            return self._generate_synthetic_surface(ticker, spot_price)
    
    def _fetch_chain(self, ticker: str) -> List[Dict]:
        """Fetch options chain data."""
        try:
            from .alpaca_data_loader import get_alpaca_client
            client = get_alpaca_client()
            
            chain = []
            expirations = client.get_option_expirations(ticker)
            
            for exp in expirations[:5]:  # Limit to 5 expirations
                contracts = client.get_options_chain(ticker, exp)
                for contract in contracts:
                    chain.append({
                        'strike': contract.get('strike_price', 0),
                        'dte': (datetime.strptime(exp, '%Y-%m-%d') - datetime.now()).days,
                        'delta': contract.get('delta', 0.5),
                        'gamma': contract.get('gamma', 0.01),
                        'theta': contract.get('theta', -0.05),
                        'vega': contract.get('vega', 0.1),
                        'iv': contract.get('implied_volatility', 0.25)
                    })
            
            return chain
        except:
            return []
    
    def _generate_synthetic_surface(self, ticker: str, spot: float) -> GreeksSurface:
        """Generate synthetic surface for demo."""
        strikes = [spot * (0.8 + 0.05 * i) for i in range(9)]
        expirations = [7, 14, 30, 45, 60, 90]
        
        n_s, n_e = len(strikes), len(expirations)
        delta_surf = np.zeros((n_s, n_e))
        gamma_surf = np.zeros((n_s, n_e))
        theta_surf = np.zeros((n_s, n_e))
        vega_surf = np.zeros((n_s, n_e))
        iv_surf = np.zeros((n_s, n_e))
        
        for i, strike in enumerate(strikes):
            for j, dte in enumerate(expirations):
                iv = 0.20 + 0.10 * abs(strike/spot - 1) + 0.05 * np.sqrt(dte/365)
                greeks = self._calculate_greeks(spot, strike, dte, iv, 'call')
                delta_surf[i, j] = greeks['delta']
                gamma_surf[i, j] = greeks['gamma']
                theta_surf[i, j] = greeks['theta']
                vega_surf[i, j] = greeks['vega']
                iv_surf[i, j] = iv
        
        return GreeksSurface(
            ticker=ticker,
            spot_price=spot,
            strikes=strikes,
            expirations=expirations,
            delta_surface=delta_surf,
            gamma_surface=gamma_surf,
            theta_surface=theta_surf,
            vega_surface=vega_surf,
            iv_surface=iv_surf,
            generated_at=datetime.now()
        )
    
    def _calculate_greeks(self, S: float, K: float, dte: int, 
                          iv: float, option_type: str) -> Dict:
        """Calculate Black-Scholes Greeks."""
        T = max(dte / 365, 0.001)
        r = self.risk_free_rate
        sigma = iv
        
        d1 = (np.log(S/K) + (r + sigma**2/2)*T) / (sigma*np.sqrt(T))
        d2 = d1 - sigma*np.sqrt(T)
        
        if option_type == 'call':
            delta = norm.cdf(d1)
        else:
            delta = norm.cdf(d1) - 1
        
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) - 
                 r * K * np.exp(-r*T) * norm.cdf(d2)) / 365
        vega = S * norm.pdf(d1) * np.sqrt(T) / 100
        
        return {
            'delta': round(delta, 4),
            'gamma': round(gamma, 6),
            'theta': round(theta, 4),
            'vega': round(vega, 4)
        }


# ============================================================
# SENSITIVITY ANALYZER
# ============================================================

class GreeksSensitivityAnalyzer:
    """
    What-if analysis for options positions.
    Shows P&L and Greeks changes for various scenarios.
    """
    
    def __init__(self):
        self.scenario_ranges = {
            'price': [-10, -5, -2, -1, 0, 1, 2, 5, 10],  # % changes
            'iv': [-20, -10, -5, 0, 5, 10, 20],  # % point changes
            'time': [0, 1, 7, 14, 30]  # days forward
        }
    
    def analyze_price_sensitivity(self, position: Dict, 
                                   spot_price: float) -> SensitivityResult:
        """Analyze P&L sensitivity to price changes."""
        try:
            scenarios = []
            
            for pct_change in self.scenario_ranges['price']:
                new_price = spot_price * (1 + pct_change/100)
                
                # Estimate new P&L using delta approximation
                delta = position.get('delta', 0.5)
                gamma = position.get('gamma', 0.01)
                theta = position.get('theta', -0.05)
                
                price_move = new_price - spot_price
                contracts = position.get('quantity', 1)
                
                # P&L = Delta * dS + 0.5 * Gamma * dS^2 (Taylor expansion)
                delta_pnl = delta * price_move * 100 * contracts
                gamma_pnl = 0.5 * gamma * price_move**2 * 100 * contracts
                total_pnl = delta_pnl + gamma_pnl
                
                # New Greeks
                new_delta = delta + gamma * price_move
                
                scenarios.append({
                    'price_change_pct': pct_change,
                    'new_price': round(new_price, 2),
                    'pnl': round(total_pnl, 2),
                    'delta_contribution': round(delta_pnl, 2),
                    'gamma_contribution': round(gamma_pnl, 2),
                    'new_delta': round(new_delta, 4)
                })
            
            # Find breakevens
            breakeven_up = self._find_breakeven(scenarios, 'up')
            breakeven_down = self._find_breakeven(scenarios, 'down')
            
            # Max profit/loss prices
            max_profit = max(scenarios, key=lambda x: x['pnl'])
            max_loss = min(scenarios, key=lambda x: x['pnl'])
            
            return SensitivityResult(
                ticker=position.get('ticker', 'UNKNOWN'),
                base_price=spot_price,
                scenarios=scenarios,
                breakeven_up=round(breakeven_up, 2),
                breakeven_down=round(breakeven_down, 2),
                max_profit_price=max_profit['new_price'],
                max_loss_price=max_loss['new_price']
            )
            
        except Exception as e:
            logger.error(f"Sensitivity analysis failed: {e}")
            return self._empty_result(position.get('ticker', 'UNKNOWN'), spot_price)
    
    def analyze_iv_sensitivity(self, position: Dict, 
                                current_iv: float) -> List[Dict]:
        """Analyze sensitivity to IV changes."""
        scenarios = []
        vega = position.get('vega', 0.1)
        contracts = position.get('quantity', 1)
        
        for iv_change in self.scenario_ranges['iv']:
            new_iv = current_iv + iv_change/100
            pnl = vega * iv_change * contracts * 100
            
            scenarios.append({
                'iv_change_pct_points': iv_change,
                'new_iv': round(new_iv * 100, 1),
                'pnl': round(pnl, 2)
            })
        
        return scenarios
    
    def analyze_time_sensitivity(self, position: Dict) -> List[Dict]:
        """Analyze sensitivity to time decay."""
        scenarios = []
        theta = position.get('theta', -0.05)
        contracts = position.get('quantity', 1)
        
        cumulative = 0
        for days in self.scenario_ranges['time']:
            if days == 0:
                scenarios.append({'days_forward': 0, 'theta_pnl': 0, 'cumulative': 0})
            else:
                daily_decay = theta * 100 * contracts
                cumulative += daily_decay * days if len(scenarios) == 1 else daily_decay * (days - self.scenario_ranges['time'][len(scenarios)-1])
                scenarios.append({
                    'days_forward': days,
                    'theta_pnl': round(daily_decay * days, 2),
                    'cumulative': round(cumulative, 2)
                })
        
        return scenarios
    
    def _find_breakeven(self, scenarios: List[Dict], direction: str) -> float:
        """Find breakeven price."""
        for i, s in enumerate(scenarios):
            if direction == 'up' and s['price_change_pct'] > 0:
                if s['pnl'] <= 0 and i > 0 and scenarios[i-1]['pnl'] > 0:
                    return s['new_price']
            elif direction == 'down' and s['price_change_pct'] < 0:
                if s['pnl'] <= 0 and i > 0 and scenarios[i-1]['pnl'] > 0:
                    return s['new_price']
        return 0
    
    def _empty_result(self, ticker: str, price: float) -> SensitivityResult:
        return SensitivityResult(
            ticker=ticker,
            base_price=price,
            scenarios=[],
            breakeven_up=0,
            breakeven_down=0,
            max_profit_price=0,
            max_loss_price=0
        )


# ============================================================
# GAMMA SCALPING CALCULATOR
# ============================================================

class GammaScalpingCalculator:
    """
    Calculate optimal gamma scalping entry/exit points.
    Gamma scalping profits from delta hedging a long gamma position.
    """
    
    def __init__(self):
        self.hedge_threshold = 0.10  # Hedge when delta moves 0.10
        self.transaction_cost = 0.01  # Per share
    
    def calculate_scalp_signal(self, position: Dict, 
                                spot_price: float) -> GammaScalpSignal:
        """Calculate gamma scalping signal."""
        try:
            gamma = position.get('gamma', 0.01)
            delta = position.get('delta', 0)
            contracts = position.get('quantity', 1)
            
            # Position gamma in shares
            position_gamma = gamma * 100 * contracts
            
            # Calculate hedge threshold price move
            # Delta change = Gamma * Price change
            # We want delta change = hedge_threshold
            price_move_for_hedge = self.hedge_threshold / gamma if gamma > 0 else float('inf')
            
            # Determine current hedge need
            if abs(delta * contracts) > self.hedge_threshold:
                shares_to_trade = int(abs(delta * 100 * contracts))
                direction = 'sell' if delta > 0 else 'buy'
            else:
                shares_to_trade = 0
                direction = 'none'
            
            # Expected profit from scalping (simplified)
            # Profit = 0.5 * Gamma * (Price move)^2 * 100 * contracts
            expected_move = spot_price * 0.01  # Assume 1% move
            expected_profit = 0.5 * position_gamma * expected_move**2
            expected_profit -= shares_to_trade * self.transaction_cost  # Transaction costs
            
            # Breakeven move
            if position_gamma > 0:
                breakeven = np.sqrt(2 * shares_to_trade * self.transaction_cost / position_gamma)
            else:
                breakeven = float('inf')
            
            return GammaScalpSignal(
                ticker=position.get('ticker', 'UNKNOWN'),
                current_price=spot_price,
                position_gamma=round(position_gamma, 4),
                hedge_threshold=round(price_move_for_hedge, 2),
                shares_to_trade=shares_to_trade,
                direction=direction,
                expected_profit=round(expected_profit, 2),
                breakeven_move=round(breakeven, 2)
            )
            
        except Exception as e:
            logger.error(f"Gamma scalp calculation failed: {e}")
            return GammaScalpSignal(
                ticker=position.get('ticker', 'UNKNOWN'),
                current_price=spot_price,
                position_gamma=0,
                hedge_threshold=0,
                shares_to_trade=0,
                direction='none',
                expected_profit=0,
                breakeven_move=0
            )
    
    def optimal_scalp_frequency(self, gamma: float, iv: float, 
                                 transaction_cost: float) -> Dict:
        """Calculate optimal scalping frequency."""
        # Optimal hedge frequency based on gamma and transaction costs
        # Higher gamma = more frequent hedging
        # Higher transaction costs = less frequent hedging
        
        if gamma <= 0 or iv <= 0:
            return {'optimal_hours': 24, 'hedges_per_day': 1}
        
        # Simplified model
        daily_vol = iv / np.sqrt(252)
        expected_daily_move = daily_vol * 100  # As percentage
        
        # Hedge when delta change exceeds threshold
        threshold_move = self.hedge_threshold / gamma
        hedges_per_day = max(1, int(expected_daily_move / (threshold_move * 100)))
        optimal_hours = 24 / hedges_per_day
        
        return {
            'optimal_hours': round(optimal_hours, 1),
            'hedges_per_day': hedges_per_day,
            'threshold_move_pct': round(threshold_move / 100 * 100, 2)
        }


# ============================================================
# VEGA EXPOSURE ANALYZER
# ============================================================

class VegaExposureAnalyzer:
    """
    Analyze portfolio-wide vega exposure by expiration.
    Helps manage volatility risk across the portfolio.
    """
    
    def __init__(self):
        self.risk_thresholds = {
            'low': 500,
            'moderate': 1500,
            'high': float('inf')
        }
    
    def analyze_portfolio_vega(self, positions: List[Dict]) -> List[VegaExposure]:
        """Analyze vega exposure across portfolio."""
        try:
            # Group by expiration
            exp_groups = {}
            for pos in positions:
                exp = pos.get('expiration', 'unknown')
                if exp not in exp_groups:
                    exp_groups[exp] = []
                exp_groups[exp].append(pos)
            
            exposures = []
            for exp, group_positions in exp_groups.items():
                total_vega = sum(
                    p.get('vega', 0) * p.get('quantity', 1) * 100 
                    for p in group_positions
                )
                
                # Calculate DTE
                try:
                    dte = (datetime.strptime(exp, '%Y-%m-%d') - datetime.now()).days
                except:
                    dte = 30
                
                # Risk level
                abs_vega = abs(total_vega)
                if abs_vega < self.risk_thresholds['low']:
                    risk = 'low'
                elif abs_vega < self.risk_thresholds['moderate']:
                    risk = 'moderate'
                else:
                    risk = 'high'
                
                exposures.append(VegaExposure(
                    expiration=exp,
                    dte=dte,
                    total_vega=round(total_vega, 2),
                    vega_dollars=round(total_vega, 2),
                    positions=[p.get('ticker', '') for p in group_positions],
                    risk_level=risk
                ))
            
            return sorted(exposures, key=lambda x: x.dte)
            
        except Exception as e:
            logger.error(f"Vega analysis failed: {e}")
            return []
    
    def get_hedge_recommendations(self, exposures: List[VegaExposure]) -> List[Dict]:
        """Get vega hedge recommendations."""
        recommendations = []
        
        for exp in exposures:
            if exp.risk_level == 'high':
                if exp.total_vega > 0:
                    recommendations.append({
                        'expiration': exp.expiration,
                        'action': 'Sell volatility or buy puts to reduce long vega',
                        'vega_to_hedge': round(exp.total_vega * 0.5, 2),
                        'urgency': 'high'
                    })
                else:
                    recommendations.append({
                        'expiration': exp.expiration,
                        'action': 'Buy volatility or sell puts to reduce short vega',
                        'vega_to_hedge': round(abs(exp.total_vega) * 0.5, 2),
                        'urgency': 'high'
                    })
        
        return recommendations


# ============================================================
# THETA DECAY PROJECTOR
# ============================================================

class ThetaDecayProjector:
    """
    Project theta decay over time.
    Accounts for weekend/holiday decay patterns.
    """
    
    def __init__(self):
        self.weekend_decay_factor = 3.0  # Friday's theta covers Sat/Sun
    
    def project_decay(self, positions: List[Dict], days: int = 30) -> ThetaProjection:
        """Project cumulative theta decay."""
        try:
            total_daily_theta = sum(
                p.get('theta', 0) * p.get('quantity', 1) * 100 
                for p in positions
            )
            
            dates = []
            daily_theta = []
            cumulative = []
            running_total = 0
            
            start_date = datetime.now()
            
            for i in range(days + 1):
                current_date = start_date + timedelta(days=i)
                dates.append(current_date.strftime('%Y-%m-%d'))
                
                # Weekend decay (Friday)
                if current_date.weekday() == 4:  # Friday
                    day_theta = total_daily_theta * self.weekend_decay_factor
                elif current_date.weekday() in [5, 6]:  # Sat/Sun - decay already counted
                    day_theta = 0
                else:
                    day_theta = total_daily_theta
                
                running_total += day_theta
                daily_theta.append(round(day_theta, 2))
                cumulative.append(round(running_total, 2))
            
            # Calculate weekend decay contribution
            weekends_in_period = days // 7
            weekend_decay = total_daily_theta * 2 * weekends_in_period
            
            ticker = positions[0].get('ticker', 'PORTFOLIO') if positions else 'PORTFOLIO'
            
            return ThetaProjection(
                ticker=ticker,
                dates=dates,
                cumulative_theta=cumulative,
                daily_theta=daily_theta,
                weekend_decay=round(weekend_decay, 2),
                total_decay_30d=round(cumulative[-1], 2) if cumulative else 0
            )
            
        except Exception as e:
            logger.error(f"Theta projection failed: {e}")
            return ThetaProjection(
                ticker='ERROR',
                dates=[],
                cumulative_theta=[],
                daily_theta=[],
                weekend_decay=0,
                total_decay_30d=0
            )
    
    def get_theta_calendar(self, positions: List[Dict]) -> List[Dict]:
        """Get theta calendar showing decay by day."""
        projection = self.project_decay(positions, 14)
        
        calendar = []
        for i, date in enumerate(projection.dates):
            dt = datetime.strptime(date, '%Y-%m-%d')
            calendar.append({
                'date': date,
                'day_name': dt.strftime('%A'),
                'theta': projection.daily_theta[i],
                'cumulative': projection.cumulative_theta[i],
                'is_weekend': dt.weekday() in [5, 6]
            })
        
        return calendar


# ============================================================
# UNIFIED ADVANCED GREEKS
# ============================================================

class AdvancedGreeksEngine:
    """Unified engine for all advanced Greeks analytics."""
    
    def __init__(self):
        self.surface_builder = GreeksSurfaceBuilder()
        self.sensitivity_analyzer = GreeksSensitivityAnalyzer()
        self.gamma_calculator = GammaScalpingCalculator()
        self.vega_analyzer = VegaExposureAnalyzer()
        self.theta_projector = ThetaDecayProjector()
    
    def full_analysis(self, ticker: str, spot_price: float,
                      positions: List[Dict] = None) -> Dict:
        """Complete Greeks analysis."""
        if positions is None:
            positions = [{'ticker': ticker, 'delta': 0.5, 'gamma': 0.02, 
                         'theta': -0.05, 'vega': 0.15, 'quantity': 1}]
        
        # Build surface
        surface = self.surface_builder.build_surface(ticker, spot_price)
        
        # Sensitivity for first position
        sensitivity = self.sensitivity_analyzer.analyze_price_sensitivity(
            positions[0], spot_price
        )
        
        # Gamma scalping
        gamma_signal = self.gamma_calculator.calculate_scalp_signal(
            positions[0], spot_price
        )
        
        # Vega exposure
        vega_exposures = self.vega_analyzer.analyze_portfolio_vega(positions)
        
        # Theta projection
        theta_proj = self.theta_projector.project_decay(positions)
        
        return {
            'ticker': ticker,
            'spot_price': spot_price,
            'surface': {
                'strikes': surface.strikes,
                'expirations': surface.expirations,
                'delta_range': [float(surface.delta_surface.min()), 
                               float(surface.delta_surface.max())],
                'gamma_max': float(surface.gamma_surface.max()),
                'iv_range': [float(surface.iv_surface.min()), 
                            float(surface.iv_surface.max())]
            },
            'sensitivity': {
                'breakeven_up': sensitivity.breakeven_up,
                'breakeven_down': sensitivity.breakeven_down,
                'max_profit_price': sensitivity.max_profit_price,
                'max_loss_price': sensitivity.max_loss_price
            },
            'gamma_scalp': {
                'shares_to_trade': gamma_signal.shares_to_trade,
                'direction': gamma_signal.direction,
                'expected_profit': gamma_signal.expected_profit
            },
            'vega_exposure': {
                'total_positions': len(vega_exposures),
                'high_risk_count': sum(1 for v in vega_exposures if v.risk_level == 'high')
            },
            'theta_projection': {
                'total_30d': theta_proj.total_decay_30d,
                'weekend_decay': theta_proj.weekend_decay
            },
            'generated_at': datetime.now().isoformat()
        }


# ============================================================
# SINGLETON GETTER
# ============================================================

_advanced_greeks_engine = None

def get_advanced_greeks() -> AdvancedGreeksEngine:
    """Get singleton instance."""
    global _advanced_greeks_engine
    if _advanced_greeks_engine is None:
        _advanced_greeks_engine = AdvancedGreeksEngine()
    return _advanced_greeks_engine

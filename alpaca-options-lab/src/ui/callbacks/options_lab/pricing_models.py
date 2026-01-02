"""
Options Pricing Models Module
=============================
Multiple pricing model implementations:
- Black-Scholes model
- Binomial tree model
- Monte Carlo simulation
- Volatility surface builder
- Skew analyzer
- Term structure analyzer
- Greeks attribution

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
from scipy.optimize import brentq
from scipy.interpolate import RectBivariateSpline, griddata

logger = logging.getLogger(__name__)


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class PricingResult:
    """Option pricing result."""
    model: str
    price: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    computation_time: float


@dataclass
class ModelComparison:
    """Comparison of multiple pricing models."""
    ticker: str
    strike: float
    expiration: str
    option_type: str
    spot_price: float
    
    black_scholes: PricingResult
    binomial: PricingResult
    monte_carlo: PricingResult
    
    market_price: Optional[float]
    best_model: str
    price_range: Tuple[float, float]


@dataclass
class VolatilitySurface:
    """Implied volatility surface."""
    ticker: str
    spot_price: float
    strikes: List[float]
    expirations: List[int]
    iv_matrix: np.ndarray
    
    atm_iv: float
    skew_25d: float  # 25-delta put IV - 25-delta call IV
    term_slope: float
    
    generated_at: datetime


@dataclass
class SkewAnalysis:
    """Put-call skew analysis."""
    ticker: str
    expiration: str
    
    put_skew: float  # OTM put premium
    call_skew: float  # OTM call premium
    skew_direction: str  # 'put_heavy', 'call_heavy', 'neutral'
    
    risk_reversal: float  # 25-delta risk reversal
    butterfly: float  # 25-delta butterfly
    
    trading_signal: str
    confidence: float


@dataclass
class TermStructure:
    """Volatility term structure."""
    ticker: str
    expirations: List[int]  # DTEs
    atm_ivs: List[float]
    
    slope: float  # Positive = contango, negative = backwardation
    structure_type: str  # 'contango', 'backwardation', 'flat'
    
    trading_implications: List[str]


@dataclass
class GreeksAttribution:
    """P&L attribution by Greek."""
    total_pnl: float
    delta_pnl: float
    gamma_pnl: float
    theta_pnl: float
    vega_pnl: float
    rho_pnl: float
    unexplained_pnl: float
    
    attribution_pct: Dict[str, float]


# ============================================================
# BLACK-SCHOLES MODEL
# ============================================================

class BlackScholesModel:
    """
    Classic Black-Scholes option pricing model.
    Assumes constant volatility and no dividends.
    """
    
    def __init__(self):
        self.risk_free_rate = 0.05
    
    def price(self, S: float, K: float, T: float, sigma: float,
              option_type: str = 'call', r: float = None) -> PricingResult:
        """Calculate option price and Greeks."""
        import time
        start = time.time()
        
        if r is None:
            r = self.risk_free_rate
        
        T = max(T, 0.0001)  # Avoid division by zero
        
        d1 = (np.log(S/K) + (r + sigma**2/2)*T) / (sigma*np.sqrt(T))
        d2 = d1 - sigma*np.sqrt(T)
        
        if option_type == 'call':
            price = S * norm.cdf(d1) - K * np.exp(-r*T) * norm.cdf(d2)
            delta = norm.cdf(d1)
        else:
            price = K * np.exp(-r*T) * norm.cdf(-d2) - S * norm.cdf(-d1)
            delta = norm.cdf(d1) - 1
        
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        vega = S * norm.pdf(d1) * np.sqrt(T) / 100
        theta = (-S * norm.pdf(d1) * sigma / (2*np.sqrt(T)) - 
                 r * K * np.exp(-r*T) * norm.cdf(d2 if option_type == 'call' else -d2)) / 365
        rho = K * T * np.exp(-r*T) * norm.cdf(d2 if option_type == 'call' else -d2) / 100
        
        if option_type == 'put':
            rho = -K * T * np.exp(-r*T) * norm.cdf(-d2) / 100
        
        return PricingResult(
            model='Black-Scholes',
            price=round(price, 4),
            delta=round(delta, 4),
            gamma=round(gamma, 6),
            theta=round(theta, 4),
            vega=round(vega, 4),
            rho=round(rho, 4),
            computation_time=time.time() - start
        )
    
    def implied_volatility(self, S: float, K: float, T: float,
                           market_price: float, option_type: str = 'call') -> float:
        """Calculate implied volatility from market price."""
        try:
            def objective(sigma):
                result = self.price(S, K, T, sigma, option_type)
                return result.price - market_price
            
            iv = brentq(objective, 0.01, 3.0)
            return round(iv, 4)
        except:
            return 0.25  # Default


# ============================================================
# BINOMIAL MODEL
# ============================================================

class BinomialModel:
    """
    Cox-Ross-Rubinstein binomial tree model.
    More accurate for American options.
    """
    
    def __init__(self, steps: int = 100):
        self.steps = steps
        self.risk_free_rate = 0.05
    
    def price(self, S: float, K: float, T: float, sigma: float,
              option_type: str = 'call', american: bool = False,
              r: float = None) -> PricingResult:
        """Price option using binomial tree."""
        import time
        start = time.time()
        
        if r is None:
            r = self.risk_free_rate
        
        n = self.steps
        dt = T / n
        
        # CRR parameters
        u = np.exp(sigma * np.sqrt(dt))
        d = 1 / u
        p = (np.exp(r * dt) - d) / (u - d)
        
        # Build stock price tree (last row only needed for efficiency)
        stock_prices = np.array([S * u**j * d**(n-j) for j in range(n+1)])
        
        # Option values at maturity
        if option_type == 'call':
            option_values = np.maximum(stock_prices - K, 0)
        else:
            option_values = np.maximum(K - stock_prices, 0)
        
        # Backward induction
        discount = np.exp(-r * dt)
        for i in range(n-1, -1, -1):
            stock_prices = stock_prices[:-1] * u
            continuation = discount * (p * option_values[1:] + (1-p) * option_values[:-1])
            
            if american:
                if option_type == 'call':
                    exercise = np.maximum(stock_prices - K, 0)
                else:
                    exercise = np.maximum(K - stock_prices, 0)
                option_values = np.maximum(continuation, exercise)
            else:
                option_values = continuation
        
        price = option_values[0]
        
        # Approximate Greeks using finite differences
        eps = 0.01
        price_up = self._quick_price(S*(1+eps), K, T, sigma, option_type, american)
        price_down = self._quick_price(S*(1-eps), K, T, sigma, option_type, american)
        delta = (price_up - price_down) / (2 * S * eps)
        gamma = (price_up - 2*price + price_down) / (S * eps)**2
        
        price_sigma_up = self._quick_price(S, K, T, sigma+0.01, option_type, american)
        vega = (price_sigma_up - price) / 0.01 / 100
        
        price_t = self._quick_price(S, K, T-1/365, sigma, option_type, american)
        theta = (price_t - price)
        
        return PricingResult(
            model='Binomial',
            price=round(price, 4),
            delta=round(delta, 4),
            gamma=round(gamma, 6),
            theta=round(theta, 4),
            vega=round(vega, 4),
            rho=0,  # Simplified
            computation_time=time.time() - start
        )
    
    def _quick_price(self, S, K, T, sigma, option_type, american) -> float:
        """Quick pricing for Greeks calculation."""
        n = 50  # Fewer steps for speed
        dt = max(T, 0.001) / n
        r = self.risk_free_rate
        
        u = np.exp(sigma * np.sqrt(dt))
        d = 1 / u
        p = (np.exp(r * dt) - d) / (u - d)
        
        stock_prices = np.array([S * u**j * d**(n-j) for j in range(n+1)])
        
        if option_type == 'call':
            option_values = np.maximum(stock_prices - K, 0)
        else:
            option_values = np.maximum(K - stock_prices, 0)
        
        discount = np.exp(-r * dt)
        for i in range(n-1, -1, -1):
            stock_prices = stock_prices[:-1] * u
            option_values = discount * (p * option_values[1:] + (1-p) * option_values[:-1])
            
            if american:
                if option_type == 'call':
                    exercise = np.maximum(stock_prices - K, 0)
                else:
                    exercise = np.maximum(K - stock_prices, 0)
                option_values = np.maximum(option_values, exercise)
        
        return option_values[0]


# ============================================================
# MONTE CARLO MODEL
# ============================================================

class MonteCarloModel:
    """
    Monte Carlo simulation for option pricing.
    Most flexible, handles path-dependent options.
    """
    
    def __init__(self, simulations: int = 10000, steps: int = 252):
        self.simulations = simulations
        self.steps = steps
        self.risk_free_rate = 0.05
    
    def price(self, S: float, K: float, T: float, sigma: float,
              option_type: str = 'call', r: float = None) -> PricingResult:
        """Price option using Monte Carlo simulation."""
        import time
        start = time.time()
        
        if r is None:
            r = self.risk_free_rate
        
        dt = T / self.steps
        
        # Generate random paths
        np.random.seed(42)  # For reproducibility
        Z = np.random.standard_normal((self.simulations, self.steps))
        
        # Simulate price paths
        drift = (r - 0.5 * sigma**2) * dt
        diffusion = sigma * np.sqrt(dt) * Z
        
        log_returns = drift + diffusion
        price_paths = S * np.exp(np.cumsum(log_returns, axis=1))
        
        # Final prices
        final_prices = price_paths[:, -1]
        
        # Payoffs
        if option_type == 'call':
            payoffs = np.maximum(final_prices - K, 0)
        else:
            payoffs = np.maximum(K - final_prices, 0)
        
        # Discounted expected value
        price = np.exp(-r * T) * np.mean(payoffs)
        
        # Standard error
        std_error = np.std(payoffs) / np.sqrt(self.simulations)
        
        # Approximate Greeks
        eps = 0.01
        price_up = self._quick_mc(S*(1+eps), K, T, sigma, option_type)
        price_down = self._quick_mc(S*(1-eps), K, T, sigma, option_type)
        delta = (price_up - price_down) / (2 * S * eps)
        gamma = (price_up - 2*price + price_down) / (S * eps)**2
        
        return PricingResult(
            model='Monte Carlo',
            price=round(price, 4),
            delta=round(delta, 4),
            gamma=round(gamma, 6),
            theta=0,  # Would need time perturbation
            vega=0,
            rho=0,
            computation_time=time.time() - start
        )
    
    def _quick_mc(self, S, K, T, sigma, option_type) -> float:
        """Quick MC for Greeks."""
        r = self.risk_free_rate
        Z = np.random.standard_normal(1000)
        final_prices = S * np.exp((r - 0.5*sigma**2)*T + sigma*np.sqrt(T)*Z)
        
        if option_type == 'call':
            payoffs = np.maximum(final_prices - K, 0)
        else:
            payoffs = np.maximum(K - final_prices, 0)
        
        return np.exp(-r*T) * np.mean(payoffs)


# ============================================================
# VOLATILITY SURFACE BUILDER
# ============================================================

class VolatilitySurfaceBuilder:
    """
    Build implied volatility surface from market data.
    Interpolates between available strikes and expirations.
    """
    
    def __init__(self):
        self.bs_model = BlackScholesModel()
    
    def build_surface(self, ticker: str, spot: float,
                      options_data: List[Dict] = None) -> VolatilitySurface:
        """Build IV surface from options data."""
        try:
            if options_data and len(options_data) > 10:
                return self._build_from_data(ticker, spot, options_data)
            else:
                return self._build_synthetic(ticker, spot)
        except Exception as e:
            logger.error(f"Surface build failed: {e}")
            return self._build_synthetic(ticker, spot)
    
    def _build_from_data(self, ticker: str, spot: float,
                         data: List[Dict]) -> VolatilitySurface:
        """Build from real data."""
        # Extract IVs
        strikes = sorted(set(d['strike'] for d in data))
        expirations = sorted(set(d['dte'] for d in data))
        
        # Build matrix
        iv_matrix = np.zeros((len(strikes), len(expirations)))
        
        for d in data:
            i = strikes.index(d['strike'])
            j = expirations.index(d['dte'])
            iv_matrix[i, j] = d.get('iv', 0.25)
        
        # Calculate key metrics
        atm_idx = np.argmin(np.abs(np.array(strikes) - spot))
        atm_iv = iv_matrix[atm_idx, 0] if iv_matrix.shape[1] > 0 else 0.25
        
        # Skew (25-delta approximation)
        otm_put_idx = max(0, atm_idx - 2)
        otm_call_idx = min(len(strikes)-1, atm_idx + 2)
        skew_25d = iv_matrix[otm_put_idx, 0] - iv_matrix[otm_call_idx, 0] if iv_matrix.shape[1] > 0 else 0
        
        # Term slope
        if iv_matrix.shape[1] >= 2:
            term_slope = (iv_matrix[atm_idx, -1] - iv_matrix[atm_idx, 0]) / (expirations[-1] - expirations[0]) * 30
        else:
            term_slope = 0
        
        return VolatilitySurface(
            ticker=ticker,
            spot_price=spot,
            strikes=strikes,
            expirations=expirations,
            iv_matrix=iv_matrix,
            atm_iv=round(atm_iv, 4),
            skew_25d=round(skew_25d, 4),
            term_slope=round(term_slope, 4),
            generated_at=datetime.now()
        )
    
    def _build_synthetic(self, ticker: str, spot: float) -> VolatilitySurface:
        """Build synthetic surface."""
        strikes = [spot * (0.85 + 0.05*i) for i in range(7)]
        expirations = [7, 14, 30, 45, 60, 90]
        
        iv_matrix = np.zeros((len(strikes), len(expirations)))
        
        base_iv = 0.25
        for i, strike in enumerate(strikes):
            for j, dte in enumerate(expirations):
                # Skew: higher IV for OTM puts
                moneyness = strike / spot
                skew_adj = 0.1 * (1 - moneyness) if moneyness < 1 else 0.02 * (moneyness - 1)
                
                # Term structure: slightly higher for longer dated
                term_adj = 0.01 * np.sqrt(dte / 30)
                
                iv_matrix[i, j] = base_iv + skew_adj + term_adj
        
        atm_idx = 3
        atm_iv = iv_matrix[atm_idx, 0]
        skew_25d = iv_matrix[1, 0] - iv_matrix[5, 0]
        term_slope = (iv_matrix[atm_idx, -1] - iv_matrix[atm_idx, 0]) / 83 * 30
        
        return VolatilitySurface(
            ticker=ticker,
            spot_price=spot,
            strikes=strikes,
            expirations=expirations,
            iv_matrix=iv_matrix,
            atm_iv=round(atm_iv, 4),
            skew_25d=round(skew_25d, 4),
            term_slope=round(term_slope, 4),
            generated_at=datetime.now()
        )


# ============================================================
# SKEW ANALYZER
# ============================================================

class SkewAnalyzer:
    """
    Analyze put-call skew for trading signals.
    """
    
    def analyze(self, surface: VolatilitySurface, expiration_idx: int = 0) -> SkewAnalysis:
        """Analyze skew for given expiration."""
        try:
            spot = surface.spot_price
            strikes = surface.strikes
            ivs = surface.iv_matrix[:, expiration_idx]
            
            # Find ATM
            atm_idx = np.argmin(np.abs(np.array(strikes) - spot))
            atm_iv = ivs[atm_idx]
            
            # OTM put (lower strike) and call (higher strike)
            put_idx = max(0, atm_idx - 2)
            call_idx = min(len(strikes)-1, atm_idx + 2)
            
            put_iv = ivs[put_idx]
            call_iv = ivs[call_idx]
            
            put_skew = put_iv - atm_iv
            call_skew = call_iv - atm_iv
            
            # Risk reversal: 25-delta call IV - 25-delta put IV
            risk_reversal = call_iv - put_iv
            
            # Butterfly: average wing IV - ATM IV
            butterfly = (put_iv + call_iv) / 2 - atm_iv
            
            # Determine skew direction
            if put_skew > call_skew + 0.02:
                skew_direction = 'put_heavy'
                signal = 'Elevated put demand - consider selling puts or buying calls'
            elif call_skew > put_skew + 0.02:
                skew_direction = 'call_heavy'
                signal = 'Elevated call demand - consider selling calls or buying puts'
            else:
                skew_direction = 'neutral'
                signal = 'Balanced skew - no directional bias from skew'
            
            confidence = min(abs(risk_reversal) * 10, 0.95)
            
            return SkewAnalysis(
                ticker=surface.ticker,
                expiration=str(surface.expirations[expiration_idx]),
                put_skew=round(put_skew, 4),
                call_skew=round(call_skew, 4),
                skew_direction=skew_direction,
                risk_reversal=round(risk_reversal, 4),
                butterfly=round(butterfly, 4),
                trading_signal=signal,
                confidence=round(confidence, 3)
            )
        except Exception as e:
            logger.error(f"Skew analysis failed: {e}")
            return SkewAnalysis(
                ticker=surface.ticker,
                expiration='unknown',
                put_skew=0,
                call_skew=0,
                skew_direction='neutral',
                risk_reversal=0,
                butterfly=0,
                trading_signal='Analysis unavailable',
                confidence=0
            )


# ============================================================
# TERM STRUCTURE ANALYZER
# ============================================================

class TermStructureAnalyzer:
    """
    Analyze volatility term structure.
    """
    
    def analyze(self, surface: VolatilitySurface) -> TermStructure:
        """Analyze term structure."""
        try:
            spot = surface.spot_price
            strikes = surface.strikes
            
            # Find ATM row
            atm_idx = np.argmin(np.abs(np.array(strikes) - spot))
            atm_ivs = list(surface.iv_matrix[atm_idx, :])
            
            expirations = surface.expirations
            
            # Calculate slope (change per 30 days)
            if len(expirations) >= 2:
                slope = (atm_ivs[-1] - atm_ivs[0]) / (expirations[-1] - expirations[0]) * 30
            else:
                slope = 0
            
            # Determine structure type
            if slope > 0.01:
                structure_type = 'contango'
                implications = [
                    'Calendar spreads may be profitable (sell near, buy far)',
                    'Long-dated options are relatively expensive',
                    'Consider time decay strategies on near-term'
                ]
            elif slope < -0.01:
                structure_type = 'backwardation'
                implications = [
                    'Near-term uncertainty is elevated',
                    'Consider buying near-term for hedging',
                    'Reverse calendars may work (buy near, sell far)'
                ]
            else:
                structure_type = 'flat'
                implications = [
                    'Term structure provides no directional bias',
                    'Focus on other factors for trade selection',
                    'Standard strategies apply'
                ]
            
            return TermStructure(
                ticker=surface.ticker,
                expirations=expirations,
                atm_ivs=atm_ivs,
                slope=round(slope, 4),
                structure_type=structure_type,
                trading_implications=implications
            )
        except Exception as e:
            logger.error(f"Term structure analysis failed: {e}")
            return TermStructure(
                ticker=surface.ticker,
                expirations=[],
                atm_ivs=[],
                slope=0,
                structure_type='unknown',
                trading_implications=[]
            )


# ============================================================
# GREEKS ATTRIBUTION
# ============================================================

class GreeksAttributionEngine:
    """
    Attribute P&L changes to specific Greeks.
    """
    
    def attribute(self, position: Dict, 
                  price_change: float,
                  iv_change: float,
                  time_elapsed: int,
                  rate_change: float = 0) -> GreeksAttribution:
        """Calculate P&L attribution."""
        try:
            contracts = position.get('quantity', 1)
            multiplier = 100
            
            # Get Greeks
            delta = position.get('delta', 0.5)
            gamma = position.get('gamma', 0.01)
            theta = position.get('theta', -0.05)
            vega = position.get('vega', 0.10)
            rho = position.get('rho', 0.05)
            
            # Calculate contributions
            delta_pnl = delta * price_change * multiplier * contracts
            gamma_pnl = 0.5 * gamma * price_change**2 * multiplier * contracts
            theta_pnl = theta * time_elapsed * multiplier * contracts
            vega_pnl = vega * (iv_change * 100) * contracts  # IV in percentage points
            rho_pnl = rho * (rate_change * 100) * contracts
            
            explained_pnl = delta_pnl + gamma_pnl + theta_pnl + vega_pnl + rho_pnl
            
            # Actual P&L from position (simplified)
            total_pnl = position.get('pnl', explained_pnl)
            unexplained = total_pnl - explained_pnl
            
            # Attribution percentages
            attribution = {
                'delta': round(delta_pnl / total_pnl * 100 if total_pnl != 0 else 0, 1),
                'gamma': round(gamma_pnl / total_pnl * 100 if total_pnl != 0 else 0, 1),
                'theta': round(theta_pnl / total_pnl * 100 if total_pnl != 0 else 0, 1),
                'vega': round(vega_pnl / total_pnl * 100 if total_pnl != 0 else 0, 1),
                'rho': round(rho_pnl / total_pnl * 100 if total_pnl != 0 else 0, 1),
                'unexplained': round(unexplained / total_pnl * 100 if total_pnl != 0 else 0, 1)
            }
            
            return GreeksAttribution(
                total_pnl=round(total_pnl, 2),
                delta_pnl=round(delta_pnl, 2),
                gamma_pnl=round(gamma_pnl, 2),
                theta_pnl=round(theta_pnl, 2),
                vega_pnl=round(vega_pnl, 2),
                rho_pnl=round(rho_pnl, 2),
                unexplained_pnl=round(unexplained, 2),
                attribution_pct=attribution
            )
        except Exception as e:
            logger.error(f"Attribution failed: {e}")
            return GreeksAttribution(
                total_pnl=0,
                delta_pnl=0,
                gamma_pnl=0,
                theta_pnl=0,
                vega_pnl=0,
                rho_pnl=0,
                unexplained_pnl=0,
                attribution_pct={}
            )


# ============================================================
# MULTI-MODEL PRICER
# ============================================================

class MultiModelPricer:
    """
    Compare multiple pricing models for same option.
    """
    
    def __init__(self):
        self.bs = BlackScholesModel()
        self.binomial = BinomialModel(steps=100)
        self.mc = MonteCarloModel(simulations=5000)
        self.surface_builder = VolatilitySurfaceBuilder()
        self.skew_analyzer = SkewAnalyzer()
        self.term_analyzer = TermStructureAnalyzer()
        self.attribution_engine = GreeksAttributionEngine()
    
    def compare_models(self, S: float, K: float, T: float, sigma: float,
                       option_type: str = 'call',
                       market_price: float = None) -> ModelComparison:
        """Compare all models."""
        bs_result = self.bs.price(S, K, T, sigma, option_type)
        binomial_result = self.binomial.price(S, K, T, sigma, option_type)
        mc_result = self.mc.price(S, K, T, sigma, option_type)
        
        prices = [bs_result.price, binomial_result.price, mc_result.price]
        price_range = (min(prices), max(prices))
        
        # Determine best model
        if market_price:
            errors = {
                'Black-Scholes': abs(bs_result.price - market_price),
                'Binomial': abs(binomial_result.price - market_price),
                'Monte Carlo': abs(mc_result.price - market_price)
            }
            best_model = min(errors, key=errors.get)
        else:
            best_model = 'Black-Scholes'  # Default for European options
        
        return ModelComparison(
            ticker='OPTION',
            strike=K,
            expiration=f"{int(T*365)} days",
            option_type=option_type,
            spot_price=S,
            black_scholes=bs_result,
            binomial=binomial_result,
            monte_carlo=mc_result,
            market_price=market_price,
            best_model=best_model,
            price_range=price_range
        )
    
    def full_analysis(self, ticker: str, spot: float, strike: float,
                      dte: int, sigma: float, option_type: str = 'call') -> Dict:
        """Complete pricing analysis."""
        T = dte / 365
        
        # Model comparison
        comparison = self.compare_models(spot, strike, T, sigma, option_type)
        
        # Build surface
        surface = self.surface_builder.build_surface(ticker, spot)
        
        # Skew analysis
        skew = self.skew_analyzer.analyze(surface)
        
        # Term structure
        term = self.term_analyzer.analyze(surface)
        
        return {
            'ticker': ticker,
            'spot': spot,
            'strike': strike,
            'dte': dte,
            'model_prices': {
                'black_scholes': comparison.black_scholes.price,
                'binomial': comparison.binomial.price,
                'monte_carlo': comparison.monte_carlo.price
            },
            'best_model': comparison.best_model,
            'surface': {
                'atm_iv': surface.atm_iv,
                'skew_25d': surface.skew_25d,
                'term_slope': surface.term_slope
            },
            'skew_analysis': {
                'direction': skew.skew_direction,
                'risk_reversal': skew.risk_reversal,
                'signal': skew.trading_signal
            },
            'term_structure': {
                'type': term.structure_type,
                'slope': term.slope,
                'implications': term.trading_implications
            },
            'generated_at': datetime.now().isoformat()
        }


# ============================================================
# SINGLETON GETTER
# ============================================================

_multi_model_pricer = None

def get_pricing_models() -> MultiModelPricer:
    """Get singleton instance."""
    global _multi_model_pricer
    if _multi_model_pricer is None:
        _multi_model_pricer = MultiModelPricer()
    return _multi_model_pricer

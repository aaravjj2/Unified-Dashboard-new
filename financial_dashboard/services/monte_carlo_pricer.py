"""
Monte Carlo Option Pricing Service
Implements #112 from ROADMAP_ULTIMATE.md
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from scipy.stats import norm
from concurrent.futures import ProcessPoolExecutor
import logging

logger = logging.getLogger(__name__)


@dataclass
class OptionParams:
    """Option parameters for pricing"""
    spot: float
    strike: float
    time_to_expiry: float  # In years
    risk_free_rate: float
    volatility: float
    dividend_yield: float = 0.0
    option_type: str = 'call'  # 'call' or 'put'


class MonteCarloOptionPricer:
    """
    Monte Carlo simulation for option pricing with:
    - European options
    - American options (with LSM)
    - Asian options
    - Barrier options
    - Variance reduction techniques
    """
    
    def __init__(self, num_simulations: int = 100000, num_steps: int = 252):
        self.num_simulations = num_simulations
        self.num_steps = num_steps
        
    def _generate_gbm_paths(self, params: OptionParams, 
                           antithetic: bool = True) -> np.ndarray:
        """Generate Geometric Brownian Motion paths"""
        dt = params.time_to_expiry / self.num_steps
        drift = (params.risk_free_rate - params.dividend_yield - 
                 0.5 * params.volatility**2) * dt
        diffusion = params.volatility * np.sqrt(dt)
        
        n_paths = self.num_simulations // 2 if antithetic else self.num_simulations
        
        # Generate random increments
        z = np.random.standard_normal((n_paths, self.num_steps))
        
        if antithetic:
            z = np.vstack([z, -z])  # Antithetic variates
        
        # Calculate log returns
        log_returns = drift + diffusion * z
        
        # Calculate price paths
        paths = params.spot * np.exp(np.cumsum(log_returns, axis=1))
        paths = np.column_stack([np.full(self.num_simulations, params.spot), paths])
        
        return paths
    
    def price_european(self, params: OptionParams, 
                      control_variate: bool = True) -> Dict[str, float]:
        """Price European option using Monte Carlo"""
        paths = self._generate_gbm_paths(params)
        
        # Terminal prices
        ST = paths[:, -1]
        
        # Calculate payoffs
        if params.option_type == 'call':
            payoffs = np.maximum(ST - params.strike, 0)
        else:
            payoffs = np.maximum(params.strike - ST, 0)
        
        # Discount factor
        discount = np.exp(-params.risk_free_rate * params.time_to_expiry)
        
        # Option price
        mc_price = discount * np.mean(payoffs)
        mc_std = discount * np.std(payoffs) / np.sqrt(self.num_simulations)
        
        # Control variate using Black-Scholes
        if control_variate:
            bs_price = self._black_scholes_price(params)
            # Use spot as control variate
            spot_mean = np.mean(ST)
            spot_expected = params.spot * np.exp((params.risk_free_rate - 
                           params.dividend_yield) * params.time_to_expiry)
            
            # Adjust using control variate
            cov = np.cov(payoffs, ST)[0, 1]
            var_st = np.var(ST)
            beta = cov / var_st if var_st > 0 else 0
            
            adjusted_payoffs = payoffs - beta * (ST - spot_expected)
            mc_price_cv = discount * np.mean(adjusted_payoffs)
            
            return {
                'price': mc_price_cv,
                'std_error': mc_std,
                'bs_price': bs_price,
                'raw_mc_price': mc_price,
                'confidence_95': (mc_price_cv - 1.96*mc_std, mc_price_cv + 1.96*mc_std)
            }
        
        return {
            'price': mc_price,
            'std_error': mc_std,
            'confidence_95': (mc_price - 1.96*mc_std, mc_price + 1.96*mc_std)
        }
    
    def price_american(self, params: OptionParams, 
                      lsm_basis: int = 3) -> Dict[str, float]:
        """
        Price American option using Longstaff-Schwartz LSM method
        """
        paths = self._generate_gbm_paths(params)
        dt = params.time_to_expiry / self.num_steps
        discount_dt = np.exp(-params.risk_free_rate * dt)
        
        # Calculate exercise values at each step
        if params.option_type == 'call':
            exercise_values = np.maximum(paths - params.strike, 0)
        else:
            exercise_values = np.maximum(params.strike - paths, 0)
        
        # Continuation values (start from end)
        continuation_values = exercise_values[:, -1].copy()
        
        # Work backwards
        for t in range(self.num_steps - 1, 0, -1):
            # In-the-money paths
            itm = exercise_values[:, t] > 0
            
            if np.sum(itm) > lsm_basis:
                # Regression for continuation value
                X = paths[itm, t]
                Y = continuation_values[itm] * discount_dt
                
                # Polynomial basis
                X_poly = np.column_stack([X**i for i in range(lsm_basis + 1)])
                
                # Least squares regression
                try:
                    coeffs = np.linalg.lstsq(X_poly, Y, rcond=None)[0]
                    expected_continuation = X_poly @ coeffs
                    
                    # Exercise decision
                    exercise_now = exercise_values[itm, t] > expected_continuation
                    
                    # Update continuation values
                    continuation_values[itm] = np.where(
                        exercise_now,
                        exercise_values[itm, t],
                        continuation_values[itm] * discount_dt
                    )
                except:
                    continuation_values[itm] *= discount_dt
            else:
                continuation_values[itm] *= discount_dt
                
            # Out-of-the-money paths just continue
            continuation_values[~itm] *= discount_dt
        
        # Final discounting
        american_price = np.mean(continuation_values)
        american_std = np.std(continuation_values) / np.sqrt(self.num_simulations)
        
        # Compare to European
        european = self.price_european(params, control_variate=False)
        
        return {
            'price': american_price,
            'std_error': american_std,
            'european_price': european['price'],
            'early_exercise_premium': american_price - european['price'],
            'confidence_95': (american_price - 1.96*american_std, 
                            american_price + 1.96*american_std)
        }
    
    def price_asian(self, params: OptionParams, 
                   averaging: str = 'arithmetic') -> Dict[str, float]:
        """Price Asian option (average price option)"""
        paths = self._generate_gbm_paths(params)
        
        # Calculate average prices
        if averaging == 'arithmetic':
            avg_prices = np.mean(paths[:, 1:], axis=1)
        else:  # geometric
            avg_prices = np.exp(np.mean(np.log(paths[:, 1:]), axis=1))
        
        # Payoffs
        if params.option_type == 'call':
            payoffs = np.maximum(avg_prices - params.strike, 0)
        else:
            payoffs = np.maximum(params.strike - avg_prices, 0)
        
        # Discount
        discount = np.exp(-params.risk_free_rate * params.time_to_expiry)
        asian_price = discount * np.mean(payoffs)
        asian_std = discount * np.std(payoffs) / np.sqrt(self.num_simulations)
        
        return {
            'price': asian_price,
            'std_error': asian_std,
            'averaging': averaging,
            'confidence_95': (asian_price - 1.96*asian_std, asian_price + 1.96*asian_std)
        }
    
    def price_barrier(self, params: OptionParams, 
                     barrier: float, 
                     barrier_type: str = 'down-and-out') -> Dict[str, float]:
        """
        Price barrier option
        Types: 'up-and-in', 'up-and-out', 'down-and-in', 'down-and-out'
        """
        paths = self._generate_gbm_paths(params)
        
        # Check barrier hits
        if 'down' in barrier_type:
            barrier_hit = np.any(paths <= barrier, axis=1)
        else:  # up
            barrier_hit = np.any(paths >= barrier, axis=1)
        
        # Terminal payoffs
        ST = paths[:, -1]
        if params.option_type == 'call':
            base_payoffs = np.maximum(ST - params.strike, 0)
        else:
            base_payoffs = np.maximum(params.strike - ST, 0)
        
        # Apply barrier condition
        if 'out' in barrier_type:
            payoffs = np.where(barrier_hit, 0, base_payoffs)
        else:  # 'in'
            payoffs = np.where(barrier_hit, base_payoffs, 0)
        
        # Price
        discount = np.exp(-params.risk_free_rate * params.time_to_expiry)
        barrier_price = discount * np.mean(payoffs)
        barrier_std = discount * np.std(payoffs) / np.sqrt(self.num_simulations)
        
        # Vanilla price for comparison
        vanilla = self.price_european(params, control_variate=False)
        
        return {
            'price': barrier_price,
            'std_error': barrier_std,
            'barrier_type': barrier_type,
            'barrier': barrier,
            'vanilla_price': vanilla['price'],
            'knock_probability': np.mean(barrier_hit),
            'confidence_95': (barrier_price - 1.96*barrier_std, 
                            barrier_price + 1.96*barrier_std)
        }
    
    def calculate_greeks(self, params: OptionParams, 
                        bump_pct: float = 0.01) -> Dict[str, float]:
        """Calculate Greeks using finite differences"""
        base_price = self.price_european(params)['price']
        
        # Delta: dV/dS
        params_up = OptionParams(**{**params.__dict__, 'spot': params.spot * (1 + bump_pct)})
        params_down = OptionParams(**{**params.__dict__, 'spot': params.spot * (1 - bump_pct)})
        price_up = self.price_european(params_up)['price']
        price_down = self.price_european(params_down)['price']
        delta = (price_up - price_down) / (2 * params.spot * bump_pct)
        
        # Gamma: d²V/dS²
        gamma = (price_up - 2*base_price + price_down) / (params.spot * bump_pct)**2
        
        # Vega: dV/dσ
        vol_bump = 0.01
        params_vol_up = OptionParams(**{**params.__dict__, 'volatility': params.volatility + vol_bump})
        params_vol_down = OptionParams(**{**params.__dict__, 'volatility': params.volatility - vol_bump})
        vega = (self.price_european(params_vol_up)['price'] - 
               self.price_european(params_vol_down)['price']) / (2 * vol_bump) / 100
        
        # Theta: -dV/dt (per day)
        dt = 1/365
        params_t = OptionParams(**{**params.__dict__, 
                                   'time_to_expiry': max(params.time_to_expiry - dt, 0.001)})
        theta = -(self.price_european(params_t)['price'] - base_price)
        
        # Rho: dV/dr
        r_bump = 0.001
        params_r_up = OptionParams(**{**params.__dict__, 'risk_free_rate': params.risk_free_rate + r_bump})
        rho = (self.price_european(params_r_up)['price'] - base_price) / r_bump / 100
        
        return {
            'delta': delta,
            'gamma': gamma,
            'vega': vega,
            'theta': theta,
            'rho': rho,
            'price': base_price
        }
    
    def _black_scholes_price(self, params: OptionParams) -> float:
        """Black-Scholes analytical price for comparison"""
        d1 = (np.log(params.spot / params.strike) + 
             (params.risk_free_rate - params.dividend_yield + 
              0.5 * params.volatility**2) * params.time_to_expiry) / \
             (params.volatility * np.sqrt(params.time_to_expiry))
        d2 = d1 - params.volatility * np.sqrt(params.time_to_expiry)
        
        if params.option_type == 'call':
            price = (params.spot * np.exp(-params.dividend_yield * params.time_to_expiry) * 
                    norm.cdf(d1) - 
                    params.strike * np.exp(-params.risk_free_rate * params.time_to_expiry) * 
                    norm.cdf(d2))
        else:
            price = (params.strike * np.exp(-params.risk_free_rate * params.time_to_expiry) * 
                    norm.cdf(-d2) - 
                    params.spot * np.exp(-params.dividend_yield * params.time_to_expiry) * 
                    norm.cdf(-d1))
        
        return price
    
    def run_convergence_study(self, params: OptionParams, 
                             sim_counts: List[int] = None) -> pd.DataFrame:
        """Study convergence with increasing simulations"""
        if sim_counts is None:
            sim_counts = [1000, 5000, 10000, 50000, 100000, 500000]
        
        results = []
        bs_price = self._black_scholes_price(params)
        
        for n in sim_counts:
            self.num_simulations = n
            mc_result = self.price_european(params)
            
            results.append({
                'simulations': n,
                'mc_price': mc_result['price'],
                'std_error': mc_result['std_error'],
                'bs_price': bs_price,
                'error': abs(mc_result['price'] - bs_price),
                'error_pct': abs(mc_result['price'] - bs_price) / bs_price * 100
            })
        
        return pd.DataFrame(results)
    
    def price_portfolio(self, options: List[OptionParams], 
                       positions: List[float]) -> Dict[str, Any]:
        """Price a portfolio of options"""
        total_value = 0
        total_delta = 0
        total_gamma = 0
        total_vega = 0
        total_theta = 0
        
        option_details = []
        
        for opt, pos in zip(options, positions):
            greeks = self.calculate_greeks(opt)
            value = greeks['price'] * pos * 100  # Standard contract size
            
            total_value += value
            total_delta += greeks['delta'] * pos * 100
            total_gamma += greeks['gamma'] * pos * 100
            total_vega += greeks['vega'] * pos * 100
            total_theta += greeks['theta'] * pos * 100
            
            option_details.append({
                'strike': opt.strike,
                'type': opt.option_type,
                'expiry': opt.time_to_expiry,
                'position': pos,
                'value': value,
                'delta': greeks['delta'] * pos * 100,
                'gamma': greeks['gamma'] * pos * 100,
                'vega': greeks['vega'] * pos * 100,
                'theta': greeks['theta'] * pos * 100
            })
        
        return {
            'total_value': total_value,
            'total_delta': total_delta,
            'total_gamma': total_gamma,
            'total_vega': total_vega,
            'total_theta': total_theta,
            'options': option_details
        }


# Convenience function for quick pricing
def monte_carlo_price(spot: float, strike: float, expiry: float, 
                     volatility: float, rate: float = 0.05,
                     option_type: str = 'call', 
                     n_sims: int = 100000) -> Dict[str, float]:
    """Quick Monte Carlo pricing"""
    params = OptionParams(
        spot=spot,
        strike=strike,
        time_to_expiry=expiry,
        risk_free_rate=rate,
        volatility=volatility,
        option_type=option_type
    )
    pricer = MonteCarloOptionPricer(num_simulations=n_sims)
    return pricer.price_european(params)


# Singleton instance
_mc_pricer = None

def get_mc_pricer(n_sims: int = 100000) -> MonteCarloOptionPricer:
    global _mc_pricer
    if _mc_pricer is None or _mc_pricer.num_simulations != n_sims:
        _mc_pricer = MonteCarloOptionPricer(num_simulations=n_sims)
    return _mc_pricer

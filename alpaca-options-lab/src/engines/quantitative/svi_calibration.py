"""
SVI/SSVI Volatility Surface Calibration
Week 7: Volatility Surface Modeling (SVI/SSVI)

Implements Stochastic Volatility Inspired (SVI) model calibration per roadmap.
Based on: wangys96/SVI-Volatility-Surface-Calibration
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class SVICalibrator:
    """
    Stochastic Volatility Inspired (SVI) model calibrator.
    
    The Raw SVI equation for total variance w(k) at log-strike k is:
    w(k) = a + b * { ρ(k - m) + sqrt((k - m)² + σ²) }
    
    Parameters:
    - a: vertical shift
    - b: overall variance level
    - ρ: skew (correlation between price and vol)
    - m: location of minimum
    - σ: smile curvature (vol of vol)
    """
    
    def __init__(self):
        self.params = None
        self.calibration_error = None
    
    def svi_raw(self, k: np.ndarray, a: float, b: float, rho: float, 
                m: float, sigma: float) -> np.ndarray:
        """
        Raw SVI parameterization.
        
        Args:
            k: Log-strike array
            a, b, rho, m, sigma: SVI parameters
            
        Returns:
            Total variance w(k)
        """
        return a + b * (rho * (k - m) + np.sqrt((k - m)**2 + sigma**2))
    
    def svi_quasi(self, k: np.ndarray, mu: float, sigma: float, rho: float,
                  gamma: float, eta: float) -> np.ndarray:
        """
        Quasi-parameterization (more numerically stable for optimization).
        
        Args:
            k: Log-strike array
            mu, sigma, rho, gamma, eta: Quasi parameters
            
        Returns:
            Total variance w(k)
        """
        # Convert quasi to raw parameters
        a = mu - gamma * sigma
        b = gamma
        m = -rho * sigma / np.sqrt(1 - rho**2) if abs(rho) < 1 else 0
        sigma_raw = sigma * np.sqrt(1 - rho**2) if abs(rho) < 1 else sigma
        
        return self.svi_raw(k, a, b, rho, m, sigma_raw)
    
    def objective_function(self, params: np.ndarray, k: np.ndarray, 
                          w_market: np.ndarray, use_quasi: bool = True) -> float:
        """
        Objective function for calibration (RMSE).
        
        Args:
            params: SVI parameters [a, b, rho, m, sigma] or [mu, sigma, rho, gamma, eta]
            k: Log-strikes
            w_market: Market-observed total variance
            use_quasi: Use quasi-parameterization
            
        Returns:
            Root Mean Square Error
        """
        try:
            if use_quasi:
                mu, sigma, rho, gamma, eta = params
                w_model = self.svi_quasi(k, mu, sigma, rho, gamma, eta)
            else:
                a, b, rho, m, sigma = params
                w_model = self.svi_raw(k, a, b, rho, m, sigma)
            
            # Ensure non-negative variance
            w_model = np.maximum(w_model, 1e-6)
            
            # RMSE
            rmse = np.sqrt(np.mean((w_model - w_market)**2))
            return rmse
            
        except Exception as e:
            logger.warning(f"SVI objective function error: {e}")
            return 1e6  # Large penalty for invalid parameters
    
    def calibrate(self, strikes: np.ndarray, ivs: np.ndarray, 
                  spot: float, t: float = 1.0,
                  method: str = 'SLSQP') -> Dict:
        """
        Calibrate SVI parameters to market data.
        
        Args:
            strikes: Strike prices
            ivs: Implied volatilities (as decimals, e.g., 0.25 for 25%)
            spot: Spot price
            t: Time to expiration (years)
            method: Optimization method ('SLSQP' or 'Nelder-Mead')
            
        Returns:
            Dictionary with calibrated parameters and metrics
        """
        try:
            # Convert to log-strikes
            k = np.log(strikes / spot)
            
            # Convert IV to total variance: w = σ² * T
            w_market = (ivs ** 2) * t
            
            # Initial guess (quasi-parameterization)
            # Reasonable defaults for equity options
            initial_params = np.array([
                0.04,  # mu: base variance level
                0.1,   # sigma: volatility of volatility
                -0.5,  # rho: negative skew (typical for equities)
                0.3,   # gamma: overall level
                0.05   # eta: additional curvature
            ])
            
            # Bounds for quasi parameters
            bounds = [
                (0.001, 0.5),    # mu
                (0.001, 1.0),    # sigma
                (-0.99, 0.99),   # rho
                (0.001, 2.0),    # gamma
                (0.001, 0.5)     # eta
            ]
            
            # Constraints: ensure no-arbitrage conditions
            constraints = [
                {'type': 'ineq', 'fun': lambda p: p[1] - 0.001},  # sigma > 0
                {'type': 'ineq', 'fun': lambda p: 1.0 - abs(p[2])},  # |rho| < 1
            ]
            
            # Optimize
            result = minimize(
                self.objective_function,
                initial_params,
                args=(k, w_market, True),  # use_quasi=True
                method=method,
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000, 'ftol': 1e-6}
            )
            
            if result.success:
                self.params = result.x
                self.calibration_error = result.fun
                
                # Convert quasi to raw for output
                mu, sigma, rho, gamma, eta = result.x
                a = mu - gamma * sigma
                b = gamma
                m = -rho * sigma / np.sqrt(1 - rho**2) if abs(rho) < 1 else 0
                sigma_raw = sigma * np.sqrt(1 - rho**2) if abs(rho) < 1 else sigma
                
                return {
                    'success': True,
                    'params_raw': {
                        'a': float(a),
                        'b': float(b),
                        'rho': float(rho),
                        'm': float(m),
                        'sigma': float(sigma_raw)
                    },
                    'params_quasi': {
                        'mu': float(mu),
                        'sigma': float(sigma),
                        'rho': float(rho),
                        'gamma': float(gamma),
                        'eta': float(eta)
                    },
                    'rmse': float(result.fun),
                    'calibration_error': float(result.fun),
                    'iterations': int(result.nit)
                }
            else:
                logger.warning(f"SVI calibration failed: {result.message}")
                return {
                    'success': False,
                    'error': result.message,
                    'rmse': float(result.fun) if hasattr(result, 'fun') else None
                }
                
        except Exception as e:
            logger.error(f"SVI calibration error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def evaluate(self, strikes: np.ndarray, spot: float, 
                 params: Optional[Dict] = None) -> np.ndarray:
        """
        Evaluate SVI model at given strikes.
        
        Args:
            strikes: Strike prices
            spot: Spot price
            params: SVI parameters (if None, use calibrated params)
            
        Returns:
            Implied volatilities
        """
        if params is None:
            if self.params is None:
                raise ValueError("No parameters available. Run calibrate() first.")
            params = self.params
        
        k = np.log(strikes / spot)
        
        # Use quasi parameterization
        mu, sigma, rho, gamma, eta = params
        w = self.svi_quasi(k, mu, sigma, rho, gamma, eta)
        
        # Convert total variance to IV: σ = sqrt(w / T)
        # Assume T=1 for now (can be parameterized)
        ivs = np.sqrt(np.maximum(w, 0) / 1.0)
        
        return ivs


class SSVICalibrator(SVICalibrator):
    """
    Surface SVI (SSVI) calibrator.
    
    SSVI imposes constraints on how parameters evolve over time to ensure
    the surface is arbitrage-free across all maturities.
    """
    
    def calibrate_surface(self, expirations: List[float], 
                          strikes_by_exp: Dict[float, np.ndarray],
                          ivs_by_exp: Dict[float, np.ndarray],
                          spot: float) -> Dict:
        """
        Calibrate SSVI surface across multiple expirations.
        
        Args:
            expirations: List of time-to-expiration (years)
            strikes_by_exp: Dict mapping expiration -> strikes
            ivs_by_exp: Dict mapping expiration -> IVs
            spot: Spot price
            
        Returns:
            Dictionary with calibrated surface parameters
        """
        surface_params = {}
        
        for t in sorted(expirations):
            strikes = strikes_by_exp[t]
            ivs = ivs_by_exp[t]
            
            # Calibrate each slice
            result = self.calibrate(strikes, ivs, spot, t)
            
            if result['success']:
                surface_params[t] = result
            else:
                logger.warning(f"SSVI calibration failed for T={t}: {result.get('error')}")
        
        # Check for calendar spread arbitrage
        # (Simplified check - full implementation would verify all pairs)
        arbitrage_free = self._check_arbitrage_free(surface_params)
        
        return {
            'surface_params': surface_params,
            'arbitrage_free': arbitrage_free,
            'num_slices': len(surface_params)
        }
    
    def _check_arbitrage_free(self, surface_params: Dict) -> bool:
        """
        Check if surface is arbitrage-free (simplified check).
        
        Args:
            surface_params: Dictionary of calibrated parameters by expiration
            
        Returns:
            True if surface appears arbitrage-free
        """
        # Basic check: ensure parameters evolve smoothly
        # Full implementation would check butterfly and calendar spread constraints
        if len(surface_params) < 2:
            return True
        
        # Check that variance increases with time (rough check)
        times = sorted(surface_params.keys())
        prev_var = None
        
        for t in times:
            params = surface_params[t].get('params_raw', {})
            a = params.get('a', 0)
            b = params.get('b', 0)
            
            # Approximate variance at ATM
            curr_var = a + b * abs(params.get('m', 0))
            
            if prev_var is not None and curr_var < prev_var * 0.9:
                logger.warning(f"Potential arbitrage: variance decreases at T={t}")
                return False
            
            prev_var = curr_var
        
        return True


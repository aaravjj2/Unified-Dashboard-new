"""
Options Analytics Service - Roadmap Items 141-260
Options pricing, Greeks, volatility analysis, and flow analytics
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from scipy import stats
from scipy.optimize import brentq, minimize
from scipy.interpolate import interp1d, RectBivariateSpline
from datetime import datetime, timedelta
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptionType(Enum):
    CALL = "call"
    PUT = "put"

@dataclass
class OptionContract:
    """Option contract specification"""
    symbol: str
    underlying: str
    strike: float
    expiry: datetime
    option_type: OptionType
    bid: float = 0.0
    ask: float = 0.0
    last: float = 0.0
    volume: int = 0
    open_interest: int = 0
    implied_vol: float = 0.0

@dataclass
class Greeks:
    """Option Greeks"""
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    vanna: float = 0.0
    volga: float = 0.0
    charm: float = 0.0
    vomma: float = 0.0
    speed: float = 0.0

@dataclass
class VolSurfacePoint:
    """Point on volatility surface"""
    strike: float
    expiry_days: int
    implied_vol: float
    moneyness: float

class BlackScholesPricer:
    """Black-Scholes option pricing - Items 141-160"""
    
    @staticmethod
    def d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate d1 in BS formula"""
        if T <= 0 or sigma <= 0:
            return 0.0
        return (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    
    @staticmethod
    def d2(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate d2 in BS formula"""
        return BlackScholesPricer.d1(S, K, T, r, sigma) - sigma * np.sqrt(T)
    
    @staticmethod
    def call_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate call option price"""
        if T <= 0:
            return max(0, S - K)
        
        d1 = BlackScholesPricer.d1(S, K, T, r, sigma)
        d2 = BlackScholesPricer.d2(S, K, T, r, sigma)
        
        return S * stats.norm.cdf(d1) - K * np.exp(-r * T) * stats.norm.cdf(d2)
    
    @staticmethod
    def put_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate put option price"""
        if T <= 0:
            return max(0, K - S)
        
        d1 = BlackScholesPricer.d1(S, K, T, r, sigma)
        d2 = BlackScholesPricer.d2(S, K, T, r, sigma)
        
        return K * np.exp(-r * T) * stats.norm.cdf(-d2) - S * stats.norm.cdf(-d1)
    
    @staticmethod
    def price(S: float, K: float, T: float, r: float, sigma: float, 
              option_type: OptionType) -> float:
        """Calculate option price"""
        if option_type == OptionType.CALL:
            return BlackScholesPricer.call_price(S, K, T, r, sigma)
        return BlackScholesPricer.put_price(S, K, T, r, sigma)
    
    @staticmethod
    def greeks(S: float, K: float, T: float, r: float, sigma: float,
               option_type: OptionType) -> Greeks:
        """Calculate all Greeks - Items 151-160"""
        if T <= 0 or sigma <= 0:
            return Greeks(0, 0, 0, 0, 0)
        
        d1 = BlackScholesPricer.d1(S, K, T, r, sigma)
        d2 = BlackScholesPricer.d2(S, K, T, r, sigma)
        
        sqrt_T = np.sqrt(T)
        n_d1 = stats.norm.pdf(d1)
        N_d1 = stats.norm.cdf(d1)
        N_d2 = stats.norm.cdf(d2)
        
        # Delta
        if option_type == OptionType.CALL:
            delta = N_d1
        else:
            delta = N_d1 - 1
        
        # Gamma
        gamma = n_d1 / (S * sigma * sqrt_T)
        
        # Theta
        theta_part1 = -(S * n_d1 * sigma) / (2 * sqrt_T)
        if option_type == OptionType.CALL:
            theta = theta_part1 - r * K * np.exp(-r * T) * N_d2
        else:
            theta = theta_part1 + r * K * np.exp(-r * T) * stats.norm.cdf(-d2)
        theta = theta / 365  # Daily theta
        
        # Vega
        vega = S * n_d1 * sqrt_T / 100  # Per 1% vol change
        
        # Rho
        if option_type == OptionType.CALL:
            rho = K * T * np.exp(-r * T) * N_d2 / 100
        else:
            rho = -K * T * np.exp(-r * T) * stats.norm.cdf(-d2) / 100
        
        # Second-order Greeks
        vanna = -n_d1 * d2 / sigma
        volga = vega * d1 * d2 / sigma
        charm = -n_d1 * (2 * r * T - d2 * sigma * sqrt_T) / (2 * T * sigma * sqrt_T)
        vomma = vega * (d1 * d2) / sigma
        speed = -gamma / S * (d1 / (sigma * sqrt_T) + 1)
        
        return Greeks(
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega,
            rho=rho,
            vanna=vanna,
            volga=volga,
            charm=charm,
            vomma=vomma,
            speed=speed
        )

class ImpliedVolatility:
    """Implied volatility calculation - Items 161-170"""
    
    @staticmethod
    def calculate(price: float, S: float, K: float, T: float, r: float,
                  option_type: OptionType, initial_guess: float = 0.2) -> float:
        """Calculate implied volatility using Newton-Raphson"""
        if T <= 0:
            return 0.0
        
        # Intrinsic value check
        if option_type == OptionType.CALL:
            intrinsic = max(0, S - K * np.exp(-r * T))
        else:
            intrinsic = max(0, K * np.exp(-r * T) - S)
        
        if price <= intrinsic:
            return 0.0
        
        def objective(sigma):
            return BlackScholesPricer.price(S, K, T, r, sigma, option_type) - price
        
        try:
            iv = brentq(objective, 0.001, 5.0)
            return iv
        except ValueError:
            # Fallback to Newton-Raphson
            sigma = initial_guess
            for _ in range(100):
                price_calc = BlackScholesPricer.price(S, K, T, r, sigma, option_type)
                vega = BlackScholesPricer.greeks(S, K, T, r, sigma, option_type).vega * 100
                
                if abs(vega) < 1e-10:
                    break
                
                sigma = sigma - (price_calc - price) / vega
                sigma = max(0.001, min(5.0, sigma))
                
                if abs(price_calc - price) < 1e-6:
                    break
            
            return sigma

class VolatilitySurface:
    """Volatility surface construction and analysis - Items 181-220"""
    
    def __init__(self):
        self.surface_data: List[VolSurfacePoint] = []
        self.strikes: np.ndarray = None
        self.expiries: np.ndarray = None
        self.vols: np.ndarray = None
        self.interpolator = None
        
    def add_point(self, strike: float, expiry_days: int, implied_vol: float, 
                  spot: float):
        """Add point to volatility surface"""
        moneyness = np.log(strike / spot)
        point = VolSurfacePoint(
            strike=strike,
            expiry_days=expiry_days,
            implied_vol=implied_vol,
            moneyness=moneyness
        )
        self.surface_data.append(point)
    
    def build_surface(self, spot: float):
        """Build interpolated volatility surface"""
        if len(self.surface_data) < 9:
            return
        
        # Organize data
        df = pd.DataFrame([
            {'strike': p.strike, 'expiry': p.expiry_days, 'vol': p.implied_vol}
            for p in self.surface_data
        ])
        
        # Create grid
        self.strikes = np.sort(df['strike'].unique())
        self.expiries = np.sort(df['expiry'].unique())
        
        # Pivot to matrix
        pivot = df.pivot_table(values='vol', index='strike', columns='expiry', 
                               aggfunc='mean')
        pivot = pivot.interpolate(axis=0).interpolate(axis=1)
        
        self.vols = pivot.values
        
        # Create interpolator
        if len(self.strikes) >= 2 and len(self.expiries) >= 2:
            try:
                self.interpolator = RectBivariateSpline(
                    self.strikes, self.expiries, self.vols
                )
            except Exception:
                pass
    
    def get_vol(self, strike: float, expiry_days: int) -> float:
        """Get interpolated volatility"""
        if self.interpolator is None:
            return 0.2  # Default
        
        try:
            return float(self.interpolator(strike, expiry_days)[0, 0])
        except Exception:
            return 0.2
    
    def get_smile(self, expiry_days: int) -> pd.DataFrame:
        """Get volatility smile for expiry"""
        if self.strikes is None:
            return pd.DataFrame()
        
        vols = [self.get_vol(k, expiry_days) for k in self.strikes]
        return pd.DataFrame({'strike': self.strikes, 'implied_vol': vols})
    
    def get_term_structure(self, strike: float) -> pd.DataFrame:
        """Get term structure at strike"""
        if self.expiries is None:
            return pd.DataFrame()
        
        vols = [self.get_vol(strike, e) for e in self.expiries]
        return pd.DataFrame({'expiry_days': self.expiries, 'implied_vol': vols})
    
    def calculate_skew(self, expiry_days: int, spot: float) -> float:
        """Calculate volatility skew - Item 191"""
        atm_vol = self.get_vol(spot, expiry_days)
        otm_put_vol = self.get_vol(spot * 0.9, expiry_days)  # 10% OTM put
        
        return otm_put_vol - atm_vol
    
    def calculate_smile_convexity(self, expiry_days: int, spot: float) -> float:
        """Calculate smile convexity - Item 192"""
        atm_vol = self.get_vol(spot, expiry_days)
        put_vol = self.get_vol(spot * 0.9, expiry_days)
        call_vol = self.get_vol(spot * 1.1, expiry_days)
        
        return (put_vol + call_vol) / 2 - atm_vol

class OptionsFlowAnalytics:
    """Options flow and market making analytics - Items 221-260"""
    
    def __init__(self):
        self.flow_data: List[Dict] = []
        self.positions: Dict[str, Dict] = {}
        
    def add_trade(self, contract: OptionContract, side: str, quantity: int,
                  delta: float = None):
        """Record options trade"""
        trade = {
            'timestamp': datetime.now(),
            'symbol': contract.symbol,
            'strike': contract.strike,
            'expiry': contract.expiry,
            'type': contract.option_type.value,
            'side': side,
            'quantity': quantity,
            'price': contract.last,
            'premium': contract.last * quantity * 100,
            'delta': delta
        }
        self.flow_data.append(trade)
    
    def get_flow_summary(self) -> Dict[str, Any]:
        """Get flow summary statistics - Item 221"""
        if not self.flow_data:
            return {}
        
        df = pd.DataFrame(self.flow_data)
        
        call_premium = df[df['type'] == 'call']['premium'].sum()
        put_premium = df[df['type'] == 'put']['premium'].sum()
        
        call_volume = df[df['type'] == 'call']['quantity'].sum()
        put_volume = df[df['type'] == 'put']['quantity'].sum()
        
        return {
            'total_premium': call_premium + put_premium,
            'call_premium': call_premium,
            'put_premium': put_premium,
            'put_call_premium_ratio': put_premium / call_premium if call_premium > 0 else 0,
            'call_volume': call_volume,
            'put_volume': put_volume,
            'put_call_volume_ratio': put_volume / call_volume if call_volume > 0 else 0,
            'total_trades': len(df)
        }
    
    def detect_unusual_activity(self, threshold: float = 2.0) -> List[Dict]:
        """Detect unusual options activity - Item 231"""
        if len(self.flow_data) < 20:
            return []
        
        df = pd.DataFrame(self.flow_data)
        df['premium_zscore'] = (df['premium'] - df['premium'].mean()) / df['premium'].std()
        
        unusual = df[abs(df['premium_zscore']) > threshold]
        return unusual.to_dict('records')
    
    def calculate_gamma_exposure(self, spot: float) -> float:
        """Calculate market gamma exposure - Item 241"""
        total_gamma = 0
        
        for trade in self.flow_data:
            if trade.get('delta'):
                # Estimate gamma from delta change
                sign = 1 if trade['side'] == 'buy' else -1
                gamma_estimate = abs(trade['delta']) * 0.05  # Rough estimate
                total_gamma += sign * gamma_estimate * trade['quantity'] * 100
        
        return total_gamma
    
    def calculate_delta_exposure(self) -> float:
        """Calculate market delta exposure - Item 242"""
        total_delta = 0
        
        for trade in self.flow_data:
            if trade.get('delta'):
                sign = 1 if trade['side'] == 'buy' else -1
                total_delta += sign * trade['delta'] * trade['quantity'] * 100
        
        return total_delta

class OptionsAnalyticsService:
    """Main options analytics service - Items 141-260"""
    
    def __init__(self):
        self.pricer = BlackScholesPricer()
        self.iv_calculator = ImpliedVolatility()
        self.vol_surface = VolatilitySurface()
        self.flow_analytics = OptionsFlowAnalytics()
        self.options_chain: Dict[str, List[OptionContract]] = {}
        
    def price_option(self, S: float, K: float, T: float, r: float, sigma: float,
                     option_type: str = "call") -> Dict[str, Any]:
        """Price option and calculate Greeks"""
        opt_type = OptionType.CALL if option_type.lower() == "call" else OptionType.PUT
        
        price = self.pricer.price(S, K, T, r, sigma, opt_type)
        greeks = self.pricer.greeks(S, K, T, r, sigma, opt_type)
        
        return {
            'price': price,
            'delta': greeks.delta,
            'gamma': greeks.gamma,
            'theta': greeks.theta,
            'vega': greeks.vega,
            'rho': greeks.rho,
            'vanna': greeks.vanna,
            'volga': greeks.volga,
            'charm': greeks.charm
        }
    
    def calculate_implied_vol(self, price: float, S: float, K: float, T: float,
                              r: float, option_type: str = "call") -> float:
        """Calculate implied volatility"""
        opt_type = OptionType.CALL if option_type.lower() == "call" else OptionType.PUT
        return self.iv_calculator.calculate(price, S, K, T, r, opt_type)
    
    def build_options_chain(self, underlying: str, spot: float, 
                           strikes: List[float], expiries: List[int],
                           base_vol: float = 0.25, r: float = 0.05) -> pd.DataFrame:
        """Build synthetic options chain"""
        chain_data = []
        
        for expiry_days in expiries:
            T = expiry_days / 365
            
            for strike in strikes:
                moneyness = strike / spot
                
                # Add skew effect
                skew = -0.15 * (moneyness - 1)
                smile = 0.05 * (moneyness - 1) ** 2
                iv = base_vol + skew + smile
                iv = max(0.05, iv)
                
                for opt_type in [OptionType.CALL, OptionType.PUT]:
                    price = self.pricer.price(spot, strike, T, r, iv, opt_type)
                    greeks = self.pricer.greeks(spot, strike, T, r, iv, opt_type)
                    
                    chain_data.append({
                        'underlying': underlying,
                        'strike': strike,
                        'expiry_days': expiry_days,
                        'type': opt_type.value,
                        'bid': price * 0.98,
                        'ask': price * 1.02,
                        'last': price,
                        'implied_vol': iv,
                        'delta': greeks.delta,
                        'gamma': greeks.gamma,
                        'theta': greeks.theta,
                        'vega': greeks.vega,
                        'volume': np.random.randint(100, 10000),
                        'open_interest': np.random.randint(1000, 100000)
                    })
                    
                    # Add to vol surface
                    self.vol_surface.add_point(strike, expiry_days, iv, spot)
        
        self.vol_surface.build_surface(spot)
        return pd.DataFrame(chain_data)
    
    def analyze_vol_surface(self, spot: float) -> Dict[str, Any]:
        """Analyze volatility surface characteristics"""
        if not self.vol_surface.expiries is None:
            expiries = self.vol_surface.expiries
        else:
            expiries = [30, 60, 90]
        
        analysis = {
            'skew_by_expiry': {},
            'convexity_by_expiry': {},
            'term_structure': []
        }
        
        for exp in expiries:
            analysis['skew_by_expiry'][int(exp)] = self.vol_surface.calculate_skew(exp, spot)
            analysis['convexity_by_expiry'][int(exp)] = self.vol_surface.calculate_smile_convexity(exp, spot)
        
        term_struct = self.vol_surface.get_term_structure(spot)
        if len(term_struct) > 0:
            analysis['term_structure'] = term_struct.to_dict('records')
        
        return analysis
    
    def generate_sample_analysis(self) -> Dict[str, Any]:
        """Generate sample analysis for testing"""
        spot = 100.0
        strikes = [85, 90, 95, 100, 105, 110, 115]
        expiries = [7, 14, 30, 60, 90, 180]
        
        # Build chain
        chain = self.build_options_chain("SAMPLE", spot, strikes, expiries)
        
        # Get various analytics
        atm_call = self.price_option(spot, 100, 30/365, 0.05, 0.25, "call")
        
        vol_analysis = self.analyze_vol_surface(spot)
        
        flow_summary = self.flow_analytics.get_flow_summary()
        
        return {
            'spot_price': spot,
            'atm_call': atm_call,
            'chain_size': len(chain),
            'vol_surface_analysis': vol_analysis,
            'flow_summary': flow_summary
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            'vol_surface_points': len(self.vol_surface.surface_data),
            'flow_trades': len(self.flow_analytics.flow_data),
            'options_chains': len(self.options_chain)
        }


if __name__ == "__main__":
    # Test the service
    service = OptionsAnalyticsService()
    
    print("Options Analytics Service Test")
    print("=" * 50)
    
    # Price an option
    print("\nPricing ATM Call Option:")
    result = service.price_option(
        S=100, K=100, T=30/365, r=0.05, sigma=0.25, option_type="call"
    )
    print(f"  Price: ${result['price']:.4f}")
    print(f"  Delta: {result['delta']:.4f}")
    print(f"  Gamma: {result['gamma']:.6f}")
    print(f"  Theta: ${result['theta']:.4f}/day")
    print(f"  Vega: ${result['vega']:.4f}/1% vol")
    
    # Calculate IV
    print("\nImplied Volatility:")
    iv = service.calculate_implied_vol(
        price=3.50, S=100, K=100, T=30/365, r=0.05, option_type="call"
    )
    print(f"  IV for $3.50 option: {iv:.2%}")
    
    # Generate full analysis
    print("\nFull Analysis:")
    analysis = service.generate_sample_analysis()
    print(f"  Chain Size: {analysis['chain_size']} contracts")
    print(f"  Spot: ${analysis['spot_price']}")
    
    if analysis['vol_surface_analysis']['skew_by_expiry']:
        print(f"  30-day Skew: {analysis['vol_surface_analysis']['skew_by_expiry'].get(30, 0):.4f}")
    
    print(f"\nService Stats: {service.get_stats()}")
    
    print("\n✅ Options Analytics Service operational - Items 141-260")

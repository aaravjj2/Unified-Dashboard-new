"""
Phase 7 — Options Risk Simulator: Greeks & Payoff Analysis Under Scenarios
===========================================================================

Simulates option positions under market scenarios using Black-Scholes model
with IV skew adjustments. Computes Greeks under stress conditions.

Features:
- Black-Scholes option pricing (calls and puts)
- Implied Volatility (IV) skew modeling
- Greeks calculation: Delta, Gamma, Vega, Theta, Rho
- Scenario-based option payoff analysis
- Batch processing for portfolio-wide option positions
- Stress testing of Greeks under extreme scenarios

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0 (Phase 7 - Offline Simulation Framework)
Date: October 29, 2025
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum
import logging
from scipy.stats import norm

# Import scenario and portfolio components
from scenario_engine import ScenarioDataset, ScenarioPath
from portfolio_simulator import Portfolio, PortfolioHolding

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMERATIONS & TYPE DEFINITIONS
# ============================================================================

class OptionType(Enum):
    """Option contract type"""
    CALL = "call"
    PUT = "put"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class OptionContract:
    """Single option contract specification"""
    ticker: str
    option_type: OptionType
    strike: float
    expiry_days: int  # Days to expiration
    contracts: int  # Number of contracts (1 contract = 100 shares)
    premium_paid: float  # Premium per share
    
    @property
    def notional_shares(self) -> int:
        """Total shares represented"""
        return self.contracts * 100
    
    @property
    def cost_basis(self) -> float:
        """Total cost of position"""
        return self.premium_paid * self.notional_shares


@dataclass
class Greeks:
    """Option Greeks (sensitivities)"""
    delta: float  # ∂V/∂S (price sensitivity)
    gamma: float  # ∂²V/∂S² (delta sensitivity)
    vega: float  # ∂V/∂σ (volatility sensitivity)
    theta: float  # ∂V/∂t (time decay)
    rho: float  # ∂V/∂r (interest rate sensitivity)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class OptionValuation:
    """Complete option valuation at a point in time"""
    ticker: str
    option_type: str
    strike: float
    spot_price: float
    time_to_expiry: float  # Years
    implied_volatility: float
    risk_free_rate: float
    
    # Valuation
    theoretical_value: float
    intrinsic_value: float
    time_value: float
    
    # Greeks
    greeks: Greeks
    
    # Scenario metadata
    scenario_day: int
    date: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "ticker": self.ticker,
            "option_type": self.option_type,
            "strike": self.strike,
            "spot_price": self.spot_price,
            "time_to_expiry": self.time_to_expiry,
            "implied_volatility": self.implied_volatility,
            "risk_free_rate": self.risk_free_rate,
            "theoretical_value": self.theoretical_value,
            "intrinsic_value": self.intrinsic_value,
            "time_value": self.time_value,
            "greeks": self.greeks.to_dict(),
            "scenario_day": self.scenario_day,
            "date": self.date
        }


@dataclass
class OptionSimulationResult:
    """Results from simulating option under scenario"""
    contract: OptionContract
    scenario_id: str
    
    # Initial state
    initial_spot: float
    initial_value: float
    initial_greeks: Greeks
    
    # Final state
    final_spot: float
    final_value: float
    final_greeks: Greeks
    
    # PnL
    total_pnl: float
    total_return_pct: float
    
    # Time series
    valuations: List[OptionValuation]
    dates: List[str]
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "scenario_id": self.scenario_id,
            "timestamp": self.timestamp,
            "contract": {
                "ticker": self.contract.ticker,
                "option_type": self.contract.option_type.value,
                "strike": self.contract.strike,
                "expiry_days": self.contract.expiry_days,
                "contracts": self.contract.contracts,
                "premium_paid": self.contract.premium_paid
            },
            "initial_spot": self.initial_spot,
            "initial_value": self.initial_value,
            "initial_greeks": self.initial_greeks.to_dict(),
            "final_spot": self.final_spot,
            "final_value": self.final_value,
            "final_greeks": self.final_greeks.to_dict(),
            "total_pnl": self.total_pnl,
            "total_return_pct": self.total_return_pct,
            "num_valuations": len(self.valuations),
            "dates": self.dates,
            "valuations": [v.to_dict() for v in self.valuations]
        }


# ============================================================================
# BLACK-SCHOLES MODEL
# ============================================================================

class BlackScholesModel:
    """
    Black-Scholes option pricing model.
    
    Standard formulas:
    - Call: C = S*N(d1) - K*exp(-r*T)*N(d2)
    - Put: P = K*exp(-r*T)*N(-d2) - S*N(-d1)
    
    where:
    - d1 = [ln(S/K) + (r + σ²/2)*T] / (σ*sqrt(T))
    - d2 = d1 - σ*sqrt(T)
    - N(x) = cumulative standard normal distribution
    """
    
    @staticmethod
    def _d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate d1 parameter"""
        if T <= 0 or sigma <= 0:
            return 0.0
        return (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    
    @staticmethod
    def _d2(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate d2 parameter"""
        if T <= 0 or sigma <= 0:
            return 0.0
        d1 = BlackScholesModel._d1(S, K, T, r, sigma)
        return d1 - sigma * np.sqrt(T)
    
    @staticmethod
    def price_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Price European call option.
        
        Args:
            S: Spot price
            K: Strike price
            T: Time to expiry (years)
            r: Risk-free rate
            sigma: Implied volatility
            
        Returns:
            Call option price
        """
        if T <= 0:
            return max(S - K, 0.0)  # Intrinsic value at expiry
        
        d1 = BlackScholesModel._d1(S, K, T, r, sigma)
        d2 = BlackScholesModel._d2(S, K, T, r, sigma)
        
        call_price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        return float(call_price)
    
    @staticmethod
    def price_put(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Price European put option.
        
        Args:
            S: Spot price
            K: Strike price
            T: Time to expiry (years)
            r: Risk-free rate
            sigma: Implied volatility
            
        Returns:
            Put option price
        """
        if T <= 0:
            return max(K - S, 0.0)  # Intrinsic value at expiry
        
        d1 = BlackScholesModel._d1(S, K, T, r, sigma)
        d2 = BlackScholesModel._d2(S, K, T, r, sigma)
        
        put_price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        return float(put_price)
    
    @staticmethod
    def calculate_greeks(
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        option_type: OptionType
    ) -> Greeks:
        """
        Calculate all Greeks.
        
        Returns:
            Greeks object with delta, gamma, vega, theta, rho
        """
        if T <= 0:
            # At expiry, most Greeks are zero
            if option_type == OptionType.CALL:
                delta = 1.0 if S > K else 0.0
            else:
                delta = -1.0 if S < K else 0.0
            
            return Greeks(
                delta=delta,
                gamma=0.0,
                vega=0.0,
                theta=0.0,
                rho=0.0
            )
        
        d1 = BlackScholesModel._d1(S, K, T, r, sigma)
        d2 = BlackScholesModel._d2(S, K, T, r, sigma)
        
        sqrt_T = np.sqrt(T)
        
        # Delta
        if option_type == OptionType.CALL:
            delta = norm.cdf(d1)
        else:
            delta = -norm.cdf(-d1)
        
        # Gamma (same for call and put)
        gamma = norm.pdf(d1) / (S * sigma * sqrt_T)
        
        # Vega (same for call and put, per 1% change in volatility)
        vega = S * norm.pdf(d1) * sqrt_T / 100.0
        
        # Theta (per day, not per year)
        if option_type == OptionType.CALL:
            theta = (
                -S * norm.pdf(d1) * sigma / (2 * sqrt_T)
                - r * K * np.exp(-r * T) * norm.cdf(d2)
            ) / 365.0
        else:
            theta = (
                -S * norm.pdf(d1) * sigma / (2 * sqrt_T)
                + r * K * np.exp(-r * T) * norm.cdf(-d2)
            ) / 365.0
        
        # Rho (per 1% change in interest rate)
        if option_type == OptionType.CALL:
            rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100.0
        else:
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100.0
        
        return Greeks(
            delta=float(delta),
            gamma=float(gamma),
            vega=float(vega),
            theta=float(theta),
            rho=float(rho)
        )


# ============================================================================
# IMPLIED VOLATILITY SKEW
# ============================================================================

class IVSkewModel:
    """
    Implied Volatility skew model.
    
    Models volatility smile/skew as function of moneyness (S/K).
    - OTM puts: Higher IV (downside protection demand)
    - ATM: Base IV
    - OTM calls: Slightly higher IV (upside speculation)
    """
    
    @staticmethod
    def get_skewed_iv(
        spot: float,
        strike: float,
        base_iv: float,
        option_type: OptionType,
        skew_steepness: float = 0.1
    ) -> float:
        """
        Calculate IV adjusted for skew.
        
        Args:
            spot: Current spot price
            strike: Strike price
            base_iv: At-the-money IV
            option_type: Call or put
            skew_steepness: Sensitivity to moneyness
            
        Returns:
            Adjusted IV
        """
        moneyness = spot / strike  # S/K ratio
        
        if option_type == OptionType.PUT:
            # Puts: Higher IV for lower strikes (moneyness < 1)
            if moneyness < 1.0:
                # OTM put (spot < strike)
                iv_adjustment = (1.0 - moneyness) * skew_steepness
            else:
                # ITM put (spot > strike)
                iv_adjustment = 0.0
        else:
            # Calls: Slight IV increase for higher strikes
            if moneyness > 1.0:
                # OTM call (spot < strike)
                iv_adjustment = (moneyness - 1.0) * skew_steepness * 0.5
            else:
                # ITM call (spot > strike)
                iv_adjustment = 0.0
        
        adjusted_iv = base_iv + iv_adjustment
        
        # Ensure IV stays positive and reasonable
        adjusted_iv = max(0.05, min(adjusted_iv, 2.0))
        
        return float(adjusted_iv)


# ============================================================================
# OPTIONS RISK SIMULATOR
# ============================================================================

class OptionsRiskSimulator:
    """
    Simulate option positions under market scenarios.
    """
    
    def __init__(
        self,
        contracts: List[OptionContract],
        base_iv: float = 0.25,  # 25% base IV
        risk_free_rate: float = 0.05,  # 5% risk-free rate
        iv_skew_steepness: float = 0.1
    ):
        self.contracts = contracts
        self.base_iv = base_iv
        self.risk_free_rate = risk_free_rate
        self.iv_skew_steepness = iv_skew_steepness
    
    def simulate_contract(
        self,
        contract: OptionContract,
        scenario: ScenarioDataset
    ) -> OptionSimulationResult:
        """
        Simulate single option contract under scenario.
        
        Args:
            contract: Option contract to simulate
            scenario: Scenario to apply
            
        Returns:
            OptionSimulationResult
        """
        logger.info(f"🎯 Simulating {contract.option_type.value} option: {contract.ticker} strike ${contract.strike}")
        
        # Find matching scenario path
        path = self._find_path(scenario.paths, contract.ticker)
        if path is None:
            raise ValueError(f"No scenario path found for ticker: {contract.ticker}")
        
        # Track valuations over time
        valuations = []
        
        initial_expiry_days = contract.expiry_days
        
        for day_idx, (date, spot_price) in enumerate(zip(path.dates, path.prices)):
            # Calculate time to expiry
            days_remaining = initial_expiry_days - day_idx
            time_to_expiry = max(days_remaining / 365.0, 0.0)
            
            # Get scenario volatility (if available) or use base
            scenario_vol = path.volatilities[day_idx] if day_idx < len(path.volatilities) else self.base_iv
            
            # Apply IV skew
            adjusted_iv = IVSkewModel.get_skewed_iv(
                spot_price,
                contract.strike,
                scenario_vol,
                contract.option_type,
                self.iv_skew_steepness
            )
            
            # Price option
            if contract.option_type == OptionType.CALL:
                theo_value = BlackScholesModel.price_call(
                    spot_price,
                    contract.strike,
                    time_to_expiry,
                    self.risk_free_rate,
                    adjusted_iv
                )
            else:
                theo_value = BlackScholesModel.price_put(
                    spot_price,
                    contract.strike,
                    time_to_expiry,
                    self.risk_free_rate,
                    adjusted_iv
                )
            
            # Calculate intrinsic and time value
            if contract.option_type == OptionType.CALL:
                intrinsic = max(spot_price - contract.strike, 0.0)
            else:
                intrinsic = max(contract.strike - spot_price, 0.0)
            
            time_value = theo_value - intrinsic
            
            # Calculate Greeks
            greeks = BlackScholesModel.calculate_greeks(
                spot_price,
                contract.strike,
                time_to_expiry,
                self.risk_free_rate,
                adjusted_iv,
                contract.option_type
            )
            
            valuation = OptionValuation(
                ticker=contract.ticker,
                option_type=contract.option_type.value,
                strike=contract.strike,
                spot_price=spot_price,
                time_to_expiry=time_to_expiry,
                implied_volatility=adjusted_iv,
                risk_free_rate=self.risk_free_rate,
                theoretical_value=theo_value,
                intrinsic_value=intrinsic,
                time_value=time_value,
                greeks=greeks,
                scenario_day=day_idx,
                date=date
            )
            valuations.append(valuation)
        
        # Summary statistics
        initial_val = valuations[0]
        final_val = valuations[-1]
        
        initial_position_value = initial_val.theoretical_value * contract.notional_shares
        final_position_value = final_val.theoretical_value * contract.notional_shares
        
        total_pnl = final_position_value - contract.cost_basis
        total_return = total_pnl / contract.cost_basis if contract.cost_basis > 0 else 0.0
        
        result = OptionSimulationResult(
            contract=contract,
            scenario_id=scenario.scenario_id,
            initial_spot=initial_val.spot_price,
            initial_value=initial_val.theoretical_value,
            initial_greeks=initial_val.greeks,
            final_spot=final_val.spot_price,
            final_value=final_val.theoretical_value,
            final_greeks=final_val.greeks,
            total_pnl=total_pnl,
            total_return_pct=total_return,
            valuations=valuations,
            dates=path.dates
        )
        
        logger.info(f"✅ Simulation complete: PnL = ${total_pnl:,.2f}, Return = {total_return:.2%}")
        return result
    
    def batch_simulate(
        self,
        scenarios: List[ScenarioDataset]
    ) -> List[OptionSimulationResult]:
        """
        Simulate all contracts across multiple scenarios.
        
        Args:
            scenarios: List of scenarios
            
        Returns:
            List of OptionSimulationResult
        """
        logger.info(f"🔄 Batch simulating {len(self.contracts)} contracts × {len(scenarios)} scenarios")
        
        results = []
        
        for scenario in scenarios:
            for contract in self.contracts:
                try:
                    result = self.simulate_contract(contract, scenario)
                    results.append(result)
                except Exception as e:
                    logger.error(f"❌ Failed to simulate {contract.ticker}: {e}")
        
        logger.info(f"✅ Batch simulation complete: {len(results)} results")
        return results
    
    def _find_path(self, paths: List[ScenarioPath], ticker: str) -> Optional[ScenarioPath]:
        """Find scenario path for ticker"""
        for path in paths:
            if path.ticker == ticker:
                return path
        return None
    
    def save_results(
        self,
        results: List[OptionSimulationResult],
        output_dir: str = "outputs/phase7_options"
    ) -> None:
        """Save option simulation results"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        for result in results:
            filename = f"{result.scenario_id}_{result.contract.ticker}_{result.contract.option_type.value}.json"
            filepath = Path(output_dir) / filename
            
            with open(filepath, 'w') as f:
                import json
                json.dump(result.to_dict(), f, indent=2)
            
            logger.info(f"💾 Saved option result: {filepath}")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_option_contract(
    ticker: str,
    option_type: str,
    strike: float,
    expiry_days: int,
    contracts: int = 1,
    premium_paid: float = 5.0
) -> OptionContract:
    """Quick function to create option contract"""
    return OptionContract(
        ticker=ticker,
        option_type=OptionType.CALL if option_type.lower() == "call" else OptionType.PUT,
        strike=strike,
        expiry_days=expiry_days,
        contracts=contracts,
        premium_paid=premium_paid
    )


# ============================================================================
# MAIN EXECUTION (FOR TESTING)
# ============================================================================

if __name__ == "__main__":
    from scenario_engine import create_monte_carlo_scenario, create_stress_scenario, StressType
    
    logger.info("=" * 80)
    logger.info("PHASE 7 — OPTIONS RISK SIMULATOR TEST")
    logger.info("=" * 80)
    
    # Test 1: Call option under Monte Carlo
    logger.info("\n📊 Test 1: Call Option - Monte Carlo Scenario")
    
    call_contract = create_option_contract(
        ticker="SPY",
        option_type="call",
        strike=460.0,  # Slightly OTM
        expiry_days=60,  # 60 days to expiration
        contracts=10,
        premium_paid=8.50
    )
    
    mc_scenario = create_monte_carlo_scenario(
        tickers=["SPY"],
        num_simulations=1000,
        num_days=60,
        random_seed=42
    )
    
    simulator = OptionsRiskSimulator(
        contracts=[call_contract],
        base_iv=0.20,
        risk_free_rate=0.05
    )
    
    call_result = simulator.simulate_contract(call_contract, mc_scenario)
    
    logger.info(f"   Initial Spot: ${call_result.initial_spot:.2f}")
    logger.info(f"   Final Spot: ${call_result.final_spot:.2f}")
    logger.info(f"   Initial Option Value: ${call_result.initial_value:.2f}")
    logger.info(f"   Final Option Value: ${call_result.final_value:.2f}")
    logger.info(f"   Total PnL: ${call_result.total_pnl:,.2f}")
    logger.info(f"   Return: {call_result.total_return_pct:.2%}")
    logger.info(f"   Initial Delta: {call_result.initial_greeks.delta:.3f}")
    logger.info(f"   Final Delta: {call_result.final_greeks.delta:.3f}")
    logger.info(f"   Final Theta: ${call_result.final_greeks.theta:.2f}/day")
    
    # Test 2: Put option under volatility spike
    logger.info("\n📈 Test 2: Put Option - Volatility Spike")
    
    put_contract = create_option_contract(
        ticker="SPY",
        option_type="put",
        strike=440.0,  # Slightly OTM protective put
        expiry_days=60,
        contracts=5,
        premium_paid=6.00
    )
    
    vol_scenario = create_stress_scenario(
        tickers=["SPY"],
        stress_type=StressType.VOLATILITY_SPIKE,
        stress_magnitude=2.5,
        num_days=60,
        random_seed=42
    )
    
    put_simulator = OptionsRiskSimulator(
        contracts=[put_contract],
        base_iv=0.20,
        risk_free_rate=0.05
    )
    
    put_result = put_simulator.simulate_contract(put_contract, vol_scenario)
    
    logger.info(f"   Total PnL: ${put_result.total_pnl:,.2f}")
    logger.info(f"   Return: {put_result.total_return_pct:.2%}")
    logger.info(f"   Final Vega: ${put_result.final_greeks.vega:.2f} per 1% IV")
    logger.info(f"   Final Gamma: {put_result.final_greeks.gamma:.3f}")
    
    # Test 3: Multiple options under Black Swan
    logger.info("\n🦢 Test 3: Option Portfolio - Black Swan Event")
    
    option_portfolio = [
        create_option_contract("SPY", "call", 460.0, 90, 10, 10.0),
        create_option_contract("SPY", "put", 440.0, 90, 10, 8.0),
        create_option_contract("QQQ", "call", 390.0, 90, 5, 12.0)
    ]
    
    swan_scenario = create_stress_scenario(
        tickers=["SPY", "QQQ"],
        stress_type=StressType.BLACK_SWAN,
        num_days=90,
        random_seed=42
    )
    
    portfolio_simulator = OptionsRiskSimulator(
        contracts=option_portfolio,
        base_iv=0.22,
        risk_free_rate=0.05
    )
    
    batch_results = portfolio_simulator.batch_simulate([swan_scenario])
    
    total_pnl = sum(r.total_pnl for r in batch_results)
    logger.info(f"   Portfolio Total PnL: ${total_pnl:,.2f}")
    
    # Save results
    logger.info("\n💾 Saving results")
    simulator.save_results([call_result, put_result] + batch_results)
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ ALL OPTIONS RISK SIMULATOR TESTS COMPLETE")
    logger.info("=" * 80)

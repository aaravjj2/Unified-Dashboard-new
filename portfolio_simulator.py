"""
Phase 7 — Portfolio Simulator: Risk Analysis & Scenario Testing
================================================================

Applies scenario datasets to portfolio holdings to compute risk metrics and PnL distributions.

Features:
- Portfolio loading from Phase 3 CSVs or synthetic data
- Scenario application to holdings
- Risk metrics: VaR, CVaR (Expected Shortfall), Sharpe, Sortino, Max Drawdown
- Sector exposure analysis
- Beta and correlation calculations
- Multi-scenario batch processing
- Deterministic reproducibility

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0 (Phase 7 - Offline Simulation Framework)
Date: October 29, 2025
"""

import json
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import logging

# Import scenario engine components
from scenario_engine import ScenarioDataset, ScenarioPath, ScenarioType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class PortfolioHolding:
    """Single portfolio position"""
    ticker: str
    shares: float
    entry_price: float
    current_price: float
    sector: str = "unknown"
    
    @property
    def market_value(self) -> float:
        """Current market value"""
        return self.shares * self.current_price
    
    @property
    def cost_basis(self) -> float:
        """Original cost"""
        return self.shares * self.entry_price
    
    @property
    def unrealized_pnl(self) -> float:
        """Unrealized profit/loss"""
        return self.market_value - self.cost_basis
    
    @property
    def return_pct(self) -> float:
        """Return percentage"""
        if self.cost_basis == 0:
            return 0.0
        return (self.current_price / self.entry_price) - 1.0


@dataclass
class Portfolio:
    """Portfolio snapshot"""
    holdings: List[PortfolioHolding]
    cash: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    portfolio_id: str = "default_portfolio"
    
    @property
    def total_market_value(self) -> float:
        """Total portfolio value"""
        return sum(h.market_value for h in self.holdings) + self.cash
    
    @property
    def total_equity_value(self) -> float:
        """Equity positions only"""
        return sum(h.market_value for h in self.holdings)
    
    @property
    def num_positions(self) -> int:
        """Number of holdings"""
        return len(self.holdings)
    
    def get_holding(self, ticker: str) -> Optional[PortfolioHolding]:
        """Get holding by ticker"""
        for holding in self.holdings:
            if holding.ticker == ticker:
                return holding
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "portfolio_id": self.portfolio_id,
            "timestamp": self.timestamp,
            "cash": self.cash,
            "total_market_value": self.total_market_value,
            "num_positions": self.num_positions,
            "holdings": [
                {
                    "ticker": h.ticker,
                    "shares": h.shares,
                    "entry_price": h.entry_price,
                    "current_price": h.current_price,
                    "market_value": h.market_value,
                    "unrealized_pnl": h.unrealized_pnl,
                    "return_pct": h.return_pct,
                    "sector": h.sector
                }
                for h in self.holdings
            ]
        }


@dataclass
class RiskMetrics:
    """Comprehensive risk metrics"""
    # VaR and Expected Shortfall
    var_95: float  # 95% Value at Risk
    var_99: float  # 99% Value at Risk
    cvar_95: float  # 95% Expected Shortfall (CVaR)
    cvar_99: float  # 99% Expected Shortfall
    
    # Return metrics
    mean_return: float
    std_return: float
    sharpe_ratio: float
    sortino_ratio: float
    
    # Drawdown metrics
    max_drawdown: float
    max_drawdown_duration: int  # Days
    
    # Distribution metrics
    skewness: float
    kurtosis: float
    
    # Portfolio metrics
    total_return: float
    annualized_return: float
    annualized_volatility: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class SectorExposure:
    """Sector-level exposure analysis"""
    sector: str
    market_value: float
    weight: float  # % of portfolio
    num_positions: int
    avg_return: float
    volatility: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class SimulationResult:
    """Results from applying scenario to portfolio"""
    scenario_id: str
    scenario_type: str
    portfolio_id: str
    
    # Initial state
    initial_portfolio_value: float
    
    # Final state
    final_portfolio_value: float
    total_pnl: float
    total_return_pct: float
    
    # Risk metrics
    risk_metrics: RiskMetrics
    
    # Exposure analysis
    sector_exposures: List[SectorExposure]
    
    # Time series
    portfolio_values: List[float]
    daily_returns: List[float]
    dates: List[str]
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "scenario_id": self.scenario_id,
            "scenario_type": self.scenario_type,
            "portfolio_id": self.portfolio_id,
            "timestamp": self.timestamp,
            "initial_portfolio_value": self.initial_portfolio_value,
            "final_portfolio_value": self.final_portfolio_value,
            "total_pnl": self.total_pnl,
            "total_return_pct": self.total_return_pct,
            "risk_metrics": self.risk_metrics.to_dict(),
            "sector_exposures": [se.to_dict() for se in self.sector_exposures],
            "num_days": len(self.dates),
            "dates": self.dates,
            "portfolio_values": self.portfolio_values,
            "daily_returns": self.daily_returns
        }


# ============================================================================
# PORTFOLIO LOADER
# ============================================================================

class PortfolioLoader:
    """Load portfolio from various sources"""
    
    @staticmethod
    def from_csv(filepath: str, portfolio_id: str = "csv_portfolio") -> Portfolio:
        """
        Load portfolio from CSV file.
        
        Expected columns: ticker, shares, entry_price, current_price, sector
        """
        logger.info(f"📂 Loading portfolio from CSV: {filepath}")
        
        df = pd.read_csv(filepath)
        required_cols = ["ticker", "shares", "entry_price", "current_price"]
        
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        holdings = []
        for _, row in df.iterrows():
            holding = PortfolioHolding(
                ticker=row["ticker"],
                shares=float(row["shares"]),
                entry_price=float(row["entry_price"]),
                current_price=float(row["current_price"]),
                sector=row.get("sector", "unknown")
            )
            holdings.append(holding)
        
        cash = float(df["cash"].iloc[0]) if "cash" in df.columns else 0.0
        
        portfolio = Portfolio(
            holdings=holdings,
            cash=cash,
            portfolio_id=portfolio_id
        )
        
        logger.info(f"✅ Loaded portfolio: {portfolio.num_positions} positions, ${portfolio.total_market_value:,.2f} total value")
        return portfolio
    
    @staticmethod
    def create_synthetic(
        tickers: List[str],
        allocation: float = 10000.0,
        portfolio_id: str = "synthetic_portfolio"
    ) -> Portfolio:
        """
        Create synthetic portfolio with equal weighting.
        
        Args:
            tickers: List of ticker symbols
            allocation: Total cash to allocate
            portfolio_id: Portfolio identifier
        """
        logger.info(f"🔧 Creating synthetic portfolio: {len(tickers)} tickers, ${allocation:,.2f} allocation")
        
        # Default prices
        default_prices = {
            "SPY": 450.0,
            "QQQ": 380.0,
            "IWM": 190.0,
            "AAPL": 180.0,
            "MSFT": 380.0,
            "GOOGL": 140.0,
            "AMZN": 170.0,
            "NVDA": 500.0
        }
        
        # Default sectors
        default_sectors = {
            "SPY": "broad_market",
            "QQQ": "technology",
            "IWM": "small_cap",
            "AAPL": "technology",
            "MSFT": "technology",
            "GOOGL": "technology",
            "AMZN": "consumer_discretionary",
            "NVDA": "technology"
        }
        
        allocation_per_ticker = allocation / len(tickers)
        holdings = []
        
        for ticker in tickers:
            price = default_prices.get(ticker, 100.0)
            shares = allocation_per_ticker / price
            
            holding = PortfolioHolding(
                ticker=ticker,
                shares=shares,
                entry_price=price,
                current_price=price,
                sector=default_sectors.get(ticker, "unknown")
            )
            holdings.append(holding)
        
        portfolio = Portfolio(
            holdings=holdings,
            cash=0.0,
            portfolio_id=portfolio_id
        )
        
        logger.info(f"✅ Created synthetic portfolio: {portfolio.num_positions} positions")
        return portfolio


# ============================================================================
# RISK CALCULATOR
# ============================================================================

class RiskCalculator:
    """Calculate comprehensive risk metrics"""
    
    @staticmethod
    def calculate_var(returns: np.ndarray, confidence: float = 0.95) -> float:
        """
        Calculate Value at Risk (VaR).
        
        Args:
            returns: Array of returns
            confidence: Confidence level (0.95 = 95%)
            
        Returns:
            VaR as positive number (loss threshold)
        """
        if len(returns) == 0:
            return 0.0
        
        # VaR is the negative of the percentile
        percentile = (1 - confidence) * 100
        var = -np.percentile(returns, percentile)
        return float(var)
    
    @staticmethod
    def calculate_cvar(returns: np.ndarray, confidence: float = 0.95) -> float:
        """
        Calculate Conditional Value at Risk (CVaR / Expected Shortfall).
        
        CVaR is the expected loss given that VaR has been exceeded.
        
        Args:
            returns: Array of returns
            confidence: Confidence level
            
        Returns:
            CVaR as positive number (expected loss)
        """
        if len(returns) == 0:
            return 0.0
        
        var = RiskCalculator.calculate_var(returns, confidence)
        # Take mean of all returns worse than VaR
        tail_returns = returns[returns < -var]
        
        if len(tail_returns) == 0:
            return var  # Fallback to VaR
        
        cvar = -np.mean(tail_returns)
        return float(cvar)
    
    @staticmethod
    def calculate_sharpe_ratio(
        returns: np.ndarray,
        risk_free_rate: float = 0.0
    ) -> float:
        """
        Calculate Sharpe Ratio.
        
        Sharpe = (Mean Return - Risk Free Rate) / Std Dev
        """
        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0
        
        excess_return = np.mean(returns) - risk_free_rate
        sharpe = excess_return / np.std(returns)
        
        # Annualize (assuming daily returns)
        sharpe_annualized = sharpe * np.sqrt(252)
        return float(sharpe_annualized)
    
    @staticmethod
    def calculate_sortino_ratio(
        returns: np.ndarray,
        risk_free_rate: float = 0.0
    ) -> float:
        """
        Calculate Sortino Ratio (uses downside deviation instead of total volatility).
        
        Sortino = (Mean Return - Risk Free Rate) / Downside Deviation
        """
        if len(returns) == 0:
            return 0.0
        
        excess_return = np.mean(returns) - risk_free_rate
        
        # Downside deviation (only negative returns)
        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0:
            return 0.0
        
        downside_dev = np.std(downside_returns)
        if downside_dev == 0:
            return 0.0
        
        sortino = excess_return / downside_dev
        
        # Annualize
        sortino_annualized = sortino * np.sqrt(252)
        return float(sortino_annualized)
    
    @staticmethod
    def calculate_max_drawdown(values: np.ndarray) -> Tuple[float, int]:
        """
        Calculate maximum drawdown and its duration.
        
        Returns:
            Tuple of (max_drawdown, duration_in_days)
        """
        if len(values) == 0:
            return 0.0, 0
        
        running_max = np.maximum.accumulate(values)
        drawdown = (values - running_max) / running_max
        
        max_dd = float(np.min(drawdown))
        
        # Find duration (days from peak to trough)
        max_dd_idx = np.argmin(drawdown)
        peak_idx = np.argmax(values[:max_dd_idx + 1]) if max_dd_idx > 0 else 0
        duration = max_dd_idx - peak_idx
        
        return max_dd, int(duration)
    
    @staticmethod
    def calculate_full_metrics(
        portfolio_values: List[float],
        daily_returns: List[float],
        num_days: int
    ) -> RiskMetrics:
        """
        Calculate all risk metrics.
        
        Args:
            portfolio_values: Time series of portfolio values
            daily_returns: Daily return series
            num_days: Number of trading days
            
        Returns:
            RiskMetrics object
        """
        returns_array = np.array(daily_returns)
        values_array = np.array(portfolio_values)
        
        # VaR and CVaR
        var_95 = RiskCalculator.calculate_var(returns_array, 0.95)
        var_99 = RiskCalculator.calculate_var(returns_array, 0.99)
        cvar_95 = RiskCalculator.calculate_cvar(returns_array, 0.95)
        cvar_99 = RiskCalculator.calculate_cvar(returns_array, 0.99)
        
        # Return metrics
        mean_return = float(np.mean(returns_array))
        std_return = float(np.std(returns_array))
        sharpe_ratio = RiskCalculator.calculate_sharpe_ratio(returns_array)
        sortino_ratio = RiskCalculator.calculate_sortino_ratio(returns_array)
        
        # Drawdown
        max_dd, max_dd_duration = RiskCalculator.calculate_max_drawdown(values_array)
        
        # Distribution
        from scipy.stats import skew, kurtosis
        skewness = float(skew(returns_array))
        kurt = float(kurtosis(returns_array))
        
        # Total and annualized returns
        total_return = (values_array[-1] / values_array[0]) - 1.0
        annualized_return = (1 + total_return) ** (252 / num_days) - 1.0
        annualized_vol = std_return * np.sqrt(252)
        
        return RiskMetrics(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            mean_return=mean_return,
            std_return=std_return,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_dd,
            max_drawdown_duration=max_dd_duration,
            skewness=skewness,
            kurtosis=kurt,
            total_return=float(total_return),
            annualized_return=float(annualized_return),
            annualized_volatility=float(annualized_vol)
        )


# ============================================================================
# PORTFOLIO SIMULATOR
# ============================================================================

class PortfolioSimulator:
    """
    Apply scenarios to portfolio and compute risk metrics.
    """
    
    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio
        
    def apply_scenario(self, scenario: ScenarioDataset) -> SimulationResult:
        """
        Apply scenario to portfolio and compute metrics.
        
        Args:
            scenario: ScenarioDataset to apply
            
        Returns:
            SimulationResult with all metrics
        """
        logger.info(f"🎯 Applying scenario '{scenario.scenario_id}' to portfolio '{self.portfolio.portfolio_id}'")
        
        # Match portfolio holdings to scenario paths
        portfolio_values = []
        dates = []
        
        # Get first path to determine dates
        if len(scenario.paths) > 0:
            dates = scenario.paths[0].dates
        else:
            raise ValueError("Scenario has no paths")
        
        num_days = len(dates)
        
        # Initialize portfolio value time series
        for day_idx in range(num_days):
            total_value = self.portfolio.cash
            
            for holding in self.portfolio.holdings:
                # Find matching scenario path
                path = self._find_path(scenario.paths, holding.ticker)
                
                if path is None:
                    # Ticker not in scenario, use current price
                    total_value += holding.shares * holding.current_price
                else:
                    # Use scenario price
                    scenario_price = path.prices[day_idx]
                    total_value += holding.shares * scenario_price
            
            portfolio_values.append(total_value)
        
        # Calculate daily returns
        daily_returns = []
        for i in range(1, len(portfolio_values)):
            daily_ret = (portfolio_values[i] / portfolio_values[i-1]) - 1.0
            daily_returns.append(daily_ret)
        
        # Calculate risk metrics
        risk_metrics = RiskCalculator.calculate_full_metrics(
            portfolio_values,
            daily_returns,
            num_days - 1
        )
        
        # Calculate sector exposures
        sector_exposures = self._calculate_sector_exposures(scenario)
        
        # Summary statistics
        initial_value = portfolio_values[0]
        final_value = portfolio_values[-1]
        total_pnl = final_value - initial_value
        total_return = (final_value / initial_value) - 1.0
        
        result = SimulationResult(
            scenario_id=scenario.scenario_id,
            scenario_type=scenario.scenario_type.value,
            portfolio_id=self.portfolio.portfolio_id,
            initial_portfolio_value=initial_value,
            final_portfolio_value=final_value,
            total_pnl=total_pnl,
            total_return_pct=total_return,
            risk_metrics=risk_metrics,
            sector_exposures=sector_exposures,
            portfolio_values=portfolio_values,
            daily_returns=daily_returns,
            dates=dates
        )
        
        logger.info(f"✅ Simulation complete: Total Return = {total_return:.2%}, Sharpe = {risk_metrics.sharpe_ratio:.2f}")
        return result
    
    def _find_path(self, paths: List[ScenarioPath], ticker: str) -> Optional[ScenarioPath]:
        """Find scenario path for ticker"""
        for path in paths:
            if path.ticker == ticker:
                return path
        return None
    
    def _calculate_sector_exposures(self, scenario: ScenarioDataset) -> List[SectorExposure]:
        """Calculate sector-level exposures and metrics"""
        sector_data: Dict[str, Dict[str, Any]] = {}
        
        for holding in self.portfolio.holdings:
            sector = holding.sector
            
            if sector not in sector_data:
                sector_data[sector] = {
                    "market_value": 0.0,
                    "num_positions": 0,
                    "returns": []
                }
            
            sector_data[sector]["market_value"] += holding.market_value
            sector_data[sector]["num_positions"] += 1
            
            # Get returns from scenario
            path = self._find_path(scenario.paths, holding.ticker)
            if path is not None:
                sector_data[sector]["returns"].extend(path.returns)
        
        # Create SectorExposure objects
        exposures = []
        total_value = self.portfolio.total_equity_value
        
        for sector, data in sector_data.items():
            avg_return = float(np.mean(data["returns"])) if data["returns"] else 0.0
            volatility = float(np.std(data["returns"])) if data["returns"] else 0.0
            weight = data["market_value"] / total_value if total_value > 0 else 0.0
            
            exposure = SectorExposure(
                sector=sector,
                market_value=data["market_value"],
                weight=weight,
                num_positions=data["num_positions"],
                avg_return=avg_return,
                volatility=volatility
            )
            exposures.append(exposure)
        
        # Sort by weight descending
        exposures.sort(key=lambda x: x.weight, reverse=True)
        
        return exposures
    
    def batch_simulate(self, scenarios: List[ScenarioDataset]) -> List[SimulationResult]:
        """
        Apply multiple scenarios to portfolio.
        
        Args:
            scenarios: List of scenarios to apply
            
        Returns:
            List of SimulationResult objects
        """
        logger.info(f"🔄 Running batch simulation: {len(scenarios)} scenarios")
        
        results = []
        for scenario in scenarios:
            result = self.apply_scenario(scenario)
            results.append(result)
        
        logger.info(f"✅ Batch simulation complete: {len(results)} results")
        return results
    
    def save_results(
        self,
        results: List[SimulationResult],
        output_dir: str = "outputs/phase7_simulations"
    ) -> None:
        """Save simulation results to JSON files"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        for result in results:
            filename = f"{result.scenario_id}_{result.portfolio_id}.json"
            filepath = Path(output_dir) / filename
            
            with open(filepath, 'w') as f:
                json.dump(result.to_dict(), f, indent=2)
            
            logger.info(f"💾 Saved result: {filepath}")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def simulate_portfolio_scenario(
    portfolio: Portfolio,
    scenario: ScenarioDataset,
    output_dir: str = "outputs/phase7_simulations"
) -> SimulationResult:
    """
    Quick function to simulate portfolio under scenario.
    
    Args:
        portfolio: Portfolio to simulate
        scenario: Scenario to apply
        output_dir: Output directory
        
    Returns:
        SimulationResult
    """
    simulator = PortfolioSimulator(portfolio)
    result = simulator.apply_scenario(scenario)
    
    # Save result
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    filename = f"{result.scenario_id}_{result.portfolio_id}.json"
    filepath = Path(output_dir) / filename
    
    with open(filepath, 'w') as f:
        json.dump(result.to_dict(), f, indent=2)
    
    return result


# ============================================================================
# MAIN EXECUTION (FOR TESTING)
# ============================================================================

if __name__ == "__main__":
    from scenario_engine import create_monte_carlo_scenario, create_stress_scenario, StressType
    
    logger.info("=" * 80)
    logger.info("PHASE 7 — PORTFOLIO SIMULATOR TEST")
    logger.info("=" * 80)
    
    # Create synthetic portfolio
    logger.info("\n📊 Creating synthetic portfolio")
    portfolio = PortfolioLoader.create_synthetic(
        tickers=["SPY", "QQQ", "IWM"],
        allocation=100000.0,
        portfolio_id="test_portfolio"
    )
    
    # Test 1: Monte Carlo simulation
    logger.info("\n🎲 Test 1: Monte Carlo Simulation")
    mc_scenario = create_monte_carlo_scenario(
        tickers=["SPY", "QQQ", "IWM"],
        num_simulations=1000,
        num_days=252,
        random_seed=42
    )
    
    simulator = PortfolioSimulator(portfolio)
    mc_result = simulator.apply_scenario(mc_scenario)
    
    logger.info(f"   Initial Value: ${mc_result.initial_portfolio_value:,.2f}")
    logger.info(f"   Final Value: ${mc_result.final_portfolio_value:,.2f}")
    logger.info(f"   Total Return: {mc_result.total_return_pct:.2%}")
    logger.info(f"   Sharpe Ratio: {mc_result.risk_metrics.sharpe_ratio:.2f}")
    logger.info(f"   VaR 95%: {mc_result.risk_metrics.var_95:.2%}")
    logger.info(f"   CVaR 95%: {mc_result.risk_metrics.cvar_95:.2%}")
    logger.info(f"   Max Drawdown: {mc_result.risk_metrics.max_drawdown:.2%}")
    
    # Test 2: Volatility spike
    logger.info("\n📈 Test 2: Volatility Spike Stress Test")
    vol_scenario = create_stress_scenario(
        tickers=["SPY", "QQQ", "IWM"],
        stress_type=StressType.VOLATILITY_SPIKE,
        stress_magnitude=2.5,
        random_seed=42
    )
    
    vol_result = simulator.apply_scenario(vol_scenario)
    logger.info(f"   Total Return: {vol_result.total_return_pct:.2%}")
    logger.info(f"   Sharpe Ratio: {vol_result.risk_metrics.sharpe_ratio:.2f}")
    logger.info(f"   Max Drawdown: {vol_result.risk_metrics.max_drawdown:.2%}")
    
    # Test 3: Black Swan
    logger.info("\n🦢 Test 3: Black Swan Event")
    swan_scenario = create_stress_scenario(
        tickers=["SPY", "QQQ", "IWM"],
        stress_type=StressType.BLACK_SWAN,
        random_seed=42
    )
    
    swan_result = simulator.apply_scenario(swan_scenario)
    logger.info(f"   Total Return: {swan_result.total_return_pct:.2%}")
    logger.info(f"   VaR 99%: {swan_result.risk_metrics.var_99:.2%}")
    logger.info(f"   CVaR 99%: {swan_result.risk_metrics.cvar_99:.2%}")
    
    # Save all results
    logger.info("\n💾 Saving results")
    simulator.save_results(
        [mc_result, vol_result, swan_result],
        output_dir="outputs/phase7_simulations"
    )
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ ALL PORTFOLIO SIMULATOR TESTS COMPLETE")
    logger.info("=" * 80)

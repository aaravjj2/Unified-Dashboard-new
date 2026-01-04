"""
Tests for src.risk.aggregator - Portfolio Risk Aggregation

Tests cover:
- Position risk calculation
- Portfolio Greeks aggregation
- Underlying-level aggregation
- Dollar Greeks calculation
- Stress testing
- Scenario analysis
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest
import numpy as np

from src.risk.aggregator import (
    RiskAggregator,
    PositionRisk,
    UnderlyingRisk,
    PortfolioGreeks,
    AggregationLevel,
)


class TestPositionRisk:
    """Test PositionRisk dataclass."""
    
    def test_position_risk_creation(self):
        """Test creating position risk."""
        risk = PositionRisk(
            position_id="POS-001",
            symbol="AAPL240119C00150000",
            underlying="AAPL",
            quantity=10,
            delta=5.5,
            gamma=0.24,
            theta=-3.5,
            vega=3.0,
            rho=0.15,
            market_value=4200.0,
            delta_dollars=825.0,  # 5.5 * 150
            gamma_dollars=36.0,
            vega_dollars=300.0,
        )
        
        assert risk.position_id == "POS-001"
        assert risk.delta == 5.5
        assert risk.delta_dollars == 825.0
    
    def test_position_risk_net_exposure(self):
        """Test net exposure calculation."""
        risk = PositionRisk(
            position_id="POS-001",
            symbol="AAPL240119C00150000",
            underlying="AAPL",
            quantity=10,
            delta=5.5,
            gamma=0.24,
            theta=-3.5,
            vega=3.0,
            market_value=4200.0,
            delta_dollars=825.0,
        )
        
        assert risk.market_value == 4200.0


class TestUnderlyingRisk:
    """Test UnderlyingRisk dataclass."""
    
    def test_underlying_risk_creation(self):
        """Test creating underlying risk."""
        risk = UnderlyingRisk(
            underlying="AAPL",
            spot_price=150.0,
            net_delta=7.0,
            net_gamma=0.34,
            net_theta=-2.3,
            net_vega=4.5,
            delta_dollars=1050.0,
            gamma_dollars=51.0,
            vega_dollars=450.0,
            position_count=3,
            total_exposure=8000.0,
        )
        
        assert risk.underlying == "AAPL"
        assert risk.net_delta == 7.0
        assert risk.position_count == 3


class TestPortfolioGreeks:
    """Test PortfolioGreeks dataclass."""
    
    def test_portfolio_greeks_creation(self):
        """Test creating portfolio Greeks."""
        greeks = PortfolioGreeks(
            total_delta=15.5,
            total_gamma=0.58,
            total_theta=-8.2,
            total_vega=9.5,
            total_rho=0.35,
            delta_dollars=2325.0,
            gamma_dollars=87.0,
            vega_dollars=950.0,
            beta_weighted_delta=12.0,
            net_exposure=25000.0,
            gross_exposure=35000.0,
        )
        
        assert greeks.total_delta == 15.5
        assert greeks.net_exposure == 25000.0


class TestRiskAggregator:
    """Test RiskAggregator class."""
    
    @pytest.fixture
    def sample_positions(self) -> List[Dict]:
        """Sample positions for testing."""
        return [
            {
                "position_id": "POS-001",
                "symbol": "AAPL240119C00150000",
                "underlying": "AAPL",
                "quantity": 10,
                "side": "long",
                "delta": 5.5,
                "gamma": 0.24,
                "theta": -3.5,
                "vega": 3.0,
                "rho": 0.15,
                "market_value": 4200.0,
            },
            {
                "position_id": "POS-002",
                "symbol": "AAPL240119P00145000",
                "underlying": "AAPL",
                "quantity": -5,
                "side": "short",
                "delta": 1.5,  # Short put
                "gamma": 0.10,
                "theta": 1.2,  # Collecting theta
                "vega": -1.0,
                "rho": -0.08,
                "market_value": -1200.0,
            },
            {
                "position_id": "POS-003",
                "symbol": "MSFT240119C00400000",
                "underlying": "MSFT",
                "quantity": 5,
                "side": "long",
                "delta": 2.75,
                "gamma": 0.08,
                "theta": -2.0,
                "vega": 1.5,
                "rho": 0.10,
                "market_value": 3000.0,
            },
        ]
    
    @pytest.fixture
    def spot_prices(self) -> Dict[str, float]:
        """Sample spot prices."""
        return {
            "AAPL": 150.0,
            "MSFT": 400.0,
        }
    
    @pytest.fixture
    def aggregator(self, sample_positions, spot_prices):
        """Create aggregator instance."""
        return RiskAggregator(positions=sample_positions, spot_prices=spot_prices)
    
    def test_aggregator_creation(self, aggregator):
        """Test aggregator creation."""
        assert aggregator is not None
    
    def test_aggregate_by_underlying(self, aggregator):
        """Test aggregation by underlying."""
        by_underlying = aggregator.aggregate_by_underlying()
        
        assert "AAPL" in by_underlying
        assert "MSFT" in by_underlying
        
        # AAPL should have 2 positions
        assert by_underlying["AAPL"].position_count == 2
        
        # Net delta for AAPL = 5.5 + 1.5 = 7.0
        assert abs(by_underlying["AAPL"].net_delta - 7.0) < 0.01
    
    def test_aggregate_portfolio(self, aggregator):
        """Test portfolio-level aggregation."""
        portfolio = aggregator.aggregate_portfolio()
        
        # Total delta = 5.5 + 1.5 + 2.75 = 9.75
        assert abs(portfolio.total_delta - 9.75) < 0.01
        
        # Total gamma = 0.24 + 0.10 + 0.08 = 0.42
        assert abs(portfolio.total_gamma - 0.42) < 0.01
        
        # Total theta = -3.5 + 1.2 + (-2.0) = -4.3
        assert abs(portfolio.total_theta - (-4.3)) < 0.01
    
    def test_calculate_dollar_greeks(self, aggregator):
        """Test dollar Greeks calculation."""
        by_underlying = aggregator.aggregate_by_underlying()
        
        # AAPL delta dollars = 7.0 * 150 = 1050
        assert abs(by_underlying["AAPL"].delta_dollars - 1050.0) < 1.0
    
    def test_calculate_position_risks(self, aggregator):
        """Test individual position risk calculation."""
        position_risks = aggregator.calculate_position_risks()
        
        assert len(position_risks) == 3
        
        # Find POS-001
        pos1 = next(p for p in position_risks if p.position_id == "POS-001")
        assert pos1.delta == 5.5
    
    def test_empty_portfolio(self):
        """Test aggregation with empty portfolio."""
        aggregator = RiskAggregator(positions=[], spot_prices={})
        
        portfolio = aggregator.aggregate_portfolio()
        
        assert portfolio.total_delta == 0.0
        assert portfolio.total_gamma == 0.0
    
    def test_single_position(self):
        """Test aggregation with single position."""
        positions = [{
            "position_id": "POS-001",
            "symbol": "AAPL240119C00150000",
            "underlying": "AAPL",
            "quantity": 10,
            "delta": 5.5,
            "gamma": 0.24,
            "theta": -3.5,
            "vega": 3.0,
            "market_value": 4200.0,
        }]
        
        aggregator = RiskAggregator(
            positions=positions,
            spot_prices={"AAPL": 150.0},
        )
        
        portfolio = aggregator.aggregate_portfolio()
        
        assert portfolio.total_delta == 5.5
        assert portfolio.total_gamma == 0.24


class TestStressTesting:
    """Test stress testing functionality."""
    
    @pytest.fixture
    def aggregator(self):
        """Create aggregator with positions."""
        positions = [
            {
                "position_id": "POS-001",
                "symbol": "AAPL240119C00150000",
                "underlying": "AAPL",
                "quantity": 10,
                "delta": 5.5,
                "gamma": 0.24,
                "theta": -3.5,
                "vega": 3.0,
                "market_value": 4200.0,
            },
        ]
        return RiskAggregator(
            positions=positions,
            spot_prices={"AAPL": 150.0},
        )
    
    def test_stress_test_spot_up(self, aggregator):
        """Test stress test with spot move up."""
        result = aggregator.stress_test(
            underlying="AAPL",
            spot_shock_pct=0.10,  # +10%
            vol_shock_pct=0.0,
        )
        
        assert "pnl" in result
        assert "new_delta" in result
    
    def test_stress_test_spot_down(self, aggregator):
        """Test stress test with spot move down."""
        result = aggregator.stress_test(
            underlying="AAPL",
            spot_shock_pct=-0.10,  # -10%
            vol_shock_pct=0.0,
        )
        
        assert "pnl" in result
    
    def test_stress_test_vol_up(self, aggregator):
        """Test stress test with volatility increase."""
        result = aggregator.stress_test(
            underlying="AAPL",
            spot_shock_pct=0.0,
            vol_shock_pct=0.20,  # +20% vol
        )
        
        assert "pnl" in result
    
    def test_stress_test_combined(self, aggregator):
        """Test stress test with combined shocks."""
        result = aggregator.stress_test(
            underlying="AAPL",
            spot_shock_pct=-0.15,  # -15% spot
            vol_shock_pct=0.30,   # +30% vol
        )
        
        assert "pnl" in result


class TestScenarioMatrix:
    """Test scenario matrix generation."""
    
    @pytest.fixture
    def aggregator(self):
        """Create aggregator."""
        positions = [
            {
                "position_id": "POS-001",
                "symbol": "AAPL240119C00150000",
                "underlying": "AAPL",
                "quantity": 10,
                "delta": 5.5,
                "gamma": 0.24,
                "theta": -3.5,
                "vega": 3.0,
                "market_value": 4200.0,
            },
        ]
        return RiskAggregator(
            positions=positions,
            spot_prices={"AAPL": 150.0},
        )
    
    def test_scenario_matrix_generation(self, aggregator):
        """Test generating scenario matrix."""
        matrix = aggregator.get_scenario_matrix(
            underlying="AAPL",
            spot_range=(-0.10, 0.10),
            vol_range=(-0.10, 0.10),
            spot_steps=5,
            vol_steps=5,
        )
        
        assert "spot_shocks" in matrix
        assert "vol_shocks" in matrix
        assert "pnl_matrix" in matrix
        
        # Should be 5x5 matrix
        assert len(matrix["pnl_matrix"]) == 5
        assert len(matrix["pnl_matrix"][0]) == 5
    
    def test_scenario_matrix_contains_base_case(self, aggregator):
        """Test that scenario matrix contains base case (0% shock)."""
        matrix = aggregator.get_scenario_matrix(
            underlying="AAPL",
            spot_range=(-0.10, 0.10),
            vol_range=(-0.10, 0.10),
            spot_steps=5,
            vol_steps=5,
        )
        
        # Find center of matrix (base case)
        center_idx = 2  # Middle of 5 steps
        base_pnl = matrix["pnl_matrix"][center_idx][center_idx]
        
        # Base case should have zero or near-zero P&L
        assert abs(base_pnl) < 100  # Allow for theta decay


class TestBetaWeighting:
    """Test beta-weighted Greeks."""
    
    @pytest.fixture
    def aggregator_with_betas(self):
        """Create aggregator with beta data."""
        positions = [
            {
                "position_id": "POS-001",
                "symbol": "AAPL240119C00150000",
                "underlying": "AAPL",
                "quantity": 10,
                "delta": 5.5,
                "gamma": 0.24,
                "theta": -3.5,
                "vega": 3.0,
                "market_value": 4200.0,
            },
            {
                "position_id": "POS-002",
                "symbol": "MSFT240119C00400000",
                "underlying": "MSFT",
                "quantity": 5,
                "delta": 2.75,
                "gamma": 0.08,
                "theta": -2.0,
                "vega": 1.5,
                "market_value": 3000.0,
            },
        ]
        
        return RiskAggregator(
            positions=positions,
            spot_prices={"AAPL": 150.0, "MSFT": 400.0},
            betas={"AAPL": 1.2, "MSFT": 0.95},  # Beta to SPY
            index_price=500.0,  # SPY price
        )
    
    def test_beta_weighted_delta(self, aggregator_with_betas):
        """Test beta-weighted delta calculation."""
        portfolio = aggregator_with_betas.aggregate_portfolio()
        
        # Beta-weighted delta should be different from raw delta
        assert portfolio.beta_weighted_delta is not None
        assert portfolio.beta_weighted_delta != portfolio.total_delta
    
    def test_beta_adjustment(self, aggregator_with_betas):
        """Test beta adjustment factors."""
        by_underlying = aggregator_with_betas.aggregate_by_underlying()
        
        # AAPL beta = 1.2
        aapl_bwd = by_underlying["AAPL"].net_delta * 1.2
        
        # MSFT beta = 0.95
        msft_bwd = by_underlying["MSFT"].net_delta * 0.95
        
        # Total beta-weighted delta
        expected_bwd = aapl_bwd + msft_bwd
        
        portfolio = aggregator_with_betas.aggregate_portfolio()
        assert abs(portfolio.beta_weighted_delta - expected_bwd) < 0.1


class TestVaRCalculation:
    """Test Value at Risk calculations."""
    
    @pytest.fixture
    def aggregator(self):
        """Create aggregator."""
        positions = [
            {
                "position_id": "POS-001",
                "symbol": "AAPL240119C00150000",
                "underlying": "AAPL",
                "quantity": 10,
                "delta": 5.5,
                "gamma": 0.24,
                "theta": -3.5,
                "vega": 3.0,
                "market_value": 4200.0,
            },
        ]
        return RiskAggregator(
            positions=positions,
            spot_prices={"AAPL": 150.0},
        )
    
    def test_parametric_var(self, aggregator):
        """Test parametric VaR calculation."""
        var = aggregator.calculate_parametric_var(
            confidence_level=0.95,
            horizon_days=1,
            underlying_volatility={"AAPL": 0.25},
        )
        
        assert "var_95" in var
        assert "var_99" in var
        assert var["var_95"] > 0
        assert var["var_99"] > var["var_95"]
    
    def test_historical_var(self, aggregator):
        """Test historical VaR with return series."""
        # Generate mock historical returns
        returns = np.random.normal(0, 0.01, 252)
        
        var = aggregator.calculate_historical_var(
            returns=returns.tolist(),
            confidence_level=0.95,
        )
        
        assert "var_95" in var
        assert var["var_95"] > 0


class TestConcentrationRisk:
    """Test concentration risk metrics."""
    
    @pytest.fixture
    def diverse_portfolio(self):
        """Create diversified portfolio."""
        positions = [
            {"position_id": f"POS-{i}", "symbol": f"STOCK{i}", "underlying": f"STOCK{i}",
             "quantity": 10, "delta": 1.0, "gamma": 0.1, "theta": -0.5, "vega": 0.5,
             "market_value": 1000.0}
            for i in range(10)
        ]
        spots = {f"STOCK{i}": 100.0 for i in range(10)}
        return RiskAggregator(positions=positions, spot_prices=spots)
    
    @pytest.fixture
    def concentrated_portfolio(self):
        """Create concentrated portfolio."""
        positions = [
            {"position_id": "POS-001", "symbol": "AAPL", "underlying": "AAPL",
             "quantity": 100, "delta": 80.0, "gamma": 5.0, "theta": -10.0, "vega": 20.0,
             "market_value": 80000.0},
            {"position_id": "POS-002", "symbol": "MSFT", "underlying": "MSFT",
             "quantity": 10, "delta": 5.0, "gamma": 0.5, "theta": -1.0, "vega": 2.0,
             "market_value": 10000.0},
        ]
        return RiskAggregator(
            positions=positions,
            spot_prices={"AAPL": 150.0, "MSFT": 400.0},
        )
    
    def test_concentration_metrics_diverse(self, diverse_portfolio):
        """Test concentration metrics for diverse portfolio."""
        metrics = diverse_portfolio.calculate_concentration_metrics()
        
        # HHI should be low for diverse portfolio
        assert metrics["hhi"] < 0.2
        
        # Top position weight should be ~10%
        assert 0.08 < metrics["top_position_weight"] < 0.12
    
    def test_concentration_metrics_concentrated(self, concentrated_portfolio):
        """Test concentration metrics for concentrated portfolio."""
        metrics = concentrated_portfolio.calculate_concentration_metrics()
        
        # HHI should be high
        assert metrics["hhi"] > 0.5
        
        # Top position should be ~89%
        assert metrics["top_position_weight"] > 0.8

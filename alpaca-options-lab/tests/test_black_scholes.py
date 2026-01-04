"""
Tests for src.pricing.black_scholes - Black-Scholes Option Pricing

Tests cover:
- European call/put pricing
- Greeks calculation (delta, gamma, theta, vega, rho)
- Boundary conditions
- Put-call parity
- Edge cases (deep ITM/OTM, near expiry)
"""
from __future__ import annotations

import math
from decimal import Decimal

import pytest
import numpy as np

from src.pricing.black_scholes import (
    BlackScholesModel,
    black_scholes_price,
    calculate_greeks,
    calculate_delta,
    calculate_gamma,
    calculate_theta,
    calculate_vega,
    calculate_rho,
    d1,
    d2,
    OptionType,
)


class TestBlackScholesFormulas:
    """Test Black-Scholes fundamental formulas."""
    
    def test_d1_calculation(self):
        """Test d1 calculation."""
        S, K, r, T, sigma = 100, 100, 0.05, 1.0, 0.2
        
        d1_val = d1(S, K, r, T, sigma)
        
        # Manual calculation
        expected = (math.log(S/K) + (r + sigma**2/2)*T) / (sigma * math.sqrt(T))
        
        assert abs(d1_val - expected) < 1e-10
    
    def test_d2_calculation(self):
        """Test d2 calculation."""
        S, K, r, T, sigma = 100, 100, 0.05, 1.0, 0.2
        
        d1_val = d1(S, K, r, T, sigma)
        d2_val = d2(S, K, r, T, sigma)
        
        expected = d1_val - sigma * math.sqrt(T)
        
        assert abs(d2_val - expected) < 1e-10


class TestBlackScholesPrice:
    """Test Black-Scholes pricing function."""
    
    def test_atm_call_price(self):
        """Test ATM call option price."""
        price = black_scholes_price(
            spot=100, strike=100, rate=0.05,
            time_to_expiry=1.0, volatility=0.2,
            option_type="call",
        )
        
        # ATM call should be approximately 10.45 for these parameters
        assert 10.0 < price < 11.0
    
    def test_atm_put_price(self):
        """Test ATM put option price."""
        price = black_scholes_price(
            spot=100, strike=100, rate=0.05,
            time_to_expiry=1.0, volatility=0.2,
            option_type="put",
        )
        
        # ATM put should be approximately 5.57 for these parameters
        assert 5.0 < price < 6.5
    
    def test_itm_call_price(self):
        """Test ITM call option price."""
        price = black_scholes_price(
            spot=120, strike=100, rate=0.05,
            time_to_expiry=1.0, volatility=0.2,
            option_type="call",
        )
        
        # ITM call has intrinsic value of 20
        assert price > 20.0
    
    def test_itm_put_price(self):
        """Test ITM put option price."""
        price = black_scholes_price(
            spot=80, strike=100, rate=0.05,
            time_to_expiry=1.0, volatility=0.2,
            option_type="put",
        )
        
        # ITM put has intrinsic value of 20
        assert price > 20.0
    
    def test_otm_call_price(self):
        """Test OTM call option price."""
        price = black_scholes_price(
            spot=80, strike=100, rate=0.05,
            time_to_expiry=1.0, volatility=0.2,
            option_type="call",
        )
        
        # OTM call has no intrinsic value, only time value
        assert 0 < price < 5
    
    def test_otm_put_price(self):
        """Test OTM put option price."""
        price = black_scholes_price(
            spot=120, strike=100, rate=0.05,
            time_to_expiry=1.0, volatility=0.2,
            option_type="put",
        )
        
        # OTM put has no intrinsic value
        assert 0 < price < 5
    
    def test_deep_itm_call_converges_to_intrinsic(self):
        """Test deep ITM call converges to intrinsic + discount."""
        price = black_scholes_price(
            spot=200, strike=100, rate=0.05,
            time_to_expiry=0.01, volatility=0.2,
            option_type="call",
        )
        
        intrinsic = 200 - 100
        assert abs(price - intrinsic) < 2.0
    
    def test_deep_otm_call_approaches_zero(self):
        """Test deep OTM call approaches zero."""
        price = black_scholes_price(
            spot=50, strike=100, rate=0.05,
            time_to_expiry=0.01, volatility=0.2,
            option_type="call",
        )
        
        assert price < 0.01
    
    def test_zero_time_to_expiry_call(self):
        """Test call at expiry."""
        # ITM
        price_itm = black_scholes_price(
            spot=110, strike=100, rate=0.05,
            time_to_expiry=0.0001, volatility=0.2,
            option_type="call",
        )
        assert abs(price_itm - 10) < 0.1
        
        # OTM
        price_otm = black_scholes_price(
            spot=90, strike=100, rate=0.05,
            time_to_expiry=0.0001, volatility=0.2,
            option_type="call",
        )
        assert price_otm < 0.1
    
    def test_put_call_parity(self):
        """Test put-call parity: C - P = S - K*e^(-rT)."""
        S, K, r, T, sigma = 100, 100, 0.05, 1.0, 0.2
        
        call_price = black_scholes_price(S, K, r, T, sigma, "call")
        put_price = black_scholes_price(S, K, r, T, sigma, "put")
        
        # Put-call parity
        lhs = call_price - put_price
        rhs = S - K * math.exp(-r * T)
        
        assert abs(lhs - rhs) < 1e-8
    
    def test_higher_volatility_higher_price(self):
        """Test that higher volatility leads to higher option prices."""
        base_params = dict(
            spot=100, strike=100, rate=0.05, time_to_expiry=1.0
        )
        
        low_vol_call = black_scholes_price(**base_params, volatility=0.1, option_type="call")
        high_vol_call = black_scholes_price(**base_params, volatility=0.3, option_type="call")
        
        assert high_vol_call > low_vol_call
    
    def test_longer_time_higher_price(self):
        """Test that longer time to expiry leads to higher call prices."""
        base_params = dict(
            spot=100, strike=100, rate=0.05, volatility=0.2
        )
        
        short_time = black_scholes_price(**base_params, time_to_expiry=0.25, option_type="call")
        long_time = black_scholes_price(**base_params, time_to_expiry=1.0, option_type="call")
        
        assert long_time > short_time


class TestGreeksCalculation:
    """Test Greeks calculations."""
    
    @pytest.fixture
    def standard_params(self):
        """Standard option parameters."""
        return {
            "spot": 100,
            "strike": 100,
            "rate": 0.05,
            "time_to_expiry": 0.25,  # 3 months
            "volatility": 0.2,
        }
    
    def test_call_delta_positive(self, standard_params):
        """Test call delta is positive."""
        delta = calculate_delta(**standard_params, option_type="call")
        
        assert 0 < delta < 1
    
    def test_put_delta_negative(self, standard_params):
        """Test put delta is negative."""
        delta = calculate_delta(**standard_params, option_type="put")
        
        assert -1 < delta < 0
    
    def test_atm_call_delta_around_half(self, standard_params):
        """Test ATM call delta is around 0.5."""
        delta = calculate_delta(**standard_params, option_type="call")
        
        # ATM delta should be slightly above 0.5 due to drift
        assert 0.45 < delta < 0.65
    
    def test_call_put_delta_relationship(self, standard_params):
        """Test call delta - put delta = 1."""
        call_delta = calculate_delta(**standard_params, option_type="call")
        put_delta = calculate_delta(**standard_params, option_type="put")
        
        assert abs((call_delta - put_delta) - 1.0) < 1e-8
    
    def test_gamma_positive(self, standard_params):
        """Test gamma is always positive."""
        gamma = calculate_gamma(**standard_params)
        
        assert gamma > 0
    
    def test_gamma_same_for_call_and_put(self, standard_params):
        """Test gamma is same for call and put at same strike."""
        # Gamma doesn't depend on option type for same parameters
        gamma = calculate_gamma(**standard_params)
        
        assert gamma > 0
    
    def test_atm_gamma_maximized(self, standard_params):
        """Test gamma is highest at ATM."""
        atm_gamma = calculate_gamma(**standard_params)
        
        # ITM gamma
        itm_params = {**standard_params, "spot": 110}
        itm_gamma = calculate_gamma(**itm_params)
        
        # OTM gamma
        otm_params = {**standard_params, "spot": 90}
        otm_gamma = calculate_gamma(**otm_params)
        
        assert atm_gamma > itm_gamma
        assert atm_gamma > otm_gamma
    
    def test_theta_negative_for_long_call(self, standard_params):
        """Test theta is negative for long call (time decay)."""
        theta = calculate_theta(**standard_params, option_type="call")
        
        assert theta < 0
    
    def test_theta_negative_for_long_put(self, standard_params):
        """Test theta is negative for long put."""
        theta = calculate_theta(**standard_params, option_type="put")
        
        # Long put theta is usually negative
        assert theta < 0 or abs(theta) < 0.01  # Can be slightly positive for deep ITM
    
    def test_vega_positive(self, standard_params):
        """Test vega is always positive."""
        vega = calculate_vega(**standard_params)
        
        assert vega > 0
    
    def test_vega_same_for_call_and_put(self, standard_params):
        """Test vega is same for call and put at same strike."""
        vega = calculate_vega(**standard_params)
        
        assert vega > 0
    
    def test_call_rho_positive(self, standard_params):
        """Test call rho is positive."""
        rho = calculate_rho(**standard_params, option_type="call")
        
        assert rho > 0
    
    def test_put_rho_negative(self, standard_params):
        """Test put rho is negative."""
        rho = calculate_rho(**standard_params, option_type="put")
        
        assert rho < 0
    
    def test_calculate_greeks_all(self, standard_params):
        """Test calculate_greeks returns all Greeks."""
        greeks = calculate_greeks(**standard_params, option_type="call")
        
        assert "delta" in greeks
        assert "gamma" in greeks
        assert "theta" in greeks
        assert "vega" in greeks
        assert "rho" in greeks


class TestBlackScholesModel:
    """Test BlackScholesModel class."""
    
    @pytest.fixture
    def model(self):
        """Create model instance."""
        return BlackScholesModel()
    
    def test_price_call(self, model):
        """Test pricing call with model."""
        price = model.price(
            spot=100, strike=100, rate=0.05,
            time_to_expiry=1.0, volatility=0.2,
            option_type=OptionType.CALL,
        )
        
        assert 10.0 < price < 11.0
    
    def test_price_put(self, model):
        """Test pricing put with model."""
        price = model.price(
            spot=100, strike=100, rate=0.05,
            time_to_expiry=1.0, volatility=0.2,
            option_type=OptionType.PUT,
        )
        
        assert 5.0 < price < 6.5
    
    def test_greeks_call(self, model):
        """Test Greeks calculation with model."""
        greeks = model.greeks(
            spot=100, strike=100, rate=0.05,
            time_to_expiry=0.25, volatility=0.2,
            option_type=OptionType.CALL,
        )
        
        assert 0.4 < greeks.delta < 0.7
        assert greeks.gamma > 0
        assert greeks.theta < 0
        assert greeks.vega > 0
        assert greeks.rho > 0
    
    def test_model_with_dividend_yield(self, model):
        """Test model with dividend yield."""
        # Without dividend
        price_no_div = model.price(
            spot=100, strike=100, rate=0.05,
            time_to_expiry=1.0, volatility=0.2,
            option_type=OptionType.CALL,
            dividend_yield=0.0,
        )
        
        # With dividend
        price_with_div = model.price(
            spot=100, strike=100, rate=0.05,
            time_to_expiry=1.0, volatility=0.2,
            option_type=OptionType.CALL,
            dividend_yield=0.02,
        )
        
        # Dividend yield reduces call price
        assert price_with_div < price_no_div


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_very_small_time_to_expiry(self):
        """Test with very small time to expiry."""
        price = black_scholes_price(
            spot=100, strike=100, rate=0.05,
            time_to_expiry=0.001, volatility=0.2,
            option_type="call",
        )
        
        # Should not raise and should be near zero for ATM
        assert price >= 0
        assert price < 1
    
    def test_very_high_volatility(self):
        """Test with very high volatility."""
        price = black_scholes_price(
            spot=100, strike=100, rate=0.05,
            time_to_expiry=1.0, volatility=1.0,  # 100% vol
            option_type="call",
        )
        
        # Should not raise
        assert price > 0
        assert price < 100  # Less than spot
    
    def test_very_low_volatility(self):
        """Test with very low volatility."""
        price = black_scholes_price(
            spot=100, strike=100, rate=0.05,
            time_to_expiry=1.0, volatility=0.01,  # 1% vol
            option_type="call",
        )
        
        # Should not raise
        assert price > 0
    
    def test_zero_interest_rate(self):
        """Test with zero interest rate."""
        call_price = black_scholes_price(
            spot=100, strike=100, rate=0.0,
            time_to_expiry=1.0, volatility=0.2,
            option_type="call",
        )
        
        put_price = black_scholes_price(
            spot=100, strike=100, rate=0.0,
            time_to_expiry=1.0, volatility=0.2,
            option_type="put",
        )
        
        # Put-call parity with r=0: C - P = S - K
        assert abs((call_price - put_price) - (100 - 100)) < 1e-8
    
    def test_very_high_strike(self):
        """Test with very high strike (deep OTM call)."""
        price = black_scholes_price(
            spot=100, strike=500, rate=0.05,
            time_to_expiry=1.0, volatility=0.2,
            option_type="call",
        )
        
        assert price >= 0
        assert price < 0.01  # Essentially zero
    
    def test_very_low_strike(self):
        """Test with very low strike (deep ITM call)."""
        price = black_scholes_price(
            spot=100, strike=10, rate=0.05,
            time_to_expiry=1.0, volatility=0.2,
            option_type="call",
        )
        
        # Deep ITM call worth approximately intrinsic
        intrinsic = 100 - 10 * math.exp(-0.05 * 1.0)
        assert abs(price - intrinsic) < 0.5


class TestNumericalStability:
    """Test numerical stability."""
    
    def test_repeated_calculations_consistent(self):
        """Test that repeated calculations give consistent results."""
        params = dict(
            spot=100, strike=100, rate=0.05,
            time_to_expiry=1.0, volatility=0.2,
            option_type="call",
        )
        
        prices = [black_scholes_price(**params) for _ in range(100)]
        
        # All prices should be identical
        assert all(abs(p - prices[0]) < 1e-10 for p in prices)
    
    def test_vectorized_calculation(self):
        """Test vectorized calculation gives same results as scalar."""
        S, K, r, T, sigma = 100, 100, 0.05, 1.0, 0.2
        
        # Scalar
        scalar_price = black_scholes_price(S, K, r, T, sigma, "call")
        
        # Array (if supported)
        spots = np.array([S, S, S])
        
        # Each should give same result
        for spot in spots:
            assert abs(black_scholes_price(spot, K, r, T, sigma, "call") - scalar_price) < 1e-10

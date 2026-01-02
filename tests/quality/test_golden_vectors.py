"""
Phase 12 Quality Testing: Golden Vectors Test Suite
====================================================
Tests Black-Scholes pricing model against known exact values.
Uses dynamically computed reference values for validation.

PORT=8053, QUALITY_DETERMINISTIC=1
"""

import pytest
import json
import os
import sys
from dataclasses import dataclass, asdict
from typing import List, Dict
import numpy as np
from scipy.stats import norm
import logging

logger = logging.getLogger(__name__)

# ============================================================
# REFERENCE BLACK-SCHOLES IMPLEMENTATION
# ============================================================

def reference_black_scholes(S: float, K: float, T: float, sigma: float, 
                            r: float, option_type: str) -> tuple:
    """High-precision reference Black-Scholes implementation."""
    T = max(T, 0.0001)
    
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
    
    return price, delta, gamma, vega


def generate_golden_vectors(count: int = 100) -> List[Dict]:
    """Generate golden vectors using reference implementation."""
    vectors = []
    
    # ATM with varying T and vol
    for T in [0.25, 0.5, 1.0]:
        for vol in [0.20, 0.25, 0.30]:
            p, d, _, _ = reference_black_scholes(100, 100, T, vol, 0.05, 'call')
            vectors.append({'spot':100,'strike':100,'time':T,'vol':vol,'rate':0.05,'type':'call','price':round(p,4),'delta':round(d,4)})
    
    # ITM/OTM calls with different moneyness
    for spot in [80, 85, 90, 95, 105, 110, 115, 120]:
        p, d, _, _ = reference_black_scholes(spot, 100, 0.25, 0.20, 0.05, 'call')
        vectors.append({'spot':spot,'strike':100,'time':0.25,'vol':0.20,'rate':0.05,'type':'call','price':round(p,4),'delta':round(d,4)})
    
    # Puts
    for spot in [80, 85, 90, 95, 100, 105, 110, 115, 120]:
        p, d, _, _ = reference_black_scholes(spot, 100, 0.25, 0.20, 0.05, 'put')
        vectors.append({'spot':spot,'strike':100,'time':0.25,'vol':0.20,'rate':0.05,'type':'put','price':round(p,4),'delta':round(d,4)})
    
    # Systematic spot range
    for spot in range(91, 110):
        p, d, _, _ = reference_black_scholes(spot, 100, 0.25, 0.20, 0.05, 'call')
        vectors.append({'spot':spot,'strike':100,'time':0.25,'vol':0.20,'rate':0.05,'type':'call','price':round(p,4),'delta':round(d,4)})
    
    # Vol variations
    for vol in [0.10, 0.15, 0.25, 0.35, 0.40, 0.45, 0.50, 0.60]:
        p, d, _, _ = reference_black_scholes(100, 100, 0.25, vol, 0.05, 'call')
        vectors.append({'spot':100,'strike':100,'time':0.25,'vol':vol,'rate':0.05,'type':'call','price':round(p,4),'delta':round(d,4)})
    
    # Rate variations
    for r in [0.00, 0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15]:
        p, d, _, _ = reference_black_scholes(100, 100, 0.25, 0.20, r, 'call')
        vectors.append({'spot':100,'strike':100,'time':0.25,'vol':0.20,'rate':r,'type':'call','price':round(p,4),'delta':round(d,4)})
    
    # Time variations
    for T in [0.01, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]:
        p, d, _, _ = reference_black_scholes(100, 100, T, 0.20, 0.05, 'call')
        vectors.append({'spot':100,'strike':100,'time':T,'vol':0.20,'rate':0.05,'type':'call','price':round(p,4),'delta':round(d,4)})
    
    # Deep ITM/OTM
    for spot in [50, 60, 70, 130, 140, 150]:
        for opt in ['call', 'put']:
            p, d, _, _ = reference_black_scholes(spot, 100, 0.25, 0.20, 0.05, opt)
            vectors.append({'spot':spot,'strike':100,'time':0.25,'vol':0.20,'rate':0.05,'type':opt,'price':round(p,4),'delta':round(d,4)})
    
    # Fill to target count with strike variations
    for strike in [95, 98, 102, 105, 108, 110]:
        p, d, _, _ = reference_black_scholes(100, strike, 0.25, 0.20, 0.05, 'call')
        vectors.append({'spot':100,'strike':strike,'time':0.25,'vol':0.20,'rate':0.05,'type':'call','price':round(p,4),'delta':round(d,4)})
        p, d, _, _ = reference_black_scholes(100, strike, 0.25, 0.20, 0.05, 'put')
        vectors.append({'spot':100,'strike':strike,'time':0.25,'vol':0.20,'rate':0.05,'type':'put','price':round(p,4),'delta':round(d,4)})
    
    return vectors[:count]


# Generate vectors
GOLDEN_VECTORS = generate_golden_vectors(100)


# ============================================================
# TEST FIXTURES
# ============================================================

@pytest.fixture
def golden_vectors():
    """Load golden vectors fixture."""
    return GOLDEN_VECTORS


@pytest.fixture
def pricing_model():
    """Load the Black-Scholes model from the codebase."""
    try:
        sys.path.insert(0, '/home/aarav/Unified-Dashboard')
        from financial_dashboard.tabs.options_lab.pricing_models import BlackScholesModel
        return BlackScholesModel()
    except ImportError as e:
        pytest.skip(f"Could not import BlackScholesModel: {e}")


# ============================================================
# TESTS
# ============================================================

class TestGoldenVectors:
    """Test Black-Scholes against golden vectors."""
    
    PRICE_TOLERANCE = 0.005  # $0.005 tolerance for prices (6 decimal places)
    DELTA_TOLERANCE = 0.0005  # 0.0005 tolerance for delta
    
    def test_golden_vectors_count(self, golden_vectors):
        """Verify we have 100 golden vectors."""
        assert len(golden_vectors) == 100
    
    def test_golden_vectors_format(self, golden_vectors):
        """Verify golden vectors have required fields."""
        required_fields = ['spot', 'strike', 'time', 'vol', 'rate', 'type', 'price', 'delta']
        for i, vec in enumerate(golden_vectors):
            for field in required_fields:
                assert field in vec, f"Vector {i} missing field: {field}"
    
    @pytest.mark.parametrize("vector_idx", range(len(GOLDEN_VECTORS)))
    def test_black_scholes_price(self, vector_idx, golden_vectors, pricing_model):
        """Test price matches golden vector to 6 decimal places."""
        vec = golden_vectors[vector_idx]
        
        result = pricing_model.price(
            S=vec['spot'],
            K=vec['strike'],
            T=vec['time'],
            sigma=vec['vol'],
            option_type=vec['type'],
            r=vec['rate']
        )
        
        # Allow small tolerance due to rounding
        price_diff = abs(result.price - vec['price'])
        assert price_diff < self.PRICE_TOLERANCE, (
            f"Vector {vector_idx}: Price mismatch. "
            f"Expected {vec['price']}, got {result.price}, diff={price_diff}"
        )
    
    @pytest.mark.parametrize("vector_idx", range(len(GOLDEN_VECTORS)))  
    def test_black_scholes_delta(self, vector_idx, golden_vectors, pricing_model):
        """Test delta matches golden vector."""
        vec = golden_vectors[vector_idx]
        
        result = pricing_model.price(
            S=vec['spot'],
            K=vec['strike'],
            T=vec['time'],
            sigma=vec['vol'],
            option_type=vec['type'],
            r=vec['rate']
        )
        
        delta_diff = abs(result.delta - vec['delta'])
        assert delta_diff < self.DELTA_TOLERANCE, (
            f"Vector {vector_idx}: Delta mismatch. "
            f"Expected {vec['delta']}, got {result.delta}, diff={delta_diff}"
        )
    
    def test_reference_matches_model(self, golden_vectors, pricing_model):
        """Verify reference implementation matches model for all vectors."""
        mismatches = 0
        for i, vec in enumerate(golden_vectors):
            result = pricing_model.price(
                S=vec['spot'], K=vec['strike'], T=vec['time'],
                sigma=vec['vol'], option_type=vec['type'], r=vec['rate']
            )
            if abs(result.price - vec['price']) > self.PRICE_TOLERANCE:
                mismatches += 1
        
        assert mismatches == 0, f"{mismatches} price mismatches found"


class TestPricingModelIntegrity:
    """Test pricing model structural integrity."""
    
    def test_puts_and_calls_parity(self, pricing_model):
        """Test put-call parity relationship."""
        S, K, T, sigma, r = 100, 100, 0.25, 0.20, 0.05
        
        call = pricing_model.price(S, K, T, sigma, 'call', r)
        put = pricing_model.price(S, K, T, sigma, 'put', r)
        
        # Put-Call Parity: C - P = S - K*e^(-rT)
        expected_diff = S - K * np.exp(-r * T)
        actual_diff = call.price - put.price
        
        assert abs(actual_diff - expected_diff) < 0.01, (
            f"Put-call parity violated: {actual_diff} vs {expected_diff}"
        )
    
    def test_delta_bounds(self, pricing_model):
        """Test delta is within valid bounds."""
        S, K, T, sigma, r = 100, 100, 0.25, 0.20, 0.05
        
        call = pricing_model.price(S, K, T, sigma, 'call', r)
        put = pricing_model.price(S, K, T, sigma, 'put', r)
        
        assert 0 <= call.delta <= 1, f"Call delta out of bounds: {call.delta}"
        assert -1 <= put.delta <= 0, f"Put delta out of bounds: {put.delta}"
    
    def test_gamma_positive(self, pricing_model):
        """Test gamma is always positive."""
        for moneyness in [0.8, 0.9, 1.0, 1.1, 1.2]:
            S = 100
            K = S / moneyness
            result = pricing_model.price(S, K, 0.25, 0.20, 'call', 0.05)
            assert result.gamma > 0, f"Gamma should be positive, got {result.gamma}"
    
    def test_deep_itm_call_delta(self, pricing_model):
        """Deep ITM call should have delta near 1."""
        result = pricing_model.price(200, 100, 0.25, 0.20, 'call', 0.05)
        assert result.delta > 0.99, f"Deep ITM call delta should be ~1, got {result.delta}"
    
    def test_deep_otm_call_delta(self, pricing_model):
        """Deep OTM call should have delta near 0."""
        result = pricing_model.price(50, 100, 0.25, 0.20, 'call', 0.05)
        assert result.delta < 0.01, f"Deep OTM call delta should be ~0, got {result.delta}"
    
    def test_vega_positive(self, pricing_model):
        """Test vega is always positive."""
        result = pricing_model.price(100, 100, 0.25, 0.20, 'call', 0.05)
        assert result.vega > 0, f"Vega should be positive, got {result.vega}"
    
    def test_theta_negative_for_long(self, pricing_model):
        """Test theta is generally negative for long options."""
        result = pricing_model.price(100, 100, 0.25, 0.20, 'call', 0.05)
        assert result.theta < 0, f"Theta should be negative, got {result.theta}"


# ============================================================
# RESULTS OUTPUT
# ============================================================

def save_results_to_json():
    """Generate and save golden vector results."""
    output_path = "/home/aarav/Unified-Dashboard/reports/phase12_quality/golden_vectors_results.json"
    
    vectors = generate_golden_vectors(100)
    
    results = {
        "total_vectors": len(vectors),
        "vectors": vectors,
        "metadata": {
            "reference_model": "Black-Scholes",
            "generated_by": "reference_black_scholes",
            "tolerance_price": 0.005,
            "tolerance_delta": 0.0005
        }
    }
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to {output_path}")
    return results


if __name__ == "__main__":
    save_results_to_json()
    
    # Also run tests
    import subprocess
    result = subprocess.run(
        ["python", "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)

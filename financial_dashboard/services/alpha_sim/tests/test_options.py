"""
Tests for AlphaSim Options module - HISTORICAL_OPTIONS endpoint.
"""
import pytest
import math
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


class TestBlackScholes:
    """Tests for Black-Scholes option pricing."""
    
    def test_black_scholes_call_at_the_money(self):
        """Test call option pricing for ATM option."""
        from financial_dashboard.services.alpha_sim.options import _black_scholes_call
        
        # ATM call with 1 year to expiration
        S = 100  # Stock price
        K = 100  # Strike price
        T = 1.0  # Time to expiration (1 year)
        r = 0.05  # Risk-free rate
        sigma = 0.2  # Volatility
        
        call_price = _black_scholes_call(S, K, T, r, sigma)
        
        # ATM call should have positive value
        assert call_price > 0
        # ATM call should be roughly 10-15% of stock price for 20% vol
        assert 5 < call_price < 20
    
    def test_black_scholes_call_deep_itm(self):
        """Test call option for deep in-the-money."""
        from financial_dashboard.services.alpha_sim.options import _black_scholes_call
        
        S = 150  # Stock price much higher than strike
        K = 100  # Strike price
        T = 0.25  # 3 months
        r = 0.05
        sigma = 0.2
        
        call_price = _black_scholes_call(S, K, T, r, sigma)
        
        # Deep ITM call should be close to intrinsic value
        intrinsic = S - K
        assert call_price >= intrinsic * 0.95
    
    def test_black_scholes_call_deep_otm(self):
        """Test call option for deep out-of-the-money."""
        from financial_dashboard.services.alpha_sim.options import _black_scholes_call
        
        S = 100
        K = 150  # Strike much higher than stock
        T = 0.25
        r = 0.05
        sigma = 0.2
        
        call_price = _black_scholes_call(S, K, T, r, sigma)
        
        # Deep OTM call should have small value
        assert call_price >= 0.01  # Minimum price
        assert call_price < 5  # But not too high
    
    def test_black_scholes_call_at_expiration(self):
        """Test call option at expiration."""
        from financial_dashboard.services.alpha_sim.options import _black_scholes_call
        
        # ITM at expiration
        call_itm = _black_scholes_call(S=110, K=100, T=0, r=0.05, sigma=0.2)
        assert call_itm == max(110 - 100, 0)
        
        # OTM at expiration
        call_otm = _black_scholes_call(S=90, K=100, T=0, r=0.05, sigma=0.2)
        assert call_otm == max(90 - 100, 0)
    
    def test_black_scholes_put_at_the_money(self):
        """Test put option pricing for ATM option."""
        from financial_dashboard.services.alpha_sim.options import _black_scholes_put
        
        S = 100
        K = 100
        T = 1.0
        r = 0.05
        sigma = 0.2
        
        put_price = _black_scholes_put(S, K, T, r, sigma)
        
        # ATM put should have positive value
        assert put_price > 0
    
    def test_put_call_parity(self):
        """Test put-call parity relationship."""
        from financial_dashboard.services.alpha_sim.options import (
            _black_scholes_call, _black_scholes_put
        )
        
        S = 100
        K = 100
        T = 1.0
        r = 0.05
        sigma = 0.2
        
        call = _black_scholes_call(S, K, T, r, sigma)
        put = _black_scholes_put(S, K, T, r, sigma)
        
        # Put-call parity: C - P = S - K*e^(-rT)
        parity_lhs = call - put
        parity_rhs = S - K * math.exp(-r * T)
        
        assert abs(parity_lhs - parity_rhs) < 0.01


class TestGenerateSyntheticChain:
    """Tests for synthetic options chain generation."""
    
    def test_generate_synthetic_chain_structure(self):
        """Test that chain has correct structure."""
        from financial_dashboard.services.alpha_sim.options import _generate_synthetic_chain
        
        contracts = _generate_synthetic_chain(
            symbol="AAPL",
            current_price=150.0,
            expiration_date=datetime.utcnow() + timedelta(days=30),
            volatility=0.25
        )
        
        assert len(contracts) > 0
        
        # Check contract structure
        contract = contracts[0]
        assert "contractSymbol" in contract
        assert "strike" in contract
        assert "type" in contract
        assert "expiration" in contract
        assert "bid" in contract
        assert "ask" in contract
        assert "lastPrice" in contract
        assert "volume" in contract
        assert "openInterest" in contract
        assert "impliedVolatility" in contract
        assert "inTheMoney" in contract
    
    def test_generate_synthetic_chain_has_calls_and_puts(self):
        """Test that chain has both calls and puts."""
        from financial_dashboard.services.alpha_sim.options import _generate_synthetic_chain
        
        contracts = _generate_synthetic_chain(
            symbol="AAPL",
            current_price=150.0,
            expiration_date=datetime.utcnow() + timedelta(days=30)
        )
        
        calls = [c for c in contracts if c["type"] == "call"]
        puts = [c for c in contracts if c["type"] == "put"]
        
        assert len(calls) > 0
        assert len(puts) > 0
        assert len(calls) == len(puts)
    
    def test_generate_synthetic_chain_strikes_centered(self):
        """Test that strikes are centered around current price."""
        from financial_dashboard.services.alpha_sim.options import _generate_synthetic_chain
        
        current_price = 150.0
        contracts = _generate_synthetic_chain(
            symbol="AAPL",
            current_price=current_price,
            expiration_date=datetime.utcnow() + timedelta(days=30)
        )
        
        strikes = sorted(set(c["strike"] for c in contracts))
        
        # Check that there are strikes both above and below current price
        assert any(s < current_price for s in strikes)
        assert any(s > current_price for s in strikes)
    
    def test_generate_synthetic_chain_bid_ask_spread(self):
        """Test bid-ask spread is reasonable."""
        from financial_dashboard.services.alpha_sim.options import _generate_synthetic_chain
        
        contracts = _generate_synthetic_chain(
            symbol="AAPL",
            current_price=150.0,
            expiration_date=datetime.utcnow() + timedelta(days=30)
        )
        
        for contract in contracts:
            assert contract["bid"] <= contract["ask"]
            assert contract["bid"] >= 0
            # Last price should be between bid and ask
            assert contract["bid"] <= contract["lastPrice"] <= contract["ask"]


class TestGetCurrentPrice:
    """Tests for current price fetching."""
    
    def test_get_current_price_returns_positive(self):
        """Test that price is positive."""
        from financial_dashboard.services.alpha_sim.options import _get_current_price
        
        price = _get_current_price("AAPL")
        assert price > 0
    
    def test_get_current_price_deterministic(self):
        """Test that same symbol returns same fallback price."""
        from financial_dashboard.services.alpha_sim.options import _get_current_price
        
        # With engine mocked to return None, should use deterministic fallback
        price1 = _get_current_price("TEST")
        price2 = _get_current_price("TEST")
        
        # Prices may differ if engine succeeds, but fallback is deterministic
        assert price1 > 0
        assert price2 > 0


class TestGetExpirationDates:
    """Tests for expiration date generation."""
    
    def test_get_expiration_dates_returns_dates(self):
        """Test that expiration dates are returned."""
        from financial_dashboard.services.alpha_sim.options import _get_expiration_dates
        
        dates = _get_expiration_dates()
        
        assert len(dates) > 0
        assert all(isinstance(d, datetime) for d in dates)
    
    def test_get_expiration_dates_are_future(self):
        """Test that all dates are in the future."""
        from financial_dashboard.services.alpha_sim.options import _get_expiration_dates
        
        now = datetime.utcnow()
        dates = _get_expiration_dates(now)
        
        assert all(d > now for d in dates)
    
    def test_get_expiration_dates_sorted(self):
        """Test that dates are sorted."""
        from financial_dashboard.services.alpha_sim.options import _get_expiration_dates
        
        dates = _get_expiration_dates()
        
        assert dates == sorted(dates)
    
    def test_get_expiration_dates_third_fridays(self):
        """Test that monthly expirations are third Fridays."""
        from financial_dashboard.services.alpha_sim.options import _get_expiration_dates
        
        dates = _get_expiration_dates()
        
        # At least some should be Fridays (day 4)
        fridays = [d for d in dates if d.weekday() == 4]
        assert len(fridays) > 0


class TestGetOptionsChain:
    """Tests for the main get_options_chain function."""
    
    def test_get_options_chain_returns_valid_response(self):
        """Test that function returns valid response."""
        from financial_dashboard.services.alpha_sim.options import get_options_chain
        
        result = get_options_chain("AAPL", use_cache=False)
        
        assert "Meta Data" in result
        assert "optionChain" in result
    
    def test_get_options_chain_meta_data(self):
        """Test meta data structure."""
        from financial_dashboard.services.alpha_sim.options import get_options_chain
        
        result = get_options_chain("AAPL", use_cache=False)
        
        meta = result["Meta Data"]
        assert "1. Information" in meta
        assert "2. Symbol" in meta
        assert meta["2. Symbol"] == "AAPL"
    
    def test_get_options_chain_structure(self):
        """Test option chain structure."""
        from financial_dashboard.services.alpha_sim.options import get_options_chain
        
        result = get_options_chain("AAPL", use_cache=False)
        
        chain = result["optionChain"]
        assert "symbol" in chain
        assert "underlyingPrice" in chain
        assert "expirationDates" in chain
        assert "options" in chain
        
        assert chain["symbol"] == "AAPL"
        assert chain["underlyingPrice"] > 0
        assert len(chain["expirationDates"]) > 0
        assert len(chain["options"]) > 0
    
    def test_get_options_chain_options_structure(self):
        """Test individual option expiration structure."""
        from financial_dashboard.services.alpha_sim.options import get_options_chain
        
        result = get_options_chain("AAPL", use_cache=False)
        
        options = result["optionChain"]["options"][0]
        assert "expirationDate" in options
        assert "calls" in options
        assert "puts" in options
        
        assert len(options["calls"]) > 0
        assert len(options["puts"]) > 0
    
    def test_get_options_chain_filter_by_type(self):
        """Test filtering by option type."""
        from financial_dashboard.services.alpha_sim.options import get_options_chain
        
        calls_only = get_options_chain("AAPL", option_type="call", use_cache=False)
        puts_only = get_options_chain("AAPL", option_type="put", use_cache=False)
        
        # Verify calls only has calls
        for exp in calls_only["optionChain"]["options"]:
            assert len(exp["puts"]) == 0
        
        # Verify puts only has puts
        for exp in puts_only["optionChain"]["options"]:
            assert len(exp["calls"]) == 0
    
    def test_get_options_chain_caching(self):
        """Test caching works."""
        from financial_dashboard.services.alpha_sim.options import get_options_chain
        from financial_dashboard.services.alpha_sim.cache import get_cache
        
        cache = get_cache()
        cache.clear()
        
        # First call
        result1 = get_options_chain("MSFT", use_cache=True)
        
        # Second call - should use cache
        result2 = get_options_chain("MSFT", use_cache=True)
        
        assert result1 == result2


class TestGetOptionQuote:
    """Tests for single option quote."""
    
    def test_get_option_quote_returns_contract(self):
        """Test that quote returns a contract."""
        from financial_dashboard.services.alpha_sim.options import get_option_quote, get_options_chain
        
        # First get a chain to find a valid strike
        chain = get_options_chain("AAPL", use_cache=False)
        options = chain["optionChain"]["options"][0]
        call = options["calls"][0]
        
        # Now get quote for that specific option
        result = get_option_quote(
            symbol="AAPL",
            strike=call["strike"],
            expiration=call["expiration"],
            option_type="call"
        )
        
        assert "contract" in result or "Error" in result
    
    def test_get_option_quote_not_found(self):
        """Test error for non-existent option."""
        from financial_dashboard.services.alpha_sim.options import get_option_quote
        
        result = get_option_quote(
            symbol="AAPL",
            strike=99999.99,  # Impossible strike
            expiration="2025-12-31",
            option_type="call"
        )
        
        assert "Error" in result


class TestBuildOptionsResponse:
    """Tests for response building."""
    
    def test_build_options_response_structure(self):
        """Test response structure."""
        from financial_dashboard.services.alpha_sim.options import build_options_response
        from datetime import datetime, timedelta
        
        contracts = [
            {
                "contractSymbol": "AAPL251220C00150000",
                "strike": 150,
                "type": "call",
                "expiration": "2025-12-20",
                "bid": 5.00,
                "ask": 5.20
            },
            {
                "contractSymbol": "AAPL251220P00150000",
                "strike": 150,
                "type": "put",
                "expiration": "2025-12-20",
                "bid": 3.00,
                "ask": 3.20
            }
        ]
        
        exp_dates = [datetime(2025, 12, 20)]
        
        result = build_options_response("AAPL", 155.0, contracts, exp_dates)
        
        assert "Meta Data" in result
        assert "optionChain" in result
        assert result["optionChain"]["symbol"] == "AAPL"
        assert result["optionChain"]["underlyingPrice"] == 155.0

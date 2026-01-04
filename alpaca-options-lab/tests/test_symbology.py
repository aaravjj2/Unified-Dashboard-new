"""
Tests for src.data.symbology - OSI Symbol Parser

Tests cover:
- Symbol parsing (standard and edge cases)
- Symbol construction
- Strike normalization
- Validation
- Option chain filtering
"""
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal

import pytest


# Import module under test
from src.data.symbology import (
    OptionSymbol,
    parse_osi_symbol,
    construct_osi_symbol,
    normalize_strike,
    denormalize_strike,
    is_valid_osi_symbol,
    get_expiration_from_symbol,
    get_strike_from_symbol,
    get_option_type_from_symbol,
    filter_chain_by_expiration,
    filter_chain_by_strike_range,
    filter_chain_by_moneyness,
)


class TestOptionSymbolDataclass:
    """Tests for OptionSymbol dataclass."""
    
    def test_option_symbol_creation(self):
        """Test creating an OptionSymbol."""
        symbol = OptionSymbol(
            underlying="AAPL",
            expiration=date(2024, 1, 19),
            strike=Decimal("150.00"),
            option_type="call",
        )
        
        assert symbol.underlying == "AAPL"
        assert symbol.expiration == date(2024, 1, 19)
        assert symbol.strike == Decimal("150.00")
        assert symbol.option_type == "call"
    
    def test_option_symbol_osi_property(self):
        """Test OSI format property."""
        symbol = OptionSymbol(
            underlying="AAPL",
            expiration=date(2024, 1, 19),
            strike=Decimal("150.00"),
            option_type="call",
        )
        
        assert symbol.osi == "AAPL  240119C00150000"
    
    def test_option_symbol_is_call(self):
        """Test is_call property."""
        call = OptionSymbol("AAPL", date(2024, 1, 19), Decimal("150"), "call")
        put = OptionSymbol("AAPL", date(2024, 1, 19), Decimal("150"), "put")
        
        assert call.is_call is True
        assert put.is_call is False
    
    def test_option_symbol_is_put(self):
        """Test is_put property."""
        call = OptionSymbol("AAPL", date(2024, 1, 19), Decimal("150"), "call")
        put = OptionSymbol("AAPL", date(2024, 1, 19), Decimal("150"), "put")
        
        assert call.is_put is False
        assert put.is_put is True
    
    def test_option_symbol_days_to_expiry(self):
        """Test days to expiry calculation."""
        # Use a fixed reference date
        symbol = OptionSymbol(
            underlying="AAPL",
            expiration=date(2024, 6, 21),
            strike=Decimal("150"),
            option_type="call",
        )
        
        dte = symbol.days_to_expiry(reference_date=date(2024, 1, 15))
        assert dte == 158  # 158 days from Jan 15 to June 21


class TestParseOsiSymbol:
    """Tests for parse_osi_symbol function."""
    
    def test_parse_standard_call(self):
        """Test parsing standard call option."""
        symbol = parse_osi_symbol("AAPL  240119C00150000")
        
        assert symbol.underlying == "AAPL"
        assert symbol.expiration == date(2024, 1, 19)
        assert symbol.strike == Decimal("150.00")
        assert symbol.option_type == "call"
    
    def test_parse_standard_put(self):
        """Test parsing standard put option."""
        symbol = parse_osi_symbol("AAPL  240119P00150000")
        
        assert symbol.underlying == "AAPL"
        assert symbol.expiration == date(2024, 1, 19)
        assert symbol.strike == Decimal("150.00")
        assert symbol.option_type == "put"
    
    def test_parse_fractional_strike(self):
        """Test parsing option with fractional strike."""
        symbol = parse_osi_symbol("AAPL  240119C00152500")
        
        assert symbol.strike == Decimal("152.50")
    
    def test_parse_high_strike(self):
        """Test parsing option with high strike price."""
        symbol = parse_osi_symbol("SPY   240119C00500000")
        
        assert symbol.underlying == "SPY"
        assert symbol.strike == Decimal("500.00")
    
    def test_parse_low_strike(self):
        """Test parsing option with low strike price."""
        symbol = parse_osi_symbol("F     240119P00010000")
        
        assert symbol.underlying == "F"
        assert symbol.strike == Decimal("10.00")
    
    def test_parse_single_letter_underlying(self):
        """Test parsing single letter underlying."""
        symbol = parse_osi_symbol("F     240119C00012000")
        
        assert symbol.underlying == "F"
    
    def test_parse_long_underlying(self):
        """Test parsing longer underlying symbols."""
        symbol = parse_osi_symbol("GOOGL 240119C00150000")
        
        assert symbol.underlying == "GOOGL"
    
    def test_parse_without_spaces(self):
        """Test parsing symbol without padding spaces."""
        symbol = parse_osi_symbol("AAPL240119C00150000")
        
        assert symbol.underlying == "AAPL"
        assert symbol.strike == Decimal("150.00")
    
    def test_parse_lowercase_call(self):
        """Test parsing lowercase option type."""
        symbol = parse_osi_symbol("AAPL  240119c00150000")
        
        assert symbol.option_type == "call"
    
    def test_parse_lowercase_put(self):
        """Test parsing lowercase option type."""
        symbol = parse_osi_symbol("AAPL  240119p00150000")
        
        assert symbol.option_type == "put"
    
    def test_parse_invalid_format_raises(self):
        """Test that invalid format raises exception."""
        with pytest.raises(ValueError):
            parse_osi_symbol("INVALID")
    
    def test_parse_invalid_option_type_raises(self):
        """Test that invalid option type raises exception."""
        with pytest.raises(ValueError):
            parse_osi_symbol("AAPL  240119X00150000")


class TestConstructOsiSymbol:
    """Tests for construct_osi_symbol function."""
    
    def test_construct_standard_call(self):
        """Test constructing standard call option symbol."""
        osi = construct_osi_symbol(
            underlying="AAPL",
            expiration=date(2024, 1, 19),
            strike=Decimal("150.00"),
            option_type="call",
        )
        
        assert osi == "AAPL  240119C00150000"
    
    def test_construct_standard_put(self):
        """Test constructing standard put option symbol."""
        osi = construct_osi_symbol(
            underlying="AAPL",
            expiration=date(2024, 1, 19),
            strike=Decimal("150.00"),
            option_type="put",
        )
        
        assert osi == "AAPL  240119P00150000"
    
    def test_construct_fractional_strike(self):
        """Test constructing option with fractional strike."""
        osi = construct_osi_symbol(
            underlying="AAPL",
            expiration=date(2024, 1, 19),
            strike=Decimal("152.50"),
            option_type="call",
        )
        
        assert osi == "AAPL  240119C00152500"
    
    def test_construct_from_float_strike(self):
        """Test constructing with float strike."""
        osi = construct_osi_symbol(
            underlying="AAPL",
            expiration=date(2024, 1, 19),
            strike=150.0,
            option_type="call",
        )
        
        assert osi == "AAPL  240119C00150000"
    
    def test_construct_from_datetime_expiration(self):
        """Test constructing with datetime expiration."""
        osi = construct_osi_symbol(
            underlying="AAPL",
            expiration=datetime(2024, 1, 19, 16, 0),
            strike=Decimal("150.00"),
            option_type="call",
        )
        
        assert osi == "AAPL  240119C00150000"
    
    def test_construct_short_underlying(self):
        """Test constructing with short underlying."""
        osi = construct_osi_symbol(
            underlying="F",
            expiration=date(2024, 1, 19),
            strike=Decimal("12.00"),
            option_type="put",
        )
        
        assert osi == "F     240119P00012000"
    
    def test_construct_uppercase_option_type(self):
        """Test constructing with uppercase option type."""
        osi = construct_osi_symbol(
            underlying="AAPL",
            expiration=date(2024, 1, 19),
            strike=Decimal("150.00"),
            option_type="CALL",
        )
        
        assert osi == "AAPL  240119C00150000"


class TestNormalizeStrike:
    """Tests for strike normalization functions."""
    
    def test_normalize_integer_strike(self):
        """Test normalizing integer strike."""
        result = normalize_strike(150)
        assert result == 150000
    
    def test_normalize_decimal_strike(self):
        """Test normalizing decimal strike."""
        result = normalize_strike(Decimal("152.50"))
        assert result == 152500
    
    def test_normalize_float_strike(self):
        """Test normalizing float strike."""
        result = normalize_strike(152.50)
        assert result == 152500
    
    def test_denormalize_strike(self):
        """Test denormalizing strike."""
        result = denormalize_strike(152500)
        assert result == Decimal("152.50")
    
    def test_roundtrip_strike(self):
        """Test roundtrip normalization."""
        original = Decimal("152.50")
        normalized = normalize_strike(original)
        denormalized = denormalize_strike(normalized)
        
        assert denormalized == original


class TestValidation:
    """Tests for symbol validation."""
    
    def test_valid_call_symbol(self):
        """Test validating valid call symbol."""
        assert is_valid_osi_symbol("AAPL  240119C00150000") is True
    
    def test_valid_put_symbol(self):
        """Test validating valid put symbol."""
        assert is_valid_osi_symbol("AAPL  240119P00150000") is True
    
    def test_valid_compact_symbol(self):
        """Test validating compact symbol."""
        assert is_valid_osi_symbol("AAPL240119C00150000") is True
    
    def test_invalid_too_short(self):
        """Test rejecting too short symbol."""
        assert is_valid_osi_symbol("AAPL") is False
    
    def test_invalid_option_type(self):
        """Test rejecting invalid option type."""
        assert is_valid_osi_symbol("AAPL  240119X00150000") is False
    
    def test_invalid_strike_format(self):
        """Test rejecting invalid strike format."""
        assert is_valid_osi_symbol("AAPL  240119C00ABCDEF") is False


class TestExtractorFunctions:
    """Tests for individual field extractor functions."""
    
    def test_get_expiration_from_symbol(self):
        """Test extracting expiration date."""
        exp = get_expiration_from_symbol("AAPL  240119C00150000")
        assert exp == date(2024, 1, 19)
    
    def test_get_strike_from_symbol(self):
        """Test extracting strike price."""
        strike = get_strike_from_symbol("AAPL  240119C00152500")
        assert strike == Decimal("152.50")
    
    def test_get_option_type_call(self):
        """Test extracting call option type."""
        opt_type = get_option_type_from_symbol("AAPL  240119C00150000")
        assert opt_type == "call"
    
    def test_get_option_type_put(self):
        """Test extracting put option type."""
        opt_type = get_option_type_from_symbol("AAPL  240119P00150000")
        assert opt_type == "put"


class TestChainFilters:
    """Tests for option chain filtering functions."""
    
    @pytest.fixture
    def sample_chain(self):
        """Sample option chain for testing."""
        return [
            OptionSymbol("AAPL", date(2024, 1, 19), Decimal("145"), "call"),
            OptionSymbol("AAPL", date(2024, 1, 19), Decimal("150"), "call"),
            OptionSymbol("AAPL", date(2024, 1, 19), Decimal("155"), "call"),
            OptionSymbol("AAPL", date(2024, 1, 26), Decimal("145"), "call"),
            OptionSymbol("AAPL", date(2024, 1, 26), Decimal("150"), "call"),
            OptionSymbol("AAPL", date(2024, 1, 26), Decimal("155"), "call"),
            OptionSymbol("AAPL", date(2024, 1, 19), Decimal("145"), "put"),
            OptionSymbol("AAPL", date(2024, 1, 19), Decimal("150"), "put"),
            OptionSymbol("AAPL", date(2024, 1, 19), Decimal("155"), "put"),
        ]
    
    def test_filter_by_expiration(self, sample_chain):
        """Test filtering chain by expiration."""
        filtered = filter_chain_by_expiration(
            sample_chain,
            expiration=date(2024, 1, 19),
        )
        
        assert len(filtered) == 6
        for symbol in filtered:
            assert symbol.expiration == date(2024, 1, 19)
    
    def test_filter_by_strike_range(self, sample_chain):
        """Test filtering chain by strike range."""
        filtered = filter_chain_by_strike_range(
            sample_chain,
            min_strike=Decimal("148"),
            max_strike=Decimal("152"),
        )
        
        assert len(filtered) == 3
        for symbol in filtered:
            assert Decimal("148") <= symbol.strike <= Decimal("152")
    
    def test_filter_by_moneyness_atm(self, sample_chain):
        """Test filtering chain for ATM options."""
        filtered = filter_chain_by_moneyness(
            sample_chain,
            spot_price=150.0,
            max_delta=0.02,  # Within 2% of ATM
        )
        
        # Should only return the 150 strike options
        assert len(filtered) == 3
        for symbol in filtered:
            assert symbol.strike == Decimal("150")

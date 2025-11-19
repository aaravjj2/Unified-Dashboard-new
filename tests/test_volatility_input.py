"""
Tests for Custom Ticker Input in Volatility Lab

RED → GREEN TDD for ticker validation and parsing functionality.
Tests valid, invalid, and mixed ticker inputs.
"""

import pytest
from financial_dashboard.tabs.volatility_lab import validate_and_parse_tickers


class TestTickerValidation:
    """Test suite for validate_and_parse_tickers function"""
    
    def test_valid_tickers_single(self):
        """Test single valid ticker"""
        valid, invalid = validate_and_parse_tickers("AAPL")
        assert valid == ['AAPL']
        assert invalid == []
    
    def test_valid_tickers_multiple(self):
        """Test multiple valid tickers"""
        valid, invalid = validate_and_parse_tickers("AAPL,MSFT,SPY")
        assert valid == ['AAPL', 'MSFT', 'SPY']
        assert invalid == []
    
    def test_valid_tickers_lowercase(self):
        """Test lowercase tickers are converted to uppercase"""
        valid, invalid = validate_and_parse_tickers("aapl,msft,spy")
        assert valid == ['AAPL', 'MSFT', 'SPY']
        assert invalid == []
    
    def test_valid_tickers_with_whitespace(self):
        """Test tickers with extra whitespace"""
        valid, invalid = validate_and_parse_tickers(" AAPL , MSFT  ,SPY ")
        assert valid == ['AAPL', 'MSFT', 'SPY']
        assert invalid == []
    
    def test_valid_ticker_with_hyphen(self):
        """Test special symbols with hyphen (e.g., BRK-B)"""
        valid, invalid = validate_and_parse_tickers("BRK-B,SPY")
        assert valid == ['BRK-B', 'SPY']
        assert invalid == []
    
    def test_invalid_ticker_too_long(self):
        """Test ticker longer than 5 characters"""
        valid, invalid = validate_and_parse_tickers("TOOLONG")
        assert valid == []
        assert invalid == ['TOOLONG']
    
    def test_invalid_ticker_empty(self):
        """Test empty ticker symbol"""
        valid, invalid = validate_and_parse_tickers("")
        assert valid == []
        assert invalid == []
    
    def test_invalid_ticker_numeric(self):
        """Test numeric ticker (should be invalid)"""
        valid, invalid = validate_and_parse_tickers("123")
        assert valid == []
        assert invalid == ['123']
    
    def test_invalid_ticker_special_chars(self):
        """Test ticker with invalid special characters"""
        valid, invalid = validate_and_parse_tickers("AAPL$")
        assert valid == []
        assert invalid == ['AAPL$']
    
    def test_mixed_valid_invalid(self):
        """Test mixture of valid and invalid tickers"""
        valid, invalid = validate_and_parse_tickers("AAPL,123,MSFT,TOOLONG,SPY")
        assert valid == ['AAPL', 'MSFT', 'SPY']
        assert invalid == ['123', 'TOOLONG']
    
    def test_empty_string_input(self):
        """Test empty string input"""
        valid, invalid = validate_and_parse_tickers("")
        assert valid == []
        assert invalid == []
    
    def test_none_input(self):
        """Test None input"""
        valid, invalid = validate_and_parse_tickers(None)
        assert valid == []
        assert invalid == []
    
    def test_whitespace_only(self):
        """Test whitespace-only input"""
        valid, invalid = validate_and_parse_tickers("   ,  ,  ")
        assert valid == []
        assert invalid == []
    
    def test_one_char_ticker(self):
        """Test single character ticker (valid)"""
        valid, invalid = validate_and_parse_tickers("F")
        assert valid == ['F']
        assert invalid == []
    
    def test_five_char_ticker(self):
        """Test 5-character ticker (boundary case - valid)"""
        valid, invalid = validate_and_parse_tickers("GOOGL")
        assert valid == ['GOOGL']
        assert invalid == []
    
    def test_mixed_case_with_numbers(self):
        """Test mixed valid and invalid with numbers"""
        valid, invalid = validate_and_parse_tickers("aapl,12345,msft")
        assert valid == ['AAPL', 'MSFT']
        assert invalid == ['12345']


class TestTickerInputIntegration:
    """Integration tests for ticker input in callback context"""
    
    def test_ticker_validation_integration(self):
        """Test that validation integrates properly with callback logic"""
        # Simulate callback receiving custom ticker input
        ticker_input = "AAPL,INVALID123,MSFT"
        valid, invalid = validate_and_parse_tickers(ticker_input)
        
        assert len(valid) == 2
        assert 'AAPL' in valid
        assert 'MSFT' in valid
        assert len(invalid) == 1
        assert 'INVALID123' in invalid
    
    def test_common_tickers(self):
        """Test validation with commonly used tickers"""
        common = "SPY,QQQ,AAPL,MSFT,NVDA,TSLA,GOOGL,AMZN,META"
        valid, invalid = validate_and_parse_tickers(common)
        
        assert len(valid) == 9
        assert invalid == []
        assert set(valid) == {'SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL', 'AMZN', 'META'}
    
    def test_edge_case_all_invalid(self):
        """Test when all tickers are invalid"""
        all_invalid = "123,456,789,@@@"
        valid, invalid = validate_and_parse_tickers(all_invalid)
        
        assert valid == []
        assert len(invalid) == 4


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

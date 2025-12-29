import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from financial_dashboard.services.bot_engine.alpha_vantage import AlphaVantageClient

class TestBotEngine(unittest.TestCase):
    def test_no_alpha_vantage_dependency(self):
        """Test that the AlphaVantageClient does not actually use Alpha Vantage URL"""
        with open('financial_dashboard/services/bot_engine/alpha_vantage.py', 'r') as f:
            code = f.read()
        self.assertNotIn('www.alphavantage.co', code, "Alpha Vantage API URL found in code")

    @patch('financial_dashboard.services.bot_engine.alpha_vantage.yf.Ticker')
    def test_rsi_calculation_source(self, mock_ticker):
        """Test that RSI is calculated using local yfinance data"""
        # Mock yfinance data with DatetimeIndex
        dates = [datetime.now() - timedelta(days=i) for i in range(30)]
        dates.reverse()
        mock_hist = pd.DataFrame({'Close': [100 + i for i in range(30)]}, index=dates)
        mock_ticker.return_value.history.return_value = mock_hist
        
        client = AlphaVantageClient()
        rsi = client.get_rsi('AAPL')
        
        self.assertEqual(rsi.get('source'), 'yfinance_local')
        self.assertIn('latest_value', rsi)

    @patch('financial_dashboard.services.bot_engine.alpha_vantage.yf.Ticker')
    def test_macd_calculation_source(self, mock_ticker):
        """Test that MACD is calculated using local yfinance data"""
        # Mock yfinance data with DatetimeIndex
        dates = [datetime.now() - timedelta(days=i) for i in range(40)]
        dates.reverse()
        mock_hist = pd.DataFrame({'Close': [100 + i for i in range(40)]}, index=dates)
        mock_ticker.return_value.history.return_value = mock_hist
        
        client = AlphaVantageClient()
        macd = client.get_macd('SPY')
        
        self.assertEqual(macd.get('source'), 'yfinance_local')
        self.assertIn('latest', macd)
        self.assertIn('macd', macd['latest'])
        self.assertIn('signal', macd['latest'])
        self.assertIn('histogram', macd['latest'])

if __name__ == '__main__':
    unittest.main()

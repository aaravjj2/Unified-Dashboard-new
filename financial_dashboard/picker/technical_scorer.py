"""
Technical Scorer - Analyze technical indicators.
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict

logger = logging.getLogger(__name__)


class TechnicalScorer:
    """Score stocks based on technical indicators."""
    
    def __init__(self):
        self.weight = 0.15  # 15% weight in ensemble
    
    def score(self, ticker: str) -> float:
        """
        Calculate technical score for a stock (0-100).
        
        Factors:
        - RSI (30%) - 50-70 is best
        - MACD signal (30%) - positive crossover is best
        - Price vs MA50/MA200 (40%) - above both is best
        
        Returns:
            Score 0-100 (higher is better)
        """
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty or len(hist) < 50:
                logger.warning(f"{ticker}: Insufficient data for technical")
                return 50.0
            
            close = hist['Close']
            current_price = close.iloc[-1]
            
            # RSI (Relative Strength Index)
            rsi = self._calculate_rsi(close)
            # Map RSI: 30-40=good buy, 50-60=neutral, 70-80=overbought
            # Best score around RSI=60
            if rsi < 30:
                rsi_score = 40  # Oversold
            elif rsi < 70:
                # Peak at RSI=60
                rsi_score = 50 + (10 - abs(60 - rsi)) * 5
            else:
                rsi_score = max(0, 100 - (rsi - 70) * 3)  # Overbought penalty
            
            # MACD
            macd_line, signal_line = self._calculate_macd(close)
            macd_diff = macd_line - signal_line
            
            # Positive MACD = bullish, negative = bearish
            # Map -5 to +5 to 0-100 score
            macd_score = max(0, min(100, ((macd_diff + 5) / 10) * 100))
            
            # Moving Averages
            ma50 = close.rolling(50).mean().iloc[-1]
            ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else ma50
            
            # Score based on position relative to MAs
            above_ma50 = current_price > ma50
            above_ma200 = current_price > ma200
            
            if above_ma50 and above_ma200:
                ma_score = 100  # Strong uptrend
            elif above_ma50:
                ma_score = 70  # Short-term uptrend
            elif above_ma200:
                ma_score = 40  # Long-term support
            else:
                ma_score = 20  # Downtrend
            
            # Weighted average
            total_score = (
                rsi_score * 0.30 +
                macd_score * 0.30 +
                ma_score * 0.40
            )
            
            logger.info(f"{ticker} technical: {total_score:.1f} (RSI:{rsi:.1f}, MACD:{macd_diff:.2f}, MA:{above_ma50}/{above_ma200})")
            
            return round(total_score, 1)
            
        except Exception as e:
            logger.error(f"Technical scoring error for {ticker}: {e}")
            return 50.0
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI indicator."""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.iloc[-1]
        except:
            return 50.0
    
    def _calculate_macd(self, prices: pd.Series) -> tuple:
        """Calculate MACD indicator."""
        try:
            exp1 = prices.ewm(span=12, adjust=False).mean()
            exp2 = prices.ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            
            return macd.iloc[-1], signal.iloc[-1]
        except:
            return 0.0, 0.0
    
    def get_details(self, ticker: str) -> Dict:
        """Get detailed technical metrics."""
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty:
                return {}
            
            close = hist['Close']
            current_price = close.iloc[-1]
            
            rsi = self._calculate_rsi(close)
            macd_line, signal_line = self._calculate_macd(close)
            ma50 = close.rolling(50).mean().iloc[-1]
            ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else ma50
            
            details = {
                'current_price': current_price,
                'rsi': rsi,
                'macd': macd_line - signal_line,
                'ma50': ma50,
                'ma200': ma200,
                'above_ma50': current_price > ma50,
                'above_ma200': current_price > ma200
            }
            
            return details
            
        except:
            return {}

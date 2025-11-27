"""
Momentum Scorer - Analyze price momentum and trends.
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict

logger = logging.getLogger(__name__)


class MomentumScorer:
    """Score stocks based on momentum indicators."""
    
    def __init__(self):
        self.weight = 0.35  # 35% weight in ensemble
    
    def score(self, ticker: str) -> float:
        """
        Calculate momentum score for a stock (0-100).
        
        Factors:
        - 1-month return (30%)
        - 3-month return (30%)
        - 6-month return (20%)
        - Relative strength vs SPY (20%)
        
        Returns:
            Score 0-100 (higher is better)
        """
        try:
            import yfinance as yf
            
            # Fetch historical data
            stock = yf.Ticker(ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty or len(hist) < 30:
                logger.warning(f"{ticker}: Insufficient data for momentum")
                return 50.0  # Neutral score
            
            current_price = hist['Close'].iloc[-1]
            
            # Calculate returns
            returns = {}
            periods = {'1m': 21, '3m': 63, '6m': 126}
            
            for period, days in periods.items():
                if len(hist) >= days:
                    past_price = hist['Close'].iloc[-days]
                    returns[period] = ((current_price - past_price) / past_price) * 100
                else:
                    returns[period] = 0
            
            # Calculate relative strength vs SPY
            try:
                spy = yf.Ticker('SPY')
                spy_hist = spy.history(start=start_date, end=end_date)
                
                if not spy_hist.empty and len(spy_hist) >= 63:
                    spy_current = spy_hist['Close'].iloc[-1]
                    spy_past = spy_hist['Close'].iloc[-63]
                    spy_return = ((spy_current - spy_past) / spy_past) * 100
                    
                    rel_strength = returns['3m'] - spy_return
                else:
                    rel_strength = 0
            except:
                rel_strength = 0
            
            # Normalize scores to 0-100
            # Assume -50% to +100% return range maps to 0-100 score
            def normalize_return(ret, min_ret=-50, max_ret=100):
                normalized = ((ret - min_ret) / (max_ret - min_ret)) * 100
                return max(0, min(100, normalized))
            
            score_1m = normalize_return(returns['1m'])
            score_3m = normalize_return(returns['3m'])
            score_6m = normalize_return(returns['6m'])
            score_rel = normalize_return(rel_strength, min_ret=-30, max_ret=30)
            
            # Weighted average
            total_score = (
                score_1m * 0.30 +
                score_3m * 0.30 +
                score_6m * 0.20 +
                score_rel * 0.20
            )
            
            logger.info(f"{ticker} momentum: {total_score:.1f} (1m:{returns['1m']:.1f}%, 3m:{returns['3m']:.1f}%, 6m:{returns['6m']:.1f}%)")
            
            return round(total_score, 1)
            
        except Exception as e:
            logger.error(f"Momentum scoring error for {ticker}: {e}")
            return 50.0  # Neutral score on error
    
    def get_details(self, ticker: str) -> Dict:
        """Get detailed momentum metrics."""
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty:
                return {}
            
            current_price = hist['Close'].iloc[-1]
            
            # Calculate all metrics
            details = {
                'current_price': current_price,
                '1m_return': 0,
                '3m_return': 0,
                '6m_return': 0,
                'rel_strength_vs_spy': 0
            }
            
            periods = {'1m_return': 21, '3m_return': 63, '6m_return': 126}
            
            for key, days in periods.items():
                if len(hist) >= days:
                    past_price = hist['Close'].iloc[-days]
                    details[key] = ((current_price - past_price) / past_price) * 100
            
            return details
            
        except:
            return {}

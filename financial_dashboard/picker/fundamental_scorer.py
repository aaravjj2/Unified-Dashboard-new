"""
Fundamental Scorer - Analyze fundamental metrics.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class FundamentalScorer:
    """Score stocks based on fundamental metrics."""
    
    def __init__(self):
        self.weight = 0.25  # 25% weight in ensemble
    
    def score(self, ticker: str) -> float:
        """
        Calculate fundamental score for a stock (0-100).
        
        Factors:
        - P/E ratio (25%) - lower is better
        - Revenue growth (25%) - higher is better
        - Profit margin (20%) - higher is better
        - ROE (15%) - higher is better
        - Debt/Equity (15%) - lower is better
        
        Returns:
            Score 0-100 (higher is better)
        """
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # P/E ratio (lower is better, but not negative)
            pe_ratio = info.get('trailingPE') or info.get('forwardPE') or 30
            # Map P/E of 0-60 to score of 100-0 (lower P/E = higher score)
            pe_score = max(0, min(100, 100 - (pe_ratio / 60) * 100))
            
            # Revenue growth
            revenue_growth = info.get('revenueGrowth', 0) * 100  # Convert to percentage
            # Map -10% to +40% growth to 0-100 score
            growth_score = max(0, min(100, ((revenue_growth + 10) / 50) * 100))
            
            # Profit margin
            profit_margin = info.get('profitMargins', 0) * 100
            # Map 0% to 30% margin to 0-100 score
            margin_score = min(100, (profit_margin / 30) * 100)
            
            # ROE (Return on Equity)
            roe = info.get('returnOnEquity', 0) * 100
            # Map 0% to 30% ROE to 0-100 score
            roe_score = min(100, (roe / 30) * 100)
            
            # Debt/Equity ratio (lower is better)
            debt_equity = info.get('debtToEquity', 100) / 100  # Convert to ratio
            # Map 0-2 D/E to score of 100-0
            de_score = max(0, min(100, 100 - (debt_equity / 2) * 100))
            
            # Weighted average
            total_score = (
                pe_score * 0.25 +
                growth_score * 0.25 +
                margin_score * 0.20 +
                roe_score * 0.15 +
                de_score * 0.15
            )
            
            logger.info(f"{ticker} fundamental: {total_score:.1f} (PE:{pe_ratio:.1f}, Growth:{revenue_growth:.1f}%, Margin:{profit_margin:.1f}%)")
            
            return round(total_score, 1)
            
        except Exception as e:
            logger.error(f"Fundamental scoring error for {ticker}: {e}")
            return 50.0  # Neutral score on error
    
    def get_details(self, ticker: str) -> Dict:
        """Get detailed fundamental metrics."""
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            info = stock.info
            
            details = {
                'pe_ratio': info.get('trailingPE') or info.get('forwardPE', 0),
                'revenue_growth': info.get('revenueGrowth', 0) * 100,
                'profit_margin': info.get('profitMargins', 0) * 100,
                'roe': info.get('returnOnEquity', 0) * 100,
                'debt_equity': info.get('debtToEquity', 0) / 100
            }
            
            return details
            
        except:
            return {}

"""
Stock Universe - Define and filter stock universes.
"""

import pandas as pd
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class StockUniverse:
    """Manage stock universes for picking."""
    
    # S&P 500 top holdings (simplified for MVP - full list can be fetched from Wikipedia)
    SP500_TOP_100 = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.B', 'UNH', 'JNJ',
        'V', 'WMT', 'JPM', 'XOM', 'PG', 'MA', 'HD', 'CVX', 'MRK', 'ABBV',
        'KO', 'PEP', 'COST', 'AVGO', 'TMO', 'MCD', 'CSCO', 'ACN', 'LLY', 'DHR',
        'ABT', 'VZ', 'ADBE', 'NKE', 'CRM', 'NFLX', 'TXN', 'CMCSA', 'DIS', 'ORCL',
        'AMD', 'QCOM', 'INTC', 'PM', 'UNP', 'BMY', 'HON', 'NEE', 'RTX', 'INTU',
        'LOW', 'SPGI', 'UPS', 'CAT', 'BA', 'SBUX', 'GS', 'AMAT', 'DE', 'LMT',
        'BLK', 'AXP', 'BKNG', 'GILD', 'ADI', 'MDLZ', 'MMM', 'SYK', 'TJX', 'ADP',
        'CVS', 'CI', 'VRTX', 'ZTS', 'ISRG', 'PLD', 'AMT', 'MO', 'REGN', 'CB',
        'DUK', 'SO', 'SCHW', 'TMUS', 'PGR', 'COP', 'BSX', 'ETN', 'EQIX', 'ITW',
        'MMC', 'APD', 'SLB', 'EOG', 'WM', 'ICE', 'GE', 'CL', 'PSA', 'FDX'
    ]
    
    # Tech-heavy NASDAQ stocks
    NASDAQ_TOP_50 = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'ASML', 'COST',
        'NFLX', 'AMD', 'QCOM', 'INTC', 'CSCO', 'ADBE', 'INTU', 'PYPL', 'CMCSA', 'TXN',
        'AMAT', 'MU', 'SBUX', 'GILD', 'BKNG', 'ISRG', 'ADI', 'REGN', 'VRTX', 'LRCX',
        'MRNA', 'KLAC', 'SNPS', 'CDNS', 'MRVL', 'PANW', 'CRWD', 'FTNT', 'WDAY', 'ZS',
        'DDOG', 'SNOW', 'NET', 'OKTA', 'DOCU', 'TEAM', 'ZM', 'ABNB', 'UBER', 'LYFT'
    ]

    # Mid-Cap Stocks (S&P 400 / Russell 1000 Mid representative)
    MID_CAP_50 = [
        'HUBB', 'DOV', 'TXT', 'MAS', 'IX', 'BALL', 'DRI', 'POOL', 'WAT', 'EXPD',
        'BRO', 'ATO', 'CNP', 'CMS', 'PFG', 'HOLX', 'COO', 'DGX', 'LH', 'STE',
        'RMD', 'TECH', 'BIO', 'PODD', 'ENTG', 'WOLF', 'LSCC', 'MPWR', 'TRMB', 'PTC',
        'TYL', 'FICO', 'ANSS', 'CDW', 'KEYS', 'LDOS', 'WAB', 'GME', 'AMC', 'PLTR',
        'DKNG', 'RBLX', 'U', 'AFRM', 'HOOD', 'COIN', 'MSTR', 'MARA', 'RIOT', 'CLSK'
    ]
    
    @classmethod
    def get_sp500(cls, limit: Optional[int] = None) -> List[str]:
        """Get S&P 500 tickers (top holdings for MVP)."""
        tickers = cls.SP500_TOP_100.copy()
        if limit:
            tickers = tickers[:limit]
        logger.info(f"Retrieved {len(tickers)} S&P 500 tickers")
        return tickers
    
    @classmethod
    def get_nasdaq100(cls, limit: Optional[int] = None) -> List[str]:
        """Get NASDAQ 100 tickers."""
        tickers = cls.NASDAQ_TOP_50.copy()
        if limit:
            tickers = tickers[:limit]
        logger.info(f"Retrieved {len(tickers)} NASDAQ tickers")
        return tickers

    @classmethod
    def get_midcap(cls, limit: Optional[int] = None) -> List[str]:
        """Get Mid-Cap tickers."""
        tickers = cls.MID_CAP_50.copy()
        if limit:
            tickers = tickers[:limit]
        logger.info(f"Retrieved {len(tickers)} Mid-Cap tickers")
        return tickers
    
    @classmethod
    def get_combined_universe(cls) -> List[str]:
        """Get combined universe (S&P 500 + NASDAQ, deduplicated)."""
        combined = list(set(cls.SP500_TOP_100 + cls.NASDAQ_TOP_50))
        logger.info(f"Retrieved {len(combined)} unique tickers from combined universe")
        return combined

    @classmethod
    def get_broad_universe(cls) -> List[str]:
        """Get broad universe (S&P 500 + NASDAQ + Mid-Cap, deduplicated)."""
        combined = list(set(cls.SP500_TOP_100 + cls.NASDAQ_TOP_50 + cls.MID_CAP_50))
        logger.info(f"Retrieved {len(combined)} unique tickers from broad universe (Large + Tech + Mid)")
        return combined
    
    @classmethod
    def filter_by_market_cap(cls, tickers: List[str], min_cap: float = 500_000_000) -> List[str]:
        """
        Filter tickers by minimum market cap.
        
        Args:
            tickers: List of tickers to filter
            min_cap: Minimum market cap in dollars (default: $500M)
            
        Returns:
            Filtered list of tickers
        """
        try:
            import yfinance as yf
            
            filtered = []
            for ticker in tickers:
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    market_cap = info.get('marketCap', 0)
                    
                    if market_cap >= min_cap:
                        filtered.append(ticker)
                except:
                    # If can't fetch data, skip ticker
                    logger.warning(f"Could not fetch market cap for {ticker}")
                    continue
            
            logger.info(f"Filtered {len(tickers)} tickers to {len(filtered)} by market cap >= ${min_cap:,.0f}")
            return filtered
            
        except Exception as e:
            logger.error(f"Market cap filter error: {e}")
            # Return original list if filtering fails
            return tickers
    
    @classmethod
    def filter_by_liquidity(cls, tickers: List[str], min_volume: int = 500_000) -> List[str]:
        """
        Filter tickers by minimum average daily volume.
        
        Args:
            tickers: List of tickers to filter
            min_volume: Minimum avg daily volume (default: 500K shares)
            
        Returns:
            Filtered list of tickers
        """
        try:
            import yfinance as yf
            
            filtered = []
            for ticker in tickers:
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    avg_volume = info.get('averageVolume', 0)
                    
                    if avg_volume >= min_volume:
                        filtered.append(ticker)
                except:
                    logger.warning(f"Could not fetch volume for {ticker}")
                    continue
            
            logger.info(f"Filtered {len(tickers)} tickers to {len(filtered)} by volume >= {min_volume:,}")
            return filtered
            
        except Exception as e:
            logger.error(f"Liquidity filter error: {e}")
            return tickers

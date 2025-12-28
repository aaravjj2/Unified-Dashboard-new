"""
Helper to get stock screening universe (S&P 500 + NASDAQ 100 top stocks)
"""

# Common high-volume stocks for screening
SCREENING_UNIVERSE = [
    # Tech Giants
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'INTC', 'NFLX',
    # Finance
    'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'V', 'MA', 'PYPL',
    # Healthcare
    'JNJ', 'UNH', 'PFE', 'ABBV', 'TMO', 'ABT', 'DHR', 'BMY', 'LLY', 'MRK',
    # Consumer
    'WMT', 'HD', 'PG', 'KO', 'PEP', 'COST', 'NKE', 'MCD', 'SBUX', 'DIS',
    # Energy
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO',
    # Industrials
    'BA', 'CAT', 'GE', 'HON', 'UPS', 'LMT', 'RTX', 'MMM', 'DE',
    # More Tech
    'ORCL', 'CRM', 'ADBE', 'CSCO', 'AVGO', 'QCOM', 'TXN', 'NOW', 'SNOW', 'PLTR',
    # Communication
    'T', 'VZ', 'CMCSA', 'TMUS', 'CHTR',
    # Retail/E-commerce
    'TGT', 'LOW', 'BKNG', 'ABNB', 'EBAY', 'ETSY',
    # Biotech
    'GILD', 'AMGN', 'REGN', 'VRTX', 'BIIB', 'MRNA',
    # Semiconductors
    'TSM', 'ASML', 'AMAT', 'LRCX', 'MU', 'MRVL',
    # Automotive
    'F', 'GM', 'RIVN', 'LCID',
    # Real Estate/REITs
    'AMT', 'PLD', 'CCI', 'EQIX', 'SPG',
    # More stocks for diversity
    'BRK.B', 'SHOP', 'SQ', 'DOCU', 'ZM', 'UBER', 'LYFT', 'DASH', 'COIN', 'HOOD',
    'SOFI', 'AFRM', 'RBLX', 'U', 'DKNG', 'PENN', 'FUBO', 'ROKU', 'SPOT'
]

print(f"Screening universe contains {len(SCREENING_UNIVERSE)} tickers")

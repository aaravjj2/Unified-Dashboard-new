import re

def normalize_ticker(t):
    """Normalize ticker: uppercase, strip common suffixes, punctuation, and handle option symbols."""
    t = str(t).upper().strip()
    
    print(f"Processing: {t}")
    
    # Handle option symbols (e.g., GOOGL230616C00120000 -> GOOGL)
    # Simple heuristic: if it contains digits and is long, take the alpha prefix
    if len(t) > 6 and any(c.isdigit() for c in t):
        # Try to match standard OCC format: Root + 6 digits (YYMMDD)
        # Regex explanation:
        # ^([A-Z]+)   : Start with 1 or more uppercase letters (Group 1: Root)
        # \d{6}       : Followed by exactly 6 digits (Date)
        # [CP]        : Followed by 'C' or 'P' (Call/Put)
        # \d+$        : Followed by 1 or more digits (Strike) to end
        match = re.match(r'^([A-Z]+)\d{6}[CP]\d+$', t)
        if match:
            print(f"  Matched OCC format: {match.group(1)}")
            return match.group(1)
        else:
            print("  Did NOT match OCC format")
        
        # Fallback: just take the leading alpha characters
        match_alpha = re.match(r'^([A-Z]+)', t)
        if match_alpha:
            print(f"  Matched fallback alpha: {match_alpha.group(1)}")
            return match_alpha.group(1)

    # Remove common suffixes
    for suffix in ['.A', '.B', '-A', '-B', ' US', ' EQUITY']:
        if t.endswith(suffix):
            t = t[:-len(suffix)]
    
    return t.replace('-', '').replace('.', '').replace(' ', '')

# Test cases from diagnostic info
tickers = [
    "GLD260918C00380000",
    "NVDA250620C00150000",
    "AAPL",
    "BRK.B",
    "GOOGL"
]

for t in tickers:
    print(f"Result: {normalize_ticker(t)}")
    print("-" * 20)

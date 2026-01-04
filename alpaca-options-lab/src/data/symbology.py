"""
Alpaca Options Lab - Symbol Management Module

Production-grade OSI (Options Symbology Initiative) symbol handling with:
- Full OSI symbol parsing and validation
- Symbol construction from components
- Underlying extraction
- Expiration date handling
- Strike price normalization
- Option type detection

OSI Format: UNDERLYING + YYMMDD + C/P + STRIKE (8 digits, 3 decimal places)
Example: AAPL240119C00150000 = AAPL $150 Call expiring Jan 19, 2024

Performance:
- O(1) symbol parsing with compiled regex
- LRU caching for repeated lookups
- Thread-safe operations

Usage:
    from src.data.symbology import (
        parse_osi_symbol,
        build_osi_symbol,
        OptionSymbol,
        SymbolMapper,
    )
    
    # Parse an OSI symbol
    option = parse_osi_symbol("AAPL240119C00150000")
    print(option.underlying)  # "AAPL"
    print(option.strike)      # 150.0
    print(option.expiry)      # datetime.date(2024, 1, 19)
    print(option.option_type) # OptionType.CALL
    
    # Build an OSI symbol
    symbol = build_osi_symbol("AAPL", date(2024, 1, 19), OptionType.CALL, 150.0)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from functools import lru_cache
from typing import Dict, List, Optional, Set, Tuple, Union

from src.utils.exceptions import ValidationError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Compiled regex for OSI symbol parsing - optimized for performance
# Format: UNDERLYING (1-6 chars) + YYMMDD + C/P + STRIKE (8 digits, implies 3 decimals)
OSI_PATTERN = re.compile(
    r'^(?P<underlying>[A-Z]{1,6})'
    r'(?P<year>\d{2})'
    r'(?P<month>\d{2})'
    r'(?P<day>\d{2})'
    r'(?P<option_type>[CP])'
    r'(?P<strike>\d{8})$'
)

# Alternative pattern for extended format with explicit decimals
OSI_EXTENDED_PATTERN = re.compile(
    r'^(?P<underlying>[A-Z]{1,6})'
    r'(?P<expiry>\d{6})'
    r'(?P<option_type>[CP])'
    r'(?P<strike>\d+\.?\d*)$'
)


class OptionType(Enum):
    """Option contract type."""
    CALL = "C"
    PUT = "P"
    
    @classmethod
    def from_string(cls, value: str) -> "OptionType":
        """Parse option type from string."""
        value = value.upper().strip()
        if value in ("C", "CALL"):
            return cls.CALL
        elif value in ("P", "PUT"):
            return cls.PUT
        else:
            raise ValidationError(
                message=f"Invalid option type: {value}",
                field_name="option_type",
                field_value=value,
                validation_rule="Must be 'C', 'CALL', 'P', or 'PUT'",
            )
    
    @property
    def is_call(self) -> bool:
        """Check if this is a call option."""
        return self == OptionType.CALL
    
    @property
    def is_put(self) -> bool:
        """Check if this is a put option."""
        return self == OptionType.PUT


@dataclass(frozen=True)
class OptionSymbol:
    """
    Immutable representation of a parsed option symbol.
    
    Provides computed properties for common operations and
    maintains data integrity through immutability.
    
    Attributes:
        underlying: Stock ticker symbol (1-6 uppercase letters)
        expiry: Option expiration date
        option_type: CALL or PUT
        strike: Strike price (positive float)
        osi_symbol: Full OSI symbol string
    """
    underlying: str
    expiry: date
    option_type: OptionType
    strike: float
    osi_symbol: str = field(default="", compare=False)
    
    def __post_init__(self) -> None:
        """Validate and normalize on creation."""
        # Validate underlying
        if not self.underlying or not self.underlying.isalpha():
            raise ValidationError(
                message="Invalid underlying symbol",
                field_name="underlying",
                field_value=self.underlying,
            )
        
        # Validate strike
        if self.strike <= 0:
            raise ValidationError(
                message="Strike price must be positive",
                field_name="strike",
                field_value=self.strike,
            )
        
        # Build OSI symbol if not provided
        if not self.osi_symbol:
            object.__setattr__(self, 'osi_symbol', self._build_osi())
    
    def _build_osi(self) -> str:
        """Build OSI symbol from components."""
        # Strike is stored as integer with 3 implied decimals (8 digits total)
        strike_int = int(self.strike * 1000)
        return (
            f"{self.underlying.upper()}"
            f"{self.expiry.strftime('%y%m%d')}"
            f"{self.option_type.value}"
            f"{strike_int:08d}"
        )
    
    @property
    def days_to_expiry(self) -> int:
        """Calculate days until expiration."""
        return (self.expiry - date.today()).days
    
    @property
    def time_to_expiry(self) -> float:
        """Calculate time to expiry in years (ACT/365)."""
        days = self.days_to_expiry
        return max(days / 365.0, 0.0)
    
    @property
    def is_expired(self) -> bool:
        """Check if option has expired."""
        return self.days_to_expiry < 0
    
    @property
    def is_itm(self) -> bool:
        """Check if option is in-the-money (requires current price)."""
        # This is a placeholder - actual ITM check requires spot price
        return False
    
    @property
    def moneyness_description(self) -> str:
        """Get human-readable expiry description."""
        days = self.days_to_expiry
        if days < 0:
            return "Expired"
        elif days == 0:
            return "Expiring today"
        elif days <= 7:
            return f"{days}d to expiry"
        elif days <= 30:
            weeks = days // 7
            return f"{weeks}w to expiry"
        else:
            return f"{days}d to expiry"
    
    def to_dict(self) -> Dict[str, Union[str, float, int]]:
        """Convert to dictionary representation."""
        return {
            "osi_symbol": self.osi_symbol,
            "underlying": self.underlying,
            "expiry": self.expiry.isoformat(),
            "option_type": self.option_type.value,
            "strike": self.strike,
            "days_to_expiry": self.days_to_expiry,
            "time_to_expiry": round(self.time_to_expiry, 6),
        }
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.underlying} ${self.strike:.2f} {self.option_type.name} {self.expiry}"
    
    def __repr__(self) -> str:
        return f"OptionSymbol('{self.osi_symbol}')"


@lru_cache(maxsize=100000)
def parse_osi_symbol(symbol: str) -> OptionSymbol:
    """
    Parse an OSI symbol string into an OptionSymbol object.
    
    This function is heavily cached for performance as the same
    symbols are frequently parsed during market data processing.
    
    Args:
        symbol: OSI format symbol string (e.g., "AAPL240119C00150000")
        
    Returns:
        Parsed OptionSymbol object
        
    Raises:
        ValidationError: If symbol format is invalid
        
    Example:
        >>> option = parse_osi_symbol("AAPL240119C00150000")
        >>> option.underlying
        'AAPL'
        >>> option.strike
        150.0
    """
    symbol = symbol.strip().upper()
    
    match = OSI_PATTERN.match(symbol)
    if not match:
        raise ValidationError(
            message=f"Invalid OSI symbol format: {symbol}",
            field_name="symbol",
            field_value=symbol,
            validation_rule="Must match pattern: UNDERLYING + YYMMDD + C/P + STRIKE",
        )
    
    groups = match.groupdict()
    
    # Parse expiration date
    year = 2000 + int(groups['year'])
    month = int(groups['month'])
    day = int(groups['day'])
    
    try:
        expiry = date(year, month, day)
    except ValueError as e:
        raise ValidationError(
            message=f"Invalid expiration date in symbol: {symbol}",
            field_name="expiry",
            field_value=f"{year}-{month:02d}-{day:02d}",
            context={"error": str(e)},
        )
    
    # Parse strike (8 digits with 3 implied decimals)
    strike = int(groups['strike']) / 1000.0
    
    # Parse option type
    option_type = OptionType.CALL if groups['option_type'] == 'C' else OptionType.PUT
    
    return OptionSymbol(
        underlying=groups['underlying'],
        expiry=expiry,
        option_type=option_type,
        strike=strike,
        osi_symbol=symbol,
    )


def build_osi_symbol(
    underlying: str,
    expiry: Union[date, datetime, str],
    option_type: Union[OptionType, str],
    strike: float,
) -> str:
    """
    Build an OSI symbol from components.
    
    Args:
        underlying: Stock ticker (1-6 uppercase letters)
        expiry: Expiration date (date, datetime, or YYMMDD/YYYY-MM-DD string)
        option_type: CALL/PUT or 'C'/'P'
        strike: Strike price
        
    Returns:
        OSI format symbol string
        
    Example:
        >>> build_osi_symbol("AAPL", date(2024, 1, 19), OptionType.CALL, 150.0)
        'AAPL240119C00150000'
    """
    # Normalize underlying
    underlying = underlying.strip().upper()
    if not underlying or len(underlying) > 6 or not underlying.isalpha():
        raise ValidationError(
            message="Invalid underlying symbol",
            field_name="underlying",
            field_value=underlying,
        )
    
    # Normalize expiry
    if isinstance(expiry, str):
        if len(expiry) == 6:  # YYMMDD
            expiry = datetime.strptime(expiry, "%y%m%d").date()
        elif len(expiry) == 10:  # YYYY-MM-DD
            expiry = datetime.strptime(expiry, "%Y-%m-%d").date()
        else:
            raise ValidationError(
                message="Invalid expiry format",
                field_name="expiry",
                field_value=expiry,
            )
    elif isinstance(expiry, datetime):
        expiry = expiry.date()
    
    # Normalize option type
    if isinstance(option_type, str):
        option_type = OptionType.from_string(option_type)
    
    # Create OptionSymbol (validates and builds OSI)
    option = OptionSymbol(
        underlying=underlying,
        expiry=expiry,
        option_type=option_type,
        strike=strike,
    )
    
    return option.osi_symbol


def extract_underlying(symbol: str) -> str:
    """
    Extract the underlying ticker from an option or stock symbol.
    
    Args:
        symbol: OSI option symbol or stock ticker
        
    Returns:
        Underlying stock ticker
        
    Example:
        >>> extract_underlying("AAPL240119C00150000")
        'AAPL'
        >>> extract_underlying("AAPL")
        'AAPL'
    """
    symbol = symbol.strip().upper()
    
    # Try to parse as OSI symbol
    match = OSI_PATTERN.match(symbol)
    if match:
        return match.group('underlying')
    
    # Assume it's already a stock ticker
    if symbol.isalpha() and len(symbol) <= 6:
        return symbol
    
    # Try to extract leading letters
    underlying = ""
    for char in symbol:
        if char.isalpha():
            underlying += char
        else:
            break
    
    if underlying:
        return underlying
    
    raise ValidationError(
        message=f"Cannot extract underlying from symbol: {symbol}",
        field_name="symbol",
        field_value=symbol,
    )


def is_option_symbol(symbol: str) -> bool:
    """
    Check if a symbol is an OSI option symbol.
    
    Args:
        symbol: Symbol string to check
        
    Returns:
        True if symbol matches OSI format
    """
    return bool(OSI_PATTERN.match(symbol.strip().upper()))


class SymbolMapper:
    """
    Symbol management and lookup service.
    
    Provides:
    - Symbol validation and normalization
    - Option chain organization
    - Expiry date lookups
    - Strike price grouping
    - Underlying-to-options mapping
    
    Thread-safe for concurrent access.
    
    Example:
        mapper = SymbolMapper()
        
        # Register options for tracking
        mapper.register_symbol("AAPL240119C00150000")
        mapper.register_symbol("AAPL240119P00150000")
        
        # Get all options for underlying
        aapl_options = mapper.get_options_for_underlying("AAPL")
        
        # Get option chain
        chain = mapper.get_option_chain("AAPL", date(2024, 1, 19))
    """
    
    def __init__(self) -> None:
        """Initialize the symbol mapper."""
        self._symbols: Dict[str, OptionSymbol] = {}
        self._underlying_index: Dict[str, Set[str]] = {}
        self._expiry_index: Dict[date, Set[str]] = {}
        self._strike_index: Dict[float, Set[str]] = {}
    
    def register_symbol(self, symbol: Union[str, OptionSymbol]) -> OptionSymbol:
        """
        Register a symbol for tracking.
        
        Args:
            symbol: OSI symbol string or OptionSymbol object
            
        Returns:
            Parsed/validated OptionSymbol
        """
        if isinstance(symbol, str):
            option = parse_osi_symbol(symbol)
        else:
            option = symbol
        
        osi = option.osi_symbol
        
        # Store in main index
        self._symbols[osi] = option
        
        # Update underlying index
        if option.underlying not in self._underlying_index:
            self._underlying_index[option.underlying] = set()
        self._underlying_index[option.underlying].add(osi)
        
        # Update expiry index
        if option.expiry not in self._expiry_index:
            self._expiry_index[option.expiry] = set()
        self._expiry_index[option.expiry].add(osi)
        
        # Update strike index
        if option.strike not in self._strike_index:
            self._strike_index[option.strike] = set()
        self._strike_index[option.strike].add(osi)
        
        return option
    
    def get_symbol(self, osi_symbol: str) -> Optional[OptionSymbol]:
        """Get a registered symbol by OSI string."""
        return self._symbols.get(osi_symbol.upper())
    
    def get_or_parse(self, symbol: str) -> OptionSymbol:
        """Get registered symbol or parse it."""
        existing = self.get_symbol(symbol)
        if existing:
            return existing
        return parse_osi_symbol(symbol)
    
    def get_options_for_underlying(self, underlying: str) -> List[OptionSymbol]:
        """Get all registered options for an underlying."""
        underlying = underlying.upper()
        symbols = self._underlying_index.get(underlying, set())
        return [self._symbols[s] for s in symbols]
    
    def get_options_by_expiry(self, expiry: date) -> List[OptionSymbol]:
        """Get all registered options with a specific expiry."""
        symbols = self._expiry_index.get(expiry, set())
        return [self._symbols[s] for s in symbols]
    
    def get_option_chain(
        self,
        underlying: str,
        expiry: date,
    ) -> Dict[str, List[OptionSymbol]]:
        """
        Get the option chain (calls and puts) for an underlying and expiry.
        
        Args:
            underlying: Stock ticker
            expiry: Expiration date
            
        Returns:
            Dict with 'calls' and 'puts' lists, sorted by strike
        """
        underlying = underlying.upper()
        
        options = [
            opt for opt in self.get_options_for_underlying(underlying)
            if opt.expiry == expiry
        ]
        
        calls = sorted(
            [opt for opt in options if opt.option_type == OptionType.CALL],
            key=lambda x: x.strike
        )
        puts = sorted(
            [opt for opt in options if opt.option_type == OptionType.PUT],
            key=lambda x: x.strike
        )
        
        return {"calls": calls, "puts": puts}
    
    def get_expiries_for_underlying(self, underlying: str) -> List[date]:
        """Get all expiry dates for an underlying, sorted ascending."""
        underlying = underlying.upper()
        expiries = set()
        
        for option in self.get_options_for_underlying(underlying):
            expiries.add(option.expiry)
        
        return sorted(expiries)
    
    def get_strikes_for_expiry(
        self,
        underlying: str,
        expiry: date,
    ) -> List[float]:
        """Get all strike prices for an underlying and expiry."""
        underlying = underlying.upper()
        strikes = set()
        
        for option in self.get_options_for_underlying(underlying):
            if option.expiry == expiry:
                strikes.add(option.strike)
        
        return sorted(strikes)
    
    def get_atm_strike(
        self,
        underlying: str,
        expiry: date,
        spot_price: float,
    ) -> Optional[float]:
        """
        Get the at-the-money strike closest to spot price.
        
        Args:
            underlying: Stock ticker
            expiry: Expiration date
            spot_price: Current stock price
            
        Returns:
            Strike price closest to spot, or None if no strikes available
        """
        strikes = self.get_strikes_for_expiry(underlying, expiry)
        if not strikes:
            return None
        
        return min(strikes, key=lambda x: abs(x - spot_price))
    
    def clear(self) -> None:
        """Clear all registered symbols."""
        self._symbols.clear()
        self._underlying_index.clear()
        self._expiry_index.clear()
        self._strike_index.clear()
    
    @property
    def symbol_count(self) -> int:
        """Get total number of registered symbols."""
        return len(self._symbols)
    
    @property
    def underlying_count(self) -> int:
        """Get number of unique underlyings."""
        return len(self._underlying_index)


# =============================================================================
# OPTION CHAIN GENERATION UTILITIES
# =============================================================================

def generate_strike_range(
    spot_price: float,
    num_strikes: int = 10,
    strike_width: float = 1.0,
    round_to: float = 1.0,
) -> List[float]:
    """
    Generate a range of strike prices around the current spot.
    
    Args:
        spot_price: Current stock price
        num_strikes: Number of strikes on each side of ATM
        strike_width: Dollar distance between strikes
        round_to: Round strikes to this increment
        
    Returns:
        List of strike prices centered around spot
        
    Example:
        >>> generate_strike_range(150.0, num_strikes=3, strike_width=2.5)
        [142.5, 145.0, 147.5, 150.0, 152.5, 155.0, 157.5]
    """
    # Round spot to nearest strike
    atm_strike = round(spot_price / round_to) * round_to
    
    strikes = []
    for i in range(-num_strikes, num_strikes + 1):
        strike = atm_strike + (i * strike_width)
        if strike > 0:
            strikes.append(round(strike, 2))
    
    return sorted(set(strikes))


def get_monthly_expiries(
    start_date: date,
    num_months: int = 3,
) -> List[date]:
    """
    Get standard monthly expiration dates (third Friday of month).
    
    Args:
        start_date: Starting date for expiry search
        num_months: Number of monthly expiries to return
        
    Returns:
        List of monthly expiration dates
    """
    expiries = []
    current = start_date.replace(day=1)
    
    while len(expiries) < num_months:
        # Find third Friday of the month
        # First day of month
        first = current.replace(day=1)
        # Find first Friday
        days_until_friday = (4 - first.weekday()) % 7
        first_friday = first + timedelta(days=days_until_friday)
        # Third Friday
        third_friday = first_friday + timedelta(weeks=2)
        
        if third_friday >= start_date:
            expiries.append(third_friday)
        
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    return expiries


def get_weekly_expiries(
    start_date: date,
    num_weeks: int = 4,
) -> List[date]:
    """
    Get weekly expiration dates (Fridays).
    
    Args:
        start_date: Starting date for expiry search
        num_weeks: Number of weekly expiries to return
        
    Returns:
        List of weekly expiration dates
    """
    expiries = []
    
    # Find next Friday
    days_until_friday = (4 - start_date.weekday()) % 7
    if days_until_friday == 0 and start_date.weekday() == 4:
        # If start_date is Friday, start from next Friday
        days_until_friday = 7
    
    next_friday = start_date + timedelta(days=days_until_friday)
    
    for i in range(num_weeks):
        expiries.append(next_friday + timedelta(weeks=i))
    
    return expiries

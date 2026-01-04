"""
Alpaca Options Lab - Volatility Lab Module (Phase 2 Modules 9-10)

Comprehensive volatility analysis tools:
- Volatility surface construction
- IV analysis and modeling
- Term structure analysis
- Volatility skew metrics
- Vol-based trading strategies
"""

from src.volatility.surface import (
    VolatilitySurface,
    SurfaceConfig,
    SurfacePoint,
    InterpolationMethod,
)
from src.volatility.iv_engine import (
    IVEngine,
    IVResult,
    IVModel,
)
from src.volatility.term_structure import (
    TermStructure,
    TermStructureAnalysis,
    ContangoBackwardation,
)
from src.volatility.skew import (
    VolatilitySkew,
    SkewMetrics,
    SkewType,
)
from src.volatility.strategies import (
    VolStrategy,
    VolArbitrage,
    CalendarSpreadFinder,
    SkewTrade,
)

__all__ = [
    # Surface
    "VolatilitySurface",
    "SurfaceConfig",
    "SurfacePoint",
    "InterpolationMethod",
    # IV Engine
    "IVEngine",
    "IVResult",
    "IVModel",
    # Term Structure
    "TermStructure",
    "TermStructureAnalysis",
    "ContangoBackwardation",
    # Skew
    "VolatilitySkew",
    "SkewMetrics",
    "SkewType",
    # Strategies
    "VolStrategy",
    "VolArbitrage",
    "CalendarSpreadFinder",
    "SkewTrade",
]

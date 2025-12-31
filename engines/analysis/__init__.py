"""
Analysis Engine Module
Phase 15 - Agent-UX + AI Enhancements

Contains pattern recognition, technical analysis, and AI forecasting tools.

Modules:
- patterns: Chart pattern detection using scipy
- talib_patterns: TA-Lib candlestick pattern recognition (61 patterns)
- ai_options_forecast: AI-powered options recommendations
"""

from .patterns import PatternDetector

# Lazy imports for optional dependencies
try:
    from .talib_patterns import TALibPatternEngine, scan_symbol_patterns, TALIB_AVAILABLE
except ImportError:
    TALibPatternEngine = None
    scan_symbol_patterns = None
    TALIB_AVAILABLE = False

try:
    from .ai_options_forecast import AIOptionsForecast, OptionRecommendation
except ImportError:
    AIOptionsForecast = None
    OptionRecommendation = None

__all__ = [
    "PatternDetector",
    "TALibPatternEngine",
    "scan_symbol_patterns",
    "TALIB_AVAILABLE",
    "AIOptionsForecast",
    "OptionRecommendation",
]

"""
Analysis Engine Package
=======================
Phase 1: Hybrid Sentiment Engine - Pattern Detection

Provides technical analysis and pattern recognition:
- Double Bottom detection
- Bull Flag detection
- Head & Shoulders (future)
- Support/Resistance levels

Usage:
    from financial_dashboard.engines.analysis import PatternDetector
    
    detector = PatternDetector()
    patterns = detector.detect_patterns(price_series)
"""

from .patterns import PatternDetector, PatternResult

__all__ = ['PatternDetector', 'PatternResult']


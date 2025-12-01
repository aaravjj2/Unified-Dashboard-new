"""
Stock Picker Package - Automated stock selection with multi-factor scoring.

Modules:
- universe: Define stock universes (S&P 500, Russell 2000)
- momentum_scorer: Momentum analysis
- sentiment_scorer: Sentiment analysis  
- fundamental_scorer: Fundamental metrics
- technical_scorer: Technical indicators
- ensemble_picker: Combine scores and rank stocks
"""

from .universe import StockUniverse
from .ensemble_picker import EnsemblePicker

__all__ = ['StockUniverse', 'EnsemblePicker']

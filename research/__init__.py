"""
Research package for unified-dashboard.
Provides storage abstractions for research briefs.
"""

from .store import ResearchStore, JSONStore

__all__ = ['ResearchStore', 'JSONStore']

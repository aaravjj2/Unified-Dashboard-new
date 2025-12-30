"""
Execution Module - Phase 4 TradeOps

Provides order routing and execution management.
"""

from .router import OrderRouter, OrderStatus, ExecutionResult

__all__ = ['OrderRouter', 'OrderStatus', 'ExecutionResult']

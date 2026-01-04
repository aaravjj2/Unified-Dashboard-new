"""
Alpaca Options Lab - Multi-Account Manager (Phase 2 Modules 14-15)

Manage multiple trading accounts:
- Account aggregation
- Position synchronization
- Order routing per account
- Performance attribution
- Risk allocation
"""

from src.accounts.manager import (
    AccountManager,
    Account,
    AccountType,
    AccountStatus,
)
from src.accounts.allocator import (
    CapitalAllocator,
    AllocationStrategy,
    AllocationResult,
)
from src.accounts.aggregator import (
    PositionAggregator,
    AggregatedPosition,
    AccountSummary,
)

__all__ = [
    # Manager
    "AccountManager",
    "Account",
    "AccountType",
    "AccountStatus",
    # Allocator
    "CapitalAllocator",
    "AllocationStrategy",
    "AllocationResult",
    # Aggregator
    "PositionAggregator",
    "AggregatedPosition",
    "AccountSummary",
]

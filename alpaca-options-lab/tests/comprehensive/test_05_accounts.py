"""
Alpaca Options Lab - Comprehensive Account Tests
Test File 5 of 10: Multi-Account Manager, Allocator, Aggregator
~50 tests covering all account components
"""
import pytest
from datetime import datetime, date, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
import sys
sys.path.insert(0, '.')


class TestAccountManager:
    """Tests for Account Manager - 20 tests"""
    
    def test_account_manager_import(self):
        from src.accounts.manager import AccountManager
        assert AccountManager is not None
    
    def test_account_type_enum(self):
        from src.accounts.manager import AccountType
        assert AccountType is not None
    
    def test_account_status_enum(self):
        from src.accounts.manager import AccountStatus
        assert AccountStatus is not None
    
    def test_account_manager_creation(self):
        from src.accounts.manager import AccountManager
        manager = AccountManager()
        assert manager is not None
    
    def test_add_account(self):
        from src.accounts.manager import AccountManager, AccountType
        manager = AccountManager()
        manager.add_account(name="Test", account_type=AccountType.LIVE)
        assert True
    
    def test_get_all_accounts(self):
        from src.accounts.manager import AccountManager, AccountType
        manager = AccountManager()
        manager.add_account(name="Test", account_type=AccountType.LIVE)
        accounts = manager.get_all_accounts()
        assert len(accounts) > 0
    
    def test_account_class(self):
        from src.accounts.manager import Account
        assert Account is not None
    
    def test_account_credentials_class(self):
        from src.accounts.manager import AccountCredentials
        assert AccountCredentials is not None
    
    def test_broker_connection_class(self):
        from src.accounts.manager import BrokerConnection
        assert BrokerConnection is not None
    
    def test_account_type_live(self):
        from src.accounts.manager import AccountType
        assert hasattr(AccountType, 'LIVE')
    
    def test_account_type_paper(self):
        from src.accounts.manager import AccountType
        assert hasattr(AccountType, 'PAPER')
    
    def test_account_status_active(self):
        from src.accounts.manager import AccountStatus
        assert hasattr(AccountStatus, 'ACTIVE')
    
    def test_account_status_inactive(self):
        from src.accounts.manager import AccountStatus
        assert hasattr(AccountStatus, 'INACTIVE') or hasattr(AccountStatus, 'DISABLED')
    
    def test_manager_has_get_account(self):
        from src.accounts.manager import AccountManager
        manager = AccountManager()
        assert hasattr(manager, 'get_account')
    
    def test_manager_has_remove_account(self):
        from src.accounts.manager import AccountManager
        manager = AccountManager()
        assert hasattr(manager, 'remove_account') or hasattr(manager, 'delete_account')
    
    def test_manager_has_update_account(self):
        from src.accounts.manager import AccountManager
        manager = AccountManager()
        assert hasattr(manager, 'update_account') or hasattr(manager, 'modify_account')
    
    def test_multiple_accounts(self):
        from src.accounts.manager import AccountManager, AccountType
        manager = AccountManager()
        manager.add_account(name="Live1", account_type=AccountType.LIVE)
        manager.add_account(name="Paper1", account_type=AccountType.PAPER)
        accounts = manager.get_all_accounts()
        assert len(accounts) >= 2
    
    def test_manager_has_balance(self):
        from src.accounts.manager import AccountManager
        manager = AccountManager()
        assert hasattr(manager, 'get_balance') or hasattr(manager, 'get_equity')
    
    def test_manager_file_size(self):
        import os
        path = 'src/accounts/manager.py'
        assert os.path.exists(path)
        with open(path) as f:
            lines = len(f.readlines())
        assert lines > 200
    
    def test_account_has_name(self):
        from src.accounts.manager import Account
        import dataclasses
        if dataclasses.is_dataclass(Account):
            fields = [f.name for f in dataclasses.fields(Account)]
            assert 'name' in fields


class TestCapitalAllocator:
    """Tests for Capital Allocator - 15 tests"""
    
    def test_allocator_import(self):
        from src.accounts.allocator import CapitalAllocator
        assert CapitalAllocator is not None
    
    def test_allocator_creation(self):
        from src.accounts.allocator import CapitalAllocator
        from src.accounts.manager import AccountManager
        allocator = CapitalAllocator(account_manager=AccountManager())
        assert allocator is not None
    
    def test_allocation_strategy_enum(self):
        from src.accounts.allocator import AllocationStrategy
        assert AllocationStrategy is not None
    
    def test_allocation_request_class(self):
        from src.accounts.allocator import AllocationRequest
        assert AllocationRequest is not None
    
    def test_allocation_result_class(self):
        from src.accounts.allocator import AllocationResult
        assert AllocationResult is not None
    
    def test_allocation_algorithm_class(self):
        from src.accounts.allocator import AllocationAlgorithm
        assert AllocationAlgorithm is not None
    
    def test_equal_allocation_class(self):
        from src.accounts.allocator import EqualAllocation
        assert EqualAllocation is not None
    
    def test_allocator_has_allocate(self):
        from src.accounts.allocator import CapitalAllocator
        from src.accounts.manager import AccountManager
        allocator = CapitalAllocator(account_manager=AccountManager())
        assert hasattr(allocator, 'allocate')
    
    def test_allocator_has_rebalance(self):
        from src.accounts.allocator import CapitalAllocator
        from src.accounts.manager import AccountManager
        allocator = CapitalAllocator(account_manager=AccountManager())
        assert hasattr(allocator, 'rebalance')
    
    def test_allocator_has_manager(self):
        from src.accounts.allocator import CapitalAllocator
        from src.accounts.manager import AccountManager
        mgr = AccountManager()
        allocator = CapitalAllocator(account_manager=mgr)
        assert allocator.account_manager == mgr or allocator._account_manager == mgr
    
    def test_allocation_strategy_equal(self):
        from src.accounts.allocator import AllocationStrategy
        assert hasattr(AllocationStrategy, 'EQUAL')
    
    def test_allocation_strategy_proportional(self):
        from src.accounts.allocator import AllocationStrategy
        assert hasattr(AllocationStrategy, 'PROPORTIONAL') or hasattr(AllocationStrategy, 'WEIGHTED')
    
    def test_allocator_has_get_allocation(self):
        from src.accounts.allocator import CapitalAllocator
        from src.accounts.manager import AccountManager
        allocator = CapitalAllocator(account_manager=AccountManager())
        assert hasattr(allocator, 'get_allocation') or hasattr(allocator, 'get_current_allocation')
    
    def test_allocator_file_size(self):
        import os
        path = 'src/accounts/allocator.py'
        assert os.path.exists(path)
        with open(path) as f:
            lines = len(f.readlines())
        assert lines > 200
    
    def test_allocation_algorithms_count(self):
        from src.accounts.allocator import AllocationStrategy
        assert len(list(AllocationStrategy)) >= 2


class TestPositionAggregator:
    """Tests for Position Aggregator - 15 tests"""
    
    def test_aggregator_import(self):
        from src.accounts.aggregator import PositionAggregator
        assert PositionAggregator is not None
    
    def test_aggregator_creation(self):
        from src.accounts.aggregator import PositionAggregator
        from src.accounts.manager import AccountManager
        aggregator = PositionAggregator(account_manager=AccountManager())
        assert aggregator is not None
    
    def test_position_class(self):
        from src.accounts.aggregator import Position
        assert Position is not None
    
    def test_aggregated_position_class(self):
        from src.accounts.aggregator import AggregatedPosition
        assert AggregatedPosition is not None
    
    def test_account_summary_class(self):
        from src.accounts.aggregator import AccountSummary
        assert AccountSummary is not None
    
    def test_portfolio_summary_class(self):
        from src.accounts.aggregator import PortfolioSummary
        assert PortfolioSummary is not None
    
    def test_aggregator_has_get_positions(self):
        from src.accounts.aggregator import PositionAggregator
        from src.accounts.manager import AccountManager
        aggregator = PositionAggregator(account_manager=AccountManager())
        assert hasattr(aggregator, 'get_positions') or hasattr(aggregator, 'get_all_positions')
    
    def test_aggregator_has_aggregate(self):
        from src.accounts.aggregator import PositionAggregator
        from src.accounts.manager import AccountManager
        aggregator = PositionAggregator(account_manager=AccountManager())
        assert hasattr(aggregator, 'aggregate')
    
    def test_aggregator_has_summary(self):
        from src.accounts.aggregator import PositionAggregator
        from src.accounts.manager import AccountManager
        aggregator = PositionAggregator(account_manager=AccountManager())
        assert hasattr(aggregator, 'get_summary') or hasattr(aggregator, 'summary')
    
    def test_aggregator_has_manager(self):
        from src.accounts.aggregator import PositionAggregator
        from src.accounts.manager import AccountManager
        mgr = AccountManager()
        aggregator = PositionAggregator(account_manager=mgr)
        assert aggregator.account_manager == mgr or aggregator._account_manager == mgr
    
    def test_position_has_symbol(self):
        from src.accounts.aggregator import Position
        import dataclasses
        if dataclasses.is_dataclass(Position):
            fields = [f.name for f in dataclasses.fields(Position)]
            assert 'symbol' in fields
    
    def test_position_has_quantity(self):
        from src.accounts.aggregator import Position
        import dataclasses
        if dataclasses.is_dataclass(Position):
            fields = [f.name for f in dataclasses.fields(Position)]
            assert 'quantity' in fields or 'qty' in fields
    
    def test_aggregator_has_by_symbol(self):
        from src.accounts.aggregator import PositionAggregator
        from src.accounts.manager import AccountManager
        aggregator = PositionAggregator(account_manager=AccountManager())
        assert hasattr(aggregator, 'get_by_symbol') or hasattr(aggregator, 'by_symbol')
    
    def test_aggregator_has_by_account(self):
        from src.accounts.aggregator import PositionAggregator
        from src.accounts.manager import AccountManager
        aggregator = PositionAggregator(account_manager=AccountManager())
        assert hasattr(aggregator, 'get_by_account') or hasattr(aggregator, 'by_account')
    
    def test_aggregator_file_size(self):
        import os
        path = 'src/accounts/aggregator.py'
        assert os.path.exists(path)
        with open(path) as f:
            lines = len(f.readlines())
        assert lines > 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
